"""M-10 dataset-gen — os perfis de ground truth, determinísticos por seed.

Fonte: specs/datasets/perfis-de-serie.md. Os quatro primeiros perfis reproduzem a sondagem
da Fase 0 (com `seed=7` e N=7200 dão 0,33 / 2,67 / 6,41 / 6,63 B/ponto), e os três últimos
existem para exercitar caminhos que dado bonito não exercita.

SÓ STDLIB (achados MEC-03/ASM-05): `numpy` foi removido do projeto porque troca de versão
muda o gerador, muda o ground truth e muda o resultado de CA-4 sem que nada no produto mude.
`random.Random(seed)` da stdlib é estável para os métodos usados aqui.
"""

from __future__ import annotations

import random
import struct

from .series import Point, SeriesError

PROFILES = (
    "gauge-stable",
    "counter",
    "temp-1dec",
    "float-noise",
    "jitter",
    "gaps",
    "ieee-edge",
)

BASE_TS = 1786464000  # alinhado a 7200: base de chunk válida

# Casos-limite de IEEE-754 que CA-1 exige. A ordem importa: `-inf` seguido de subnormal
# produz XOR com bit 63 e bit 0 setados ⇒ comprimento significativo 64, que é a armadilha
# NOTA D do port (o campo de comprimento tem 6 bits).
IEEE_EDGE = (
    0.0,
    -0.0,
    1.0,
    -1.0,
    float("inf"),
    float("-inf"),
    5e-324,  # menor subnormal positivo
    1e308,
    2.0**53 + 1,  # limite de inteiro exato em double
    struct.unpack(">d", struct.pack(">Q", 0x7FF8000000000001))[0],  # NaN com payload
    struct.unpack(">d", struct.pack(">Q", 0x8000000000000001))[0],  # -subnormal
)


def generate(profile: str, n: int, seed: int, step: int = 60, base_ts: int = BASE_TS):
    """Gera `n` pontos do perfil. Gerador: não materializa a série."""
    if profile not in PROFILES:
        raise SeriesError(f"perfil {profile!r} desconhecido; use um de {list(PROFILES)}")
    if n <= 0:
        raise SeriesError("n deve ser > 0")
    rnd = random.Random(seed)

    if profile == "ieee-edge":
        for i, v in enumerate(IEEE_EDGE[: n if n < len(IEEE_EDGE) else len(IEEE_EDGE)]):
            yield Point(base_ts + i * step, v)
        return

    if profile == "jitter":
        # Exercita mais de um bucket de delta-of-delta: sem jitter, 96% dos ts custam 1 bit.
        # `max(1, ...)` garante I2 (estritamente crescente) para QUALQUER step — com
        # step=1 o jitter de -1 zeraria o delta e produziria ts duplicado. O gerador tem
        # de garantir a invariante que ele mesmo alimenta.
        ts = base_ts
        for i in range(n):
            yield Point(ts, float(rnd.choice([40, 40, 40, 41, 40])))
            ts += max(1, step + rnd.choice([-1, 0, 0, 0, 1]))
        return

    if profile == "gaps":
        # R1 §4.1.1 cita literalmente: deltas 60,60,121,59 ⇒ D = 0, 61, -62.
        ts = base_ts
        for i in range(n):
            yield Point(ts, float(rnd.choice([40, 41])))
            ts += step * (2 if i % 97 == 96 else 1)
        return

    for i in range(n):
        ts = base_ts + i * step
        if profile == "gauge-stable":
            v = float(rnd.choice([40, 40, 40, 41, 40]))
        elif profile == "counter":
            v = float(1000 * i)
        elif profile == "temp-1dec":
            v = round(20 + 3 * rnd.random(), 1)
        else:  # float-noise
            v = 20 + 3 * rnd.random()
        yield Point(ts, v)


def describe(profile: str) -> str:
    return {
        "gauge-stable": "gauge inteiro estável — melhor caso, exercita xor == 0",
        "counter": "contador monotônico — ramo '10' com trailing == 0",
        "temp-1dec": "temperatura com 1 decimal",
        "float-noise": "float de alta precisão — pior caso de razão",
        "jitter": "jitter de ±1 s — exercita os 4 buckets de delta-of-delta",
        "gaps": "pontos faltando — o exemplo de R1 §4.1.1 (D = 0, 61, -62)",
        "ieee-edge": "casos-limite IEEE-754 obrigatórios de CA-1",
    }[profile]
