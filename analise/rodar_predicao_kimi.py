"""Roda a predição cega no Kimi (Moonshot), N vezes por projeto.

    export MOONSHOT_API_KEY='sk-...'          # a chave fica na sua máquina
    python3 rodar_predicao_kimi.py            # os 12 projetos, 3 rodadas cada
    python3 rodar_predicao_kimi.py T13-autoscaler T05-etl
    python3 rodar_predicao_kimi.py --modelo kimi-k2.6 --n 3

Espelha `rodar_predicao.py` (Qwen local) de propósito: MESMO pacote, MESMA contagem
de rodadas, MESMA temperatura. Se o protocolo diferisse entre os dois preditores, a
discordância entre eles mediria a diferença de protocolo, não de julgamento.

Por que um segundo preditor: até aqui o lote tem UM só (o Qwen local). A coluna
"lentes esperadas" do BATCH-PROTOCOL §2 não conta como segundo — ela foi escrita para
DESENHAR o lote (escolher projetos que ativassem cada condicional em ≥3), não para
prever o que a Fase 2 faria, e não traz o "por qual sinal" que o §3 define como a
medição. Com dois preditores independentes, a comparação predição × declaração passa
a ter concordância entre avaliadores; com um, não tem.

O Kimi é de outra família que o Qwen, o que dá independência real — o
`qwen3-coder:30b` local seria a mesma linhagem.

Custo estimado: ~36 chamadas, ~2k tokens cada. Em `kimi-k3` ($3/$15 por M), menos de
US$ 1 pelos 12 projetos.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES, PACOTE  # noqa: E402
from preparar import PROJETOS  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"
BASE_URL = "https://api.moonshot.ai/v1/chat/completions"
NOMES = [n for n, _, _ in LENTES]

INSTRUCAO_JSON = (
    "\n\nResponda EXCLUSIVAMENTE com o objeto JSON pedido, sem cercas de código, sem "
    "preâmbulo e sem comentário. As 12 lentes têm que aparecer, com o nome exatamente "
    "como está na tabela."
)


def _prompt(task_id: str) -> str:
    enunciado = RO3 / task_id / "ENUNCIADO.md"
    linhas = enunciado.read_text(encoding="utf-8").splitlines()
    descricao = next(l.strip() for l in linhas[1:] if l.strip() and not l.startswith("#"))
    tabela = "\n".join(f"| {n} | {p} | {q} |" for n, p, q in LENTES)
    return PACOTE.format(task_id=task_id, descricao=descricao, tabela=tabela) + INSTRUCAO_JSON


def _chamar(chave: str, modelo: str, prompt: str, temp: float) -> dict:
    corpo = json.dumps({
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        BASE_URL, data=corpo,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {chave}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        resposta = json.loads(r.read())
    return json.loads(resposta["choices"][0]["message"]["content"])


def _validar(resp: dict) -> list[str]:
    """O Kimi não aceita schema como o Ollama, então a validação é aqui.
    Formato inválido é erro visível, nunca resultado parcial silencioso."""
    problemas = []
    lentes = resp.get("lentes")
    if not isinstance(lentes, list):
        return ["resposta sem a lista `lentes`"]
    vistas = [l.get("lente") for l in lentes]
    desconhecidas = [v for v in vistas if v not in NOMES]
    if desconhecidas:
        problemas.append(f"nome(s) fora dos 12 canônicos: {', '.join(map(str, desconhecidas))}")
    faltando = set(NOMES) - set(vistas)
    if faltando:
        problemas.append(f"lente(s) ausente(s): {', '.join(sorted(faltando))}")
    if len(vistas) != len(set(vistas)):
        problemas.append("lente repetida")
    if not isinstance(resp.get("modulos_estimados"), int):
        problemas.append("`modulos_estimados` ausente ou não inteiro")
    for l in lentes:
        if not isinstance(l.get("ativa"), bool):
            problemas.append(f"`ativa` não booleano em {l.get('lente')}")
        if not str(l.get("sinal", "")).strip():
            problemas.append(f"`sinal` vazio em {l.get('lente')}")
    return problemas


def main(argv):
    chave = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not chave:
        print("ERRO: defina MOONSHOT_API_KEY (ou KIMI_API_KEY) no ambiente.\n"
              "  export MOONSHOT_API_KEY='sk-...'", file=sys.stderr)
        return 1

    modelo = argv[argv.index("--modelo") + 1] if "--modelo" in argv else "kimi-k3"
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    temp = float(argv[argv.index("--temp") + 1] if "--temp" in argv else 0.7)
    alvos = [a for a in argv if not a.startswith("--") and a not in (modelo, str(n), str(temp))]
    if not alvos:
        alvos = [t for t, _, _ in PROJETOS]

    SAIDA.mkdir(exist_ok=True)
    print(f"modelo {modelo} · temperatura {temp} · {n} rodadas · {len(alvos)} projeto(s)\n")
    falhou = []

    for task_id in alvos:
        if not (RO3 / task_id / "ENUNCIADO.md").exists():
            print(f"  {task_id}: sem ENUNCIADO.md — pulado")
            falhou.append(task_id)
            continue
        prompt = _prompt(task_id)
        votos, ok = Counter(), 0
        for i in range(1, n + 1):
            try:
                r = _chamar(chave, modelo, prompt, temp)
            except urllib.error.HTTPError as e:
                print(f"  {task_id} r{i}: HTTP {e.code} — {e.read()[:160].decode(errors='replace')}")
                falhou.append(f"{task_id}#{i}")
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  {task_id} r{i}: {type(e).__name__}: {e}")
                falhou.append(f"{task_id}#{i}")
                continue

            problemas = _validar(r)
            if problemas:
                print(f"  {task_id} r{i}: ⚠ {'; '.join(problemas)}")
                falhou.append(f"{task_id}#{i}")
                continue

            (SAIDA / f"{task_id}-predicao-{modelo.replace(':', '_')}-r{i}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            for l in r["lentes"]:
                if l["ativa"]:
                    votos[l["lente"]] += 1
            ok += 1
            time.sleep(1)  # cortesia com o rate limit

        if ok:
            estaveis = sorted(x for x in NOMES if votos[x] == ok)
            oscilou = sorted(x for x in NOMES if 0 < votos[x] < ok)
            print(f"  {task_id:<18} {ok}/{n} rodadas · estáveis: {len(estaveis)} · "
                  f"oscilou: {len(oscilou)}{'  ' + ', '.join(oscilou) if oscilou else ''}")

    print()
    if falhou:
        print(f"⚠ {len(falhou)} chamada(s)/projeto(s) com problema: {', '.join(falhou)}")
        print("  Nada parcial foi gravado para elas — reexecute só esses alvos.")
    print(f"Respostas em {SAIDA}. Depois:  python3 agregar_predicoes.py --modelo {modelo}")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
