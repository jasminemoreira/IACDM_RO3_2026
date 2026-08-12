"""VAL-1 a VAL-8 de specs/validation/criterios-aceitacao.md.

Cada teste verifica o critério EXATO, não um proxy. Onde a spec diz "< 60 s", o
teste cronometra; onde diz "estado idêntico", compara digest; onde diz "zero
falso positivo", planta o caso capaz de produzi-lo.
"""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path

import pytest

from t26 import cli
from t26.persistence.store import Store

RAIZ = Path(__file__).resolve().parent.parent
PERFIS = RAIZ / "perfis"


def test_val1_zero_falsos_negativos(base, dados, ground_truth, capsys):
    """VAL-1: toda duplicata de reimportação plantada é detectada.

    O teste é a contagem final de transações únicas: se alguma duplicata
    escapasse, a base teria mais linhas do que o total real de eventos.
    """
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    capsys.readouterr()
    assert Store(base).contar("transacao") == ground_truth["total_transacoes"], (
        "há transações a mais na base: duplicata de reimportação escapou"
    )


def test_val2_zero_falsos_positivos(base, dados, ground_truth, capsys):
    """VAL-2: nenhuma colisão legítima plantada é fundida."""
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "extrato-julago.ofx"), "bancox", None)
    capsys.readouterr()
    st = Store(base)
    fundidas = [
        fitid
        for par in ground_truth["colisoes_legitimas"]
        for fitid in par
        if (
            r := st.conexao.execute(
                "SELECT duplicata_de FROM transacao WHERE fitid = ?", (fitid,)
            ).fetchone()
        )
        and r["duplicata_de"] is not None
    ]
    assert not fundidas, f"falsos positivos: {fundidas}"


def test_val3_soma_bate_e_nenhum_item_em_dois_estados(base, dados, capsys):
    """VAL-3: 'exatamente um estado' tem duas metades — ambas verificadas."""
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "livro.csv"), None, str(PERFIS / "livro.json"))
    cli.conciliar(str(base))
    capsys.readouterr()
    cli.relatar(str(base), "json", str(base.parent / "rel.json"))
    capsys.readouterr()

    import json

    rel = json.loads((base.parent / "rel.json").read_text())
    assert rel["val3_soma_bate"], "soma por estado não fecha com o total"
    assert sum(rel["contagens"].values()) == rel["total"]
    assert rel["total"] > 0


@pytest.mark.lento
def test_val4_cinquenta_mil_em_menos_de_60s(tmp_path, capsys):
    """VAL-4: CRONOMETRA o pipeline com 50k. "Terminou" não é cobertura."""
    from t26.fixtures.gerador import gerar

    destino = tmp_path / "carga"
    gt = gerar(7, 50000, destino, PERFIS / "bancox.json", PERFIS / "livro.json")
    assert gt.total_transacoes >= 50000, "a carga precisa ter ao menos 50k transações"

    base = tmp_path / "perf.db"
    inicio = time.monotonic()
    cli.importar(str(base), str(destino / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(destino / "livro.csv"), None, str(PERFIS / "livro.json"))
    cli.conciliar(str(base))
    decorrido = time.monotonic() - inicio
    capsys.readouterr()
    assert decorrido < 60, f"pipeline levou {decorrido:.1f}s, limiar é 60s"


def test_val5_digest_identico_apos_3_rodadas(base, dados, capsys):
    """VAL-5: digest do CONTEÚDO, não contagem de linhas."""
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    capsys.readouterr()
    primeiro = Store(base).digest_estado()
    for _ in range(3):
        cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
        capsys.readouterr()
    assert Store(base).digest_estado() == primeiro


def test_val6_nenhuma_transacao_com_dois_casamentos(base, dados, capsys):
    """VAL-6: o invariante 1:1 é do BANCO — consulta procura a violação."""
    cli.importar(str(base), str(dados / "extrato-jul.ofx"), "bancox", None)
    cli.importar(str(base), str(dados / "livro.csv"), None, str(PERFIS / "livro.json"))
    cli.conciliar(str(base))
    capsys.readouterr()
    st = Store(base)
    for coluna in ("transacao", "lancamento"):
        violacoes = st.conexao.execute(
            f"SELECT {coluna} FROM casamento GROUP BY {coluna} HAVING COUNT(*) > 1"
        ).fetchall()
        assert not violacoes, f"{coluna} com mais de um casamento: {violacoes}"


def test_val7_heuristica_nao_sobrescreve_humano(store):
    """NEGATIVO / VAL-7: o UNIQUE do banco impede o segundo casamento.

    Verifica o mecanismo diretamente: tentar casar a mesma transação duas vezes
    deve falhar na constraint, não passar silenciosamente.
    """
    import sqlite3

    from t26.domain.model import Casamento, ChaveNatural, Resultado, Situacao

    a = ChaveNatural("bx", "1", fitid="T1")
    b = ChaveNatural("erp", "1", fitid="L1")
    c = ChaveNatural("erp", "1", fitid="L2")
    with store.unidade_de_trabalho("t1") as uow:
        store.salvar_casamentos(
            uow, [Casamento(a, b, Resultado.CASADO, Situacao.AUTOMATICA, 100)]
        )
    with pytest.raises(sqlite3.IntegrityError):
        with store.unidade_de_trabalho("t2") as uow:
            store.salvar_casamentos(
                uow, [Casamento(a, c, Resultado.CASADO, Situacao.AUTOMATICA, 100)]
            )


def test_val8_dinheiro_recusa_float():
    """NEGATIVO / VAL-8: float em caminho monetário levanta erro de domínio."""
    from t26.domain.model import Dinheiro, ErroDominio

    with pytest.raises(ErroDominio):
        Dinheiro(1250.00)
    with pytest.raises(ErroDominio):
        Dinheiro("1250.00")
    assert Dinheiro(Decimal("1250.00")).texto() == "1250.00"
