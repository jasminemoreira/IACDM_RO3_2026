"""Reestimativa das lentes com os gatilhos **Y** — a taxonomia corrigida.

    OPENAI_API_KEY=... python3 reestimar_Y.py T21-certificados --n 3

POR QUE EXISTE
--------------
O `DIFF-TAXONOMICO-GATILHOS-CONDICIONAIS.md` propõe reescrever nove dos doze gatilhos
condicionais, e registra as consequências de ativação como **"direção projetada, não
medida"**. Isso não precisa ficar projetado: os doze pacotes de estimativa são
reproduzíveis byte a byte a partir da V(1) congelada, então dá para medir a ativação de Y
no mesmo corpus.

O QUE ISTO É, E O QUE NÃO É
----------------------------
**NÃO é validação da RO3.** As declarações da Fase 2 foram feitas sob os gatilhos X. Este
script não produz um novo "acerto contra a Fase 2" — produz a **ativação medida de Y**,
para substituir a projeção à mão por número.

Comparar a ativação de Y com a declaração da Fase 2 seria comparar dois instrumentos
diferentes. O que se compara aqui é **X contra Y, no mesmo leitor e no mesmo pacote**.

CONTROLE
--------
A única diferença entre o pacote X e o pacote Y é o **texto do gatilho** das nove lentes
reescritas. Mesma arquitetura V(1), mesma pergunta central, mesma regra de ativação, mesmo
template, mesmo modelo, mesmo número de rodadas. SUS, UI/UX e GOV **não** foram reescritas
no diff — elas já receberam a forma-condição na v0.12.9 —, então em Y ficam idênticas a X,
e servem de controle interno: se a ativação delas mudar, é ruído do modelo, não efeito da
reescrita.

Os gatilhos Y são lidos do próprio diff, não transcritos, para não introduzir erro de cópia.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES, REGRA_ATIVACAO  # noqa: E402
from reestimar_lentes import PACOTE, SAIDA, _kimicode, _remoto, fatiar  # noqa: E402
from ro3_parser import SIGLA, carregar  # noqa: E402

RO3 = Path(__file__).resolve().parent.parent
DIFF = Path("/mnt/c/Users/jasmi/OneDrive/Documents/Data Science/IACDM/"
            "DIFF-TAXONOMICO-GATILHOS-CONDICIONAIS.md")
NOMES = [n for n, _, _ in LENTES]


def gatilhos_Y() -> dict[str, str]:
    """Lê os gatilhos Y do diff. Falha alto se o formato mudar — nunca cai para X em
    silêncio, porque isso produziria uma 'medição de Y' que na verdade mediu X."""
    if not DIFF.is_file():
        raise SystemExit(f"ERRO: diff não encontrado em {DIFF}")
    texto = DIFF.read_text(encoding="utf-8")
    Y: dict[str, str] = {}
    secao = None
    for linha in texto.split("\n"):
        m = re.match(r"^### [A-Z]{2,3} — (.+?)\s+·", linha)
        if m:
            secao = m.group(1).strip()
        m2 = re.match(r"^- \*\*Y:\*\* `(.+)`\s*$", linha)
        if m2 and secao:
            Y[secao] = m2.group(1)

    # Y2 — as revisadas depois da primeira medição, que vivem no cabeçalho do diff em
    # bloco de citação e podem ocupar várias linhas. SOBRESCREVEM o Y correspondente.
    # Sem isto, "medir Y2" mediria Y em silêncio, que é o pior desfecho possível.
    SIG = {"ETI": "Ethical / Human Impact", "MIG": "Migration / Coexistence",
           "CTR": "Control Engineering"}
    corpo = "\n".join(l.lstrip("> ").rstrip() for l in texto.split("\n"))
    for sig, nome in SIG.items():
        m = re.search(rf"\*\*{sig}[^:]*:\*\*\s*`([^`]+)`", corpo, re.S)
        if m:
            Y[nome] = " ".join(m.group(1).split())
    desconhecidas = set(Y) - set(NOMES)
    if desconhecidas:
        raise SystemExit(f"ERRO: o diff nomeia lentes fora das 12: {desconhecidas}")
    if not Y:
        raise SystemExit("ERRO: nenhuma reescrita extraída — o formato do diff mudou.")
    return Y


def main(argv):
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    task_id = argv[0]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    modelo = argv[argv.index("--modelo") + 1] if "--modelo" in argv else "gpt-5.4-2026-03-05"
    # Rótulo do conjunto de gatilhos. NUNCA reaproveitar: sobrescrever a medição
    # anterior apagaria a linha de base contra a qual esta é comparada.
    rot = argv[argv.index("--rotulo") + 1] if "--rotulo" in argv else "Y"

    Y = gatilhos_Y()
    ws = RO3 / task_id
    arq, versao = fatiar((ws / "specs" / "technical" / "architecture.md")
                         .read_text(encoding="utf-8"), "1")
    linhas = (ws / "ENUNCIADO.md").read_text(encoding="utf-8").splitlines()
    descricao = next(l.strip() for l in linhas[1:] if l.strip() and not l.startswith("#"))

    # a ÚNICA diferença para o pacote X: o texto do gatilho das nove reescritas
    tabela = "\n".join(f"| {nome} | {pergunta} | {Y.get(nome, gatilho)} |"
                       for nome, pergunta, gatilho in LENTES)
    prompt = PACOTE.format(task_id=task_id, descricao=descricao, arquitetura=arq,
                           tabela=tabela, regra=REGRA_ATIVACAO)

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / f"{task_id}-{rot}-V{versao}-pacote.md").write_text(prompt, encoding="utf-8")

    votos, ok = Counter(), 0
    for i in range(1, n + 1):
        r = _kimicode(prompt) if modelo == "kimicode" else _remoto(prompt, modelo, i)
        (SAIDA / f"{task_id}-{rot}-V{versao}-{modelo.replace(':', '_')}-r{i}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        for l in r["lentes"]:
            if l["ativa"]:
                votos[l["lente"]] += 1
        ok += 1

    proj = carregar(ws)
    it1 = set(proj.condicionais_por_iteracao[min(proj.condicionais_por_iteracao)])
    estavel = {x for x in NOMES if votos[x] == ok}
    print(f"{task_id} · {modelo} · {ok} rodadas · gatilhos {rot}")
    print(f"  ativas estáveis: {len(estavel)}/12 — "
          f"{', '.join(sorted(SIGLA[x] for x in estavel)) or '—'}")
    print(f"  (Fase 2 sob X declarou {len(it1)}: "
          f"{', '.join(sorted(SIGLA[x] for x in it1))})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
