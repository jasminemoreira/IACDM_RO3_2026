"""M-02 gorilla-codec — codec de R1 §4.1 + o Chunk, que é sua unidade de estado.

PORT LITERAL (S6 Tier 2). Fonte única:
  R1 = Pelkonen et al., "Gorilla: A Fast, Scalable, In-Memory Time Series Database",
       PVLDB 8(12):1816-1827, 2015 — §4.1.1 (timestamps) e §4.1.2 (valores).
Transcrição em specs/technical/codec-gorilla.md; pseudocódigo em
specs/examples/gorilla-pseudocodigo.md.

O bloco foi absorvido aqui (achado ARQ-05): `base_ts`, `prev_delta`, `prev_lead` e
`prev_trail` nascem e morrem juntos, e V(1) os fazia atravessar fronteira de módulo.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from .bitstream import BitReader, BitWriter, to_signed
from .series import (
    MAX_BLOCK_SECONDS,
    Point,
    SeriesError,
    align_down,
    validate_block_seconds,
)

# --- Parâmetros de R1 §4.1.1, itens (b)-(f). NENHUM é escolha nossa. ------------------
FIRST_DELTA_BITS = 14  # R1 nota 1: 2^14 = 16.384 s, "um pouco mais de 4 horas"

# (limite_inferior, limite_superior, prefixo, n_bits_prefixo, n_bits_payload)
# ⚠️ Faixas ASSIMÉTRICAS, exatamente como no paper: [-63, 64], não [-64, 63].
TS_BUCKETS = (
    (-63, 64, 0b10, 2, 7),
    (-255, 256, 0b110, 3, 9),
    (-2047, 2048, 0b1110, 4, 12),
)
TS_FALLBACK_PREFIX = 0b1111
TS_FALLBACK_PREFIX_BITS = 4
TS_FALLBACK_BITS = 32

VALUE_LEADING_BITS = 5  # R1 §4.1.2: até 31 zeros à esquerda
VALUE_LENGTH_BITS = 6  # R1 §4.1.2

# DECISÃO DE REPRESENTAÇÃO NOSSA, não parâmetro de R1 (registrada como diagnóstico na F5).
# O campo de comprimento tem 6 bits (0..63), mas o comprimento significativo pode ser 64:
# acontece quando o XOR tem o bit 63 E o bit 0 setados, p.ex.
#   -inf (0xFFF0000000000000) ^ 5e-324 (0x0000000000000001) = 0xFFF0000000000001
#   → lead=0, trail=0, significante=64.
# Gravar 64 em 6 bits truncaria para 0. Gravamos `significant - 1`, cobrindo 1..64 — o
# comprimento de um XOR não-zero é sempre >= 1, então 0 nunca foi valor legítimo.
# É a mesma classe de lacuna das faixas assimétricas: R1 fixa a semântica e deixa a
# codificação do campo implícita.
VALUE_LENGTH_BIAS = 1

# Escolha de ENGENHARIA, não de R1 (achado SCI-05): crc32 do zlib detecta corrupção
# ACIDENTAL. Não autentica — quem escreve recalcula o crc (achado SEC-07).
CHUNK_MAGIC = b"TSZ2"
CHUNK_HEADER = ">4sqIII"  # magic, base_ts, block_seconds, n_points, crc32
CHUNK_HEADER_SIZE = struct.calcsize(CHUNK_HEADER)


def _bits_of(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _float_of(bits: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


@dataclass
class CodecState:
    """Estado do stream. Vale por CHUNK — nunca reaproveitar entre chunks."""

    prev_ts: int = 0
    prev_delta: int = 0
    prev_bits: int = 0
    prev_lead: int | None = None  # None = ainda não houve caso '11' (ver NOTA C)
    prev_trail: int | None = None


# --- Timestamps: R1 §4.1.1 ------------------------------------------------------------


def encode_first_timestamp(w: BitWriter, st: CodecState, base_ts: int, ts: int) -> None:
    delta = ts - base_ts
    if not 0 <= delta < (1 << FIRST_DELTA_BITS):
        # ASM-03: o campo de 14 bits é sem sinal e relativo ao base do chunk.
        raise SeriesError(
            f"ts {ts} está fora da janela do chunk que começa em {base_ts}: "
            f"o primeiro delta tem {FIRST_DELTA_BITS} bits sem sinal"
        )
    w.write_bits(delta, FIRST_DELTA_BITS)
    st.prev_ts = ts
    st.prev_delta = 0  # NOTA A: R1 não declara; o 2º ponto cai no bucket de 32 bits


def encode_timestamp(w: BitWriter, st: CodecState, ts: int) -> None:
    delta = ts - st.prev_ts
    d = delta - st.prev_delta  # delta-of-delta
    if d == 0:
        w.write_bit(0)  # ~96% dos casos (R1 Fig. 3)
    else:
        for lo, hi, prefix, prefix_bits, payload_bits in TS_BUCKETS:
            if lo <= d <= hi:
                w.write_bits(prefix, prefix_bits)
                # NOTA B / armadilha P5: a faixa tem `hi - lo + 1` valores e NÃO é o
                # alcance natural do complemento de dois. Gravamos com deslocamento
                # (d - lo), que cobre exatamente [lo, hi] em `payload_bits` bits.
                w.write_bits(d - lo, payload_bits)
                break
        else:
            w.write_bits(TS_FALLBACK_PREFIX, TS_FALLBACK_PREFIX_BITS)
            w.write_bits(d, TS_FALLBACK_BITS)
    st.prev_ts = ts
    st.prev_delta = delta


def decode_first_timestamp(r: BitReader, st: CodecState, base_ts: int) -> int:
    ts = base_ts + r.read_bits(FIRST_DELTA_BITS)
    st.prev_ts = ts
    st.prev_delta = 0
    return ts


def decode_timestamp(r: BitReader, st: CodecState) -> int:
    # Os prefixos 0 / 10 / 110 / 1110 / 1111 formam código de prefixo livre.
    if r.read_bit() == 0:
        d = 0
    elif r.read_bit() == 0:
        lo, hi, _, _, payload_bits = TS_BUCKETS[0]
        d = r.read_bits(payload_bits) + lo
    elif r.read_bit() == 0:
        lo, hi, _, _, payload_bits = TS_BUCKETS[1]
        d = r.read_bits(payload_bits) + lo
    elif r.read_bit() == 0:
        lo, hi, _, _, payload_bits = TS_BUCKETS[2]
        d = r.read_bits(payload_bits) + lo
    else:
        d = to_signed(r.read_bits(TS_FALLBACK_BITS), TS_FALLBACK_BITS)
    delta = st.prev_delta + d
    ts = st.prev_ts + delta
    st.prev_ts = ts
    st.prev_delta = delta
    return ts


# --- Valores: R1 §4.1.2 ---------------------------------------------------------------


def encode_first_value(w: BitWriter, st: CodecState, value: float) -> None:
    bits = _bits_of(value)
    w.write_bits(bits, 64)  # R1: o primeiro valor vai SEM compressão
    st.prev_bits = bits
    st.prev_lead = None
    st.prev_trail = None


def encode_value(w: BitWriter, st: CodecState, value: float) -> None:
    bits = _bits_of(value)
    x = bits ^ st.prev_bits
    if x == 0:
        w.write_bit(0)  # ~51% dos casos (R1 Fig. 5)
    else:
        w.write_bit(1)
        lead = 64 - x.bit_length()
        trail = (x & -x).bit_length() - 1  # P3: x != 0 já garantido acima
        if (
            st.prev_lead is not None
            and lead >= st.prev_lead
            and trail >= st.prev_trail
        ):
            # Control '10' — cabe na janela anterior: ~30%, 26,6 bits médios.
            w.write_bit(0)
            w.write_bits(x >> st.prev_trail, 64 - st.prev_lead - st.prev_trail)
            # NOTA C: prev_lead/prev_trail NÃO são atualizados aqui. É por caberem na
            # janela anterior que este ramo é barato; atualizar quebra o decodificador.
        else:
            # Control '11' — ~19%, 36,9 bits médios (13 bits de metadado).
            w.write_bit(1)
            w.write_bits(lead, VALUE_LEADING_BITS)
            w.write_bits(64 - lead - trail - VALUE_LENGTH_BIAS, VALUE_LENGTH_BITS)
            w.write_bits(x >> trail, 64 - lead - trail)
            st.prev_lead = lead
            st.prev_trail = trail
    st.prev_bits = bits


def decode_first_value(r: BitReader, st: CodecState) -> float:
    bits = r.read_bits(64)
    st.prev_bits = bits
    st.prev_lead = None
    st.prev_trail = None
    return _float_of(bits)


def decode_value(r: BitReader, st: CodecState) -> float:
    if r.read_bit() == 0:
        return _float_of(st.prev_bits)
    if r.read_bit() == 0:
        if st.prev_lead is None:
            raise SeriesError(
                "bitstream corrompido: control '10' antes de qualquer '11', "
                "logo não há janela anterior de bits significativos"
            )
        significant = 64 - st.prev_lead - st.prev_trail
        x = r.read_bits(significant) << st.prev_trail
    else:
        lead = r.read_bits(VALUE_LEADING_BITS)
        significant = r.read_bits(VALUE_LENGTH_BITS) + VALUE_LENGTH_BIAS
        if lead + significant > 64:
            raise SeriesError(
                f"bitstream corrompido: lead={lead}, significant={significant}"
            )
        trail = 64 - lead - significant
        x = r.read_bits(significant) << trail
        st.prev_lead = lead
        st.prev_trail = trail
    bits = st.prev_bits ^ x
    st.prev_bits = bits
    return _float_of(bits)


# --- Chunk: a unidade de estado do codec ----------------------------------------------


class Chunk:
    """Um bloco append-only. `base_ts` alinhado a `block_seconds` (R1 §4.1.1)."""

    __slots__ = ("base_ts", "block_seconds", "_w", "_st", "_n", "_last_ts")

    def __init__(self, base_ts: int, block_seconds: int) -> None:
        validate_block_seconds(block_seconds)
        if base_ts % block_seconds != 0:
            raise SeriesError(
                f"base_ts {base_ts} não está alinhado à janela de {block_seconds}s"
            )
        self.base_ts = base_ts
        self.block_seconds = block_seconds
        self._w = BitWriter()
        self._st = CodecState()
        self._n = 0
        self._last_ts: int | None = None

    @staticmethod
    def window_of(ts: int, block_seconds: int) -> int:
        return align_down(ts, block_seconds)

    def contains(self, ts: int) -> bool:
        return self.base_ts <= ts < self.base_ts + self.block_seconds

    @property
    def n_points(self) -> int:
        return self._n

    @property
    def last_ts(self) -> int | None:
        return self._last_ts

    def append(self, ts: int, value: float) -> None:
        if not self.contains(ts):
            raise SeriesError(
                f"ts {ts} fora da janela [{self.base_ts}, "
                f"{self.base_ts + self.block_seconds})"
            )
        if self._last_ts is not None and ts <= self._last_ts:
            raise SeriesError(
                f"chunk é append-only e crescente: {ts} não é maior que {self._last_ts}"
            )
        if self._n == 0:
            encode_first_timestamp(self._w, self._st, self.base_ts, ts)
            encode_first_value(self._w, self._st, value)
        else:
            encode_timestamp(self._w, self._st, ts)
            encode_value(self._w, self._st, value)
        self._n += 1
        self._last_ts = ts

    def payload(self) -> tuple[bytes, int]:
        return self._w.to_bytes(), self._w.nbits

    def to_bytes(self) -> bytes:
        payload, nbits = self.payload()
        header = struct.pack(
            CHUNK_HEADER,
            CHUNK_MAGIC,
            self.base_ts,
            self.block_seconds,
            self._n,
            zlib.crc32(payload) & 0xFFFFFFFF,
        )
        # nbits vai como u32 depois do header: sem ele, o padding do último byte é
        # indistinguível de dado (achado RES-04).
        return header + struct.pack(">I", nbits) + payload

    @staticmethod
    def read(blob: bytes) -> tuple[int, int, int, bytes, int]:
        """Devolve (base_ts, block_seconds, n_points, payload, nbits), verificando o crc."""
        if len(blob) < CHUNK_HEADER_SIZE + 4:
            raise SeriesError("chunk truncado: menor que o próprio cabeçalho")
        magic, base_ts, block_seconds, n_points, crc = struct.unpack(
            CHUNK_HEADER, blob[:CHUNK_HEADER_SIZE]
        )
        if magic != CHUNK_MAGIC:
            raise SeriesError(f"não é um chunk TSZ (magic {magic!r})")
        # MEC-06: block_seconds vem de arquivo, isto é, de fora. Validar na CARGA.
        if block_seconds > MAX_BLOCK_SECONDS or block_seconds <= 0:
            raise SeriesError(
                f"chunk declara block_seconds={block_seconds}, fora de 1..{MAX_BLOCK_SECONDS}"
            )
        (nbits,) = struct.unpack(">I", blob[CHUNK_HEADER_SIZE : CHUNK_HEADER_SIZE + 4])
        payload = blob[CHUNK_HEADER_SIZE + 4 :]
        if nbits > len(payload) * 8:
            raise SeriesError(
                f"chunk truncado: declara {nbits} bits, há {len(payload) * 8}"
            )
        if (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
            raise SeriesError(
                "crc32 do chunk não confere: corrupção detectada. "
                "(o crc detecta corrupção acidental; não autentica)"
            )
        return base_ts, block_seconds, n_points, payload, nbits

    @staticmethod
    def points_of(blob: bytes):
        """Itera os pontos de um chunk serializado. Sequencial por construção."""
        base_ts, block_seconds, n_points, payload, nbits = Chunk.read(blob)
        r = BitReader(payload, nbits)
        st = CodecState()
        for i in range(n_points):
            if i == 0:
                ts = decode_first_timestamp(r, st, base_ts)
                value = decode_first_value(r, st)
            else:
                ts = decode_timestamp(r, st)
                value = decode_value(r, st)
            yield Point(ts, value)

    @staticmethod
    def from_bytes(blob: bytes) -> "Chunk":
        """Reconstrói um chunk gravável a partir dos bytes (re-codifica os pontos)."""
        base_ts, block_seconds, _, _, _ = Chunk.read(blob)
        chunk = Chunk(base_ts, block_seconds)
        for p in Chunk.points_of(blob):
            chunk.append(p.ts, p.value)
        return chunk
