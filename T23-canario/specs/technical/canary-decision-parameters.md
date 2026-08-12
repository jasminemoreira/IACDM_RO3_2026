# Parâmetros numéricos da decisão canário — com fonte

Depositado na Fase 0. **Toda linha desta tabela tem fonte.** Um parâmetro sem
fonte nesta página não pode ser usado na Fase 5 (AP7 / S6 Tier 2).

Referências completas em `specs/references/canary-analysis-sources.md`.

---

## 1. Parâmetros de análise estatística

| Parâmetro | Valor de referência | Fonte | Observação para o desenho |
|---|---|---|---|
| Teste de comparação | Mann-Whitney U (Wilcoxon rank-sum) | R-02 | Não paramétrico. Latência não é normal — tem cauda longa e assimetria. |
| Nível de confiança | **98%** | R-02 | Kayenta só marca diferença com 98% de confiança. Alto de propósito: falso positivo custa um rollback indevido. |
| Amostra mínima por métrica | **≥ 50 pontos de série temporal** | R-03, R-05 | "at least 50 pieces of time series data per metric for the statistical analysis to produce accurate results". **Abaixo disso a decisão não é decisão — é ruído.** |
| Fator de outlier | **3.0** | R-02 | `outlierFactor` padrão do Kayenta. |
| Tratamento de NaN | `remove` (padrão) ou `replace` por zero | R-02 | Duas políticas legítimas com consequências opostas; a escolha precisa ser explícita, não implícita. |

## 2. Limiares de decisão (score)

| Parâmetro | Valor de referência | Fonte |
|---|---|---|
| `marginalThreshold` | **75** | R-03 |
| `passThreshold` | **95** | R-03 |
| Comparação de limiar | **inclusiva (≥)** | R-02, R-03 — "A score of exactly 95 with a pass threshold of 95 results in a pass." |
| Score de grupo | `(Pass count / Total count) × 100`, excluindo `Nodata` do total | R-02, R-04 |
| Score final | média ponderada dos scores de grupo | R-02 |

## 3. Classificação por métrica (Kayenta)

| Rótulo | Significado | Fonte |
|---|---|---|
| `Pass` | Nenhuma diferença significativa detectada | R-02, R-04 |
| `High` | Canário significativamente **acima** do baseline | R-02, R-04 |
| `Low` | Canário significativamente **abaixo** do baseline | R-02, R-04 |
| `Nodata` | Dados insuficientes para comparar | R-02 |
| `NodataFailMetric` | Dado ausente em métrica marcada `mustHaveData: true` | R-02 |

**Nota de direção (não é detalhe):** `High` só é ruim se a métrica for do tipo
"menor é melhor" (latência, taxa de erro). Para "maior é melhor" (vazão,
disponibilidade), `Low` é a reprovação. A direção precisa estar declarada por
métrica, ou o julgamento inverte o sinal silenciosamente.

## 4. Tolerância a falha e erro (Argo Rollouts, do código-fonte)

| Campo | Padrão | Comentário citado do código | Fonte |
|---|---|---|---|
| `failureLimit` | **0** | "maximum number of times the measurement is allowed to fail, before the entire metric is considered Failed (default: 0)" | R-06 |
| `inconclusiveLimit` | **0** | "maximum number of times the measurement is allowed to measure Inconclusive […] (default: 0)" | R-06 |
| `consecutiveErrorLimit` | **4** | "maximum number of times the measurement is allowed to error in succession, before the metric is considered error (default: 4)" | R-06 |
| `consecutiveSuccessLimit` | **0** (desabilitado) | "number of consecutive times the measurement must succeed for the entire metric to be considered Successful" | R-06 |
| `interval` | — | "If omitted, will perform a single measurement" | R-06 |
| `count` | — | "If both interval and count are omitted, the effective count is 1. If only interval is specified, metric runs indefinitely. If count > 1, interval must be specified." | R-06 |

