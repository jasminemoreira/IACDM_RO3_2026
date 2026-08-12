# Glossário do domínio — implantação canário

Vocabulário fixado na Fase 0, Nível 1. **Sinônimos são proibidos**: cada conceito
tem um nome só, e é esse nome que aparece nos módulos da Fase 1, na matriz de
cobertura da Fase 2 e no código da Fase 5.

| Termo | Definição adotada | Sinônimo a EVITAR | Fonte |
|---|---|---|---|
| **estável** | A versão atualmente em produção, que serve a maior fatia do tráfego e é o destino do rollback. | "primária", "produção", "atual", "v1" | R-07 usa "primary"; adotamos "estável" por ser o termo do enunciado |
| **canário** | A versão nova sob avaliação, recebendo fatia minoritária de tráfego real. | "nova versão", "candidata" | enunciado |
| **baseline** | Ponto de comparação das métricas do canário. **Não é sinônimo de estável** — ver nota abaixo. | usar "estável" no lugar | R-03, R-04 |
| **peso** | Fração do tráfego real roteada a uma versão, em % inteiro de 0 a 100. Soma sempre 100. | "porcentagem", "split", "fatia" | R-07 (`stepWeight`, `maxWeight`) |
| **passo** | Um degrau da progressão do peso do canário (ex.: 5% → 25% → 50%). | "estágio", "fase" (colide com as fases da metodologia) | R-07 (`stepWeights`) |
| **julgamento** | Uma avaliação das métricas coletadas que produz um veredito. Ocorre a cada intervalo. | "análise", "check" | R-02 ("canary judgment") |
| **veredito** | Resultado de um julgamento sobre uma métrica: `Pass` / `High` / `Low` / `Nodata`. | "resultado", "status" | R-02 |
| **score** | Agregação dos vereditos em número de 0 a 100: `(Pass / Total) × 100`, excluindo `Nodata`. | "nota", "pontuação" | R-02, R-04 |
| **promoção** | Avançar o canário para o próximo passo, ou, no último, torná-lo a estável. | "deploy", "release" | R-07 |
| **rollback** | Devolver 100% do peso à estável e encerrar o canário como reprovado. | "revert", "abort", "rollout back" | R-06, R-07 |
| **falha** | Um julgamento cujo veredito reprova o canário. Contada no **total acumulado**. | usar como sinônimo de "erro" | R-06 |
| **erro** | Impossibilidade de *medir* (coletor indisponível, série ausente). Contado em **sucessão**, com reset ao recuperar. | usar como sinônimo de "falha" | R-06 |
| **janela** | Intervalo de tempo cujas amostras alimentam um julgamento. | "período", "intervalo" (reservado para o espaçamento entre julgamentos) | R-03 |
| **intervalo** | Espaçamento de tempo **entre** julgamentos sucessivos. | "janela" | R-07 (`interval`) |
| **direção** | Propriedade de uma métrica: se "menor é melhor" (latência, erro) ou "maior é melhor" (vazão). Determina se `High` ou `Low` reprova. | — | derivado de R-02 |

---

## Nota crítica: **baseline ≠ estável**

Esta é a distinção que a literatura mais insiste e a que mais se perde na
tradução informal.

A "estável" é o que está em produção há tempo indeterminado. O "baseline" é o
ponto de comparação correto para o canário — e, segundo R-03/R-04/R-05, ele deve
ser uma instância **da versão estável recém-implantada no mesmo instante que o
canário**, e não a estável de vida longa.

O motivo é que a estável de vida longa difere da recém-criada em coisas que nada
têm a ver com a versão: cache aquecido, JIT compilado, heap crescido,
balanceamento acomodado. Comparar canário (frio) contra estável (quente) atribui
à *mudança de código* uma diferença que é de *idade da instância* — e o resultado
é um rollback disparado por um defeito que não existe.

Se este projeto comparar o canário diretamente contra a estável de vida longa,
está adotando conscientemente um viés conhecido e documentado. Isso pode ser
legítimo (o substrato é simulado; o simulador pode não modelar aquecimento), mas
precisa ser uma **premissa declarada**, não um descuido. Está aberto na síntese e
é alvo da lente Premissas na Fase 2.

---

## Termos vagos do enunciado, já desambiguados por decisão do operador

| Termo vago | Resolução | Decisão |
|---|---|---|
| "convivendo com a versão estável" | Ambas rodam simultaneamente recebendo **tráfego real** em fatias controladas pelo coordenador | `COEXISTÊNCIA` |
| "rollback automático por métrica" | Decisão por **comparação concorrente** canário vs. estável no mesmo intervalo, não por limiar absoluto fixo | `SINAL DE DECISÃO` |
| "coordenador" | Componente que **decide e age**: governa o peso, dispara julgamentos, promove e reverte | a formalizar no Nível 3 |

Referências (R-01 … R-07): `specs/references/canary-analysis-sources.md`.
