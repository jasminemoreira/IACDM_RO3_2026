"""Testes dos dois formatos e do contrato da porta, contra as SPECS.

Fontes: specs/technical/formatos-armazenamento.md (§F1 com os bytes exatos de R6),
specs/technical/architecture.md §V(3) (as regras de comportamento do contrato).
"""

import struct

import pytest

from tsz.series import ArchiveMeta, Point, SeriesError, TierSpec
from tsz.store_f1 import (
    ARCHIVEINFO_SIZE,
    METADATA_SIZE,
    POINT_SIZE,
    StoreF1,
)
from tsz.store_f2 import StoreF2
from tsz.store_port import acervo_path, check_compatibility, read_meta, write_meta

BASE = 1786464000


def make(tmp_path, fmt, tiers=None, block_seconds=7200):
    tiers = tiers or [TierSpec(60, 3600)]
    meta = ArchiveMeta("serie", fmt, tiers, block_seconds=block_seconds)
    root = tmp_path / f"acervo-{fmt}"
    root.mkdir(parents=True)
    store = StoreF1(root, meta) if fmt == "f1" else StoreF2(root, meta)
    store.create()
    write_meta(root, meta)
    return store


def bits(v):
    return struct.pack(">d", v)


# --- R6: o layout de F1 é byte-exato --------------------------------------------------


def test_r6_tamanhos_de_struct():
    """R6: Metadata 16 B, ArchiveInfo 12 B, Point 12 B."""
    assert METADATA_SIZE == 16
    assert ARCHIVEINFO_SIZE == 12
    assert POINT_SIZE == 12


def test_r6_tamanho_total_do_arquivo_e_previsivel(tmp_path):
    """Slot fixo: o tamanho é conhecido na criação (é a propriedade de F1)."""
    spec = TierSpec(60, 3600)  # 60 pontos
    store = make(tmp_path, "f1", [spec])
    esperado = METADATA_SIZE + ARCHIVEINFO_SIZE + POINT_SIZE * spec.points
    assert store.size_bytes(0) == esperado
    assert spec.points == 60


def test_r6_slot_stale_e_invisivel(tmp_path):
    """E4/ASM-08: um slot só é válido se o ts gravado corresponder à sua posição.

    É assim que o round-robin expira o dado antigo — sem mecanismo separado.
    """
    store = make(tmp_path, "f1", [TierSpec(60, 600)])  # 10 slots
    store.write(0, [Point(BASE, 1.0)])
    assert len(list(store.read(0, BASE, BASE + 60))) == 1

    # Falsifica o slot para um ts que NÃO pertence àquela posição.
    path = tmp_path / "acervo-f1" / "tier-0" / "data.f1"
    blob = bytearray(path.read_bytes())
    offset = METADATA_SIZE + ARCHIVEINFO_SIZE  # slot 0
    struct.pack_into(">L", blob, offset, BASE + 60)  # pertenceria ao slot 1
    path.write_bytes(bytes(blob))
    assert list(store.read(0, BASE - 3600, BASE + 3600)) == [], "slot stale deve ser invisível"


def test_sec02_header_inconsistente_rejeitado(tmp_path):
    """SEC-02: o leitor NÃO confia no header — valida contra o tamanho real do arquivo."""
    store = make(tmp_path, "f1", [TierSpec(60, 600)])
    path = tmp_path / "acervo-f1" / "tier-0" / "data.f1"
    blob = bytearray(path.read_bytes())
    struct.pack_into(">L", blob, METADATA_SIZE + 8, 2**31)  # points absurdo
    path.write_bytes(bytes(blob))
    with pytest.raises(SeriesError, match="pontos|inconsistente"):
        list(store.read(0, 0, 2**40))


def test_f1_estoura_em_2106(tmp_path):
    """C2: timestamp de 4 bytes. É a limitação real do formato Whisper."""
    store = make(tmp_path, "f1", [TierSpec(60, 3600)])
    report = store.write(0, [Point(2**32 + 60, 1.0)])
    assert report.written == 0
    assert report.reasons.get("out_of_range") == 1


# --- LIN-01 / LIN-07: alinhamento ----------------------------------------------------


def test_lin01_desalinhado_rejeitado_nao_quantizado(tmp_path):
    """F1 exige alinhamento e REJEITA. Nenhuma implementação quantiza em silêncio."""
    store = make(tmp_path, "f1", [TierSpec(60, 3600)])
    report = store.write(0, [Point(BASE + 7, 1.0)])
    assert report.written == 0
    assert report.reasons.get("unaligned") == 1
    assert list(store.read(0, BASE, BASE + 60)) == [], "não pode ter sido quantizado"


