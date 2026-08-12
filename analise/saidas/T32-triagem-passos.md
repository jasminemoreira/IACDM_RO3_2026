# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T32-triagem)  
Achados: 78  ·  Defeitos distintos (clusters): 72  ·  Módulos: 12


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T32-triagem | api-http | ARQ | ARQ-08 |
| T32-triagem | api-http | SEG | SEG-03, SEG-05 |
| T32-triagem | autorizacao | LIN | LIN-03 |
| T32-triagem | autorizacao | SEG | SEG-01 |
| T32-triagem | casos-de-uso | ARQ | ARQ-01 |
| T32-triagem | casos-de-uso | IMP | IMP-01, IMP-04 |
| T32-triagem | casos-de-uso | SEG | SEG-04 |
| T32-triagem | chamado | ARQ | ARQ-05 |
| T32-triagem | chamado | PRE | PRE-04, PRE-05 |
| T32-triagem | chamado | ETI | ETI-01 |
| T32-triagem | chamado | JOG | JOG-01, JOG-03, JOG-04 |
| T32-triagem | chamado | PRO | PRO-01, PRO-04, PRO-05 |
| T32-triagem | configuracao | ARQ | ARQ-07 |
| T32-triagem | configuracao | PRE | PRE-01, PRE-06 |
| T32-triagem | configuracao | CTR | CTL-01, CTL-03 |
| T32-triagem | configuracao | GOV | GOV-02, GOV-04 |
| T32-triagem | configuracao | MEC | MEC-02 |
| T32-triagem | configuracao | OBS | OBS-01 |
| T32-triagem | configuracao | RES | RES-02, RES-03 |
| T32-triagem | configuracao | CIE | CIE-01, CIE-02, CIE-04 |
| T32-triagem | prioridade | CIE | CIE-03 |
| T32-triagem | recurso | ARQ | ARQ-06 |
| T32-triagem | recurso | PRE | PRE-02 |
| T32-triagem | recurso | ETI | ETI-02 |
| T32-triagem | recurso | JOG | JOG-02 |
| T32-triagem | recurso | LIN | LIN-04 |
| T32-triagem | recurso | PRO | PRO-06 |
| T32-triagem | recurso | REG | REG-01, REG-02, REG-04 |
| T32-triagem | relogio | PRE | PRE-03 |
| T32-triagem | relogio | LIN | LIN-01 |
| T32-triagem | repositorio | ARQ | ARQ-04 |
| T32-triagem | repositorio | MEC | MEC-01 |
| T32-triagem | repositorio | DES | PER-01, PER-03, PER-04 |
| T32-triagem | repositorio | RES | RES-01 |
| T32-triagem | repositorio | SUS | SUS-02 |
| T32-triagem | sla | CTR | CTL-02 |
| T32-triagem | sla | IMP | IMP-03 |
| T32-triagem | sla | MEC | MEC-03 |
| T32-triagem | trilha | ARQ | ARQ-03 |
| T32-triagem | trilha | PRE | PRE-07 |
| T32-triagem | trilha | ETI | ETI-03, ETI-04 |
| T32-triagem | trilha | GOV | GOV-01, GOV-03 |
| T32-triagem | trilha | LIN | LIN-02, LIN-05 |
| T32-triagem | trilha | DES | PER-02 |
| T32-triagem | trilha | REG | REG-03 |
| T32-triagem | trilha | SUS | SUS-01, SUS-03 |
| T32-triagem | ui-web | ARQ | ARQ-02 |
| T32-triagem | ui-web | IMP | IMP-02 |
| T32-triagem | ui-web | PRO | PRO-02, PRO-03 |
| T32-triagem | ui-web | SEG | SEG-02 |
| T32-triagem | ui-web | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 7 | 6 | 1 |
| ARQ Architectural | univ | 1 | 8 | 7 | 1 |
| IMP Implementability | univ | 1 | 4 | 3 | 1 |
| CIE Scientific | univ | 1 | 4 | 4 | 1 |
| SEG Security | univ | 1 | 5 | 4 | 1 |
| DES Performance | univ | 1 | 4 | 3 | 1 |
| REG Regulatory | univ | 1 | 4 | 3 | 1 |
| RES Resilience | cond | 1 | 3 | 3 | 1 |
| UX UI/UX | cond | 1 | 6 | 6 | 1 |
| MIG Migration / Coexistence | cond | 0 | 0 | 0 | 0 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 2 | 1 |
| ETI Ethical / Human Impact | cond | 1 | 4 | 3 | 1 |
| PRO Process / Workflow | cond | 1 | 6 | 4 | 1 |
| GOV Governance / Accountability | cond | 1 | 4 | 3 | 1 |
| OBS Observability / Operability | cond | 1 | 1 | 1 | 1 |
| CTR Control Engineering | cond | 1 | 3 | 3 | 1 |
| JOG Game Theory | cond | 1 | 4 | 4 | 1 |
| LIN Linguistics / Grammar | cond | 1 | 5 | 5 | 1 |
| MEC Mechanical Engineering | cond | 1 | 3 | 3 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 3 | 1 | 33% | faltam 2 defeito(s) |
| ETI Ethical / Human Impact | 4 | 1 | 25% | faltam 3 defeito(s) |
| IMP Implementability | 4 | 1 | 25% | faltam 3 defeito(s) |
| GOV Governance / Accountability | 4 | 1 | 25% | faltam 3 defeito(s) |
| DES Performance | 4 | 1 | 25% | faltam 3 defeito(s) |
| REG Regulatory | 4 | 1 | 25% | faltam 3 defeito(s) |
| SEG Security | 5 | 1 | 20% | faltam 4 defeito(s) |
| PRO Process / Workflow | 5 | 1 | 20% | faltam 4 defeito(s) |
| PRE Assumptions | 7 | 1 | 14% | faltam 6 defeito(s) |
| ARQ Architectural | 8 | 1 | 12% | faltam 7 defeito(s) |
| CIE Scientific | 4 | 0 | 0% | faltam 4 defeito(s) |
| RES Resilience | 3 | 0 | 0% | faltam 3 defeito(s) |
| UX UI/UX | 6 | 0 | 0% | faltam 6 defeito(s) |
| CTR Control Engineering | 3 | 0 | 0% | faltam 3 defeito(s) |
| JOG Game Theory | 4 | 0 | 0% | faltam 4 defeito(s) |
| LIN Linguistics / Grammar | 5 | 0 | 0% | faltam 5 defeito(s) |
| MEC Mechanical Engineering | 3 | 0 | 0% | faltam 3 defeito(s) |
| OBS Observability / Operability | 1 | 0 | 0% | faltam 1 defeito(s) |

