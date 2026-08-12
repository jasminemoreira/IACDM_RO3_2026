# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T26-extratos)  
Achados: 112  ·  Defeitos distintos (clusters): 108  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T26-extratos | audit-log | GOV | GOV-06 |
| T26-extratos | audit-log | IMP | IMP-08 |
| T26-extratos | audit-log | MIG | MIG-02 |
| T26-extratos | audit-log | DES | PRF-07 |
| T26-extratos | audit-log | REG | REG-04 |
| T26-extratos | audit-log | RES | RES-06 |
| T26-extratos | audit-log | SEG | SEC-07 |
| T26-extratos | audit-log | SUS | SUS-04 |
| T26-extratos | canonicalizer | ARQ | ARC-06 |
| T26-extratos | canonicalizer | PRE | ASM-02 |
| T26-extratos | canonicalizer | LIN | LIN-04 |
| T26-extratos | canonicalizer | DES | PRF-05 |
| T26-extratos | cli | ARQ | ARC-01 |
| T26-extratos | cli | OBS | OBS-01, OBS-03 |
| T26-extratos | cli | PRO | PRC-03, PRC-04 |
| T26-extratos | cli | RES | RES-05 |
| T26-extratos | cli | SEG | SEC-04 |
| T26-extratos | cli | UX | UX-02, UX-05, UX-07 |
| T26-extratos | csv-adapter | PRE | ASM-07 |
| T26-extratos | csv-adapter | IMP | IMP-03 |
| T26-extratos | csv-adapter | LIN | LIN-01, LIN-08 |
| T26-extratos | csv-adapter | MEC | MEC-02 |
| T26-extratos | csv-adapter | RES | RES-03 |
| T26-extratos | dedup-engine | PRE | ASM-03 |
| T26-extratos | dedup-engine | CTR | CTL-01, CTL-03 |
| T26-extratos | dedup-engine | GOV | GOV-02 |
| T26-extratos | dedup-engine | DES | PRF-02 |
| T26-extratos | dedup-engine | PRO | PRC-07 |
| T26-extratos | domain-model | PRE | ASM-01, ASM-10, ASM-11 |
| T26-extratos | domain-model | IMP | IMP-06 |
| T26-extratos | domain-model | LIN | LIN-02, LIN-05, LIN-06 |
| T26-extratos | domain-model | PRO | PRC-06 |
| T26-extratos | fixture-generator | ARQ | ARC-03, ARC-08 |
| T26-extratos | fixture-generator | PRE | ASM-08 |
| T26-extratos | fixture-generator | IMP | IMP-05 |
| T26-extratos | fixture-generator | SEG | SEC-05 |
| T26-extratos | fixture-generator | SUS | SUS-03 |
| T26-extratos | matcher | ARQ | ARC-02 |
| T26-extratos | matcher | PRE | ASM-12 |
| T26-extratos | matcher | CTR | CTL-02, CTL-04 |
| T26-extratos | matcher | IMP | IMP-02, IMP-07 |
| T26-extratos | matcher | LIN | LIN-03 |
| T26-extratos | matcher | MEC | MEC-04, MEC-05 |
| T26-extratos | matcher | OBS | OBS-02, OBS-05 |
| T26-extratos | matcher | DES | PRF-01, PRF-06 |
| T26-extratos | matcher | CIE | SCI-01, SCI-02, SCI-05, SCI-06 |
| T26-extratos | matcher | SUS | SUS-02 |
| T26-extratos | ofx-adapter | PRE | ASM-05 |
| T26-extratos | ofx-adapter | IMP | IMP-10 |
| T26-extratos | ofx-adapter | MEC | MEC-01 |
| T26-extratos | ofx-adapter | RES | RES-02 |
| T26-extratos | ofx-adapter | SEG | SEC-02 |
| T26-extratos | reconcile-engine | PRE | ASM-06 |
| T26-extratos | reconcile-engine | IMP | IMP-01, IMP-09 |
| T26-extratos | reconcile-engine | DES | PRF-04 |
| T26-extratos | reconcile-engine | PRO | PRC-01 |
| T26-extratos | reconcile-engine | CIE | SCI-03 |
| T26-extratos | reporter | ARQ | ARC-04 |
| T26-extratos | reporter | GOV | GOV-04 |
| T26-extratos | reporter | REG | REG-03 |
| T26-extratos | reporter | CIE | SCI-04, SCI-07 |
| T26-extratos | reporter | SEG | SEC-01 |
| T26-extratos | reporter | UX | UX-04 |
| T26-extratos | repository | PRE | ASM-04 |
| T26-extratos | repository | GOV | GOV-03 |
| T26-extratos | repository | IMP | IMP-04 |
| T26-extratos | repository | MEC | MEC-03 |
| T26-extratos | repository | OBS | OBS-04 |
| T26-extratos | repository | DES | PRF-03 |
| T26-extratos | repository | REG | REG-01, REG-02 |
| T26-extratos | repository | RES | RES-01, RES-04 |
| T26-extratos | repository | SEG | SEC-03, SEC-06 |
| T26-extratos | repository | SUS | SUS-01 |
| T26-extratos | review-queue | ARQ | ARC-05 |
| T26-extratos | review-queue | GOV | GOV-01, GOV-05 |
| T26-extratos | review-queue | PRO | PRC-02, PRC-05 |
| T26-extratos | review-queue | UX | UX-01, UX-03, UX-06 |
| T26-extratos | store | ARQ | ARC-07 |
| T26-extratos | store | PRE | ASM-09 |
| T26-extratos | store | LIN | LIN-07 |
| T26-extratos | store | MIG | MIG-01, MIG-03 |
| T26-extratos | store | RES | RES-07 |
| T26-extratos | store | SEG | SEC-08 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 12 | 12 | 1 |
| ARQ Architectural | univ | 1 | 8 | 8 | 1 |
| IMP Implementability | univ | 1 | 10 | 9 | 1 |
| CIE Scientific | univ | 1 | 7 | 6 | 1 |
| SEG Security | univ | 1 | 8 | 8 | 1 |
| DES Performance | univ | 1 | 7 | 7 | 1 |
| REG Regulatory | univ | 1 | 4 | 3 | 1 |
| RES Resilience | cond | 1 | 7 | 7 | 1 |
| UX UI/UX | cond | 1 | 7 | 7 | 1 |
| MIG Migration / Coexistence | cond | 1 | 3 | 3 | 1 |
| SUS Sustainability / Proportionality | cond | 1 | 4 | 4 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 7 | 7 | 1 |
| GOV Governance / Accountability | cond | 1 | 6 | 5 | 1 |
| OBS Observability / Operability | cond | 1 | 5 | 5 | 1 |
| CTR Control Engineering | cond | 1 | 4 | 3 | 1 |
| JOG Game Theory | cond | 0 | 0 | 0 | 0 |
| LIN Linguistics / Grammar | cond | 1 | 8 | 8 | 1 |
| MEC Mechanical Engineering | cond | 1 | 5 | 4 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| REG Regulatory | 4 | 1 | 25% | faltam 3 defeito(s) |
| CTR Control Engineering | 4 | 1 | 25% | faltam 3 defeito(s) |
| MEC Mechanical Engineering | 5 | 1 | 20% | faltam 4 defeito(s) |
| GOV Governance / Accountability | 6 | 1 | 17% | faltam 5 defeito(s) |
| CIE Scientific | 7 | 1 | 14% | faltam 6 defeito(s) |
| IMP Implementability | 10 | 1 | 10% | faltam 9 defeito(s) |
| PRE Assumptions | 12 | 0 | 0% | faltam 12 defeito(s) |
| ARQ Architectural | 8 | 0 | 0% | faltam 8 defeito(s) |
| SEG Security | 8 | 0 | 0% | faltam 8 defeito(s) |
| DES Performance | 7 | 0 | 0% | faltam 7 defeito(s) |
| RES Resilience | 7 | 0 | 0% | faltam 7 defeito(s) |
| UX UI/UX | 7 | 0 | 0% | faltam 7 defeito(s) |
| SUS Sustainability / Proportionality | 4 | 0 | 0% | faltam 4 defeito(s) |
| PRO Process / Workflow | 7 | 0 | 0% | faltam 7 defeito(s) |
| OBS Observability / Operability | 5 | 0 | 0% | faltam 5 defeito(s) |
| LIN Linguistics / Grammar | 8 | 0 | 0% | faltam 8 defeito(s) |
| MIG Migration / Coexistence | 3 | 0 | 0% | faltam 3 defeito(s) |