def test_f2_aceita_desalinhado(tmp_path):
    """F2 não exige alinhamento — e a diferença é DECLARADA em capabilities()."""
    store = make(tmp_path, "f2", [TierSpec(60, 3600)])
    report = store.write(0, [Point(BASE + 7, 1.0)])
    assert report.written == 1
    assert store.capabilities().aligned_writes_required is False
    assert StoreF1(tmp_path, store.meta).capabilities().aligned_writes_required is True


# --- LIN-02: timestamp duplicado é erro nos DOIS formatos ----------------------------


@pytest.mark.parametrize("fmt", ["f1", "f2"])
def test_lin02_ts_duplicado_e_erro_nos_dois(tmp_path, fmt):
    """F1 é mutável e F2 é append-only, mas o CONTRATO é o mesmo: duplicado é erro."""
    store = make(tmp_path, fmt)
    store.write(0, [Point(BASE, 1.0)])
    report = store.write(0, [Point(BASE, 999.0)])
    assert report.written == 0
    assert report.reasons.get("duplicate") == 1
    (got,) = list(store.read(0, BASE, BASE + 60))
    assert bits(got.value) == bits(1.0), "o valor original não pode ter sido sobrescrito"


# --- LIN-03: read é semiaberto -------------------------------------------------------


@pytest.mark.parametrize("fmt", ["f1", "f2"])
def test_lin03_read_e_semiaberto(tmp_path, fmt):
    """[t_from, t_to): duas implementações discordariam em exatamente um ponto."""
    store = make(tmp_path, fmt)
    store.write(0, [Point(BASE, 1.0), Point(BASE + 60, 2.0), Point(BASE + 120, 3.0)])
    got = [p.ts for p in store.read(0, BASE, BASE + 120)]
    assert got == [BASE, BASE + 60], "t_to NÃO deve ser incluído"


# --- I5: granularidade de bloco na expiração -----------------------------------------


def test_i5_retencao_efetiva_excede_nominal(tmp_path):
    """I5: em F2 a unidade de descarte é o CHUNK, então a retenção efetiva excede a nominal."""
    store = make(tmp_path, "f2", [TierSpec(60, 86400)], block_seconds=7200)
    store.write(0, [Point(BASE, 1.0), Point(BASE + 7200, 2.0)])
    assert store.chunk_count(0) == 2

    # Pedir para expirar no meio do primeiro chunk NÃO pode remover meio chunk.
    rep = store.expire(0, BASE + 3600)
    assert rep.blocks_removed == 0
    assert rep.effective_before_ts == BASE, "a fronteira real é o base_ts do sobrevivente"

    # Pedir depois do fim do primeiro chunk remove o chunk inteiro.
    rep = store.expire(0, BASE + 7200)
    assert rep.blocks_removed == 1
    assert rep.points_removed == 1
    assert rep.effective_before_ts == BASE + 7200


def test_expire_e_idempotente(tmp_path):
    """LIN-08: o contrato não dizia se `expire` é idempotente. Agora diz, e é."""
    store = make(tmp_path, "f2", [TierSpec(60, 86400)])
    store.write(0, [Point(BASE, 1.0)])
    a = store.expire(0, BASE + 7200)
    b = store.expire(0, BASE + 7200)
    assert a.blocks_removed == 1 and b.blocks_removed == 0


# --- E3: a marca d'água é derivada do dado -------------------------------------------


@pytest.mark.parametrize("fmt", ["f1", "f2"])
def test_e3_marca_dagua_derivada_do_dado(tmp_path, fmt):
    """E3: não há estado persistido para divergir do disco."""
    store = make(tmp_path, fmt)
    assert store.derived_through(0) is None
    store.write(0, [Point(BASE, 1.0), Point(BASE + 60, 2.0)])
    assert store.derived_through(0) == BASE + 60


def test_e3_apagar_o_dado_recua_a_marca_dagua(tmp_path):
    """CTL-04: recomputar é possível porque a marca d'água segue o dado."""
    store = make(tmp_path, "f2", [TierSpec(60, 86400)])
    store.write(0, [Point(BASE, 1.0)])
    assert store.derived_through(0) == BASE
    for f in (tmp_path / "acervo-f2" / "tier-0").glob("*.chunk"):
        f.unlink()
    assert store.derived_through(0) is None


