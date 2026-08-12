"""Agrega as predições cegas dos 12 projetos e confronta com a coluna do §2.

    python3 agregar_predicoes.py

Lê todas as rodadas salvas em `cego/*-predicao-*-rN.json` e responde três coisas:

1. **Concordância com o §2.** A coluna "lentes esperadas" do BATCH-PROTOCOL é a
   predição da autora, feita no desenho do lote e congelada. O modelo nunca a viu.
   Recall = das lentes que o §2 previu, quantas o modelo também previu.

2. **Ativação além do §2.** Quantas lentes o modelo ativa que o §2 não previu. Se
   for sistemático, o suspeito não é o modelo: são os critérios de ativação, largos
   demais para separar condicional de universal.

3. **Cobertura projetada.** Em quantos projetos cada condicional ativaria segundo o
   modelo, contra os ≥3 que o desenho do §2 exige. Diz se a cobertura planejada
   sobrevive ao que de fato vai ativar.

Nada aqui substitui a declaração da Fase 2 — que é o dado real. Isto é a predição
contra a qual ela será comparada, e existe antes dela por construção.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES  # noqa: E402
from preparar import PROJETOS  # noqa: E402

SAIDA = Path(__file__).resolve().parent / "cego"
NOMES = [n for n, _, _ in LENTES]

# Siglas do §2 -> nome canônico, para ler a coluna "lentes esperadas".
SIGLA_PARA_NOME = {
    "RES": "Resilience", "UX": "UI/UX", "MIG": "Migration / Coexistence",
    "SUS": "Sustainability / Proportionality", "ETI": "Ethical / Human Impact",
    "PRO": "Process / Workflow", "GOV": "Governance / Accountability",
    "OBS": "Observability / Operability", "CTR": "Control Engineering",
    "JOG": "Game Theory", "LIN": "Linguistics / Grammar", "MEC": "Mechanical Engineering",
}
NOME_PARA_SIGLA = {v: k for k, v in SIGLA_PARA_NOME.items()}


def _esperadas(coluna: str) -> set[str]:
    return {SIGLA_PARA_NOME[s.strip()] for s in coluna.split("·") if s.strip() in SIGLA_PARA_NOME}


def _rodadas(task_id: str, modelo: str) -> list[dict]:
    """Rodadas de UM preditor. O filtro por modelo não é conveniência: sem ele o glob
    mistura Qwen e Kimi na mesma contagem de votos, e a 'estabilidade' de um vira
    concordância entre os dois — outra medida, com o mesmo nome."""
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(SAIDA.glob(f"{task_id}-predicao-*{modelo}*-r*.json"))]


def main(argv=()) -> int:
    modelo = argv[argv.index("--modelo") + 1] if "--modelo" in argv else "qwen3.6"
    print(f"<!-- preditor: {modelo} -->")
    dados = {}
    for task_id, _, coluna in PROJETOS:
        rodadas = _rodadas(task_id, modelo)
        if not rodadas:
            continue
        votos = defaultdict(int)
        for r in rodadas:
            for l in r["lentes"]:
                if l["ativa"]:
                    votos[l["lente"]] += 1
        n = len(rodadas)
        dados[task_id] = {
            "n": n,
            "esperadas": _esperadas(coluna),
            "sempre": {x for x in NOMES if votos[x] == n},
            "oscilou": {x for x in NOMES if 0 < votos[x] < n},
            "modulos": [r["modulos_estimados"] for r in rodadas],
        }

    if not dados:
        print(f"Nenhuma predição de '{modelo}' em {SAIDA}.", file=sys.stderr)
        return 1

    print(f"# Predição cega × coluna do §2 — {len(dados)} de 12 projetos\n")
    print("Modelo cego à coluna do §2: viu só o ENUNCIADO.md e a definição das 12 lentes.\n")

    print("| projeto | §2 esperava | confirmadas | §2 previu e o modelo não | modelo previu além | oscilou |")
    print("|---|---|---|---|---|---|")
    tot_esp = tot_conf = tot_alem = 0
    for task_id, d in dados.items():
        conf = d["esperadas"] & d["sempre"]
        perdidas = d["esperadas"] - d["sempre"] - d["oscilou"]
        alem = d["sempre"] - d["esperadas"]
        tot_esp += len(d["esperadas"])
        tot_conf += len(conf)
        tot_alem += len(alem)
        sig = lambda s: " · ".join(sorted(NOME_PARA_SIGLA[x] for x in s)) or "—"  # noqa: E731
        print(f"| {task_id} | {sig(d['esperadas'])} | {len(conf)}/{len(d['esperadas'])} | "
              f"{sig(perdidas)} | {sig(alem)} | {sig(d['oscilou'])} |")

    print(f"\n**Recall do §2:** {tot_conf}/{tot_esp} lentes previstas pela autora foram "
          f"confirmadas de forma estável pelo modelo cego.")
    print(f"**Ativação além do §2:** {tot_alem} ativações estáveis que o §2 não previu.\n")

    print("## Cobertura projetada por lente condicional\n")
    print("O §2 exige ≥3 projetos por condicional, senão não se distingue 'não detecta' de")
    print("'não foi exercitada'. `§2` é o planejado; `modelo` é o que de fato ativaria.\n")
    print("| lente | §2 | modelo (estável) | + oscilando |")
    print("|---|---|---|---|")
    for nome in NOMES:
        p_esp = sum(1 for d in dados.values() if nome in d["esperadas"])
        p_sem = sum(1 for d in dados.values() if nome in d["sempre"])
        p_osc = sum(1 for d in dados.values() if nome in d["oscilou"])
        alerta = "" if p_sem >= 3 else "  ← abaixo de 3"
        print(f"| {NOME_PARA_SIGLA[nome]} {nome} | {p_esp} | {p_sem}{alerta} | {p_osc} |")

    osc_total = sum(len(d["oscilou"]) for d in dados.values())
    print(f"\n## Estabilidade\n")
    print(f"Oscilações: {osc_total} em {len(dados)} projetos × 12 lentes = "
          f"{100 * osc_total / (len(dados) * 12):.0f}% das decisões.\n")
    for task_id, d in sorted(dados.items(), key=lambda kv: -len(kv[1]["oscilou"])):
        if d["oscilou"]:
            print(f"  {task_id:<18} {len(d['oscilou'])}/12  "
                  f"{' · '.join(sorted(NOME_PARA_SIGLA[x] for x in d['oscilou']))}")
    print("\nOscilação alta num projeto e baixa noutro, com o mesmo modelo e a mesma")
    print("temperatura, mede o ENUNCIADO, não o modelo: quanto sinal aquela frase carrega.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
