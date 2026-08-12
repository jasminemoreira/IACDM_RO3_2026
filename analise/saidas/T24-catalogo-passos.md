# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T24-catalogo)  
Achados: 75  ·  Defeitos distintos (clusters): 70  ·  Módulos: 9


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T24-catalogo | catalog | PRE | ASM-03 |
| T24-catalogo | catalog | JOG | GAME-02 |
| T24-catalogo | catalog | GOV | GOV-01 |
| T24-catalogo | catalog | PRO | PROC-03 |
| T24-catalogo | catalog-mapper | ARQ | ARC-06 |
| T24-catalogo | catalog-mapper | PRE | ASM-01 |
| T24-catalogo | catalog-mapper | CTR | CTRL-03 |
| T24-catalogo | catalog-mapper | JOG | GAME-01 |
| T24-catalogo | catalog-mapper | GOV | GOV-02 |
| T24-catalogo | catalog-mapper | IMP | IMPL-07 |
| T24-catalogo | catalog-mapper | LIN | LING-01, LING-06 |
| T24-catalogo | catalog-mapper | DES | PERF-04 |
| T24-catalogo | catalog-repository | ARQ | ARC-01 |
| T24-catalogo | catalog-repository | PRE | ASM-02 |
| T24-catalogo | catalog-repository | CTR | CTRL-01 |
| T24-catalogo | catalog-repository | IMP | IMPL-02 |
| T24-catalogo | catalog-repository | DES | PERF-01 |
| T24-catalogo | catalog-repository | PRO | PROC-02 |
| T24-catalogo | catalog-repository | RES | RES-02, RES-03 |
| T24-catalogo | catalog-repository | SEG | SEC-02 |
| T24-catalogo | catalog-repository | SUS | SUS-01 |
| T24-catalogo | cli | ARQ | ARC-04, ARC-08 |
| T24-catalogo | cli | PRO | PROC-01, PROC-04, PROC-05 |
| T24-catalogo | cli | REG | REG-02 |
| T24-catalogo | cli | SUS | SUS-03 |
| T24-catalogo | cli | UX | UX-02, UX-04 |
| T24-catalogo | errors | ARQ | ARC-02 |
| T24-catalogo | formatters | JOG | GAME-03 |
| T24-catalogo | formatters | GOV | GOV-05 |
| T24-catalogo | formatters | IMP | IMPL-03 |
| T24-catalogo | formatters | LIN | LING-03 |
| T24-catalogo | formatters | UX | UX-01, UX-03, UX-06 |
| T24-catalogo | lineage-graph | MEC | MEC-02 |
| T24-catalogo | lineage-graph | CIE | SCI-01, SCI-02, SCI-03 |
| T24-catalogo | lineage-graph | SUS | SUS-02 |
| T24-catalogo | model | ARQ | ARC-05, ARC-07 |
| T24-catalogo | model | PRE | ASM-05 |
| T24-catalogo | model | GOV | GOV-03, GOV-04 |
| T24-catalogo | model | IMP | IMPL-04, IMPL-05, IMPL-06 |
| T24-catalogo | model | LIN | LING-02 |
| T24-catalogo | model | MEC | MEC-03, MEC-04 |
| T24-catalogo | model | REG | REG-01, REG-03 |
| T24-catalogo | model | SEG | SEC-03, SEC-05 |
| T24-catalogo | query-service | PRE | ASM-04, ASM-06 |
| T24-catalogo | validation | ARQ | ARC-03 |
| T24-catalogo | validation | CTR | CTRL-02 |
| T24-catalogo | validation | IMP | IMPL-01, IMPL-08 |
| T24-catalogo | validation | LIN | LING-04 |
| T24-catalogo | validation | DES | PERF-02 |
| T24-catalogo | yaml-loader | LIN | LING-05 |
| T24-catalogo | yaml-loader | MEC | MEC-01 |
| T24-catalogo | yaml-loader | RES | RES-01, RES-04 |
| T24-catalogo | yaml-loader | SEG | SEC-01, SEC-04 |
| T24-catalogo | yaml-loader | UX | UX-05 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 6 | 6 | 1 |
| ARQ Architectural | univ | 1 | 8 | 8 | 1 |
| IMP Implementability | univ | 1 | 8 | 8 | 1 |
| CIE Scientific | univ | 1 | 3 | 2 | 1 |
| SEG Security | univ | 1 | 5 | 4 | 1 |
| DES Performance | univ | 1 | 3 | 2 | 1 |
| REG Regulatory | univ | 1 | 3 | 1 | 1 |
| RES Resilience | cond | 1 | 4 | 4 | 1 |
| UX UI/UX | cond | 1 | 6 | 6 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 1 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 5 | 5 | 1 |
| GOV Governance / Accountability | cond | 1 | 5 | 5 | 1 |
| OBS Observability / Operability | cond | 0 | 0 | 0 | 0 |
| CTR Control Engineering | cond | 1 | 3 | 3 | 1 |
| JOG Game Theory | cond | 1 | 3 | 3 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 6 | 6 | 1 |
| MEC Mechanical Engineering | cond | 1 | 4 | 4 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| REG Regulatory | 2 | 1 | 50% | faltam 1 defeito(s) |
| SUS Sustainability / Proportionality | 2 | 1 | 50% | faltam 1 defeito(s) |
| DES Performance | 3 | 1 | 33% | faltam 2 defeito(s) |
| SEG Security | 5 | 1 | 20% | faltam 4 defeito(s) |
| PRE Assumptions | 6 | 0 | 0% | faltam 6 defeito(s) |
| ARQ Architectural | 8 | 0 | 0% | faltam 8 defeito(s) |
| IMP Implementability | 8 | 0 | 0% | faltam 8 defeito(s) |
| CIE Scientific | 2 | 0 | 0% | faltam 2 defeito(s) |
| RES Resilience | 4 | 0 | 0% | faltam 4 defeito(s) |
| UX UI/UX | 6 | 0 | 0% | faltam 6 defeito(s) |
| PRO Process / Workflow | 5 | 0 | 0% | faltam 5 defeito(s) |
| GOV Governance / Accountability | 5 | 0 | 0% | faltam 5 defeito(s) |
| CTR Control Engineering | 3 | 0 | 0% | faltam 3 defeito(s) |
| JOG Game Theory | 3 | 0 | 0% | faltam 3 defeito(s) |
| LIN Linguistics / Grammar | 6 | 0 | 0% | faltam 6 defeito(s) |
| MEC Mechanical Engineering | 4 | 0 | 0% | faltam 4 defeito(s) |

