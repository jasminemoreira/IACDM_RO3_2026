# RO3 — análise de ortogonalidade das lentes

Projetos: 12 (T21-certificados, T24-catalogo, T22-plantoes, T23-canario, T25-orcamento, T26-extratos, T27-despesas, T28-agenda, T29-retencao, T30-notifica, T31-precos, T32-triagem)  
Achados: 1100  ·  Defeitos distintos (clusters): 1029  ·  Módulos: 130


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
| PRE Assumptions | univ | 12 | 107 | 98 | 12 |
| ARQ Architectural | univ | 12 | 90 | 88 | 12 |
| IMP Implementability | univ | 12 | 79 | 70 | 12 |
| CIE Scientific | univ | 12 | 60 | 55 | 12 |
| SEG Security | univ | 12 | 82 | 74 | 12 |
| DES Performance | univ | 12 | 61 | 47 | 12 |
| REG Regulatory | univ | 12 | 42 | 34 | 12 |
| RES Resilience | cond | 12 | 66 | 56 | 12 |
| UX UI/UX | cond | 12 | 75 | 73 | 12 |
| MIG Migration / Coexistence | cond | 4 | 16 | 14 | 4 |
| SUS Sustainability / Proportionality | cond | 12 | 41 | 26 | 11 |
| ETI Ethical / Human Impact | cond | 5 | 18 | 15 | 5 |
| PRO Process / Workflow | cond | 12 | 71 | 60 | 12 |
| GOV Governance / Accountability | cond | 12 | 57 | 52 | 12 |
| OBS Observability / Operability | cond | 9 | 37 | 36 | 9 |
| CTR Control Engineering | cond | 12 | 47 | 42 | 12 |
| JOG Game Theory | cond | 7 | 27 | 20 | 7 |
| LIN Linguistics / Grammar | cond | 12 | 79 | 76 | 12 |
| MEC Mechanical Engineering | cond | 10 | 45 | 42 | 10 |

### Grau de sobreposição por lente (adendo A6)

Que fração dos defeitos de cada lente outra lente TAMBÉM encontrou. O critério de
remoção do §4 é binário e exige **100%** — todos os defeitos compartilhados. Esta
coluna mostra a distância até lá, que o veredito sozinho esconde: uma lente com 60%
de sobreposição, largamente redundante para qualquer leitor, passa no §4 como
legítima.

| lente | defeitos | compartilhados | % | distância até o critério |
|---|---|---|---|---|
| SUS Sustainability / Proportionality | 39 | 13 | 33% | faltam 26 defeito(s) |
| DES Performance | 59 | 12 | 20% | faltam 47 defeito(s) |
| JOG Game Theory | 25 | 5 | 20% | faltam 20 defeito(s) |
| ETI Ethical / Human Impact | 18 | 3 | 17% | faltam 15 defeito(s) |
| REG Regulatory | 40 | 6 | 15% | faltam 34 defeito(s) |
| PRO Process / Workflow | 70 | 10 | 14% | faltam 60 defeito(s) |
| RES Resilience | 64 | 8 | 12% | faltam 56 defeito(s) |
| MIG Migration / Coexistence | 16 | 2 | 12% | faltam 14 defeito(s) |
| IMP Implementability | 79 | 9 | 11% | faltam 70 defeito(s) |
| CTR Control Engineering | 47 | 5 | 11% | faltam 42 defeito(s) |
| PRE Assumptions | 107 | 9 | 8% | faltam 98 defeito(s) |
| SEG Security | 80 | 6 | 8% | faltam 74 defeito(s) |
| GOV Governance / Accountability | 56 | 4 | 7% | faltam 52 defeito(s) |
| MEC Mechanical Engineering | 45 | 3 | 7% | faltam 42 defeito(s) |
| LIN Linguistics / Grammar | 79 | 3 | 4% | faltam 76 defeito(s) |
| CIE Scientific | 57 | 2 | 4% | faltam 55 defeito(s) |
| OBS Observability / Operability | 37 | 1 | 3% | faltam 36 defeito(s) |
| UX UI/UX | 75 | 2 | 3% | faltam 73 defeito(s) |
| ARQ Architectural | 90 | 2 | 2% | faltam 88 defeito(s) |

Sobreposição média: **10%**. Nenhuma lente é declarável removível pelo §4 enquanto essa coluna não chegar a 100%.

Nenhuma lente produziu achados sem nenhuma contribuição exclusiva.

## Passo 3 — simulação de remoção

