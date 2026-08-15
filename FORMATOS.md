# Formatos e convenções do pacote

Referência para quem for ler ou reprocessar os dados. Nada aqui é interpretação — só o que
cada arquivo contém e como está estruturado.

---

## Convenção de nomes dos projetos

`T<nn>-<slug>`, por exemplo `T26-extratos`.

O número **não é ordinal de execução**. Vem do desenho de amostragem em `PROJETOS.md`, que
fixou doze slots antes do lote começar, cada um mirando um subconjunto de lentes
condicionais. A ordem em que foram executados está no `LOG-OPERACAO.md`.

Os slots do ciclo 2 vão de **T21 a T32**. Numerações abaixo de T21 pertencem ao ciclo 1,
**descartado por inteiro** e não incluído neste pacote — o motivo está no log.

**Um slot pode aparecer mais de uma vez no log** com slugs diferentes: `T21-cofre`,
`T21-quotas` e `T21-certificados` são três tentativas do mesmo slot, as duas primeiras
descartadas. Só o projeto válido está no pacote.

---

## Estrutura de um projeto

```
T26-extratos/
├── ENUNCIADO.md                      o problema, congelado antes da Fase 0
├── RETRABALHO.md                     defeitos pós-entrega e achados pré-entrega
├── specs/
│   ├── technical/architecture.md     arquitetura, uma seção por versão
│   ├── design/coverage-matrix.md     a matriz de achados — dado primário
│   ├── validation/  datasets/  references/  models/  domain/  …
├── <código do produto>
└── .versus/state.json                estado da metodologia
```

---

## `specs/design/coverage-matrix.md` — o dado primário

Tabela markdown. **Cinco colunas, nesta ordem, congeladas pelo §5 do protocolo:**

| coluna | conteúdo |
|---|---|
| 1 · `id` | `<PREFIXO>-<n>`, prefixo de 1 a 4 letras. `M-` é **reservado** a módulos e nunca é id de achado |
| 2 · `módulo` | nome do módulo, coluna 2 da tabela de arquitetura — a chave estável entre fases |
| 3 · `lente` | um dos **19 nomes canônicos**, ou o literal `NENHUMA` |
| 4 · `severidade` | `🔴` crítico · `🟡` importante · `🟢` sugestão |
| 5 · `descrição` | texto livre; pode conter o marcador `duplica: <id>` |

**`duplica: <id>`** dentro da descrição marca que o achado descreve o mesmo defeito que
`<id>`. É o discriminante de "mesmo defeito", e os clusters da análise são o **fecho
transitivo** dessas marcações (union-find). Vale entre lentes diferentes e dentro da mesma.

**Cabeçalhos `## Iteração N — V(N)`** separam as rodadas do laço crítica↔revisão. Um achado
pertence à iteração cujo cabeçalho o precede, e é validado contra o conjunto de lentes
declarado **naquela** iteração — não contra a união, e não contra a iteração corrente.

Os 19 nomes canônicos não estão escritos à mão em lugar nenhum: são extraídos do bundle em
`instrumento/server.js`. Ver `analise/ro3_parser.py`.

---

## `specs/technical/architecture.md`

Uma seção por versão, `## V(1)`, `## V(2)`, … A Fase 3 **acrescenta** uma seção a cada volta
do laço, em vez de sobrescrever — foi assim que a V(1) sobreviveu para as estimativas cegas.

Cada seção traz uma tabela de módulos: `M-<nn> | nome | responsabilidade | interface | dependências`.

**Ressalva de leitura:** uma versão pode ser um **delta** — só os módulos que mudaram. O
T23-canario escreveu 12, 12 e 4. Delta e remoção são indistinguíveis pelo texto, e o
relatório da análise avisa quando a última versão é menor que uma anterior. Nenhuma medida
da RO3 depende dessa contagem: os Passos usam o módulo escrito em **cada achado**.

---

## `.versus/state.json`