Sobreposição média: **13%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| ARQ Architectural | 8 | 10% | 7 | 10% |
| PRE Assumptions | 7 | 9% | 6 | 8% |
| UX UI/UX | 6 | 8% | 6 | 8% |
| LIN Linguistics / Grammar | 5 | 6% | 5 | 7% |
| CIE Scientific | 4 | 5% | 4 | 6% |
| SEG Security | 5 | 6% | 4 | 6% |
| PRO Process / Workflow | 6 | 8% | 4 | 6% |
| JOG Game Theory | 4 | 5% | 4 | 6% |
| IMP Implementability | 4 | 5% | 3 | 4% |
| DES Performance | 4 | 5% | 3 | 4% |
| REG Regulatory | 4 | 5% | 3 | 4% |
| RES Resilience | 3 | 4% | 3 | 4% |
| ETI Ethical / Human Impact | 4 | 5% | 3 | 4% |
| GOV Governance / Accountability | 4 | 5% | 3 | 4% |
| CTR Control Engineering | 3 | 4% | 3 | 4% |
| MEC Mechanical Engineering | 3 | 4% | 3 | 4% |
| SUS Sustainability / Proportionality | 3 | 4% | 2 | 3% |
| OBS Observability / Operability | 1 | 1% | 1 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 1.00 | 1 | 0.17 |  |
| GOV × SEG | 0.00 | 1 | 0.12 |  |
| PRO × REG | 0.25 | 1 | 0.12 |  |
| PRE × ETI | 0.60 | 1 | 0.10 |  |
| ARQ × IMP | 0.22 | 1 | 0.09 |  |
| ARQ × PRE | 0.44 | 0 | 0.00 | sim (§4) |
| ARQ × CTR | 0.11 | 0 | 0.00 |  |
| ARQ × ETI | 0.38 | 0 | 0.00 |  |
| ARQ × JOG | 0.25 | 0 | 0.00 |  |
| ARQ × GOV | 0.25 | 0 | 0.00 |  |
| ARQ × LIN | 0.20 | 0 | 0.00 |  |
| ARQ × MEC | 0.22 | 0 | 0.00 |  |
| ARQ × OBS | 0.12 | 0 | 0.00 |  |
| ARQ × DES | 0.25 | 0 | 0.00 |  |
| ARQ × PRO | 0.38 | 0 | 0.00 |  |
| ARQ × REG | 0.25 | 0 | 0.00 |  |
| ARQ × RES | 0.25 | 0 | 0.00 |  |
| ARQ × CIE | 0.11 | 0 | 0.00 |  |
| ARQ × SEG | 0.33 | 0 | 0.00 |  |
| ARQ × SUS | 0.25 | 0 | 0.00 |  |
| ARQ × UX | 0.12 | 0 | 0.00 |  |
| PRE × CTR | 0.17 | 0 | 0.00 |  |
| PRE × JOG | 0.40 | 0 | 0.00 |  |
| PRE × GOV | 0.40 | 0 | 0.00 |  |
| PRE × IMP | 0.00 | 0 | 0.00 |  |

