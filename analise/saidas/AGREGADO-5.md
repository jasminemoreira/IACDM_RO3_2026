# RO3 — análise de ortogonalidade das lentes

Projetos: 5 (T21-certificados, T24-catalogo, T22-plantoes, T23-canario, T25-orcamento)  
Achados: 396  ·  Defeitos distintos (clusters): 371  ·  Módulos: 46


> ⚠ **T24-catalogo: a última versão da arquitetura tem menos módulos que uma anterior** — V(1) 11 · V(2) 9 · V(3) 9. Ou a Fase 3 removeu módulos, ou escreveu a última versão como *delta*; o texto não distingue os dois. A contagem acima usa a última tabela. Nenhum Passo depende dela: os Passos 1 e 4 usam o módulo escrito em cada achado.


> ⚠ **T22-plantoes: a última versão da arquitetura tem menos módulos que uma anterior** — V(1) 11 · V(2) 12 · V(3) 11. Ou a Fase 3 removeu módulos, ou escreveu a última versão como *delta*; o texto não distingue os dois. A contagem acima usa a última tabela. Nenhum Passo depende dela: os Passos 1 e 4 usam o módulo escrito em cada achado.


> ⚠ **T23-canario: a última versão da arquitetura tem menos módulos que uma anterior** — V(1) 12 · V(2) 12 · V(3) 4. Ou a Fase 3 removeu módulos, ou escreveu a última versão como *delta*; o texto não distingue os dois. A contagem acima usa a última tabela. Nenhum Passo depende dela: os Passos 1 e 4 usam o módulo escrito em cada achado.


## Passo 1 — incidência agregada (módulo × lente)

