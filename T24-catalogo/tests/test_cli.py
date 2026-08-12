"""CA-13, CA-14, CA-21, CA-22 e codigos de saida — a CLI como PROCESSO REAL.

Ferramenta escolhida na Fase 6: pytest + subprocess. Invoca o ponto de entrada de
verdade e assere stdout, stderr e codigo de saida — chamar main(argv) em processo seria
testar quase a CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

OK, CATALOGO_INVALIDO, ERRO_DE_USO = 0, 1, 2


def t24(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "t24.cli", *args],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )


# ------------------------------------------------------------------ codigos de saida


def test_exit_code_catalogo_valido():
    assert t24("validar").returncode == OK


def test_exit_code_catalogo_invalido():
    r = t24("--catalogo", str(FIXTURES / "ciclo"), "validar")
    assert r.returncode == CATALOGO_INVALIDO
    assert r.stderr.strip()  # o erro vai para stderr, nao stdout


def test_exit_code_dataset_inexistente():
    assert t24("impacto", "vendas.inexistente").returncode == ERRO_DE_USO


def test_exit_code_diretorio_inexistente():
    r = t24("--catalogo", "/caminho/que/nao/existe", "validar")
    assert r.returncode == ERRO_DE_USO
    assert "nao encontrado" in r.stderr


# ----------------------------------------------------------- bordas visiveis (CA-13/14)


def test_folha_imprime_frase_explicita():
    """CA-13 / UX-03: silencio seria indistinguivel de falha do comando."""
    r = t24("impacto", "logistica.rastreio")
    assert r.returncode == OK
    assert "nenhum impacto a jusante" in r.stdout


def test_inexistente_tem_mensagem_distinta_de_vazio():
    """CA-14 / UX-02: as duas situacoes NAO podem produzir a mesma saida."""
    vazio = t24("impacto", "logistica.rastreio")
    inexistente = t24("impacto", "vendas.inexistente")
    assert vazio.returncode != inexistente.returncode
    assert "nao esta declarado" in inexistente.stderr
    assert "nao esta declarado" not in vazio.stdout


# ----------------------------------------------------------------- saida dupla (CA-21)


def test_json_traz_os_mesmos_conjuntos_que_o_texto():
    texto = t24("impacto", "vendas.pedidos")
    dados = json.loads(t24("impacto", "vendas.pedidos", "--json").stdout)

    assert len(dados["afetados"]) == 6
    assert len(dados["responsaveis"]) == 4
    # Todo dataset citado no JSON aparece tambem na saida texto.
    for id_ in dados["afetados"]:
        assert id_ in texto.stdout


def test_json_aceito_nas_duas_posicoes():
    """Defeito encontrado pela micro-checagem S7 na Fase 5: --json so funcionava antes
    do subcomando, e depois do subcomando e a ordem que o usuario escreve."""
    antes = t24("--json", "impacto", "vendas.pedidos")
    depois = t24("impacto", "vendas.pedidos", "--json")
    assert antes.returncode == depois.returncode == OK
    assert json.loads(antes.stdout) == json.loads(depois.stdout)


def test_json_de_violacoes_e_parseavel():
    r = t24("--catalogo", str(FIXTURES / "ciclo"), "validar", "--json")
    dados = json.loads(r.stderr)
    assert dados["valido"] is False
    assert len(dados["violacoes"]) == 1


# -------------------------------------------------------------------- ressalva (CA-22)


def test_ressalva_aparece_uma_unica_vez_no_texto():
    """CA-22 / UX-06: repetida em toda linha viraria ruido."""
    saida = t24("impacto", "vendas.pedidos").stdout
    assert saida.count("limite inferior") == 1


def test_ressalva_e_campo_estruturado_no_json():
    dados = json.loads(t24("impacto", "vendas.pedidos", "--json").stdout)
    assert dados["escopo"] == "declarado"


# ------------------------------------------------------------- agrupamento por dono (UX-01)


def test_saida_texto_agrupa_por_dono():
    """UX-01: a promessa e 'quem avisar'; lista plana entregaria o dado, nao a resposta."""
    saida = t24("impacto", "vendas.pedidos").stdout
    assert "Ana Costa <ana.costa@empresa.com>" in saida
    # Os dois datasets da Ana aparecem indentados sob o nome dela, nao soltos.
    linhas = saida.splitlines()
    i = next(n for n, linha in enumerate(linhas) if "Ana Costa" in linha)
    seguintes = [linhas[i + 1].strip(), linhas[i + 2].strip()]
    assert seguintes == ["- logistica.envios", "- logistica.rastreio"]
