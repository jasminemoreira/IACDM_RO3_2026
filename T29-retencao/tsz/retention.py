"""M-04 retention — valida a configuração de tiers e COMPUTA o plano. Função pura, sem I/O.

Fonte: specs/technical/politica-retencao.md (R6 divisibilidade, R7 xff, R9 tiers/idades).

Recebe a marca d'água DERIVADA do dado (decisão E3 de V(3)) em vez de estado persistido —
por isso `plan()` não pode agir sobre uma realidade que não existe (achado ASM-02) e `retain`
é idempotente por construção (achados PRC-01/CTL-01).
"""

from __future__ import annotations

from .series import REAGGREGABLE, RetentionPlan, SeriesError, TierSpec, align_down


def validate(tiers: list[TierSpec]) -> None:
    """Recusa configurações inválidas. Cada regra tem fonte citada."""
    if not tiers:
        raise SeriesError("é preciso pelo menos um tier (o cru)")

    for i in range(1, len(tiers)):
        prev, cur = tiers[i - 1], tiers[i]

        # A ORDEM DESTAS DUAS VERIFICAÇÕES IMPORTA: se a ordenação estiver errada, a
        # divisibilidade também estará, e a mensagem sobre divisibilidade ("60s não é
        # divisível por 300s") confunde em vez de ajudar. A verificação mais fundamental
        # vem primeiro.
        if cur.seconds_per_point <= prev.seconds_per_point:
            raise SeriesError(
                f"tier {i}: os tiers devem ir do de MAIOR resolução para o de MENOR "
                f"(R6); {cur.seconds_per_point}s não é mais grosseiro que "
                f"{prev.seconds_per_point}s do tier {i - 1}"
            )

        # R6, regra literal: a precisão do arquivo de retenção mais longa deve ser
        # divisível pela precisão do arquivo imediatamente inferior. (I3)
        if cur.seconds_per_point % prev.seconds_per_point != 0:
            raise SeriesError(
                f"tier {i}: resolução {cur.seconds_per_point}s não é divisível por "
                f"{prev.seconds_per_point}s do tier {i - 1} "
                f"({cur.seconds_per_point}/{prev.seconds_per_point} = "
                f"{cur.seconds_per_point / prev.seconds_per_point:.2f}). Regra de R6"
            )

        # D2 de V(2): `average` não é associativo sob re-agregação, os outros quatro são.
        # Um tier só pode ser alimentado por um tier `average` se esse for o cru.
        if prev.aggregation not in REAGGREGABLE and i - 1 != 0:
            raise SeriesError(
                f"tier {i} seria derivado do tier {i - 1}, cuja agregação é "
                f"'{prev.aggregation}', que não é associativa sob re-agregação. "
                f"Use uma de {sorted(REAGGREGABLE)} nos tiers intermediários, ou "
                f"derive '{prev.aggregation}' direto do cru (tier 0)"
            )

        # I7 / R9: se a retenção do nível de origem for menor que a idade mínima para
        # derivar o nível seguinte, o dado é apagado ANTES de poder ser derivado —
        # perda silenciosa. É a regra de bolso do Thanos, escrita como código.
        needed = cur.min_age_seconds + cur.seconds_per_point
        if prev.retention_seconds < needed:
            raise SeriesError(
                f"tier {i - 1} retém {prev.retention_seconds}s, mas derivar o tier {i} "
                f"exige que o dado sobreviva {needed}s "
                f"(min_age {cur.min_age_seconds}s + resolução {cur.seconds_per_point}s). "
                f"Como está, o dado seria apagado antes de ser agregado: perda "
                f"silenciosa (invariante I7, armadilha documentada em R9)"
            )


def plan(
    tiers: list[TierSpec],
    derived_through: dict[int, int | None],
    now: int,
) -> RetentionPlan:
    """Computa o que derivar e o que expirar. Não toca disco.

    `derived_through[i]` é o ts do ponto mais recente que JÁ existe no tier i, ou None se
    o tier está vazio. Vem do próprio dado (E3), não de estado persistido.

    Intervalos são SEMIABERTOS [t_from, t_to) e `now` é truncado para a resolução do tier
    de destino — sem isso, um ponto na fronteira entraria e sairia conforme o relógio
    (achado CTL-02).
    """
    validate(tiers)
    derive: list[tuple[int, int, int, int]] = []
    expire: list[tuple[int, int]] = []

    for dst in range(1, len(tiers)):
        spec = tiers[dst]
        src = dst - 1
        # Só derivamos o que já é velho o bastante (min_age de R9) e completo.
        horizon = align_down(now - spec.min_age_seconds, spec.seconds_per_point)
        have = derived_through.get(dst)
        if have is None:
            # Tier vazio: começar no mais antigo que a origem ainda pode ter.
            t_from = align_down(
                now - tiers[src].retention_seconds, spec.seconds_per_point
            )
        else:
            # A janela do último ponto derivado já está fechada: começar na seguinte.
            t_from = align_down(have, spec.seconds_per_point) + spec.seconds_per_point
        if t_from < horizon:
            derive.append((src, dst, t_from, horizon))

    for i, spec in enumerate(tiers):
        # LIN-06: a retenção conta a partir de floor(now), não do ponto mais novo.
        before = align_down(now, spec.seconds_per_point) - spec.retention_seconds
        expire.append((i, before))

    return RetentionPlan(derive=derive, expire=expire, now_used=now)


def default_tiers(raw_seconds_per_point: int = 60) -> list[TierSpec]:
    """Default: DOIS tiers — cru → 5 min. Divisibilidade 300/60 = 5 (R6).

    Idade mínima do tier de 5 min: 40 h, o gatilho publicado em R9. A retenção do cru
    (15 d) satisfaz I7 com folga (precisa de 40 h + 5 min).

    POR QUE NÃO TRÊS TIERS NO DEFAULT: um terceiro tier de 1 h seria derivado do de
    5 min, e com `average` nos dois isso viola D2 — `average` não é associativo sob
    re-agregação. Um default que a própria `validate()` recusa é pior que um default
    modesto. Para três níveis, escolha conscientemente uma agregação associativa nos
    intermediários, p.ex.:

        --tiers "60:15d:average,300:90d:max:0.5:40h,3600:730d:max:0.5:10d"

    ou derive cada nível do cru configurando um acervo por resolução.
    """
    return [
        TierSpec(
            raw_seconds_per_point, retention_seconds=15 * 86400, aggregation="average"
        ),
        TierSpec(
            300,
            retention_seconds=90 * 86400,
            aggregation="average",
            min_age_seconds=40 * 3600,
        ),
    ]
