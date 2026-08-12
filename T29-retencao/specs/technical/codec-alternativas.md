# Codecs alternativos ao Gorilla — comparação com números citados

Levantado para que a escolha de codec na Fase 1 seja uma decisão com evidência, e para
que a lente **Scientific** da Fase 2 tenha o que verificar. Nenhum número aqui é estimado.

---

## 1. Chimp (R2 — PVLDB 15(11), 2022, §4.1.5)

Substituto direto do estágio XOR do Gorilla. Mesma família (streaming, sem lookahead).

### Esquema de codificação (transcrição de R2 §4.1.5)

O primeiro valor vai sem compressão. Para os demais, `xor = bits(vₙ) ⊕ bits(vₙ₋₁)`:

**Caso A — `xor` tem mais de 6 zeros à direita:** grava um bit `0`, seguido de:
- control `0`: resultado é zero (valores idênticos)
- control `1`: **3 bits** com o nº de zeros à esquerda, **6 bits** com o comprimento da
  parte significativa, depois os bits significativos

**Caso B — `xor` tem 6 ou menos zeros à direita:** grava um bit `1`, seguido de:
- control `0`: nº de zeros à esquerda é **exatamente igual** ao anterior → grava só os bits significativos
- control `1`: **3 bits** de zeros à esquerda + **6 bits** de comprimento + bits significativos

### Diferenças de projeto frente ao Gorilla

| | Gorilla (R1) | Chimp (R2) |
|---|---|---|
| Bits para zeros à esquerda | **5** (até 31) | **3** (até 8 buckets) |
| Ramo primário do fluxo | XOR é zero? | nº de zeros à direita > 6? |
| Flags | 3 casos (`0`, `10`, `11`) | 4 sequências de flag de 2 bits |

O corte de 5→3 bits vem de **quantizar** o nº de zeros à esquerda em 8 buckets (R2 §4.1.4):
valores próximos são mapeados ao mesmo bucket e passam a "contar como iguais", o que
favorece o ramo control `0` (que omite os 9 bits de metadados). É uma troca deliberada:
perde-se precisão no metadado para ganhar frequência no caso barato.

**Variante de precisão simples:** R2 §4.1.5 diz literalmente — trocar 64 por 32 nas linhas
3, 16, 23, 27 do Algoritmo 2 e 6 por 5 nas linhas 9 e 17. Ou seja, o limiar de "6 zeros à
direita" vira **5** para float32.

### Ganho medido (R2)

- Ganho médio de **0,51 bit por valor** (mecanismo de zeros à esquerda) e **0,95 bit por
  valor** (mecanismo combinado) — R2 §4.1.4.
- Chimp ocupa em média **~50% do espaço** exigido pelas abordagens de streaming do estado
  da arte (R2, abstract).
- **Chimp128:** examina os **128 valores anteriores** e escolhe o melhor como referência de
  XOR, em vez de só o imediatamente anterior (R2 §4.2). Custo: janela de 128 valores em
  memória — **O(128) de estado**, não O(1).

## 2. Elf (R3 — PVLDB 16(7), 2023)

- Melhor razão de compressão em quase todos os datasets testados.
- Melhoria relativa média de **~51%** sobre Gorilla e FPC em séries temporais.
- Melhoria de **47%** sobre Chimp e **12%** sobre Chimp128.
- Pegada de memória **O(1)**, ao contrário do Chimp128.

## 3. Codecs genéricos e de coluna (R10, R13)

| Técnica | Melhor para | Nota |
|---|---|---|
| `DELTA_BINARY_PACKED` (Parquet) | INT32/INT64 — timestamps | R10: suportado só para inteiros |
| `BYTE_STREAM_SPLIT` (Parquet) | FLOAT/DOUBLE | R10: separa os bytes de mesma posição em streams; melhora o trabalho do codec genérico a jusante |
| RLE / bit-packing | valores repetidos, baixa cardinalidade | R10 |
| Dicionário | colunas de baixa cardinalidade (ex.: nome da série) | R13: ~3× em nomes de cidade |
| Simple-8b + RLE | inteiros, timestamps | R13 |
| Snappy / ZSTD | fallback genérico | R13: Parquet default Snappy; razões tipicamente **5–10×** |

## 4. Decisão de projeto proposta (a confirmar na Fase 1)

**Codec primário: Gorilla (R1).** Justificativa por S6/Tier:

- **Tier 2** — algoritmo documentado bit a bit em fonte peer-reviewed, com implementação de
  referência em produção (R8, Prometheus `chunkenc`) e distribuições medidas para validar
  a saída. Portável literalmente.
- Estado O(1), sem janela — cabe num compactador de sessão única.
- É o *baseline* contra o qual R2 e R3 se medem: implementá-lo dá a base de comparação.

**Elf e Chimp128: fora de escopo, não por serem piores — por serem melhores em razão de
compressão a custo de complexidade e (Chimp128) de estado O(128).** Registrar como escopo
negativo explícito na Fase 1, com esta linha como justificativa, e não como omissão.

Risco a levar para a Fase 2 (lente Scientific): se implementarmos "Gorilla" com os buckets
do Prometheus ou com as faixas do resumo R14, o número 1,37 byte/ponto **deixa de ser
comparável** e o critério de acerto perde a âncora.
