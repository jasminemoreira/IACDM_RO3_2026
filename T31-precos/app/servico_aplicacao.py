"""M-09 `servico-aplicacao` — Facade e fronteira única de validação.

É a ÚNICA superfície que `api-http`, `ui-web` e `ui-editor-regras` enxergam.
Sem isso os adapters duplicam orquestração e divergem — passando a responder
coisas diferentes para a mesma pergunta (ARQ-02).

Responsabilidades que a crítica atribuiu explicitamente a este módulo:
  * U1/ASS-01 — TODA validação de entrada acontece aqui; o núcleo declara
    pré-condições e assume entrada válida (Design by Contract).
  * V(4)/X1 + V(5)/Y1 — cache LRU de versões por NÚMERO. Versões publicadas
    são imutáveis (I-4), logo o cache não precisa de invalidação; precisa de
    EXPULSÃO, que a subtração de W1 havia levado junto (ASS-09). O teto é
    parâmetro OBSERVÁVEL, não constante de fé (A-22).
  * X2/CTL-04 — `versao_vigente_em(D)` resolve pelo MAIOR NÚMERO entre as
    versões com `vigente_desde <= D`; imune a ajuste de relógio.
  * W2/ARQ-05 — a prova de paridade mora aqui, não no importador.
  * A-15 — sem registro, não há preço: se o log falhar, a operação falha.
  * A-04 — o relógio entra por injeção (`agora`), nunca é lido pelo núcleo.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable

from .adaptadores.importador_csv import (
    ResultadoImportacao,
    exportar as _exportar_csv,
    importar as _importar_csv,
)
from .adaptadores.repositorio_sqlite import ErroDePersistencia, RepositorioSQLite
from .dominio import validador_coerencia as validador
from .dominio.explicador import explicar
from .dominio.modelo_dominio import (
    ConjuntoDeRegras,
    Decisao,
    EmpateInsoluvel,
    Origem,
    Precificacao,
    Regra,
    TipoOrigem,
    VersaoDeRegras,
    normalizar_sku,
)
from .dominio.motor_precificacao import precificar as _precificar

TETO_CACHE = 8  # A-22: parâmetro observável; critério de revisão em /saude


class EntradaInvalida(Exception):
    """Fronteira única (U1): entrada malformada nunca chega ao núcleo."""


class SemVersaoPublicada(Exception):
    """ASS-03: estado distinto de "nenhuma regra casou" (I-2)."""


class RascunhoConflitante(Exception):
    """PRO-02: importar por cima de edição manual exige confirmação."""


@dataclass(slots=True)
class RelatorioParidade:
    conferem: int = 0
    divergencias: list[dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.conferem + len(self.divergencias)


@dataclass(slots=True)
class _Cache:
    """LRU por NÚMERO de versão. Sem invalidação: I-4 garante a corretude."""

    teto: int = TETO_CACHE
    _itens: OrderedDict[int, VersaoDeRegras] = field(default_factory=OrderedDict)
    _conjuntos: dict[int, ConjuntoDeRegras] = field(default_factory=dict)
    acertos: int = 0
    erros: int = 0

    def obter(self, numero: int) -> VersaoDeRegras | None:
        v = self._itens.get(numero)
        if v is None:
            self.erros += 1
            return None
        self.acertos += 1
        self._itens.move_to_end(numero)
        return v

    def guardar(self, v: VersaoDeRegras) -> None:
        self._itens[v.numero] = v
        self._conjuntos[v.numero] = v.conjunto()  # Y4: índice na fronteira
        self._itens.move_to_end(v.numero)
        while len(self._itens) > self.teto:
            saiu, _ = self._itens.popitem(last=False)
            self._conjuntos.pop(saiu, None)

    def conjunto(self, numero: int) -> ConjuntoDeRegras:
        return self._conjuntos[numero]

    @property
    def taxa_acerto(self) -> float:
        total = self.acertos + self.erros
        return round(self.acertos / total, 3) if total else 0.0

    def estado(self) -> dict:
        return {
            "versoes_em_cache": sorted(self._itens),
            "teto": self.teto,
            "regras_em_cache": sum(len(v.regras) for v in self._itens.values()),
            "taxa_acerto": self.taxa_acerto,
        }


class ServicoAplicacao:
    def __init__(
        self,
        repo: RepositorioSQLite,
        agora: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repo = repo
        self._agora = agora  # A-04: relógio injetado, nunca lido pelo núcleo
        self._cache = _Cache()
        self._indice: list[tuple[date, int]] | None = None  # Y1: sob demanda

    # -- versões e cache -------------------------------------------------

    def _indice_vigencia(self) -> list[tuple[date, int]]:
        if self._indice is None:
            self._indice = self._repo.indice_vigencia()
        return self._indice

    def versao_vigente_em(self, quando: date) -> VersaoDeRegras:
        """X2/CTL-04: maior NÚMERO entre as versões com vigente_desde <= D."""
        candidatas = [n for d, n in self._indice_vigencia() if d <= quando]
        if not candidatas:
            raise SemVersaoPublicada(
                f"nenhuma versão de regras estava publicada em {quando:%d/%m/%Y}"
            )
        return self._versao(max(candidatas))

    def _versao(self, numero: int) -> VersaoDeRegras:
        v = self._cache.obter(numero)
        if v is None:
            v = self._repo.versao(numero)
            if v is None:
                raise SemVersaoPublicada(f"versão {numero} não existe")
            self._cache.guardar(v)
        return v

    def saude(self) -> dict:
        ultima = self._repo.ultima_versao()
        return {"versao_vigente": ultima, "cache": self._cache.estado()}

    # -- precificação ----------------------------------------------------

    def precificar(
        self, sku: str, quantidade: int, quando: date, solicitante: str
    ) -> tuple[Decisao, str]:
        produto, conjunto, numero = self._preparar(sku, quantidade, quando)
        try:
            p = _precificar(conjunto, produto, quantidade, quando)
        except EmpateInsoluvel as e:
            raise EntradaInvalida(
                f"a versão vigente está incoerente e não deveria ter sido publicada: {e}"
            ) from e

        agora = self._agora()
        d = Decisao(
            id=uuid.uuid4().hex[:12],
            sku=produto.sku,
            quantidade=quantidade,
            data_pedido=quando,
            versao_regras=numero,
            preco_unitario=p.preco_unitario,
            total=p.total,
            trace=p.trace,
            solicitante=solicitante or "não informado",
            registrada_em=agora,
        )
        # A-15: sem registro, sem preço. Se o log falhar, a operação falha —
        # um preço não auditável é o que a planilha já dava.
        self._repo.registrar(d)
        return d, explicar(p, produto.sku)

    def recalcular(self, decisao_id: str) -> tuple[Decisao, Precificacao]:
        """I-7: o registrado prova o que o motor RESPONDEU; o recálculo mostra
        o que as regras vigentes hoje dizem sobre aquela data. Coisas distintas.
        """
        d = self._repo.obter(decisao_id)
        if d is None:
            raise EntradaInvalida(f"decisão {decisao_id} não encontrada")
        produto, conjunto, _ = self._preparar(d.sku, d.quantidade, d.data_pedido)
        return d, _precificar(conjunto, produto, d.quantidade, d.data_pedido)

    def _preparar(self, sku: str, quantidade: int, quando: date):
        """Fronteira única de validação (U1). Nada malformado passa daqui."""
        if not isinstance(quantidade, int) or quantidade < 1:
            raise EntradaInvalida(f"quantidade deve ser inteiro >= 1, recebido {quantidade!r}")
        if quando is None:
            raise EntradaInvalida("a data do pedido é obrigatória (A-04)")
        chave = normalizar_sku(sku)
        if not chave:
            raise EntradaInvalida("SKU é obrigatório")
        catalogo = self._repo.produtos()
        if not catalogo:
            # Dizer "SKU desconhecido" com catálogo vazio é verdadeiro e
            # inútil — mesma família do defeito que prendeu o operador no
            # teste manual. Aqui o estado real é "nada foi importado ainda".
            raise SemVersaoPublicada(
                "nenhum produto cadastrado — importe a planilha antes de precificar"
            )
        produto = catalogo.get(chave)
        if produto is None:
            raise EntradaInvalida(f"SKU desconhecido no catálogo: {chave}")
        versao = self.versao_vigente_em(quando)
        return produto, self._cache.conjunto(versao.numero), versao.numero

    def historico(self, sku: str | None = None, limite: int = 100) -> list[Decisao]:
        return self._repo.listar(normalizar_sku(sku) if sku else None, limite)

    # -- rascunho, importação e publicação -------------------------------

    def rascunho_atual(self) -> list[Regra]:
        return self._repo.rascunho_atual()

    def salvar_rascunho(self, regras: list[Regra]) -> None:
        self._repo.salvar_rascunho(regras)

    def validar_rascunho(self) -> validador.Relatorio:
        """A evidência de conflito vem do REPOSITÓRIO, não da memória.

        Ela vivia em `self._conflitos` e sumia no restart — a trava era
        volátil enquanto o dado travado era durável, o que derrotava V-04 em
        silêncio. Tudo que bloqueia uma publicação tem de ter o mesmo tempo de
        vida do rascunho que bloqueia.
        """
        regras = self._repo.rascunho_atual()
        return validador.validar(
            regras, self._repo.produtos(), self._repo.conflitos_base()
        )

    def importar(
        self, conteudo: bytes, substituir: bool = False
    ) -> tuple[ResultadoImportacao, validador.Relatorio, RelatorioParidade]:
        """PRO-02/MIG-03: importar sobre rascunho editado exige `substituir`."""
        if self._repo.rascunho_atual() and not substituir:
            raise RascunhoConflitante(
                "já existe um rascunho em edição. Importar vai substituí-lo — "
                "confirme para prosseguir."
            )
        res = _importar_csv(conteudo, self._agora().date())
        self._repo.salvar_produtos(res.produtos)
        self._repo.salvar_rascunho(res.rascunho)
        self._repo.salvar_conflitos_base(res.conflitos_base)
        rel = validador.validar(res.rascunho, self._repo.produtos(), res.conflitos_base)
        par = self.verificar_paridade(res)
        return res, rel, par

    def verificar_paridade(self, res: ResultadoImportacao) -> RelatorioParidade:
        """CS-1 — roda sobre o RASCUNHO (W2/U6), antes de publicar.

        Compara a resposta do motor com o valor ORIGINAL da planilha, nunca
        com outra saída do motor.
        """
        produtos = {p.sku: p for p in res.produtos}
        conjunto = ConjuntoDeRegras(res.rascunho)
        hoje = self._agora().date()
        rel = RelatorioParidade()
        for linha, sku, qtd, esperado in res.paridade_esperada:
            produto = produtos.get(sku)
            if produto is None:
                continue
            try:
                obtido = _precificar(conjunto, produto, qtd, hoje).preco_unitario.iso()
            except EmpateInsoluvel as e:
                rel.divergencias.append(
                    {"linha": linha, "sku": sku, "quantidade": qtd, "erro": str(e)}
                )
                continue
            if obtido == esperado:
                rel.conferem += 1
            else:
                rel.divergencias.append(
                    {
                        "linha": linha,
                        "sku": sku,
                        "quantidade": qtd,
                        "esperado": esperado,
                        "obtido": obtido,
                    }
                )
        return rel

    def publicar(self, autor: str, justificativa: str) -> VersaoDeRegras:
        rel = self.validar_rascunho()
        if rel.bloqueia_publicacao:
            raise EntradaInvalida(
                "publicação bloqueada pelo validador: "
                + "; ".join(e.descricao for e in rel.erros)
            )
        return self._publicar(
            self._repo.rascunho_atual(),
            autor,
            Origem(tipo=TipoOrigem.EDICAO, justificativa=justificativa),
        )

    def republicar(self, numero: int, autor: str, justificativa: str) -> VersaoDeRegras:
        """PRO-03: reverter sem violar I-4 — publica NOVA versão com o conteúdo
        da versão N. V(5)/Y7: NÃO toca o rascunho em edição (PRO-05).
        """
        alvo = self._versao(numero)
        return self._publicar(
            list(alvo.regras),
            autor,
            Origem(
                tipo=TipoOrigem.REVERSAO,
                justificativa=justificativa,
                revertida_de=numero,
            ),
            tocar_rascunho=False,
        )

    def _publicar(
        self,
        regras: list[Regra],
        autor: str,
        origem: Origem,
        tocar_rascunho: bool = True,
    ) -> VersaoDeRegras:
        if not (autor or "").strip():
            raise EntradaInvalida("informe o autor da publicação (A-14)")
        try:
            v = self._repo.publicar(regras, autor.strip(), origem, self._agora())
        except ErroDePersistencia:
            raise
        # Y10/RES-07: o índice em memória só é apendado APÓS o commit.
        if self._indice is not None:
            self._indice.append((v.vigente_desde, v.numero))
        self._cache.guardar(v)
        if tocar_rascunho:
            # PRO-01: o rascunho vira cópia da versão publicada — sem estado órfão.
            self._repo.salvar_rascunho(list(v.regras))
        return v

    def exportar(self) -> bytes:
        """MIG-01: caminho de rollback, aprovado pelo operador na Fase 3."""
        return _exportar_csv(self._repo.rascunho_atual(), self._repo.produtos())
