"""M-08 e M-05 — CS-1 (paridade) e CS-3 (validador pega as armadilhas).

Origem dos valores: `specs/datasets/casos-armadilha.md` §A, §B, §C, §C-bis, §D.
"""

from datetime import date

import pytest

from app.adaptadores.importador_csv import ErroDeImportacao, exportar, importar
from app.dominio import validador_coerencia as validador
from app.dominio.modelo_dominio import ConjuntoDeRegras, ESCOPO_GERAL
from app.dominio.motor_precificacao import precificar
from conftest import HOJE, PARIDADE_A, csv_bruto, csv_corrigido


@pytest.fixture
def resultado():
    return importar(csv_bruto(), HOJE)


# --------------------------------------------------------------------------
# CS-3 — rejeições (§C). Esperado: 6 na primeira importação, cada uma com
# linha e motivo nomeados. R-06 saiu daqui e virou §C-bis (reimportação).
# --------------------------------------------------------------------------

REJEICOES_C = [
    (9, "faixa invertida"),        # R-01
    (19, "preço ausente"),         # R-02
    (20, "preço negativo"),        # R-03
    (24, "não-monetário"),         # R-04
    (30, "duplicada"),             # R-07
    (35, "'De' não numérico"),     # R-05
]


def test_cs3_seis_rejeicoes_nomeadas(resultado):
    assert len(resultado.rejeitadas) == 6, [r.motivo for r in resultado.rejeitadas]


@pytest.mark.parametrize("linha,trecho", REJEICOES_C)
def test_cs3_cada_rejeicao_por_linha_e_motivo(resultado, linha, trecho):
    achada = [r for r in resultado.rejeitadas if r.linha == linha]
    assert achada, f"linha {linha} deveria ter sido rejeitada"
    assert trecho in achada[0].motivo


def test_cs3_relatorio_nomeia_linha_nao_so_conta(resultado):
    """CS-3: '7 linhas rejeitadas' sem discriminação NÃO atende o critério."""
    assert all(r.linha > 0 and r.motivo for r in resultado.rejeitadas)


# --------------------------------------------------------------------------
# CS-3 — coerência (§D). Esperado: V-01 colisão, V-03 lacuna, V-04 preço base.
# --------------------------------------------------------------------------


def test_v01_colisao_bloqueia_com_intervalo(resultado):
    """V-01: SKU-1003 5–19, 20–99 e 15–60 → colide em 15–19 e em 20–60."""
    rel = validador.validar(
        resultado.rascunho,
        {p.sku: p for p in resultado.produtos},
        resultado.conflitos_base,
    )
    colisoes = [e for e in rel.erros if e.tipo == "colisao"]
    assert len(colisoes) == 2
    intervalos = " ".join(e.descricao for e in colisoes)
    assert "15–19" in intervalos and "20–60" in intervalos
    assert rel.bloqueia_publicacao


def test_v04_preco_base_bloqueia_e_nao_escolhe(resultado):
    """V-04: arbitrado na Fase 5 — bloqueia a publicação, não rejeita a linha."""
    rel = validador.validar(
        resultado.rascunho,
        {p.sku: p for p in resultado.produtos},
        resultado.conflitos_base,
    )
    base = [e for e in rel.erros if e.tipo == "preco_base_inconsistente"]
    assert len(base) == 1
    assert "SKU-1007" in base[0].descricao
    assert "29,90" in base[0].descricao and "31,00" in base[0].descricao
    # a linha NÃO foi rejeitada — o conflito é do produto, não da regra
    assert not any("preço base" in r.motivo for r in resultado.rejeitadas)


def test_v03_lacuna_avisa_mas_nao_bloqueia():
    """V-03 + AMB-5: lacuna é AVISO. SKU-1009 descoberto em 10–19 e 100+."""
    res = importar(csv_corrigido(), HOJE)
    rel = validador.validar(
        res.rascunho, {p.sku: p for p in res.produtos}, res.conflitos_base
    )
    lacunas = [a for a in rel.avisos if a.sku == "SKU-1009"]
    assert lacunas, "a lacuna do SKU-1009 tem de ser reportada"
    assert "10–19" in lacunas[0].descricao
    assert not any(e.tipo == "lacuna" for e in rel.erros)  # nunca bloqueia


def test_v06_faixa_aberta_duplicada_bloqueia():
    """V-06: duas regras [200,∞) no mesmo SKU e prioridade → colisão."""
    from test_motor import PROD_1001, regra

    regras = [regra("R-1", "SKU-1001", 200, None, "1,85"), regra("R-2", "SKU-1001", 200, None, "1,80")]
    rel = validador.validar(regras, {"SKU-1001": PROD_1001}, [])
    assert any(e.tipo == "colisao" for e in rel.erros)


