"""M-09 overlap-detector — conflito de AGENDA (acepcao B).

Predicado canonico de sobreposicao, intervalos SEMIABERTOS: eventos apenas
encostados (fim de x == inicio de y) NAO se sobrepoem.

    overlap(x, y)  <=>  x.start < y.end  e  y.start < x.end

Varredura ordenada (sweep line): O(n log n) para ordenar + O(n + k) para
enumerar os k pares, exigencia VAL-3 — nunca o produto cartesiano O(n^2).
Nota de honestidade (achado SCI-02): o limite O(n log n) vale para DETECTAR;
enumerar k pares custa inevitavelmente O(k).

Modulo PURO: recebe ocorrencias ja expandidas em UTC, nao faz I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from .canonical_event import Occurrence


@dataclass(frozen=True, slots=True)
class Overlap:
    left: Occurrence
    right: Occurrence

    @property
    def minutes(self) -> int:
        start = max(self.left.start_utc, self.right.start_utc)
        end = min(self.left.end_utc, self.right.end_utc)
        return max(0, int((end - start).total_seconds() // 60))


def find_overlaps(occurrences: list[Occurrence]) -> list[Overlap]:
    ordered = sorted(occurrences, key=lambda o: (o.start_utc, o.end_utc))
    active: list[Occurrence] = []
    out: list[Overlap] = []
    for occ in ordered:
        active = [a for a in active if a.end_utc > occ.start_utc]  # expira encerrados
        for a in active:
            out.append(Overlap(a, occ))  # a.start <= occ.start e a.end > occ.start
        active.append(occ)
    return out
