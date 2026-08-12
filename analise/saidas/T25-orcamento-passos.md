# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T25-orcamento)  
Achados: 68  ·  Defeitos distintos (clusters): 63  ·  Módulos: 10


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T25-orcamento | escrow | PRE | A-01 |
| T25-orcamento | escrow | CTR | CTL-01, CTL-03 |
| T25-orcamento | escrow | ETI | ETI-01, ETI-03 |
| T25-orcamento | escrow | JOG | GAM-01, GAM-02, GAM-03 |
| T25-orcamento | escrow | GOV | GOV-03 |
| T25-orcamento | escrow | IMP | IMP-04 |
| T25-orcamento | escrow | LIN | LIN-02 |
| T25-orcamento | escrow | OBS | OBS-03 |
| T25-orcamento | escrow | DES | PERF-01 |
| T25-orcamento | escrow | PRO | PRO-01, PRO-03 |
| T25-orcamento | escrow | RES | RES-04, RES-05 |
| T25-orcamento | escrow | CIE | CIE-02, CIE-04 |
| T25-orcamento | gateway-http | ARQ | ARQ-01 |
| T25-orcamento | gateway-http | IMP | IMP-01 |
| T25-orcamento | gateway-http | LIN | LIN-01, LIN-03 |
| T25-orcamento | gateway-http | OBS | OBS-01 |
| T25-orcamento | gateway-http | RES | RES-02, RES-03 |
| T25-orcamento | gateway-http | SEG | SEG-02, SEG-06 |
| T25-orcamento | gateway-http | UX | UX-02 |
| T25-orcamento | identidade | ARQ | ARQ-02 |
| T25-orcamento | identidade | PRO | PRO-02 |
| T25-orcamento | identidade | SEG | SEG-01, SEG-03 |
| T25-orcamento | janela | ARQ | ARQ-03 |
| T25-orcamento | janela | PRE | A-02, A-06 |
| T25-orcamento | painel-api | ARQ | ARQ-04, ARQ-05 |
| T25-orcamento | painel-api | GOV | GOV-01 |
| T25-orcamento | painel-api | DES | PERF-04 |
| T25-orcamento | painel-api | SEG | SEG-04, SEG-05 |
| T25-orcamento | painel-web | CTR | CTL-02 |
| T25-orcamento | painel-web | ETI | ETI-02 |
| T25-orcamento | painel-web | IMP | IMP-02 |
| T25-orcamento | painel-web | UX | UX-01, UX-03, UX-04 |
| T25-orcamento | persistencia | OBS | OBS-02 |
| T25-orcamento | persistencia | DES | PERF-02, PERF-03, PERF-05 |
| T25-orcamento | persistencia | REG | REG-01, REG-02 |
| T25-orcamento | persistencia | SUS | SUS-02, SUS-03 |
| T25-orcamento | precificador | PRE | A-04, A-05 |
| T25-orcamento | precificador | CIE | CIE-03 |
| T25-orcamento | precificador | SUS | SUS-01 |
| T25-orcamento | rate-card | GOV | GOV-02 |
| T25-orcamento | rate-card | MEC | MEC-01, MEC-03 |
| T25-orcamento | rate-card | CIE | CIE-01 |
| T25-orcamento | upstream | PRE | A-03 |
| T25-orcamento | upstream | IMP | IMP-03 |
| T25-orcamento | upstream | MEC | MEC-02 |
| T25-orcamento | upstream | RES | RES-01 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 6 | 5 | 1 |
| ARQ Architectural | univ | 1 | 5 | 5 | 1 |
| IMP Implementability | univ | 1 | 4 | 4 | 1 |
| CIE Scientific | univ | 1 | 4 | 4 | 1 |
| SEG Security | univ | 1 | 6 | 5 | 1 |
| DES Performance | univ | 1 | 5 | 3 | 1 |
| REG Regulatory | univ | 1 | 2 | 2 | 1 |
| RES Resilience | cond | 1 | 5 | 3 | 1 |
| UX UI/UX | cond | 1 | 4 | 4 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 2 | 1 |
| ETI Ethical / Human Impact | cond | 1 | 3 | 3 | 1 |
| PRO Process / Workflow | cond | 1 | 3 | 3 | 1 |
| GOV Governance / Accountability | cond | 1 | 3 | 2 | 1 |
| OBS Observability / Operability | cond | 1 | 3 | 3 | 1 |
| CTR Control Engineering | cond | 1 | 3 | 2 | 1 |
| JOG Game Theory | cond | 1 | 3 | 3 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 3 | 3 | 1 |
| MEC Mechanical Engineering | cond | 1 | 3 | 3 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| DES Performance | 5 | 2 | 40% | faltam 3 defeito(s) |
| GOV Governance / Accountability | 3 | 1 | 33% | faltam 2 defeito(s) |
| SUS Sustainability / Proportionality | 3 | 1 | 33% | faltam 2 defeito(s) |
| CTR Control Engineering | 3 | 1 | 33% | faltam 2 defeito(s) |
| RES Resilience | 4 | 1 | 25% | faltam 3 defeito(s) |
| PRE Assumptions | 6 | 1 | 17% | faltam 5 defeito(s) |
| SEG Security | 6 | 1 | 17% | faltam 5 defeito(s) |
| ARQ Architectural | 5 | 0 | 0% | faltam 5 defeito(s) |
| IMP Implementability | 4 | 0 | 0% | faltam 4 defeito(s) |
| CIE Scientific | 4 | 0 | 0% | faltam 4 defeito(s) |
| REG Regulatory | 2 | 0 | 0% | faltam 2 defeito(s) |
| UX UI/UX | 4 | 0 | 0% | faltam 4 defeito(s) |
| ETI Ethical / Human Impact | 3 | 0 | 0% | faltam 3 defeito(s) |
| PRO Process / Workflow | 3 | 0 | 0% | faltam 3 defeito(s) |
| OBS Observability / Operability | 3 | 0 | 0% | faltam 3 defeito(s) |
| JOG Game Theory | 3 | 0 | 0% | faltam 3 defeito(s) |
| LIN Linguistics / Grammar | 3 | 0 | 0% | faltam 3 defeito(s) |
| MEC Mechanical Engineering | 3 | 0 | 0% | faltam 3 defeito(s) |

