"""Plano de análise da RO3 — Passos 1 a 5 do BATCH-PROTOCOL §4.

Uso:
    python3 ro3_analise.py <workspace> [<workspace> ...]
    python3 ro3_analise.py --json <workspace> ...

DECISÃO DE ANÁLISE, FIXADA ANTES DA COLETA
------------------------------------------
"Contribuição exclusiva" é operacionalizada por CLUSTER DE DEFEITO, não por
célula módulo×lente.

Um cluster é o fecho transitivo das marcações `duplica:` — o conjunto de achados
que apontam o mesmo defeito. Uma lente L tem contribuição exclusiva num cluster
quando L é a única lente presente nele.

Por que assim, e não "achados de L num módulo onde nenhuma outra lente achou
nada": o critério do paper é *uma lente é legítima apenas se removê-la expõe uma
CLASSE DE FALHA que nenhuma outra detecta* — a unidade é o defeito, não o módulo.
Num módulo denso, quase nada seria exclusivo pelo critério de módulo, e a medida
diria mais sobre o tamanho do módulo que sobre a lente. O §3 já fixou `duplica`
como o discriminante de "mesmo defeito"; este passo apenas o usa.

Consequência assumida: a medida herda o viés de quem marca `duplica`.

DIREÇÃO DO VIÉS — e a palavra "conservador" não é usada aqui, de propósito.
A regra do §3 ("na dúvida, não marque duplicata") produz MENOS fusões, logo MAIS
clusters, logo é mais provável que uma lente seja a única ocupante de um cluster.
Isso INFLA a contribuição exclusiva, que é a variável dependente. Ou seja: a regra
enviesa a favor da hipótese de ortogonalidade.

A regra é prudente quanto ao ATO DE MARCAR — asseverar que dois achados são o mesmo
defeito é uma afirmação positiva, e abster-se é o default defensável. Mas é o oposto
de prudente QUANTO À HIPÓTESE. Chamar isso de "viés conservador" sem dizer conservador
em relação a quê conflaciona as duas coisas; o §3 e o §7 do protocolo o fazem, e a
`ERRATA-CRITERIO-DUPLICA.md` na raiz do pacote registra a leitura correta.

O CORRETIVO está no desenho, não na regra: a remarcação cega, e em particular a
UNIÃO das clusterizações — que funde todo par que qualquer avaliador agrupou, e é
portanto a leitura mais hostil à hipótese. Diferença medida: 1.029 clusters sob a
marcação do gerador contra 668 sob a união, 35% a menos. Nenhuma lente chega a zero
sob nenhuma das quatro.

Por isso o Passo 2 nunca deve ser reportado só sob a marcação do gerador.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from ro3_parser import CONDICIONAIS, SEM_LENTE, SIGLA, UNIVERSAIS, ErroDeFormato, Projeto, carregar


# ------------------------------------------------------------------- clusters

class _UF:
    def __init__(self): self.pai = {}

    def find(self, x):
        self.pai.setdefault(x, x)
        while self.pai[x] != x:
            self.pai[x] = self.pai[self.pai[x]]
            x = self.pai[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.pai[rb] = ra


def clusters(proj: Projeto) -> list[list]:
    """Achados agrupados por defeito, via fecho transitivo de `duplica`."""
    uf = _UF()
    for a in proj.achados:
        uf.find(a.id)
        if a.duplica:
            uf.union(a.id, a.duplica)
    grupos = defaultdict(list)
    for a in proj.achados:
        grupos[uf.find(a.id)].append(a)
    return list(grupos.values())


# ---------------------------------------------------------------------- passos

def passo1(projetos):
    """Matriz de incidência agregada: (projeto, módulo, lente) -> ids."""
    inc = defaultdict(list)
    for p in projetos:
        for a in p.achados:
            inc[(p.task_id, a.modulo, a.lente)].append(a.id)
    return inc


def passo2(projetos):
    """Contribuição exclusiva por lente, por cluster de defeito."""
    total = defaultdict(int)       # achados produzidos pela lente
    exclusiva = defaultdict(int)   # clusters em que a lente é a única
    projetos_com_exclusiva = defaultdict(set)
    ativou_em = defaultdict(set)

    for p in projetos:
        for l in p.lentes_ativas:
            ativou_em[l].add(p.task_id)
        for a in p.achados:
            total[a.lente] += 1
        for grupo in clusters(p):
            lentes = {a.lente for a in grupo}
            if len(lentes) == 1:
                (l,) = lentes
                exclusiva[l] += 1
                projetos_com_exclusiva[l].add(p.task_id)
    return total, exclusiva, projetos_com_exclusiva, ativou_em


def passo3(projetos):
    """Simulação de remoção: o que se perde ao remover a lente, e o que ninguém recupera."""
    n_achados = sum(len(p.achados) for p in projetos)
    todos = [g for p in projetos for g in clusters(p)]
    n_clusters = len(todos)
    fora = {}
    for l in UNIVERSAIS + CONDICIONAIS:
        perdidos = sum(1 for p in projetos for a in p.achados if a.lente == l)
        orfaos = sum(1 for g in todos if {a.lente for a in g} == {l})
        fora[l] = {
            "achados_perdidos": perdidos,
            "frac_achados_perdidos": perdidos / n_achados if n_achados else 0.0,
            "defeitos_nao_recuperados": orfaos,
            "frac_defeitos_nao_recuperados": orfaos / n_clusters if n_clusters else 0.0,
        }
    return fora, n_achados, n_clusters


def passo4(projetos):
    """Sobreposição par a par: co-ocorrência em módulos e em defeitos."""
    mods = defaultdict(set)       # lente -> {(projeto, módulo)}
    for p in projetos:
        for a in p.achados:
            mods[a.lente].add((p.task_id, a.modulo))

    lentes_por_cluster = [{a.lente for a in g} for p in projetos for g in clusters(p)]
    ativas = sorted({a.lente for p in projetos for a in p.achados} - {SEM_LENTE})

    pares = []
    for x, y in combinations(ativas, 2):
        amb = sum(1 for ls in lentes_por_cluster if {x, y} <= ls)
        qual = sum(1 for ls in lentes_por_cluster if {x, y} & ls)
        jac_mod = (len(mods[x] & mods[y]) / len(mods[x] | mods[y])) if (mods[x] | mods[y]) else 0.0
        pares.append({
            "lente_a": x, "lente_b": y,
            "jaccard_modulos": jac_mod,
            "defeitos_em_comum": amb,
            "jaccard_defeitos": amb / qual if qual else 0.0,
            "a_priori": {x, y} == {"Assumptions", "Architectural"},
        })
    pares.sort(key=lambda d: -d["jaccard_defeitos"])
    return pares


def passo5(projetos, total, ativou_em):
    """Cobertura: achados sem lente, lentes ativas sem achado, lentes sub-exercitadas."""
    sem_lente = [(p.task_id, a.id, a.descricao) for p in projetos for a in p.achados
                 if a.lente == SEM_LENTE]
    ativas_sem_achado = []
    for p in projetos:
        produziu = {a.lente for a in p.achados}
        for l in p.lentes_ativas:
            if l not in produziu:
                ativas_sem_achado.append((p.task_id, l))
    subcobertas = [(l, len(ativou_em[l])) for l in CONDICIONAIS if len(ativou_em[l]) < 3]
    return sem_lente, ativas_sem_achado, subcobertas


# ------------------------------------------------------------------- relatório

def _pct(x): return f"{100 * x:.0f}%"


def relatorio(projetos) -> str:
    total, exclusiva, proj_excl, ativou_em = passo2(projetos)
    total_def, compart = Counter(), Counter()
    for p in projetos:
        for g in clusters(p):
            ls = {a.lente for a in g}
            for l in ls:
                total_def[l] += 1
                if len(ls) > 1:
                    compart[l] += 1
    fora, n_achados, n_clusters = passo3(projetos)
    pares = passo4(projetos)
    sem_lente, ativas_sem_achado, subcobertas = passo5(projetos, total, ativou_em)
    inc = passo1(projetos)

    L = []
    L.append("# RO3 — análise de ortogonalidade das lentes\n")
    L.append(f"Projetos: {len(projetos)} ({', '.join(p.task_id for p in projetos)})  ")
    L.append(f"Achados: {n_achados}  ·  Defeitos distintos (clusters): {n_clusters}  ·  "
             f"Módulos: {sum(len(p.modulos) for p in projetos)}\n")

    # Uma versão da arquitetura pode ser DELTA (só o que mudou) em vez de retrato
    # completo — o T23-canario escreveu 12, 12 e 4. Delta e remoção são indistinguíveis
    # pelo texto, então o relatório mostra o perfil em vez de escolher em silêncio.
    for p in projetos:
        perfil = p.modulos_por_versao
        if len(perfil) > 1 and len(p.modulos) < max(perfil.values()):
            L.append(f"\n> ⚠ **{p.task_id}: a última versão da arquitetura tem menos módulos que "
                     f"uma anterior** — V" + " · V".join(f"({v}) {n}" for v, n in perfil.items()) +
                     f". Ou a Fase 3 removeu módulos, ou escreveu a última versão como *delta*; "
                     f"o texto não distingue os dois. A contagem acima usa a última tabela. "
                     f"Nenhum Passo depende dela: os Passos 1 e 4 usam o módulo escrito em cada "
                     f"achado.\n")

    if n_achados < 30:
        L.append(f"> ⚠ **{n_achados} achados é pouco para sustentar os Passos 3 e 4.** A simulação de "
                 f"remoção e a sobreposição par a par produzem frações sobre denominadores pequenos; "
                 f"trate como indicativo, não como resultado.\n")

    L.append("\n## Passo 1 — incidência agregada (módulo × lente)\n")
    L.append("| projeto | módulo | lente | achados |")
    L.append("|---|---|---|---|")
    for (proj, mod, lente), ids in sorted(inc.items()):
        L.append(f"| {proj} | {mod} | {SIGLA.get(lente, lente)} | {', '.join(sorted(ids))} |")

    L.append("\n## Passo 2 — contribuição exclusiva por lente\n")
    L.append("Exclusiva = defeitos (clusters) em que a lente é a única presente.\n")
    L.append("| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |")
    L.append("|---|---|---|---|---|---|")
    for l in UNIVERSAIS + CONDICIONAIS:
        tipo = "univ" if l in UNIVERSAIS else "cond"
        L.append(f"| {SIGLA[l]} {l} | {tipo} | {len(ativou_em[l])} | {total[l]} | "
                 f"{exclusiva[l]} | {len(proj_excl[l])} |")

    # Duas evidências distintas, deliberadamente NÃO somadas:
    #   redundante    — achou, mas nada que outra lente não tenha achado (sobreposição)
    #   sem detecção  — não achou nada onde ativou (não exercitada, ou sem poder de detecção)
    # O §4 fala em "contribuição exclusiva zero" e as duas satisfazem a letra do critério,
    # mas só a primeira é evidência de redundância. Somá-las inflaria a lista de candidatas
    # a remoção com lentes sobre as quais o lote nada disse.
    redundantes = [l for l in UNIVERSAIS + CONDICIONAIS
                   if ativou_em[l] and total[l] > 0 and exclusiva[l] == 0]
    sem_deteccao = [l for l in UNIVERSAIS + CONDICIONAIS if ativou_em[l] and total[l] == 0]

    # A6 — grau de sobreposição, não só o veredito binário do §4.
    L.append("\n### Grau de sobreposição por lente (adendo A6)\n")
    L.append("Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de")
    L.append("remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta")
    L.append("coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%")
    L.append("de sobreposição, largamente redundante para qualquer leitor, passa no §4 como")
    L.append("legítima.\n")
    L.append("| lente | defeitos | compartilhados | % | distância até o critério |")
    L.append("|---|---|---|---|---|")
    for l in sorted(total_def, key=lambda x: -(compart[x] / total_def[x]) if total_def[x] else 0):
        # SEM_LENTE não é lente: é o canal do Passo 5 para achado que não coube em
        # nenhuma. Não tem critério de ativação nem se candidata a remoção.
        if not total_def[l] or l == SEM_LENTE:
            continue
        pc = 100 * compart[l] / total_def[l]
        L.append(f"| {SIGLA[l]} {l} | {total_def[l]} | {compart[l]} | {pc:.0f}% | "
                 f"faltam {total_def[l] - compart[l]} defeito(s) |")
    reais = {l: v for l, v in total_def.items() if l != SEM_LENTE}
    if reais:
        med = 100 * sum(compart[l] for l in reais) / sum(reais.values())
        L.append(f"\nSobreposição média: **{med:.0f}%**. Nenhuma lente é declarável removível "
                 f"pelo §4 enquanto essa coluna não chegar a 100%.")

    if redundantes:
        L.append("\n**Candidatas a remoção por redundância** — produziram achados, nenhum exclusivo "
                 "(todo defeito que viram, outra lente também viu):\n")
        for l in redundantes:
            L.append(f"- {SIGLA[l]} {l} — {total[l]} achado(s) em {len(ativou_em[l])} projeto(s), "
                     f"0 exclusivos")
    else:
        L.append("\nNenhuma lente produziu achados sem nenhuma contribuição exclusiva.")

    if sem_deteccao:
        L.append("\n**Sem detecção onde ativaram** — evidência DIFERENTE da anterior: não achar nada "
                 "não é o mesmo que achar só o que outra achou. Com poucos projetos, isto mede "
                 "exercício, não poder de detecção:\n")
        for l in sem_deteccao:
            L.append(f"- {SIGLA[l]} {l} — ativa em {len(ativou_em[l])} projeto(s), 0 achados")

    L.append("\n## Passo 3 — simulação de remoção\n")
    L.append("| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |")
    L.append("|---|---|---|---|---|")
    for l, d in sorted(fora.items(), key=lambda kv: -kv[1]["frac_defeitos_nao_recuperados"]):
        if not ativou_em[l]:
            continue
        L.append(f"| {SIGLA[l]} {l} | {d['achados_perdidos']} | {_pct(d['frac_achados_perdidos'])} | "
                 f"{d['defeitos_nao_recuperados']} | {_pct(d['frac_defeitos_nao_recuperados'])} |")

    L.append("\n## Passo 4 — sobreposição par a par\n")
    L.append("| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |")
    L.append("|---|---|---|---|---|")
    # Os pares NOMEADOS a priori pelo §4 entram sempre, mesmo fora do top 25. A coluna
    # "a priori?" existe para exibi-los, e ordenar por Jaccard os empurra para o fim
    # justamente quando a predição se sustenta — que é o caso interessante. Truncar aqui
    # já custou uma leitura errada: `ARQ × PRE` ficou de fora, e a ausência na tabela foi
    # lida como ausência de sobreposição. Eles compartilham 1 defeito, não zero.
    mostrar = pares[:25] + [d for d in pares[25:] if d["a_priori"]]
    for d in mostrar:
        marca = "sim (§4)" if d["a_priori"] else ""
        fora_do_top = " ⟵ fora do top 25, incluído por ser a priori" if d in pares[25:] else ""
        L.append(f"| {SIGLA.get(d['lente_a'])} × {SIGLA.get(d['lente_b'])} | "
                 f"{d['jaccard_modulos']:.2f} | {d['defeitos_em_comum']} | "
                 f"{d['jaccard_defeitos']:.3f} | {marca}{fora_do_top} |")
    if len(pares) > len(mostrar):
        L.append(f"\n*({len(pares) - len(mostrar)} pares restantes omitidos da tabela; todos "
                 f"estão no JSON — nenhum corte silencioso. Os pares a priori do §4 nunca "
                 f"são omitidos, independentemente da posição.)*")

    deriva = [(p.task_id, m, ids) for p in projetos
              for m, ids in getattr(p, "modulos_de_versoes_antigas", {}).items()]
    if deriva:
        L.append("\n### Módulos removidos entre versões da arquitetura\n")
        L.append("Achados de iterações anteriores citam módulos que a versão corrente não tem")
        L.append("mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua")
        L.append("válido contra a versão que ele criticou. Listado para leitura da matriz: quem")
        L.append("procurar o módulo na arquitetura final não vai encontrá-lo.\n")
        L.append("O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate")
        L.append("cruzado da v0.13.0 barra na origem, e não chega até aqui.\n")
        for t, m, ids in deriva:
            L.append(f"- `{t}` · **{m}** existia numa versão anterior · {len(ids)} achado(s): "
                     f"{', '.join(sorted(ids))}")

    L.append("\n## Passo 5 — cobertura\n")
    if sem_lente:
        L.append(f"**{len(sem_lente)} achado(s) não couberam em nenhuma lente** — indício de dimensão "
                 f"faltante na taxonomia:\n")
        for proj, aid, desc in sem_lente:
            L.append(f"- `{proj}` {aid}: {desc[:120]}")
    else:
        L.append("Nenhum achado marcado `NENHUMA` — nenhuma dimensão faltante declarada.")

    if ativas_sem_achado:
        L.append(f"\nLentes ativas que não produziram achado (por projeto): "
                 f"{len(ativas_sem_achado)} ocorrência(s).\n")
        for proj, l in ativas_sem_achado:
            L.append(f"- `{proj}` — {SIGLA[l]} {l}")

    if subcobertas:
        L.append("\n**Lentes condicionais sub-exercitadas** (< 3 projetos — o §2 declara que abaixo "
                 "disso não se distingue 'não detecta' de 'não foi exercitada'):\n")
        for l, n in subcobertas:
            L.append(f"- {SIGLA[l]} {l} — ativou em {n} projeto(s)")

    return "\n".join(L) + "\n"


def main(argv):
    saida_json = "--json" in argv
    caminhos = [a for a in argv if not a.startswith("--")]
    if not caminhos:
        print(__doc__)
        return 2

    projetos, erros = [], []
    for c in caminhos:
        try:
            projetos.append(carregar(Path(c)))
        except ErroDeFormato as e:
            erros.append(f"{Path(c).name}: {e}")

    if erros:
        print("ERRO DE FORMATO — análise interrompida.\n", file=sys.stderr)
        for e in erros:
            print(f"  {e}\n", file=sys.stderr)
        print("Nenhum resultado parcial é emitido: uma análise de RO3 sobre dado malformado "
              "pareceria completa e não seria.", file=sys.stderr)
        return 1

    if saida_json:
        total, exclusiva, proj_excl, ativou_em = passo2(projetos)
        fora, n_achados, n_clusters = passo3(projetos)
        print(json.dumps({
            "projetos": [p.task_id for p in projetos],
            "n_achados": n_achados, "n_defeitos": n_clusters,
            "passo2": {l: {"achados": total[l], "exclusiva": exclusiva[l],
                           "projetos_ativa": sorted(ativou_em[l])}
                       for l in UNIVERSAIS + CONDICIONAIS},
            "passo3": fora,
            "passo4": passo4(projetos),
        }, ensure_ascii=False, indent=2))
    else:
        print(relatorio(projetos))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