def test_cs3_reimportacao_rejeita_sku_inexistente():
    """§C-bis (R-06 reclassificado na Fase 5).

    Na PRIMEIRA importação o catálogo é derivado da própria planilha, então
    SKU-9999 se auto-cadastra e o caso não existe. Numa regra sem linha de
    preço base, o SKU não entra no catálogo e a regra é rejeitada.
    """
    csv = (
        "SKU;Produto;Preco base;De;Ate;Preco un.\n"
        "SKU-1001;Caneta;2,50;1;9;2,50\n"
        "SKU-9999;Descontinuado;;1;10;15,00\n"
    ).encode()
    res = importar(csv, HOJE)
    assert any("SKU-9999" in r.motivo for r in res.rejeitadas)
    assert all(r.escopo != "SKU-9999" for r in res.rascunho)


# --------------------------------------------------------------------------
# §B — normalizações que devem ser IMPORTADAS, não rejeitadas.
# --------------------------------------------------------------------------


def test_n01_ate_textual_vira_faixa_aberta(resultado):
    """N-01: 'acima de 200' → [200, ∞)."""
    r = next(x for x in resultado.rascunho if x.escopo == "SKU-1001" and x.faixa.minimo == 200)
    assert r.faixa.maximo is None
    assert r.efeito.valor.iso() == "1.85"


def test_n03_n04_milhar_sobrevive(resultado):
    """N-03/N-04: 'R$ 1.299,00' e 'R$ 1.189,50' do SKU-1010."""
    valores = {
        r.faixa.minimo: r.efeito.valor.iso()
        for r in resultado.rascunho
        if r.escopo == "SKU-1010"
    }
    assert valores == {1: "1299.00", 3: "1189.50"}


def test_n05_sku_com_espaco_e_caixa_normalizado(resultado):
    """N-05: ' sku-1002 ' → SKU-1002, sem produto fantasma."""
    skus = {p.sku for p in resultado.produtos}
    assert "sku-1002" not in skus and " sku-1002 " not in skus
    faixas = sorted(r.faixa.minimo for r in resultado.rascunho if r.escopo == "SKU-1002")
    assert 200 in faixas  # a linha do SKU sujo entrou no SKU certo


def test_normalizacao_antes_da_coerencia(resultado):
    """V-02: a normalização acontece ANTES da checagem, não depois."""
    rel = validador.validar(
        resultado.rascunho, {p.sku: p for p in resultado.produtos}, []
    )
    assert not any("SKU-1002" in e.descricao for e in rel.erros if e.tipo == "colisao")


def test_coluna_desconhecida_preservada_no_relatorio(resultado):
    """LIN-10/Y6: `Obs` é anotação humana — vai ao relatório, não à regra."""
    assert "Obs" in resultado.colunas_desconhecidas


# --------------------------------------------------------------------------
# CS-1 — paridade contra a COLUNA ORIGINAL da planilha (§A, 26 linhas).
# --------------------------------------------------------------------------


def test_cs1_paridade_26_linhas():
    """CS-1: cada linha válida reconsultada no motor bate com o §A.

    O esperado vem da tabela transcrita do artefato, NÃO da saída do motor.
    """
    res = importar(csv_corrigido(), HOJE)
    produtos = {p.sku: p for p in res.produtos}
    conjunto = ConjuntoDeRegras(res.rascunho)
    divergencias = []
    for sku, esperado, qtd in PARIDADE_A:
        obtido = precificar(conjunto, produtos[sku], qtd, HOJE).preco_unitario
        # Tolerância CS-1: R$ 0,01 por unidade.
        if abs(obtido.centavos - int(round(float(esperado) * 100))) > 1:
            divergencias.append((sku, qtd, esperado, obtido.iso()))
    assert not divergencias, divergencias
    assert len(PARIDADE_A) == 26


def test_sec02_limite_de_linhas():
    """SEC-02 + A-18: acima de 2.000 linhas o arquivo é recusado."""
    cabecalho = "SKU;Produto;Preco base;De;Ate;Preco un.\n"
    linhas = "".join(f"SKU-1;P;1,00;{i};{i};1,00\n" for i in range(1, 2100))
    with pytest.raises(ErroDeImportacao) as e:
        importar((cabecalho + linhas).encode(), HOJE)
    assert "linhas" in str(e.value)


def test_sec06_e_lin09_escape_de_formula_ida_e_volta():
    """SEC-06 + LIN-09/Y3: escapa fórmula na saída, desescapa SÓ fórmula na entrada."""
    from app.adaptadores.importador_csv import _desescapar, _escapar

    assert _escapar("=SOMA(A1)") == "'=SOMA(A1)"
    assert _desescapar("'=SOMA(A1)") == "=SOMA(A1)"
    # Valor que LEGITIMAMENTE começa com apóstrofo sobrevive:
    assert _escapar("'Caneta") == "'Caneta"
    assert _desescapar("'Caneta") == "'Caneta"


def test_mig05_round_trip_idempotente():
    """ASS-08/W4: importar → exportar → importar não perde regra nenhuma."""
    res1 = importar(csv_corrigido(), HOJE)
    csv2 = exportar(res1.rascunho, {p.sku: p for p in res1.produtos})
    res2 = importar(csv2, HOJE)
    assert len(res2.rascunho) == len(res1.rascunho)
    assert res2.rejeitadas == []
    chave = lambda r: (r.escopo, r.faixa.minimo, r.faixa.maximo, r.prioridade)
    assert sorted(map(chave, res2.rascunho)) == sorted(map(chave, res1.rascunho))
