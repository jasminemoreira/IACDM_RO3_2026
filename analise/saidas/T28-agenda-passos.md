# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T28-agenda)  
Achados: 105  ·  Defeitos distintos (clusters): 102  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T28-agenda | canonical-event | PRE | ASS-03 |
| T28-agenda | canonical-event | LIN | LIN-04, LIN-06 |
| T28-agenda | canonical-event | REG | REG-01 |
| T28-agenda | cli | ARQ | ARC-05 |
| T28-agenda | cli | OBS | OBS-02 |
| T28-agenda | cli | SEG | SEC-03, SEC-07 |
| T28-agenda | cli | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08 |
| T28-agenda | conflict-queue | ARQ | ARC-01, ARC-08 |
| T28-agenda | conflict-queue | GOV | GOV-03 |
| T28-agenda | conflict-queue | IMP | IMP-08 |
| T28-agenda | conflict-queue | PRO | PRO-01, PRO-03, PRO-05 |
| T28-agenda | normalizer | ARQ | ARC-03 |
| T28-agenda | normalizer | PRE | ASS-04, ASS-07 |
| T28-agenda | normalizer | CTR | CTL-03, CTL-04 |
| T28-agenda | normalizer | IMP | IMP-06 |
| T28-agenda | normalizer | MEC | MEC-02, MEC-04, MEC-05 |
| T28-agenda | normalizer | DES | PER-04, PER-05 |
| T28-agenda | normalizer | REG | REG-02, REG-04 |
| T28-agenda | normalizer | CIE | SCI-04, SCI-05 |
| T28-agenda | normalizer | SEG | SEC-01 |
| T28-agenda | overlap-detector | ARQ | ARC-04 |
| T28-agenda | overlap-detector | CIE | SCI-02 |
| T28-agenda | policies | PRE | ASS-05, ASS-12 |
| T28-agenda | policies | IMP | IMP-02 |
| T28-agenda | policies | PRO | PRO-04 |
| T28-agenda | policies | REG | REG-03 |
| T28-agenda | policies | CIE | SCI-01 |
| T28-agenda | provider-alpha | SEG | SEC-04 |
| T28-agenda | provider-beta | IMP | IMP-01 |
| T28-agenda | provider-beta | LIN | LIN-01 |
| T28-agenda | provider-beta | RES | RES-02, RES-07 |
| T28-agenda | provider-beta | SEG | SEC-05 |
| T28-agenda | reconciler | ARQ | ARC-06 |
| T28-agenda | reconciler | PRE | ASS-02, ASS-09 |
| T28-agenda | reconciler | CIE | SCI-03 |
| T28-agenda | recurrence | IMP | IMP-03 |
| T28-agenda | recurrence | MEC | MEC-01 |
| T28-agenda | recurrence | DES | PER-02 |
| T28-agenda | recurrence | SUS | SUS-02 |
| T28-agenda | repository | ARQ | ARC-07 |
| T28-agenda | repository | PRE | ASS-06, ASS-08, ASS-10 |
| T28-agenda | repository | GOV | GOV-01, GOV-04, GOV-05 |
| T28-agenda | repository | IMP | IMP-05, IMP-07 |
| T28-agenda | repository | LIN | LIN-03, LIN-05, LIN-08 |
| T28-agenda | repository | MEC | MEC-03 |
| T28-agenda | repository | OBS | OBS-03 |
| T28-agenda | repository | DES | PER-03, PER-06 |
| T28-agenda | repository | RES | RES-04, RES-06 |
| T28-agenda | repository | SEG | SEC-02, SEC-06 |
| T28-agenda | repository | SUS | SUS-01, SUS-04 |
| T28-agenda | sync-engine | ARQ | ARC-02, ARC-09 |
| T28-agenda | sync-engine | PRE | ASS-01, ASS-11 |
| T28-agenda | sync-engine | CTR | CTL-01, CTL-02, CTL-05 |
| T28-agenda | sync-engine | GOV | GOV-02 |
| T28-agenda | sync-engine | IMP | IMP-04 |
| T28-agenda | sync-engine | LIN | LIN-02, LIN-07 |
| T28-agenda | sync-engine | OBS | OBS-01, OBS-04, OBS-05 |
| T28-agenda | sync-engine | DES | PER-01, PER-07 |
| T28-agenda | sync-engine | PRO | PRO-02, PRO-06 |
| T28-agenda | sync-engine | RES | RES-01, RES-03, RES-05 |
| T28-agenda | sync-engine | SUS | SUS-03 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 12 | 12 | 1 |
| ARQ Architectural | univ | 1 | 9 | 9 | 1 |
| IMP Implementability | univ | 1 | 8 | 7 | 1 |
| CIE Scientific | univ | 1 | 5 | 5 | 1 |
| SEG Security | univ | 1 | 7 | 5 | 1 |
| DES Performance | univ | 1 | 7 | 7 | 1 |
| REG Regulatory | univ | 1 | 4 | 4 | 1 |
| RES Resilience | cond | 1 | 7 | 6 | 1 |
| UX UI/UX | cond | 1 | 8 | 8 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 4 | 3 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 6 | 6 | 1 |
| GOV Governance / Accountability | cond | 1 | 5 | 5 | 1 |
| OBS Observability / Operability | cond | 1 | 5 | 5 | 1 |
| CTR Control Engineering | cond | 1 | 5 | 5 | 1 |
| JOG Game Theory | cond | 0 | 0 | 0 | 0 |
| LIN Linguistics / Grammar | cond | 1 | 8 | 8 | 1 |
| MEC Mechanical Engineering | cond | 1 | 5 | 5 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 4 | 1 | 25% | faltam 3 defeito(s) |
| SEG Security | 6 | 1 | 17% | faltam 5 defeito(s) |
| RES Resilience | 7 | 1 | 14% | faltam 6 defeito(s) |
| IMP Implementability | 8 | 1 | 12% | faltam 7 defeito(s) |
| PRE Assumptions | 12 | 0 | 0% | faltam 12 defeito(s) |
| ARQ Architectural | 9 | 0 | 0% | faltam 9 defeito(s) |
| CIE Scientific | 5 | 0 | 0% | faltam 5 defeito(s) |
| DES Performance | 7 | 0 | 0% | faltam 7 defeito(s) |
| REG Regulatory | 4 | 0 | 0% | faltam 4 defeito(s) |
| UX UI/UX | 8 | 0 | 0% | faltam 8 defeito(s) |
| PRO Process / Workflow | 6 | 0 | 0% | faltam 6 defeito(s) |
| GOV Governance / Accountability | 5 | 0 | 0% | faltam 5 defeito(s) |
| OBS Observability / Operability | 5 | 0 | 0% | faltam 5 defeito(s) |
| CTR Control Engineering | 5 | 0 | 0% | faltam 5 defeito(s) |
| LIN Linguistics / Grammar | 8 | 0 | 0% | faltam 8 defeito(s) |
| MEC Mechanical Engineering | 5 | 0 | 0% | faltam 5 defeito(s) |

