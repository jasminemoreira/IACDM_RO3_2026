# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T31-precos)  
Achados: 109  ·  Defeitos distintos (clusters): 104  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T31-precos | api-http | LIN | LIN-04, LIN-06 |
| T31-precos | api-http | MEC | MEC-03 |
| T31-precos | api-http | OBS | OBS-03, OBS-06 |
| T31-precos | api-http | SEG | SEC-01, SEC-05 |
| T31-precos | dinheiro | MEC | MEC-05, MEC-06 |
| T31-precos | dinheiro | CIE | SCI-02 |
| T31-precos | explicador | ARQ | ARQ-04 |
| T31-precos | explicador | PRE | ASS-06 |
| T31-precos | importador-csv | ARQ | ARQ-05 |
| T31-precos | importador-csv | PRE | ASS-04, ASS-08 |
| T31-precos | importador-csv | CTR | CTL-03 |
| T31-precos | importador-csv | GOV | GOV-03 |
| T31-precos | importador-csv | IMP | IMP-03 |
| T31-precos | importador-csv | LIN | LIN-03, LIN-07, LIN-08, LIN-09, LIN-10 |
| T31-precos | importador-csv | MEC | MEC-02, MEC-04 |
| T31-precos | importador-csv | MIG | MIG-03, MIG-04, MIG-05 |
| T31-precos | importador-csv | DES | PERF-05 |
| T31-precos | importador-csv | REG | REG-03 |
| T31-precos | importador-csv | RES | RES-03 |
| T31-precos | importador-csv | SEG | SEC-02, SEC-06, SEC-07 |
| T31-precos | modelo-dominio | ARQ | ARQ-08 |
| T31-precos | modelo-dominio | PRE | ASS-02, ASS-05 |
| T31-precos | modelo-dominio | GOV | GOV-02 |
| T31-precos | modelo-dominio | IMP | IMP-05, IMP-06 |
| T31-precos | modelo-dominio | LIN | LIN-01, LIN-02, LIN-05 |
| T31-precos | modelo-dominio | CIE | SCI-04 |
| T31-precos | motor-precificacao | PRE | ASS-01 |
| T31-precos | motor-precificacao | OBS | OBS-02 |
| T31-precos | motor-precificacao | DES | PERF-01, PERF-06 |
| T31-precos | prova-paridade | ARQ | ARQ-01 |
| T31-precos | prova-paridade | MEC | MEC-01 |
| T31-precos | prova-paridade | MIG | MIG-02 |
| T31-precos | prova-paridade | DES | PERF-02 |
| T31-precos | repositorio-sqlite | PRE | ASS-03 |
| T31-precos | repositorio-sqlite | CTR | CTL-04, CTL-05 |
| T31-precos | repositorio-sqlite | GOV | GOV-01, GOV-04, GOV-05, GOV-06, GOV-07 |
| T31-precos | repositorio-sqlite | DES | PERF-03 |
| T31-precos | repositorio-sqlite | REG | REG-02 |
| T31-precos | repositorio-sqlite | RES | RES-01 |
| T31-precos | repositorio-sqlite | SEG | SEC-04 |
| T31-precos | repositorio-sqlite | SUS | SUS-01, SUS-02, SUS-03 |
| T31-precos | resolvedor-precedencia | CIE | SCI-03 |
| T31-precos | servico-aplicacao | ARQ | ARQ-02, ARQ-07 |
| T31-precos | servico-aplicacao | PRE | ASS-07, ASS-09, ASS-10 |
| T31-precos | servico-aplicacao | CTR | CTL-01, CTL-02 |
| T31-precos | servico-aplicacao | MIG | MIG-01 |
| T31-precos | servico-aplicacao | OBS | OBS-01, OBS-04, OBS-05 |
| T31-precos | servico-aplicacao | DES | PERF-07 |
| T31-precos | servico-aplicacao | PRO | PRO-01, PRO-02, PRO-03, PRO-05 |
| T31-precos | servico-aplicacao | REG | REG-01 |
| T31-precos | servico-aplicacao | RES | RES-02, RES-05, RES-06, RES-07 |
| T31-precos | servico-aplicacao | CIE | SCI-01 |
| T31-precos | servico-aplicacao | SUS | SUS-04 |
| T31-precos | ui-editor-regras | ARQ | ARQ-06 |
| T31-precos | ui-editor-regras | IMP | IMP-04 |
| T31-precos | ui-editor-regras | PRO | PRO-06 |
| T31-precos | ui-web | ARQ | ARQ-03 |
| T31-precos | ui-web | IMP | IMP-01 |
| T31-precos | ui-web | RES | RES-04 |
| T31-precos | ui-web | SEG | SEC-03 |
| T31-precos | ui-web | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08 |
| T31-precos | validador-coerencia | IMP | IMP-02 |
| T31-precos | validador-coerencia | DES | PERF-04 |
| T31-precos | validador-coerencia | PRO | PRO-04 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 10 | 7 | 1 |
| ARQ Architectural | univ | 1 | 8 | 8 | 1 |
| IMP Implementability | univ | 1 | 6 | 6 | 1 |
| CIE Scientific | univ | 1 | 4 | 4 | 1 |
| SEG Security | univ | 1 | 7 | 7 | 1 |
| DES Performance | univ | 1 | 7 | 6 | 1 |
| REG Regulatory | univ | 1 | 3 | 2 | 1 |
| RES Resilience | cond | 1 | 7 | 6 | 1 |
| UX UI/UX | cond | 1 | 8 | 8 | 1 |
| MIG Migration / Coexistence | cond | 1 | 5 | 4 | 1 |
| SUS Sustainability / Proportionality | cond | 1 | 4 | 3 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 6 | 6 | 1 |
| GOV Governance / Accountability | cond | 1 | 7 | 7 | 1 |
| OBS Observability / Operability | cond | 1 | 6 | 6 | 1 |
| CTR Control Engineering | cond | 1 | 5 | 5 | 1 |
| JOG Game Theory | cond | 0 | 0 | 0 | 0 |
| LIN Linguistics / Grammar | cond | 1 | 10 | 10 | 1 |
| MEC Mechanical Engineering | cond | 1 | 6 | 6 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| PRE Assumptions | 10 | 3 | 30% | faltam 7 defeito(s) |
| SUS Sustainability / Proportionality | 4 | 1 | 25% | faltam 3 defeito(s) |
| MIG Migration / Coexistence | 5 | 1 | 20% | faltam 4 defeito(s) |
| RES Resilience | 7 | 1 | 14% | faltam 6 defeito(s) |
| ARQ Architectural | 8 | 0 | 0% | faltam 8 defeito(s) |
| IMP Implementability | 6 | 0 | 0% | faltam 6 defeito(s) |
| CIE Scientific | 4 | 0 | 0% | faltam 4 defeito(s) |
| SEG Security | 7 | 0 | 0% | faltam 7 defeito(s) |
| DES Performance | 6 | 0 | 0% | faltam 6 defeito(s) |
| REG Regulatory | 2 | 0 | 0% | faltam 2 defeito(s) |
| UX UI/UX | 8 | 0 | 0% | faltam 8 defeito(s) |
| PRO Process / Workflow | 6 | 0 | 0% | faltam 6 defeito(s) |
| GOV Governance / Accountability | 7 | 0 | 0% | faltam 7 defeito(s) |
| OBS Observability / Operability | 6 | 0 | 0% | faltam 6 defeito(s) |
| LIN Linguistics / Grammar | 10 | 0 | 0% | faltam 10 defeito(s) |
| MEC Mechanical Engineering | 6 | 0 | 0% | faltam 6 defeito(s) |
| CTR Control Engineering | 5 | 0 | 0% | faltam 5 defeito(s) |

