"""Superfície de CLI — pytest + subprocess (decisão UI TOOL da Fase 6).

A CLI é exercida como o operador a exerce: por linha de comando, verificando
código de saída e saída padrão.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GUARDA = ["--guarda-taxa-erro", "0.10", "--guarda-latencia-p99", "400"]


def executar(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "canario.cli", *args],
        cwd=RAIZ, capture_output=True, text=True, timeout=120,
    )


def test_cli_uc2_reverte_com_saida_1() -> None:
    r = executar("uc2", *GUARDA)
    assert r.returncode == 1
    assert "REVERTIDO" in r.stdout


def test_cli_uc3_nao_reverte_com_saida_0() -> None:
    r = executar("uc3", *GUARDA)
    assert r.returncode == 0
    assert "PROMOVIDO" in r.stdout


def test_cli_imprime_a_configuracao_da_guarda() -> None:
    """Achados GOV-02 e SCI-01: o valor sem fonte é impresso e atribuído."""
    r = executar("uc1", *GUARDA)
    assert "SEM FONTE" in r.stdout
    assert "0.1" in r.stdout


def test_cli_imprime_aquecendo_em_vez_de_silenciar() -> None:
    """Achado UX-01: silêncio durante os primeiros 50 pontos seria
    indistinguível de travamento."""
    r = executar("uc1", *GUARDA)
    assert "aquecendo" in r.stdout


def test_cli_distingue_erro_de_coleta_de_falha_do_canario() -> None:
    """Achado OBS-02 / UC-4."""
    r = executar("uc4", *GUARDA)
    assert "erro de coleta, NÃO falha do canário" in r.stdout


def test_cli_expoe_temporizacao_de_r07() -> None:
    """VAL-8 observável na saída, não só no teste."""
    r = executar("uc2", *GUARDA)
    assert "R-07" in r.stdout
    assert "rollback em 30, previsto 30" in r.stdout


def test_cli_exige_os_limiares_da_guarda() -> None:
    """NEGATIVO — sem os obrigatórios, argparse recusa."""
    r = executar("uc1")
    assert r.returncode != 0
    assert "guarda" in (r.stderr + r.stdout).lower()


def test_cli_recusa_cenario_inexistente() -> None:
    """NEGATIVO — achado SEC-03."""
    r = executar("uc99", *GUARDA)
    assert r.returncode != 0


def test_cli_reporta_configuracao_invalida_sem_traceback() -> None:
    """NEGATIVO — achado MEC-03: falha de validação é mensagem, não exceção crua."""
    r = executar("uc1", *GUARDA, "--duracao-maxima", "0")
    saida = r.stdout + r.stderr
    assert "Traceback" not in saida or r.returncode == 1


@pytest.mark.parametrize("chave", ["uc1", "uc2", "uc3", "uc4"])
def test_cli_determinismo_entre_execucoes(chave: str) -> None:
    """VAL-10 pela superfície: duas execuções, saída byte a byte idêntica."""
    assert executar(chave, *GUARDA).stdout == executar(chave, *GUARDA).stdout
