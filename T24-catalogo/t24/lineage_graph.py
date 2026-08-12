"""M-03 lineage_graph — grafo dirigido de linhagem e suas travessias.

UNICO modulo do projeto que conhece NetworkX. Se a lib for trocada, so este arquivo muda.

Escolha Tier 1 (S6), registrada na Validacao Tecnologica da Fase 1: o criterio de acerto
do projeto mede igualdade EXATA de conjuntos incluindo o caso diamante (no alcancavel por
dois caminhos deve aparecer uma unica vez), e e precisamente onde uma travessia escrita a
mao erra. Alternativa Tier 2 documentada e nao escolhida: Kahn (1962) CACM 5(11):558-562
e DFS com back-edge (Tarjan 1976; CLRS 2a ed. 22.4) — ver specs/technical/graph-algorithms.md.

ADVERTENCIA da propria documentacao do NetworkX, que originou a assuncao A8:
"most of these functions are only guaranteed to work for DAGs [...] these functions do
not check for acyclic-ness, so it is up to the user to check for that."
Por isso a aciclicidade e verificada explicitamente por `validation` ANTES de qualquer
consulta, e nao presumida aqui.

A6: `downstream(X)` EXCLUI o proprio X — e a semantica de networkx.descendants. Fixada
por teste de caracterizacao (CA-20), requisito de saida da Fase 5 para este modulo.
"""

from __future__ import annotations

from typing import Iterable, Optional

import networkx as nx

from .model import DatasetId, LineageEdge


class LineageGraph:
    """Grafo dirigido cujos nos sao DatasetId e cujas arestas apontam no sentido do fluxo."""

    def __init__(self, grafo: nx.DiGraph) -> None:
        self._g = grafo

    @staticmethod
    def build(ids: Iterable[DatasetId], arestas: Iterable[LineageEdge]) -> "LineageGraph":
        """Monta o grafo.

        Recebe TODOS os ids declarados, e nao apenas os que aparecem em arestas: sem isso
        um dataset isolado nao existiria como no e `downstream` levantaria NodeNotFound em
        vez de devolver conjunto vazio — confundindo dataset isolado com inexistente
        (UX-02) e quebrando CA-13.
        """
        g = nx.DiGraph()
        g.add_nodes_from(ids)
        for aresta in arestas:
            g.add_edge(aresta.origem, aresta.destino)
        return LineageGraph(g)

    def tem(self, id_: DatasetId) -> bool:
        return self._g.has_node(id_)

    def downstream(self, id_: DatasetId) -> set[DatasetId]:
        """Todos os alcancaveis a partir de `id_`, sem incluir o proprio (A6)."""
        return set(nx.descendants(self._g, id_))

    def upstream(self, id_: DatasetId) -> set[DatasetId]:
        """Todos os que alcancam `id_`, sem incluir o proprio."""
        return set(nx.ancestors(self._g, id_))

    def is_acyclic(self) -> bool:
        return nx.is_directed_acyclic_graph(self._g)

    def find_cycle(self) -> Optional[list[DatasetId]]:
        """Devolve os datasets de UM ciclo, em ordem, ou None.

        Nomear o ciclo — e nao apenas detecta-lo — e requisito da Fase 0 (UC-3, CA-3).
        E tambem a razao pela qual Kahn (1962) sozinho nao bastaria: ele detecta QUE ha
        ciclo, pelas arestas remanescentes, mas nao QUAL e.
        """
        try:
            arestas = nx.find_cycle(self._g, orientation="original")
        except nx.NetworkXNoCycle:
            return None
        return [origem for origem, _destino, *_ in arestas]

    def arestas(self) -> tuple[LineageEdge, ...]:
        return tuple(LineageEdge(o, d) for o, d in self._g.edges())