Sobreposição média: **6%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| ARQ Architectural | 8 | 11% | 8 | 11% |
| IMP Implementability | 8 | 11% | 8 | 11% |
| PRE Assumptions | 6 | 8% | 6 | 9% |
| UX UI/UX | 6 | 8% | 6 | 9% |
| LIN Linguistics / Grammar | 6 | 8% | 6 | 9% |
| PRO Process / Workflow | 5 | 7% | 5 | 7% |
| GOV Governance / Accountability | 5 | 7% | 5 | 7% |
| SEG Security | 5 | 7% | 4 | 6% |
| RES Resilience | 4 | 5% | 4 | 6% |
| MEC Mechanical Engineering | 4 | 5% | 4 | 6% |
| CTR Control Engineering | 3 | 4% | 3 | 4% |
| JOG Game Theory | 3 | 4% | 3 | 4% |
| CIE Scientific | 3 | 4% | 2 | 3% |
| DES Performance | 3 | 4% | 2 | 3% |
| REG Regulatory | 3 | 4% | 1 | 1% |
| SUS Sustainability / Proportionality | 3 | 4% | 1 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.20 | 1 | 0.25 |  |
| REG × SEG | 0.25 | 1 | 0.17 |  |
| ARQ × PRE | 0.38 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.50 | 0 | 0.00 |  |
| ARQ × JOG | 0.12 | 0 | 0.00 |  |
| ARQ × GOV | 0.25 | 0 | 0.00 |  |
| ARQ × IMP | 0.57 | 0 | 0.00 |  |
| ARQ × LIN | 0.38 | 0 | 0.00 |  |
| ARQ × MEC | 0.12 | 0 | 0.00 |  |
| ARQ × DES | 0.50 | 0 | 0.00 |  |
| ARQ × PRO | 0.29 | 0 | 0.00 |  |
| ARQ × REG | 0.33 | 0 | 0.00 |  |
| ARQ × RES | 0.14 | 0 | 0.00 |  |
| ARQ × CIE | 0.00 | 0 | 0.00 |  |
| ARQ × SEG | 0.29 | 0 | 0.00 |  |
| ARQ × SUS | 0.29 | 0 | 0.00 |  |
| ARQ × UX | 0.12 | 0 | 0.00 |  |
| PRE × CTR | 0.33 | 0 | 0.00 |  |
| PRE × JOG | 0.33 | 0 | 0.00 |  |
| PRE × GOV | 0.50 | 0 | 0.00 |  |
| PRE × IMP | 0.43 | 0 | 0.00 |  |
| PRE × LIN | 0.25 | 0 | 0.00 |  |
| PRE × MEC | 0.14 | 0 | 0.00 |  |
| PRE × DES | 0.33 | 0 | 0.00 |  |
| PRE × PRO | 0.33 | 0 | 0.00 |  |

*(95 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T24-catalogo` · **catalog-repository** existia numa versão anterior · 10 achado(s): ARC-01, ASM-02, CTRL-01, IMPL-02, PERF-01, PROC-02, RES-02, RES-03, SEC-02, SUS-01
- `T24-catalogo` · **errors** existia numa versão anterior · 1 achado(s): ARC-02

## Passo 5 — cobertura

Nenhum achado marcado `NENHUMA` — nenhuma dimensão faltante declarada.

**Lentes condicionais sub-exercitadas** (< 3 projetos — o §2 declara que abaixo disso não se distingue 'não detecta' de 'não foi exercitada'):

- RES Resilience — ativou em 1 projeto(s)
- UX UI/UX — ativou em 1 projeto(s)
- MIG Migration / Coexistence — ativou em 0 projeto(s)
- SUS Sustainability / Proportionality — ativou em 1 projeto(s)
- ETI Ethical / Human Impact — ativou em 0 projeto(s)
- PRO Process / Workflow — ativou em 1 projeto(s)
- GOV Governance / Accountability — ativou em 1 projeto(s)
- OBS Observability / Operability — ativou em 0 projeto(s)
- CTR Control Engineering — ativou em 1 projeto(s)
- JOG Game Theory — ativou em 1 projeto(s)
- LIN Linguistics / Grammar — ativou em 1 projeto(s)
- MEC Mechanical Engineering — ativou em 1 projeto(s)