| projeto | módulo | lente | achados |
|---|---|---|---|
| T21-certificados | autorizacao | PRE | ASS-06 |
| T21-certificados | autorizacao | ETI | ETH-03 |
| T21-certificados | autorizacao | JOG | GAM-02 |
| T21-certificados | autorizacao | GOV | GOV-03 |
| T21-certificados | autorizacao | IMP | IMP-04 |
| T21-certificados | autorizacao | CIE | SCI-01 |
| T21-certificados | autorizacao | SEG | SEC-04 |
| T21-certificados | caso-governanca | ARQ | ARC-06 |
| T21-certificados | caso-governanca | PRE | ASS-11 |
| T21-certificados | caso-governanca | ETI | ETH-04 |
| T21-certificados | caso-governanca | JOG | GAM-04 |
| T21-certificados | caso-governanca | GOV | GOV-05 |
| T21-certificados | caso-governanca | PRO | PRO-07 |
| T21-certificados | caso-governanca | REG | REG-05 |
| T21-certificados | caso-governanca | SEG | SEC-09 |
| T21-certificados | caso-varredura | PRE | ASS-09 |
| T21-certificados | caso-varredura | CTR | CTL-04 |
| T21-certificados | caso-varredura | IMP | IMP-06 |
| T21-certificados | caso-varredura | OBS | OBS-04 |
| T21-certificados | caso-varredura | DES | PER-05 |
| T21-certificados | caso-varredura | RES | RES-06 |
| T21-certificados | casos-de-uso | ARQ | ARC-01 |
| T21-certificados | casos-de-uso | JOG | GAM-01 |
| T21-certificados | casos-de-uso | GOV | GOV-01 |
| T21-certificados | casos-de-uso | OBS | OBS-01 |
| T21-certificados | casos-de-uso | DES | PER-01, PER-04 |
| T21-certificados | casos-de-uso | PRO | PRO-04 |
| T21-certificados | casos-de-uso | REG | REG-01 |
| T21-certificados | casos-de-uso | RES | RES-02 |
| T21-certificados | casos-de-uso | SUS | SUS-02 |
| T21-certificados | certificado | PRE | ASS-01, ASS-10 |
| T21-certificados | certificado | MEC | MEC-02 |
| T21-certificados | certificado | REG | REG-02 |
| T21-certificados | pedido | ARQ | ARC-02 |
| T21-certificados | pedido | CTR | CTL-03 |
| T21-certificados | pedido | LIN | LIN-02 |
| T21-certificados | pedido | PRO | PRO-01, PRO-02, PRO-05, PRO-06 |
| T21-certificados | politica-limiar | PRE | ASS-04 |
| T21-certificados | politica-limiar | CTR | CTL-02 |
| T21-certificados | politica-limiar | IMP | IMP-03 |
| T21-certificados | politica-limiar | LIN | LIN-03 |
| T21-certificados | politica-limiar | MEC | MEC-03 |
| T21-certificados | politica-limiar | REG | REG-03 |
| T21-certificados | politica-limiar | CIE | SCI-03 |
| T21-certificados | reconciliacao | ARQ | ARC-04 |
| T21-certificados | reconciliacao | PRE | ASS-03 |
| T21-certificados | reconciliacao | CTR | CTL-01 |
| T21-certificados | reconciliacao | ETI | ETH-01 |
| T21-certificados | reconciliacao | LIN | LIN-01, LIN-05 |
| T21-certificados | reconciliacao | PRO | PRO-03 |
| T21-certificados | relogio | PRE | ASS-08 |
| T21-certificados | relogio | MEC | MEC-04 |
| T21-certificados | relogio | RES | RES-07 |
| T21-certificados | repositorio | ARQ | ARC-03 |
| T21-certificados | repositorio | PRE | ASS-07 |
| T21-certificados | repositorio | GOV | GOV-02 |
| T21-certificados | repositorio | IMP | IMP-02 |
| T21-certificados | repositorio | LIN | LIN-06 |
| T21-certificados | repositorio | MEC | MEC-01, MEC-05 |
| T21-certificados | repositorio | DES | PER-03 |
| T21-certificados | repositorio | RES | RES-03, RES-05 |
| T21-certificados | repositorio | SEG | SEC-07, SEC-11 |
| T21-certificados | repositorio | SUS | SUS-01, SUS-03 |
| T21-certificados | sonda-tls | PRE | ASS-02 |
| T21-certificados | sonda-tls | LIN | LIN-04 |
| T21-certificados | sonda-tls | OBS | OBS-03 |
| T21-certificados | sonda-tls | RES | RES-01, RES-04 |
| T21-certificados | sonda-tls | CIE | SCI-02, SCI-06 |
| T21-certificados | sonda-tls | SEG | SEC-06 |
| T21-certificados | trilha | PRE | ASS-05, ASS-12 |
| T21-certificados | trilha | ETI | ETH-02 |
| T21-certificados | trilha | GOV | GOV-04 |
| T21-certificados | trilha | IMP | IMP-05 |
| T21-certificados | trilha | DES | PER-06 |
| T21-certificados | trilha | REG | REG-04 |
| T21-certificados | trilha | CIE | SCI-04 |
| T21-certificados | trilha | SEG | SEC-08 |
| T21-certificados | web-ui | ARQ | ARC-05, ARC-07 |
| T21-certificados | web-ui | JOG | GAM-03 |
| T21-certificados | web-ui | IMP | IMP-01, IMP-07 |
| T21-certificados | web-ui | OBS | OBS-02 |
| T21-certificados | web-ui | DES | PER-02 |
| T21-certificados | web-ui | CIE | SCI-05 |
| T21-certificados | web-ui | SEG | SEC-01, SEC-02, SEC-03, SEC-05, SEC-10 |
| T21-certificados | web-ui | UX | UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07 |
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
| T24-catalogo | catalog | PRE | ASM-03 |
| T24-catalogo | catalog | JOG | GAME-02 |
| T24-catalogo | catalog | GOV | GOV-01 |
| T24-catalogo | catalog | PRO | PROC-03 |
| T24-catalogo | catalog-mapper | ARQ | ARC-06 |
| T24-catalogo | catalog-mapper | PRE | ASM-01 |
| T24-catalogo | catalog-mapper | CTR | CTRL-03 |
| T24-catalogo | catalog-mapper | JOG | GAME-01 |
| T24-catalogo | catalog-mapper | GOV | GOV-02 |
| T24-catalogo | catalog-mapper | IMP | IMPL-07 |
| T24-catalogo | catalog-mapper | LIN | LING-01, LING-06 |
| T24-catalogo | catalog-mapper | DES | PERF-04 |
| T24-catalogo | catalog-repository | ARQ | ARC-01 |
| T24-catalogo | catalog-repository | PRE | ASM-02 |
| T24-catalogo | catalog-repository | CTR | CTRL-01 |
| T24-catalogo | catalog-repository | IMP | IMPL-02 |
| T24-catalogo | catalog-repository | DES | PERF-01 |
| T24-catalogo | catalog-repository | PRO | PROC-02 |
| T24-catalogo | catalog-repository | RES | RES-02, RES-03 |
| T24-catalogo | catalog-repository | SEG | SEC-02 |
| T24-catalogo | catalog-repository | SUS | SUS-01 |
| T24-catalogo | cli | ARQ | ARC-04, ARC-08 |
| T24-catalogo | cli | PRO | PROC-01, PROC-04, PROC-05 |
| T24-catalogo | cli | REG | REG-02 |
| T24-catalogo | cli | SUS | SUS-03 |
| T24-catalogo | cli | UX | UX-02, UX-04 |
| T24-catalogo | errors | ARQ | ARC-02 |
| T24-catalogo | formatters | JOG | GAME-03 |
| T24-catalogo | formatters | GOV | GOV-05 |
| T24-catalogo | formatters | IMP | IMPL-03 |
| T24-catalogo | formatters | LIN | LING-03 |
| T24-catalogo | formatters | UX | UX-01, UX-03, UX-06 |
| T24-catalogo | lineage-graph | MEC | MEC-02 |
| T24-catalogo | lineage-graph | CIE | SCI-01, SCI-02, SCI-03 |
| T24-catalogo | lineage-graph | SUS | SUS-02 |
| T24-catalogo | model | ARQ | ARC-05, ARC-07 |
| T24-catalogo | model | PRE | ASM-05 |
| T24-catalogo | model | GOV | GOV-03, GOV-04 |
| T24-catalogo | model | IMP | IMPL-04, IMPL-05, IMPL-06 |
| T24-catalogo | model | LIN | LING-02 |
| T24-catalogo | model | MEC | MEC-03, MEC-04 |
| T24-catalogo | model | REG | REG-01, REG-03 |
| T24-catalogo | model | SEG | SEC-03, SEC-05 |
| T24-catalogo | query-service | PRE | ASM-04, ASM-06 |
| T24-catalogo | validation | ARQ | ARC-03 |
| T24-catalogo | validation | CTR | CTRL-02 |
| T24-catalogo | validation | IMP | IMPL-01, IMPL-08 |
| T24-catalogo | validation | LIN | LING-04 |
| T24-catalogo | validation | DES | PERF-02 |
| T24-catalogo | yaml-loader | LIN | LING-05 |
| T24-catalogo | yaml-loader | MEC | MEC-01 |
| T24-catalogo | yaml-loader | RES | RES-01, RES-04 |
| T24-catalogo | yaml-loader | SEG | SEC-01, SEC-04 |
| T24-catalogo | yaml-loader | UX | UX-05 |
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
| PRE Assumptions | univ | 5 | 37 | 35 | 5 |
| ARQ Architectural | univ | 5 | 32 | 31 | 5 |
| IMP Implementability | univ | 5 | 29 | 27 | 5 |
| CIE Scientific | univ | 5 | 26 | 23 | 5 |
| SEG Security | univ | 5 | 29 | 25 | 5 |
| DES Performance | univ | 5 | 21 | 13 | 5 |
| REG Regulatory | univ | 5 | 15 | 13 | 5 |
| RES Resilience | cond | 5 | 24 | 22 | 5 |
| UX UI/UX | cond | 5 | 25 | 23 | 5 |
| MIG Migration / Coexistence | cond | 1 | 3 | 3 | 1 |
| SUS Sustainability / Proportionality | cond | 5 | 15 | 8 | 5 |
| ETI Ethical / Human Impact | cond | 3 | 11 | 11 | 3 |
| PRO Process / Workflow | cond | 5 | 26 | 23 | 5 |
| GOV Governance / Accountability | cond | 5 | 20 | 18 | 5 |
| OBS Observability / Operability | cond | 3 | 10 | 10 | 3 |
| CTR Control Engineering | cond | 5 | 17 | 15 | 5 |
| JOG Game Theory | cond | 4 | 14 | 10 | 4 |
| LIN Linguistics / Grammar | cond | 5 | 26 | 26 | 5 |
| MEC Mechanical Engineering | cond | 4 | 16 | 16 | 4 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 14 | 6 | 43% | faltam 8 defeito(s) |
| DES Performance | 21 | 8 | 38% | faltam 13 defeito(s) |
| JOG Game Theory | 13 | 3 | 23% | faltam 10 defeito(s) |
| SEG Security | 29 | 4 | 14% | faltam 25 defeito(s) |
| CTR Control Engineering | 17 | 2 | 12% | faltam 15 defeito(s) |
| PRO Process / Workflow | 26 | 3 | 12% | faltam 23 defeito(s) |
| GOV Governance / Accountability | 20 | 2 | 10% | faltam 18 defeito(s) |
| UX UI/UX | 25 | 2 | 8% | faltam 23 defeito(s) |
| REG Regulatory | 14 | 1 | 7% | faltam 13 defeito(s) |
| IMP Implementability | 29 | 2 | 7% | faltam 27 defeito(s) |
| PRE Assumptions | 37 | 2 | 5% | faltam 35 defeito(s) |
| RES Resilience | 23 | 1 | 4% | faltam 22 defeito(s) |
| CIE Scientific | 24 | 1 | 4% | faltam 23 defeito(s) |
| ARQ Architectural | 32 | 1 | 3% | faltam 31 defeito(s) |
| ETI Ethical / Human Impact | 11 | 0 | 0% | faltam 11 defeito(s) |
| OBS Observability / Operability | 10 | 0 | 0% | faltam 10 defeito(s) |
| LIN Linguistics / Grammar | 26 | 0 | 0% | faltam 26 defeito(s) |
| MEC Mechanical Engineering | 16 | 0 | 0% | faltam 16 defeito(s) |
| MIG Migration / Coexistence | 3 | 0 | 0% | faltam 3 defeito(s) |

