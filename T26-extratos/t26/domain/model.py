"""M-01 domain-model — entidades, value objects e invariantes.

Núcleo puro: NÃO importa ofxtools, sqlite3 nem csv (fronteira declarada em
specs/technical/architecture.md).

Invariantes garantidos aqui, na construção do objeto (specs/domain/glossario.md):
  I1 dinheiro nunca é float · I2 sinal é semântico · I3 todo item tem um estado
  terminal · I4 casamento é 1:1 · I5 nunca funde sob evidência fraca ·
  I6 colisão legítima é preservada · I7 resolução humana é soberana ·
  I8 importação é idempotente.

Decisões de V(3) materializadas neste módulo:
  - ChaveEvento é DERIVADA sob demanda, nunca armazenada (IMP-06): mudar a regra
    de normalização não invalida histórico.
  - Identidade da observação é ChaveNatural com ordinal (ASM-09): distingue
    colisão legítima (I6) e reproduz-se igual na reimportação sobreposta (I8).
  - Dois eixos ortogonais Resultado × Situacao, com a projeção estado_val3
    restaurando VAL-3 tal como escrito na Fase 0 (PRC-06).
  - Igualdade de Dinheiro pelo valor numérico, não pela representação (ASM-11).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Sequence

# Versão da regra de normalização. Entra na ChaveEvento derivada; mudá-la muda as
# chaves calculadas daqui em diante sem invalidar nada gravado (IMP-06).
VERSAO_REGRA_NORMALIZACAO = "1"


class ErroDominio(ValueError):
    """Violação de invariante de domínio. Nunca deve ser silenciada."""


# --------------------------------------------------------------------------- #
# Dinheiro (I1)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Dinheiro:
    """Valor monetário. Sempre Decimal — float é proibido em caminho monetário.

    Guarda a escala original recebida da fonte (ASM-01: OFX admite mais de duas
    casas e arredondar na entrada destruiria a comparação exata que VAL-2 exige).
    A igualdade é pelo VALOR NUMÉRICO e não pela representação (ASM-11), de modo
    que 1250.00 vindo do CSV e 1250.000 vindo do OFX são o mesmo valor.
    """

    valor: Decimal
    moeda: str = "BRL"

    def __post_init__(self) -> None:
        if isinstance(self.valor, float):
            raise ErroDominio(
                "I1: valor monetário recebido como float. Use Decimal ou str."
            )
        if not isinstance(self.valor, Decimal):
            raise ErroDominio(f"I1: valor monetário deve ser Decimal, veio {type(self.valor).__name__}")

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Dinheiro):
            return NotImplemented
        return self.moeda == outro.moeda and self.valor == outro.valor

    def __hash__(self) -> int:
        return hash((self.moeda, self.valor.normalize()))

    @property
    def negativo(self) -> bool:
        return self.valor < 0

    @property
    def sinal(self) -> int:
        """-1 débito, +1 crédito, 0 valor nulo (I2: sinal é semântico)."""
        if self.valor < 0:
            return -1
        if self.valor > 0:
            return 1
        return 0

    def absoluto(self) -> Decimal:
        return abs(self.valor)

    def texto(self) -> str:
        return f"{self.valor:.2f}"

    @classmethod
    def de_texto(cls, bruto: str, moeda: str = "BRL") -> "Dinheiro":
        return cls(Decimal(bruto.strip()), moeda)


# --------------------------------------------------------------------------- #
# Normalização e chaves
# --------------------------------------------------------------------------- #


def normalizar_descricao(bruta: str) -> str:
    """Regra de normalização de descrição, versionada e explícita (LIN-04).

    Sem regra declarada, duas implementações do mesmo contrato produziriam chaves
    de evento diferentes para a mesma transação. As transformações, nesta ordem:
    remove acentos, caixa alta, colapsa espaços, remove pontuação de separação.
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", bruta) if not unicodedata.combining(c)
    )
    caixa_alta = sem_acento.upper()
    limpa = "".join(c if c.isalnum() or c.isspace() else " " for c in caixa_alta)
    return " ".join(limpa.split())