Sobreposição média: **6%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| LIN Linguistics / Grammar | 10 | 9% | 10 | 10% |
| ARQ Architectural | 8 | 7% | 8 | 8% |
| UX UI/UX | 8 | 7% | 8 | 8% |
| PRE Assumptions | 10 | 9% | 7 | 7% |
| SEG Security | 7 | 6% | 7 | 7% |
| GOV Governance / Accountability | 7 | 6% | 7 | 7% |
| IMP Implementability | 6 | 6% | 6 | 6% |
| DES Performance | 7 | 6% | 6 | 6% |
| RES Resilience | 7 | 6% | 6 | 6% |
| PRO Process / Workflow | 6 | 6% | 6 | 6% |
| OBS Observability / Operability | 6 | 6% | 6 | 6% |
| MEC Mechanical Engineering | 6 | 6% | 6 | 6% |
| CTR Control Engineering | 5 | 5% | 5 | 5% |
| CIE Scientific | 4 | 4% | 4 | 4% |
| MIG Migration / Coexistence | 5 | 5% | 4 | 4% |
| SUS Sustainability / Proportionality | 4 | 4% | 3 | 3% |
| REG Regulatory | 3 | 3% | 2 | 2% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| PRE × SUS | 0.33 | 1 | 0.08 |  |
| PRE × MIG | 0.29 | 1 | 0.07 |  |
| PRE × RES | 0.43 | 1 | 0.06 |  |
| ARQ × PRE | 0.44 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.25 | 0 | 0.00 |  |
| ARQ × GOV | 0.25 | 0 | 0.00 |  |
| ARQ × IMP | 0.50 | 0 | 0.00 |  |
| ARQ × LIN | 0.25 | 0 | 0.00 |  |
| ARQ × MEC | 0.22 | 0 | 0.00 |  |
| ARQ × MIG | 0.43 | 0 | 0.00 |  |
| ARQ × OBS | 0.11 | 0 | 0.00 |  |
| ARQ × DES | 0.30 | 0 | 0.00 |  |
| ARQ × PRO | 0.25 | 0 | 0.00 |  |
| ARQ × REG | 0.25 | 0 | 0.00 |  |
| ARQ × RES | 0.38 | 0 | 0.00 |  |
| ARQ × CIE | 0.22 | 0 | 0.00 |  |
| ARQ × SEG | 0.22 | 0 | 0.00 |  |
| ARQ × SUS | 0.12 | 0 | 0.00 |  |
| ARQ × UX | 0.14 | 0 | 0.00 |  |
| PRE × CTR | 0.50 | 0 | 0.00 |  |
| PRE × GOV | 0.50 | 0 | 0.00 |  |
| PRE × IMP | 0.22 | 0 | 0.00 |  |
| PRE × LIN | 0.29 | 0 | 0.00 |  |
| PRE × MEC | 0.11 | 0 | 0.00 |  |
| PRE × OBS | 0.29 | 0 | 0.00 |  |

*(111 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T31-precos` · **prova-paridade** existia numa versão anterior · 4 achado(s): ARQ-01, MEC-01, MIG-02, PERF-02

## Passo 5 — cobertura

Nenhum achado marcado `NENHUMA` — nenhuma dimensão faltante declarada.

**Lentes condicionais sub-exercitadas** (< 3 projetos — o §2 declara que abaixo disso não se distingue 'não detecta' de 'não foi exercitada'):

- RES Resilience — ativou em 1 projeto(s)
- UX UI/UX — ativou em 1 projeto(s)
- MIG Migration / Coexistence — ativou em 1 projeto(s)
- SUS Sustainability / Proportionality — ativou em 1 projeto(s)
- ETI Ethical / Human Impact — ativou em 0 projeto(s)
- PRO Process / Workflow — ativou em 1 projeto(s)
- GOV Governance / Accountability — ativou em 1 projeto(s)
- OBS Observability / Operability — ativou em 1 projeto(s)
- CTR Control Engineering — ativou em 1 projeto(s)
- JOG Game Theory — ativou em 0 projeto(s)
- LIN Linguistics / Grammar — ativou em 1 projeto(s)
- MEC Mechanical Engineering — ativou em 1 projeto(s)

