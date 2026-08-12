"""Testes do codec contra as SPECS, não contra a implementação.

Fontes: specs/technical/codec-gorilla.md (R1 §4.1.1/§4.1.2),
specs/examples/gorilla-pseudocodigo.md (as 4 armadilhas de port),
specs/validation/criterios-aceitacao.md (CA-1 e os casos-limite obrigatórios).
"""

import struct

import pytest

from tsz.bitstream import BitReader, BitstreamError, BitWriter
from tsz.dataset_gen import IEEE_EDGE, PROFILES, generate
from tsz.gorilla_codec import (
    Chunk,
    CodecState,
    decode_timestamp,
    encode_timestamp,
)
from tsz.series import MAX_BLOCK_SECONDS, SeriesError

BASE = 1786464000  # alinhado a 7200


def bits(v: float) -> bytes:
    return struct.pack(">d", v)


def roundtrip(pairs, block_seconds=7200):
    chunk = Chunk(Chunk.window_of(pairs[0][0], block_seconds), block_seconds)
    for ts, value in pairs:
        chunk.append(ts, value)
    return list(Chunk.points_of(chunk.to_bytes()))


# --- CA-1: lossless bit a bit ---------------------------------------------------------


def test_ca1_roundtrip_ieee_edge():
    """CA-1: decode(encode(S)) == S comparando BYTES, nos casos-limite obrigatórios."""
    pairs = [(BASE + i * 60, v) for i, v in enumerate(IEEE_EDGE)]
    out = roundtrip(pairs)
    assert len(out) == len(pairs)
    for got, (ts, value) in zip(out, pairs):
        assert got.ts == ts
        assert bits(got.value) == bits(value), f"valor {value!r} não sobreviveu"


def test_ca1_nan_payload_preservado():
    """Um NaN genérico perderia o payload. `lossless` exige preservá-lo."""
    nan = struct.unpack(">d", struct.pack(">Q", 0x7FF8000000000001))[0]
    (got,) = roundtrip([(BASE, nan)])
    assert struct.pack(">d", got.value) == struct.pack(">Q", 0x7FF8000000000001)


def test_ca1_zero_negativo_distinto():
    """`0.0 == -0.0` em aritmética, mas os bits diferem e o codec é lossless."""
    out = roundtrip([(BASE, 0.0), (BASE + 60, -0.0)])
    assert bits(out[0].value) == bits(0.0)
    assert bits(out[1].value) == bits(-0.0)
    assert bits(out[0].value) != bits(out[1].value)


def test_ca1_significante_64_bits():
    """NOTA D: o campo de comprimento tem 6 bits e o significante pode ser 64.

    `-inf ^ 5e-324 = 0xFFF0000000000001` → lead=0, trail=0, significante=64.
    Um codec que grave 64 em 6 bits trunca para 0 e falha ao decodificar.
    """
    x = struct.unpack(">Q", struct.pack(">d", float("-inf")))[0] ^ struct.unpack(
        ">Q", struct.pack(">d", 5e-324)
    )[0]
    assert 64 - x.bit_length() == 0, "pré-condição: nenhum zero à esquerda"
    assert (x & -x).bit_length() - 1 == 0, "pré-condição: nenhum zero à direita"

    out = roundtrip([(BASE, float("-inf")), (BASE + 60, 5e-324)])
    assert bits(out[0].value) == bits(float("-inf"))
    assert bits(out[1].value) == bits(5e-324)


def test_ca1_comparacao_por_igualdade_falharia():
    """O teste que valida o teste: `==` daria falso-positivo/negativo aqui.

    Se a suíte comparasse valores com `==`, `nan != nan` reprovaria um round-trip
    correto e `0.0 == -0.0` aprovaria um errado. Por isso tudo compara bytes.
    """
    nan = float("nan")
    assert not (nan == nan)  # aprovaria errado / reprovaria certo
    assert 0.0 == -0.0  # aprovaria um codec que perdesse o sinal
    assert bits(0.0) != bits(-0.0)  # a comparação correta distingue


# --- R1 §4.1.1: buckets de delta-of-delta ---------------------------------------------


