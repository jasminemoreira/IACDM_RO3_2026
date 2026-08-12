"""MEC-B (journal), histerese de oscilacao e manutencao.

Estes mecanismos responderam a criticos da Fase 2 (ASS-01, RES-01, CTL-05).
Deixa-los sem teste seria a armadilha classica: a suite fica verde e o criterio
nao esta verificado.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from conftest import edit, event_of, seed
from t28agenda.canonical_event import EventKey
from t28agenda.repository import CycleStateError, DONE


def test_ciclo_interrompido_e_reconciliado_no_proximo_sync(stack, fixtures):
    """ASS-01/RES-01: processo morto no meio do ciclo deixa journal aberto. O
    ciclo seguinte reconcilia sem perder nem reverter o que ja foi aplicado."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()

    # simula morte do processo: abre um ciclo com intencao registrada e some
    repo.begin()
    cycle_id = repo.open_cycle(
        [(EventKey("compartilhado@t28"), "a->b", "upsert")], "pol4", False,
        datetime.now().astimezone(),
    )
    repo.commit()
    repo._open_cycle_id = None
    assert repo.open_cycles() == [cycle_id]

    report = engine.run_cycle()
    assert report.recovered_cycle == cycle_id
    assert repo.open_cycles() == []
    assert event_of(beta, "compartilhado@t28") is not None, "retomada perdeu evento ja aplicado"


def test_close_cycle_recusa_acao_planejada_nao_marcada(stack, fixtures):
    """NEGATIVO (LIN-08): fechar com acao pendente deixaria o estado ambiguo."""
    repo, alpha, beta, engine = stack
    repo.begin()
    cycle_id = repo.open_cycle(
        [(EventKey("x@t28"), "a->b", "upsert")], "pol4", False, datetime.now().astimezone()
    )
    repo.commit()
    with pytest.raises(CycleStateError):
        repo.close_cycle(cycle_id, {}, datetime.now().astimezone())


def test_mark_applied_e_idempotente(stack):
    """IMP-07: a retomada pode remarcar a mesma acao."""
    repo, alpha, beta, engine = stack
    repo.begin()
    cycle_id = repo.open_cycle(
        [(EventKey("x@t28"), "a->b", "upsert")], "pol4", False, datetime.now().astimezone()
    )
    repo.commit()
    entrada = repo.journal_of(cycle_id)[0]
    repo.begin()
    repo.mark_applied(entrada.id, "pid-1", "v1", "fp1")
    repo.mark_applied(entrada.id, "pid-1", "v1", "fp1")
    repo.commit()
    entradas = repo.journal_of(cycle_id)
    assert len(entradas) == 1 and entradas[0].state == DONE


def test_histerese_suspende_chave_oscilante(stack, fixtures):
    """CTL-05: chave que alterna de direcao em 3 ciclos seguidos e suspensa e vai
    para a fila, em vez de continuar sendo reescrita para sempre."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()

    chave = EventKey("compartilhado@t28")
    # historico fabricado: a->b, b->a, a->b em ciclos consecutivos
    for direcao in ("a->b", "b->a", "a->b"):
        repo.begin()
        cycle_id = repo.open_cycle([(chave, direcao, "upsert")], "pol4", False,
                                   datetime.now().astimezone())
        repo.commit()
        entrada = repo.journal_of(cycle_id)[0]
        repo.begin()
        repo.mark_applied(entrada.id, "pid", "v", "fp")
        repo.close_cycle(cycle_id, {}, datetime.now().astimezone())
        repo.commit()

    edit(beta, "compartilhado@t28", summary="mudanca que iria propagar b->a")
    report = engine.run_cycle()
    assert report.suspended_oscillating == ["compartilhado@t28"]
    assert report.applied == []
    assert repo.list_conflicts("OPEN")[0].klass == "OSCILLATION"


def test_chave_estavel_nao_e_suspensa(stack, fixtures):
    """NEGATIVO: propagacao sempre na MESMA direcao nao pode ser confundida com
    oscilacao — senao a histerese pararia o sync normal."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    for i in range(4):
        edit(alpha, "compartilhado@t28", summary=f"edicao {i}")
        report = engine.run_cycle()
        assert report.suspended_oscillating == []
        assert len(report.applied) == 1


def test_maintenance_recompute_fingerprints(stack, fixtures):
    """MEC-05: o recalculo tem caminho de execucao real (depende de C-1, que
    devolveu o snapshot ao ancestral)."""
    from t28agenda.normalizer import fingerprint

    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    ancestral = repo.load_all_ancestors()[EventKey("compartilhado@t28")]
    assert ancestral.side_a.snapshot is not None
    assert ancestral.side_a.fingerprint == fingerprint(ancestral.side_a.snapshot)


def test_prune_preserva_ciclo_com_conflito_aberto(stack, fixtures):
    """GOV-05: a poda nao pode apagar journal referenciado por conflito aberto."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="A")
    edit(beta, "compartilhado@t28", summary="B")
    engine.run_cycle()
    ciclos_antes = len(repo.recent_cycles(100))
    repo.begin()
    repo.prune(datetime.now().astimezone())
    repo.commit()
    assert len(repo.recent_cycles(100)) == ciclos_antes


def test_lock_impede_dois_ciclos_simultaneos(stack):
    """RES-04: duas execucoes sobre o mesmo .db nao podem se sobrepor."""
    repo, alpha, beta, engine = stack
    from t28agenda.repository import Repository

    repo.acquire_lock()
    outro = Repository(repo.path)
    outro.conn.execute(
        "INSERT INTO meta(k,v) VALUES ('lock', ?) ON CONFLICT(k) DO UPDATE SET v = ?",
        ('[999999, %f]' % 1e12, '[999999, %f]' % 1e12),
    )
    with pytest.raises(RuntimeError, match="outro ciclo em execucao"):
        outro.acquire_lock()


def test_lock_orfao_expira(stack):
    """NEGATIVO (RES-06): lock deixado por processo morto nao pode bloquear para
    sempre — expira por tempo."""

    repo, alpha, beta, engine = stack
    repo.conn.execute(
        "INSERT INTO meta(k,v) VALUES ('lock', ?) ON CONFLICT(k) DO UPDATE SET v = ?",
        ("[999999, 0.0]", "[999999, 0.0]"),
    )
    repo.acquire_lock()  # timestamp 0 => muito velho => expirado


def test_sec01_serie_infinita_nao_expande_sem_limite(stack):
    """SEC-01: RRULE sem UNTIL/COUNT com frequencia alta e uma bomba de expansao."""
    from datetime import timedelta

    from t28agenda.recurrence import MAX_INSTANCES_PER_SERIES, ExpansionWindow, build_calendar, expand
    from conftest import ANCHOR

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "specs" / "datasets"))
    import generate

    bomba = generate.vevent("bomba@t28", ANCHOR, 1, "bomba", rrule="FREQ=MINUTELY")
    janela = ExpansionWindow(ANCHOR - timedelta(days=1), ANCHOR + timedelta(days=30))
    with pytest.raises(ValueError, match=str(MAX_INSTANCES_PER_SERIES)):
        expand(build_calendar([bomba]), janela, "alpha")