*(128 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T32-triagem` · **configuracao** existia numa versão anterior · 14 achado(s): ARQ-07, CIE-01, CIE-02, CIE-04, CTL-01, CTL-03, GOV-02, GOV-04, MEC-02, OBS-01, PRE-01, PRE-06, RES-02, RES-03
- `T32-triagem` · **recurso** existia numa versão anterior · 9 achado(s): ARQ-06, ETI-02, JOG-02, LIN-04, PRE-02, PRO-06, REG-01, REG-02, REG-04
- `T32-triagem` · **chamado** existia numa versão anterior · 10 achado(s): ARQ-05, ETI-01, JOG-01, JOG-03, JOG-04, PRE-04, PRE-05, PRO-01, PRO-04, PRO-05
- `T32-triagem` · **casos-de-uso** existia numa versão anterior · 4 achado(s): ARQ-01, IMP-01, IMP-04, SEG-04
- `T32-triagem` · **ui-web** existia numa versão anterior · 11 achado(s): ARQ-02, IMP-02, PRO-02, PRO-03, SEG-02, UX-01, UX-02, UX-03, UX-04, UX-05, UX-06
- `T32-triagem` · **trilha** existia numa versão anterior · 12 achado(s): ARQ-03, ETI-03, ETI-04, GOV-01, GOV-03, LIN-02, LIN-05, PER-02, PRE-07, REG-03, SUS-01, SUS-03
- `T32-triagem` · **repositorio** existia numa versão anterior · 7 achado(s): ARQ-04, MEC-01, PER-01, PER-03, PER-04, RES-01, SUS-02
- `T32-triagem` · **sla** existia numa versão anterior · 3 achado(s): CTL-02, IMP-03, MEC-03
- `T32-triagem` · **api-http** existia numa versão anterior · 3 achado(s): ARQ-08, SEG-03, SEG-05

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

