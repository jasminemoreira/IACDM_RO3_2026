# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T30-notifica)  
Achados: 96  ·  Defeitos distintos (clusters): 92  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T30-notifica | channel-email | IMP | IMP-04 |
| T30-notifica | channel-email | LIN | LIN-01 |
| T30-notifica | channel-email | MEC | MEC-02 |
| T30-notifica | channel-email | PRO | PRO-07 |
| T30-notifica | channel-email | REG | REG-01 |
| T30-notifica | channel-email | RES | RES-02 |
| T30-notifica | channel-webhook | PRE | ASS-06 |
| T30-notifica | channel-webhook | LIN | LIN-05 |
| T30-notifica | channel-webhook | RES | RES-03 |
| T30-notifica | channel-webhook | CIE | SCI-03 |
| T30-notifica | channel-webhook | SEG | SEC-03, SEC-10, SEC-11 |
| T30-notifica | cli | ARQ | ARC-03 |
| T30-notifica | cli | SEG | SEC-05 |
| T30-notifica | cli | UX | UX-01, UX-02, UX-06 |
| T30-notifica | delivery-policy | ARQ | ARC-06 |
| T30-notifica | delivery-policy | CTR | CTL-05 |
| T30-notifica | delivery-policy | LIN | LIN-06 |
| T30-notifica | delivery-policy | PRO | PRO-05 |
| T30-notifica | delivery-policy | CIE | SCI-05 |
| T30-notifica | delivery-worker | ARQ | ARC-02 |
| T30-notifica | delivery-worker | PRE | ASS-01 |
| T30-notifica | delivery-worker | CTR | CTL-01 |
| T30-notifica | delivery-worker | MEC | MEC-03 |
| T30-notifica | delivery-worker | OBS | OBS-01 |
| T30-notifica | delivery-worker | DES | PERF-01, PERF-05 |
| T30-notifica | delivery-worker | PRO | PRO-02 |
| T30-notifica | delivery-worker | RES | RES-01 |
| T30-notifica | delivery-worker | CIE | SCI-04 |
| T30-notifica | delivery-worker | SUS | SUS-02 |
| T30-notifica | http-api | ARQ | ARC-04 |
| T30-notifica | http-api | IMP | IMP-02, IMP-05 |
| T30-notifica | http-api | LIN | LIN-04 |
| T30-notifica | http-api | OBS | OBS-02 |
| T30-notifica | http-api | SEG | SEC-01, SEC-02, SEC-07, SEC-12 |
| T30-notifica | http-api | UX | UX-03 |
| T30-notifica | ingestion | PRE | ASS-02 |
| T30-notifica | ingestion | JOG | GAM-01, GAM-03 |
| T30-notifica | ingestion | GOV | GOV-01 |
| T30-notifica | ingestion | PRO | PRO-01 |
| T30-notifica | ingestion | SEG | SEC-06, SEC-08 |
| T30-notifica | outbox | PRE | ASS-07 |
| T30-notifica | outbox | LIN | LIN-03 |
| T30-notifica | outbox | OBS | OBS-04 |
| T30-notifica | outbox | DES | PERF-02 |
| T30-notifica | outbox | RES | RES-05, RES-06 |
| T30-notifica | preferences | ARQ | ARC-07 |
| T30-notifica | preferences | PRE | ASS-05 |
| T30-notifica | preferences | ETI | ETH-03 |
| T30-notifica | preferences | GOV | GOV-03, GOV-04 |
| T30-notifica | preferences | PRO | PRO-04 |
| T30-notifica | preferences | REG | REG-02, REG-04 |
| T30-notifica | preferences | UX | UX-04 |
| T30-notifica | quiet-hours | PRE | ASS-03, ASS-08 |
| T30-notifica | quiet-hours | CTR | CTL-03 |
| T30-notifica | quiet-hours | IMP | IMP-03 |
| T30-notifica | quiet-hours | CIE | SCI-02 |
| T30-notifica | rate-limiter | PRE | ASS-04 |
| T30-notifica | rate-limiter | CTR | CTL-02 |
| T30-notifica | rate-limiter | JOG | GAM-02, GAM-04 |
| T30-notifica | rate-limiter | DES | PERF-04 |
| T30-notifica | rate-limiter | CIE | SCI-01 |
| T30-notifica | store | ARQ | ARC-05, ARC-08 |
| T30-notifica | store | IMP | IMP-01 |
| T30-notifica | store | MEC | MEC-01, MEC-04 |
| T30-notifica | store | OBS | OBS-03 |
| T30-notifica | store | REG | REG-03 |
| T30-notifica | store | RES | RES-04 |
| T30-notifica | store | SEG | SEC-04, SEC-09 |
| T30-notifica | store | SUS | SUS-01, SUS-03 |
| T30-notifica | suppression | ARQ | ARC-01 |
| T30-notifica | suppression | ETI | ETH-01, ETH-02 |
| T30-notifica | suppression | GOV | GOV-02 |
| T30-notifica | suppression | LIN | LIN-02 |
| T30-notifica | suppression | DES | PERF-03 |
| T30-notifica | suppression | PRO | PRO-03 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 8 | 8 | 1 |
| ARQ Architectural | univ | 1 | 8 | 8 | 1 |
| IMP Implementability | univ | 1 | 5 | 5 | 1 |
| CIE Scientific | univ | 1 | 5 | 5 | 1 |
| SEG Security | univ | 1 | 12 | 12 | 1 |
| DES Performance | univ | 1 | 5 | 5 | 1 |
| REG Regulatory | univ | 1 | 4 | 3 | 1 |
| RES Resilience | cond | 1 | 6 | 5 | 1 |
| UX UI/UX | cond | 1 | 5 | 5 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 3 | 1 |
| ETI Ethical / Human Impact | cond | 1 | 3 | 1 | 1 |
| PRO Process / Workflow | cond | 1 | 6 | 6 | 1 |
| GOV Governance / Accountability | cond | 1 | 4 | 4 | 1 |
| OBS Observability / Operability | cond | 1 | 4 | 4 | 1 |
| CTR Control Engineering | cond | 1 | 4 | 4 | 1 |
| JOG Game Theory | cond | 1 | 4 | 2 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 6 | 5 | 1 |
| MEC Mechanical Engineering | cond | 1 | 4 | 4 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| ETI Ethical / Human Impact | 3 | 2 | 67% | faltam 1 defeito(s) |
| JOG Game Theory | 4 | 2 | 50% | faltam 2 defeito(s) |
| REG Regulatory | 4 | 1 | 25% | faltam 3 defeito(s) |
| RES Resilience | 6 | 1 | 17% | faltam 5 defeito(s) |
| LIN Linguistics / Grammar | 6 | 1 | 17% | faltam 5 defeito(s) |
| PRE Assumptions | 8 | 0 | 0% | faltam 8 defeito(s) |
| ARQ Architectural | 8 | 0 | 0% | faltam 8 defeito(s) |
| IMP Implementability | 5 | 0 | 0% | faltam 5 defeito(s) |
| CIE Scientific | 5 | 0 | 0% | faltam 5 defeito(s) |
| SEG Security | 12 | 0 | 0% | faltam 12 defeito(s) |
| DES Performance | 5 | 0 | 0% | faltam 5 defeito(s) |
| UX UI/UX | 5 | 0 | 0% | faltam 5 defeito(s) |
| SUS Sustainability / Proportionality | 3 | 0 | 0% | faltam 3 defeito(s) |
| PRO Process / Workflow | 6 | 0 | 0% | faltam 6 defeito(s) |
| GOV Governance / Accountability | 4 | 0 | 0% | faltam 4 defeito(s) |
| OBS Observability / Operability | 4 | 0 | 0% | faltam 4 defeito(s) |
| CTR Control Engineering | 4 | 0 | 0% | faltam 4 defeito(s) |
| MEC Mechanical Engineering | 4 | 0 | 0% | faltam 4 defeito(s) |

