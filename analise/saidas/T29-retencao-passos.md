# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T29-retencao)  
Achados: 109  ·  Defeitos distintos (clusters): 96  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T29-retencao | bitstream | DES | PRF-02 |
| T29-retencao | block | ARQ | ARQ-05 |
| T29-retencao | block | PRE | ASM-03 |
| T29-retencao | block | MEC | MEC-04 |
| T29-retencao | cli | ARQ | ARQ-01 |
| T29-retencao | cli | PRE | ASM-06 |
| T29-retencao | cli | IMP | IMP-05 |
| T29-retencao | cli | OBS | OBS-02, OBS-03, OBS-04 |
| T29-retencao | cli | PRO | PRC-02 |
| T29-retencao | cli | RES | RES-05 |
| T29-retencao | cli | SEG | SEC-04 |
| T29-retencao | cli | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-08 |
| T29-retencao | dataset-gen | PRE | ASM-05 |
| T29-retencao | dataset-gen | MEC | MEC-03 |
| T29-retencao | dataset-gen | SEG | SEC-05 |
| T29-retencao | downsampler | PRE | ASM-04 |
| T29-retencao | downsampler | IMP | IMP-04 |
| T29-retencao | downsampler | CIE | SCI-01, SCI-04 |
| T29-retencao | downsampler | SUS | SUS-03 |
| T29-retencao | gorilla-codec | ARQ | ARQ-08 |
| T29-retencao | gorilla-codec | MEC | MEC-02, MEC-06 |
| T29-retencao | gorilla-codec | CIE | SCI-05 |
| T29-retencao | journal | ARQ | ARQ-09 |
| T29-retencao | journal | PRE | ASM-09 |
| T29-retencao | journal | GOV | GOV-04 |
| T29-retencao | journal | IMP | IMP-08 |
| T29-retencao | journal | LIN | LIN-09 |
| T29-retencao | journal | DES | PRF-05 |
| T29-retencao | journal | RES | RES-07 |
| T29-retencao | journal | SEG | SEC-06 |
| T29-retencao | journal | SUS | SUS-04 |
| T29-retencao | migrator | ARQ | ARQ-04 |
| T29-retencao | migrator | GOV | GOV-03 |
| T29-retencao | migrator | MIG | MIG-01, MIG-02, MIG-03 |
| T29-retencao | migrator | DES | PRF-03 |
| T29-retencao | retention | ARQ | ARQ-02 |
| T29-retencao | retention | PRE | ASM-02, ASM-10 |
| T29-retencao | retention | CTR | CTL-01, CTL-02, CTL-03, CTL-04, CTL-05 |
| T29-retencao | retention | GOV | GOV-01 |
| T29-retencao | retention | IMP | IMP-03 |
| T29-retencao | retention | LIN | LIN-06 |
| T29-retencao | retention | PRO | PRC-01, PRC-03, PRC-05 |
| T29-retencao | retention | CIE | SCI-03 |
| T29-retencao | retention | SUS | SUS-01 |
| T29-retencao | series | PRE | ASM-11 |
| T29-retencao | series | MEC | MEC-05 |
| T29-retencao | series | MIG | MIG-05 |
| T29-retencao | store-f1 | ARQ | ARQ-03 |
| T29-retencao | store-f1 | PRE | ASM-01, ASM-08 |
| T29-retencao | store-f1 | IMP | IMP-01, IMP-06 |
| T29-retencao | store-f1 | MEC | MEC-01 |
| T29-retencao | store-f1 | RES | RES-03 |
| T29-retencao | store-f1 | CIE | SCI-02 |
| T29-retencao | store-f1 | SEG | SEC-01, SEC-02 |
| T29-retencao | store-f1 | SUS | SUS-02 |
| T29-retencao | store-f2 | IMP | IMP-02 |
| T29-retencao | store-f2 | OBS | OBS-01, OBS-05 |
| T29-retencao | store-f2 | DES | PRF-01, PRF-04 |
| T29-retencao | store-f2 | RES | RES-01, RES-02, RES-04 |
| T29-retencao | store-f2 | SEG | SEC-03, SEC-07 |
| T29-retencao | store-f2 | SUS | SUS-05 |
| T29-retencao | store-port | ARQ | ARQ-06 |
| T29-retencao | store-port | PRE | ASM-07 |
| T29-retencao | store-port | GOV | GOV-02 |
| T29-retencao | store-port | LIN | LIN-01, LIN-02, LIN-03, LIN-04, LIN-05, LIN-07, LIN-08 |
| T29-retencao | store-port | REG | REG-01, REG-02 |
| T29-retencao | usecases | ARQ | ARQ-07 |
| T29-retencao | usecases | GOV | GOV-05 |
| T29-retencao | usecases | IMP | IMP-07 |
| T29-retencao | usecases | MIG | MIG-04 |
| T29-retencao | usecases | OBS | OBS-06 |
| T29-retencao | usecases | PRO | PRC-04 |
| T29-retencao | usecases | REG | REG-03 |
| T29-retencao | usecases | RES | RES-06 |
| T29-retencao | usecases | UX | UX-07 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 11 | 8 | 1 |
| ARQ Architectural | univ | 1 | 9 | 9 | 1 |
| IMP Implementability | univ | 1 | 8 | 7 | 1 |
| CIE Scientific | univ | 1 | 5 | 5 | 1 |
| SEG Security | univ | 1 | 7 | 6 | 1 |
| DES Performance | univ | 1 | 5 | 3 | 1 |
| REG Regulatory | univ | 1 | 3 | 3 | 1 |
| RES Resilience | cond | 1 | 7 | 2 | 1 |
| UX UI/UX | cond | 1 | 8 | 8 | 1 |
| MIG Migration / Coexistence | cond | 1 | 5 | 4 | 1 |
| SUS Sustainability / Proportionality | cond | 1 | 5 | 3 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 5 | 1 | 1 |
| GOV Governance / Accountability | cond | 1 | 5 | 5 | 1 |
| OBS Observability / Operability | cond | 1 | 6 | 5 | 1 |
| CTR Control Engineering | cond | 1 | 5 | 4 | 1 |
| JOG Game Theory | cond | 0 | 0 | 0 | 0 |
| LIN Linguistics / Grammar | cond | 1 | 9 | 8 | 1 |
| MEC Mechanical Engineering | cond | 1 | 6 | 4 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| PRO Process / Workflow | 5 | 4 | 80% | faltam 1 defeito(s) |
| RES Resilience | 6 | 4 | 67% | faltam 2 defeito(s) |
| DES Performance | 5 | 2 | 40% | faltam 3 defeito(s) |
| SUS Sustainability / Proportionality | 5 | 2 | 40% | faltam 3 defeito(s) |
| MEC Mechanical Engineering | 6 | 2 | 33% | faltam 4 defeito(s) |
| PRE Assumptions | 11 | 3 | 27% | faltam 8 defeito(s) |
| MIG Migration / Coexistence | 5 | 1 | 20% | faltam 4 defeito(s) |
| CTR Control Engineering | 5 | 1 | 20% | faltam 4 defeito(s) |
| OBS Observability / Operability | 6 | 1 | 17% | faltam 5 defeito(s) |
| IMP Implementability | 8 | 1 | 12% | faltam 7 defeito(s) |
| LIN Linguistics / Grammar | 9 | 1 | 11% | faltam 8 defeito(s) |
| ARQ Architectural | 9 | 0 | 0% | faltam 9 defeito(s) |
| CIE Scientific | 5 | 0 | 0% | faltam 5 defeito(s) |
| SEG Security | 6 | 0 | 0% | faltam 6 defeito(s) |
| REG Regulatory | 3 | 0 | 0% | faltam 3 defeito(s) |
| UX UI/UX | 8 | 0 | 0% | faltam 8 defeito(s) |
| GOV Governance / Accountability | 5 | 0 | 0% | faltam 5 defeito(s) |