@dataclass(frozen=True)
class ChaveNatural:
    """Identidade da OBSERVAÇÃO — a linha, não o evento financeiro (R4 de V(3)).

    Quando há identificador nativo, a chave é (fonte, conta, fitid). O escopo de
    unicidade do FITID é a CONTA e não a instituição, conforme a especificação
    OFX (specs/references/fontes-externas.md §1.2) — daí fonte e conta comporem
    a chave.

    Sem identificador nativo (caso do CSV), a chave é
    (fonte, conta, data, valor, descricao_bruta, ordinal). O `ordinal` é a
    posição da linha dentro do grupo de linhas idênticas do mesmo dia: distingue
    as duas transações legitimamente iguais (I6) e é reproduzido igual numa
    reimportação de janela sobreposta, restaurando a idempotência do UC-2 (I8).
    """

    fonte: str
    conta: str
    fitid: str | None = None
    data: date | None = None
    valor_texto: str | None = None
    descricao_bruta: str | None = None
    ordinal: int = 0

    def __post_init__(self) -> None:
        if self.fitid is None and (self.data is None or self.valor_texto is None):
            raise ErroDominio(
                "ChaveNatural sem fitid exige data e valor para compor a chave natural"
            )

    def texto(self) -> str:
        if self.fitid is not None:
            return f"{self.fonte}|{self.conta}|fitid:{self.fitid}"
        return (
            f"{self.fonte}|{self.conta}|nat:{self.data.isoformat()}"
            f"|{self.valor_texto}|{self.descricao_bruta}|{self.ordinal}"
        )


@dataclass(frozen=True)
class ChaveEvento:
    """Identidade do EVENTO financeiro — evidência, nunca constraint de banco.

    DERIVADA sob demanda por `chave_evento()`, jamais armazenada (IMP-06).
    """

    conta: str
    data: date
    valor_texto: str
    descricao_normalizada: str
    versao_regra: str = VERSAO_REGRA_NORMALIZACAO

    def texto(self) -> str:
        return (
            f"v{self.versao_regra}|{self.conta}|{self.data.isoformat()}"
            f"|{self.valor_texto}|{self.descricao_normalizada}"
        )


# --------------------------------------------------------------------------- #
# Eixos de estado (PRC-06, LIN-02, LIN-06)
# --------------------------------------------------------------------------- #


class Resultado(Enum):
    """Eixo do RESULTADO da conciliação — o que se concluiu sobre o item."""

    CASADO = "casado"
    CASADO_COM_DIVERGENCIA = "casado-com-divergencia"
    ORFAO_NO_EXTRATO = "orfao-no-extrato"
    ORFAO_NO_LIVRO = "orfao-no-livro"


class Situacao(Enum):
    """Eixo da SITUAÇÃO — a origem/fase da decisão, ortogonal ao resultado.

    `AUTOMATICA` indica origem da decisão (o sistema decidiu sozinho);
    `PENDENTE` e `RESOLVIDA` indicam fase do fluxo. A distinção está declarada
    aqui porque LIN-06 apontou que misturar os dois sentidos sem dizer qual é
    qual reproduz a não-ortogonalidade que este eixo veio corrigir.
    """

    AUTOMATICA = "automatica"
    PENDENTE = "pendente"
    RESOLVIDA = "resolvida"


class Estado5(Enum):
    """Os 5 estados terminais exatamente como escritos na Fase 0 (VAL-3).

    Não é um terceiro eixo: é a PROJEÇÃO declarada dos dois eixos acima, que
    devolve a VAL-3 a verificabilidade na forma em que o critério foi escrito.
    """

    CASADO = "casado"
    CASADO_COM_DIVERGENCIA = "casado-com-divergencia"
    ORFAO_NO_EXTRATO = "orfao-no-extrato"
    ORFAO_NO_LIVRO = "orfao-no-livro"
    PENDENTE_DE_REVISAO = "pendente-de-revisao"


def estado_val5(resultado: Resultado | None, situacao: Situacao) -> Estado5:
    """Projeção Resultado × Situacao -> Estado5 (VAL-3).

    Regra declarada em specs/technical/architecture.md, seção V(3):
    pendente-de-revisao quando a situação é PENDENTE; senão, o próprio resultado.
    """
    if situacao is Situacao.PENDENTE:
        return Estado5.PENDENTE_DE_REVISAO
    if resultado is None:
        raise ErroDominio(
            "I3: item não pendente precisa de um resultado para ter estado terminal"
        )
    return Estado5(resultado.value)


# --------------------------------------------------------------------------- #
# Entidades
# --------------------------------------------------------------------------- #


class Instrumento(Enum):
    """Instrumento de pagamento — define a janela de compensação aplicável.

    Valores e janelas em specs/technical/rubrica-score.md §2, com fonte citada.
    DESCONHECIDO cai no default conservador e é sinalizado no relatório, para o
    analista não confundir conservadorismo com resultado.
    """

    PIX = "pix"
    TED = "ted"
    BOLETO = "boleto"
    CARTAO = "cartao"
    DESCONHECIDO = "desconhecido"