**Distinção estrutural (R-06):** *falha* é contada no **total acumulado**; *erro*
é contado em **sucessão** e o contador zera ao recuperar — "unlike failures,
errors tend to happen ephemerally and may recover on its own".
Uma métrica ruim e uma coleta quebrada são eventos de naturezas diferentes e não
podem cair no mesmo contador. Confundi-los produz rollback por indisponibilidade
do coletor, não por defeito do canário.

## 5. Parâmetros do laço de promoção (Flagger)

| Parâmetro | Exemplo da doc | Significado | Fonte |
|---|---|---|---|
| `interval` | `1m` | Período entre verificações | R-07 |
| `stepWeight` | `2` (%) | Incremento de peso por intervalo | R-07 |
| `maxWeight` | `50` (%) | Teto de tráfego no canário | R-07 |
| `threshold` | `10` | Verificações falhas toleradas antes do rollback | R-07 |
| `stepWeights` | `[1, 2, 10, 80]` | Progressão não-linear alternativa | R-07 |

**Fórmulas citadas literalmente (R-07):**
```
tempo mínimo de promoção = interval * (maxWeight / stepWeight)
tempo até rollback       = interval * threshold
```
Estas duas fórmulas são o meio de verificar, no teste, que a temporização
implementada é a esperada — são critério, não enfeite.

## 6. Parâmetros de duração (Spinnaker)

| Parâmetro | Valor inicial recomendado | Fonte |
|---|---|---|
| Tempo de vida da análise | 3 horas | R-03 |
| Intervalo de julgamento | 1 hora (→ 3 julgamentos) | R-03 |
| Período de aquecimento | nenhum, como ponto de partida | R-03 |

⚠️ **Conflito registrado, a resolver na Fase 1, não aqui:** estes valores são de
produção real. O substrato deste projeto é simulado (decisão `SUBSTRATO DE
EXECUÇÃO`), e o §2 do enunciado dá 2-4h de sessão única. Uma análise de 3 horas
de relógio não cabe. A saída **não** é inventar números menores: é tornar o tempo
uma dependência injetável, de modo que a *razão* entre os parâmetros (amostra
mínima, intervalos por julgamento, passos até `maxWeight`) seja preservada
enquanto a escala de relógio é comprimida no simulador. Preservar as razões é o
que mantém as fórmulas de R-07 verificáveis no teste.

## 7. Seleção de métricas

Os quatro sinais de ouro (R-01): **latência, tráfego, erros, saturação**.
R-05 recomenda no mínimo latência + erros + saturação — "you can get started with
a single metric, [but] we advise that you use several metrics that represent
different aspects of your application's health".

Duas regras do R-01 que são restrições de coleta, não sugestões:
1. **Latência de requisições bem-sucedidas e falhas medidas separadamente** — um
   erro servido rápido melhora a latência média e mascara o defeito.
2. **Percentis/histogramas, não médias** — a média oculta a cauda, e a cauda é
   onde a regressão aparece primeiro.

## 8. Premissa metodológica herdada (R-03, R-04, R-05) — a mais cara de ignorar

**O canário não deve ser comparado com a produção em execução prolongada.** Ele
deve ser comparado com um **baseline implantado no mesmo instante, com a versão e
a configuração da estável**, recebendo o mesmo tipo e volume de tráfego.

Motivo: instâncias de vida longa diferem da recém-criada em aquecimento de cache,
JIT, tamanho de heap e algoritmo de balanceamento. Comparar contra elas atribui à
*mudança de versão* uma diferença que na verdade é de *idade da instância*.

Consequência direta para este projeto, a decidir na Fase 1: a decisão registrada
`SINAL DE DECISÃO` fala em "canário vs. estável no mesmo intervalo". A literatura
diz que isso só é válido se a estável comparada for um **baseline pareado**, e não
a estável de vida longa. Isso é uma pergunta em aberto de escopo — está listada
nas Ambiguidades Remanescentes da síntese, e é candidata natural à lente Premissas
e à lente Científica na Fase 2.