Sobreposição média: **5%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 12 | 11% | 12 | 11% |
| IMP Implementability | 10 | 9% | 9 | 8% |
| ARQ Architectural | 8 | 7% | 8 | 7% |
| SEG Security | 8 | 7% | 8 | 7% |
| LIN Linguistics / Grammar | 8 | 7% | 8 | 7% |
| DES Performance | 7 | 6% | 7 | 6% |
| RES Resilience | 7 | 6% | 7 | 6% |
| UX UI/UX | 7 | 6% | 7 | 6% |
| PRO Process / Workflow | 7 | 6% | 7 | 6% |
| CIE Scientific | 7 | 6% | 6 | 6% |
| GOV Governance / Accountability | 6 | 5% | 5 | 5% |
| OBS Observability / Operability | 5 | 4% | 5 | 5% |
| SUS Sustainability / Proportionality | 4 | 4% | 4 | 4% |
| MEC Mechanical Engineering | 5 | 4% | 4 | 4% |
| REG Regulatory | 4 | 4% | 3 | 3% |
| MIG Migration / Coexistence | 3 | 3% | 3 | 3% |
| CTR Control Engineering | 4 | 4% | 3 | 3% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| CTR × REG | 0.00 | 1 | 0.14 |  |
| CTR × MEC | 0.20 | 1 | 0.12 |  |
| MEC × REG | 0.17 | 1 | 0.12 |  |
| CTR × GOV | 0.17 | 1 | 0.11 |  |
| GOV × REG | 0.60 | 1 | 0.11 |  |
| GOV × MEC | 0.12 | 1 | 0.10 |  |
| IMP × CIE | 0.22 | 1 | 0.06 |  |
| ARQ × PRE | 0.31 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.12 | 0 | 0.00 |  |
| ARQ × GOV | 0.20 | 0 | 0.00 |  |
| ARQ × IMP | 0.15 | 0 | 0.00 |  |
| ARQ × LIN | 0.33 | 0 | 0.00 |  |
| ARQ × MEC | 0.10 | 0 | 0.00 |  |
| ARQ × MIG | 0.12 | 0 | 0.00 |  |
| ARQ × OBS | 0.25 | 0 | 0.00 |  |
| ARQ × DES | 0.18 | 0 | 0.00 |  |
| ARQ × PRO | 0.20 | 0 | 0.00 |  |
| ARQ × REG | 0.11 | 0 | 0.00 |  |
| ARQ × RES | 0.18 | 0 | 0.00 |  |
| ARQ × CIE | 0.25 | 0 | 0.00 |  |
| ARQ × SEG | 0.40 | 0 | 0.00 |  |
| ARQ × SUS | 0.22 | 0 | 0.00 |  |
| ARQ × UX | 0.43 | 0 | 0.00 |  |
| PRE × CTR | 0.20 | 0 | 0.00 |  |
| PRE × GOV | 0.15 | 0 | 0.00 |  |

*(111 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T26-extratos` · **canonicalizer** existia numa versão anterior · 4 achado(s): ARC-06, ASM-02, LIN-04, PRF-05
- `T26-extratos` · **repository** existia numa versão anterior · 13 achado(s): ASM-04, GOV-03, IMP-04, MEC-03, OBS-04, PRF-03, REG-01, REG-02, RES-01, RES-04, SEC-03, SEC-06, SUS-01

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

