"""M-12 cli — testada por subprocesso: stdout e exit code de verdade.

Exit codes sao contrato (achado UX-04): 0 sucesso, 1 erro, 2 conflito aberto,
3 provedor indisponivel na retomada.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import ROOT, edit, make_stack, seed


def run(workspace, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "t28agenda.cli", "-w", str(workspace), *args],
        capture_output=True, text=True, cwd=ROOT,
    )


@pytest.fixture
def preparado(workspace, fixtures):
    repo, alpha, beta, engine = make_stack(workspace)
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    seed(beta, fixtures / "basic" / "so-em-b.ics")
    return workspace, repo, alpha, beta, engine


def test_cli_sync_aplica_e_sai_zero(preparado):
    workspace, *_ = preparado
    resultado = run(workspace, "sync")
    assert resultado.returncode == 0
    assert "escritas aplicadas: 2" in resultado.stdout


def test_cli_dry_run_nao_escreve(preparado):
    """NEGATIVO: o plano nao pode alterar nenhum provedor."""
    workspace, repo, alpha, beta, engine = preparado
    antes = (alpha.write_count(), beta.write_count())
    resultado = run(workspace, "sync", "--dry-run")
    assert resultado.returncode == 0
    assert "dry-run" in resultado.stdout
    assert (alpha.write_count(), beta.write_count()) == antes


def test_cli_exit_code_2_com_conflito_aberto(preparado):
    workspace, repo, alpha, beta, engine = preparado
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="A")
    edit(beta, "compartilhado@t28", summary="B")
    resultado = run(workspace, "sync")
    assert resultado.returncode == 2, "script nao consegue distinguir sucesso de pendencia"
    assert "BLOQUEADAS POR CONFLITO" in resultado.stdout or "conflitos abertos" in resultado.stdout


def test_cli_conflicts_show_exibe_os_tres_valores(preparado):
    """UX-02: decidir sem ver ancestral, lado A e lado B e decidir as cegas."""
    workspace, repo, alpha, beta, engine = preparado
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="Versao A")
    edit(beta, "compartilhado@t28", summary="Versao B")
    engine.run_cycle()
    conflito = repo.list_conflicts("OPEN")[0]
    resultado = run(workspace, "conflicts", "show", conflito.id)
    assert resultado.returncode == 0
    assert "ancestral" in resultado.stdout
    assert "Versao A" in resultado.stdout and "Versao B" in resultado.stdout


def test_cli_resolve_nao_aplica_sozinho(preparado):
    """PRO-03: o handoff e explicito — resolver grava, `sync` aplica."""
    workspace, repo, alpha, beta, engine = preparado
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="Versao A")
    edit(beta, "compartilhado@t28", summary="Versao B")
    engine.run_cycle()
    conflito = repo.list_conflicts("OPEN")[0]
    resultado = run(workspace, "conflicts", "resolve", conflito.id, "--take", "a")
    assert resultado.returncode == 0
    assert "rode `t28 sync`" in resultado.stdout
    assert repo.get_conflict(conflito.id).state == "RESOLVED"


def test_cli_resolve_merge_invalido_em_delete_vs_update(preparado):
    """NEGATIVO: escolha sem significado para a classe tem de ser recusada."""
    from conftest import delete

    workspace, repo, alpha, beta, engine = preparado
    engine.run_cycle()
    delete(alpha, "compartilhado@t28")
    edit(beta, "compartilhado@t28", summary="editado")
    engine.run_cycle()
    conflito = repo.list_conflicts("OPEN")[0]
    resultado = run(workspace, "conflicts", "resolve", conflito.id, "--take", "merge")
    assert resultado.returncode == 1
    assert "invalida" in resultado.stderr


def test_cli_conflito_inexistente_e_erro(preparado):
    """NEGATIVO: id que nao existe nao pode sair 0."""
    workspace, *_ = preparado
    resultado = run(workspace, "conflicts", "show", "C-naoexiste")
    assert resultado.returncode == 1


def test_cli_overlaps_since_sem_until_e_erro(preparado):
    """NEGATIVO: janela pela metade nao pode explodir com stack trace."""
    workspace, *_ = preparado
    resultado = run(workspace, "overlaps", "--since", "2026-11-01T00:00:00+00:00")
    assert resultado.returncode == 1
    assert "juntos" in resultado.stderr


def test_cli_status_e_journal_refletem_o_ciclo(preparado):
    workspace, repo, alpha, beta, engine = preparado
    run(workspace, "sync")
    status = run(workspace, "status")
    assert status.returncode == 0
    assert "eventos com ancestral: 2" in status.stdout
    diario = run(workspace, "journal")
    assert diario.returncode == 0
    assert "upsert" in diario.stdout
    assert "valores omitidos" in diario.stdout  # SEC-07: conteudo nao vaza por padrao
