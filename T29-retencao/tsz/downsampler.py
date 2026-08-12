"""M-05 downsampler — agrega um stream de pontos para uma resolução menor.

Fonte: R6 (os 5 métodos de agregação e o xFilesFactor) e R9 (o princípio de preservar
informação re-agregável).

Um tier guarda UM valor por ponto, com o método declarado em `TierSpec.aggregation`
(decisão D1 de V(2)): o tipo `Aggregate(min,max,sum,count)` não existe. Isso é a leitura
literal de R6 — o Whisper guarda um valor por slot e o método no header; os quatro agregados
são propriedade do formato do Thanos, não do domínio (achado SCI-02).

REGRA DO xFilesFactor (achado SCI-04, declarada porque R6/R9 não a formalizam):
o `xff` é aplicado SÓ contra a contagem nominal do tier de origem imediato, e o estado
"indefinido" NÃO propaga — um ponto derivado existe ou não existe. É o comportamento do
Whisper. Com jitter no cru a contagem nominal é uma aproximação, e isso está dito.
"""

from __future__ import annotations

from .series import AGGREGATIONS, Point, SeriesError, align_down

# Strategy: os 5 métodos de R6. `average` é o default do Whisper.
_STRATEGIES = {
    "average": lambda vs: sum(vs) / len(vs),
    "sum": sum,
    "last": lambda vs: vs[-1],
    "max": max,
    "min": min,
}
assert set(_STRATEGIES) == set(AGGREGATIONS)


def aggregate(points, src_res: int, dst_res: int, fn: str, xff: float):
    """Gera pontos alinhados a `dst_res`. Streaming: não materializa a série.

    Assume a entrada ordenada (I2, garantida pelo caminho de escrita da porta).
    """
    if fn not in _STRATEGIES:
        raise SeriesError(f"agregação {fn!r} desconhecida; use uma de {sorted(_STRATEGIES)}")
    if dst_res % src_res != 0:
        raise SeriesError(
            f"{dst_res}s não é divisível por {src_res}s: a regra de divisibilidade de R6 "
            "vale também aqui"
        )
    if not 0.0 <= xff <= 1.0:
        raise SeriesError("xff deve estar em [0.0, 1.0]")

    strategy = _STRATEGIES[fn]
    nominal = dst_res // src_res  # quantos pontos DEVERIAM existir na janela
    window: int | None = None
    bucket: list[float] = []

    def emit(w: int, values: list[float]):
        # I6: agregado é indefinido se a fração de pontos definidos < xff.
        # "Indefinido" aqui significa NÃO EMITIDO — não existe ponto marcado como nulo.
        if values and (len(values) / nominal) >= xff:
            return Point(w, float(strategy(values)))
        return None

    for p in points:
        w = align_down(p.ts, dst_res)
        if window is None:
            window = w
        elif w != window:
            out = emit(window, bucket)
            if out is not None:
                yield out
            window, bucket = w, []
        bucket.append(p.value)

    if window is not None:
        out = emit(window, bucket)
        if out is not None:
            yield out
