"""UC-1 a UC-6 e UC-8 — specs/validation/acceptance.md."""

from __future__ import annotations

import pytest

from conftest import delete, edit, event_of, make_stack, seed
from t28agenda.providers import Scenario
from t28agenda.reconciler import DELETE_VS_UPDATE, SAME_FIELD


@pytest.fixture
def basic(stack, fixtures):
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "so-em-a.ics")
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    seed(beta, fixtures / "basic" / "so-em-b.ics")
    return repo, alpha, beta, engine


# --- UC-1 -------------------------------------------------------------------
def test_uc1_primeira_sync_converge(basic):
    repo, alpha, beta, engine = basic
    report = engine.run_cycle()
    assert len(report.applied) == 3
    assert report.conflicts_opened == []
    assert len(alpha.all_resources()) == 3
    assert len(beta.all_resources()) == 3


def test_uc1_evento_de_um_lado_nao_e_descartado(basic):
    """NEGATIVO: evento que existe em um so lado nao pode sumir."""
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    assert event_of(beta, "so-em-a@t28") is not None
    assert event_of(alpha, "so-em-b@t28") is not None


# --- UC-2 -------------------------------------------------------------------
def test_uc2_segundo_ciclo_nao_escreve(basic):
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    writes_before = alpha.write_count() + beta.write_count()
    report = engine.run_cycle()
    assert report.applied == []
    # VAL-4 verifica o criterio EXATO: zero escritas, contando chamadas no
    # provedor. Comparar o estado final passaria mesmo reescrevendo o igual.
    assert alpha.write_count() + beta.write_count() == writes_before


