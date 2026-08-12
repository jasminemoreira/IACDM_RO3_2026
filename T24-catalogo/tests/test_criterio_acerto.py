"""CA-0 — o criterio de acerto do projeto.

Escrito contra specs/datasets/ground-truth.md, que foi redigido na Fase 4 ANTES do codigo.
Os conjuntos abaixo sao transcritos do oraculo, nao extraidos da implementacao.

A asserção e de IGUALDADE DE CONJUNTOS, nao de continencia: falso negativo (afetado
omitido) e falso positivo (nao-afetado incluido) reprovam igualmente.
"""

from __future__ import annotations

from t24.model import DatasetId

# --------------------------------------------------------- transcrito do ground truth
AFETADOS_ESPERADOS = {
    "vendas.itens_pedido",
    "logistica.envios",
    "logistica.rastreio",
    "financeiro.receita",
    "financeiro.conciliacao",
    "financeiro.previsao",
}
RESPONSAVEIS_ESPERADOS = {"Maria Silva", "Ana Costa", "Joao Souza", "Carlos Lima"}


def test_afetados_exatos(servico):
    """CA-0: igualdade de conjunto com os 6 afetados do oraculo."""
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    assert {str(d) for d in resultado.afetados} == AFETADOS_ESPERADOS


def test_responsaveis_exatos(servico):
    """CA-0: igualdade de conjunto com os 4 responsaveis do oraculo."""
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    assert {dono.nome for dono in resultado.donos} == RESPONSAVEIS_ESPERADOS


def test_diamante_aparece_uma_vez(servico):
    """CA-0(a): `financeiro.conciliacao` e alcancavel por DOIS caminhos independentes
    (via itens_pedido->receita e via envios) e precisa aparecer UMA vez."""
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    ocorrencias = [d for d in resultado.afetados if str(d) == "financeiro.conciliacao"]
    assert len(ocorrencias) == 1

    # E uma vez tambem no agrupamento por dono, nao repetido entre donos.
    todos_agrupados = [str(d) for _dono, ds in resultado.responsaveis for d in ds]
    assert todos_agrupados.count("financeiro.conciliacao") == 1
    assert len(todos_agrupados) == len(resultado.afetados)


def test_dono_sobrescrito_prevalece(servico):
    """CA-0(b): `financeiro.previsao` sobrescreve o dono do dominio.

    Responde Carlos Lima, e NAO Joao Souza — que e o dono do dominio financeiro.
    """
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    dono_da_previsao = {
        dono.nome
        for dono, datasets in resultado.responsaveis
        if any(str(d) == "financeiro.previsao" for d in datasets)
    }
    assert dono_da_previsao == {"Carlos Lima"}


def test_impacto_exclui_o_proprio(servico):
    """A6: o dataset consultado nunca aparece entre os afetados.

    Teste NEGATIVO: se a semantica de descendants mudasse, o conjunto passaria de 6 para
    7 elementos e CA-0 falharia por um elemento.
    """
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    assert DatasetId.parse("vendas.pedidos") not in resultado.afetados


def test_donos_deduplicados(servico):
    """CA-16: Ana Costa possui 2 datasets afetados e Joao Souza tambem, mas cada um
    aparece UMA vez na lista de responsaveis."""
    resultado = servico.impact(DatasetId.parse("vendas.pedidos"))
    nomes = [dono.nome for dono, _ in resultado.responsaveis]
    assert len(nomes) == len(set(nomes)) == 4
    por_nome = {dono.nome: datasets for dono, datasets in resultado.responsaveis}
    assert len(por_nome["Ana Costa"]) == 2
    assert len(por_nome["Joao Souza"]) == 2
