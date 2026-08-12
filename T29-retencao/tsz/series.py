"""M-03 series — tipos que atravessam interfaces e invariantes do domínio.

Fonte: specs/models/tipos.md e specs/technical/architecture.md §V(3).
Nenhum I/O. `TierState` não existe: em V(3) a marca d'água é DERIVADA do dado (decisão E3).
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

# --- Agregações: os 5 métodos de R6 (Whisper), com os códigos do próprio formato -------
AGGREGATIONS = ("average", "sum", "last", "max", "min")

# R6: aggregationType no Metadata é 1..5 nesta ordem.
AGGREGATION_CODE = {name: i + 1 for i, name in enumerate(AGGREGATIONS)}
AGGREGATION_NAME = {code: name for name, code in AGGREGATION_CODE.items()}

# Somente estes são associativos sob re-agregação (decisão D2 de V(2)):
# min(min(a),min(b)) == min(a∪b); idem max; sum é somável; last de lasts é o last.
# `average` NÃO é — por isso R9 precisa guardar sum+count.
REAGGREGABLE = frozenset({"min", "max", "sum", "last"})

SERIES_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")  # SEC-01: nunca concatenado como caminho

FORMAT_VERSION = 1


class SeriesError(Exception):
    """Erro de domínio. O CLI o converte em mensagem para o operador."""


# --- Tipos ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Point:
    """Um ponto. `value` é IEEE-754 binary64 e é preservado bit a bit (I1)."""

    ts: int
    value: float

    def same_value_bits(self, other: "Point") -> bool:
        """Compara valores por BYTES, nunca por ==.

        Armadilha P2: `nan != nan`, e `0.0 == -0.0` apesar de terem bits diferentes.
        Todo teste de round-trip tem de passar por aqui.
        """
        return struct.pack(">d", self.value) == struct.pack(">d", other.value)


@dataclass(frozen=True)
class TierSpec:
    seconds_per_point: int
    retention_seconds: int
    aggregation: str = "average"
    x_files_factor: float = 0.5  # R6/R7: default 0.5
    min_age_seconds: int = 0

    def __post_init__(self) -> None:
        if self.seconds_per_point <= 0:
            raise SeriesError("seconds_per_point deve ser > 0")
        if self.retention_seconds <= 0:
            raise SeriesError("retention_seconds deve ser > 0")
        if self.aggregation not in AGGREGATIONS:
            raise SeriesError(
                f"aggregation {self.aggregation!r} desconhecida; "
                f"use uma de {', '.join(AGGREGATIONS)} (R6)"
            )
        if not 0.0 <= self.x_files_factor <= 1.0:
            raise SeriesError("x_files_factor deve estar em [0.0, 1.0]")
        if self.min_age_seconds < 0:
            raise SeriesError("min_age_seconds não pode ser negativo")

    @property
    def points(self) -> int:
        """Quantos pontos o tier guarda. Define o tamanho do arquivo em F1."""
        return self.retention_seconds // self.seconds_per_point

    def as_dict(self) -> dict:
        return {
            "seconds_per_point": self.seconds_per_point,
            "retention_seconds": self.retention_seconds,
            "aggregation": self.aggregation,
            "x_files_factor": self.x_files_factor,
            "min_age_seconds": self.min_age_seconds,
        }

    @staticmethod
    def from_dict(d: dict) -> "TierSpec":
        return TierSpec(
            seconds_per_point=int(d["seconds_per_point"]),
            retention_seconds=int(d["retention_seconds"]),
            aggregation=str(d.get("aggregation", "average")),
            x_files_factor=float(d.get("x_files_factor", 0.5)),
            min_age_seconds=int(d.get("min_age_seconds", 0)),
        )


@dataclass
class ArchiveMeta:
    """Metadados do acervo. Vive em meta.json, FORA do arquivo de dados (decisão E1).

    É por isso que o arquivo de dados de F1 pode ser byte-exato a R6: estes 8 campos
    não precisam caber nos 20 bytes do Metadata do Whisper (achado IMP-06).
    """

    series_name: str
    fmt: str  # "f1" | "f2"
    tiers: list[TierSpec]
    block_seconds: int = 7200
    created_at: int = 0
    writer_version: str = "0.1.0"
    format_version: int = FORMAT_VERSION
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        validate_series_name(self.series_name)
        if self.fmt not in ("f1", "f2"):
            raise SeriesError(f"formato {self.fmt!r} desconhecido; use f1 ou f2")
        if not self.tiers:
            raise SeriesError("um acervo precisa de pelo menos um tier")

    def as_dict(self) -> dict:
        return {
            "format_version": self.format_version,
            "format": self.fmt,
            "block_seconds": self.block_seconds,
            "created_at": self.created_at,
            "writer_version": self.writer_version,
            "series_name": self.series_name,
            "tiers": [t.as_dict() for t in self.tiers],
            "superseded_by": self.superseded_by,
        }

    @staticmethod
    def from_dict(d: dict) -> "ArchiveMeta":
        # MIG-05: recusar ler versão MAIOR que a do escritor. Igual aceita.
        version = int(d.get("format_version", 1))
        if version > FORMAT_VERSION:
            raise SeriesError(
                f"acervo em format_version {version}, este programa lê até "
                f"{FORMAT_VERSION}. Atualize o programa; não há migração de downgrade."
            )
        # MEC-06: block_seconds vem de dado externo — validar NA CARGA, não ao decodificar.
        block_seconds = int(d.get("block_seconds", 7200))
        validate_block_seconds(block_seconds)
        return ArchiveMeta(
            series_name=str(d["series_name"]),
            fmt=str(d["format"]),
            tiers=[TierSpec.from_dict(t) for t in d["tiers"]],
            block_seconds=block_seconds,
            created_at=int(d.get("created_at", 0)),
            writer_version=str(d.get("writer_version", "0.1.0")),
            format_version=version,
            superseded_by=d.get("superseded_by"),
        )


@dataclass(frozen=True)
class RetentionPlan:
    # (tier_src, tier_dst, t_from, t_to) — intervalo SEMIABERTO [t_from, t_to)
    derive: list[tuple[int, int, int, int]] = field(default_factory=list)
    expire: list[tuple[int, int]] = field(default_factory=list)  # (tier, before_ts)
    now_used: int = 0

    def is_empty(self) -> bool:
        return not self.derive and not self.expire


# --- Alinhamento (achado LIN-07: "alinhado" precisava de definição) -------------------

BLOCK_SECONDS_DEFAULT = 7200  # R1 Fig. 6: 2h dá 1,37 B/ponto; acima disso, retorno decrescente
MAX_BLOCK_SECONDS = 14400  # R1 nota 1: o primeiro delta tem 14 bits ⇒ 16.384 s > 4h


def validate_block_seconds(block_seconds: int) -> None:
    if block_seconds <= 0:
        raise SeriesError("block_seconds deve ser > 0")
    if block_seconds > MAX_BLOCK_SECONDS:
        raise SeriesError(
            f"block_seconds={block_seconds} excede {MAX_BLOCK_SECONDS}s: o primeiro "
            "delta do bloco tem 14 bits (2^14 = 16.384 s), R1 nota de rodapé 1"
        )


def is_aligned(ts: int, seconds_per_point: int) -> bool:
    """LIN-07: alinhado é `ts % spp == 0`, na época Unix. É a definição do Whisper."""
    return ts % seconds_per_point == 0


def align_down(ts: int, seconds_per_point: int) -> int:
    """O `interval` do Whisper: `ts - (ts % secondsPerPoint)`.

    Funciona para ts negativo porque `%` em Python já arredonda para baixo.
    """
    return ts - (ts % seconds_per_point)


def validate_series_name(name: str) -> None:
    """SEC-01: o nome vira componente de caminho; sem separadores, sem `.` nem `..`.

    O nome sempre entra prefixado (`acervo-<nome>`), então `..` não causaria travessia
    de verdade — mas aceitá-lo é higiene ruim e um dia o prefixo muda.
    """
    if not SERIES_NAME_RE.match(name or "") or name in (".", ".."):
        raise SeriesError(
            f"nome de série inválido: {name!r}. Use apenas letras, dígitos, ponto, "
            "hífen e sublinhado (sem barras, e nem '.' nem '..' sozinhos)"
        )


# --- Invariantes -----------------------------------------------------------------------


def validate_stream(points, expect_aligned_to: int | None = None):
    """I2: timestamps estritamente crescentes. Gerador, para não materializar a série.

    Fora de ordem é ERRO, não é reordenado (escopo negativo de V(1)): reordenar
    esconderia um problema do produtor do dado.
    """
    prev = None
    for p in points:
        if prev is not None and p.ts <= prev:
            raise SeriesError(
                f"timestamps devem ser estritamente crescentes: {p.ts} veio depois de {prev}"
            )
        if expect_aligned_to is not None and not is_aligned(p.ts, expect_aligned_to):
            raise SeriesError(
                f"ts {p.ts} não está alinhado a {expect_aligned_to}s "
                f"(esperado {align_down(p.ts, expect_aligned_to)})"
            )
        prev = p.ts
        yield p