Estado da metodologia, escrito pela extensão. Campos que a análise usa:

| campo | conteúdo |
|---|---|
| `agent` | identificador do agente gerador (`"claude"`; o ID exato do modelo está no `LOG-OPERACAO.md`) |
| `currentPhase` · `currentIteration` | fase 0–7 e iteração corrente |
| `history[]` | `{from, to}` por transição — é daqui que sai o número de voltas do laço |
| `phase0Score` · `phase0Breakdown` | pontuação da Fase 0 |
| **`activatedLenses[]`** | **uma entrada por iteração** — ver abaixo |
| `decisions[]` | `{phase, category, content}` — o log narrativo |
| `exitCriteria[]` | `{phase, criterion, met, details}` |
| `safeguards[]` | `{id, status}` para S0–S7 |
| `lastTestOutcome` | `{outcome, phase, at}` — o registro do gate de testes |
| `stateVersion` | presente a partir da v0.14.0; distingue projeto novo de legado |

### `activatedLenses[]`

```json
{ "universal": ["Assumptions", "..."],          // as 7, sempre
  "conditional": ["Resilience", "..."],          // as declaradas ativas NESTA iteração
  "notActivated": [{"lens": "...", "reason": "..."}],   // as 12 devem estar contabilizadas
  "iteration": 2,
  "againstVersion": 3,                           // a versão da arquitetura criticada
  "recordedAt": "2026-08-10T01:14:12.419Z" }
```

**Uma entrada por iteração, não acumulada.** Em 3 dos 12 projetos o conjunto muda entre
iterações. Comparar uma estimativa sobre a V(1) com a **união** das iterações é erro — a
comparação correta é contra a entrada da iteração correspondente.

---

## `analise/cego/` — as avaliações cegas

| padrão | conteúdo |
|---|---|
| `T*-cego.md` | o pacote entregue ao juiz de duplicatas: matriz **sem** a coluna de lente, ids renomeados `F-01…`, ordem embaralhada por `sha256(taskId::id)`, marcações `duplica` removidas |
| `T*-mapa.json` | `{"cego_para_original": {"F-01": "UX-04", …}}`. **Não** era entregue ao juiz |
| `T*-resposta.json` | juiz `qwen3.6:27b` local, quantizado Q4_K_M |
| `T*-resposta-qwen3_6-27b.json` | juiz `qwen3.6-27b` precisão plena, via DashScope |
| `T*-resposta-gpt-5_4-2026-03-05.json` | juiz `gpt-5.4`, modelo pinado por data |

Todas as respostas de juiz: `{"grupos": [["F-03","F-14"], …]}` — cada lista é um conjunto
de achados que o juiz considerou o mesmo defeito.

### Estimativa de ativação de lentes

| padrão | conteúdo |
|---|---|
| `T*-reestimativa-V1-pacote.md` | o pacote: enunciado, arquitetura **V(1)**, tabela das 12 condicionais, regra de ativação |
| `T*-reestimativa-V1-<modelo>-r<n>.json` | estimativa sob os gatilhos **X**, rodada `n` de 3 |
| `T*-Y-V1-<modelo>-r<n>.json` | idem sob os gatilhos **Y** (primeira reescrita) |
| `T*-Y2-V1-<modelo>-r<n>.json` | idem sob **Y2** (ETI, MIG e CTR revisados após a medição de Y) |

Formato de toda estimativa:

```json
{ "projeto": "T24-catalogo",
  "modulos_estimados": 11,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "…"}]   // as 12, sempre
}
```

Uma lente é **estável** num projeto quando as três rodadas concordam (3/3 ou 0/3); as
demais são reportadas como oscilação e não entram nas contagens de concordância.

**Os pacotes X, Y e Y2 diferem entre si apenas no texto do gatilho.** X→Y: 18 linhas.
Y→Y2: 6 linhas. Todo o resto é byte-idêntico — verificável com `diff`.

