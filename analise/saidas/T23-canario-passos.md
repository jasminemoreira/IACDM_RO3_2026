# RO3 — análise de ortogonalidade das lentes

Projetos: 1 (T23-canario)  
Achados: 72  ·  Defeitos distintos (clusters): 67  ·  Módulos: 4


> ⚠ **T23-canario: a última versão da arquitetura tem menos módulos que uma anterior** — V(1) 12 · V(2) 12 · V(3) 4. Ou a Fase 3 removeu módulos, ou escreveu a última versão como *delta*; o texto não distingue os dois. A contagem acima usa a última tabela. Nenhum Passo depende dela: os Passos 1 e 4 usam o módulo escrito em cada achado.


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T23-canario | alvo-de-implantacao | PRE | ASM-08 |
| T23-canario | alvo-de-implantacao | LIN | LIN-03 |
| T23-canario | alvo-de-implantacao | MIG | MIG-01, MIG-03 |
| T23-canario | alvo-de-implantacao | PRO | PRO-03, PRO-04 |
| T23-canario | alvo-de-implantacao | SEG | SEC-02 |
| T23-canario | alvo-de-implantacao | SUS | SUS-03 |
| T23-canario | cli | GOV | GOV-02, GOV-03 |
| T23-canario | cli | IMP | IMP-04 |
| T23-canario | cli | OBS | OBS-02 |
| T23-canario | cli | SEG | SEC-01, SEC-03 |
| T23-canario | cli | UX | UX-01, UX-02, UX-03, UX-04 |
| T23-canario | configuracao | ARQ | ARQ-05 |
| T23-canario | configuracao | IMP | IMP-05 |
| T23-canario | configuracao | MEC | MEC-03 |
| T23-canario | configuracao | CIE | SCI-06 |
| T23-canario | contadores | RES | RES-02, RES-04 |
| T23-canario | coordenador | ARQ | ARQ-01 |
| T23-canario | coordenador | CTR | CTL-01, CTL-04 |
| T23-canario | coordenador | GOV | GOV-01 |
| T23-canario | coordenador | IMP | IMP-03 |
| T23-canario | coordenador | MIG | MIG-02 |
| T23-canario | coordenador | OBS | OBS-01, OBS-03 |
| T23-canario | coordenador | PRO | PRO-01, PRO-02, PRO-05 |
| T23-canario | coordenador | RES | RES-03 |
| T23-canario | fonte-de-metricas | LIN | LIN-01, LIN-04 |
| T23-canario | fonte-de-metricas | RES | RES-01 |
| T23-canario | guarda-absoluta | PRE | ASM-04 |
| T23-canario | guarda-absoluta | IMP | IMP-02 |
| T23-canario | guarda-absoluta | CIE | SCI-01, SCI-07 |
| T23-canario | janela | PRE | ASM-03, ASM-07 |
| T23-canario | janela | CTR | CTL-02, CTL-03 |
| T23-canario | janela | DES | PERF-01, PERF-03 |
| T23-canario | janela | CIE | SCI-04 |
| T23-canario | janela | SUS | SUS-02 |
| T23-canario | julgamento | IMP | IMP-01 |
| T23-canario | julgamento | MEC | MEC-02, MEC-04 |
| T23-canario | julgamento | DES | PERF-02 |
| T23-canario | julgamento | REG | REG-01 |
| T23-canario | julgamento | CIE | SCI-03, SCI-05, SCI-08 |
| T23-canario | plano-de-passos | ARQ | ARQ-04 |
| T23-canario | plano-de-passos | PRE | ASM-02 |
| T23-canario | plano-de-passos | SUS | SUS-01 |
| T23-canario | relogio | PRE | ASM-05 |
| T23-canario | relogio | LIN | LIN-02, LIN-05 |
| T23-canario | score | ARQ | ARQ-02 |
| T23-canario | score | MEC | MEC-01 |
| T23-canario | score | CIE | SCI-02, SCI-09 |
| T23-canario | simulador-de-cenario | ARQ | ARQ-03 |
| T23-canario | simulador-de-cenario | PRE | ASM-01, ASM-09 |

