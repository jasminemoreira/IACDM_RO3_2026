"""CA-20 — testes de caracterizacao do NetworkX. Requisito de SAIDA da Fase 5.

Origem: achado SCI-02 (Iteracao 1) e ASM-06 (Iteracao 2).

A assuncao A6 — "impact(X) exclui o proprio X" — repousa inteiramente na semantica de
`networkx.descendants`, lida da documentacao oficial. Sem estes testes, uma mudanca de
comportamento da biblioteca alteraria o criterio de acerto do projeto EM SILENCIO: o
conjunto passaria a conter um elemento a mais e nada acusaria.

Estes testes nao verificam o nosso codigo. Verificam a premissa sobre a qual ele foi
construido — que e uma coisa diferente, e a razao de estarem num arquivo separado.
"""

from __future__ import annotations

import networkx as nx
import pytest


@pytest.fixture
def diamante() -> nx.DiGraph:
    """a -> b -> d  e  a -> c -> d. O no `d` e alcancavel por dois caminhos."""
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "d"), ("a", "c"), ("c", "d")])
    return g


def test_descendants_exclui_a_origem(diamante: nx.DiGraph) -> None:
    """A6 depende disto. Se `descendants` passasse a incluir a origem, o criterio de
    acerto do projeto mudaria de 6 para 7 afetados sem nenhum aviso."""
    assert nx.descendants(diamante, "a") == {"b", "c", "d"}
    assert "a" not in nx.descendants(diamante, "a")


def test_descendants_nao_duplica_no_alcancavel_por_dois_caminhos(
    diamante: nx.DiGraph,
) -> None:
    """O caso diamante e o coracao do criterio de acerto: `d` uma vez, nao duas."""
    resultado = nx.descendants(diamante, "a")
    assert isinstance(resultado, set)
    assert len([x for x in resultado if x == "d"]) == 1


def test_descendants_de_folha_e_vazio(diamante: nx.DiGraph) -> None:
    """CA-13 depende disto: folha devolve conjunto vazio, nao erro."""
    assert nx.descendants(diamante, "d") == set()


def test_descendants_levanta_para_no_inexistente(diamante: nx.DiGraph) -> None:
    """Justifica por que `lineage_graph.build` recebe TODOS os ids como nos: sem isso,
    um dataset isolado cairia aqui em vez de devolver conjunto vazio."""
    with pytest.raises(nx.NetworkXError):
        nx.descendants(diamante, "no_que_nao_existe")


def test_no_isolado_tem_descendants_vazio() -> None:
    """Contrapartida do teste acima: adicionado como no, o isolado responde vazio."""
    g = nx.DiGraph()
    g.add_node("isolado")
    assert nx.descendants(g, "isolado") == set()
    assert nx.ancestors(g, "isolado") == set()


def test_ancestors_exclui_o_proprio(diamante: nx.DiGraph) -> None:
    assert nx.ancestors(diamante, "d") == {"a", "b", "c"}
    assert "d" not in nx.ancestors(diamante, "d")


def test_find_cycle_levanta_quando_nao_ha_ciclo(diamante: nx.DiGraph) -> None:
    """A deteccao de ciclo depende desta excecao especifica, nao de retorno vazio."""
    with pytest.raises(nx.NetworkXNoCycle):
        nx.find_cycle(diamante, orientation="original")


def test_find_cycle_nomeia_as_arestas_do_ciclo() -> None:
    """UC-3/CA-3 exigem NOMEAR o ciclo, nao apenas detecta-lo. E a razao pela qual Kahn
    (1962) sozinho nao bastaria: ele detecta QUE ha ciclo, mas nao QUAL e."""
    g = nx.DiGraph()
    g.add_edges_from([("x", "y"), ("y", "x")])
    arestas = nx.find_cycle(g, orientation="original")
    nos = {origem for origem, _destino, *_ in arestas}
    assert nos == {"x", "y"}


def test_is_directed_acyclic_graph_concorda_com_find_cycle(diamante: nx.DiGraph) -> None:
    assert nx.is_directed_acyclic_graph(diamante) is True
    ciclico = nx.DiGraph()
    ciclico.add_edges_from([("x", "y"), ("y", "x")])
    assert nx.is_directed_acyclic_graph(ciclico) is False