def ts_roundtrip(deltas):
    st = CodecState()
    w = BitWriter()
    ts, seq = 0, []
    for d in deltas:
        ts += d
        seq.append(ts)
        encode_timestamp(w, st, ts)
    r = BitReader(w.to_bytes(), w.nbits)
    st2 = CodecState()
    return [decode_timestamp(r, st2) for _ in seq], seq, w.nbits


@pytest.mark.parametrize(
    "deltas,esperado_bits",
    [
        ([0, 0, 0, 0, 0], 5),  # D=0 → 1 bit cada (~96% dos casos em R1 Fig. 3)
        ([64], 9),  # '10' + 7 bits
        ([256], 12),  # '110' + 9 bits
        ([2048], 16),  # '1110' + 12 bits
        ([99999], 36),  # '1111' + 32 bits
    ],
)
def test_r1_buckets_delta_of_delta(deltas, esperado_bits):
    got, seq, nbits = ts_roundtrip(deltas)
    assert got == seq
    assert nbits == esperado_bits


def test_r1_faixa_assimetrica_p5():
    """Armadilha P5: as faixas de R1 são [-63, 64], NÃO [-64, 63].

    `D = 64` tem de caber no bucket de 7 bits (9 bits no total) e `D = -64` NÃO —
    ele cai no bucket seguinte (12 bits). Um codec que usasse complemento de dois
    ingênuo inverteria os dois.
    """
    _, _, bits_pos = ts_roundtrip([64])
    _, _, bits_neg = ts_roundtrip([-64])
    assert bits_pos == 9, "D=64 deve caber no bucket de 7 bits"
    assert bits_neg == 12, "D=-64 NÃO cabe: cai no bucket de 9 bits"

    _, _, bits_63 = ts_roundtrip([-63])
    assert bits_63 == 9, "D=-63 é o limite inferior do primeiro bucket"


def test_r1_extremos_de_cada_bucket_fazem_roundtrip():
    for d in (-63, 64, -255, 256, -2047, 2048, -2048, 2049, 2**20, -(2**20)):
        got, seq, _ = ts_roundtrip([d])
        assert got == seq, f"D={d} não fez round-trip"


# --- R1 §4.1.2: NOTA C ----------------------------------------------------------------


def test_r1_ramo_10_depois_do_11():
    """NOTA C: prev_lead/prev_trail NÃO são atualizados no ramo '10'.

    É por caberem na janela anterior que o ramo é barato; atualizar quebra o
    decodificador. Esta sequência força '11' e depois '10'.
    """
    out = roundtrip(
        [(BASE, 1.0), (BASE + 60, 1.5), (BASE + 120, 1.25), (BASE + 180, 1.125)]
    )
    for got, expected in zip(out, [1.0, 1.5, 1.25, 1.125]):
        assert bits(got.value) == bits(expected)


def test_r1_valores_identicos_custam_um_bit():
    """R1 §4.1.2: XOR zero → um único bit '0' (~51% dos valores em produção).

    NOTA A: o 2º ponto tem `D = delta - 0 = delta`. Com delta = 1 s, D = 1 cai no bucket
    `[-63, 64]` ⇒ 2 bits de prefixo + 7 de payload = 9 bits de timestamp.
    Custo total do 2º ponto: 9 (timestamp) + 1 (valor idêntico) = 10 bits.
    """
    chunk = Chunk(BASE, 7200)
    chunk.append(BASE, 42.0)
    antes = chunk.payload()[1]
    chunk.append(BASE + 1, 42.0)
    depois = chunk.payload()[1]
    assert depois - antes == 9 + 1

    # E do 3º ponto em diante, série regular ⇒ D = 0 ⇒ 1 bit de timestamp.
    chunk.append(BASE + 2, 42.0)
    assert chunk.payload()[1] - depois == 1 + 1


# --- R1 nota 1: o teto de 4h ----------------------------------------------------------


def test_r1_bloco_acima_de_4h_rejeitado():
    """O primeiro delta tem 14 bits (2^14 = 16.384 s), logo o bloco não passa de 4h."""
    with pytest.raises(SeriesError, match="14 bits"):
        Chunk(0, MAX_BLOCK_SECONDS + 1)


