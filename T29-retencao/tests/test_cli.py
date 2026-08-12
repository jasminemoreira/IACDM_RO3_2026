"""Testes dos casos de uso UC-1..UC-6 pela CLI real, como subprocesso.

Ferramenta escolhida na Fase 6: pytest + subprocess (zero dependência nova; os 9 comandos
são não-interativos e escrevem JSON em stdout).

Fonte: os casos de uso da Fase 0 e specs/validation/criterios-aceitacao.md.
"""

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BASE = 1786464000


def tsz(*args, cwd, expect_ok=True):
    proc = subprocess.run(
        [sys.executable, "-m", "tsz.cli", "--base", ".", *map(str, args)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
    )
    if expect_ok:
        assert proc.returncode == 0, f"falhou: {proc.stderr}"
    return proc


def as_json(proc):
    return json.loads(proc.stdout)


@pytest.fixture
def acervo(tmp_path):
    """Acervo F2 com tier cru de 1s e derivado de 5s (min_age 10s)."""
    tsz(
        "create",
        "cpu.load",
        "--format",
        "f2",
        "--tiers",
        "1:3600:average,5:86400:average:0.5:10",
        cwd=tmp_path,
    )
    csv = tmp_path / "pts.csv"
    csv.write_text("".join(f"{BASE + i},{40.0 + (i % 3)}\n" for i in range(120)))
    return tmp_path


# --- UC-1: ingerir e comprimir --------------------------------------------------------


def test_cli_uc1_ingest(acervo):
    out = as_json(tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo))
    assert out["written"] == 120
    assert out["rejected"] == 0
    assert out["bytes_written"] > 0


def test_cli_uc1_ingest_duplicado_aborta_por_default(acervo):
    """UX-07: `abort` é o default — o operador decide antes de metade estar dentro."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    proc = tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo, expect_ok=False)
    assert proc.returncode == 2
    assert "rejeitado" in proc.stderr


def test_cli_uc1_on_reject_skip_prossegue(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    out = as_json(
        tsz(
            "ingest",
            "cpu.load",
            "--input",
            "pts.csv",
            "--on-reject",
            "skip",
            cwd=acervo,
        )
    )
    assert out["written"] == 0
    assert out["rejected"] == 120


# --- UC-2: ler intervalo --------------------------------------------------------------


def test_cli_uc2_read_semiaberto(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    proc = tsz("read", "cpu.load", "--from", BASE + 10, "--to", BASE + 15, cwd=acervo)
    linhas = [l for l in proc.stdout.strip().splitlines() if l]
    assert len(linhas) == 5, "5 pontos em [+10, +15)"
    assert linhas[0].startswith(f"{BASE + 10},")
    assert linhas[-1].startswith(f"{BASE + 14},")


def test_cli_uc2_read_intervalo_vazio(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    proc = tsz("read", "cpu.load", "--from", 0, "--to", 100, cwd=acervo)
    assert proc.stdout.strip() == ""


# --- UC-3: retenção -------------------------------------------------------------------


def test_cli_uc3_dry_run_nao_altera_nada(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    tier1 = acervo / "acervo-cpu.load" / "tier-1"
    antes = sorted(f.name for f in tier1.glob("*.chunk"))
    out = as_json(
        tsz("retain", "cpu.load", "--now", BASE + 120, "--dry-run", cwd=acervo)
    )
    assert out["dry_run"] is True
    assert sorted(f.name for f in tier1.glob("*.chunk")) == antes


def test_cli_uc3_dry_run_informa_o_now_usado(acervo):
    """UX-06: um preview que não corresponde à execução é pior que preview nenhum."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    proc = tsz("retain", "cpu.load", "--now", BASE + 120, "--dry-run", cwd=acervo)
    assert f"now={BASE + 120}" in proc.stderr
    assert as_json(proc)["now_used"] == BASE + 120


