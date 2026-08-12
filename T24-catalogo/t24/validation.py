"""M-04 validation — invariantes, violacoes e CERTIFICACAO.

Dona de `Violation`, `CatalogInvalid` e `LoadedCatalog`. Quem valida e quem certifica:
`certify` e a UNICA funcao do sistema que produz um LoadedCatalog.

IMPL-06 — a garantia central do desenho. Nao e "so este modulo pode construir" (Python
nao tem construtor privado, e isso seria convencao, nao garantia). E: `LoadedCatalog`
EXIGE a lista de violacoes no construtor e RECUSA construir se ela nao estiver vazia.
Deixa de importar quem chama — um catalogo invalido e inconstruivel para qualquer um.

A8 deixa de ser assuncao documentada e vira propriedade do sistema de tipos: nao existe
LoadedCatalog que nao tenha passado pela validacao.

A9 — as violacoes sao AGREGADAS: todas de uma vez, nunca uma por execucao.
IMPL-01 / IMPL-08 — a ordem e deterministica: violacoes SEM dominio primeiro (erro de
parse de arquivo que sequer chegou a ter o campo lido), por nome de arquivo; depois as
com dominio, em ordem lexicografica de dominio e, dentro dele, ordem de declaracao.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .catalog import Catalog
from .lineage_graph import LineageGraph
from .model import DatasetId, LineageEdge, Owner


@dataclass(frozen=True)
class Violation:
    """Um defeito concreto na declaracao.

    RES-04: `arquivo` e obrigatorio — sempre sabemos de qual arquivo veio o problema.
    `linha` e opcional: um arquivo ilegivel por permissao nao tem linha a apontar.
    """

    arquivo: str
    mensagem: str
    dominio: Optional[str] = None
    linha: Optional[int] = None

    def __str__(self) -> str:
        local = self.arquivo if self.linha is None else f"{self.arquivo}:{self.linha}"
        return f"{local}: {self.mensagem}"


class CatalogInvalid(Exception):
    """Levantada quando o catalogo declarado viola alguma invariante."""

    def __init__(self, violacoes: Sequence[Violation]) -> None:
        self.violacoes: tuple[Violation, ...] = tuple(violacoes)
        super().__init__(f"catalogo invalido: {len(self.violacoes)} violacao(oes)")


def ordenar(violacoes: Iterable[Violation]) -> tuple[Violation, ...]:
    """Ordem deterministica (IMPL-01, IMPL-08).

    `sorted` e estavel, entao a ordem de declaracao original e preservada dentro de cada
    grupo — que e exatamente o desempate especificado.
    """
    return tuple(
        sorted(
            violacoes,
            key=lambda v: (v.dominio is not None, v.dominio or v.arquivo),
        )
    )


class LoadedCatalog:
    """Catalogo validado. Inconstruivel enquanto houver qualquer violacao (IMPL-06)."""

    def __init__(
        self,
        catalogo: Catalog,
        grafo: LineageGraph,
        violacoes: Sequence[Violation],
    ) -> None:
        if violacoes:
            raise CatalogInvalid(ordenar(violacoes))
        self._catalogo = catalogo
        self._grafo = grafo

    @property
    def catalogo(self) -> Catalog:
        return self._catalogo

    @property
    def grafo(self) -> LineageGraph:
        return self._grafo


# --------------------------------------------------------------------------- invariantes


def _inv5_arestas_referenciam_declarados(
    catalogo: Catalog, arestas: Sequence[LineageEdge], arquivo_por_dominio: dict[str, str]
) -> list[Violation]:
    """INV-5: os dois extremos de toda aresta precisam estar declarados.

    Um afetado nao declarado nao tem dono resolvivel, e a analise de impacto devolveria
    resposta silenciosamente incompleta — pior que erro explicito (decisao da Fase 0,
    mantida pelo operador na arbitragem de PROC-02).
    """
    achados: list[Violation] = []
    for aresta in arestas:
        for ponta in (aresta.origem, aresta.destino):
            if not catalogo.has(ponta):
                consumidor = aresta.destino
                achados.append(
                    Violation(
                        arquivo=arquivo_por_dominio.get(consumidor.dominio, "?"),
                        dominio=consumidor.dominio,
                        mensagem=(
                            f"'{consumidor}' declara ser alimentado por '{ponta}', "
                            f"que nao esta declarado em nenhum dominio do catalogo"
                        ),
                    )
                )
    return achados


def _inv4_aciclico(
    grafo: LineageGraph, arquivo_por_dominio: dict[str, str]
) -> list[Violation]:
    """INV-4: DAG estrito. O ciclo precisa ser NOMEADO, nao apenas detectado (CA-3)."""
    ciclo = grafo.find_cycle()
    if ciclo is None:
        return []
    caminho = " -> ".join(str(no) for no in ciclo) + f" -> {ciclo[0]}"
    primeiro = ciclo[0]
    return [
        Violation(
            arquivo=arquivo_por_dominio.get(primeiro.dominio, "?"),
            dominio=primeiro.dominio,
            mensagem=f"ciclo na linhagem: {caminho}",
        )
    ]


def _gov04_contato_ambiguo(
    catalogo: Catalog, arquivo_por_dominio: dict[str, str]
) -> list[Violation]:
    """GOV-04: dois NOMES distintos com o MESMO contato.

    A identidade de Owner e o contato normalizado (GOV-03), o que faz a mesma pessoa
    grafada de dois modos contar como uma so. O reverso — duas pessoas dividindo caixa —
    colapsaria em silencio. Aqui o conflito e recusado e a desambiguacao, exigida.
    """
    nomes_por_contato: dict[str, dict[str, str]] = {}

    def registrar(dono: Owner, dominio: str) -> None:
        nomes_por_contato.setdefault(dono.chave, {}).setdefault(dono.nome.strip(), dominio)

    for dominio in catalogo.domains():
        registrar(dominio.dono, dominio.nome)
        for ds in dominio.datasets:
            if ds.dono is not None:
                registrar(ds.dono, dominio.nome)

    achados: list[Violation] = []
    for contato, nomes in sorted(nomes_por_contato.items()):
        if len(nomes) > 1:
            listados = ", ".join(f"'{n}'" for n in sorted(nomes))
            dominio = sorted(nomes.values())[0]
            achados.append(
                Violation(
                    arquivo=arquivo_por_dominio.get(dominio, "?"),
                    dominio=dominio,
                    mensagem=(
                        f"o contato '{contato}' esta declarado com nomes diferentes "
                        f"({listados}); use um contato por pessoa ou unifique o nome — "
                        f"sem isso duas pessoas seriam tratadas como um unico dono"
                    ),
                )
            )
    return achados


def validate(
    catalogo: Catalog,
    grafo: LineageGraph,
    arestas: Sequence[LineageEdge],
    arquivo_por_dominio: dict[str, str],
) -> list[Violation]:
    """Aplica as invariantes que dependem do catalogo COMPLETO.

    INV-1 (unicidade de dominio e de dataset) e INV-2 (dominio tem dono) sao verificadas
    em catalog_mapper, onde os duplicados e os campos ausentes ainda sao visiveis.
    INV-3 (nenhum orfao) e INV-6 (dependencia entre dominios nunca declarada) valem por
    construcao: todo dataset pertence a um dominio com dono, e o formato nao oferece
    nenhuma forma de declarar aresta entre dominios.
    """
    achados: list[Violation] = []
    achados += _inv5_arestas_referenciam_declarados(catalogo, arestas, arquivo_por_dominio)
    achados += _gov04_contato_ambiguo(catalogo, arquivo_por_dominio)
    # A aciclicidade so faz sentido se todas as pontas existem; um ciclo apontando para
    # dataset inexistente ja foi reportado como INV-5.
    if not achados:
        achados += _inv4_aciclico(grafo, arquivo_por_dominio)
    return achados


def certify(
    catalogo: Catalog,
    grafo: LineageGraph,
    arestas: Sequence[LineageEdge],
    arquivo_por_dominio: dict[str, str],
    violacoes_anteriores: Sequence[Violation] = (),
) -> LoadedCatalog:
    """Unica funcao do sistema que produz um LoadedCatalog.

    IMPL-07: nao devolve uniao. Ou devolve o catalogo certificado, ou levanta
    CatalogInvalid com TODAS as violacoes agregadas (A9).
    """
    todas = list(violacoes_anteriores) + validate(
        catalogo, grafo, arestas, arquivo_por_dominio
    )
    return LoadedCatalog(catalogo, grafo, todas)


def ids_declarados(catalogo: Catalog) -> tuple[DatasetId, ...]:
    return catalogo.ids()
