# Fontes primárias — análise canário e rollback automático

Depositado na Fase 0 (Nível 1 — Domínio), iteração 1. Autorizado pelo operador
em decisão `PESQUISA AUTORIZADA` (modo: pesquisar e depositar).

Regra em vigor (AP7 / S6): **nenhum algoritmo ou parâmetro numérico entra na
Fase 5 sem constar aqui com fonte verificável.**

---

## R-01 — Google SRE Book, cap. 6 "Monitoring Distributed Systems"

<https://sre.google/sre-book/monitoring-distributed-systems/>

Os **quatro sinais de ouro** (four golden signals) para sistemas voltados ao usuário:

| Sinal | Definição (citada) |
|---|---|
| **Latency** | "The time it takes to service a request." |
| **Traffic** | "A measure of how much demand is being placed on your system, measured in a high-level system-specific metric." |
| **Errors** | "The rate of requests that fail, either explicitly (e.g., HTTP 500s), implicitly (for example, an HTTP 200 success response, but coupled with the wrong content), or by policy." |
| **Saturation** | "How 'full' your service is." |

Duas orientações que restringem diretamente o desenho do coletor:

- **Latência de sucesso e de falha devem ser medidas SEPARADAMENTE.** "An HTTP 500
  error […] might be served very quickly; however […] a slow error is even worse
  than a fast error!" Filtrar os erros para fora do cálculo de latência **esconde**
  a degradação — um canário que falha rápido parece mais rápido que a estável.
- **Não usar médias.** "Collect request counts bucketed by latencies […] rather
  than actual latencies", com fronteiras de histograma exponenciais, porque a
  média oculta a cauda. Percentis (p99) servem como sinal precoce de saturação.

---

## R-02 — Spinnaker: "How canary judgment works"

<https://spinnaker.io/docs/guides/user/canary/judge/>

- Teste estatístico: **Mann-Whitney U** — "a nonparametric test that compares two
  distributions", escolhido porque "doesn't assume your data follows any
  particular pattern (like a bell curve)". Métricas de latência são
  assimétricas com cauda longa; testes paramétricos assumem normalidade que não
  existe.
- Confiança exigida: **98%** — "The judge needs to be 98% confident there's a
  real difference before flagging a metric."
- Classificação por métrica: `Pass` (sem diferença significativa) / `High`
  (canário significativamente acima do baseline) / `Low` (significativamente
  abaixo) / `Nodata` (dados insuficientes) / `NodataFailMetric` (dado ausente em
  métrica com `mustHaveData: true`).
- Score de grupo: `Group Score = (Pass count / Total count) × 100`, **excluindo
  `Nodata` do total**.
- Score final: média ponderada dos grupos; comparações **inclusivas (≥)**.
  `score ≥ passThreshold` → Pass; `score ≥ marginalThreshold` → Marginal; senão → Fail.
- Tratamento de dados: `nanStrategy: remove` (padrão, descarta NaN) ou `replace`
  (substitui por zero). `outlierFactor` padrão **3.0**.

---

## R-03 — Spinnaker: "Best practices for configuring canary"

<https://spinnaker.io/docs/guides/user/canary/best-practices/>

- **Amostra mínima: "You need at least 50 pieces of time series data per metric
  for the statistical analysis to produce accurate results."**
- Baseline: "Compare the canary against an equivalent baseline, deployed at the
  same time" — mesma versão e configuração da produção, mesmo instante de
  implantação, mesmo porte, mesmo volume de tráfego.
  Aviso explícito: "You might be tempted to compare the canary deployment against
  your current production deployment. Instead always compare the canary against an
  equivalent baseline."
- Parâmetros iniciais recomendados: "canary lifetime of 3 hours, an interval of
  1 hour and no warm-up period" → três julgamentos por execução.
- Limiares iniciais recomendados: **marginal = 75**, **pass = 95**.
  "Threshold comparisons are inclusive (≥). A score of exactly 95 with a pass
  threshold of 95 results in a pass."

---