def test_uc2_eco_de_provedor_que_renormaliza_nao_propaga(stack, fixtures):
    """NEGATIVO: o dialeto beta TRUNCA a descricao ao gravar. O eco dessa
    renormalizacao nao pode ser lido como mudanca externa (achado CTL-04)."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    edit(alpha, "compartilhado@t28", description="x" * 400)
    engine.run_cycle()
    assert len(event_of(beta, "compartilhado@t28").description) == 200  # provedor truncou
    for _ in range(3):
        report = engine.run_cycle()
        assert report.applied == [], "ping-pong: o eco da renormalizacao virou mudanca externa"


# --- UC-3 -------------------------------------------------------------------
def test_uc3_campos_disjuntos_mesclam(basic):
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", location="Sala 9")
    edit(beta, "compartilhado@t28", summary="Planejamento revisado")
    report = engine.run_cycle(policy="pol4")
    assert report.conflicts_opened == []
    for provider in (alpha, beta):
        event = event_of(provider, "compartilhado@t28")
        assert event.location == "Sala 9"
        assert event.summary == "Planejamento revisado"


def test_uc3_merge_nao_descarta_nenhum_lado(basic):
    """NEGATIVO: nenhuma das duas edicoes pode ser perdida."""
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", location="Sala 9")
    edit(beta, "compartilhado@t28", description="pauta nova")
    engine.run_cycle(policy="pol4")
    event = event_of(alpha, "compartilhado@t28")
    assert event.location == "Sala 9" and event.description == "pauta nova"


# --- UC-4 -------------------------------------------------------------------
def test_uc4_mesmo_campo_abre_conflito(basic):
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="Versao A")
    edit(beta, "compartilhado@t28", summary="Versao B")
    report = engine.run_cycle(policy="pol4")
    assert len(report.conflicts_opened) == 1
    assert report.applied == []
    assert repo.list_conflicts("OPEN")[0].klass == SAME_FIELD


def test_uc4_chave_bloqueada_ate_decisao(basic):
    """NEGATIVO: com conflito aberto, nada daquela chave e aplicado."""
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="Versao A")
    edit(beta, "compartilhado@t28", summary="Versao B")
    engine.run_cycle(policy="pol4")
    report = engine.run_cycle(policy="pol4")
    assert report.applied == []
    assert "compartilhado@t28" in report.blocked_keys
    assert event_of(beta, "compartilhado@t28").summary == "Versao B"  # intacto


def test_uc4_resolve_aplica_no_proximo_sync(basic):
    from datetime import datetime

    from t28agenda.conflict_queue import transition_resolve

    repo, alpha, beta, engine = basic
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="Versao A")
    edit(beta, "compartilhado@t28", summary="Versao B")
    engine.run_cycle(policy="pol4")
    conflict = repo.list_conflicts("OPEN")[0]
    repo.begin()
    repo.save_conflict(transition_resolve(conflict, "a", datetime.now().astimezone()))
    repo.commit()
    report = engine.run_cycle(policy="pol4")
    assert len(report.applied) == 1
    assert event_of(beta, "compartilhado@t28").summary == "Versao A"
    assert repo.get_conflict(conflict.id).state == "APPLIED"


# --- UC-5 -------------------------------------------------------------------
def test_uc5_delete_vs_update_e_classe_propria(basic):
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    delete(alpha, "compartilhado@t28")
    edit(beta, "compartilhado@t28", summary="editado em B")
    report = engine.run_cycle(policy="pol4")
    assert report.applied == []
    assert [c.klass for c in repo.list_conflicts("OPEN")] == [DELETE_VS_UPDATE]


def test_uc5_delete_simples_propaga(basic):
    """NEGATIVO: delecao SEM edicao concorrente nao pode virar conflito."""
    repo, alpha, beta, engine = basic
    engine.run_cycle()
    delete(alpha, "compartilhado@t28")
    report = engine.run_cycle(policy="pol4")
    assert repo.list_conflicts("OPEN") == []
    assert event_of(beta, "compartilhado@t28") is None
    assert any("delete" in item for item in report.applied)


# --- UC-6 -------------------------------------------------------------------
def test_uc6_token_invalidado_refaz_full_sync(workspace, fixtures):
    repo, alpha, beta, engine = make_stack(workspace, Scenario(invalidate_token_at_cycle=2))
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    antes = len(beta.all_resources())
    report = engine.run_cycle()
    assert report.full_resync == ["beta"]
    assert len(beta.all_resources()) == antes


def test_uc6_full_resync_preserva_mapa_de_identidade(workspace, fixtures):
    """NEGATIVO: refazer full sync nao pode duplicar nem perder evento."""
    repo, alpha, beta, engine = make_stack(workspace, Scenario(invalidate_token_at_cycle=2))
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    seed(alpha, fixtures / "basic" / "so-em-a.ics")
    engine.run_cycle()
    engine.run_cycle()
    engine.run_cycle()
    uids = [event_of(beta, uid) for uid in ("compartilhado@t28", "so-em-a@t28")]
    assert all(e is not None for e in uids)
    assert len(beta.all_resources()) == 2, "full resync duplicou eventos"


# --- UC-8 -------------------------------------------------------------------
def test_uc8_excecao_tem_chave_propria(stack, fixtures):
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "recurring" / "serie.ics")
    seed(alpha, fixtures / "recurring" / "serie-excecao.ics")
    engine.run_cycle()
    chaves = {str(k) for k in repo.load_all_ancestors()}
    assert "serie@t28" in chaves
    assert "serie@t28#2026-11-13T12:00:00+00:00" in chaves


def test_uc8_editar_excecao_nao_altera_serie(stack, fixtures):
    """NEGATIVO: mexer na instancia destacada nao pode reescrever a serie-mestre."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "recurring" / "serie.ics")
    seed(alpha, fixtures / "recurring" / "serie-excecao.ics")
    engine.run_cycle()
    for provider_id, ics in beta.all_resources().items():
        from t28agenda.normalizer import to_canonical, to_ics
        from t28agenda.providers import WriteOp

        event = to_canonical(ics, beta.dialect)
        if event.recurrence_id is not None:
            beta.write(WriteOp("update", ics=to_ics(event.with_fields(summary="mexido"), beta.dialect),
                               provider_id=provider_id))
    engine.run_cycle()
    mestre_depois = [
        to_canonical(ics, alpha.dialect) for ics in alpha.all_resources().values()
    ]
    mestre = [e for e in mestre_depois if e.uid == "serie@t28" and e.recurrence_id is None][0]
    assert mestre.rrule is not None
    assert mestre.summary != "mexido"