@dataclass(frozen=True)
class RegistroBruto:
    """Saída dos adapters: dados da fonte, ainda sem interpretação de domínio."""

    fonte: str
    conta: str
    data: date
    valor_texto: str
    descricao_bruta: str
    arquivo: str
    linha: int
    fitid: str | None = None
    instrumento: Instrumento = Instrumento.DESCONHECIDO


@dataclass(frozen=True)
class Transacao:
    """Linha observada num extrato importado."""

    chave: ChaveNatural
    conta: str
    data: date
    valor: Dinheiro
    descricao_bruta: str
    fonte: str
    arquivo: str
    linha: int
    instrumento: Instrumento = Instrumento.DESCONHECIDO
    fitid: str | None = None

    def descricao_normalizada(self) -> str:
        return normalizar_descricao(self.descricao_bruta)


@dataclass(frozen=True)
class Lancamento:
    """Registro do livro interno de valores esperados (contas a pagar/receber).

    Termo distinto de Transacao por decisão de vocabulário: usar um pelo outro é
    proibido (specs/domain/glossario.md).
    """

    chave: ChaveNatural
    conta: str
    data: date
    valor: Dinheiro
    descricao_bruta: str
    fonte: str
    arquivo: str
    linha: int
    documento: str | None = None
    instrumento: Instrumento = Instrumento.DESCONHECIDO

    def descricao_normalizada(self) -> str:
        return normalizar_descricao(self.descricao_bruta)


def construir_transacoes(registros: Sequence[RegistroBruto]) -> list[Transacao]:
    """RegistroBruto -> Transacao, atribuindo o ORDINAL da ChaveNatural.

    O ordinal é a peça que faz a correção R4 funcionar: distingue duas linhas
    legitimamente idênticas (I6) e se reproduz igual numa reimportação de janela
    sobreposta (I8). É atribuído por ORDEM DE APARIÇÃO dentro do grupo
    (conta, data, valor, descrição bruta) — o mesmo arquivo, ou uma janela
    sobreposta com as mesmas linhas na mesma ordem, gera os mesmos ordinais.

    Registros com identificador nativo não usam ordinal: o FITID já é a chave.
    """
    contadores: dict[tuple, int] = {}
    saida: list[Transacao] = []
    for reg in sorted(registros, key=lambda r: r.linha):
        valor = Dinheiro(Decimal(reg.valor_texto))
        chave, ordinal = _chave_natural(reg, valor, contadores)
        saida.append(
            Transacao(
                chave=chave,
                conta=reg.conta,
                data=reg.data,
                valor=valor,
                descricao_bruta=reg.descricao_bruta,
                fonte=reg.fonte,
                arquivo=reg.arquivo,
                linha=reg.linha,
                instrumento=reg.instrumento,
                fitid=reg.fitid,
            )
        )
    return saida


def construir_lancamentos(
    registros: Sequence[RegistroBruto], documentos: dict[int, str] | None = None
) -> list[Lancamento]:
    """Idem para o livro interno. `documentos` mapeia linha -> nº do documento."""
    contadores: dict[tuple, int] = {}
    documentos = documentos or {}
    saida: list[Lancamento] = []
    for reg in sorted(registros, key=lambda r: r.linha):
        valor = Dinheiro(Decimal(reg.valor_texto))
        chave, _ = _chave_natural(reg, valor, contadores)
        saida.append(
            Lancamento(
                chave=chave,
                conta=reg.conta,
                data=reg.data,
                valor=valor,
                descricao_bruta=reg.descricao_bruta,
                fonte=reg.fonte,
                arquivo=reg.arquivo,
                linha=reg.linha,
                documento=documentos.get(reg.linha),
                instrumento=reg.instrumento,
            )
        )
    return saida


def _chave_natural(
    reg: RegistroBruto, valor: Dinheiro, contadores: dict[tuple, int]
) -> tuple[ChaveNatural, int]:
    if reg.fitid:
        return ChaveNatural(fonte=reg.fonte, conta=reg.conta, fitid=reg.fitid), 0
    grupo = (reg.fonte, reg.conta, reg.data, valor.texto(), reg.descricao_bruta)
    ordinal = contadores.get(grupo, 0)
    contadores[grupo] = ordinal + 1
    return (
        ChaveNatural(
            fonte=reg.fonte,
            conta=reg.conta,
            data=reg.data,
            valor_texto=valor.texto(),
            descricao_bruta=reg.descricao_bruta,
            ordinal=ordinal,
        ),
        ordinal,
    )