| lente | achados perdidos | % do total | defeitos que ninguém recupera | % dos defeitos |
|---|---|---|---|---|
| PRE Assumptions | 107 | 10% | 98 | 10% |
| ARQ Architectural | 90 | 8% | 88 | 9% |
| LIN Linguistics / Grammar | 79 | 7% | 76 | 7% |
| SEG Security | 82 | 7% | 74 | 7% |
| UX UI/UX | 75 | 7% | 73 | 7% |
| IMP Implementability | 79 | 7% | 70 | 7% |
| PRO Process / Workflow | 71 | 6% | 60 | 6% |
| RES Resilience | 66 | 6% | 56 | 5% |
| CIE Scientific | 60 | 5% | 55 | 5% |
| GOV Governance / Accountability | 57 | 5% | 52 | 5% |
| DES Performance | 61 | 6% | 47 | 5% |
| CTR Control Engineering | 47 | 4% | 42 | 4% |
| MEC Mechanical Engineering | 45 | 4% | 42 | 4% |
| OBS Observability / Operability | 37 | 3% | 36 | 3% |
| REG Regulatory | 42 | 4% | 34 | 3% |
| SUS Sustainability / Proportionality | 41 | 4% | 26 | 3% |
| JOG Game Theory | 27 | 2% | 20 | 2% |
| ETI Ethical / Human Impact | 18 | 2% | 15 | 1% |
| MIG Migration / Coexistence | 16 | 1% | 14 | 1% |

## Passo 4 — sobreposição par a par

| par | Jaccard módulos | defeitos em comum | Jaccard defeitos | a priori? |
|---|---|---|---|---|
| DES × SUS | 0.40 | 9 | 0.10 |  |
| ETI × JOG | 0.23 | 2 | 0.05 |  |
| CTR × PRO | 0.20 | 3 | 0.03 |  |
| JOG × SEG | 0.08 | 2 | 0.02 |  |
| ETI × REG | 0.15 | 1 | 0.02 |  |
| MEC × MIG | 0.07 | 1 | 0.02 |  |
| JOG × REG | 0.11 | 1 | 0.02 |  |
| PRO × RES | 0.17 | 2 | 0.02 |  |
| GOV × SEG | 0.26 | 2 | 0.01 |  |
| IMP × CIE | 0.23 | 2 | 0.01 |  |
| PRE × SUS | 0.24 | 2 | 0.01 |  |
| IMP × LIN | 0.28 | 2 | 0.01 |  |
| REG × SUS | 0.19 | 1 | 0.01 |  |
| MEC × REG | 0.16 | 1 | 0.01 |  |
| CTR × REG | 0.09 | 1 | 0.01 |  |
| CTR × MEC | 0.12 | 1 | 0.01 |  |
| JOG × PRO | 0.25 | 1 | 0.01 |  |
| GOV × REG | 0.24 | 1 | 0.01 |  |
| GOV × MEC | 0.10 | 1 | 0.01 |  |
| OBS × RES | 0.33 | 1 | 0.01 |  |
| CTR × GOV | 0.15 | 1 | 0.01 |  |
| PRO × REG | 0.16 | 1 | 0.01 |  |
| CTR × RES | 0.17 | 1 | 0.01 |  |
| IMP × REG | 0.19 | 1 | 0.01 |  |
| SEG × SUS | 0.18 | 1 | 0.01 |  |

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
- `T26-extratos` · **canonicalizer** existia numa versão anterior · 4 achado(s): ARC-06, ASM-02, LIN-04, PRF-05
- `T26-extratos` · **repository** existia numa versão anterior · 13 achado(s): ASM-04, GOV-03, IMP-04, MEC-03, OBS-04, PRF-03, REG-01, REG-02, RES-01, RES-04, SEC-03, SEC-06, SUS-01
- `T29-retencao` · **block** existia numa versão anterior · 3 achado(s): ARQ-05, ASM-03, MEC-04
- `T29-retencao` · **migrator** existia numa versão anterior · 6 achado(s): ARQ-04, GOV-03, MIG-01, MIG-02, MIG-03, PRF-03
- `T30-notifica` · **suppression** existia numa versão anterior · 7 achado(s): ARC-01, ETH-01, ETH-02, GOV-02, LIN-02, PERF-03, PRO-03
- `T31-precos` · **prova-paridade** existia numa versão anterior · 4 achado(s): ARQ-01, MEC-01, MIG-02, PERF-02
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

