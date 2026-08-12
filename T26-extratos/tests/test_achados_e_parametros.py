"""Testes derivados dos ACHADOS da Fase 2 e dos parâmetros de specs/technical.

Cada teste aqui existe porque uma lente adversarial produziu o cenário de falha
que ele exercita. O id do achado está no docstring — é o que permite a um
post-mortem checar se o achado foi de fato tratado, e não apenas marcado.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from t26.domain.model import (
    ChaveNatural,
    Dinheiro,
    Instrumento,
    RegistroBruto,
    Transacao,
    construir_transacoes,
)
from t26.matching import matcher as M

RAIZ = Path(__file__).resolve().parent.parent
PERFIS = RAIZ / "perfis"
D = date(2026, 7, 14)


def _tx(valor, data=D, desc="PIX ENVIADO JOAO", conta="1", fonte="bx", arq="a.csv", ordinal=0,
        instrumento=Instrumento.DESCONHECIDO):
    chave = ChaveNatural(fonte, conta, data=data, valor_texto=valor,
                         descricao_bruta=desc, ordinal=ordinal)
    return Transacao(chave=chave, conta=conta, data=data, valor=Dinheiro(Decimal(valor)),
                     descricao_bruta=desc, fonte=fonte, arquivo=arq, linha=1,
                     instrumento=instrumento)


# --------------------------------------------------------------------------- #
# A7 — estorno (premissa aberta desde a Fase 0)
# --------------------------------------------------------------------------- #


def test_a7_estorno_nao_funde_com_original():
    """NEGATIVO / A7: sinais opostos vetam a fusão, mesmo com valor absoluto igual."""
    original = _tx("-1250.00")
    estorno = _tx("1250.00", desc="ESTORNO PIX JOAO", fonte="by", arq="b.csv")
    assert M.score(M.Par(original, estorno, "b")) < M.CORTE_REVISAO


def test_a7_estorno_ainda_cai_no_mesmo_bloco():
    """A7 documentada, não resolvida: o bloco por abs(valor) SEGUE juntando os dois.

    Este teste afirma a LIMITAÇÃO em vez de escondê-la. Se um dia o bloco passar
    a separar estorno da original, este teste falha e obriga a rever a premissa —
    que é o comportamento correto para uma limitação conhecida.
    """
    original = _tx("-1250.00")
    estorno = _tx("1250.00", desc="ESTORNO PIX JOAO", fonte="by", arq="b.csv")
    assert M.chave_bloco(original).split("|")[1] == M.chave_bloco(estorno).split("|")[1]


# --------------------------------------------------------------------------- #
# PRF-06 / VAL-1 × VAL-4 — teto de bloco
# --------------------------------------------------------------------------- #


def test_bloco_degenerado_vira_pendencia_nao_distinta():
    """PRF-06: excedente do teto é ESCALADO, nunca descartado.

    A precedência declarada em V(3) é corretude sobre desempenho: nenhum par é
    declarado distinto sem que alguém tenha olhado.
    """
    tarifas = [_tx("-30.00", desc=f"TARIFA {i}", ordinal=i) for i in range(M.TETO_BLOCO + 10)]
    pares, excedentes, metricas = M.candidatos(tarifas)
    assert metricas.maior_bloco > M.TETO_BLOCO
    assert excedentes, "bloco acima do teto deve produzir excedentes"
    assert len(excedentes) == len({e.item.chave.texto() for e in excedentes}), (
        "excedente duplicado entre chaves de bloco — infla a fila de revisão"
    )


def test_piso_de_evidencia_forte_impede_descarte():
    """VAL-1: valor e data idênticos nunca caem abaixo do corte de revisão.

    Cenário: cross-source com descrição ilegível de um lado (premissa A6).
    """
    a = _tx("-1250.00", desc="PIX ENVIADO JOAO")
    b = _tx("-1250.00", desc="XPTO 9931", conta="2", fonte="by", arq="b.csv")
    assert M.score(M.Par(a, b, "x")) >= M.CORTE_REVISAO


def test_veto_de_mesma_origem_preserva_colisao():
    """NEGATIVO / VAL-2: duas linhas do MESMO arquivo são dois eventos."""
    a = _tx("-12.00", desc="CAFE CENTRAL", ordinal=0)
    b = _tx("-12.00", desc="CAFE CENTRAL", ordinal=1)
    assert M.score(M.Par(a, b, "x")) < M.CORTE_REVISAO


def test_disjuncao_encontra_par_entre_contas_distintas():
    """A chave única por conta impediria estruturalmente o cross-source."""
    a = _tx("-1250.00", conta="1", fonte="bx", arq="a.csv")
    b = _tx("-1250.00", conta="2", fonte="by", arq="b.csv")
    pares, _, _ = M.candidatos([b], [a])
    assert pares, "disjunção de blocos não gerou o par entre contas distintas"


# --------------------------------------------------------------------------- #
# Janelas por instrumento — specs/technical/rubrica-score.md §2
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "instrumento,dias,dentro_da_janela",
    [
        ("pix", 0, True),
        ("pix", 1, False),  # PIX credita em segundos: 1 dia já é anômalo
        ("ted", 1, True),
        ("cartao", 30, True),  # D+32
        ("cartao", 40, False),
        ("desconhecido", 3, True),  # default conservador
        ("desconhecido", 4, False),
    ],
)
def test_janela_por_instrumento(instrumento, dias, dentro_da_janela):
    """A JANELA por instrumento decide se o par segue candidato ou é descartado.

    O teste mede o efeito da janela, não o casamento automático: com contrapartes
    nomeadas de formas diferentes (premissa A6), a rubrica soma 50 + 30 = 80 e o
    par vai para REVISÃO HUMANA, não para casamento — que é o comportamento
    especificado e conservador. Fora da janela, o par cai abaixo do corte de
    revisão e vira órfão.
    """
    from datetime import timedelta

    from t26.domain.model import Lancamento

    transacao = _tx("-500.00", instrumento=Instrumento(instrumento))
    chave = ChaveNatural("erp", "1", data=D - timedelta(days=dias),
                         valor_texto="-500.00", descricao_bruta="FORNEC X", ordinal=0)
    lancamento = Lancamento(
        chave=chave, conta="1", data=D - timedelta(days=dias),
        valor=Dinheiro(Decimal("-500.00")), descricao_bruta="FORNEC X",
        fonte="erp", arquivo="l.csv", linha=1,
    )
    pontos = M.score_conciliacao(transacao, lancamento)
    assert (pontos >= M.CORTE_REVISAO) is dentro_da_janela, (
        f"{instrumento} com {dias} dias de defasagem: score {pontos}; "
        f"janela documentada = D+{M.janela_do_instrumento(instrumento)}"
    )


# --------------------------------------------------------------------------- #
# Perfis CSV — fecha a lacuna 🟡 declarada na saída da Fase 5
# --------------------------------------------------------------------------- #


def test_tres_perfis_leem_os_tres_layouts(tmp_path):
    """Os TRÊS layouts prometidos na Fase 0 leem dados reais, não só validam."""
    from t26.adapters import csv_fonte
    from t26.adapters.perfil import carregar_perfil

    arquivos = {
        "bancox": ("Data;Valor;Historico\n14/07/2026;-1.250,00;PIX JOAO\n", "utf-8"),
        "bancoy": ("date,debit,credit,memo\n2026-07-14,1250.00,,PIX JOAO\n", "utf-8"),
        "bancoz": ("DT;VLR;DC;DESCR\n14/07/2026;1.250,00;D;PIX JOAO\n", "cp1252"),
    }
    for nome, (conteudo, enc) in arquivos.items():
        caminho = tmp_path / f"{nome}.csv"
        caminho.write_text(conteudo, encoding=enc)
        perfil = carregar_perfil(PERFIS / f"{nome}.json")
        registros = list(csv_fonte.ler(caminho, perfil))
        assert len(registros) == 1, nome
        assert registros[0].valor_texto == "-1250.00", (
            f"perfil {nome} interpretou o sinal errado: {registros[0].valor_texto}"
        )


def test_debito_e_credito_ambos_preenchidos_recusa(tmp_path):
    """NEGATIVO / LIN-08: caso degenerado da gramática tem comportamento declarado."""
    from t26.adapters import csv_fonte
    from t26.adapters.perfil import carregar_perfil

    caminho = tmp_path / "ambos.csv"
    caminho.write_text("date,debit,credit,memo\n2026-07-14,1250.00,500.00,X\n")
    with pytest.raises(csv_fonte.ErroLeituraCSV) as erro:
        csv_fonte.ler(caminho, carregar_perfil(PERFIS / "bancoy.json"))
    assert "ambos.csv:2" in str(erro.value)


def test_utf8_declarado_cp1252_recusado(tmp_path):
    """NEGATIVO / ASM-07: mojibake silencioso é recusado, não aceito."""
    from t26.adapters import csv_fonte
    from t26.adapters.perfil import carregar_perfil

    caminho = tmp_path / "enc.csv"
    caminho.write_bytes("DT;VLR;DC;DESCR\n14/07/2026;1,00;D;JOÃO\n".encode("utf-8"))
    with pytest.raises(csv_fonte.ErroLeituraCSV) as erro:
        csv_fonte.ler(caminho, carregar_perfil(PERFIS / "bancoz.json"))
    assert "UTF-8" in str(erro.value)


# --------------------------------------------------------------------------- #
# Segurança, resiliência e migração
# --------------------------------------------------------------------------- #


def test_formula_csv_saneada_na_exportacao():
    """NEGATIVO / SEC-01: campo de fonte externa não sai executável no Excel."""
    from t26.report.reporter import ItemRelatorio, render, resumo
    from t26.domain.model import Estado5

    itens = [
        ItemRelatorio("k", Estado5.ORFAO_NO_EXTRATO, Decimal("-1"), D, "=cmd|' /c calc'!A0")
    ]
    csv = render(resumo(itens, {}, {}, D), "csv")
    linha = [l for l in csv.splitlines() if "cmd" in l][0]
    assert not linha.split(";")[5].startswith("=")


def test_ofx_com_doctype_recusado(tmp_path):
    """NEGATIVO / SEC-02: expansão de entidades é barrada na entrada."""
    from t26.adapters import ofx

    caminho = tmp_path / "hostil.ofx"
    caminho.write_text('<?xml version="1.0"?>\n<!DOCTYPE r [<!ENTITY a "x">]>\n<OFX/>\n')
    with pytest.raises(ofx.ErroLeituraOFX) as erro:
        ofx.ler(caminho, "bx")
    assert "DOCTYPE" in str(erro.value)


def test_falha_reverte_trilha_e_estado_juntos(store):
    """NEGATIVO / RES-06: a fronteira transacional é compartilhada.

    Se a trilha sobrevivesse a um lote revertido, estado e auditoria divergiriam
    exatamente no momento em que a auditoria é necessária.
    """
    from t26.domain.model import Camada, DecisaoDedup, Veredito
    from t26.persistence.auditoria import AuditLog

    log = AuditLog(store)
    chave = ChaveNatural("bx", "1", fitid="T9")
    antes = store.contar("auditoria")
    with pytest.raises(RuntimeError):
        with store.unidade_de_trabalho("t-falha") as uow:
            log.registrar_lote(
                uow, [DecisaoDedup(chave, Veredito.DISTINTA, Camada.L5_DISTINTAS, "x")]
            )
            raise RuntimeError("falha no meio do lote")
    assert store.contar("auditoria") == antes


def test_base_de_esquema_mais_novo_recusada(base):
    """NEGATIVO / MIG-03: recusar é melhor que ler errado."""
    from t26.persistence.store import EsquemaIncompativel, Store

    st = Store(base)
    st.conexao.execute("UPDATE esquema SET versao = 99")
    st.fechar()
    with pytest.raises(EsquemaIncompativel):
        Store(base)


def test_desfazer_nao_apaga_o_registro_anterior(store):
    """NEGATIVO / GOV-01: a trilha é append-only; corrigir é acrescentar."""
    from t26.domain.model import AcaoDedup, Resolucao
    from t26.persistence.auditoria import AuditLog, agora

    log = AuditLog(store)
    with store.unidade_de_trabalho("t-gov") as uow:
        uow.executar(
            """INSERT INTO pendencia (id, familia, esquerda, candidatos, scores,
                   motivo, aberta, execucao) VALUES (?,?,?,?,?,?,1,?)""",
            ("P1", "dedup", "bx|1|fitid:A", "[]", "[]", "x", "t-gov"),
        )
        log.registrar_resolucao(
            uow, Resolucao("R1", "P1", AcaoDedup.E_A_MESMA, "ana", agora())
        )
        log.registrar_resolucao(
            uow, Resolucao("R2", "P1", AcaoDedup.SAO_DISTINTAS, "ana", agora(), desfaz="R1")
        )
    assert store.contar("resolucao") == 2, "o desfazer apagou o registro original"