## R-04 — Netflix Technology Blog: "Automated Canary Analysis at Netflix with Kayenta" (abr/2018)

<https://netflixtechblog.com/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69>

- Arquitetura de **três clusters**: produção (maioria do tráfego), baseline
  (~3 instâncias) e canário (~3 instâncias). Baseline e canário recebem fatias
  pequenas e equivalentes.
- Razão de existir do baseline: "comparing a newly created canary cluster to a
  long-lived production cluster could produce unreliable results". Instâncias de
  vida longa acumulam efeitos (aquecimento de cache, JIT, tamanho de heap, deriva
  de estado) que a comparação atribuiria erroneamente à mudança de versão.
- Classificação `Pass` / `High` / `Low`; score final = razão de métricas `Pass`
  sobre o total (9 de 10 → 90%).
- Viés de projeto declarado: preferência por "techniques which are simple to
  understand".
- Escala à época: ~30% dos julgamentos canário de produção, média de **200
  julgamentos/dia**.

---

## R-05 — Google Cloud Blog: "Canary analysis: lessons learned and best practices from Google and Waze"

<https://cloud.google.com/blog/products/devops-sre/canary-analysis-lessons-learned-and-best-practices-from-google-and-waze>

- Repete o mínimo de **50 pontos de série temporal por métrica** "for the
  statistical analysis to be relevant", e alerta que isso pode exigir análises de
  várias horas conforme a granularidade do monitoramento.
- "Don't compare the canary to production instances. Many differences can skew the
  results of the analysis: cache warmup time, heap size, load-balancing
  algorithms, etc."
- Seleção de métricas: começar com uma é possível, mas recomenda-se várias
  cobrindo **latência, erros e saturação** (referência explícita ao SRE Book).
- Efeito medido: a Waze "estimates that canary releases can prevent a quarter of
  all incidents on their services, including most user-facing incidents" (~25%).

---

## R-06 — Argo Rollouts: Analysis & Progressive Delivery

<https://argo-rollouts.readthedocs.io/en/stable/features/analysis/>
Código-fonte dos padrões: <https://github.com/argoproj/argo-rollouts/blob/master/pkg/apis/rollouts/v1alpha1/analysis_types.go>

- Modelo: `AnalysisTemplate` (o que medir e qual o critério) → `AnalysisRun`
  (a execução, que termina em `Successful` / `Failed` / `Inconclusive` / `Error`).
- Comportamento em falha: "aborting it, setting the canary weight back to zero" —
  o rollout entra em estado `Degraded`. **O rollback é a devolução do peso a zero.**
- Análise **background** (corre em paralelo aos passos, não bloqueia) vs.
  **inline/step** (bloqueia o passo até concluir).
- Campos e padrões citados do código-fonte — ver `specs/technical/canary-decision-parameters.md`.
- Distinção conceitual importante: `failure` é contado no **total**, `error` é
  contado em **sucessão** — "unlike failures, errors tend to happen ephemerally
  and may recover on its own". Erro de coleta ≠ métrica ruim.

---

## R-07 — Flagger: Deployment Strategies

<https://docs.flagger.app/usage/deployment-strategies>

- Laço de promoção progressiva: a cada `interval`, o peso do canário sobe em
  `stepWeight` até `maxWeight`.
- `threshold`: número máximo de verificações de métrica falhas toleradas antes do
  rollback automático. Exemplo da doc: `threshold: 10`, `interval: 1m`,
  `maxWeight: 50`, `stepWeight: 2`.
- Alternativa a progressão linear: `stepWeights: [1, 2, 10, 80]` (array ordenado).
- **Fórmulas explícitas da documentação:**
  - tempo mínimo de promoção = `interval * (maxWeight / stepWeight)`
  - tempo até rollback = `interval * threshold`
- Ação de rollback: "route all traffic to primary, scale to zero the canary
  deployment and mark it as failed".
- Distinção operacional relevante: uma verificação falha **detém o avanço** do
  peso; só o acúmulo até `threshold` **dispara o rollback**. Pausar e reverter são
  reações diferentes ao mesmo sinal.
