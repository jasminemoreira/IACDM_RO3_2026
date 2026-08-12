# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T27-despesas)  
Achados: 95  ·  Defeitos distintos (clusters): 84  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T27-despesas | api-http | GOV | GOV-03 |
| T27-despesas | api-http | IMP | IMP-04 |
| T27-despesas | api-http | RES | RES-03 |
| T27-despesas | api-http | SEG | SEC-01, SEC-02, SEC-03, SEC-06, SEC-07 |
| T27-despesas | autoridade | ARQ | ARQ-01 |
| T27-despesas | autoridade | PRE | A-02 |
| T27-despesas | autoridade | LIN | LING-01 |
| T27-despesas | autoridade | REG | REG-03 |
| T27-despesas | autoridade | CIE | SCI-02, SCI-04 |
| T27-despesas | bandeja | ARQ | ARQ-02, ARQ-07 |
| T27-despesas | bandeja | PRE | A-06, A-08 |
| T27-despesas | bandeja | CTR | CTRL-01 |
| T27-despesas | bandeja | JOG | GT-03 |
| T27-despesas | bandeja | DES | PERF-01, PERF-04 |
| T27-despesas | bandeja | PRO | PROC-02 |
| T27-despesas | bandeja | SUS | SUS-02, SUS-03 |
| T27-despesas | casos-de-uso | ARQ | ARQ-03, ARQ-08 |
| T27-despesas | casos-de-uso | PRE | A-05, A-09 |
| T27-despesas | casos-de-uso | LIN | LING-07 |
| T27-despesas | casos-de-uso | DES | PERF-05 |
| T27-despesas | casos-de-uso | PRO | PROC-03, PROC-08 |
| T27-despesas | casos-de-uso | RES | RES-02 |
| T27-despesas | dominio-delegacao | ARQ | ARQ-05 |
| T27-despesas | dominio-delegacao | PRE | A-03, A-07 |
| T27-despesas | dominio-delegacao | JOG | GT-01, GT-05 |
| T27-despesas | dominio-delegacao | PRO | PROC-04, PROC-09 |
| T27-despesas | dominio-delegacao | CIE | SCI-03 |
| T27-despesas | dominio-despesa | PRO | PROC-05 |
| T27-despesas | matriz-doa | ARQ | ARQ-06 |
| T27-despesas | matriz-doa | PRE | A-01, A-10 |
| T27-despesas | matriz-doa | JOG | GT-02, GT-04 |
| T27-despesas | matriz-doa | IMP | IMP-01, IMP-06, IMP-08 |
| T27-despesas | matriz-doa | LIN | LING-02 |
| T27-despesas | matriz-doa | DES | PERF-03 |
| T27-despesas | matriz-doa | PRO | PROC-01, PROC-06, PROC-07 |
| T27-despesas | matriz-doa | REG | REG-04, REG-05 |
| T27-despesas | matriz-doa | CIE | SCI-01 |
| T27-despesas | portas-repositorio | LIN | LING-03 |
| T27-despesas | relogio | ARQ | ARQ-04 |
| T27-despesas | relogio | PRE | A-04 |
| T27-despesas | relogio | CTR | CTRL-02, CTRL-03, CTRL-04 |
| T27-despesas | relogio | IMP | IMP-09 |
| T27-despesas | relogio | LIN | LING-04 |
| T27-despesas | relogio | RES | RES-04 |
| T27-despesas | sqlite-adaptador | GOV | GOV-02, GOV-05 |
| T27-despesas | sqlite-adaptador | IMP | IMP-05 |
| T27-despesas | sqlite-adaptador | RES | RES-01 |
| T27-despesas | sqlite-adaptador | SEG | SEC-05 |
| T27-despesas | trilha | GOV | GOV-01, GOV-04, GOV-06 |
| T27-despesas | trilha | IMP | IMP-02 |
| T27-despesas | trilha | LIN | LING-05 |
| T27-despesas | trilha | DES | PERF-02 |
| T27-despesas | trilha | REG | REG-01, REG-02 |
| T27-despesas | trilha | RES | RES-05 |
| T27-despesas | trilha | SUS | SUS-01 |
| T27-despesas | ui-web | IMP | IMP-03, IMP-07 |
| T27-despesas | ui-web | LIN | LING-06 |
| T27-despesas | ui-web | SEG | SEC-04 |
| T27-despesas | ui-web | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 10 | 10 | 1 |
| ARQ Architectural | univ | 1 | 8 | 8 | 1 |
| IMP Implementability | univ | 1 | 9 | 6 | 1 |
| CIE Scientific | univ | 1 | 4 | 3 | 1 |
| SEG Security | univ | 1 | 7 | 7 | 1 |
| DES Performance | univ | 1 | 5 | 3 | 1 |
| REG Regulatory | univ | 1 | 5 | 3 | 1 |
| RES Resilience | cond | 1 | 5 | 5 | 1 |
| UX UI/UX | cond | 1 | 8 | 8 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 0 | 0 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 9 | 7 | 1 |
| GOV Governance / Accountability | cond | 1 | 6 | 5 | 1 |
| OBS Observability / Operability | cond | 0 | 0 | 0 | 0 |
| CTR Control Engineering | cond | 1 | 4 | 3 | 1 |
| JOG Game Theory | cond | 1 | 5 | 4 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 7 | 6 | 1 |
| MEC Mechanical Engineering | cond | 0 | 0 | 0 | 0 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 2 | 2 | 100% | faltam 0 defeito(s) |
| REG Regulatory | 5 | 2 | 40% | faltam 3 defeito(s) |
| IMP Implementability | 9 | 3 | 33% | faltam 6 defeito(s) |
| DES Performance | 4 | 1 | 25% | faltam 3 defeito(s) |
| CTR Control Engineering | 4 | 1 | 25% | faltam 3 defeito(s) |
| PRO Process / Workflow | 9 | 2 | 22% | faltam 7 defeito(s) |
| LIN Linguistics / Grammar | 7 | 1 | 14% | faltam 6 defeito(s) |
| PRE Assumptions | 10 | 0 | 0% | faltam 10 defeito(s) |
| ARQ Architectural | 8 | 0 | 0% | faltam 8 defeito(s) |
| CIE Scientific | 3 | 0 | 0% | faltam 3 defeito(s) |
| SEG Security | 7 | 0 | 0% | faltam 7 defeito(s) |
| RES Resilience | 5 | 0 | 0% | faltam 5 defeito(s) |
| UX UI/UX | 8 | 0 | 0% | faltam 8 defeito(s) |
| GOV Governance / Accountability | 5 | 0 | 0% | faltam 5 defeito(s) |
| JOG Game Theory | 4 | 0 | 0% | faltam 4 defeito(s) |

