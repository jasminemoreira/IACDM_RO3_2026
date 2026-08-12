"""M-07 store-f1 — Data Mapper do formato de slot fixo. Byte-exato a R6 (Whisper).

Fonte: specs/technical/formatos-armazenamento.md §F1 e R6.

  Metadata     '>2LfL'  = 16 B : aggregationType, maxRetention, xFilesFactor, archiveCount
  ArchiveInfo  '>3L'    = 12 B : offset, secondsPerPoint, points
  Point        '>Ld'    = 12 B : timestamp (4 B), value (8 B)

Os metadados do ACERVO (format_version, tiers, etc.) moram no sidecar meta.json, fora
daqui (decisão E1) — é isso que permite este arquivo ser byte-exato a R6, que V(2) havia
quebrado sem perceber (achado IMP-06).

VALIDADE-POR-TIMESTAMP (decisão E4, achado ASM-08): um slot só é válido se o timestamp
gravado nele for igual ao timestamp esperado daquela posição. Ao dar a volta, o slot antigo
passa a ter timestamp que não corresponde e portanto JÁ ESTÁ EXPIRADO por definição —
staleness e expiração são o MESMO mecanismo, não dois. É como o Whisper funciona.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Iterable, Iterator

from .series import (
    AGGREGATION_CODE,
    ArchiveMeta,
    Point,
    SeriesError,
    TierSpec,
    is_aligned,
)
from .store_port import (
    Capabilities,
    ExpireReport,
    WriteReport,
    atomic_write,
    tier_dir,
)

METADATA_FMT = ">2LfL"
METADATA_SIZE = struct.calcsize(METADATA_FMT)  # 16 (4+4+4+4), não 20
ARCHIVEINFO_FMT = ">3L"
ARCHIVEINFO_SIZE = struct.calcsize(ARCHIVEINFO_FMT)  # 12
POINT_FMT = ">Ld"
POINT_SIZE = struct.calcsize(POINT_FMT)  # 12

DATA_NAME = "data.f1"

TS_MIN = 0
TS_MAX = 2**32 - 1  # 4 bytes sem sinal ⇒ estoura em 2106. Limitação real do formato.


class StoreF1:
    def __init__(self, root: Path, meta: ArchiveMeta) -> None:
        self.root = Path(root)
        self.meta = meta

    # --- contrato ----------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return Capabilities(
            mutable_slots=True,
            min_ts=TS_MIN,
            max_ts=TS_MAX,
            aligned_writes_required=True,
        )

    def create(self) -> None:
        for i, spec in enumerate(self.meta.tiers):
            path = self._data_path(i)
            if path.exists():
                continue
            atomic_write(path, self._empty_file(spec))

    def write(self, tier: int, points: Iterable[Point]) -> WriteReport:
        spec = self._spec(tier)
        report = WriteReport()
        path = self._data_path(tier)
        if not path.exists():
            atomic_write(path, self._empty_file(spec))
        blob = bytearray(path.read_bytes())
        self._check_header(blob, spec)
        base = METADATA_SIZE + ARCHIVEINFO_SIZE
        seen: set[int] = set()
        prev_ts: int | None = None

        for p in points:
            if not TS_MIN <= p.ts <= TS_MAX:
                report.reject("out_of_range")
                continue
            if not is_aligned(p.ts, spec.seconds_per_point):
                # LIN-01: rejeita, NÃO quantiza.
                report.reject("unaligned")
                continue
            if prev_ts is not None and p.ts <= prev_ts:
                report.reject("unordered")
                continue
            slot = (p.ts // spec.seconds_per_point) % spec.points
            offset = base + slot * POINT_SIZE
            stored_ts, _ = struct.unpack(POINT_FMT, blob[offset : offset + POINT_SIZE])
            # LIN-02: duplicado é ERRO, não sobrescrita — mesmo em formato mutável.
            if stored_ts == p.ts or p.ts in seen:
                report.reject("duplicate")
                continue
            struct.pack_into(POINT_FMT, blob, offset, p.ts, p.value)
            seen.add(p.ts)
            prev_ts = p.ts
            report.written += 1

        atomic_write(path, bytes(blob))
        report.bytes_written = len(blob)
        return report

    def read(self, tier: int, t_from: int, t_to: int) -> Iterator[Point]:
        """SEMIABERTO [t_from, t_to). Ordena por timestamp: o arquivo é round-robin."""
        spec = self._spec(tier)
        path = self._data_path(tier)
        if not path.exists():
            return iter(())
        blob = path.read_bytes()
        self._check_header(blob, spec)
        base = METADATA_SIZE + ARCHIVEINFO_SIZE
        found: list[Point] = []
        for slot in range(spec.points):
            offset = base + slot * POINT_SIZE
            ts, value = struct.unpack(POINT_FMT, blob[offset : offset + POINT_SIZE])
            if not self._slot_valid(ts, slot, spec):
                continue
            if t_from <= ts < t_to:
                found.append(Point(ts, value))
        found.sort(key=lambda p: p.ts)
        return iter(found)

    def expire(self, tier: int, before_ts: int) -> ExpireReport:
        """E4: em F1 a expiração já acontece pela validade-por-timestamp.

        Este método é um no-op que REPORTA a fronteira efetiva, calculada do tamanho do
        arquivo — a retenção real de F1 é `points * seconds_per_point`, independente do
        `before_ts` pedido. É trivialmente idempotente (achado LIN-08).
        """
        spec = self._spec(tier)
        newest = self.derived_through(tier)
        if newest is None:
            return ExpireReport(0, 0, before_ts)
        # A janela que o arquivo consegue guardar termina no ponto mais novo.
        window_start = newest - spec.points * spec.seconds_per_point + spec.seconds_per_point
        effective = max(before_ts, window_start)
        return ExpireReport(points_removed=0, blocks_removed=0, effective_before_ts=effective)

    def derived_through(self, tier: int) -> int | None:
        """E3: derivado do dado — o timestamp do slot VÁLIDO mais recente."""
        spec = self._spec(tier)
        path = self._data_path(tier)
        if not path.exists():
            return None
        blob = path.read_bytes()
        self._check_header(blob, spec)
        base = METADATA_SIZE + ARCHIVEINFO_SIZE
        newest: int | None = None
        for slot in range(spec.points):
            offset = base + slot * POINT_SIZE
            (ts,) = struct.unpack(">L", blob[offset : offset + 4])
            if self._slot_valid(ts, slot, spec) and (newest is None or ts > newest):
                newest = ts
        return newest

    def size_bytes(self, tier: int) -> int:
        path = self._data_path(tier)
        return path.stat().st_size if path.exists() else 0

    # --- internos ----------------------------------------------------------------------

    def _spec(self, tier: int) -> TierSpec:
        try:
            return self.meta.tiers[tier]
        except IndexError:
            raise SeriesError(f"tier {tier} não existe neste acervo") from None

    def _data_path(self, tier: int) -> Path:
        return tier_dir(self.root, tier) / DATA_NAME

    @staticmethod
    def _slot_valid(stored_ts: int, slot: int, spec: TierSpec) -> bool:
        """E4: válido só se o ts gravado corresponde à posição que ocupa."""
        if stored_ts == 0:
            return False
        return (stored_ts // spec.seconds_per_point) % spec.points == slot and is_aligned(
            stored_ts, spec.seconds_per_point
        )

    @staticmethod
    def _empty_file(spec: TierSpec) -> bytes:
        header = struct.pack(
            METADATA_FMT,
            AGGREGATION_CODE[spec.aggregation],
            spec.retention_seconds,
            spec.x_files_factor,
            1,  # archiveCount: um archive por arquivo, um arquivo por tier
        )
        info = struct.pack(
            ARCHIVEINFO_FMT,
            METADATA_SIZE + ARCHIVEINFO_SIZE,
            spec.seconds_per_point,
            spec.points,
        )
        return header + info + b"\x00" * (POINT_SIZE * spec.points)

    @staticmethod
    def _check_header(blob: bytes | bytearray, spec: TierSpec) -> None:
        """SEC-02: o leitor NÃO confia no header — valida contra o tamanho real do arquivo."""
        if len(blob) < METADATA_SIZE + ARCHIVEINFO_SIZE:
            raise SeriesError("arquivo F1 truncado: menor que o próprio cabeçalho")
        _, _, _, archive_count = struct.unpack(METADATA_FMT, blob[:METADATA_SIZE])
        if archive_count != 1:
            raise SeriesError(
                f"arquivo F1 declara archiveCount={archive_count}; este mapper usa um "
                "archive por arquivo (um arquivo por tier)"
            )
        offset, spp, points = struct.unpack(
            ARCHIVEINFO_FMT, blob[METADATA_SIZE : METADATA_SIZE + ARCHIVEINFO_SIZE]
        )
        expected = METADATA_SIZE + ARCHIVEINFO_SIZE + POINT_SIZE * points
        if len(blob) != expected:
            raise SeriesError(
                f"arquivo F1 declara {points} pontos (={expected} bytes) mas tem "
                f"{len(blob)} bytes: cabeçalho inconsistente ou arquivo corrompido"
            )
        if spp != spec.seconds_per_point or points != spec.points:
            raise SeriesError(
                f"arquivo F1 tem resolução {spp}s/{points} pontos, mas o meta.json diz "
                f"{spec.seconds_per_point}s/{spec.points}: a configuração de tiers mudou "
                "depois de o acervo existir. Recrie o acervo ou restaure a config"
            )
