"""M-06 store-port — o CONTRATO de armazenamento, com COMPORTAMENTO especificado.

A lição da Fase 2: declarar CAPACIDADES (V1) não removeu a ambiguidade das OPERAÇÕES.
V(2)/V(3) fecham cada uma. Estas regras valem para TODA implementação de `Store`:

  1. `read(t_from, t_to)` é SEMIABERTO: [t_from, t_to).                        (LIN-03)
  2. Timestamp DUPLICADO é rejeitado. Nenhuma implementação sobrescreve.       (LIN-02)
  3. Timestamp fora da faixa representável é rejeitado.                        (MIG-02)
  4. Se `aligned_writes_required`, ts desalinhado é REJEITADO — nenhuma
     implementação quantiza em silêncio. Alinhado = `ts % spp == 0`, época Unix. (LIN-01/LIN-07)
  5. Nenhum `get(ts)`: o contrato só expõe iteração sequencial, porque F2 não pode
     honrar acesso aleatório (o estado do decodificador exige leitura do chunk).
  6. `expire` é idempotente e devolve unidades explícitas.                     (LIN-04/LIN-08)
  7. `derived_through` é DERIVADO do dado, nunca lido de estado persistido.     (E3)

Também mora aqui o núcleo compartilhado: escrita atômica, validação de caminho e a regra
de compatibilidade entre formatos (que voltou para cá — achado ARQ-04).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from .series import ArchiveMeta, Point, SeriesError, TierSpec, validate_series_name

META_NAME = "meta.json"


@dataclass(frozen=True)
class Capabilities:
    mutable_slots: bool
    min_ts: int
    max_ts: int
    aligned_writes_required: bool


@dataclass
class WriteReport:
    written: int = 0
    rejected: int = 0
    # motivo -> contagem: "unaligned" | "duplicate" | "out_of_range" | "late" | "unordered"
    reasons: dict[str, int] = field(default_factory=dict)
    bytes_written: int = 0  # REG-02: sem isto, CA-4 (razão de compressão) não é computável

    def reject(self, reason: str, n: int = 1) -> None:
        self.rejected += n
        self.reasons[reason] = self.reasons.get(reason, 0) + n

    def as_dict(self) -> dict:
        return {
            "written": self.written,
            "rejected": self.rejected,
            "reasons": self.reasons,
            "bytes_written": self.bytes_written,
        }


@dataclass
class ExpireReport:
    points_removed: int = 0
    blocks_removed: int = 0
    # I5: a fronteira REAL do descarte. Para F2 é alinhada ao bloco, e o contrato diz isso.
    effective_before_ts: int = 0

    def as_dict(self) -> dict:
        return {
            "points_removed": self.points_removed,
            "blocks_removed": self.blocks_removed,
            "effective_before_ts": self.effective_before_ts,
        }


@dataclass(frozen=True)
class LossRisk:
    kind: str  # "ts_out_of_range" | "alignment_required" | "slot_collision"
    detail: str
    affected: int


class Store(Protocol):
    """A porta. Duas implementações; um contrato com comportamento definido."""

    meta: ArchiveMeta
    root: Path

    def capabilities(self) -> Capabilities: ...

    def write(self, tier: int, points: Iterable[Point]) -> WriteReport: ...

    def read(self, tier: int, t_from: int, t_to: int) -> Iterator[Point]: ...

    def expire(self, tier: int, before_ts: int) -> ExpireReport: ...

    def derived_through(self, tier: int) -> int | None: ...

    def size_bytes(self, tier: int) -> int: ...


# --- Núcleo compartilhado --------------------------------------------------------------


class OnReject:
    """UX-07: o operador decide antes de metade estar dentro. `abort` é o default."""

    ABORT = "abort"
    SKIP = "skip"


def atomic_write(path: Path, data: bytes) -> None:
    """Escreve tudo ou nada.

    O temporário nasce NO DIRETÓRIO DE DESTINO (achado ASM-07): `os.replace` entre
    sistemas de arquivos diferentes falharia com EXDEV, e a atomicidade prometida
    simplesmente não existiria.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + ".tmp")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atômico dentro do mesmo diretório


def acervo_path(base: Path, series_name: str) -> Path:
    """SEC-01: o nome é validado e usado como UM componente, nunca concatenado como caminho."""
    validate_series_name(series_name)
    return Path(base) / f"acervo-{series_name}"


def write_meta(root: Path, meta: ArchiveMeta) -> None:
    atomic_write(
        Path(root) / META_NAME,
        json.dumps(meta.as_dict(), ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        ),
    )


def read_meta(root: Path) -> ArchiveMeta:
    p = Path(root) / META_NAME
    if not p.exists():
        raise SeriesError(f"{p} não existe: este diretório não é um acervo TSZ")
    return ArchiveMeta.from_dict(json.loads(p.read_text(encoding="utf-8")))


def tier_dir(root: Path, tier: int) -> Path:
    return Path(root) / f"tier-{tier}"


def check_compatibility(
    src: Capabilities,
    dst: Capabilities,
    tiers: list[TierSpec],
    sample_min_ts: int | None,
    sample_max_ts: int | None,
    unaligned_count: int,
) -> list[LossRisk]:
    """Compara capacidades CONTRA OS DADOS, não contra uma flag (achado MIG-02).

    Em V(1) o precheck abortava toda migração F2→F1 porque F1 tem 32 bits de timestamp —
    inclusive quando os dados caberiam perfeitamente. Aqui só é risco se houver dado que
    de fato não cabe.
    """
    risks: list[LossRisk] = []
    if sample_min_ts is not None and sample_min_ts < dst.min_ts:
        risks.append(
            LossRisk(
                "ts_out_of_range",
                f"ts mínimo {sample_min_ts} é menor que o mínimo representável do "
                f"destino ({dst.min_ts})",
                1,
            )
        )
    if sample_max_ts is not None and sample_max_ts > dst.max_ts:
        risks.append(
            LossRisk(
                "ts_out_of_range",
                f"ts máximo {sample_max_ts} excede o máximo representável do destino "
                f"({dst.max_ts}) — o limite de 2106 do timestamp de 4 bytes",
                1,
            )
        )
    if dst.aligned_writes_required and unaligned_count:
        risks.append(
            LossRisk(
                "alignment_required",
                f"{unaligned_count} ponto(s) não alinhado(s) à resolução do tier; o "
                f"destino exige alinhamento e NÃO quantiza",
                unaligned_count,
            )
        )
    return risks
