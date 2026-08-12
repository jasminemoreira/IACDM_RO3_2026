"""Regressão do QUARTO defeito — o bloqueio imortal.

Encontrado pelo operador no teste manual da Fase 6, após onze tentativas de
publicar sem saída possível. É iatrogênico: nasceu do conserto do defeito 2
(trava volátil), que persistiu a evidência do conflito e, sem querer, a tornou
eterna. Um fato histórico sobre o arquivo importado estava sendo aplicado como
restrição sobre o estado atual do rascunho.

Os dois testes abaixo prendem as DUAS pontas: a trava tem de sobreviver ao
restart (defeito 2) E tem de ceder quando deixa de ter consequência (defeito 4).
Consertar um sem o outro reintroduz o oposto.
"""

from __future__ import annotations

import pytest

from app.adaptadores.repositorio_sqlite import RepositorioSQLite
from app.servico_aplicacao import EntradaInvalida, ServicoAplicacao
from conftest import AGORA, csv_bruto


@pytest.fixture
def servico_com_conflito(tmp_path):
    s = ServicoAplicacao(RepositorioSQLite(tmp_path / "c.db"), agora=lambda: AGORA)
    s.importar(csv_bruto(), substituir=True)
    return s


def test_conflito_bloqueia_enquanto_o_sku_tem_regras(servico_com_conflito):
    """A trava existe — e continua existindo enquanto for relevante."""
    rel = servico_com_conflito.validar_rascunho()
    assert any(e.tipo == "preco_base_inconsistente" for e in rel.erros)
    assert rel.bloqueia_publicacao


def test_conflito_cede_quando_o_sku_sai_do_rascunho(servico_com_conflito):
    """O DEFEITO: excluir todas as regras do SKU não destravava — nunca.

    Foi exatamente o que o operador fez, e o bloqueio permaneceu. Aqui a
    remoção é a mesma que ele executou pela grade.
    """
    sem_1007 = [r for r in servico_com_conflito.rascunho_atual() if r.escopo != "SKU-1007"]
    servico_com_conflito.salvar_rascunho(sem_1007)
    rel = servico_com_conflito.validar_rascunho()
    assert not any(e.tipo == "preco_base_inconsistente" for e in rel.erros), (
        "sem regras para o SKU, o conflito de preço base não tem consequência"
    )


def test_publicacao_completa_apos_o_analista_corrigir_pela_grade(servico_com_conflito):
    """UC-3 ponta a ponta pela via que o operador tentou onze vezes.

    Remove a colisão (linha 'promo fevereiro') e as regras do SKU em conflito
    — as duas ações disponíveis na grade — e publica.
    """
    limpo = [
        r
        for r in servico_com_conflito.rascunho_atual()
        if r.escopo != "SKU-1007"
        and not (r.escopo == "SKU-1003" and r.faixa.minimo == 15)
    ]
    servico_com_conflito.salvar_rascunho(limpo)
    v = servico_com_conflito.publicar("Operadora", "correção pela grade")
    assert v.numero == 1
    d, _ = servico_com_conflito.precificar("SKU-1003", 50, AGORA.date(), "teste")
    assert d.preco_unitario.iso() == "21.90"  # §E P-01


def test_mensagem_diz_o_que_nao_resolve(servico_com_conflito):
    """A mensagem tinha de avisar que excluir regras não resolve."""
    erro = next(
        e for e in servico_com_conflito.validar_rascunho().erros
        if e.tipo == "preco_base_inconsistente"
    )
    assert "Excluir regras NÃO resolve" in erro.descricao
    assert "reimporte" in erro.descricao