def chave_evento(item: Transacao | Lancamento) -> ChaveEvento:
    """Deriva a chave de evento sob demanda — nunca armazenada (IMP-06)."""
    return ChaveEvento(
        conta=item.conta,
        data=item.data,
        valor_texto=item.valor.texto(),
        descricao_normalizada=item.descricao_normalizada(),
    )


# --------------------------------------------------------------------------- #
# Casamento, pendências e resolução
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Casamento:
    """Par transação↔lançamento. I4: 1:1, garantido pelo reconcile-engine."""

    transacao: ChaveNatural
    lancamento: ChaveNatural
    resultado: Resultado
    situacao: Situacao
    score: int
    delta_valor: Decimal = Decimal("0")
    delta_dias: int = 0

    def estado(self) -> Estado5:
        return estado_val5(self.resultado, self.situacao)


class AcaoDedup(Enum):
    E_A_MESMA = "e-a-mesma"
    SAO_DISTINTAS = "sao-distintas"


class AcaoConciliacao(Enum):
    CASAR_COM = "casar-com"
    NAO_CASA = "nao-casa"


@dataclass(frozen=True)
class PendenciaDedup:
    """Pendência de deduplicação: fundir ou não duas observações (PRC-02)."""

    id: str
    esquerda: ChaveNatural
    candidatas: tuple[ChaveNatural, ...]
    scores: tuple[int, ...]
    motivo: str

    ACOES = (AcaoDedup.E_A_MESMA, AcaoDedup.SAO_DISTINTAS)


@dataclass(frozen=True)
class PendenciaConciliacao:
    """Pendência de conciliação: casar ou não transação com lançamento (PRC-02).

    Conjunto de ações distinto do de PendenciaDedup — a fusão dos dois num único
    contrato foi o defeito que esta separação corrige.
    """

    id: str
    transacao: ChaveNatural
    candidatos: tuple[ChaveNatural, ...]
    scores: tuple[int, ...]
    motivo: str

    ACOES = (AcaoConciliacao.CASAR_COM, AcaoConciliacao.NAO_CASA)


Pendencia = PendenciaDedup | PendenciaConciliacao


@dataclass(frozen=True)
class Resolucao:
    """Decisão humana. I7: soberana e nunca sobrescrita por heurística.

    Um desfazer não apaga: gera um novo registro apontando para o anterior
    (`desfaz`), preservando a trilha append-only (GOV-01, MIG-02).
    """

    id: str
    pendencia_id: str
    acao: AcaoDedup | AcaoConciliacao
    autor: str
    instante: str
    alvo: ChaveNatural | None = None
    motivo: str = ""
    desfaz: str | None = None


class Camada(Enum):
    """Camadas de precedência de identidade (specs/technical/parametros-matching.md).

    A cadeia (Chain of Responsibility) para no primeiro elo que decide.
    """

    L0_RESOLUCAO_HUMANA = "L0"
    L1_IDENTIDADE_NATIVA = "L1"
    L2_CHAVE_NATURAL = "L2"
    L3_SCORE_ALTO = "L3"
    L4_PENDENCIA = "L4"
    L5_DISTINTAS = "L5"


class Veredito(Enum):
    DUPLICATA = "duplicata"
    PENDENCIA = "pendencia"
    DISTINTA = "distinta"


@dataclass(frozen=True)
class DecisaoDedup:
    """Sempre carrega a camada que decidiu e a evidência.

    Sem isso não há como auditar um falso positivo — e VAL-2 exige zero deles.
    É persistida pelo audit-log (GOV-02), não vive só em memória.
    """

    chave: ChaveNatural
    veredito: Veredito
    camada: Camada
    evidencia: str
    contraparte: ChaveNatural | None = None
    score: int | None = None


@dataclass
class ResultadoConciliacao:
    casamentos: list[Casamento] = field(default_factory=list)
    orfaos_extrato: list[ChaveNatural] = field(default_factory=list)
    orfaos_livro: list[ChaveNatural] = field(default_factory=list)
    pendencias: list[PendenciaConciliacao] = field(default_factory=list)

    def total_classificados(self) -> int:
        return (
            len(self.casamentos) * 2
            + len(self.orfaos_extrato)
            + len(self.orfaos_livro)
            + len(self.pendencias)
        )
