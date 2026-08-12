"""M-02 `modelo-dominio` — entidades, objetos de valor e invariantes.

Domain Model (Fowler) com DDD tático: os invariantes I-1..I-7 vivem AQUI, nos
tipos, não nos serviços. Ver `specs/models/modelo-dominio.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from .dinheiro import Dinheiro

ESCOPO_GERAL = "*"


class EmpateInsoluvel(Exception):
    """I-6: incoerência é barrada na VALIDAÇÃO, nunca em runtime.

    Se esta exceção chega ao runtime, o defeito é do validador — o motor deve
    falhar ruidosamente, jamais escolher um vencedor por conta própria.
    """


# --------------------------------------------------------------------------
# Objetos de valor
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Faixa:
    """A-11: intervalo FECHADO [minimo, maximo]; `maximo=None` é aberto (∞)."""

    minimo: int
    maximo: int | None = None

    def __post_init__(self) -> None:
        if self.minimo < 1:
            raise ValueError(f"faixa inválida: mínimo {self.minimo} < 1")
        if self.maximo is not None and self.maximo < self.minimo:
            raise ValueError(
                f"faixa invertida: De ({self.minimo}) > Ate ({self.maximo})"
            )

    def contem(self, quantidade: int) -> bool:
        if quantidade < self.minimo:
            return False
        return self.maximo is None or quantidade <= self.maximo

    def sobrepoe(self, outra: "Faixa") -> bool:
        fim_a = self.maximo if self.maximo is not None else float("inf")
        fim_b = outra.maximo if outra.maximo is not None else float("inf")
        return self.minimo <= fim_b and outra.minimo <= fim_a

    def __str__(self) -> str:
        return f"{self.minimo}–{self.maximo if self.maximo is not None else '∞'}"


@dataclass(frozen=True, slots=True)
class Vigencia:
    """Valid time de uma única linha do tempo (Snodgrass). Sem eixo de conhecimento."""

    inicio: date
    fim: date | None = None

    def contem(self, d: date) -> bool:
        if d < self.inicio:
            return False
        return self.fim is None or d <= self.fim

    def sobrepoe(self, outra: "Vigencia") -> bool:
        fim_a = self.fim or date.max
        fim_b = outra.fim or date.max
        return self.inicio <= fim_b and outra.inicio <= fim_a


class TipoEfeito(StrEnum):
    PRECO_UNITARIO = "PRECO_UNITARIO"
    DESCONTO_PCT = "DESCONTO_PCT"


class Efeito(Protocol):
    """Strategy (GoF) — único ponto do domínio com variação real de algoritmo."""

    tipo: TipoEfeito

    def aplicar(self, preco_base: Dinheiro) -> Dinheiro: ...
    def descrever(self) -> str: ...


@dataclass(frozen=True, slots=True)
class PrecoUnitario:
    valor: Dinheiro
    tipo: TipoEfeito = TipoEfeito.PRECO_UNITARIO

    def aplicar(self, preco_base: Dinheiro) -> Dinheiro:
        return self.valor

    def descrever(self) -> str:
        return f"{self.valor}/un"


@dataclass(frozen=True, slots=True)
class DescontoPct:
    pct: Decimal
    tipo: TipoEfeito = TipoEfeito.DESCONTO_PCT

    def __post_init__(self) -> None:
        if not (Decimal(0) < self.pct < Decimal(100)):
            raise ValueError(f"desconto fora de (0,100): {self.pct}")

    def aplicar(self, preco_base: Dinheiro) -> Dinheiro:
        return preco_base.aplicar_pct(Decimal(100) - self.pct)

    def descrever(self) -> str:
        return f"{self.pct.normalize()}% de desconto"


# --------------------------------------------------------------------------
# Entidades
# --------------------------------------------------------------------------


def normalizar_sku(bruto: str) -> str:
    """A-02: SKU é chave, normalizável por trim + caixa alta.

    Sem isso nasce um produto fantasma (` sku-1002 `) e a sobreposição com o
    SKU real fica invisível (achado N-05 / V-02).
    """
    return (bruto or "").strip().upper()


@dataclass(frozen=True, slots=True)
class Produto:
    sku: str
    descricao: str
    preco_base: Dinheiro  # A-05/ASS-05: obrigatório — não há Produto sem base

    def __post_init__(self) -> None:
        if not self.sku:
            raise ValueError("produto sem SKU")


@dataclass(frozen=True, slots=True)
class Regra:
    id: str
    escopo: str  # um SKU específico OU ESCOPO_GERAL
    faixa: Faixa
    efeito: Efeito
    prioridade: int
    vigencia: Vigencia

    @property
    def e_especifica(self) -> bool:
        return self.escopo != ESCOPO_GERAL

    def avaliar(self, sku: str, quantidade: int, quando: date) -> "MotivoCodigo":
        """Devolve o motivo — é o que alimenta o trace exaustivo (I-3)."""
        if self.e_especifica and self.escopo != sku:
            return MotivoCodigo.ESCOPO_DIVERGENTE
        if not self.faixa.contem(quantidade):
            return MotivoCodigo.FORA_DA_FAIXA
        if not self.vigencia.contem(quando):
            return MotivoCodigo.FORA_DA_VIGENCIA
        return MotivoCodigo.CANDIDATA


class ConjuntoDeRegras:
    """V(4)/X5 — o índice nasce COM o dado.

    Indexa por escopo na construção e expõe `regras_de(sku)`, para o motor
    avaliar ~10 regras em vez de ~1.000 (PERF-06). V(5)/Y4: é construído na
    FRONTEIRA DE AVALIAÇÃO — uma vez ao carregar a versão no cache e uma vez
    ao validar ou precificar a partir do rascunho —, NUNCA por tecla digitada
    na grade. A grade edita uma lista simples.

    V(5)/Y9 — ARQ-08 aceito: o índice é detalhe INTERNO deste VO imutável e
    não vaza no contrato; trocar a estratégia de indexação fica confinado aqui.
    """

    __slots__ = ("_todas", "_por_sku", "_gerais")

    def __init__(self, regras: tuple[Regra, ...] | list[Regra]) -> None:
        self._todas: tuple[Regra, ...] = tuple(regras)
        self._por_sku: dict[str, list[Regra]] = {}
        self._gerais: list[Regra] = []
        for r in self._todas:
            if r.e_especifica:
                self._por_sku.setdefault(r.escopo, []).append(r)
            else:
                self._gerais.append(r)

    def regras_de(self, sku: str) -> list[Regra]:
        return [*self._por_sku.get(sku, ()), *self._gerais]

    @property
    def todas(self) -> tuple[Regra, ...]:
        return self._todas

    def __len__(self) -> int:
        return len(self._todas)


class TipoOrigem(StrEnum):
    IMPORTACAO = "IMPORTACAO"
    EDICAO = "EDICAO"
    REVERSAO = "REVERSAO"


@dataclass(frozen=True, slots=True)
class Origem:
    """Procedência da versão — GOV-03, GOV-05, GOV-07."""

    tipo: TipoOrigem
    justificativa: str  # V(5)/Y7: obrigatória em TODA publicação
    arquivo: str | None = None
    sha256: str | None = None
    revertida_de: int | None = None
    relatorio: dict | None = None  # rejeitadas, paridade, colunas desconhecidas

    def __post_init__(self) -> None:
        if not (self.justificativa or "").strip():
            raise ValueError("toda publicação exige justificativa (GOV-07)")
        if self.tipo is TipoOrigem.REVERSAO and self.revertida_de is None:
            raise ValueError("reversão precisa registrar de qual versão veio")


@dataclass(frozen=True, slots=True)
class VersaoDeRegras:
    """Snapshot imutável (I-4). Correção se faz publicando outra versão."""

    numero: int
    publicada_em: datetime
    vigente_desde: date  # A-21: atribuída pelo SISTEMA, nunca escolhida
    autor: str  # A-14: identidade DECLARADA, não autenticada
    origem: Origem
    regras: tuple[Regra, ...]

    def conjunto(self) -> ConjuntoDeRegras:
        return ConjuntoDeRegras(self.regras)


# --------------------------------------------------------------------------
# Trace e decisão
# --------------------------------------------------------------------------


class MotivoCodigo(StrEnum):
    """LIN-01: código enumerado — a prosa é DERIVADA por `explicador`.

    Sem isso, CS-2 ("toda candidata com veredito e motivo") não é verificável
    por teste automatizado, porque duas implementações corretas produziriam
    prosa diferente.
    """

    VENCEU = "VENCEU"
    CANDIDATA = "CANDIDATA"
    FORA_DA_FAIXA = "FORA_DA_FAIXA"
    FORA_DA_VIGENCIA = "FORA_DA_VIGENCIA"
    ESCOPO_DIVERGENTE = "ESCOPO_DIVERGENTE"
    PERDEU_POR_PRIORIDADE = "PERDEU_POR_PRIORIDADE"
    PERDEU_POR_ESPECIFICIDADE = "PERDEU_POR_ESPECIFICIDADE"


class ResultadoTrace(StrEnum):
    """V(3)/W5 — 'nenhuma regra casou' não é veredito de regra nenhuma."""

    APLICOU_REGRA = "APLICOU_REGRA"
    PRECO_BASE = "PRECO_BASE"


@dataclass(frozen=True, slots=True)
class Veredito:
    regra_id: str
    codigo: MotivoCodigo
    detalhe: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Trace:
    resultado: ResultadoTrace
    vereditos: tuple[Veredito, ...]
    calculo: str
    vencedora: str | None = None

    def __post_init__(self) -> None:
        # I-3: trace nunca vazio.
        if not self.vereditos and self.resultado is ResultadoTrace.APLICOU_REGRA:
            raise ValueError("trace sem vereditos com regra aplicada (I-3)")
        # V(4)/X9 — IMP-05: o invariante ENTRE os dois campos vive no tipo que
        # os contém, não na cabeça de quem implementa.
        venceu = [v for v in self.vereditos if v.codigo is MotivoCodigo.VENCEU]
        if self.resultado is ResultadoTrace.PRECO_BASE and venceu:
            raise ValueError("resultado PRECO_BASE com veredito VENCEU")
        if self.resultado is ResultadoTrace.APLICOU_REGRA and len(venceu) != 1:
            raise ValueError("resultado APLICOU_REGRA exige exatamente um VENCEU")


@dataclass(frozen=True, slots=True)
class Precificacao:
    """Resultado puro do motor.

    DIVERGÊNCIA DE CONTRATO encontrada pelo micro-check S7 da Fase 5: o
    documento de arquitetura diz `precificar(...) -> Decisao`, mas `Decisao`
    carrega `registrada_em: datetime` e A-04 proíbe o motor de ler o relógio.
    O motor devolve `Precificacao`; `servico-aplicacao` — que já é a fronteira
    de efeitos — carimba id, solicitante e instante. A premissa vence o
    diagrama.
    """

    preco_unitario: Dinheiro
    total: Dinheiro
    trace: Trace


@dataclass(frozen=True, slots=True)
class Decisao:
    id: str
    sku: str
    quantidade: int
    data_pedido: date
    versao_regras: int
    preco_unitario: Dinheiro
    total: Dinheiro
    trace: Trace
    solicitante: str  # GOV-02
    registrada_em: datetime