def test_bloco_de_4h_exatamente_e_aceito():
    Chunk(0, MAX_BLOCK_SECONDS)


# --- Integridade: RES-01 e RES-04 -----------------------------------------------------


def test_res01_crc_detecta_bit_trocado():
    """Um bit virado no payload corromperia todos os pontos seguintes do chunk."""
    chunk = Chunk(BASE, 7200)
    for i in range(50):
        chunk.append(BASE + i, 40.0 + i)
    blob = bytearray(chunk.to_bytes())
    blob[-1] ^= 0x01  # vira um bit no payload
    with pytest.raises(SeriesError, match="crc32"):
        list(Chunk.points_of(bytes(blob)))


def test_res04_chunk_truncado_rejeitado():
    """Truncamento é ERRO, não padding lido como dado."""
    chunk = Chunk(BASE, 7200)
    for i in range(50):
        chunk.append(BASE + i, 40.0 + i)
    blob = chunk.to_bytes()
    with pytest.raises(SeriesError):
        list(Chunk.points_of(blob[:-4]))


def test_chunk_com_magic_errado_rejeitado():
    with pytest.raises(SeriesError, match="não é um chunk"):
        Chunk.read(b"XXXX" + b"\x00" * 40)


def test_mec06_block_seconds_externo_validado_na_carga():
    """MEC-06: `block_seconds` vem do arquivo, isto é, de fora. Validar na CARGA."""
    chunk = Chunk(BASE, 7200)
    chunk.append(BASE, 1.0)
    blob = bytearray(chunk.to_bytes())
    struct.pack_into(">I", blob, 12, 20000)  # block_seconds > MAX
    with pytest.raises(SeriesError, match="block_seconds"):
        Chunk.read(bytes(blob))


# --- bitstream: armadilhas P1 e SEC-03 ------------------------------------------------


def test_p1_int_do_python_nao_trunca_sozinho():
    """P1: `int` é de precisão arbitrária. Escrever com o bit 63 setado tem de funcionar."""
    w = BitWriter()
    w.write_bits(0x8000000000000001, 64)
    r = BitReader(w.to_bytes(), w.nbits)
    assert r.read_bits(64) == 0x8000000000000001


def test_p1_valor_maior_que_n_bits_e_mascarado():
    w = BitWriter()
    w.write_bits(0xFF, 4)  # só os 4 bits menos significativos
    r = BitReader(w.to_bytes(), w.nbits)
    assert r.read_bits(4) == 0xF


def test_sec03_leitura_alem_do_fim_e_erro():
    """SEC-03/RES-04: ler além do fim é erro, nunca padding."""
    w = BitWriter()
    w.write_bits(0b101, 3)
    r = BitReader(w.to_bytes(), w.nbits)
    r.read_bits(3)
    with pytest.raises(BitstreamError, match="truncado|além"):
        r.read_bits(1)


# --- gerador de ground truth ----------------------------------------------------------


@pytest.mark.parametrize("profile", PROFILES)
def test_gerador_deterministico_e_monotonico(profile):
    """ASM-05/MEC-03: mesma seed → mesma série. E I2 vale para step=1 nos 7 perfis.

    Um gerador que produza dado inválido invalida silenciosamente todo teste que
    dependa dele — foi o defeito real do perfil `jitter` com step=1.
    """
    a = list(generate(profile, 200, seed=7, step=1))
    b = list(generate(profile, 200, seed=7, step=1))
    assert [(p.ts, bits(p.value)) for p in a] == [(p.ts, bits(p.value)) for p in b]
    for anterior, atual in zip(a, a[1:]):
        assert atual.ts > anterior.ts, f"{profile}: ts não é estritamente crescente"


def test_gerador_com_seed_diferente_produz_serie_diferente():
    a = list(generate("float-noise", 50, seed=7))
    b = list(generate("float-noise", 50, seed=8))
    assert [bits(p.value) for p in a] != [bits(p.value) for p in b]


def test_perfil_desconhecido_e_erro():
    with pytest.raises(SeriesError, match="desconhecido"):
        list(generate("nao-existe", 10, 7))