Sobreposição média: **7%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| SEG Security | 12 | 12% | 12 | 13% |
| PRE Assumptions | 8 | 8% | 8 | 9% |
| ARQ Architectural | 8 | 8% | 8 | 9% |
| PRO Process / Workflow | 6 | 6% | 6 | 7% |
| IMP Implementability | 5 | 5% | 5 | 5% |
| CIE Scientific | 5 | 5% | 5 | 5% |
| DES Performance | 5 | 5% | 5 | 5% |
| RES Resilience | 6 | 6% | 5 | 5% |
| UX UI/UX | 5 | 5% | 5 | 5% |
| LIN Linguistics / Grammar | 6 | 6% | 5 | 5% |
| GOV Governance / Accountability | 4 | 4% | 4 | 4% |
| OBS Observability / Operability | 4 | 4% | 4 | 4% |
| CTR Control Engineering | 4 | 4% | 4 | 4% |
| MEC Mechanical Engineering | 4 | 4% | 4 | 4% |
| REG Regulatory | 4 | 4% | 3 | 3% |
| SUS Sustainability / Proportionality | 3 | 3% | 3 | 3% |
| JOG Game Theory | 4 | 4% | 2 | 2% |
| ETI Ethical / Human Impact | 3 | 3% | 1 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| ETI × JOG | 0.00 | 2 | 0.40 |  |
| ETI × REG | 0.25 | 1 | 0.17 |  |
| JOG × REG | 0.00 | 1 | 0.14 |  |
| LIN × RES | 0.38 | 1 | 0.09 |  |
| ARQ × PRE | 0.17 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.22 | 0 | 0.00 |  |
| ARQ × ETI | 0.29 | 0 | 0.00 |  |
| ARQ × JOG | 0.00 | 0 | 0.00 |  |
| ARQ × GOV | 0.25 | 0 | 0.00 |  |
| ARQ × IMP | 0.22 | 0 | 0.00 |  |
| ARQ × LIN | 0.30 | 0 | 0.00 |  |
| ARQ × MEC | 0.25 | 0 | 0.00 |  |
| ARQ × OBS | 0.38 | 0 | 0.00 |  |
| ARQ × DES | 0.22 | 0 | 0.00 |  |
| ARQ × PRO | 0.44 | 0 | 0.00 |  |
| ARQ × REG | 0.25 | 0 | 0.00 |  |
| ARQ × RES | 0.20 | 0 | 0.00 |  |
| ARQ × CIE | 0.20 | 0 | 0.00 |  |
| ARQ × SEG | 0.33 | 0 | 0.00 |  |
| ARQ × SUS | 0.29 | 0 | 0.00 |  |
| ARQ × UX | 0.43 | 0 | 0.00 |  |
| PRE × CTR | 0.38 | 0 | 0.00 |  |
| PRE × ETI | 0.12 | 0 | 0.00 |  |
| PRE × JOG | 0.29 | 0 | 0.00 |  |
| PRE × GOV | 0.25 | 0 | 0.00 |  |

*(128 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T30-notifica` · **suppression** existia numa versão anterior · 7 achado(s): ARC-01, ETH-01, ETH-02, GOV-02, LIN-02, PERF-03, PRO-03

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

