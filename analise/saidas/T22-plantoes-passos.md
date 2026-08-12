# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T22-plantoes)  
Achados: 71  ·  Defeitos distintos (clusters): 66  ·  Módulos: 11


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T22-plantoes | avaliador | ARQ | ARQ-07 |
| T22-plantoes | avaliador | PRE | ASS-05 |
| T22-plantoes | avaliador | CTR | CTL-03 |
| T22-plantoes | avaliador | ETI | ETI-03, ETI-04 |
| T22-plantoes | avaliador | DES | PER-02 |
| T22-plantoes | avaliador | SUS | SUS-02 |
| T22-plantoes | carregador | LIN | LIN-02 |
| T22-plantoes | carregador | REG | REG-03 |
| T22-plantoes | carregador | RES | RES-03 |
| T22-plantoes | carregador | SEG | SEC-02 |
| T22-plantoes | catalogo-restricoes | ARQ | ARQ-02 |
| T22-plantoes | catalogo-restricoes | PRE | ASS-01 |
| T22-plantoes | catalogo-restricoes | ETI | ETI-02 |
| T22-plantoes | catalogo-restricoes | JOG | GAM-02 |
| T22-plantoes | catalogo-restricoes | IMP | IMP-01 |
| T22-plantoes | catalogo-restricoes | LIN | LIN-01 |
| T22-plantoes | catalogo-restricoes | REG | REG-01, REG-02 |
| T22-plantoes | catalogo-restricoes | CIE | CIE-01 |
| T22-plantoes | cli | ARQ | ARQ-01 |
| T22-plantoes | cli | JOG | GAM-03 |
| T22-plantoes | cli | PRO | PRO-04 |
| T22-plantoes | cli | SEG | SEC-01 |
| T22-plantoes | cli | UX | UX-01, UX-02, UX-03, UX-04 |
| T22-plantoes | diagnostico | IMP | IMP-03 |
| T22-plantoes | diario | ARQ | ARQ-05 |
| T22-plantoes | diario | GOV | GOV-04 |
| T22-plantoes | diario | IMP | IMP-04 |
| T22-plantoes | diario | LIN | LIN-05 |
| T22-plantoes | diario | DES | PER-04 |
| T22-plantoes | diario | PRO | PRO-05 |
| T22-plantoes | diario | RES | RES-04 |
| T22-plantoes | diario | SEG | SEC-04 |
| T22-plantoes | diario | SUS | SUS-03 |
| T22-plantoes | dominio | ARQ | ARQ-04 |
| T22-plantoes | dominio | GOV | GOV-03 |
| T22-plantoes | dominio | LIN | LIN-03 |
| T22-plantoes | fronteira | ARQ | ARQ-03 |
| T22-plantoes | fronteira | PRE | ASS-02 |
| T22-plantoes | fronteira | CTR | CTL-01, CTL-02 |
| T22-plantoes | fronteira | CIE | CIE-03 |
| T22-plantoes | repositorio-json | GOV | GOV-01 |
| T22-plantoes | repositorio-json | LIN | LIN-04 |
| T22-plantoes | repositorio-json | DES | PER-03 |
| T22-plantoes | repositorio-json | RES | RES-02 |
| T22-plantoes | repositorio-json | SEG | SEC-03 |
| T22-plantoes | restricoes-legais | LIN | LIN-06 |
| T22-plantoes | restricoes-legais | REG | REG-04 |
| T22-plantoes | restricoes-legais | CIE | CIE-04 |
| T22-plantoes | restricoes-modelo | ARQ | ARQ-06 |
| T22-plantoes | restricoes-modelo | IMP | IMP-05 |
| T22-plantoes | solver-cpsat | PRE | ASS-04 |
| T22-plantoes | solver-cpsat | ETI | ETI-01 |
| T22-plantoes | solver-cpsat | IMP | IMP-02 |
| T22-plantoes | solver-cpsat | DES | PER-01 |
| T22-plantoes | solver-cpsat | RES | RES-01 |
| T22-plantoes | solver-cpsat | CIE | CIE-02 |
| T22-plantoes | solver-cpsat | SUS | SUS-01 |
| T22-plantoes | troca | PRE | ASS-03 |
| T22-plantoes | troca | JOG | GAM-01, GAM-04 |
| T22-plantoes | troca | GOV | GOV-02 |
| T22-plantoes | troca | PRO | PRO-01, PRO-02, PRO-03, PRO-06 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 5 | 5 | 1 |
| ARQ Architectural | univ | 1 | 7 | 7 | 1 |
| IMP Implementability | univ | 1 | 5 | 5 | 1 |
| CIE Scientific | univ | 1 | 4 | 4 | 1 |
| SEG Security | univ | 1 | 4 | 3 | 1 |
| DES Performance | univ | 1 | 4 | 2 | 1 |
| REG Regulatory | univ | 1 | 4 | 4 | 1 |
| RES Resilience | cond | 1 | 4 | 4 | 1 |
| UX UI/UX | cond | 1 | 4 | 3 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 1 | 1 |
| ETI Ethical / Human Impact | cond | 1 | 4 | 4 | 1 |
| PRO Process / Workflow | cond | 1 | 6 | 5 | 1 |
| GOV Governance / Accountability | cond | 1 | 4 | 4 | 1 |
| OBS Observability / Operability | cond | 0 | 0 | 0 | 0 |
| CTR Control Engineering | cond | 1 | 3 | 3 | 1 |
| JOG Game Theory | cond | 1 | 4 | 2 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 6 | 6 | 1 |
| MEC Mechanical Engineering | cond | 0 | 0 | 0 | 0 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 3 | 2 | 67% | faltam 1 defeito(s) |
| DES Performance | 4 | 2 | 50% | faltam 2 defeito(s) |
| JOG Game Theory | 3 | 1 | 33% | faltam 2 defeito(s) |
| SEG Security | 4 | 1 | 25% | faltam 3 defeito(s) |
| UX UI/UX | 4 | 1 | 25% | faltam 3 defeito(s) |
| PRO Process / Workflow | 6 | 1 | 17% | faltam 5 defeito(s) |
| PRE Assumptions | 5 | 0 | 0% | faltam 5 defeito(s) |
| ARQ Architectural | 7 | 0 | 0% | faltam 7 defeito(s) |
| IMP Implementability | 5 | 0 | 0% | faltam 5 defeito(s) |
| CIE Scientific | 4 | 0 | 0% | faltam 4 defeito(s) |
| REG Regulatory | 4 | 0 | 0% | faltam 4 defeito(s) |
| RES Resilience | 4 | 0 | 0% | faltam 4 defeito(s) |
| ETI Ethical / Human Impact | 4 | 0 | 0% | faltam 4 defeito(s) |
| GOV Governance / Accountability | 4 | 0 | 0% | faltam 4 defeito(s) |
| CTR Control Engineering | 3 | 0 | 0% | faltam 3 defeito(s) |
| LIN Linguistics / Grammar | 6 | 0 | 0% | faltam 6 defeito(s) |

