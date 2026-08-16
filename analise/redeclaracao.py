"""A redeclaração de lentes entre iterações é trabalho real ou formalidade?

Uso:
    python3 redeclaracao.py            # o resumo
    python3 redeclaracao.py --textos   # e os pares, um a um, para inspeção

A PERGUNTA
----------
O laço 2↔3 exige que as 12 condicionais sejam redeclaradas a cada iteração, com uma
justificativa por lente não ativada. Se o agente copiasse a justificativa da iteração
anterior, a redeclaração seria ritual: o dado de cobertura por iteração não valeria nada.

O teste é comparar as justificativas de não-ativação entre iterações consecutivas, para
cada lente que aparece em ambas.

A MEDIDA, E POR QUE ESTA
------------------------
**Jaccard sobre tokens de palavra**, minúsculas, via `\\w+`: |A∩B| / |A∪B|.

Escolhida por três razões, e a terceira é a que decide:

  1. não tem parâmetro, heurística nem limiar — não há o que sintonizar sem querer;
  2. é insensível a ordem e a reformulação, que é exatamente o que se quer aqui: o
     interesse é se o agente reargumentou, não se ele reordenou;
  3. o artigo **já define Jaccard** para o leitor, na sobreposição entre lentes. Uma
     segunda medida exigiria um segundo parágrafo de definição para um resultado
     acessório.

A CONTAGEM DE "TEXTOS IDÊNTICOS" É INDEPENDENTE DA MEDIDA. É igualdade de string após
`strip()`. Não depende de escolha nenhuma, e é a metade da afirmação que carrega peso.

O QUE ESTE MÓDULO SUBSTITUI, E POR QUE
--------------------------------------
Uma versão descartável deste cálculo produziu a faixa **0,09–0,65** que circulou. Ela
usava `difflib.SequenceMatcher(None, a, b).ratio()` — Ratcliff/Obershelp em nível de
CARACTERE, com os defaults. Três problemas, em ordem de gravidade:

  1. **O piso era artefato.** O `difflib` liga uma heurística chamada *autojunk* quando a
     segunda sequência tem 200 elementos ou mais: elementos que aparecem em mais de 1%
     da sequência são tratados como lixo e não casam. Em caracteres de prosa portuguesa,
     isso descarta o espaço e quase todas as vogais. No T30-notifica, os textos têm 228 e
     212 caracteres, o `difflib` joga fora ` a d e g h i l m n o r s t u ã`, e o ratio cai
     de **0,405 para 0,091**. O 0,09 da faixa publicada é a heurística, não os textos.
     A heurística existe para diffs de código-fonte; prosa não é o caso de uso.
  2. **O teto estava errado.** A corrida original foi feita com **onze** projetos, antes
     de o T32 fechar, e a faixa foi reportada como sendo dos doze. Com os doze, o máximo
     daquela medida é 0,75 (T32), não 0,65 (T26).
  3. **Comparava só a primeira iteração com a última**, ignorando as intermediárias. Nos
     três projetos com 3 ou 4 voltas isso é a comparação errada: a afirmação é sobre o
     trabalho feito *entre* iterações.

Nenhum dos três muda a conclusão — os textos continuam sem repetição e longe de idênticos
por qualquer medida. Mas "0,09" convidava a pergunta "similaridade por que medida?", e a
resposta honesta era "por uma que descarta as vogais".
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def tokens(texto: str) -> set[str]:
    return set(re.findall(r"\w+", texto.lower()))


def jaccard(a: str, b: str) -> float:
    A, B = tokens(a), tokens(b)
    return len(A & B) / len(A | B) if A | B else float("nan")


def pares(ws: Path):
    """(iteração, lente, texto anterior, texto novo) para iterações consecutivas."""
    estado = json.loads((ws / ".versus" / "state.json").read_text(encoding="utf-8"))
    entradas = estado.get("activatedLenses") or []
    if len(entradas) < 2:
        return
    razoes = [{x["lens"]: x["reason"] for x in e["notActivated"]} for e in entradas]
    for i, (ant, nov) in enumerate(zip(razoes, razoes[1:]), start=1):
        for lente in sorted(set(ant) & set(nov)):
            yield i, lente, ant[lente], nov[lente]


def main(argv) -> int:
    projetos = sorted(p for p in RAIZ.glob("T*-*") if (p / "specs").is_dir())
    print(f"{'projeto':<18}{'its':>4}{'pares':>7}{'idênticos':>11}{'Jaccard médio':>15}")

    medias, total, identicos = [], 0, 0
    for ws in projetos:
        ps = list(pares(ws))
        if not ps:
            continue
        n_estado = len(json.loads((ws / ".versus" / "state.json")
                                  .read_text(encoding="utf-8"))["activatedLenses"])
        iguais = [p for p in ps if p[2].strip() == p[3].strip()]
        media = sum(jaccard(a, b) for _, _, a, b in ps) / len(ps)
        medias.append(media)
        total += len(ps)
        identicos += len(iguais)
        print(f"{ws.name:<18}{n_estado:>4}{len(ps):>7}{len(iguais):>11}{media:>15.2f}")

        if "--textos" in argv:
            for i, lente, a, b in ps:
                print(f"    it{i}→it{i+1}  {lente}  ·  Jaccard {jaccard(a, b):.2f}")
                print(f"      antes: {a}")
                print(f"      novo : {b}")

    print(f"\n{total} comparações em {len(medias)} projetos")
    print(f"justificativas idênticas: {identicos}"
          + ("" if identicos else "  — nenhuma foi copiada da iteração anterior"))
    print(f"Jaccard médio por projeto: {min(medias):.2f} a {max(medias):.2f}")
    print(f"Jaccard sobre todas as comparações: "
          f"{sum(jaccard(a, b) for ws in projetos for _, _, a, b in pares(ws)) / total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