def test_cli_uc3_retain_deriva_o_tier(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    out = as_json(tsz("retain", "cpu.load", "--now", BASE + 120, cwd=acervo))
    (passo,) = out["derive"]
    assert passo["src"] == 0 and passo["dst"] == 1
    assert passo["written"] == 22, "110 pontos crus com min_age=10 ⇒ 22 janelas de 5s"


def test_cli_uc3_prc01_idempotente(acervo):
    """PRC-01/CTL-01: rodar duas vezes com o mesmo `now` não agrega duas vezes."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    tsz("retain", "cpu.load", "--now", BASE + 120, cwd=acervo)
    out = as_json(tsz("retain", "cpu.load", "--now", BASE + 120, cwd=acervo))
    assert out["derive"] == []


def test_cli_uc3_res06_rederivacao_apos_falha_funciona(acervo):
    """RES-06: era o deadlock — as correções de LIN-02 e PRC-01 se travavam.

    Simula 'derivado mas não confirmado' apagando o chunk derivado: a re-derivação
    tem de reescrever o mesmo arquivo, e NÃO falhar permanentemente por duplicata.
    """
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    tsz("retain", "cpu.load", "--now", BASE + 120, cwd=acervo)
    for f in (acervo / "acervo-cpu.load" / "tier-1").glob("*.chunk"):
        f.unlink()
    out = as_json(tsz("retain", "cpu.load", "--now", BASE + 120, cwd=acervo))
    assert out["derive"][0]["written"] == 22


def test_cli_uc3_asm10_ponto_atrasado_rejeitado(acervo):
    """ASM-10: ponto anterior à marca d'água nunca seria agregado — rejeitar, não aceitar."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    atrasado = acervo / "atrasado.csv"
    atrasado.write_text(f"{BASE + 5},99.0\n")
    proc = tsz(
        "ingest",
        "cpu.load",
        "--input",
        "atrasado.csv",
        cwd=acervo,
        expect_ok=False,
    )
    assert proc.returncode == 2
    assert "late" in proc.stderr or "rejeitado" in proc.stderr


# --- UC-4: migrar formato -------------------------------------------------------------


def test_cli_uc4_migrate_e_verifica_ponto_a_ponto(acervo):
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    out = as_json(tsz("migrate", "cpu.load", "--to-format", "f1", cwd=acervo))
    assert out["lossless"] is True
    assert all(v["lost"] == 0 and v["differ"] == 0 for v in out["verify"])


def test_cli_uc4_origem_preservada_e_marcada(acervo):
    """MIG-01: a migração NUNCA remove a origem — o rollback é ela continuar lá.
    MIG-04: e a origem fica marcada, para não haver dois acervos 'vigentes'."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    tsz("migrate", "cpu.load", "--to-format", "f1", cwd=acervo)
    src = acervo / "acervo-cpu.load"
    assert src.exists()
    meta = json.loads((src / "meta.json").read_text())
    assert meta["superseded_by"].endswith("acervo-cpu.load-f22f1")


def test_cli_uc4_recusa_destino_existente(acervo):
    """A migração também não destrói o DESTINO."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    tsz("migrate", "cpu.load", "--to-format", "f1", cwd=acervo)
    proc = tsz("migrate", "cpu.load", "--to-format", "f1", cwd=acervo, expect_ok=False)
    assert proc.returncode == 2
    assert "já é um acervo" in proc.stderr


def test_cli_uc4_abort_antes_de_escrever_byte(tmp_path):
    """O destino não pode nem ser criado quando o precheck encontra risco."""
    tsz(
        "create", "m.serie", "--format", "f2", "--tiers", "60:3600:average", cwd=tmp_path
    )
    csv = tmp_path / "un.csv"
    csv.write_text("".join(f"{BASE + i * 60 + 7},{40.0 + i}\n" for i in range(20)))
    tsz("ingest", "m.serie", "--input", "un.csv", cwd=tmp_path)
    proc = tsz("migrate", "m.serie", "--to-format", "f1", cwd=tmp_path, expect_ok=False)
    assert proc.returncode == 2
    assert "abortada ANTES de escrever" in proc.stderr
    assert not (tmp_path / "acervo-m.serie-f22f1").exists()


def test_cli_uc4_allow_lossy_reporta_a_perda(tmp_path):
    """Com consentimento explícito, prossegue — e diz que NÃO foi lossless."""
    tsz(
        "create", "m.serie", "--format", "f2", "--tiers", "60:3600:average", cwd=tmp_path
    )
    csv = tmp_path / "un.csv"
    csv.write_text("".join(f"{BASE + i * 60 + 7},{40.0 + i}\n" for i in range(20)))
    tsz("ingest", "m.serie", "--input", "un.csv", cwd=tmp_path)
    out = as_json(
        tsz("migrate", "m.serie", "--to-format", "f1", "--allow-lossy", cwd=tmp_path)
    )
    assert out["lossless"] is False
    assert out["rejected"] == 20


def test_cli_ca2_f1_para_f2_e_volta(tmp_path):
    """CA-2, na direção EXATA que o critério nomeia: F1 → F2 → F1, bit a bit."""
    tsz("create", "s1", "--format", "f1", "--tiers", "60:3600:average", cwd=tmp_path)
    csv = tmp_path / "a.csv"
    csv.write_text("".join(f"{BASE + i * 60},{40.0 + (i % 7) * 0.5}\n" for i in range(60)))
    tsz("ingest", "s1", "--input", "a.csv", cwd=tmp_path)
    tsz("migrate", "s1", "--to-format", "f2", cwd=tmp_path)
    tsz("migrate", "s1-f12f2", "--to-format", "f1", "--to", "./volta", cwd=tmp_path)

    sys.path.insert(0, str(REPO))
    from tsz.usecases import open_store

    a = list(open_store(tmp_path / "acervo-s1").read(0, -(2**62), 2**62))
    b = list(open_store(tmp_path / "volta").read(0, -(2**62), 2**62))
    assert len(a) == len(b) == 60
    for x, y in zip(a, b):
        assert x.ts == y.ts
        assert struct.pack(">d", x.value) == struct.pack(">d", y.value)


# --- UC-5: validar configuração -------------------------------------------------------


def test_cli_uc5_config_valida(tmp_path):
    out = as_json(
        tsz(
            "validate-config",
            "--tiers",
            "60:15d:average:0.5:0,300:90d:average:0.5:40h",
            cwd=tmp_path,
        )
    )
    assert out["ok"] is True
    assert out["divisibility"] == ["60s -> 300s (5x)"]


@pytest.mark.parametrize(
    "tiers,trecho",
    [
        ("180:15d,600:90d", "3.33"),
        ("60:1h,300:90d:average:0.5:40h", "perda silenciosa"),
        ("60:15d:average,300:90d:average:0.5:1h,3600:730d:average:0.5:2h", "associativa"),
    ],
)
def test_cli_uc5_config_invalida_exit_2(tmp_path, tiers, trecho):
    """A mensagem tem de explicar POR QUE, não só dizer 'inválido'."""
    proc = tsz("validate-config", "--tiers", tiers, cwd=tmp_path, expect_ok=False)
    assert proc.returncode == 2
    assert trecho in proc.stderr


# --- UC-6: medir e reportar -----------------------------------------------------------


def test_cli_uc6_report_bate_com_a_sondagem_da_fase_0(tmp_path):
    """CA-4: a razão medida tem de reproduzir specs/datasets/perfis-de-serie.md (±10%)."""
    esperado = {
        "gauge-stable": 0.33,
        "counter": 2.67,
        "temp-1dec": 6.41,
        "float-noise": 6.63,
    }
    out = as_json(tsz("report", "--n", 7200, "--seed", 7, cwd=tmp_path))
    medido = {r["profile"]: r["bytes_per_point"] for r in out["rows"]}
    for perfil, alvo in esperado.items():
        assert abs(medido[perfil] - alvo) / alvo < 0.10, (
            f"{perfil}: medido {medido[perfil]}, spec diz {alvo} — o codec divergiu de R1"
        )


def test_cli_gen_dataset_ieee_edge(tmp_path):
    proc = tsz("gen-dataset", "ieee-edge", "--n", 11, cwd=tmp_path)
    linhas = proc.stdout.strip().splitlines()
    assert len(linhas) == 11
    assert "nan" in proc.stdout and "inf" in proc.stdout and "5e-324" in proc.stdout


# --- info / journal -------------------------------------------------------------------


def test_cli_info_mostra_bytes_por_tier(acervo):
    """SUS-01/OBS-02: o custo tem de ser visível ANTES de o operador escolher o formato."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    out = as_json(tsz("info", "cpu.load", cwd=acervo))
    assert out["format"] == "f2"
    assert out["tiers"][0]["points"] == 120
    assert out["tiers"][0]["bytes"] > 0
    assert out["tiers"][0]["bytes_per_point"] is not None
    assert out["integrity"]["tier-0"] == "ok"


def test_cli_info_history_le_o_journal(acervo):
    """OBS-06: `journal.read()` existia no contrato e não era exposto."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    out = as_json(tsz("info", "cpu.load", "--history", cwd=acervo))
    ops = [linha["op"] for linha in out["history"]]
    assert "create" in ops and "ingest" in ops


def test_cli_journal_registra_apos_o_commit(acervo):
    """RES-07: a linha é escrita DEPOIS do commit — nunca registra o que não aconteceu."""
    tsz("ingest", "cpu.load", "--input", "pts.csv", cwd=acervo)
    linhas = (acervo / "acervo-cpu.load" / "journal.jsonl").read_text().strip().splitlines()
    assert len(linhas) == 2  # create + ingest
    for linha in linhas:
        assert json.loads(linha)["op"] in ("create", "ingest")


def test_cli_serie_inexistente_da_erro_claro(tmp_path):
    proc = tsz("info", "nao.existe", cwd=tmp_path, expect_ok=False)
    assert proc.returncode == 2
    assert "não é um acervo" in proc.stderr


def test_cli_nome_de_serie_hostil_rejeitado(tmp_path):
    """SEC-01 pela superfície real: o operador não consegue sair do diretório base."""
    proc = tsz("info", "../../etc/passwd", cwd=tmp_path, expect_ok=False)
    assert proc.returncode == 2
    assert "nome de série inválido" in proc.stderr


# --- entrada malformada: NUNCA vazar traceback ---------------------------------------
#
# Classe de erro que a suíte original NÃO cobria: os 26 testes de CLI cobriam erros de
# DOMÍNIO (todos SeriesError) e nenhum cobria o PARSER estourando. Foram 3 defeitos reais
# achados nos casos de borda mecânicos da Fase 6.


def entrada_invalida(proc):
    """Erro de usuário: exit 2, mensagem prefixada por `tsz:`, e ZERO traceback."""
    assert proc.returncode == 2, f"esperava exit 2, veio {proc.returncode}"
    assert "Traceback" not in proc.stderr, "vazou traceback de Python para o operador"
    assert proc.stderr.startswith("tsz:") or "tsz:" in proc.stderr


def test_cli_csv_com_lixo_nao_vaza_traceback(acervo):
    (acervo / "lixo.csv").write_text("abc,xyz\n")
    proc = tsz("ingest", "cpu.load", "--input", "lixo.csv", cwd=acervo, expect_ok=False)
    entrada_invalida(proc)
    assert "linha 1" in proc.stderr


def test_cli_csv_com_uma_coluna_nao_vaza_traceback(acervo):
    (acervo / "curta.csv").write_text("1786464000\n")
    proc = tsz("ingest", "cpu.load", "--input", "curta.csv", cwd=acervo, expect_ok=False)
    entrada_invalida(proc)
    assert "ts,valor" in proc.stderr


def test_cli_arquivo_inexistente_nao_vaza_traceback(acervo):
    proc = tsz(
        "ingest", "cpu.load", "--input", "nao-existe.csv", cwd=acervo, expect_ok=False
    )
    entrada_invalida(proc)
    assert "não consegui ler" in proc.stderr


@pytest.mark.parametrize("duracao", ["xyz", "60:abc", "5x", ""])
def test_cli_duracao_invalida_nao_vaza_traceback(tmp_path, duracao):
    proc = tsz(
        "validate-config", "--tiers", f"60:{duracao}", cwd=tmp_path, expect_ok=False
    )
    entrada_invalida(proc)


def test_cli_csv_vazio_e_sucesso_com_zero_pontos(acervo):
    """Julgamento registrado: arquivo vazio é sucesso com written=0, não erro.

    Consciente do risco de esconder um pipeline quebrado a montante — mas `written: 0`
    no relatório é a informação, e transformar isso em erro impediria ingestão
    incremental legítima de um arquivo que ainda não tem linhas.
    """
    (acervo / "vazio.csv").write_text("")
    out = as_json(tsz("ingest", "cpu.load", "--input", "vazio.csv", cwd=acervo))
    assert out["written"] == 0 and out["rejected"] == 0


def test_cli_comentarios_e_linhas_vazias_sao_ignorados(acervo):
    (acervo / "c.csv").write_text(
        f"# cabeçalho\n\n{BASE},40.0\n\n# meio\n{BASE + 1},41.0\n"
    )
    out = as_json(tsz("ingest", "cpu.load", "--input", "c.csv", cwd=acervo))
    assert out["written"] == 2


def test_cli_stdin_funciona(acervo):
    proc = subprocess.run(
        [sys.executable, "-m", "tsz.cli", "--base", ".", "ingest", "cpu.load", "--input", "-"],
        cwd=acervo,
        input=f"{BASE},42.0\n",
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["written"] == 1


def test_cli_read_intervalo_invertido_e_vazio(acervo):
    """Julgamento registrado: [100, 50) é vazio por definição de intervalo semiaberto.

    Sai com 0 e não imprime nada — consistente com a regra do contrato, e não um erro.
    """
    proc = tsz("read", "cpu.load", "--from", 100, "--to", 50, cwd=acervo)
    assert proc.stdout.strip() == ""


def test_cli_tier_inexistente_da_erro_de_dominio(acervo):
    proc = tsz("read", "cpu.load", "--tier", 9, "--from", 0, "--to", 99, cwd=acervo, expect_ok=False)
    entrada_invalida(proc)
    assert "tier 9 não existe" in proc.stderr
