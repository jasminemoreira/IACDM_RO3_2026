# Política de retenção — mecanismos estabelecidos e seus parâmetros

Levantado na Fase 0. Existem **duas famílias** de política de retenção na literatura de
produção, e elas não são intercambiáveis. Confundi-las é o erro clássico do domínio.

---

## Família A — Retenção destrutiva (expiração)

Dado mais velho que `T` é **apagado**. Não há dado derivado.

| Sistema | Parâmetro | Valor/forma | Fonte |
|---|---|---|---|
| Prometheus | retenção por **tempo** | `--storage.tsdb.retention.time` | R8, R12 |
| Prometheus | retenção por **tamanho** | `--storage.tsdb.retention.size` | R12 |
| Prometheus | granularidade do descarte | **bloco inteiro**, não amostra | R12 |

**Invariante crítica (R12):** a unidade de expiração é o **bloco**, não o ponto. Um bloco só
é removido quando **todo** o seu intervalo caiu fora da janela de retenção. Consequência: a
retenção real excede a nominal por até uma duração de bloco. Um compactador que apaga
ponto a ponto tem semântica diferente de um que apaga bloco a bloco — e a diferença é
observável pelo usuário.

## Família B — Retenção com downsampling (multi-resolução)

O dado antigo não é apagado: é **agregado** para resolução menor e o original é descartado.
Cada nível ("tier"/"archive"/"RRA") tem sua própria resolução e sua própria janela.

### B.1 RRDtool — origem do conceito (R7)

- Unidade: **RRA** (Round Robin Archive).
- Cada RRA tem uma **consolidation function** (CF) e um **xff** (xFilesFactor).
- Forma: `RRA:AVERAGE:0.5:10:60` → CF=AVERAGE, xff=0.5, 10 PDPs por CDP, 60 linhas.

### B.2 Whisper / Graphite (R6)

Equivalências terminológicas (R6 + doc NAV): "consolidation function" do RRDtool = **aggregation
method** do Whisper. `xff` = **xFilesFactor**.

| Conceito | Especificação | Fonte |
|---|---|---|
| Métodos de agregação | `average` (default), `sum`, `last`, `max`, `min` — **5 métodos** | R6 |
| `xFilesFactor` = 0.5 | "se mais da metade dos valores agregados forem indefinidos, o resultado também é indefinido" | R6 / doc NAV |
| Ordem dos arquivos | do de **maior resolução e menor retenção** para o de **menor resolução e maior retenção** | R6 |
| Propagação | o ponto que chega é escrito em **todos** os arquivos de uma vez: cru no de maior resolução, agregado nos demais | R6 |
| **Regra de validade** | "a precisão de um arquivo de retenção mais longa deve ser divisível pela precisão do arquivo de retenção imediatamente inferior" | R6 |

**Exemplo da regra de validade (R6, literal):** 60s pode preceder 300s (300 ÷ 60 = 5); **180s
não pode preceder 600s** (600 ÷ 180 = 3,33). Esta é uma **invariante de configuração
verificável** — candidata natural a teste negativo na Fase 6.

### B.3 Thanos — números de produção (R9)

| Parâmetro | Valor | Fonte |
|---|---|---|
| Resoluções | **cru**, **5m**, **1h** | R9 |
| Gatilho para gerar bloco 5m | bloco cru com mais de **40 horas** | R9 |
| Gatilho para gerar bloco 1h | bloco 5m com mais de **10 dias** | R9 |
| Agregações preservadas no downsample | **min, max, sum, count** | R9 |
| Retenção por resolução | `--retention.resolution-raw` / `-5m` / `-1h`; `0s` = **guardar para sempre** | R9 |

**Armadilha documentada (R9, literal):** "se a retenção de cada resolução for menor que a
idade mínima para o passo de downsampling seguinte, o dado será apagado antes de o
downsampling poder ser completado". Regra prática do próprio Thanos: a retenção de cada
nível deve ser **maior que o intervalo máximo de datas** do passo seguinte (10 dias no caso
5m→1h).

→ Isto é uma **interação entre retenção e downsampling que produz perda silenciosa de
dado**. Vai para a Fase 2 como cenário de falha (lentes Process/Workflow e Assumptions),
e para a Fase 6 como teste.

**Por que min/max/sum/count e não `average`:** preservar `sum` e `count` permite calcular a
média *depois*, e permite re-agregar níveis sem erro acumulado; guardar `average` direto
destrói a informação necessária para agregar de novo. R9 confirma o mesmo princípio para
histogramas nativos (guarda `counter`, `count`, `sum`; a média é derivada).

## Comparação das duas famílias

| | A — expiração | B — downsampling |
|---|---|---|
| Dado antigo | apagado | agregado, resolução reduzida |
| Perda | total após T | de resolução, não de intervalo |
| Custo de armazenamento | cai a zero | cai por fator = razão de resolução |
| Reversível? | não | não (o cru é descartado) |
| Complexidade | baixa | precisa de CF, xff, regra de divisibilidade, ordem dos tiers |

**Ambas são "política de retenção" no jargão do domínio.** Qual das duas (ou as duas) o
projeto implementa é uma **decisão de escopo da Fase 0**, não um detalhe da Fase 1 — a
diferença muda o número de módulos e o critério de acerto.

## Interação retenção × compressão (a pergunta que o enunciado esconde)

Se o dado é comprimido em **blocos** (R1: bloco de 2h, bitstream não seekable ponto a ponto
— ver `codec-gorilla.md` §3), então:

1. Aplicar retenção por **ponto** exige **descomprimir e recomprimir** o bloco.
2. Aplicar retenção por **bloco** é O(1) — só apaga o bloco (é o que Prometheus faz, R12).
3. Fazer **downsampling** exige sempre descomprimir, agregar e recomprimir.

Esta é a tensão central do projeto e tem de estar explícita na arquitetura da Fase 1.
