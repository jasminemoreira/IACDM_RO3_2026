# Codec Gorilla — especificação bit a bit

**Fonte única:** R1 = Pelkonen et al., *Gorilla*, PVLDB 8(12), 2015, §4.1.1 e §4.1.2.
Transcrição literal do algoritmo publicado. Todo número abaixo tem origem em R1 —
nada aqui é inferido.

⚠️ Se a implementação divergir deste arquivo, a implementação está errada (S6 Tier 2:
"portar literalmente — mesma estrutura, mesmos nomes, testar com as mesmas entradas").

---

## 1. Modelo de dado

R1 §2: um ponto é uma tupla `(chave string, timestamp inteiro 64 bits, valor double)`.
R1 §4.1: cada ponto não comprimido = **16 bytes** (8 de timestamp + 8 de valor).
Alvo publicado: **1,37 byte por ponto** — redução de **12×** — com bloco de 2 horas (R1 §4.1.2, Fig. 6).

## 2. Timestamps — delta-of-delta (R1 §4.1.1)

### 2.1 Cabeçalho do bloco

- O cabeçalho guarda `t₋₁`, o timestamp inicial, **alinhado a uma janela de 2 horas**.
- O primeiro timestamp do bloco, `t₀`, é gravado como delta de `t₋₁` em **14 bits**.
- Justificativa dos 14 bits (R1, nota de rodapé 1): 2¹⁴ = **16.384 segundos**, "um pouco
  mais de 4 horas". **Se o bloco for maior que 4 horas, este campo tem de crescer.**
  → esta é uma premissa acoplada: `tamanho_bloco ≤ 4h` é condição de corretude do campo de 14 bits.

### 2.2 Pontos subsequentes

Para cada `tₙ`, computar

```
D = (tₙ − tₙ₋₁) − (tₙ₋₁ − tₙ₋₂)
```

e gravar conforme a tabela (R1 §4.1.1, itens b–f — **faixas literais do paper**):

| Condição sobre D | Prefixo | Bits do payload | Total |
|---|---|---|---|
| `D == 0` | `0` | — | **1 bit** |
| `D ∈ [-63, 64]` | `10` | 7 | 9 bits |
| `D ∈ [-255, 256]` | `110` | 9 | 12 bits |
| `D ∈ [-2047, 2048]` | `1110` | 12 | 16 bits |
| caso contrário | `1111` | 32 | 36 bits |

**Notas de fidelidade (armadilhas de implementação):**

1. As faixas são **assimétricas** — `[-63, 64]`, não `[-64, 63]`. Um payload de 7 bits em
   complemento de dois representa `[-64, 63]`; o paper usa `[-63, 64]`. Ou seja: `D = 64`
   entra no bucket de 7 bits e `D = -64` **não**. Isto tem de aparecer no teste, não no comentário.
2. As faixas foram escolhidas empiricamente amostrando séries reais de produção (R1 §4.1.1),
   não derivadas de teoria — não "otimizar" os limites sem re-amostrar dados.
3. Motivação declarada do bucket `[-255, 256]`: "muitos pontos chegam a cada 4 minutos e
   um único ponto faltando ainda cai nessa faixa" (R1 §4.1.1).

### 2.3 Distribuição medida (R1 §4.1.1, Fig. 3 — amostra de 440.000 timestamps reais)

- **~96%** de todos os timestamps comprimem para **1 bit** (D = 0).

Consequência de projeto: o ganho vem do caso `D == 0`. Uma série com jitter de amostragem
degrada a compressão de timestamp de 1 bit para 9 bits por ponto (9×). Isto é um **cenário
de falha a levar para a Fase 2**, não uma nota de rodapé.

## 3. Valores — XOR (R1 §4.1.2)

R1 restringe o valor a **double** (64 bits). Esquema derivado de FPC/[25], simplificado para
comparar apenas com o valor imediatamente anterior.

```
xor = bits(vₙ) ⊕ bits(vₙ₋₁)
```

| Caso | Codificação | Custo |
|---|---|---|
| `xor == 0` (valores idênticos) | `0` | **1 bit** |
| `xor != 0`, bloco de bits significativos **cabe dentro** do bloco anterior (≥ tantos zeros à esquerda **e** ≥ tantos zeros à direita quanto o anterior) | `1` + control `0` + bits significativos | 2 + `len` |
| `xor != 0`, caso geral | `1` + control `1` + **5 bits** (nº de zeros à esquerda) + **6 bits** (comprimento da parte significativa) + bits significativos | 13 + `len` |

O primeiro valor do bloco é gravado **sem compressão** (64 bits).

**Por que 5 e 6 bits:** 5 bits → até 31 zeros à esquerda; 6 bits → até 63 bits de
comprimento significativo. Ambos são exatamente o necessário para um double de 64 bits.

**Estado do codificador:** o esquema usa o valor anterior **e o XOR anterior** (R1 §4.1.2).
`prev_leading` e `prev_trailing` fazem parte do estado do stream — não são locais. Isto
significa que **o decodificador tem de reconstruir o mesmo estado na mesma ordem**: o
bitstream não é seekable ponto a ponto; só o começo do bloco é ponto de entrada.

### 3.1 Distribuição medida (R1 §4.1.2, Fig. 5 — amostra de 1,6 milhão de valores reais)

| Caso | % dos valores | Tamanho médio comprimido |
|---|---|---|
| `0` (idênticos) | ~51% | 1 bit |
| control `10` | ~30% | **26,6 bits** |
| control `11` | ~19% | **36,9 bits** |

Os 13 bits extras do caso `11` (5 + 6 + 2 de flag) são a origem da diferença de 36,9 − 26,6 ≈ 10,3.

R1 §4.1.2: inteiros comprimem especialmente bem porque a posição dos bits 1 após o XOR
tende a ser a mesma na série toda → mesmo número de zeros à direita.

## 4. Tamanho do bloco — trade-off publicado (R1 §4.1.2, Fig. 6)

Curva medida sobre ~2 bilhões de séries em produção, variando o bucket de 0 a 240 minutos:

- Blocos **maiores que 2 horas dão retorno decrescente** de compressão.
- **2 horas ⇒ 1,37 byte/ponto.**
- Contrapartida declarada: consultas de intervalo curto gastam CPU decodificando um bloco
  inteiro. O tamanho de bloco é um **trade-off compressão × latência de leitura**, não um
  parâmetro a maximizar.

**Parâmetro de projeto derivado:** `BLOCO = 2h` com justificativa em R1 Fig. 6.
Limite superior duro: 4h, imposto pelo campo de 14 bits (§2.1).

## 5. Parâmetros de referência da implementação em produção (R8 — Prometheus TSDB)

Prometheus implementa este codec (`chunkenc` XOR). Números úteis como sanidade:

| Parâmetro | Valor | Fonte |
|---|---|---|
| Amostras por chunk (alvo) | **120** (`DefaultSamplesPerChunk`) | R8 |
| Duração do head block | **2 horas** | R8, R12 |
| Bytes/amostra observados | ~1,37 | R8 (confirma R1) |

⚠️ **Divergência conhecida a não copiar por engano:** o encoder de varint do Prometheus usa
buckets diferentes dos de R1 §4.1.1 para o delta-of-delta. Se portarmos "do Prometheus",
não é mais o Gorilla do paper. Escolher **uma** fonte e declarar qual — este projeto usa **R1**.