Sobreposição média: **4%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 12 | 11% | 12 | 12% |
| ARQ Architectural | 9 | 9% | 9 | 9% |
| UX UI/UX | 8 | 8% | 8 | 8% |
| LIN Linguistics / Grammar | 8 | 8% | 8 | 8% |
| IMP Implementability | 8 | 8% | 7 | 7% |
| DES Performance | 7 | 7% | 7 | 7% |
| RES Resilience | 7 | 7% | 6 | 6% |
| PRO Process / Workflow | 6 | 6% | 6 | 6% |
| CIE Scientific | 5 | 5% | 5 | 5% |
| SEG Security | 7 | 7% | 5 | 5% |
| GOV Governance / Accountability | 5 | 5% | 5 | 5% |
| OBS Observability / Operability | 5 | 5% | 5 | 5% |
| CTR Control Engineering | 5 | 5% | 5 | 5% |
| MEC Mechanical Engineering | 5 | 5% | 5 | 5% |
| REG Regulatory | 4 | 4% | 4 | 4% |
| SUS Sustainability / Proportionality | 4 | 4% | 3 | 3% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| SEG × SUS | 0.14 | 1 | 0.11 |  |
| IMP × RES | 0.43 | 1 | 0.07 |  |
| ARQ × PRE | 0.44 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.29 | 0 | 0.00 |  |
| ARQ × GOV | 0.43 | 0 | 0.00 |  |
| ARQ × IMP | 0.40 | 0 | 0.00 |  |
| ARQ × LIN | 0.22 | 0 | 0.00 |  |
| ARQ × MEC | 0.25 | 0 | 0.00 |  |
| ARQ × OBS | 0.43 | 0 | 0.00 |  |
| ARQ × DES | 0.38 | 0 | 0.00 |  |
| ARQ × PRO | 0.25 | 0 | 0.00 |  |
| ARQ × REG | 0.11 | 0 | 0.00 |  |
| ARQ × RES | 0.25 | 0 | 0.00 |  |
| ARQ × CIE | 0.38 | 0 | 0.00 |  |
| ARQ × SEG | 0.33 | 0 | 0.00 |  |
| ARQ × SUS | 0.25 | 0 | 0.00 |  |
| ARQ × UX | 0.14 | 0 | 0.00 |  |
| PRE × CTR | 0.33 | 0 | 0.00 |  |
| PRE × GOV | 0.29 | 0 | 0.00 |  |
| PRE × IMP | 0.44 | 0 | 0.00 |  |
| PRE × LIN | 0.43 | 0 | 0.00 |  |
| PRE × MEC | 0.29 | 0 | 0.00 |  |
| PRE × OBS | 0.29 | 0 | 0.00 |  |
| PRE × DES | 0.43 | 0 | 0.00 |  |
| PRE × PRO | 0.29 | 0 | 0.00 |  |

*(95 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

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
- OBS Observability / Operability — ativou em 1 projeto(s)
- CTR Control Engineering — ativou em 1 projeto(s)
- JOG Game Theory — ativou em 0 projeto(s)
- LIN Linguistics / Grammar — ativou em 1 projeto(s)
- MEC Mechanical Engineering — ativou em 1 projeto(s)

