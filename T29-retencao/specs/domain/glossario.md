# Glossário de domínio — séries temporais, compressão e retenção

Fase 0, Nível 1 (Domínio). Vocabulário fixado **antes** da arquitetura: os termos abaixo têm
significado técnico preciso na literatura e sinônimos que causam ambiguidade. Onde há risco
de confusão, está marcado.

---

## Vocabulário

| Termo | Entendimento neste projeto | Exemplo | Fonte |
|---|---|---|---|
| **Série temporal** | Sequência de pares `(timestamp, valor)` de uma mesma identidade, ordenada por timestamp | `cpu.load` a cada 60 s | R1 §2 |
| **Ponto / amostra / data point** | Um par `(timestamp, valor)`. Cru = 16 B (8+8) em R1, 12 B (4+8) em Whisper | `(1786470000, 42.5)` | R1, R6 |
| **Resolução / precisão / `secondsPerPoint`** | Intervalo nominal entre pontos consecutivos | 60 s | R6 |
| **Bloco / chunk** | Unidade de compressão e de expiração. Em R1: janela de 2 h; em R8: alvo de 120 amostras | bloco `[14:00, 16:00)` | R1 §4.1.1, R8 |
| **Delta** | `tₙ − tₙ₋₁` (primeira derivada) | 60 | R1 §4.1.1 |
| **Delta-of-delta / double delta** | `(tₙ − tₙ₋₁) − (tₙ₋₁ − tₙ₋₂)` (segunda derivada) | 0 | R1 §4.1.1 |
| **XOR encoding** | Codificar `bits(vₙ) ⊕ bits(vₙ₋₁)` e gravar só a parte significativa | ~51% dos valores → 1 bit | R1 §4.1.2 |
| **Bits significativos (*meaningful bits*)** | Trecho do XOR entre o último zero à esquerda e o primeiro zero à direita | — | R1 §4.1.2 |
| **Compactação (*compaction*)** | Juntar blocos pequenos em blocos grandes, **no mesmo formato**, reindexando | Prometheus: head → bloco persistido | R12 |
| **Compressão** | Reduzir bytes por ponto via codificação | 16 B → 1,37 B | R1 |
| **Downsampling** | Gerar série de resolução menor agregando pontos, e descartar o cru | cru → 5 m → 1 h | R9 |
| **Retenção** | Regra que decide o que deixa de existir e quando | "cru por 15 d, 5 m por 90 d" | R9, R12 |
| **Tier / archive / RRA** | Um nível de resolução com sua própria janela de retenção | RRA 60 s × 1440 pontos | R6, R7 |
| **Função de agregação / consolidation function (CF)** | Como N pontos colapsam em 1 no downsampling | `average`, `sum`, `last`, `max`, `min` | R6 |
| **`xFilesFactor` / `xff`** | Fração mínima de pontos definidos para o agregado ser definido; 0.5 = "mais da metade indefinidos ⇒ resultado indefinido" | 0.5 | R6, R7 |
| **Lossless / lossy** | Sem perda de bit (Gorilla, Chimp, Elf) vs. com perda (downsampling **é** lossy) | — | R1, R2, R3 |
| **Razão de compressão** | Bytes originais ÷ bytes comprimidos, ou bytes/ponto | 12× / 1,37 B por ponto | R1 |

## Sinônimos a evitar (fonte de ambiguidade real)

| Não usar | Usar | Por quê |
|---|---|---|
| "compactar" como sinônimo de "comprimir" | **comprimir** (bytes) vs. **compactar** (juntar blocos) | Em Prometheus/TSDB, *compaction* é a operação de fundir blocos — não é compressão. O enunciado diz "compactador"; isto precisa ser desambiguado (ver abaixo) |
| "arquivar" | **downsample** ou **expirar** | "arquivar" pode significar mover, agregar ou apagar |
| "precisão" | **resolução** para intervalo temporal; **precisão** para float | R6 usa "precision" para intervalo; IEEE-754 usa para mantissa |
| "média" no tier reduzido | **sum + count** | Guardar `average` impede re-agregação (R9 guarda min/max/sum/count) |

## Termos VAGOS do enunciado — a concretizar nesta Fase 0

O enunciado congelado é: *"Compactador de séries temporais com política de retenção e troca
do formato de armazenamento"*. Três ambiguidades a resolver com o operador:

| # | Termo vago | Leituras possíveis | Precisa virar |
|---|---|---|---|
| V1 | "**Compactador**" | (a) comprime bytes (codec); (b) funde blocos (*compaction* do TSDB); (c) ambos | Uma das três, explicitamente |
| V2 | "**Política de retenção**" | (a) expiração destrutiva por tempo/tamanho; (b) downsampling multi-tier; (c) ambas compostas | Uma das três + parâmetros numéricos |
| V3 | "**Troca do formato de armazenamento**" | (a) escolher formato na criação (configurável); (b) migrar dado existente de um formato para outro; (c) suportar N formatos simultâneos atrás de uma interface | Uma das três — muda o número de módulos |

Sem V1–V3 resolvidos, "resolved ambiguities" (peso 15) não pode pontuar.

## Campo teórico e metodologias

| Sub-área | Conteúdo |
|---|---|
| **Disciplinas** | Compressão de dados (codificação de comprimento variável, entropia); representação IEEE-754 de ponto flutuante; sistemas de armazenamento (formatos on-disk, append-only, round-robin); séries temporais (amostragem, agregação, reamostragem) |
| **Conhecimento fundamental aplicável** | IEEE-754 binary64: 1 bit sinal, 11 de expoente, 52 de mantissa — é o que explica **por que** o XOR de valores próximos tem muitos zeros à esquerda (sinal+expoente+topo da mantissa idênticos, R1 §4.1.2). Codificação de prefixo livre (os prefixos `0`/`10`/`110`/`1110`/`1111` de R1 formam um código prefixo) |
| **Metodologias/padrões do domínio** | Nenhum padrão normativo (ISO/RFC) governa compressão de série temporal. O *de facto* é o codec do Gorilla, adotado por Prometheus (R8), InfluxDB e RedisTimeSeries. Para retenção, o *de facto* é o par CF+xff do RRDtool (R7), herdado pelo Whisper (R6) |
| **Ecossistema/ferramentas** | RRDtool, Graphite/Whisper, Prometheus, Thanos, InfluxDB, VictoriaMetrics, TimescaleDB, Parquet/Arrow. Ver `specs/competitors/analise.md` |

## Invariantes de domínio (candidatas a teste na Fase 6)

| # | Invariante | Origem |
|---|---|---|
| I1 | `decode(encode(S)) == S` bit a bit, para todo S — o codec é lossless | R1 (lossless por construção) |
| I2 | Timestamps de uma série são estritamente crescentes dentro de um bloco | pressuposto do delta-of-delta (R1 §4.1.1) |
| I3 | A resolução de um tier de retenção mais longa é divisível pela do tier imediatamente inferior | R6, regra literal |
| I4 | Downsampling é **irreversível**: o cru é descartado | R9 |
| I5 | A retenção efetiva ≥ retenção nominal, por até uma duração de bloco (granularidade de descarte é o bloco) | R12 |
| I6 | Um agregado é indefinido se a fração de pontos definidos < `xFilesFactor` | R6 |
| I7 | Se a retenção de um nível < idade mínima do downsampling seguinte, há **perda silenciosa** de dado | R9 (armadilha documentada) |