Sobreposição média: **10%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 37 | 9% | 35 | 9% |
| ARQ Architectural | 32 | 8% | 31 | 8% |
| IMP Implementability | 29 | 7% | 27 | 7% |
| LIN Linguistics / Grammar | 26 | 7% | 26 | 7% |
| SEG Security | 29 | 7% | 25 | 7% |
| CIE Scientific | 26 | 7% | 23 | 6% |
| UX UI/UX | 25 | 6% | 23 | 6% |
| PRO Process / Workflow | 26 | 7% | 23 | 6% |
| RES Resilience | 24 | 6% | 22 | 6% |
| GOV Governance / Accountability | 20 | 5% | 18 | 5% |
| MEC Mechanical Engineering | 16 | 4% | 16 | 4% |
| CTR Control Engineering | 17 | 4% | 15 | 4% |
| DES Performance | 21 | 5% | 13 | 4% |
| REG Regulatory | 15 | 4% | 13 | 4% |
| ETI Ethical / Human Impact | 11 | 3% | 11 | 3% |
| OBS Observability / Operability | 10 | 3% | 10 | 3% |
| JOG Game Theory | 14 | 4% | 10 | 3% |
| SUS Sustainability / Proportionality | 15 | 4% | 8 | 2% |
| MIG Migration / Coexistence | 3 | 1% | 3 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.36 | 6 | 0.21 |  |
| JOG × SEG | 0.16 | 2 | 0.05 |  |
| JOG × PRO | 0.32 | 1 | 0.03 |  |
| CTR × RES | 0.15 | 1 | 0.03 |  |
| CTR × PRO | 0.23 | 1 | 0.02 |  |
| REG × SEG | 0.15 | 1 | 0.02 |  |
| DES × UX | 0.04 | 1 | 0.02 |  |
| GOV × IMP | 0.30 | 1 | 0.02 |  |
| GOV × SEG | 0.33 | 1 | 0.02 |  |
| PRO × UX | 0.10 | 1 | 0.02 |  |
| IMP × CIE | 0.30 | 1 | 0.02 |  |
| PRE × DES | 0.24 | 1 | 0.02 |  |
| ARQ × PRE | 0.26 | 1 | 0.01 | sim (§4) |
| ARQ × CTR | 0.24 | 0 | 0.00 |  |
| ARQ × ETI | 0.12 | 0 | 0.00 |  |
| ARQ × JOG | 0.18 | 0 | 0.00 |  |
| ARQ × GOV | 0.24 | 0 | 0.00 |  |
| ARQ × IMP | 0.29 | 0 | 0.00 |  |
| ARQ × LIN | 0.26 | 0 | 0.00 |  |
| ARQ × MEC | 0.11 | 0 | 0.00 |  |
| ARQ × MIG | 0.03 | 0 | 0.00 |  |
| ARQ × OBS | 0.12 | 0 | 0.00 |  |
| ARQ × DES | 0.25 | 0 | 0.00 |  |
| ARQ × PRO | 0.31 | 0 | 0.00 |  |
| ARQ × REG | 0.14 | 0 | 0.00 |  |