Sobreposição média: **21%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| ARQ Architectural | 9 | 8% | 9 | 9% |
| PRE Assumptions | 11 | 10% | 8 | 8% |
| UX UI/UX | 8 | 7% | 8 | 8% |
| LIN Linguistics / Grammar | 9 | 8% | 8 | 8% |
| IMP Implementability | 8 | 7% | 7 | 7% |
| SEG Security | 7 | 6% | 6 | 6% |
| CIE Scientific | 5 | 5% | 5 | 5% |
| GOV Governance / Accountability | 5 | 5% | 5 | 5% |
| OBS Observability / Operability | 6 | 6% | 5 | 5% |
| MIG Migration / Coexistence | 5 | 5% | 4 | 4% |
| CTR Control Engineering | 5 | 5% | 4 | 4% |
| MEC Mechanical Engineering | 6 | 6% | 4 | 4% |
| DES Performance | 5 | 5% | 3 | 3% |
| REG Regulatory | 3 | 3% | 3 | 3% |
| SUS Sustainability / Proportionality | 5 | 5% | 3 | 3% |
| RES Resilience | 7 | 6% | 2 | 2% |
| PRO Process / Workflow | 5 | 5% | 1 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| PRO × RES | 0.33 | 2 | 0.22 |  |
| CTR × PRO | 0.33 | 1 | 0.11 |  |
| DES × SUS | 0.29 | 1 | 0.11 |  |
| MEC × MIG | 0.14 | 1 | 0.10 |  |
| DES × RES | 0.29 | 1 | 0.10 |  |
| OBS × RES | 0.60 | 1 | 0.09 |  |
| PRE × PRO | 0.20 | 1 | 0.07 |  |
| PRE × SUS | 0.40 | 1 | 0.07 |  |
| PRE × MEC | 0.40 | 1 | 0.06 |  |
| IMP × LIN | 0.25 | 1 | 0.06 |  |
| ARQ × PRE | 0.50 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.11 | 0 | 0.00 |  |
| ARQ × GOV | 0.56 | 0 | 0.00 |  |
| ARQ × IMP | 0.45 | 0 | 0.00 |  |
| ARQ × LIN | 0.33 | 0 | 0.00 |  |
| ARQ × MEC | 0.27 | 0 | 0.00 |  |
| ARQ × MIG | 0.20 | 0 | 0.00 |  |
| ARQ × OBS | 0.20 | 0 | 0.00 |  |
| ARQ × DES | 0.18 | 0 | 0.00 |  |
| ARQ × PRO | 0.33 | 0 | 0.00 |  |
| ARQ × REG | 0.22 | 0 | 0.00 |  |
| ARQ × RES | 0.40 | 0 | 0.00 |  |
| ARQ × CIE | 0.30 | 0 | 0.00 |  |
| ARQ × SEG | 0.27 | 0 | 0.00 |  |
| ARQ × SUS | 0.27 | 0 | 0.00 |  |

*(111 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T29-retencao` · **block** existia numa versão anterior · 3 achado(s): ARQ-05, ASM-03, MEC-04
- `T29-retencao` · **migrator** existia numa versão anterior · 6 achado(s): ARQ-04, GOV-03, MIG-01, MIG-02, MIG-03, PRF-03

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

