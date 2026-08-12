"""UC-7, VAL-3, VAL-7, VAL-8 — conflito de AGENDA (acepcao B) e aritmetica temporal."""

from __future__ import annotations

from datetime import datetime, timedelta


from conftest import seed
from t28agenda.canonical_event import UTC, EventKey, Occurrence
from t28agenda.overlap_detector import find_overlaps
from t28agenda.recurrence import ExpansionWindow, build_calendar, expand

JANELA = ExpansionWindow(
    datetime.fromisoformat("2026-11-01T00:00:00+00:00"),
    datetime.fromisoformat("2026-12-31T00:00:00+00:00"),
)


def ocorrencias(provider, calendar_tz="UTC"):
    resources = list(provider.all_resources().values())
    return expand(build_calendar(resources), JANELA, provider.name, calendar_tz)


def test_uc7_sobreposicao_detectada(stack, fixtures):
    _, alpha, _, _ = stack
    for name in ("sobrepoe-1.ics", "sobrepoe-2.ics"):
        seed(alpha, fixtures / "overlapping" / name)
    overlaps = find_overlaps(ocorrencias(alpha))
    assert len(overlaps) == 1
    assert overlaps[0].minutes == 30  # 14:00-15:00 x 14:30-15:30


def test_uc7_eventos_encostados_nao_sobrepoem(stack, fixtures):
    """NEGATIVO: fim de x == inicio de y NAO e sobreposicao (predicado semiaberto)."""
    _, alpha, _, _ = stack
    for name in ("encostado-1.ics", "encostado-2.ics"):
        seed(alpha, fixtures / "overlapping" / name)
    assert find_overlaps(ocorrencias(alpha)) == []


def test_val8_all_day_bloqueia(stack, fixtures):
    """R-A2: all-day ocupa [00:00, 24:00) e BLOQUEIA eventos com horario no dia."""
    _, _, beta, _ = stack
    seed(beta, fixtures / "timezone" / "feriado.ics")
    seed(beta, fixtures / "timezone" / "reuniao-sp.ics")
    overlaps = find_overlaps(ocorrencias(beta, "UTC"))
    assert len(overlaps) == 1
    assert overlaps[0].minutes == 60


def test_val8_all_day_em_outro_fuso_desloca_ocupacao(stack, fixtures):
    """NEGATIVO: o fuso do calendario de origem MUDA a ocupacao do all-day.
    E o caso que expoe erro de conversao — se o resultado fosse igual em
    qualquer fuso, a regra R-A2 nao estaria sendo aplicada."""
    _, _, beta, _ = stack
    seed(beta, fixtures / "timezone" / "feriado.ics")
    utc = ocorrencias(beta, "UTC")
    sp = ocorrencias(beta, "America/Sao_Paulo")
    assert utc[0].start_utc != sp[0].start_utc
    assert (sp[0].start_utc - utc[0].start_utc) == timedelta(hours=3)


def test_val7_serie_expandida_atravessa_transicao_de_fuso(stack, fixtures):
    """A serie semanal comeca em 06/11 e vai ate janeiro: atravessa a transicao
    de horario de verao do hemisferio norte, e a expansao precisa continuar
    ancorada no mesmo horario LOCAL."""
    _, alpha, _, _ = stack
    seed(alpha, fixtures / "recurring" / "serie.ics")
    ocs = ocorrencias(alpha)
    assert len(ocs) == 7  # 8 da serie - 1 EXDATE
    assert len({o.start_utc.hour for o in ocs}) == 1


def test_val3_sobreposicao_nao_degrada_quadraticamente():
    """VAL-3: varredura ordenada. Com 4.000 ocorrencias disjuntas o custo tem de
    ser praticamente linear — o produto cartesiano faria 8 milhoes de pares."""
    import time

    base = datetime(2026, 11, 1, tzinfo=UTC)
    disjuntas = [
        Occurrence(EventKey(f"e{i}"), base + timedelta(hours=2 * i), base + timedelta(hours=2 * i + 1),
                   f"E{i}", "alpha")
        for i in range(4000)
    ]
    inicio = time.perf_counter()
    assert find_overlaps(disjuntas) == []
    assert time.perf_counter() - inicio < 1.0


def test_val3_sobreposicao_total_enumera_todos_os_pares():
    """NEGATIVO do teste acima: se TODAS se sobrepoem, a saida e O(k) pares —
    o limite linear vale para detectar, nao para enumerar."""
    base = datetime(2026, 11, 1, tzinfo=UTC)
    todas = [
        Occurrence(EventKey(f"e{i}"), base, base + timedelta(hours=5), f"E{i}", "alpha")
        for i in range(50)
    ]
    assert len(find_overlaps(todas)) == 50 * 49 // 2
