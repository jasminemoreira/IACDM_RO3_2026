"""Dados das figuras do paper — computados do corpus, nunca transcritos.

Uso:
    python3 figuras.py              # computa e escreve os CSV
    python3 figuras.py --conferir   # e confere contra o RESULTADO-RO3.md, falha alto

POR QUE EXISTE
--------------
As quatro figuras do paper traziam seus números como literais no `make_figures.R`,
transcritos à mão do `RESULTADO-RO3.md`. A tabela do §1.4 e o painel do §5.1, por sua
vez, foram computados fora do pipeline no fechamento do lote — não havia comando que
os produzisse. A cadeia de evidência terminava numa transcrição, duas vezes.

Este módulo recomputa os quatro conjuntos do corpus e escreve `saidas/figuras/*.csv`.
O `figuras/make_figures.R` lê esses CSV. Nenhum número da figura é digitado por ninguém.

O RATIO DO PAINEL (b) NÃO É CALCULADO AQUI, DE PROPÓSITO
--------------------------------------------------------
O CSV traz `observado` e `esperado`; o ratio é computado no script da figura, como
`observado / esperado`. Duas razões: é onde ele é usado, e o `esperado` sai daqui em
precisão plena — dividir pelos 0,21 / 0,47 / 0,12 arredondados da tabela publicada
introduz erro de até 0,5 no ratio, porque o denominador tem duas casas.

O `esperado` é ele próprio derivado: para dois avaliadores que marcaram nA e nB pares
num universo de n, o esperado ao acaso é `nA·nB/n`. Não é literal da tabela — é a
mesma quantidade que entra no Pe do κ, computada dos inteiros.

A DECISÃO QUE MUDA NÚMERO PUBLICADO: FECHO, NÃO ARESTA
-------------------------------------------------------
Para o κ, cada marcação vira o conjunto das decisões pareadas "estes dois são o mesmo
defeito?". Para um juiz cego, que entrega GRUPOS, isso é todo par dentro de um grupo.
Para o modelo gerador, que entrega ARESTAS (`duplica: <id>`), há duas leituras:

    arestas declaradas    71 pares    (um por marcador `duplica`)
    fecho transitivo      82 pares    (todo par dentro do cluster resultante)

A diferença são 11 pares, vindos dos 5 clusters de tamanho 3 e dos 2 de tamanho 4.

**Este módulo usa o fecho**, por três razões convergentes:

  1. é o que o `cegar_duplicatas.py comparar` — que está no pacote e é o instrumento
     declarado — sempre computou, via `_pares_positivos(clusters(proj))`;
  2. é o mesmo objeto dos dois lados. Comparar arestas do gerador contra grupos do
     juiz mede duas coisas diferentes e chama o resultado de concordância;
  3. a variável dependente do estudo já é definida sobre o fecho: os 1.029 clusters
     do §1.4 são o fecho transitivo dessas mesmas arestas. Usar aresta no κ e fecho
     na contribuição exclusiva seria usar duas definições de "mesmo defeito" no mesmo
     resultado.

O painel do §5.1 foi computado à mão no fechamento e usava **arestas** para o gerador e
**fecho** para os juízes. Isso mudava cinco células e as duas taxas de recuperação; a fonte
única já está corrigida, e `--conferir` existe para que a discrepância não possa voltar em
silêncio.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES                                    # noqa: E402
from ro3_analise import _UF, clusters                               # noqa: E402
from ro3_parser import CONDICIONAIS, SIGLA, UNIVERSAIS, carregar    # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CEGO = Path(__file__).resolve().parent / "cego"
SAIDA = Path(__file__).resolve().parent / "saidas" / "figuras"

# Padrão do arquivo de resposta de cada juiz cego. O gerador não tem arquivo: a
# marcação dele está nas próprias matrizes, como `duplica:`.
JUIZES = {"qwenQ4": "{t}-resposta.json",
          "qwenfull": "{t}-resposta-qwen3_6-27b.json",
          "gpt": "{t}-resposta-gpt-5_4-2026-03-05.json"}

# Rótulos de exibição. São etiquetas, não dados — mas ficam explícitos aqui em vez de
# digitados na figura, para que o eixo não possa discordar do que foi computado.
ROTULO_AVALIADOR = {"gerador": "Generator (Opus 5)", "qwenQ4": "Qwen Q4 (local)",
                    "qwenfull": "Qwen full", "gpt": "GPT-5.4"}

# Os três estimadores de ATIVAÇÃO que o §2.4 chama de "capazes" — o Q4 local fica de
# fora por ser o outlier do §5.2. Modelo -> infixo do arquivo de reestimativa.
ESTIMADORES = {"qwenfull": "qwen3.6-27b", "kimi": "kimicode", "gpt": "gpt-5.4-2026-03-05"}

DIR_ESQ = "Phase 2 activated; external reader declined"
DIR_DIR = "External reader activated; Phase 2 declined"


def rotulo_lente(nome: str) -> str:
    """Nome curto de eixo, DERIVADO do nome canônico — não uma tabela paralela.
    'Process / Workflow' -> 'Process'; 'Control Engineering' -> 'Control Eng.'"""
    return nome.split(" / ")[0].replace(" Engineering", " Eng.")


def projetos() -> list[Path]:
    ps = sorted(p for p in RAIZ.glob("T*-*") if (p / "specs").is_dir())
    if len(ps) != 12:
        raise SystemExit(f"ERRO: esperados 12 projetos, achados {len(ps)}. "
                         f"As figuras do paper são do lote de doze.")
    return ps


def _pares(grupos) -> set[frozenset]:
    return {frozenset(p) for g in grupos for p in combinations(sorted(set(g)), 2)}


# --------------------------------------------------------------- marcação de duplicatas

def marcacoes():
    """(pares marcados por avaliador, universo, clusters e exclusivas por esquema).

    Devolve tudo o que as figuras 1, 3a e 3b precisam, numa passada só pelo corpus.
    """
    marcados = {k: set() for k in ("gerador", *JUIZES)}
    universo = 0
    nclusters: Counter = Counter()
    exclusiva: dict[str, Counter] = defaultdict(Counter)

    for ws in projetos():
        t, proj = ws.name, carregar(ws)
        ids = sorted(a.id for a in proj.achados)
        lente = {a.id: a.lente for a in proj.achados}
        universo += len(ids) * (len(ids) - 1) // 2

        # gerador: FECHO transitivo das arestas `duplica` — ver docstring
        esquemas = {"gerador": [[a.id for a in g] for g in clusters(proj)]}

        mapa = json.loads((CEGO / f"{t}-mapa.json").read_text(encoding="utf-8"))
        mapa = mapa["cego_para_original"]
        for nome, padrao in JUIZES.items():
            arq = CEGO / padrao.format(t=t)
            if not arq.is_file():
                raise SystemExit(f"ERRO: falta {arq} — a remarcação cega está incompleta.")
            resposta = json.loads(arq.read_text(encoding="utf-8"))
            esquemas[nome] = [[mapa[c] for c in g] for g in resposta["grupos"]]

        for nome, grupos in esquemas.items():
            marcados[nome] |= {(t, p) for p in _pares(grupos)}

        # a união funde todo par que QUALQUER avaliador agrupou
        esquemas["uniao"] = [g for e in esquemas.values() for g in e]

        for nome, grupos in esquemas.items():
            uf = _UF()
            for i in ids:
                uf.find(i)
            for g in grupos:
                g = [x for x in g if x in lente]
                for a, b in zip(g, g[1:]):
                    uf.union(a, b)
            cl = defaultdict(set)
            for i in ids:
                cl[uf.find(i)].add(lente[i])
            nclusters[nome] += len(cl)
            for ls in cl.values():
                if len(ls) == 1:
                    exclusiva[nome][next(iter(ls))] += 1

    return marcados, universo, nclusters, exclusiva


def kappa(A: set, B: set, n: int) -> tuple[int, float, float]:
    """(co-marcações observadas, esperadas ao acaso, κ de Cohen) sobre n pares."""
    obs = len(A & B)
    pa, pb = len(A) / n, len(B) / n
    po = (n - len(A ^ B)) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return obs, len(A) * len(B) / n, (po - pe) / (1 - pe)


# ------------------------------------------------------------------ divergências (fig 2)

def divergencias() -> list[tuple[str, int, int]]:
    """(lente, Fase 2 ativou e o externo não, o externo ativou e a Fase 2 não).

    Decisão estável = as três rodadas concordam. Oscilações não entram, nos dois lados.
    A comparação é contra a declaração da ITERAÇÃO 1 — a que o declarante fez com a
    V(1) à vista, que é a arquitetura que o estimador cego recebeu. Contra a união das
    iterações seria comparar leituras de arquiteturas diferentes.
    """
    nomes = [n for n, _, _ in LENTES]
    esq: Counter = Counter()
    dire: Counter = Counter()

    for ws in projetos():
        t, proj = ws.name, carregar(ws)
        it1 = min(proj.condicionais_por_iteracao)
        declarado = set(proj.condicionais_por_iteracao[it1])

        for infixo in ESTIMADORES.values():
            votos: Counter = Counter()
            for r in (1, 2, 3):
                arq = CEGO / f"{t}-reestimativa-V1-{infixo}-r{r}.json"
                if not arq.is_file():
                    raise SystemExit(f"ERRO: falta {arq} — a reestimativa está incompleta.")
                for e in json.loads(arq.read_text(encoding="utf-8"))["lentes"]:
                    if e["ativa"]:
                        votos[e["lente"]] += 1
            for l in nomes:
                if votos[l] == 3 and l not in declarado:
                    dire[l] += 1
                elif votos[l] == 0 and l in declarado:
                    esq[l] += 1

    linhas = [(l, esq[l], dire[l]) for l in nomes if esq[l] or dire[l]]
    return sorted(linhas, key=lambda x: -(x[1] + x[2]))


# ------------------------------------------------------------------------------ escrita

def _escrever(nome: str, cabecalho: list[str], linhas) -> Path:
    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = SAIDA / nome
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)
    return caminho


ORDEM_PARES = [("qwenfull", "gpt"), ("gerador", "qwenfull"), ("gerador", "gpt"),
               ("gerador", "qwenQ4"), ("qwenQ4", "qwenfull"), ("qwenQ4", "gpt")]


def computar():
    """Tudo em formato longo, com os rótulos já montados.

    O R que consome isto não decide nada: não ordena, não rotula, não deriva. Se uma
    legenda diz '(668)', o 668 foi contado aqui. A ordem das linhas do CSV é a ordem
    do eixo. A única aritmética que sobra lá é o ratio, e é deliberada.
    """
    marcados, n, nclusters, exclusiva = marcacoes()
    ativou: Counter = Counter()
    for ws in projetos():
        for l in carregar(ws).lentes_ativas:
            ativou[l] += 1

    todas = list(UNIVERSAIS) + list(CONDICIONAIS)
    ordem = sorted(todas, key=lambda l: (-exclusiva["uniao"][l], -exclusiva["gerador"][l]))
    esquemas = [("gerador", "Generator, Opus 5"), ("qwenfull", "Qwen full"),
                ("gpt", "GPT-5.4"), ("uniao", "Union of 4")]

    fig1 = [(rotulo_lente(l), SIGLA[l],
             f"{rot} ({nclusters[k]:,}{' clusters' if k == 'gerador' else ''})",
             exclusiva[k][l])
            for k, rot in esquemas for l in ordem]

    menor = ordem[-1]
    nota = (f"minimum: {rotulo_lente(menor)}, {exclusiva['uniao'][menor]} exclusive defects "
            f"(lens active in {ativou[menor]} of {len(projetos())} projects)")

    fig2 = [(rotulo_lente(l), SIGLA[l], d, v)
            for l, esq, dire in divergencias()
            for d, v in ((DIR_ESQ, -esq), (DIR_DIR, dire)) if v]

    fig3a = [(ROTULO_AVALIADOR[k], len(marcados[k]))
             for k in ("gerador", "qwenQ4", "qwenfull", "gpt")]

    fig3b = []
    for a, b in ORDEM_PARES:
        obs, esp, k = kappa(marcados[a], marcados[b], n)
        fig3b.append((f"{ROTULO_AVALIADOR[a]} × {ROTULO_AVALIADOR[b]}", obs, esp, k))

    return {"n": n, "clusters": dict(nclusters), "nota": nota,
            "fig1": fig1, "fig2": fig2, "fig3a": fig3a, "fig3b": fig3b}


def escrever(d) -> list[Path]:
    return [
        _escrever("fig-robustness.csv", ["lens", "code", "clustering", "value"], d["fig1"]),
        _escrever("fig-divergences.csv", ["lens", "code", "direction", "value"], d["fig2"]),
        _escrever("fig-kappa-rates.csv", ["evaluator", "marked_pairs"], d["fig3a"]),
        # `esperado` em precisão plena, e SEM a coluna ratio: o ratio é computado na
        # figura. Arredondar aqui reintroduziria o erro que motivou este módulo.
        _escrever("fig-kappa-chance.csv", ["pair", "observed", "expected", "kappa"],
                  [(p, o, f"{e:.10f}", f"{k:.6f}") for p, o, e, k in d["fig3b"]]),
        _escrever("fig-annotations.csv", ["key", "text"], [("robustness_minimum", d["nota"])]),
    ]


# ---------------------------------------------------------------------------- conferência

def _tabela(texto: str, cabecalho: str) -> list[list[str]]:
    """Linhas da primeira tabela markdown cujo cabeçalho casa. Falha alto se sumir."""
    linhas = texto.split("\n")
    for i, l in enumerate(linhas):
        if cabecalho in l and l.lstrip().startswith("|"):
            corpo = []
            for j in range(i + 2, len(linhas)):
                if not linhas[j].lstrip().startswith("|"):
                    break
                corpo.append([c.strip().strip("*") for c in linhas[j].strip("|").split("|")])
            return corpo
    raise SystemExit(f"ERRO: tabela com cabeçalho {cabecalho!r} não encontrada no "
                     f"RESULTADO-RO3.md. O formato mudou — conferência impossível.")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def conferir(d) -> int:
    fonte = (RAIZ / "RESULTADO-RO3.md").read_text(encoding="utf-8")
    falhas = []

    pub = {r[0]: [_num(x) for x in r[1:5]] for r in _tabela(fonte, "| lente | gerador |")}
    calc: dict[str, list[float]] = defaultdict(list)
    for _, sig, _, valor in d["fig1"]:
        calc[sig].append(valor)
    calc["clusters"] = [d["clusters"][k] for k in ("gerador", "qwenfull", "gpt", "uniao")]
    for sig, valores in calc.items():
        if sig not in pub:
            falhas.append(f"§1.4 não traz a linha {sig}")
        elif pub[sig] != valores:
            falhas.append(f"§1.4 {sig}: fonte {pub[sig]} · computado {valores}")

    kpub = _tabela(fonte, "| par de avaliadores |")
    if len(kpub) != len(d["fig3b"]):
        falhas.append(f"§5.1 tem {len(kpub)} pares, computados {len(d['fig3b'])}")
    else:
        for (_, obs, esp, k), linha in zip(d["fig3b"], kpub):
            o, e, kk = _num(linha[1]), _num(linha[2]), _num(linha[3])
            if o != obs:
                falhas.append(f"§5.1 {linha[0]}: observado fonte {o:.0f} · computado {obs}")
            if abs(e - esp) > 0.005:
                falhas.append(f"§5.1 {linha[0]}: esperado fonte {e} · computado {esp:.4f}")
            if abs(kk - k) > 0.0005:
                falhas.append(f"§5.1 {linha[0]}: κ fonte {kk} · computado {k:.3f}")

    if not falhas:
        print("\nconferência: fonte única e corpus concordam em todas as células.")
        return 0
    print(f"\nDIVERGE DA FONTE ÚNICA em {len(falhas)} célula(s):", file=sys.stderr)
    for f in falhas:
        print(f"  {f}", file=sys.stderr)
    print("\nIsto não é falha do script: é o RESULTADO-RO3.md e o corpus discordando, e\n"
          "um dos dois está errado. Não edite a fonte para calar a conferência sem antes\n"
          "saber qual — foi assim que o painel §5.1 passou meses com cinco células erradas.",
          file=sys.stderr)
    return 1


def main(argv) -> int:
    d = computar()
    print(f"corpus: 12 projetos · {d['n']} pares avaliáveis · "
          f"clusters {d['clusters']['gerador']}/{d['clusters']['qwenfull']}/"
          f"{d['clusters']['gpt']}/{d['clusters']['uniao']} (ger/full/gpt/união)\n")

    print("pares marcados: " + " · ".join(f"{r} {n}" for r, n in d["fig3a"]))
    print("\npar de avaliadores                    obs   esperado    ratio       κ")
    for par, obs, esp, k in d["fig3b"]:
        print(f"  {par:<34s} {obs:>4d} {esp:>10.4f} {obs / esp:>8.2f}  {k:>6.3f}")

    for p in escrever(d):
        print(f"\nescrito  {p.relative_to(RAIZ)}", end="")
    print(f"\n\nPara renderizar:  Rscript --vanilla {SAIDA.parent.parent.name}/"
          f"figuras/make_figures.R")

    return conferir(d) if "--conferir" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
