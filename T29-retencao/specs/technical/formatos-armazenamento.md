# Formatos de armazenamento — layouts com bytes exatos

O enunciado exige "troca do formato de armazenamento". Este arquivo levanta os formatos
candidatos com layout verificável, para que a troca seja entre coisas especificadas e não
entre nomes.

---

## F1 — Whisper: slot fixo, round-robin (R6)

Layout completo, com os tamanhos de `struct` do próprio formato:

```
Header
├── Metadata            !2LfL   = 16 bytes   ⚠️ ver correção abaixo
│   ├── aggregationType         4 bytes
│   ├── maxRetention            4 bytes
│   ├── xFilesFactor            4 bytes  (float)
│   └── archiveCount            4 bytes
└── ArchiveInfo[N]      !3L     = 12 bytes cada
    ├── offset                  4 bytes
    ├── secondsPerPoint         4 bytes
    └── points                  4 bytes
Data
└── Point               !Ld     = 12 bytes cada
    ├── timestamp               4 bytes  (unsigned long)
    └── value                   8 bytes  (double)
```

> **CORREÇÃO (achada pela suíte de testes na Fase 6).** Este arquivo dizia **20 bytes**
> para o Metadata. É **16**: `struct.calcsize('!2LfL')` = 4 + 4 + 4 + 4 = 16, e os quatro
> campos listados somam 16. O número 20 veio transcrito de um resumo da documentação em
> vez de calculado do formato de `struct` que a mesma fonte fornecia.
>
> É a **mesma classe de erro** que a Fase 0 já tinha pegado no resumo do paper do Gorilla
> (faixas de bucket divergentes) — e que eu não generalizei na hora. Regra que fica:
> **quando a fonte dá a fórmula E o resultado, a fórmula é a autoridade.**
> O código sempre usou `struct.calcsize()`, então nunca esteve errado; a documentação
> estava, em quatro lugares.

**Propriedades derivadas do layout (não opinião — consequência dos bytes):**

| Propriedade | Consequência |
|---|---|
| Ponto = **12 bytes fixos** | tamanho do arquivo é conhecido na criação: `20 + 12·N + Σ(12 · points_i)` |
| Slot fixo + round-robin | escrita é O(1) por posição calculada; **sem realocação, sem crescimento** |
| Timestamp de **4 bytes** | limite de 2³² s ⇒ **estouro em 2106** (Unix 32 bits unsigned). Limitação real e citável |
| Nenhuma compressão | 12 bytes/ponto contra **1,37** do Gorilla (R1) ⇒ **~8,8×** de diferença |
| Escrita idempotente por slot | reprocessar o mesmo timestamp sobrescreve, não duplica |

## F2 — Bitstream comprimido em blocos, estilo Gorilla (R1, R8)

- Cabeçalho de bloco: timestamp base alinhado a janela de **2h** (R1 §4.1.1).
- Corpo: bitstream de largura variável, **1,37 byte/ponto** medido (R1 §4.1.2).
- Prometheus: chunk com alvo de **120 amostras**, head block de **2h** (R8).

**Propriedade que domina o projeto:** o bitstream é **append-only e sequencialmente
decodificável**. Não há acesso aleatório a um ponto: o estado do decodificador
(`prev_value`, `prev_leading`, `prev_trailing`, `prev_delta`) só existe se todos os pontos
anteriores do bloco foram lidos. Logo:

- leitura de intervalo curto → custo de bloco inteiro (trade-off declarado em R1 §4.1.2);
- edição/remoção de um ponto → reescrita do bloco;
- corrupção de um bit → **perde o resto do bloco**, não um ponto. Isto é um cenário de
  falha para a lente Resilience na Fase 2.

## F3 — Colunar: Parquet (R10)

Encodings relevantes para série temporal, com o suporte de tipo declarado em R10:

| Encoding | Tipos suportados (R10) | Uso |
|---|---|---|
| `DELTA_BINARY_PACKED` | **INT32, INT64** | coluna de timestamp |
| `BYTE_STREAM_SPLIT` | INT32, INT64, FLOAT, DOUBLE, FIXED_LEN_BYTE_ARRAY | coluna de valor |
| `PLAIN` | todos | fallback |
| RLE / bit-packing, dicionário | baixa cardinalidade | coluna de nome de série |

- Codec de compressão default: **Snappy**; alternativa comum: **ZSTD** (R13).
- Razões típicas de 5–10× (R13) — abaixo dos 12× do Gorilla (R1) para este dado específico,
  mas com **acesso por coluna e por row-group**, que o F2 não tem.

## F4 — Arrow IPC (R11)

R11/FAQ, literal: Arrow é **in-memory**, não on-disk; Parquet é para disco. O formato IPC e o
Feather V2 existem como invólucros em disco, "mas são incomuns para armazenamento de
produção". Vantagem: sem custo de desserialização (memory-mapping direto).

⚠️ Escolher Arrow IPC como formato de **arquivamento** é usar a ferramenta contra a
recomendação da própria documentação. Se entrar no projeto, tem de ser como formato de
**troca/leitura**, não de retenção longa.

---

## Matriz de decisão para a "troca de formato"

| | F1 Whisper | F2 Gorilla | F3 Parquet | F4 Arrow IPC |
|---|---|---|---|---|
| Bytes/ponto | **12** (R6) | **1,37** (R1) | ~1–2,5 (5–10×, R13) | ≈ sem compressão (R11) |
| Acesso aleatório a ponto | **sim** (slot fixo) | não | por row-group | sim (mmap) |
| Tamanho previsível | **sim** | não | não | não |
| Downsampling in-place | sim | não (recomprime) | não | não |
| Dependência externa | nenhuma | nenhuma | biblioteca Parquet | biblioteca Arrow |
| Tier S6 | 2 (spec completa) | 2 (spec completa) | **1** (lib madura) | 1 (lib madura) |

**O que faz este projeto ser interessante e não trivial:** F1 e F2 têm **modelos de acesso
incompatíveis** (slot fixo mutável vs. bitstream append-only). A "troca de formato" não é
troca de serializador — é troca de contrato de acesso. Qualquer camada que abstraia os dois
tem de expor o mínimo comum denominador, ou vazar a diferença. **Este é o achado técnico
central da Fase 0 e a pergunta que a Fase 1 tem de responder** (lente Linguistics/Grammar
na Fase 2: dois formatos corretos que produzem comportamentos incompatíveis sob o mesmo
contrato).

## Premissas a validar (não assumir — AP4)

| # | Premissa | Como verificar |
|---|---|---|
| A1 | A plataforma escolhida faz manipulação de bits e IEEE-754 sem perda | escrever e ler um double, comparar bit a bit |
| A2 | Há biblioteca madura de Parquet na plataforma escolhida | verificar antes da Fase 1 (define Tier 1 vs 3) |
| A3 | Timestamp de 4 bytes é aceitável (limite 2106) ou precisamos de 8 | decisão de escopo da Fase 0 |
| A4 | 1,37 byte/ponto é atingível no **nosso** dataset, não só no do Facebook | medir contra `specs/datasets/` — R1 mediu em ODS, dado de monitoração |