Sobreposição média: **11%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| ARQ Architectural | 7 | 10% | 7 | 11% |
| LIN Linguistics / Grammar | 6 | 8% | 6 | 9% |
| PRE Assumptions | 5 | 7% | 5 | 8% |
| IMP Implementability | 5 | 7% | 5 | 8% |
| PRO Process / Workflow | 6 | 8% | 5 | 8% |
| CIE Scientific | 4 | 6% | 4 | 6% |
| REG Regulatory | 4 | 6% | 4 | 6% |
| RES Resilience | 4 | 6% | 4 | 6% |
| ETI Ethical / Human Impact | 4 | 6% | 4 | 6% |
| GOV Governance / Accountability | 4 | 6% | 4 | 6% |
| SEG Security | 4 | 6% | 3 | 5% |
| UX UI/UX | 4 | 6% | 3 | 5% |
| CTR Control Engineering | 3 | 4% | 3 | 5% |
| DES Performance | 4 | 6% | 2 | 3% |
| JOG Game Theory | 4 | 6% | 2 | 3% |
| SUS Sustainability / Proportionality | 3 | 4% | 1 | 2% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.75 | 2 | 0.40 |  |
| JOG × SEG | 0.17 | 1 | 0.17 |  |
| PRO × UX | 0.33 | 1 | 0.11 |  |
| ARQ × PRE | 0.33 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.29 | 0 | 0.00 |  |
| ARQ × ETI | 0.25 | 0 | 0.00 |  |
| ARQ × JOG | 0.25 | 0 | 0.00 |  |
| ARQ × GOV | 0.22 | 0 | 0.00 |  |
| ARQ × IMP | 0.33 | 0 | 0.00 |  |
| ARQ × LIN | 0.30 | 0 | 0.00 |  |
| ARQ × DES | 0.22 | 0 | 0.00 |  |
| ARQ × PRO | 0.25 | 0 | 0.00 |  |
| ARQ × REG | 0.11 | 0 | 0.00 |  |
| ARQ × RES | 0.10 | 0 | 0.00 |  |
| ARQ × CIE | 0.22 | 0 | 0.00 |  |
| ARQ × SEG | 0.22 | 0 | 0.00 |  |
| ARQ × SUS | 0.25 | 0 | 0.00 |  |
| ARQ × UX | 0.14 | 0 | 0.00 |  |
| PRE × CTR | 0.40 | 0 | 0.00 |  |
| PRE × ETI | 0.60 | 0 | 0.00 |  |
| PRE × JOG | 0.33 | 0 | 0.00 |  |
| PRE × GOV | 0.12 | 0 | 0.00 |  |
| PRE × IMP | 0.25 | 0 | 0.00 |  |
| PRE × LIN | 0.10 | 0 | 0.00 |  |
| PRE × DES | 0.29 | 0 | 0.00 |  |

