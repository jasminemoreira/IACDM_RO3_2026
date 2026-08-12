"""M-01 bitstream — escrita/leitura de campos de largura arbitrária.

Decisão de representação (achado PRF-02): `bytearray` + offset de bit. NUNCA acumular
num `int` de precisão arbitrária e deslocar — cada write copiaria o acumulado inteiro,
dando O(n²) por bloco.

Armadilha P1: `int` do Python não trunca em 64 bits. Toda escrita mascara.
"""

from __future__ import annotations

MASK64 = 0xFFFFFFFFFFFFFFFF


class BitstreamError(Exception):
    pass


class BitWriter:
    __slots__ = ("_buf", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._nbits = 0  # bits válidos já escritos

    def write_bit(self, bit: int) -> None:
        if self._nbits % 8 == 0:
            self._buf.append(0)
        if bit & 1:
            byte_index = self._nbits >> 3
            shift = 7 - (self._nbits & 7)
            self._buf[byte_index] |= 1 << shift
        self._nbits += 1

    def write_bits(self, value: int, n: int) -> None:
        """Grava os `n` bits menos significativos de `value`, mais significativo primeiro."""
        if not 0 < n <= 64:
            raise BitstreamError(f"n deve estar em 1..64, recebi {n}")
        value &= (1 << n) - 1  # P1: mascarar sempre
        for shift in range(n - 1, -1, -1):
            self.write_bit((value >> shift) & 1)

    def to_bytes(self) -> bytes:
        return bytes(self._buf)

    @property
    def nbits(self) -> int:
        return self._nbits

    def __len__(self) -> int:
        return self._nbits


class BitReader:
    """Leitura limitada pelo comprimento (achado SEC-03).

    Ler além do fim é ERRO, não padding: um bitstream truncado ou hostil não pode
    produzir dados silenciosamente (achado RES-04).
    """

    __slots__ = ("_buf", "_pos", "_limit")

    def __init__(self, data: bytes, nbits: int | None = None) -> None:
        self._buf = data
        self._pos = 0
        self._limit = len(data) * 8 if nbits is None else nbits
        if self._limit > len(data) * 8:
            raise BitstreamError(
                f"nbits={nbits} excede os {len(data) * 8} bits disponíveis"
            )

    def bits_left(self) -> int:
        return self._limit - self._pos

    def eof(self) -> bool:
        return self._pos >= self._limit

    def read_bit(self) -> int:
        if self._pos >= self._limit:
            raise BitstreamError("leitura além do fim do bitstream")
        byte_index = self._pos >> 3
        shift = 7 - (self._pos & 7)
        self._pos += 1
        return (self._buf[byte_index] >> shift) & 1

    def read_bits(self, n: int) -> int:
        if not 0 < n <= 64:
            raise BitstreamError(f"n deve estar em 1..64, recebi {n}")
        if self.bits_left() < n:
            raise BitstreamError(
                f"pedidos {n} bits, restam {self.bits_left()}: bitstream truncado"
            )
        value = 0
        for _ in range(n):
            value = (value << 1) | self.read_bit()
        return value


def to_signed(value: int, n: int) -> int:
    """Interpreta `value` de `n` bits como complemento de dois."""
    sign = 1 << (n - 1)
    return (value & (sign - 1)) - (value & sign)