Sobreposição média: **13%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

**Candidatas a remoção por redundância** — produziram achados, nenhum exclusivo (todo defeito que viram, outra lente também viu):

- SUS Sustainability / Proportionality — 3 achado(s) em 1 projeto(s), 0 exclusivos

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 10 | 11% | 10 | 12% |
| ARQ Architectural | 8 | 8% | 8 | 10% |
| UX UI/UX | 8 | 8% | 8 | 10% |
| SEG Security | 7 | 7% | 7 | 8% |
| PRO Process / Workflow | 9 | 9% | 7 | 8% |
| IMP Implementability | 9 | 9% | 6 | 7% |
| LIN Linguistics / Grammar | 7 | 7% | 6 | 7% |
| RES Resilience | 5 | 5% | 5 | 6% |
| GOV Governance / Accountability | 6 | 6% | 5 | 6% |
| JOG Game Theory | 5 | 5% | 4 | 5% |
| CIE Scientific | 4 | 4% | 3 | 4% |
| DES Performance | 5 | 5% | 3 | 4% |
| REG Regulatory | 5 | 5% | 3 | 4% |
| CTR Control Engineering | 4 | 4% | 3 | 4% |
| SUS Sustainability / Proportionality | 3 | 3% | 0 | 0% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.50 | 1 | 0.20 |  |
| REG × SUS | 0.25 | 1 | 0.17 |  |
| CTR × PRO | 0.17 | 1 | 0.08 |  |
| IMP × REG | 0.29 | 1 | 0.08 |  |
| IMP × LIN | 0.44 | 1 | 0.07 |  |
| IMP × PRO | 0.10 | 1 | 0.06 |  |
| ARQ × PRE | 1.00 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.33 | 0 | 0.00 |  |
| ARQ × JOG | 0.50 | 0 | 0.00 |  |
| ARQ × GOV | 0.00 | 0 | 0.00 |  |
| ARQ × IMP | 0.20 | 0 | 0.00 |  |
| ARQ × LIN | 0.44 | 0 | 0.00 |  |
| ARQ × DES | 0.43 | 0 | 0.00 |  |
| ARQ × PRO | 0.57 | 0 | 0.00 |  |
| ARQ × REG | 0.29 | 0 | 0.00 |  |
| ARQ × RES | 0.22 | 0 | 0.00 |  |
| ARQ × CIE | 0.50 | 0 | 0.00 |  |
| ARQ × SEG | 0.00 | 0 | 0.00 |  |
| ARQ × SUS | 0.14 | 0 | 0.00 |  |
| ARQ × UX | 0.00 | 0 | 0.00 |  |
| PRE × CTR | 0.33 | 0 | 0.00 |  |
| PRE × JOG | 0.50 | 0 | 0.00 |  |
| PRE × GOV | 0.00 | 0 | 0.00 |  |
| PRE × IMP | 0.20 | 0 | 0.00 |  |
| PRE × LIN | 0.44 | 0 | 0.00 |  |

*(80 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

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
- MEC Mechanical Engineering — ativou em 0 projeto(s)