*(95 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T22-plantoes` · **catalogo-restricoes** existia numa versão anterior · 9 achado(s): ARQ-02, ASS-01, CIE-01, ETI-02, GAM-02, IMP-01, LIN-01, REG-01, REG-02
- `T22-plantoes` · **fronteira** existia numa versão anterior · 5 achado(s): ARQ-03, ASS-02, CIE-03, CTL-01, CTL-02
- `T22-plantoes` · **diario** existia numa versão anterior · 9 achado(s): ARQ-05, GOV-04, IMP-04, LIN-05, PER-04, PRO-05, RES-04, SEC-04, SUS-03

## Passo 5 — cobertura

Nenhum achado marcado `NENHUMA` — nenhuma dimensão faltante declarada.

**Lentes condicionais sub-exercitadas** (< 3 projetos — o §2 declara que abaixo disso não se distingue 'não detecta' de 'não foi exercitada'):

- RES Resilience — ativou em 1 projeto(s)
- UX UI/UX — ativou em 1 projeto(s)
- MIG Migration / Coexistence — ativou em 0 projeto(s)
- SUS Sustainability / Proportionality — ativou em 1 projeto(s)
- ETI Ethical / Human Impact — ativou em 1 projeto(s)
- PRO Process / Workflow — ativou em 1 projeto(s)
- GOV Governance / Accountability — ativou em 1 projeto(s)
- OBS Observability / Operability — ativou em 0 projeto(s)
- CTR Control Engineering — ativou em 1 projeto(s)
- JOG Game Theory — ativou em 1 projeto(s)
- LIN Linguistics / Grammar — ativou em 1 projeto(s)
- MEC Mechanical Engineering — ativou em 0 projeto(s)