## Passo 2 — contribuição exclusiva por lente

Exclusiva = defeitos (clusters) em que a lente é a única presente.

| lente | tipo | projetos ativa | achados | exclusiva | projetos c/ exclusiva |
|---|---|---|---|---|---|
| PRE Assumptions | univ | 1 | 8 | 7 | 1 |
| ARQ Architectural | univ | 1 | 5 | 4 | 1 |
| IMP Implementability | univ | 1 | 5 | 4 | 1 |
| CIE Scientific | univ | 1 | 9 | 8 | 1 |
| SEG Security | univ | 1 | 3 | 3 | 1 |
| DES Performance | univ | 1 | 3 | 2 | 1 |
| REG Regulatory | univ | 1 | 1 | 1 | 1 |
| RES Resilience | cond | 1 | 4 | 4 | 1 |
| UX UI/UX | cond | 1 | 4 | 4 | 1 |
| MIG Migration / Coexistence | cond | 1 | 3 | 3 | 1 |
| SUS Sustainability / Proportionality | cond | 1 | 3 | 2 | 1 |
| ETI Ethical / Human Impact | cond | 0 | 0 | 0 | 0 |
| PRO Process / Workflow | cond | 1 | 5 | 4 | 1 |
| GOV Governance / Accountability | cond | 1 | 3 | 2 | 1 |
| OBS Observability / Operability | cond | 1 | 3 | 3 | 1 |
| CTR Control Engineering | cond | 1 | 4 | 3 | 1 |
| JOG Game Theory | cond | 0 | 0 | 0 | 0 |
| LIN Linguistics / Grammar | cond | 1 | 5 | 5 | 1 |
| MEC Mechanical Engineering | cond | 1 | 4 | 4 | 1 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| GOV Governance / Accountability | 3 | 1 | 33% | faltam 2 defeito(s) |
| SUS Sustainability / Proportionality | 3 | 1 | 33% | faltam 2 defeito(s) |
| DES Performance | 3 | 1 | 33% | faltam 2 defeito(s) |
| CTR Control Engineering | 4 | 1 | 25% | faltam 3 defeito(s) |
| ARQ Architectural | 5 | 1 | 20% | faltam 4 defeito(s) |
| IMP Implementability | 5 | 1 | 20% | faltam 4 defeito(s) |
| PRO Process / Workflow | 5 | 1 | 20% | faltam 4 defeito(s) |
| PRE Assumptions | 8 | 1 | 12% | faltam 7 defeito(s) |
| CIE Scientific | 8 | 0 | 0% | faltam 8 defeito(s) |
| SEG Security | 3 | 0 | 0% | faltam 3 defeito(s) |
| REG Regulatory | 1 | 0 | 0% | faltam 1 defeito(s) |
| RES Resilience | 4 | 0 | 0% | faltam 4 defeito(s) |
| UX UI/UX | 4 | 0 | 0% | faltam 4 defeito(s) |
| MIG Migration / Coexistence | 3 | 0 | 0% | faltam 3 defeito(s) |
| OBS Observability / Operability | 3 | 0 | 0% | faltam 3 defeito(s) |
| LIN Linguistics / Grammar | 5 | 0 | 0% | faltam 5 defeito(s) |
| MEC Mechanical Engineering | 4 | 0 | 0% | faltam 4 defeito(s) |