Sobreposição média: **12%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 6 | 9% | 5 | 8% |
| ARQ Architectural | 5 | 7% | 5 | 8% |
| SEG Security | 6 | 9% | 5 | 8% |
| IMP Implementability | 4 | 6% | 4 | 6% |
| CIE Scientific | 4 | 6% | 4 | 6% |
| UX UI/UX | 4 | 6% | 4 | 6% |
| DES Performance | 5 | 7% | 3 | 5% |
| RES Resilience | 5 | 7% | 3 | 5% |
| ETI Ethical / Human Impact | 3 | 4% | 3 | 5% |
| PRO Process / Workflow | 3 | 4% | 3 | 5% |
| OBS Observability / Operability | 3 | 4% | 3 | 5% |
| JOG Game Theory | 3 | 4% | 3 | 5% |
| LIN Linguistics / Grammar | 3 | 4% | 3 | 5% |
| MEC Mechanical Engineering | 3 | 4% | 3 | 5% |
| REG Regulatory | 2 | 3% | 2 | 3% |
| SUS Sustainability / Proportionality | 3 | 4% | 2 | 3% |
| GOV Governance / Accountability | 3 | 4% | 2 | 3% |
| CTR Control Engineering | 3 | 4% | 2 | 3% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| CTR × RES | 0.25 | 1 | 0.17 |  |
| DES × SUS | 0.25 | 1 | 0.14 |  |
| GOV × SEG | 0.20 | 1 | 0.12 |  |
| PRE × DES | 0.17 | 1 | 0.10 |  |
| ARQ × PRE | 0.14 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.00 | 0 | 0.00 |  |
| ARQ × ETI | 0.00 | 0 | 0.00 |  |
| ARQ × JOG | 0.00 | 0 | 0.00 |  |
| ARQ × GOV | 0.17 | 0 | 0.00 |  |
| ARQ × IMP | 0.14 | 0 | 0.00 |  |
| ARQ × LIN | 0.20 | 0 | 0.00 |  |
| ARQ × MEC | 0.00 | 0 | 0.00 |  |
| ARQ × OBS | 0.17 | 0 | 0.00 |  |
| ARQ × DES | 0.17 | 0 | 0.00 |  |
| ARQ × PRO | 0.20 | 0 | 0.00 |  |
| ARQ × REG | 0.00 | 0 | 0.00 |  |
| ARQ × RES | 0.17 | 0 | 0.00 |  |
| ARQ × CIE | 0.00 | 0 | 0.00 |  |
| ARQ × SEG | 0.75 | 0 | 0.00 |  |
| ARQ × SUS | 0.00 | 0 | 0.00 |  |
| ARQ × UX | 0.20 | 0 | 0.00 |  |
| PRE × CTR | 0.20 | 0 | 0.00 |  |
| PRE × ETI | 0.20 | 0 | 0.00 |  |
| PRE × JOG | 0.25 | 0 | 0.00 |  |
| PRE × GOV | 0.17 | 0 | 0.00 |  |

*(128 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

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
- OBS Observability / Operability — ativou em 1 projeto(s)
- CTR Control Engineering — ativou em 1 projeto(s)
- JOG Game Theory — ativou em 1 projeto(s)
- LIN Linguistics / Grammar — ativou em 1 projeto(s)
- MEC Mechanical Engineering — ativou em 1 projeto(s)