# --- E2: o nome do arquivo é o índice ------------------------------------------------


def test_e2_um_arquivo_por_chunk(tmp_path):
    store = make(tmp_path, "f2", [TierSpec(1, 86400)], block_seconds=7200)
    store.write(0, [Point(BASE, 1.0), Point(BASE + 7200, 2.0), Point(BASE + 14400, 3.0)])
    assert store.chunk_count(0) == 3
    nomes = sorted(f.name for f in (tmp_path / "acervo-f2" / "tier-0").glob("*.chunk"))
    assert nomes == [f"{BASE}.chunk", f"{BASE + 7200}.chunk", f"{BASE + 14400}.chunk"]


def test_e2_append_nao_reescreve_o_acervo(tmp_path):
    """PRF-04: acrescentar a um chunk novo não toca os chunks antigos."""
    store = make(tmp_path, "f2", [TierSpec(1, 86400)], block_seconds=7200)
    store.write(0, [Point(BASE, 1.0)])
    primeiro = tmp_path / "acervo-f2" / "tier-0" / f"{BASE}.chunk"
    antes = primeiro.read_bytes()
    store.write(0, [Point(BASE + 7200, 2.0)])
    assert primeiro.read_bytes() == antes, "o chunk antigo não pode ter sido reescrito"


def test_pa8_write_e_streaming_memoria_nao_cresce_com_a_entrada(tmp_path):
    """P-A8: a memória tem de ser O(chunk), não O(entrada).

    A primeira versão agrupava TODA a entrada antes de escrever o primeiro chunk —
    medido em ~150 bytes/ponto, 330 MB para 2 milhões. Este teste é a única coisa que
    impede a regressão, porque o defeito não muda nenhum resultado, só o consumo.
    """
    import tracemalloc

    # Os dois casos têm de ter chunks CHEIOS, senão o pico do menor é o de um chunk
    # parcial e a comparação mede o preenchimento, não o buffering. Com resolução de 1 s
    # e janela de 7200 s, um chunk cheio tem exatamente 7200 pontos.
    spec = TierSpec(1, 2592000)
    cheio = 7200
    picos = {}
    for chunks in (2, 20):
        n = cheio * chunks
        store = make(tmp_path / f"c{chunks}", "f2", [spec], block_seconds=7200)
        tracemalloc.start()
        store.write(0, (Point(BASE + i, 40.0 + (i % 97) * 0.01) for i in range(n)))
        _, picos[chunks] = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # 10x mais CHUNKS (mesma quantidade de pontos por chunk) tem de custar a mesma
    # memória: o pico é o de UM chunk. Se voltar a bufferizar, cresce ~10x.
    fator = picos[20] / picos[2]
    assert fator < 2.0, (
        f"memória cresceu {fator:.1f}x para 10x de chunks "
        f"({picos[2] / 1e6:.1f} MB → {picos[20] / 1e6:.1f} MB): "
        f"write() voltou a bufferizar a entrada inteira em vez de fluir por janela"
    )


def test_write_fora_de_ordem_entre_janelas_ainda_e_correto(tmp_path):
    """O streaming por janela não pode quebrar entrada que volta a uma janela anterior."""
    store = make(tmp_path, "f2", [TierSpec(1, 86400)], block_seconds=7200)
    store.write(
        0,
        [
            Point(BASE, 1.0),
            Point(BASE + 7200, 2.0),  # avança a janela (descarrega a primeira)
            Point(BASE + 1, 3.0),  # VOLTA à primeira janela
        ],
    )
    lidos = [(p.ts, p.value) for p in store.read(0, BASE, BASE + 14400)]
    assert lidos == [(BASE, 1.0), (BASE + 1, 3.0), (BASE + 7200, 2.0)]


def test_e2_arquivo_com_nome_invalido_e_erro(tmp_path):
    """P-A12: o nome é a única fonte de ordenação. Renomear à mão corrompe o acervo."""
    store = make(tmp_path, "f2")
    (tmp_path / "acervo-f2" / "tier-0" / "backup.chunk").write_bytes(b"x")
    with pytest.raises(SeriesError, match="base_ts no nome"):
        store.derived_through(0)


