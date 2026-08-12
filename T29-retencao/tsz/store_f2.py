"""M-08 store-f2 — Data Mapper do bitstream Gorilla: um ARQUIVO POR CHUNK.

Decisão E2 de V(3). Antes (V2) o tier era um arquivo único e `atomic_write` reescrevia o
acervo inteiro a cada append — O(acervo) por operação e O(N²) ao longo da vida, num formato
cuja razão de ser é ser append-only (achados PRF-04/SUS-05).

  tier-N/
  ├── 1786464000.chunk
  └── 1786471200.chunk

Consequências, todas de graça:
  · append custa O(chunk), não O(acervo);
  · o NOME DO ARQUIVO é o índice de salto — `read` descarta chunks sem decodificá-los
    (achado PRF-01, resolvido por DELEÇÃO do índice de prefixo que V(2) tinha inventado);
  · expirar é apagar arquivos, e a granularidade de bloco da invariante I5 fica literal;
  · varredura de integridade é iterar os arquivos e verificar o crc32 (achado OBS-05);
  · o temporário do `atomic_write` nasce no mesmo diretório ⇒ EXDEV impossível (ASM-07).

P-A12: o nome do arquivo é a única fonte de ordenação. Renomear à mão corrompe o acervo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from .gorilla_codec import Chunk
from .series import ArchiveMeta, Point, SeriesError, TierSpec
from .store_port import (
    Capabilities,
    ExpireReport,
    WriteReport,
    atomic_write,
    tier_dir,
)

CHUNK_SUFFIX = ".chunk"

TS_MIN = -(2**63)
TS_MAX = 2**63 - 1


class StoreF2:
    def __init__(self, root: Path, meta: ArchiveMeta) -> None:
        self.root = Path(root)
        self.meta = meta

    # --- contrato ----------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return Capabilities(
            mutable_slots=False,
            min_ts=TS_MIN,
            max_ts=TS_MAX,
            aligned_writes_required=False,  # F2 aceita qualquer ts monotônico
        )

    def create(self) -> None:
        for i in range(len(self.meta.tiers)):
            tier_dir(self.root, i).mkdir(parents=True, exist_ok=True)

    def write(self, tier: int, points: Iterable[Point]) -> WriteReport:
        """Escreve por STREAMING, uma janela por vez.

        A memória é O(pontos de um chunk), não O(entrada) — a premissa P-A8 exige isso, e
        a primeira versão a violava (medido: ~150 bytes/ponto, 330 MB para 2 milhões de
        pontos). Como a entrada é esperada crescente (I2), os pontos chegam janela a
        janela: acumulamos só a janela corrente e descarregamos quando ela avança.

        Entrada fora de ordem que volte a uma janela já descarregada continua CORRETA —
        o chunk daquela janela é recarregado, mesclado e reescrito. Apenas menos
        eficiente, que é o tratamento adequado para o caso anômalo.
        """
        self._spec(tier)  # valida o tier
        bs = self.meta.block_seconds
        report = WriteReport()
        window: int | None = None
        bucket: list[Point] = []

        for p in points:
            if not TS_MIN <= p.ts <= TS_MAX:
                report.reject("out_of_range")
                continue
            w = Chunk.window_of(p.ts, bs)
            if window is not None and w != window:
                self._flush(tier, window, bucket, report)
                bucket = []
            window = w
            bucket.append(p)

        if window is not None:
            self._flush(tier, window, bucket, report)
        return report

    def _flush(
        self, tier: int, base_ts: int, novos: list[Point], report: WriteReport
    ) -> None:
        """Mescla `novos` no chunk da janela e grava atomicamente."""
        merged: dict[int, Point] = {p.ts: p for p in self._load_points(tier, base_ts)}
        for p in novos:
            if p.ts in merged:
                # LIN-02: duplicado é ERRO, não sobrescrita.
                report.reject("duplicate")
                continue
            merged[p.ts] = p
            report.written += 1
        chunk = Chunk(base_ts, self.meta.block_seconds)
        for ts in sorted(merged):
            chunk.append(ts, merged[ts].value)
        blob = chunk.to_bytes()
        atomic_write(self._chunk_path(tier, base_ts), blob)
        report.bytes_written += len(blob)

    def read(self, tier: int, t_from: int, t_to: int) -> Iterator[Point]:
        """SEMIABERTO [t_from, t_to). O nome do arquivo permite pular chunks inteiros."""
        self._spec(tier)
        bs = self.meta.block_seconds
        for base_ts in self._chunk_bases(tier):
            # Índice de salto: sem decodificar nada.
            if base_ts + bs <= t_from or base_ts >= t_to:
                continue
            for p in Chunk.points_of(self._chunk_path(tier, base_ts).read_bytes()):
                if t_from <= p.ts < t_to:
                    yield p

    def expire(self, tier: int, before_ts: int) -> ExpireReport:
        """Apaga chunks cuja janela terminou antes de `before_ts`.

        I5: a granularidade é o BLOCO. `effective_before_ts` é a fronteira real do que
        sobrou — por isso a retenção efetiva excede a nominal por até uma duração de bloco,
        e o contrato reporta isso em vez de escondê-lo.
        """
        self._spec(tier)
        bs = self.meta.block_seconds
        removed_blocks = 0
        removed_points = 0
        survivors: list[int] = []
        for base_ts in self._chunk_bases(tier):
            if base_ts + bs <= before_ts:
                path = self._chunk_path(tier, base_ts)
                _, _, n_points, _, _ = Chunk.read(path.read_bytes())
                path.unlink()
                removed_blocks += 1
                removed_points += n_points
            else:
                survivors.append(base_ts)
        effective = min(survivors) if survivors else before_ts
        return ExpireReport(removed_points, removed_blocks, effective)

    def derived_through(self, tier: int) -> int | None:
        """E3: derivado do dado — o ts do último ponto do chunk mais recente."""
        self._spec(tier)
        bases = self._chunk_bases(tier)
        if not bases:
            return None
        last = None
        for p in Chunk.points_of(self._chunk_path(tier, bases[-1]).read_bytes()):
            last = p.ts
        return last

    def size_bytes(self, tier: int) -> int:
        d = tier_dir(self.root, tier)
        if not d.exists():
            return 0
        return sum(f.stat().st_size for f in d.glob(f"*{CHUNK_SUFFIX}"))

    # --- extras deste formato ----------------------------------------------------------

    def verify(self, tier: int) -> list[str]:
        """OBS-05: varredura de integridade. Devolve os problemas encontrados."""
        problems: list[str] = []
        for base_ts in self._chunk_bases(tier):
            path = self._chunk_path(tier, base_ts)
            try:
                Chunk.read(path.read_bytes())
            except SeriesError as exc:
                problems.append(f"{path.name}: {exc}")
        return problems

    def chunk_count(self, tier: int) -> int:
        return len(self._chunk_bases(tier))

    # --- internos ----------------------------------------------------------------------

    def _spec(self, tier: int) -> TierSpec:
        try:
            return self.meta.tiers[tier]
        except IndexError:
            raise SeriesError(f"tier {tier} não existe neste acervo") from None

    def _chunk_path(self, tier: int, base_ts: int) -> Path:
        return tier_dir(self.root, tier) / f"{base_ts}{CHUNK_SUFFIX}"

    def _chunk_bases(self, tier: int) -> list[int]:
        d = tier_dir(self.root, tier)
        if not d.exists():
            return []
        bases = []
        for f in d.glob(f"*{CHUNK_SUFFIX}"):
            try:
                bases.append(int(f.stem))
            except ValueError:
                raise SeriesError(
                    f"{f.name} não tem um base_ts no nome: o nome do arquivo é a única "
                    "fonte de ordenação do acervo (premissa P-A12)"
                ) from None
        return sorted(bases)

    def _load_points(self, tier: int, base_ts: int) -> list[Point]:
        path = self._chunk_path(tier, base_ts)
        if not path.exists():
            return []
        return list(Chunk.points_of(path.read_bytes()))
