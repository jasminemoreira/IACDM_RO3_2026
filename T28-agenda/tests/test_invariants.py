"""VAL-4, VAL-5, VAL-6, PR-9, R-A1, R-A3 — propriedades do sistema.

Estas sao as invariantes que a Fase 3 declarou como testadas em vez de assumidas.
"""

from __future__ import annotations

from datetime import datetime


from conftest import edit, event_of, make_stack, seed
from t28agenda.canonical_event import UTC, Event, TimeSpec
from t28agenda.normalizer import fingerprint, to_canonical, to_ics
from t28agenda.providers.base import ObservabilityWindow


def test_pr9_fingerprint_estavel_no_round_trip():
    """PR-9: se o round-trip mudar o fingerprint, o sistema oscila para sempre.
    Deixou de ser premissa tacita e virou invariante (achado CTL-03)."""
    evento = Event(
        uid="rt@t28",
        start=TimeSpec(datetime(2026, 11, 5, 17, 0, tzinfo=UTC), "America/Sao_Paulo"),
        end=TimeSpec(datetime(2026, 11, 5, 18, 0, tzinfo=UTC), "America/Sao_Paulo"),
        dtstamp=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        summary="Reuniao", location="Sala 4", description="linha 1\r\nlinha 2  ",
        rrule="FREQ=WEEKLY;COUNT=3", attendees=("mailto:b@x", "mailto:a@x"),
    )
    volta = to_canonical(to_ics(evento, "alpha"), "alpha")
    assert fingerprint(volta) == fingerprint(evento)


def test_pr9_fingerprint_ignora_metadados_de_revisao():
    """NEGATIVO: mudar so SEQUENCE/DTSTAMP nao pode alterar a identidade de
    conteudo — e o que impede o eco de virar mudanca (V(3) Regra 1)."""
    base = Event(
        uid="m@t28",
        start=TimeSpec(datetime(2026, 11, 5, 12, 0, tzinfo=UTC)),
        end=TimeSpec(datetime(2026, 11, 5, 13, 0, tzinfo=UTC)),
        dtstamp=datetime(2026, 11, 2, tzinfo=UTC), summary="X",
    )
    outro = base.with_fields(sequence=99, dtstamp=datetime(2026, 12, 1, tzinfo=UTC))
    assert fingerprint(base) == fingerprint(outro)


def test_pr9_fingerprint_muda_com_conteudo():
    """NEGATIVO simetrico: mudanca real de conteudo TEM de mudar o fingerprint,
    senao a deteccao de mudanca fica cega."""
    base = Event(
        uid="m@t28",
        start=TimeSpec(datetime(2026, 11, 5, 12, 0, tzinfo=UTC)),
        end=TimeSpec(datetime(2026, 11, 5, 13, 0, tzinfo=UTC)),
        summary="X",
    )
    assert fingerprint(base) != fingerprint(base.with_fields(summary="Y"))


def test_val5_convergencia_semantica(stack, fixtures):
    """Apos um ciclo sem conflito pendente, os dois lados sao semanticamente
    iguais — comparado por identidade de conteudo, nao por bytes."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    seed(beta, fixtures / "basic" / "so-em-b.ics")
    engine.run_cycle()
    for uid in ("compartilhado@t28", "so-em-b@t28"):
        a, b = event_of(alpha, uid), event_of(beta, uid)
        assert a is not None and b is not None
        assert a.scalar_fields() == b.scalar_fields()


def test_val4_zero_escritas_no_segundo_ciclo(stack, fixtures):
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    marca = (alpha.write_count(), beta.write_count())
    engine.run_cycle()
    engine.run_cycle()
    assert (alpha.write_count(), beta.write_count()) == marca


def test_val6_nenhuma_edicao_descartada_sem_conflito(stack, fixtures):
    """NEGATIVO: injeta duas edicoes concorrentes e audita — ou as duas foram
    preservadas, ou existe um conflito registrado. Nunca some em silencio."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", summary="A escreveu")
    edit(beta, "compartilhado@t28", summary="B escreveu")
    engine.run_cycle(policy="pol4")
    conflitos = repo.list_conflicts("OPEN")
    lados = {event_of(alpha, "compartilhado@t28").summary,
             event_of(beta, "compartilhado@t28").summary}
    assert conflitos or lados == {"A escreveu"} or lados == {"B escreveu"}
    assert lados == {"A escreveu", "B escreveu"}, "nada foi aplicado: as duas edicoes seguem intactas"
    conflito = conflitos[0]
    assert conflito.value_a.summary == "A escreveu"
    assert conflito.value_b.summary == "B escreveu"  # o valor em disputa esta guardado


def test_ra1_campo_estruturado_escala(stack, fixtures):
    """NEGATIVO: attendees concorrente NAO mescla — escala para conflito (R-A1)."""
    repo, alpha, beta, engine = stack
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    edit(alpha, "compartilhado@t28", attendees=("mailto:a@x",))
    edit(beta, "compartilhado@t28", attendees=("mailto:b@x",))
    report = engine.run_cycle(policy="pol4")
    assert report.applied == []
    assert repo.list_conflicts("OPEN")[0].klass == "STRUCTURED_FIELD"


def test_ra3_saida_de_janela_nao_e_delecao(workspace, fixtures):
    """NEGATIVO e o mais importante do sistema: evento fora da janela observavel
    do provedor com janela NAO pode ser apagado do outro lado."""
    janela = ObservabilityWindow(
        datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 30, tzinfo=UTC)
    )
    repo, alpha, beta, engine = make_stack(workspace, window=janela)
    seed(alpha, fixtures / "basic" / "compartilhado.ics")  # 2026-11-05: dentro
    engine.run_cycle()
    assert event_of(beta, "compartilhado@t28") is not None

    # o evento e movido para fora da janela do beta
    edit(alpha, "compartilhado@t28",
         start=TimeSpec(datetime(2027, 3, 1, 12, 0, tzinfo=UTC)),
         end=TimeSpec(datetime(2027, 3, 1, 13, 0, tzinfo=UTC)))
    engine.run_cycle()
    engine.run_cycle()
    assert event_of(alpha, "compartilhado@t28") is not None, "evento apagado por artefato de protocolo"


def test_ra3_delecao_real_ainda_propaga(workspace, fixtures):
    """Simetrico: a protecao de R-A3 nao pode impedir a delecao LEGITIMA."""
    from conftest import delete

    janela = ObservabilityWindow(
        datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 30, tzinfo=UTC)
    )
    repo, alpha, beta, engine = make_stack(workspace, window=janela)
    seed(alpha, fixtures / "basic" / "compartilhado.ics")
    engine.run_cycle()
    delete(beta, "compartilhado@t28")
    engine.run_cycle()
    assert event_of(alpha, "compartilhado@t28") is None