*(146 pares restantes omitidos da tabela; todos estão no JSON — nenhum corte silencioso.)*

### Módulos removidos entre versões da arquitetura

Achados de iterações anteriores citam módulos que a versão corrente não tem
mais. **Isto é normal** — a Fase 3 elimina e funde módulos, e o achado continua
válido contra a versão que ele criticou. Listado para leitura da matriz: quem
procurar o módulo na arquitetura final não vai encontrá-lo.

O que seria anomalia é um módulo ausente de TODAS as versões — isso o gate
cruzado da v0.13.0 barra na origem, e não chega até aqui.

- `T21-certificados` · **casos-de-uso** existia numa versão anterior · 10 achado(s): ARC-01, GAM-01, GOV-01, OBS-01, PER-01, PER-04, PRO-04, REG-01, RES-02, SUS-02
- `T24-catalogo` · **catalog-repository** existia numa versão anterior · 10 achado(s): ARC-01, ASM-02, CTRL-01, IMPL-02, PERF-01, PROC-02, RES-02, RES-03, SEC-02, SUS-01
- `T24-catalogo` · **errors** existia numa versão anterior · 1 achado(s): ARC-02
- `T22-plantoes` · **catalogo-restricoes** existia numa versão anterior · 9 achado(s): ARQ-02, ASS-01, CIE-01, ETI-02, GAM-02, IMP-01, LIN-01, REG-01, REG-02
- `T22-plantoes` · **fronteira** existia numa versão anterior · 5 achado(s): ARQ-03, ASS-02, CIE-03, CTL-01, CTL-02
- `T22-plantoes` · **diario** existia numa versão anterior · 9 achado(s): ARQ-05, GOV-04, IMP-04, LIN-05, PER-04, PRO-05, RES-04, SEC-04, SUS-03
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

- MIG Migration / Coexistence — ativou em 1 projeto(s)

