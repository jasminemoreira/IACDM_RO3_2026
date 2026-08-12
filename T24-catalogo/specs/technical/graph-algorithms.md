# Algoritmos de grafo — detecção de ciclo e travessia downstream

Material técnico da Fase 0 (iteração 1). Cada algoritmo tem referência bibliográfica
verificável, conforme exigido pela lente Científica da Fase 2 e pelo safeguard S6.

Contexto: a linhagem do T24 é um **grafo dirigido, decidido como DAG estrito** — ciclo
é erro de declaração e o carregamento falha apontando o ciclo (decisão de Fase 0).
Duas operações são necessárias: **(A) detectar ciclo** e **(B) alcançar todos os
descendentes de um nó** (análise de impacto downstream).

---

## A. Detecção de ciclo / ordenação topológica

### A.1 — Algoritmo de Kahn (1962) — REFERÊNCIA PRIMÁRIA

**Citação completa:**
> Kahn, Arthur B. (1962). "Topological sorting of large networks".
> *Communications of the ACM*, **5**(11): 558–562. doi:10.1145/368996.369025.

Fonte da citação: https://en.wikipedia.org/wiki/Topological_sorting
(o PDF original está atrás de paywall em https://dl.acm.org/doi/10.1145/368996.369025 — HTTP 403)

**Mecanismo:** remove repetidamente os nós sem aresta de entrada (raízes) e suas
arestas de saída. Um DAG sempre tem ao menos uma raiz, e remover raízes de um DAG
produz um subgrafo que ainda é um DAG. Logo, **terminação prematura só ocorre se o
subgrafo corrente não tem raiz — o que indica diretamente a existência de ao menos um
ciclo no grafo original**.

**Detecção de ciclo (pseudocódigo da referência, verbatim):**
> `if graph has edges then return error (graph has at least one cycle)`

— avaliado após o laço principal. É por isso que Kahn serve para as duas coisas ao
mesmo tempo: a ordenação topológica e o teste de aciclicidade são o mesmo passo.

**Complexidade:** O(V + E).

**Limitação para o T24:** Kahn detecta *que existe* ciclo (arestas remanescentes), mas
não devolve *qual é* o ciclo. O requisito de Fase 0 é "o carregamento FALHA **apontando
o ciclo**" — a mensagem de erro precisa nomear os datasets envolvidos. Portanto Kahn
sozinho é insuficiente: é preciso um passo adicional que extraia o ciclo concreto
(ver A.2 e seção C).

### A.2 — Ordenação topológica por DFS

**Citações:**
> Cormen, T. H. et al. (2001). *Introduction to Algorithms*, 2ª ed., MIT Press /
> McGraw-Hill, Seção 22.4, pp. 549–552.

> Tarjan, Robert E. (1976). "Edge-disjoint spanning trees and depth-first search".
> *Acta Informatica*, **6**(2): 171–185. doi:10.1007/BF00268499.

Fonte das citações: https://en.wikipedia.org/wiki/Topological_sorting — a página nota
que Cormen descreve o algoritmo DFS, mas Tarjan aparentemente foi o primeiro a
publicá-lo (1976).

**Vantagem sobre Kahn no caso T24:** a DFS marca nós "em progresso" na pilha de
recursão; ao encontrar uma aresta para um nó em progresso (*back edge*), o ciclo
concreto é exatamente o trecho da pilha — ou seja, **a DFS entrega o ciclo nomeado**,
que é o que a mensagem de erro exige.

**Complexidade:** O(V + E).

---

## B. Travessia downstream (análise de impacto)

A pergunta central do produto — "se eu quebrar X, o que quebra junto?" — é o conjunto
de **todos os nós alcançáveis a partir de X** seguindo as arestas na direção do fluxo.

- Busca em largura (BFS) ou profundidade (DFS) a partir de X, coletando visitados.
- Complexidade O(V + E) no pior caso.
- Num DAG estrito a travessia termina sem necessidade de conjunto de visitados por
  proteção contra ciclo — mas o conjunto continua necessário para **evitar reprocessar
  nós alcançáveis por múltiplos caminhos** (diamante A→B→D, A→C→D).
- A direção inversa (ancestrais) responderia "de onde veio este dado" — **fora do
  escopo decidido na Fase 0**, embora seja o mesmo algoritmo com as arestas invertidas.

---

## C. Tier 1 — biblioteca madura disponível (NetworkX)

**Fontes:**
- https://networkx.org/documentation/stable/reference/algorithms/dag.html
- https://networkx.org/documentation/stable/reference/algorithms/cycles.html

| Função | O que faz |
|---|---|
| `is_directed_acyclic_graph(G)` | "Returns True if the graph G is a directed acyclic graph (DAG) or False if not." |
| `topological_sort(G)` | "Returns a generator of nodes in topologically sorted order." |
| `topological_generations(G)` | "Stratifies a DAG into generations." |
| `descendants(G, source)` | "Returns all nodes reachable from source in G." — **é exatamente a análise de impacto downstream** |
| `ancestors(G, source)` | "Returns all nodes having a path to source in G." |
| `find_cycle(G[, source, orientation])` | "Returns a cycle found via depth-first traversal" — **entrega o ciclo concreto** |
| `simple_cycles(G[, length_bound])` | "Find simple cycles (elementary circuits) of a graph" |

**ADVERTÊNCIA da própria documentação (verbatim):**
> "Note that most of these functions are only guaranteed to work for DAGs. In general,
> these functions do not check for acyclic-ness, so it is up to the user to check for
> that."

Consequência direta para o T24: a validação de aciclicidade **precisa ser executada
explicitamente antes** de qualquer travessia. Não é opcional nem implícita.

**Combinação sugerida (a confirmar na Fase 1 — decisão de arquitetura, não de Fase 0):**
`is_directed_acyclic_graph` para o teste, `find_cycle` para nomear o ciclo na mensagem
de erro, `descendants` para o impacto.

**Ponto aberto para a Fase 1 (Validação Tecnológica):** NetworkX é Tier 1 maduro, mas é
uma dependência considerável para um grafo que pode ser um `dict[str, set[str]]`. As
três operações necessárias (aciclicidade, extração de ciclo, alcançáveis) somam poucas
dezenas de linhas de código com referência bibliográfica acima. A escolha
NetworkX × implementação própria portada de Kahn/DFS deve ir para tabela comparativa
na Fase 1, não ser decidida aqui.
