"""Tabela número→comando: cada valor do paper e o comando que o reproduz.

Uso:
    python3 tools/tabela_numeros.py                    # escreve TABELA-NUMEROS.md
    python3 tools/tabela_numeros.py --auditar <tex>    # e audita a cobertura contra o .tex

POR QUE EXISTE
--------------
Pedido do revisor de artefato, e a única forma honesta de responder "de onde saiu este
número?" para as 32 páginas. A tabela é GERADA: cada valor abaixo é recomputado do corpus
nesta execução, não transcrito do manuscrito. Se um valor aqui divergir do paper, um dos
dois está errado — e a auditoria diz qual linha olhar.

TRÊS CATEGORIAS, E A DISTINÇÃO IMPORTA
--------------------------------------
  medido      recomputável do corpus por um comando. É a maioria, e é o que a tabela mapeia.
  registrado  fato operacional que não está no corpus — quantos projetos foram descartados,
              qual modelo gerou. Vive no LOG-OPERACAO.md e é verificável por leitura, não
              por execução.
  citado      número de trabalho de terceiros. Não é medida nossa e não tem comando; marcar
              como se tivesse seria a pior linha da tabela.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from math import comb
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analise"))

from divergencias import decisoes                                   # noqa: E402
from figuras import CEGO, ESTIMADORES, computar as fig_computar     # noqa: E402
from predicao_cega import LENTES                                    # noqa: E402
from redeclaracao import jaccard, pares as pares_redecl             # noqa: E402
from ro3_analise import clusters                                    # noqa: E402
from ro3_parser import SIGLA, carregar                              # noqa: E402

NOMES = [n for n, _, _ in LENTES]
MODELOS = {"Qwen Q4 (local)": "qwen3.6_27b", "Qwen full": "qwen3.6-27b",
           "Kimi K2": "kimicode", "GPT-5.4": "gpt-5.4-2026-03-05"}


def projetos():
    return sorted(p for p in RAIZ.glob("T*-*") if (p / "specs").is_dir())


def pc(x: float) -> str:
    return f"{round(x * 100)}%"


def bloco_corpus():
    ps = projetos()
    sev = Counter(); achados = modulos = 0
    horas, iters = [], Counter()
    for ws in ps:
        proj = carregar(ws)
        achados += len(proj.achados)
        for a in proj.achados:
            sev[a.severidade] += 1
        modulos += len(proj.modulos)
        e = json.loads((ws / ".versus" / "state.json").read_text(encoding="utf-8"))
        t0, t1 = e.get("createdAt"), e.get("updatedAt")
        if t0 and t1:
            f = "%Y-%m-%dT%H:%M:%S.%fZ"
            horas.append((datetime.strptime(t1, f) - datetime.strptime(t0, f)).total_seconds() / 3600)
        iters[len(e["activatedLenses"])] += 1
    defeitos = sum(len(clusters(carregar(w))) for w in ps)
    horas.sort()
    n = len(horas)
    # 12 projetos: mediana é a média do 6º e do 7º. O manuscrito trazia 3,3 h, que é o
    # 7º valor sozinho (3,32) — mediana superior, convenção não declarada. O par central
    # é 2,99 e 3,32, cuja média é 3,15, e arredonda para 3,2.
    med = horas[n // 2] if n % 2 else (horas[n // 2 - 1] + horas[n // 2]) / 2
    perfil = ", ".join(f"{q}×{k}" for k, q in sorted(iters.items()))
    return [(str(len(ps)), "projetos válidos"),
            (str(achados), "achados"),
            (str(sev["critico"]), "críticos"),
            (str(sev["importante"]), "importantes"),
            (str(sev["sugestao"]), "sugestões"),
            (str(defeitos), "defeitos distintos, clusterização do gerador"),
            (str(modulos), "módulos"),
            (f"{sum(horas):.1f}", "horas decorridas, pausas incluídas"),
            (f"{med:.1f}", "mediana de horas por projeto"),
            (str(sum(k * q for k, q in iters.items())), f"iterações do laço 2↔3 ({perfil})")]


def bloco_cobertura():
    c = Counter()
    for ws in projetos():
        for l in carregar(ws).lentes_ativas:
            c[l] += 1
    return [(str(c[l]), f"{SIGLA[l]} ativou em N de 12 projetos")
            for l in sorted(NOMES, key=lambda x: -c[x])]


def bloco_sobreposicao():
    part, soz = Counter(), Counter()
    comum = defaultdict(int)
    for ws in projetos():
        for g in clusters(carregar(ws)):
            ls = sorted({a.lente for a in g})
            for l in ls:
                part[l] += 1
                if len(ls) == 1:
                    soz[l] += 1
            for i, a in enumerate(ls):
                for b in ls[i+1:]:
                    comum[(a, b)] += 1
    # (part-soz)/part, NÃO 1-soz/part: REG dá exatamente 6/40 = 15,0% e fica na fronteira
    # do critério "acima de 15%". A segunda forma devolve 0,15000000000000002 e conta REG
    # como quinta lente. Uma casa binária decide um número do paper.
    ov = {l: (part[l] - soz[l]) / part[l] for l in part}
    acima = [l for l in sorted(ov, key=ov.get, reverse=True) if ov[l] > 0.15]
    jacs = {k: v / (part[k[0]] + part[k[1]] - v) for k, v in comum.items()}
    maior = max(jacs, key=jacs.get)
    tot = 19; pares = tot * (tot - 1) // 2
    return [(pc(sum(ov.values()) / len(ov)), "sobreposição média das 19 lentes"),
            (pc(min(ov.values())), f"menor — {SIGLA[min(ov, key=ov.get)]}"),
            (pc(max(ov.values())), f"maior — {SIGLA[max(ov, key=ov.get)]}"),
            (str(len(acima)), "lentes acima de 15% — " + ", ".join(f"{SIGLA[l]} {pc(ov[l])}" for l in acima)),
            (str(len(comum)), f"pares que compartilham ao menos um defeito, de {pares}"),
            (str(pares), "pares possíveis de lentes"),
            (pc(len(comum) / pares), "idem, proporção"),
            (f"{jacs[maior]:.2f}", f"maior Jaccard par a par — {SIGLA[maior[0]]} × {SIGLA[maior[1]]}"),
            (str(comum[maior]), "defeitos em comum nesse par"),
            (f"{jacs.get((('Architectural'), ('Assumptions')), 0.0):.2f}",
             "ARQ × PRE — o par que o §4 do protocolo suspeitava a priori")]


def bloco_estimadores():
    linhas = []
    for rot, inf in MODELOS.items():
        tot = osc = ok = est = rod = 0
        for ws in projetos():
            proj = carregar(ws)
            it1 = set(proj.condicionais_por_iteracao[min(proj.condicionais_por_iteracao)])
            v: Counter = Counter()
            for r in (1, 2, 3):
                d = json.loads((CEGO / f"{ws.name}-reestimativa-V1-{inf}-r{r}.json")
                               .read_text(encoding="utf-8"))
                ativas = [e["lente"] for e in d["lentes"] if e["ativa"]]
                tot += len(ativas); rod += 1
                for l in ativas:
                    v[l] += 1
            for l in NOMES:
                if v[l] in (0, 3):
                    est += 1
                    ok += (v[l] == 3) == (l in it1)
                else:
                    osc += 1
        linhas += [(f"{tot/rod:.1f}", f"{rot} — lentes ativas por rodada"),
                   (str(osc), f"{rot} — oscilações"),
                   (pc(ok / est), f"{rot} — concordância com a Fase 2")]
    # concordância ENTRE estimadores, sobre as decisões estáveis em ambos
    est_dec = {}
    for rot, inf in MODELOS.items():
        for ws in projetos():
            v: Counter = Counter()
            for r in (1, 2, 3):
                d = json.loads((CEGO / f"{ws.name}-reestimativa-V1-{inf}-r{r}.json")
                               .read_text(encoding="utf-8"))
                for e in d["lentes"]:
                    if e["ativa"]:
                        v[e["lente"]] += 1
            for l in NOMES:
                est_dec[(rot, ws.name, l)] = True if v[l] == 3 else False if v[l] == 0 else None
    rots = list(MODELOS)
    pares = []
    for i, a in enumerate(rots):
        for b in rots[i + 1:]:
            ch = [(est_dec[(a, w.name, l)], est_dec[(b, w.name, l)])
                  for w in projetos() for l in NOMES]
            ch = [(x, y) for x, y in ch if x is not None and y is not None]
            pares.append((sum(x == y for x, y in ch) / len(ch), f"{a} × {b}"))
    pares.sort()
    linhas += [(pc(v), f"concordância entre estimadores — {r}") for v, r in pares]
    return linhas


def _fisher(a, b, c, d):
    """Exato de Fisher bicaudal: soma as tabelas com probabilidade <= a observada.
    É o teste apropriado nestas contagens — qui-quadrado não vale com célula zero."""
    n = a + b + c + d
    obs = comb(a + b, a) * comb(c + d, c)
    return sum(comb(a + b, i) * comb(c + d, a + c - i)
               for i in range(max(0, a + c - (c + d)), min(a + b, a + c) + 1)
               if comb(a + b, i) * comb(c + d, a + c - i) <= obs) / comb(n, a + c)


def bloco_adjudicacao():
    mapa = json.loads((CEGO / "ETI-adjudicacao-mapa.json").read_text(encoding="utf-8"))
    vs = {j: {x["id"]: x["v"] for x in json.loads(
              (CEGO / f"ETI-adjudicacao-{j}.json").read_text(encoding="utf-8"))["vereditos"]}
          for j in ("claude", "gpt")}
    D = [i for i, m in mapa.items() if m["grupo"] == "D"]
    C = [i for i, m in mapa.items() if m["grupo"] == "C"]
    linhas = [(str(len(mapa)), "achados cegados julgados"),
              (str(len(D)), "do grupo disputado"), (str(len(C)), "do grupo de controle")]
    for rot, f in (("Claude", lambda i: vs["claude"][i] == "SIM"),
                   ("gpt-5.4", lambda i: vs["gpt"][i] == "SIM"),
                   ("consenso", lambda i: vs["claude"][i] == vs["gpt"][i] == "SIM")):
        sd, sc = sum(map(f, D)), sum(map(f, C))
        linhas += [(f"{sd}", f"{rot} — SIM entre os {len(D)} disputados ({pc(sd/len(D))})"),
                   (f"{sc}", f"{rot} — SIM entre os {len(C)} de controle ({pc(sc/len(C))})"),
                   (f"{_fisher(sd, len(D)-sd, sc, len(C)-sc):.3f}", f"{rot} — Fisher bicaudal p")]
    po = sum(1 for i in mapa if vs["claude"][i] == vs["gpt"][i]) / len(mapa)
    cats = {v for d in vs.values() for v in d.values()}
    pe = sum((sum(1 for i in mapa if vs["claude"][i] == k) / len(mapa)) *
             (sum(1 for i in mapa if vs["gpt"][i] == k) / len(mapa)) for k in cats)
    linhas += [(pc(po), "concordância bruta entre juízes"),
               (f"{(po-pe)/(1-pe):.3f}", "κ de Cohen entre juízes")]
    return linhas


def bloco_criterios_saida():
    n = chars = vazios = 0
    for ws in projetos():
        e = json.loads((ws / ".versus" / "state.json").read_text(encoding="utf-8"))
        for c in e.get("exitCriteria", []):
            n += 1
            d = c.get("details") or ""
            chars += len(d)
            vazios += not d.strip()
    return [(str(n), "registros de critério de saída"),
            (str(round(chars / n)), "caracteres em média por registro"),
            (str(vazios), "registros vazios")]


def bloco_redeclaracao():
    ps = list(projetos())
    todos = [(a, b) for ws in ps for _, _, a, b in pares_redecl(ws)]
    med = []
    for ws in ps:
        p = list(pares_redecl(ws))
        if p:
            med.append(sum(jaccard(a, b) for _, _, a, b in p) / len(p))
    return [(str(len(todos)), "comparações lente a lente entre iterações consecutivas"),
            (str(sum(1 for a, b in todos if a.strip() == b.strip())), "justificativas idênticas"),
            (f"{sum(jaccard(a, b) for a, b in todos)/len(todos):.2f}", "Jaccard no conjunto"),
            (f"{min(med):.2f}", "menor Jaccard médio por projeto"),
            (f"{max(med):.2f}", "maior Jaccard médio por projeto")]


def bloco_figuras():
    d = fig_computar()
    L = [(str(d["n"]), "pares avaliáveis, soma intra-projeto")]
    for k, rot in (("gerador", "gerador"), ("qwenfull", "qwen full"),
                   ("gpt", "gpt-5.4"), ("uniao", "união das quatro")):
        L.append((str(d["clusters"][k]), f"clusters sob a marcação — {rot}"))
    for rot, n in d["fig3a"]:
        L.append((str(n), f"pares marcados — {rot}"))
    for par, obs, esp, k in d["fig3b"]:
        L += [(str(obs), f"co-marcações observadas — {par}"),
              (f"{esp:.2f}", f"esperado ao acaso — {par}"),
              (f"{k:.3f}", f"κ de Cohen — {par}")]
    red = (d["clusters"]["gerador"] - d["clusters"]["uniao"]) / d["clusters"]["gerador"]
    L.append((pc(red), "redução de clusters da marcação do gerador para a união"))
    marc = dict(d["fig3a"])
    ger = marc["Generator (Opus 5)"]
    for par, obs, _, _ in d["fig3b"]:
        if par.startswith("Generator"):
            L.append((pc(obs / ger), f"recuperação das marcações do gerador — {par.split(' × ')[1]}"))
    for _, sig, clus, v in d["fig1"]:
        L.append((str(v), f"contribuição exclusiva — {sig} sob {clus.split(' (')[0]}"))
    return L


def bloco_divergencias():
    declarado, estavel = decisoes()
    ps = [w.name for w in projetos()]
    L = []
    for l in NOMES:
        decl = [t for t in ps if declarado[(l, t)]]
        recu = [t for t in ps if not declarado[(l, t)]]
        a = sum(1 for t in decl for e in ESTIMADORES if estavel[(l, t, e)] is False)
        b = sum(1 for t in recu for e in ESTIMADORES if estavel[(l, t, e)] is True)
        da = sum(1 for t in decl for e in ESTIMADORES if estavel[(l, t, e)] is not None)
        db = sum(1 for t in recu for e in ESTIMADORES if estavel[(l, t, e)] is not None)
        if da:
            L.append((f"{a}/{da} ({pc(a/da)})", f"{SIGLA[l]} — Fase 2 ativou, estimador recusou"))
        if db:
            L.append((f"{b}/{db}", f"{SIGLA[l]} — Fase 2 recusou, estimador ativou"))
    return L


BLOCOS = [
    ("Corpus", "tab:corpus", "python3 analise/ro3_analise.py T*-*  ·  python3 tools/tabela_numeros.py", bloco_corpus),
    ("Cobertura de ativação", "tab:activation", "python3 tools/tabela_numeros.py", bloco_cobertura),
    ("Distribuição de sobreposição", "tab:overlap", "python3 analise/ro3_analise.py T*-*  (Passos 3 e 4)  ·  python3 tools/tabela_numeros.py", bloco_sobreposicao),
    ("Contribuição exclusiva e concordância de marcação", "tab:robustness · tab:kappa", "python3 analise/figuras.py --conferir", bloco_figuras),
    ("Estimadores cegos de ativação", "tab:estimators", "python3 tools/tabela_numeros.py", bloco_estimadores),
    ("Divergências por lente, com denominador", "tab:divergences", "python3 analise/divergencias.py", bloco_divergencias),
    ("Redeclaração entre iterações", "§5.3", "python3 analise/redeclaracao.py", bloco_redeclaracao),
    ("Adjudicação da lente Ética", "§5.5", "python3 tools/tabela_numeros.py", bloco_adjudicacao),
    ("Critérios de saída", "§5.4", "python3 tools/tabela_numeros.py", bloco_criterios_saida),
]

REGISTRADOS = [
    ("7", "projetos descartados, cada um com motivo", "`LOG-OPERACAO.md`"),
    ("claude-opus-5", "agente gerador nos doze", "`LOG-OPERACAO.md` — verificado em 5.328 mensagens"),
    ("0.14.2", "instrumento, única versão instalada", "`instrumento/server.js`, md5 `9dfee8beb881…`"),
    ("-0.001", "κ que motivou a regra de rotulagem em esparsidade", "§ desvios — medida "
     "**eliminada**; valor histórico, não resultado"),
]

# Números de trabalhos citados. NÃO são medida nossa e não têm comando — a entrada existe
# para que a auditoria não os marque como lacuna, e para que ninguém os atribua ao corpus.
CITADOS = {"90.3", "95", "1{,}900", "921", "5{,}800", "63", "330"}


def gerar() -> str:
    L = ["# Tabela número→comando", "",
         "**Gerada, não transcrita.** Cada valor foi recomputado do corpus na execução que",
         "produziu este arquivo:", "", "```bash", "python3 tools/tabela_numeros.py", "```", "",
         "Se um valor aqui divergir do manuscrito, um dos dois está errado.", "", "---", ""]
    for titulo, onde, cmd, fn in BLOCOS:
        L += [f"## {titulo}", "", f"*{onde}*", "", "```", cmd, "```", "",
              "| valor | o que é |", "|---|---|"]
        L += [f"| `{v}` | {d} |" for v, d in fn()]
        L.append("")
    L += ["---", "", "## Registrados, não computados", "",
          "Fatos operacionais que não vivem no corpus — verificáveis por leitura, não por execução.",
          "", "| valor | o que é | onde |", "|---|---|---|"]
    L += [f"| `{v}` | {d} | {o} |" for v, d, o in REGISTRADOS]
    L += ["", "## Citados de terceiros", "",
          "**Não são medida deste experimento e não têm comando.** `90,3%` e `1.900` são de",
          "Hao et al. (2026); `921`, `5.800` e `63%` de De Santana et al. (2026). Atribuí-los",
          "ao corpus seria o pior erro que esta tabela poderia cometer.", ""]
    return "\n".join(L)


def auditar(tex: Path, texto: str) -> int:
    linhas = tex.read_text(encoding="utf-8").split("\n")
    NUM = re.compile(r"(?<![\\A-Za-z0-9.])(\d+(?:\{,\}\d{3})*(?:\.\d+)?)(?![0-9}A-Za-z]|\.\d)")
    IGN = re.compile(r"ref\{|cite|label\{|includegraphics|zenodo|width=|^%|textwidth")
    cobertos = set(re.findall(r"\d+(?:\.\d+)?", texto)) | {c.replace("{,}", "") for c in CITADOS}
    faltam: dict[str, list[int]] = {}
    for i, l in enumerate(linhas[501:1692], start=502):
        if IGN.search(l):
            continue
        for m in NUM.finditer(l):
            if m.group(1).replace("{,}", "") not in cobertos:
                faltam.setdefault(m.group(1), []).append(i)
    if not faltam:
        print("auditoria: todo valor numérico do .tex aparece na tabela.")
        return 0
    print(f"\nauditoria — {len(faltam)} valor(es) do .tex fora da tabela:", file=sys.stderr)
    for v, lns in sorted(faltam.items(), key=lambda kv: -len(kv[1])):
        print(f"  {v:<10} linhas {lns[:8]}", file=sys.stderr)
    print("\nCada um é uma de três coisas: medida que falta computar, número de trabalho\n"
          "citado que falta declarar em CITADOS, ou ordinal/contagem de prosa.", file=sys.stderr)
    return 1


def main(argv) -> int:
    texto = gerar()
    (RAIZ / "TABELA-NUMEROS.md").write_text(texto, encoding="utf-8")
    print(f"escrito TABELA-NUMEROS.md · "
          f"{sum(len(fn()) for _, _, _, fn in BLOCOS)} valores em {len(BLOCOS)} blocos")
    if "--auditar" in argv:
        return auditar(Path(argv[argv.index("--auditar") + 1]), texto)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
