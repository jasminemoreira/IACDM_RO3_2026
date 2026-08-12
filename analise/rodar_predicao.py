"""Roda a predição cega num modelo local via Ollama, N vezes, e mede a estabilidade.

    python3 rodar_predicao.py T01-ratelimit
    python3 rodar_predicao.py T01-ratelimit --n 3 --modelo qwen3.6:27b --temp 0.7

DUAS COISAS SEPARADAS, DE PROPÓSITO
-----------------------------------
**Formato** é garantido pelo `format` do Ollama: a saída é restringida a conformar
com um schema JSON, e o nome da lente é um `enum` dos 12 canônicos. Nenhuma resposta
malformada chega à análise — não por obediência do modelo, por construção.

**Estabilidade de julgamento** é medida rodando N vezes com temperatura > 0. Este é
o ponto sutil: com `temperature: 0` as N respostas saem idênticas por determinismo,
não por confiabilidade, e o teste não mediria nada. É a temperatura exposta que
revela se o modelo oscila entre `true` e `false` na mesma lente lendo o mesmo
enunciado.

Se ele oscilar muito, a confiabilidade intra-avaliador é baixa e comparar a predição
dele com qualquer outra coisa perde sentido — discordância viraria ruído do preditor,
não evidência sobre o sinal do projeto.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES, PACOTE  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"
OLLAMA = "http://localhost:11434/api/chat"
NOMES = [n for n, _, _ in LENTES]

SCHEMA = {
    "type": "object",
    "properties": {
        "projeto": {"type": "string"},
        "modulos_estimados": {"type": "integer"},
        "lentes": {
            "type": "array",
            "minItems": 12, "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "lente": {"type": "string", "enum": NOMES},
                    "ativa": {"type": "boolean"},
                    "sinal": {"type": "string"},
                },
                "required": ["lente", "ativa", "sinal"],
            },
        },
    },
    "required": ["projeto", "modulos_estimados", "lentes"],
}


def _prompt(task_id: str) -> str:
    enunciado = RO3 / task_id / "ENUNCIADO.md"
    linhas = enunciado.read_text(encoding="utf-8").splitlines()
    descricao = next(l.strip() for l in linhas[1:] if l.strip() and not l.startswith("#"))
    tabela = "\n".join(f"| {n} | {p} | {q} |" for n, p, q in LENTES)
    return PACOTE.format(task_id=task_id, descricao=descricao, tabela=tabela)


def _chamar(modelo: str, prompt: str, temp: float, seed: int) -> dict:
    corpo = json.dumps({
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "format": SCHEMA,
        "options": {"temperature": temp, "seed": seed},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=corpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


def _validar(resp: dict) -> list[str]:
    problemas = []
    vistas = [l["lente"] for l in resp.get("lentes", [])]
    faltando = set(NOMES) - set(vistas)
    if faltando:
        problemas.append(f"lentes ausentes: {', '.join(sorted(faltando))}")
    if len(vistas) != len(set(vistas)):
        problemas.append("lente repetida na resposta")
    vazios = [l["lente"] for l in resp.get("lentes", []) if not l.get("sinal", "").strip()]
    if vazios:
        problemas.append(f"sinal vazio em: {', '.join(vazios)}")
    return problemas


def main(argv):
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    task_id = argv[0]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    modelo = argv[argv.index("--modelo") + 1] if "--modelo" in argv else "qwen3.6:27b"
    temp = float(argv[argv.index("--temp") + 1] if "--temp" in argv else 0.7)

    if not (RO3 / task_id / "ENUNCIADO.md").exists():
        print(f"ERRO: {task_id} não tem ENUNCIADO.md.", file=sys.stderr)
        return 1

    SAIDA.mkdir(exist_ok=True)
    prompt = _prompt(task_id)
    print(f"modelo {modelo} · temperatura {temp} · {n} rodadas · {task_id}\n")

    respostas = []
    for i in range(1, n + 1):
        try:
            r = _chamar(modelo, prompt, temp, seed=i)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  rodada {i}: FALHA na chamada ao Ollama — {e}", file=sys.stderr)
            return 1
        problemas = _validar(r)
        ativas = sorted(l["lente"] for l in r["lentes"] if l["ativa"])
        print(f"  rodada {i}: {len(ativas)}/12 ativas, {r['modulos_estimados']} módulos"
              + (f"  ⚠ {'; '.join(problemas)}" if problemas else ""))
        (SAIDA / f"{task_id}-predicao-{modelo.replace(':', '_')}-r{i}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        respostas.append(r)

    # Estabilidade: por lente, em quantas das N rodadas saiu `true`.
    print(f"\n## Estabilidade entre as {n} rodadas\n")
    votos = Counter()
    for r in respostas:
        for l in r["lentes"]:
            if l["ativa"]:
                votos[l["lente"]] += 1

    instaveis = []
    for nome in NOMES:
        v = votos[nome]
        marca = "sempre" if v == n else ("nunca" if v == 0 else f"{v}/{n} ← OSCILOU")
        if 0 < v < n:
            instaveis.append(nome)
        print(f"  {nome:<34} {marca}")

    print()
    if instaveis:
        print(f"⚠ {len(instaveis)} de 12 lentes oscilaram: {', '.join(instaveis)}.")
        print("  A confiabilidade intra-avaliador é parcial. Predições em lentes que oscilam\n"
              "  não sustentam comparação — ali a discordância mede o preditor, não o projeto.")
    else:
        print("Nenhuma lente oscilou: o julgamento é estável nesta temperatura, e a\n"
              "predição pode ser comparada com a declaração da Fase 2.")

    consenso = sorted(nome for nome in NOMES if votos[nome] > n / 2)
    print(f"\nConsenso (maioria das rodadas): {', '.join(consenso) if consenso else 'nenhuma lente'}")
    mods = [r["modulos_estimados"] for r in respostas]
    print(f"Módulos estimados: {mods}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
