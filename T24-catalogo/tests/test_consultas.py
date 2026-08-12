"""CA-1, CA-2, CA-5, CA-6, CA-13, CA-14 — consultas e bordas.

Todos os conjuntos esperados vem de specs/datasets/ground-truth.md.
"""

from __future__ import annotations

import pytest

from t24.model import DatasetId
from t24.query_service import DatasetNotFound


def test_catalogo_carrega_com_contagens(carregado):
    """CA-1: 4 dominios, 8 datasets, 7 arestas — contagem exata do oraculo."""
    assert len(carregado.catalogo.domains()) == 4
    assert len(carregado.catalogo.ids()) == 8
    assert len(carregado.grafo.arestas()) == 7


# ------------------------------------------------------------------- impacto (CA-2)


def test_impacto_receita(servico):
    resultado = servico.impact(DatasetId.parse("financeiro.receita"))
    assert {str(d) for d in resultado.afetados} == {
        "financeiro.conciliacao",
        "financeiro.previsao",
    }
    assert {d.nome for d in resultado.donos} == {"Joao Souza", "Carlos Lima"}


def test_impacto_envios(servico):
    resultado = servico.impact(DatasetId.parse("logistica.envios"))
    assert {str(d) for d in resultado.afetados} == {
        "logistica.rastreio",
        "financeiro.conciliacao",
    }
    assert {d.nome for d in resultado.donos} == {"Ana Costa", "Joao Souza"}


# --------------------------------------------------------------------- bordas (CA-13)


def test_impacto_de_folha_vazio(servico):
    """`logistica.rastreio` e folha: conjunto vazio, NAO erro."""
    resultado = servico.impact(DatasetId.parse("logistica.rastreio"))
    assert resultado.afetados == frozenset()
    assert resultado.vazio is True


def test_impacto_de_isolado_vazio(servico):
    """`marketing.campanhas` nao tem nenhuma aresta.

    So passa porque lineage_graph.build recebe TODOS os ids como nos; se o grafo fosse
    montado apenas das arestas, este dataset nem existiria e networkx levantaria.
    """
    resultado = servico.impact(DatasetId.parse("marketing.campanhas"))
    assert resultado.afetados == frozenset()


def test_impacto_de_conciliacao_vazio(servico):
    """`financeiro.conciliacao` e folha apesar de receber duas arestas."""
    resultado = servico.impact(DatasetId.parse("financeiro.conciliacao"))
    assert resultado.afetados == frozenset()


def test_impacto_de_inexistente_levanta(servico):
    """CA-14: inexistente e situacao DISTINTA de conjunto vazio (UX-02).

    Confundir as duas faria o engenheiro concluir que a mudanca e segura.
    """
    with pytest.raises(DatasetNotFound):
        servico.impact(DatasetId.parse("vendas.inexistente"))


# ---------------------------------------------------------------- procedencia (CA-6)


def test_procedencia_conciliacao(servico):
    resultado = servico.provenance(DatasetId.parse("financeiro.conciliacao"))
    assert {str(o) for o in resultado.origens} == {
        "financeiro.receita",
        "vendas.itens_pedido",
        "vendas.pedidos",
        "logistica.envios",
    }
    assert resultado.dominios == frozenset({"financeiro", "vendas", "logistica"})


def test_procedencia_previsao(servico):
    resultado = servico.provenance(DatasetId.parse("financeiro.previsao"))
    assert {str(o) for o in resultado.origens} == {
        "financeiro.receita",
        "vendas.itens_pedido",
        "vendas.pedidos",
    }


def test_procedencia_rastreio(servico):
    resultado = servico.provenance(DatasetId.parse("logistica.rastreio"))
    assert {str(o) for o in resultado.origens} == {"logistica.envios", "vendas.pedidos"}
    assert resultado.dominios == frozenset({"logistica", "vendas"})


def test_procedencia_de_isolado_vazia(servico):
    resultado = servico.provenance(DatasetId.parse("marketing.campanhas"))
    assert resultado.origens == frozenset()


def test_procedencia_de_origem_vazia(servico):
    """`vendas.pedidos` nao e alimentado por ninguem."""
    resultado = servico.provenance(DatasetId.parse("vendas.pedidos"))
    assert resultado.origens == frozenset()
    assert resultado.vazio is True


def test_procedencia_de_inexistente_levanta(servico):
    with pytest.raises(DatasetNotFound):
        servico.provenance(DatasetId.parse("vendas.inexistente"))


# ------------------------------------------------------------- resolucao de dono (CA-5)


def test_dono_herdado_do_dominio(carregado):
    dono = carregado.catalogo.effective_owner(DatasetId.parse("financeiro.receita"))
    assert dono.nome == "Joao Souza"


def test_dono_sobrescrito_no_dataset(carregado):
    dono = carregado.catalogo.effective_owner(DatasetId.parse("financeiro.previsao"))
    assert dono.nome == "Carlos Lima"
    assert dono.contato == "carlos.lima@empresa.com"
