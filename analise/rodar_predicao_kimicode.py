"""Roda a predição cega no Kimi Code CLI, em sandbox isolado, N vezes por projeto.

    python3 rodar_predicao_kimicode.py T14-loadbalancer T15-interchange
    python3 rodar_predicao_kimicode.py --todos --n 3

O ISOLAMENTO É O PONTO
----------------------
O Kimi Code é um agente com shell e acesso a arquivos. Como preditor cego isso o
desqualificaria: `RO3/PROJETOS.md` traz a coluna com as lentes esperadas, e a árvore
do projeto inteira é legível. Já falhou uma vez — um pacote colado nele foi executado
como comando em vez de respondido.

Aqui cada rodada acontece num diretório temporário **contendo apenas o pacote**. O
acesso a arquivos continua existindo e não encontra nada para vazar. É o mesmo
isolamento que o Ollama tem por construção, tornado explícito.

POR QUE UM RÓTULO SEPARADO DO `kimi` ANTERIOR
---------------------------------------------
As predições rotuladas `kimi` vieram do chat em kimi.com, coladas à mão. Estas vêm do
Kimi Code CLI. Mesmo nome comercial, caminhos diferentes e possivelmente modelos
diferentes por baixo. Juntar as duas sob um rótulo só reabriria exatamente o problema
que a v0.12.1 fechou na coluna de lente: dois valores distintos agregados como se
fossem um. Por isso o sufixo é `kimicode`, e o agregador filtra por preditor.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingerir_kimi import extrair  # noqa: E402
from predicao_cega import LENTES  # noqa: E402
from preparar import PROJETOS  # noqa: E402
from rodar_predicao_kimi import _validar  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "cego"
KIMI = Path.home() / ".kimi-code" / "bin" / "kimi"
NOMES = [n for n, _, _ in LENTES]
ROTULO = "kimicode"


def uma_rodada(pacote: Path, timeout: int = 600) -> dict | None:
    """Uma execução headless, num sandbox que contém só o pacote."""
    with tempfile.TemporaryDirectory(prefix="kimi-sb-") as sb:
        alvo = Path(sb) / "pacote.md"
        shutil.copyfile(pacote, alvo)
        try:
            r = subprocess.run([str(KIMI), "-p", alvo.read_text(encoding="utf-8")],
                               cwd=sb, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"      timeout após {timeout}s")
            return None
        objs = extrair(r.stdout)
        if not objs:
            print(f"      sem JSON na resposta ({len(r.stdout)} chars)")
            return None
        return objs[-1]


def main(argv):
    if not KIMI.exists():
        print(f"ERRO: {KIMI} não encontrado.", file=sys.stderr)
        return 1
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    alvos = ([t for t, _, _ in PROJETOS] if "--todos" in argv
             else [a for a in argv if not a.startswith("--") and a != str(n)])
    if not alvos:
        print(__doc__)
        return 2

    SAIDA.mkdir(exist_ok=True)
    print(f"Kimi Code {ROTULO} · {n} rodada(s) · {len(alvos)} projeto(s) · sandbox por rodada\n")
    falhas = []

    for task_id in alvos:
        pacote = SAIDA / f"{task_id}-predicao.md"
        if not pacote.exists():
            print(f"  {task_id}: sem pacote — pulado")
            falhas.append(task_id)
            continue
        votos, ok = Counter(), 0
        for i in range(1, n + 1):
            r = uma_rodada(pacote)
            if r is None:
                falhas.append(f"{task_id}#{i}")
                continue
            problemas = _validar(r)
            if problemas:
                print(f"  {task_id} r{i}: ⚠ {'; '.join(problemas)} — não gravada")
                falhas.append(f"{task_id}#{i}")
                continue
            (SAIDA / f"{task_id}-predicao-{ROTULO}-r{i}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            for l in r["lentes"]:
                if l["ativa"]:
                    votos[l["lente"]] += 1
            ok += 1
        if ok:
            osc = sorted(x for x in NOMES if 0 < votos[x] < ok)
            est = sorted(x for x in NOMES if votos[x] == ok)
            print(f"  {task_id:<18} {ok}/{n} · estáveis {len(est)} · "
                  f"oscilou {len(osc)}{'  ' + ', '.join(osc) if osc else ''}")

    print()
    if falhas:
        print(f"⚠ falhas: {', '.join(falhas)}")
    print(f"Depois:  python3 agregar_predicoes.py --modelo {ROTULO}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