Sobreposição média: **11%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| CIE Scientific | 9 | 12% | 8 | 12% |
| PRE Assumptions | 8 | 11% | 7 | 10% |
| LIN Linguistics / Grammar | 5 | 7% | 5 | 7% |
| ARQ Architectural | 5 | 7% | 4 | 6% |
| IMP Implementability | 5 | 7% | 4 | 6% |
| RES Resilience | 4 | 6% | 4 | 6% |
| UX UI/UX | 4 | 6% | 4 | 6% |
| PRO Process / Workflow | 5 | 7% | 4 | 6% |
| MEC Mechanical Engineering | 4 | 6% | 4 | 6% |
| SEG Security | 3 | 4% | 3 | 4% |
| MIG Migration / Coexistence | 3 | 4% | 3 | 4% |
| OBS Observability / Operability | 3 | 4% | 3 | 4% |
| CTR Control Engineering | 4 | 6% | 3 | 4% |
| DES Performance | 3 | 4% | 2 | 3% |
| SUS Sustainability / Proportionality | 3 | 4% | 2 | 3% |
| GOV Governance / Accountability | 3 | 4% | 2 | 3% |
| REG Regulatory | 1 | 1% | 1 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.25 | 1 | 0.20 |  |
| GOV × IMP | 0.40 | 1 | 0.14 |  |
| CTR × PRO | 0.33 | 1 | 0.12 |  |
| ARQ × PRE | 0.22 | 1 | 0.08 | sim (§4) |
| ARQ × CTR | 0.17 | 0 | 0.00 |  |
| ARQ × GOV | 0.17 | 0 | 0.00 |  |
| ARQ × IMP | 0.25 | 0 | 0.00 |  |
| ARQ × LIN | 0.00 | 0 | 0.00 |  |
| ARQ × MEC | 0.33 | 0 | 0.00 |  |
| ARQ × MIG | 0.17 | 0 | 0.00 |  |
| ARQ × OBS | 0.17 | 0 | 0.00 |  |
| ARQ × DES | 0.00 | 0 | 0.00 |  |
| ARQ × PRO | 0.17 | 0 | 0.00 |  |
| ARQ × REG | 0.00 | 0 | 0.00 |  |
| ARQ × RES | 0.14 | 0 | 0.00 |  |
| ARQ × CIE | 0.25 | 0 | 0.00 |  |
| ARQ × SEG | 0.00 | 0 | 0.00 |  |
| ARQ × SUS | 0.14 | 0 | 0.00 |  |
| ARQ × UX | 0.00 | 0 | 0.00 |  |
| PRE × CTR | 0.14 | 0 | 0.00 |  |
| PRE × GOV | 0.00 | 0 | 0.00 |  |
| PRE × IMP | 0.10 | 0 | 0.00 |  |
| PRE × LIN | 0.29 | 0 | 0.00 |  |
| PRE × MEC | 0.00 | 0 | 0.00 |  |
| PRE × MIG | 0.14 | 0 | 0.00 |  |

*(111 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T23-canario` · **plano-de-passos** existia numa versão anterior · 3 achado(s): ARQ-04, ASM-02, SUS-01
- `T23-canario` · **janela** existia numa versão anterior · 8 achado(s): ASM-03, ASM-07, CTL-02, CTL-03, PERF-01, PERF-03, SCI-04, SUS-02
- `T23-canario` · **guarda-absoluta** existia numa versão anterior · 4 achado(s): ASM-04, IMP-02, SCI-01, SCI-07
- `T23-canario` · **relogio** existia numa versão anterior · 3 achado(s): ASM-05, LIN-02, LIN-05
- `T23-canario` · **score** existia numa versão anterior · 4 achado(s): ARQ-02, MEC-01, SCI-02, SCI-09
- `T23-canario` · **cli** existia numa versão anterior · 10 achado(s): GOV-02, GOV-03, IMP-04, OBS-02, SEC-01, SEC-03, UX-01, UX-02, UX-03, UX-04
- `T23-canario` · **alvo-de-implantacao** existia numa versão anterior · 8 achado(s): ASM-08, LIN-03, MIG-01, MIG-03, PRO-03, PRO-04, SEC-02, SUS-03
- `T23-canario` · **fonte-de-metricas** existia numa versão anterior · 3 achado(s): LIN-01, LIN-04, RES-01
- `T23-canario` · **contadores** existia numa versão anterior · 2 achado(s): RES-02, RES-04

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