### Adjudicação da lente Ética

| arquivo | conteúdo |
|---|---|
| `ETI-adjudicacao-itens.txt` | os 60 achados cegados, `A-nn \| descrição`, um por linha |
| `ETI-adjudicacao-mapa.json` | `{"A-01": {"proj", "grupo", "lente", "id", "desc"}}`; `grupo` é `D` disputado ou `C` controle |
| `ETI-adjudicacao-claude.json` · `-gpt.json` | `{"vereditos": [{"id": "A-01", "v": "SIM|NAO|DUVIDA"}]}` |

O critério, fixado e datado **antes** da leitura, está em `analise/CRITERIO-ADJUDICACAO-ETI.md`.

---

## `analise/saidas/`

| padrão | conteúdo |
|---|---|
| `AGREGADO-<n>.md` | Passos 1–5 do §4 sobre os `n` primeiros projetos fechados. **`AGREGADO-12.md` é o do paper** |
| `T*-passos.md` | os mesmos Passos, por projeto |
| `T*-FECHAMENTO.md` | leitura do projeto no fechamento, com o que exigiu atenção |

Os agregados intermediários existem porque a análise era incremental — cada projeto novo
podia refutar a leitura anterior, e cinco refutaram. `RESULTADO-RO3.md` §6 tabula.

### `analise/saidas/figuras/` — os dados das figuras do paper

| padrão | conteúdo |
|---|---|
| `fig-robustness.csv` | contribuição exclusiva por lente sob as quatro clusterizações — §1.4 |
| `fig-divergences.csv` | divergências de ativação por lente, com direção — §2.4 |
| `fig-kappa-rates.csv` | pares marcados por avaliador — §5.1 |
| `fig-kappa-chance.csv` | co-marcações observadas, esperadas ao acaso e κ, por par — §5.1 |
| `fig-annotations.csv` | anotações de eixo que carregam número, montadas do computado |
| `fig-*.pdf` | as figuras renderizadas |

Formato longo: uma linha por ponto plotado, **na ordem do eixo**, com os rótulos de legenda
já montados e suas contagens embutidas. Quem consome não ordena, não rotula, não deriva.

`fig-kappa-chance.csv` traz `expected` em precisão plena e **não traz o ratio** — ele é
`observed / expected`, computado no script da figura. Dividir pelos 0,24 / 0,54 / 0,14
arredondados da tabela do §5.1 erra o ratio em até meia unidade.

**Como regenerar:**

```
python3 analise/figuras.py --conferir     # computa os CSV e confere contra o RESULTADO-RO3.md
Rscript --vanilla analise/figuras/make_figures.R
```

O `--conferir` recomputa as tabelas do §1.4 e do §5.1 direto do corpus e as compara, célula
a célula, com o que está escrito na fonte única. **Sai com código 1 se divergirem.** Foi
assim que se descobriu que o painel do §5.1, computado à mão no fechamento, usava aresta
declarada para o gerador e fecho transitivo para os juízes cegos — duas definições de
"mesmo defeito" dentro do mesmo κ.

---

## Códigos das lentes

Abreviações de três letras usadas nos relatórios. **Nunca aceitas como entrada** — a coluna
`lente` da matriz exige o nome canônico completo.

| | | | |
|---|---|---|---|
| PRE Assumptions | ARQ Architectural | IMP Implementability | CIE Scientific |
| SEG Security | DES Performance | REG Regulatory | RES Resilience |
| UX UI/UX | MIG Migration / Coexistence | SUS Sustainability / Proportionality | ETI Ethical / Human Impact |
| PRO Process / Workflow | GOV Governance / Accountability | OBS Observability / Operability | CTR Control Engineering |
| JOG Game Theory | LIN Linguistics / Grammar | MEC Mechanical Engineering | |

As sete primeiras são **universais** — rodam em todo projeto. As doze restantes são
**condicionais**, declaradas por iteração.
