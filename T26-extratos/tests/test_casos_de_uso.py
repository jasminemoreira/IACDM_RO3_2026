"""Casos de uso UC-1 a UC-5 da Fase 0 — 1 positivo + 1 negativo cada, no mínimo.

Testa contra as SPECS. Cada teste declara no docstring qual critério EXATO
verifica, porque specs/validation/criterios-aceitacao.md proíbe explicitamente as
falsas coberturas do tipo "o teste roda, logo a spec está atendida".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from t26 import cli
from t26.adapters import csv_fonte, ofx
from t26.adapters.perfil import carregar_perfil
from t26.persistence.store import Store

RAIZ = Path(__file__).resolve().parent.parent
PERFIS = RAIZ / "perfis"


# --------------------------------------------------------------------------- #
# UC-1 — importar extrato de fonte nova
# --------------------------------------------------------------------------- #


def test_uc1_importa_ofx_e_reporta_por_classe(base, dados, capsys):
    """UC-1: as contagens por classe devem SOMAR o total de linhas lidas.

    Não basta "importou sem erro": o caso de uso promete ao analista um
    fechamento entre novas, já presentes e duplicatas.
    """
    codigo = cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    assert codigo == cli.Saida.OK

    saida = capsys.readouterr().out
    lidas = int(saida.split(" linhas lidas")[0].strip())
    novas = int(saida.split("novas")[1].split("\n")[0].strip())
    presentes = int(saida.split("(mesma linha)")[1].split("\n")[0].strip())
    dup = int(saida.split("(dedup)")[1].split("\n")[0].strip())
    assert novas + presentes + dup == lidas, "as classes não fecham com o total lido"
    assert Store(base).contar("transacao") == novas


def test_uc1_ofx_malformado_aborta_nomeando_arquivo(base, tmp_path):
    """NEGATIVO — arquivo inválido aborta com erro que NOMEIA o arquivo.

    RES-02 é dívida aceita: sem quarentena, o lote aborta. O que não pode
    acontecer é perda silenciosa nem mensagem que não diga onde foi.
    """
    ruim = tmp_path / "quebrado.ofx"
    ruim.write_text("OFXHEADER:100\n\n<OFX><LIXO></OFX>\n")
    with pytest.raises(ofx.ErroLeituraOFX) as erro:
        ofx.ler(ruim, "bancox")
    assert "quebrado.ofx" in str(erro.value)
    assert not base.exists(), "nada deve ter sido gravado"


# --------------------------------------------------------------------------- #
# UC-2 — reimportação com janela sobreposta (idempotência)
# --------------------------------------------------------------------------- #


def test_uc2_janela_sobreposta_nao_duplica(base, dados, ground_truth, capsys):
    """UC-2: a segunda importação reconhece as linhas do período sobreposto.

    Verifica contra o ground truth: o número de já-presentes deve ser
    exatamente o de duplicatas de reimportação plantadas.
    """
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    capsys.readouterr()
    cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    saida = capsys.readouterr().out
    presentes = int(saida.split("(mesma linha)")[1].split("\n")[0].strip())
    esperado = len(ground_truth["duplicatas_reimportacao"])
    assert presentes == esperado, f"esperado {esperado} já-presentes, veio {presentes}"


def test_uc2_reimportar_n_vezes_digest_identico(base, dados, capsys):
    """VAL-5: estado IDÊNTICO, medido por digest do conteúdo.

    Contagem de linhas não serve — valores podem ser sobrescritos sem mudar a
    contagem. É a falsa cobertura que specs/validation nomeia.
    """
    for _ in range(2):
        cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
        cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    capsys.readouterr()
    digest_1 = Store(base).digest_estado()

    for _ in range(2):
        cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
        cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    capsys.readouterr()
    assert Store(base).digest_estado() == digest_1


# --------------------------------------------------------------------------- #
# UC-3 — duplicata cross-source
# --------------------------------------------------------------------------- #


def test_uc3_cross_source_nunca_descarta(base, dados, ground_truth, capsys):
    """VAL-1: nenhuma duplicata cross-source plantada pode virar "distinta".

    Ou funde, ou vira pendência. Descartar sem revisão é falso negativo.
    """
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(
        str(base), str(dados / "extrato-outrafonte.csv"), None, str(PERFIS / "bancox.json")
    )
    saida = capsys.readouterr().out
    dup = int(saida.split("(dedup)")[1].split("\n")[0].strip())
    pend = int(saida.split("pendências de revisão")[1].split("\n")[0].strip())
    plantadas = len(ground_truth["duplicatas_cross_source"])
    assert dup + pend >= plantadas, (
        f"{plantadas} cross-source plantadas, apenas {dup + pend} tratadas — "
        "o resto foi descartado sem revisão"
    )


def test_uc3_colisao_legitima_nao_funde(base, dados, ground_truth, capsys):
    """NEGATIVO / VAL-2: duas transações realmente distintas NÃO podem fundir.

    Sem colisões plantadas no dataset, este teste não teria como falhar — é
    exatamente por isso que o fixture-generator as planta.
    """
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    capsys.readouterr()
    st = Store(base)
    for a, b in ground_truth["colisoes_legitimas"]:
        for fitid in (a, b):
            linha = st.conexao.execute(
                "SELECT duplicata_de FROM transacao WHERE fitid = ?", (fitid,)
            ).fetchone()
            assert linha is not None, f"transação {fitid} sumiu da base"
            assert linha["duplicata_de"] is None, (
                f"colisão legítima {fitid} foi fundida — falso positivo, viola VAL-2"
            )


# --------------------------------------------------------------------------- #
# UC-4 — conciliar contra o livro
# --------------------------------------------------------------------------- #


def test_uc4_todo_item_em_exatamente_um_estado(base, dados, capsys):
    """VAL-3: verifica AS DUAS metades — todo item tem estado, e só um."""
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "livro.csv"), None, str(PERFIS / "livro.json"))
    capsys.readouterr()
    assert cli.conciliar(str(base)) == cli.Saida.OK
    saida = capsys.readouterr().out
    classificados, total = (
        int(x) for x in saida.split("VAL-3: ")[1].split(" itens")[0].split(" de ")
    )
    assert classificados == total, "há item sem estado terminal"

    st = Store(base)
    duplos = st.conexao.execute(
        """SELECT transacao FROM casamento GROUP BY transacao HAVING COUNT(*) > 1"""
    ).fetchall()
    assert not duplos, "item em mais de um estado — a outra metade de VAL-3"


def test_uc4_sem_livro_recusa_com_codigo_3(base, dados, capsys):
    """NEGATIVO / PRC-04: conciliar sem livro deve RECUSAR, não devolver órfãos.

    100% de órfão-no-extrato é indistinguível de falha real; o código de saída
    precisa dizer que foi pré-condição, não zero e não um.
    """
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    capsys.readouterr()
    assert cli.conciliar(str(base)) == cli.Saida.ERRO_ESTADO


# --------------------------------------------------------------------------- #
# UC-5 — revisar e resolver pendência
# --------------------------------------------------------------------------- #


def _preparar_pendencias(base, dados, capsys):
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(
        str(base), str(dados / "extrato-outrafonte.csv"), None, str(PERFIS / "bancox.json")
    )
    capsys.readouterr()


def test_uc5_resolucao_sai_da_fila(base, dados, capsys):
    """UC-5: item resolvido deixa a fila."""
    from t26.persistence.auditoria import AuditLog
    from t26.review.fila import ReviewQueue

    _preparar_pendencias(base, dados, capsys)
    st = Store(base)
    fila = ReviewQueue(st, AuditLog(st))
    antes = fila.listar()
    assert antes, "o cenário precisa gerar ao menos uma pendência"
    with st.unidade_de_trabalho("t-uc5") as uow:
        fila.resolver(uow, antes[0].id, "sao-distintas", "tester")
    assert len(fila.listar()) == len(antes) - 1


def test_uc5_acao_de_familia_errada_recusada(base, dados, capsys):
    """NEGATIVO / PRC-02: as duas famílias têm conjuntos de ação distintos."""
    from t26.persistence.auditoria import AuditLog
    from t26.review.fila import ErroRevisao, ReviewQueue

    _preparar_pendencias(base, dados, capsys)
    st = Store(base)
    fila = ReviewQueue(st, AuditLog(st))
    dedup = [i for i in fila.listar() if i.familia == "dedup"]
    assert dedup, "o cenário precisa gerar pendência de dedup"
    with pytest.raises(ErroRevisao):
        with st.unidade_de_trabalho("t-fam") as uow:
            fila.resolver(uow, dedup[0].id, "casar-com", "tester")


def test_uc5_resolucao_reaplicada_em_execucao_posterior(base, dados, capsys):
    """VAL-7: a decisão humana vale na PRÓXIMA execução, e a heurística não a sobrepõe.

    É a metade do critério que a Fase 5 deixou sem verificar: não basta gravar a
    resolução, ela tem de vincular quando o mesmo par reaparece.
    """
    from datetime import date

    from t26.domain.model import RegistroBruto, construir_transacoes
    from t26.engines.dedup import DedupEngine, Escopo
    from t26.matching import matcher as M
    from t26.persistence.auditoria import AuditLog
    from t26.review.fila import ReviewQueue

    # Cenário CONTROLADO: duas observações que caem deliberadamente na faixa de
    # revisão (valor e data iguais, contrapartes escritas de formas diferentes —
    # a premissa A6). Depender de um subproduto do dataset tornaria o teste
    # frágil e mediria outra coisa.
    dia = date(2026, 7, 14)
    def _reg(fonte, conta, desc, linha):
        return RegistroBruto(fonte=fonte, conta=conta, data=dia, valor_texto="-1250.00",
                             descricao_bruta=desc, arquivo=f"{fonte}.csv", linha=linha)

    st = Store(base)
    log = AuditLog(st)
    existente = construir_transacoes([_reg("bx", "1", "PIX ENVIADO JOAO", 2)])
    nova = construir_transacoes([_reg("by", "2", "TRANSF J SILVA ME", 2)])
    with st.unidade_de_trabalho("t-seed") as uow:
        st.gravar_lote(uow, [(t, M.chave_bloco(t)) for t in existente + nova])

    engine = DedupEngine(st, log)
    with st.unidade_de_trabalho("t-val7a") as uow:
        primeiro = engine.classificar_lote(uow, nova, existente, Escopo())
    assert primeiro.pendencias, "o cenário deve produzir pendência de dedup"

    fila = ReviewQueue(st, log)
    alvo = fila.listar(familia="dedup")[0]
    assert alvo.candidatos, "a pendência precisa ter candidato para resolver"
    with st.unidade_de_trabalho("t-val7") as uow:
        fila.resolver(uow, alvo.id, "sao-distintas", "tester", alvo=alvo.candidatos[0])

    with st.unidade_de_trabalho("t-val7b") as uow:
        res = engine.classificar_lote(uow, nova, existente, Escopo())

    camadas = {d.camada.value for d in res.decisoes}
    assert "L0" in camadas, (
        f"a resolução humana não foi reaplicada: decidiu por {camadas} em vez de L0"
    )
    assert not res.duplicatas, "heurística fundiu um par que o humano declarou distinto"


# --------------------------------------------------------------------------- #
# Código de saída real, via processo (OBS-03)
# --------------------------------------------------------------------------- #


def test_codigo_de_saida_por_classe_no_processo(tmp_path):
    """NEGATIVO / OBS-03: o processo devolve código por CLASSE de falha.

    Rodado via subprocess porque é o valor que um script veria de fato.
    """
    r = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "t26.cli",
         "--base", str(tmp_path / "x.db"), "importar", "--fonte", "b", "/nao/existe.ofx"],
        capture_output=True, text=True, cwd=RAIZ,
    )
    assert r.returncode == cli.Saida.ERRO_ENTRADA, r.stderr
