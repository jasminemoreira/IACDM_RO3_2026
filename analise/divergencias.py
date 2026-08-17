"""Denominadores e oportunidade estrutural das divergências de ativação.

Uso:
    python3 divergencias.py

A PERGUNTA
----------
A figura de divergências traz dois contadores por lente: `a` = a Fase 2 ativou e o
estimador externo recusou; `b` = o externo ativou e a Fase 2 recusou. Cinco lentes têm
`b = 0`, e disso se lê "as divergências correm numa direção só".

A leitura só vale se o sentido inverso **tinha onde ocorrer**. `b` exige um projeto em
que a Fase 2 tenha RECUSADO a lente na iteração 1. Se ela foi declarada nos doze, não
existe projeto onde `b` pudesse ser diferente de zero, e o zero é **estrutural** — não
é evidência de nada sobre a lente.

Este módulo separa as duas coisas e dá o denominador exato de cada contador.

O DENOMINADOR
-------------
A unidade de decisão é **estimador × projeto**, não estimador × projeto × rodada. As
três rodadas consolidam ANTES: uma lente é decidida num projeto quando as três
concordam — 3/3 conta como ativa, 0/3 como inativa. Qualquer resultado intermediário é
**oscilação** e não entra em contagem nenhuma, nem no numerador nem no denominador.

Logo, o máximo por lente é 3 estimadores × 12 projetos = 36, e o denominador real é 36
menos as oscilações daquela lente. O denominador de cada DIREÇÃO é menor ainda, porque
cada uma só pode ocorrer no subconjunto de projetos com a declaração correspondente:

    a  só pode ocorrer onde a Fase 2 DECLAROU a lente na iteração 1
    b  só pode ocorrer onde a Fase 2 RECUSOU  a lente na iteração 1

ITERAÇÃO 1, NÃO A UNIÃO
-----------------------
A comparação é contra a declaração da iteração 1 — a que o declarante fez com a V(1) à
vista, que é a arquitetura que o estimador cego recebeu. Contra a união das iterações
seria comparar leituras de arquiteturas diferentes. Isso importa aqui: a cobertura
reportada no §0 do RESULTADO é a união, e para três lentes ela difere da iteração 1.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from figuras import CEGO, ESTIMADORES, divergencias, projetos   # noqa: E402
from predicao_cega import LENTES                                # noqa: E402
from ro3_parser import SIGLA, carregar                          # noqa: E402

NOMES = [n for n, _, _ in LENTES]


def decisoes():
    """(lente, projeto) -> declarado na it1?  e  (lente, projeto, estimador) -> 3/3, 0/3 ou None."""
    declarado, estavel = {}, {}
    for ws in projetos():
        t, proj = ws.name, carregar(ws)
        it1 = min(proj.condicionais_por_iteracao)
        decl = set(proj.condicionais_por_iteracao[it1])
        for l in NOMES:
            declarado[(l, t)] = l in decl
        for est, infixo in ESTIMADORES.items():
            votos: Counter = Counter()
            for r in (1, 2, 3):
                arq = CEGO / f"{t}-reestimativa-V1-{infixo}-r{r}.json"
                for e in json.loads(arq.read_text(encoding="utf-8"))["lentes"]:
                    if e["ativa"]:
                        votos[e["lente"]] += 1
            for l in NOMES:
                estavel[(l, t, est)] = (True if votos[l] == 3
                                        else False if votos[l] == 0 else None)
    return declarado, estavel


def main(argv) -> int:
    declarado, estavel = decisoes()
    ps = [w.name for w in projetos()]
    nest = len(ESTIMADORES)

    print(f"Unidade de decisão: estimador × projeto. {nest} estimadores "
          f"({', '.join(ESTIMADORES)}) × {len(ps)} projetos = {nest * len(ps)} por lente.")
    print("As 3 rodadas consolidam antes: 3/3 ativa, 0/3 inativa, o resto é oscilação e sai.\n")

    cab = (f"{'lente':<6}{'decl it1':>9}{'recus it1':>10} | {'a':>3}{'/den':>5}"
           f"{'  osc':>6} | {'b':>3}{'/den':>5}{'  osc':>6} | estrutural?")
    print(cab); print("-" * len(cab))

    fig = {SIGLA[l]: (e, d) for l, e, d in divergencias()}
    for l in NOMES:
        decl = [t for t in ps if declarado[(l, t)]]
        recu = [t for t in ps if not declarado[(l, t)]]
        a = sum(1 for t in decl for e in ESTIMADORES if estavel[(l, t, e)] is False)
        b = sum(1 for t in recu for e in ESTIMADORES if estavel[(l, t, e)] is True)
        den_a = sum(1 for t in decl for e in ESTIMADORES if estavel[(l, t, e)] is not None)
        den_b = sum(1 for t in recu for e in ESTIMADORES if estavel[(l, t, e)] is not None)
        osc_a = len(decl) * nest - den_a
        osc_b = len(recu) * nest - den_b

        # a figura é a fonte: se este relatório discordar dela, ele está errado
        esperado = fig.get(SIGLA[l], (0, 0))
        if (a, b) != esperado:
            raise SystemExit(f"ERRO: {SIGLA[l]} dá ({a},{b}) aqui e {esperado} na figura. "
                             f"Os dois deveriam contar a mesma coisa.")

        if not recu:
            nota = "SIM — declarada nos 12; b não tinha onde ocorrer"
        elif b == 0:
            nota = f"não — {den_b} decisões podiam divergir e nenhuma divergiu"
        else:
            nota = ""
        print(f"{SIGLA[l]:<6}{len(decl):>9}{len(recu):>10} | {a:>3}{'/' + str(den_a):>5}"
              f"{osc_a:>6} | {b:>3}{'/' + str(den_b):>5}{osc_b:>6} | {nota}")

    print("\n`den` é o denominador daquela direção: decisões estáveis nos projetos em que "
          "ela\npodia ocorrer. `osc` são as oscilações descartadas naquele subconjunto.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