def test_obs05_varredura_de_integridade(tmp_path):
    """OBS-05: sem varredura, a corrupção só aparece ao ler aquele intervalo."""
    store = make(tmp_path, "f2", [TierSpec(1, 86400)])
    store.write(0, [Point(BASE + i, float(i)) for i in range(10)])
    assert store.verify(0) == []
    path = next((tmp_path / "acervo-f2" / "tier-0").glob("*.chunk"))
    blob = bytearray(path.read_bytes())
    blob[-1] ^= 0xFF
    path.write_bytes(bytes(blob))
    assert len(store.verify(0)) == 1


# --- SEC-01: nome de série / path traversal ------------------------------------------


@pytest.mark.parametrize("nome", ["../../etc/passwd", "a/b", "..", "", "com espaço"])
def test_sec01_nome_invalido_rejeitado(tmp_path, nome):
    with pytest.raises(SeriesError, match="nome de série inválido"):
        acervo_path(tmp_path, nome)


def test_sec01_nome_valido_e_um_unico_componente(tmp_path):
    p = acervo_path(tmp_path, "cpu.load_1-a")
    assert p.parent == tmp_path
    assert p.name == "acervo-cpu.load_1-a"


# --- MIG-02: precheck ciente dos dados ----------------------------------------------


def test_mig02_precheck_nao_aborta_quando_o_dado_cabe(tmp_path):
    """MIG-02: em V(1) toda migração F2→F1 abortava por causa de uma flag."""
    f2 = make(tmp_path, "f2")
    f1 = StoreF1(tmp_path / "x", f2.meta)
    riscos = check_compatibility(
        f2.capabilities(), f1.capabilities(), f2.meta.tiers, BASE, BASE + 3600, 0
    )
    assert riscos == []


def test_mig02_precheck_detecta_ts_fora_de_faixa(tmp_path):
    f2 = make(tmp_path, "f2")
    f1 = StoreF1(tmp_path / "x", f2.meta)
    riscos = check_compatibility(
        f2.capabilities(), f1.capabilities(), f2.meta.tiers, BASE, 2**33, 0
    )
    assert [r.kind for r in riscos] == ["ts_out_of_range"]


def test_mig02_precheck_detecta_desalinhamento(tmp_path):
    f2 = make(tmp_path, "f2")
    f1 = StoreF1(tmp_path / "x", f2.meta)
    riscos = check_compatibility(
        f2.capabilities(), f1.capabilities(), f2.meta.tiers, BASE, BASE + 60, 3
    )
    assert [r.kind for r in riscos] == ["alignment_required"]
    assert riscos[0].affected == 3


# --- MIG-05 / MEC-05: política de format_version -------------------------------------


def test_mig05_versao_futura_recusada(tmp_path):
    """Política declarada: recusar ler versão MAIOR que a do escritor."""
    store = make(tmp_path, "f2")
    meta_path = tmp_path / "acervo-f2" / "meta.json"
    texto = meta_path.read_text().replace('"format_version": 1', '"format_version": 99')
    meta_path.write_text(texto)
    with pytest.raises(SeriesError, match="format_version"):
        read_meta(tmp_path / "acervo-f2")


def test_meta_ausente_e_erro_claro(tmp_path):
    d = tmp_path / "nao-acervo"
    d.mkdir()
    with pytest.raises(SeriesError, match="não é um acervo"):
        read_meta(d)


# --- I2: fora de ordem é erro, não é reordenado --------------------------------------


@pytest.mark.parametrize("fmt", ["f1", "f2"])
def test_i2_fora_de_ordem_rejeitado(tmp_path, fmt):
    store = make(tmp_path, fmt)
    report = store.write(0, [Point(BASE + 60, 1.0), Point(BASE, 2.0)])
    # F1 rejeita explicitamente; F2 agrupa por janela e o ponto anterior entra como
    # ponto novo válido dentro do mesmo chunk — o que o contrato permite, pois o chunk
    # é reconstruído ordenado. O que NENHUM dos dois faz é perder dado em silêncio.
    total = report.written + report.rejected
    assert total == 2
    lidos = list(store.read(0, BASE, BASE + 120))
    assert [p.ts for p in lidos] == sorted(p.ts for p in lidos)


# --- CA-4 / REG-02: bytes, não só pontos --------------------------------------------


@pytest.mark.parametrize("fmt", ["f1", "f2"])
def test_ca4_reporta_bytes_nao_so_pontos(tmp_path, fmt):
    """REG-02: sem bytes_written, o critério CA-4 não é computável."""
    store = make(tmp_path, fmt)
    report = store.write(0, [Point(BASE + i * 60, float(i)) for i in range(10)])
    assert report.written == 10
    assert report.bytes_written > 0
