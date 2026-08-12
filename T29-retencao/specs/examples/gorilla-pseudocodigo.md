# Implementação de referência para port literal (S6 Tier 2)

**O que é isto:** o ativo que S6 Tier 2 exige — *"portar literalmente: mesma estrutura, mesmos
nomes, testar com as mesmas entradas"*. Transcrição algorítmica de R1 §4.1.1 e §4.1.2, para que
a Fase 5 não invente parâmetro nenhum (antídoto a AP7).

⚠️ Divergência daqui ⇒ a implementação está errada, não a spec. Fonte dos números:
`specs/technical/codec-gorilla.md`, que os transcreve do PDF original.

---

## Encoder de timestamp — R1 §4.1.1, itens (b)–(f)

```
encode_first_timestamp(w, base_ts, t0):
    w.write_bits(t0 - base_ts, 14)        # 14 bits: 2^14 = 16.384 s > 4 h (R1 nota 1)
    state.prev_ts    = t0
    state.prev_delta = 0                  # ver NOTA A

encode_timestamp(w, state, tn):
    delta = tn - state.prev_ts
    D     = delta - state.prev_delta      # delta-of-delta
    if   D == 0:                w.write_bit(0)                                    # 1 bit
    elif -63  <= D <= 64:       w.write_bits(0b10,   2); w.write_bits(D,  7)      # ver NOTA B
    elif -255 <= D <= 256:      w.write_bits(0b110,  3); w.write_bits(D,  9)
    elif -2047 <= D <= 2048:    w.write_bits(0b1110, 4); w.write_bits(D, 12)
    else:                       w.write_bits(0b1111, 4); w.write_bits(D, 32)
    state.prev_ts    = tn
    state.prev_delta = delta
```

**NOTA A:** R1 não declara o `prev_delta` inicial. Com `prev_delta = 0`, o segundo ponto do
bloco tem `D = delta - 0 = delta`, logo cai no bucket **correspondente ao próprio delta**:

| delta do 2º ponto | bucket | custo |
|---|---|---|
| 1 s ou 60 s | `[-63, 64]` | 9 bits |
| 300 s | `[-255, 256]` | 12 bits |
| 3600 s | `1111` | 36 bits |

⚠️ Uma versão anterior deste arquivo afirmava que o segundo ponto "normalmente cai no bucket
de 32 bits" — **falso**, e o erro se propagou para um teste que falhou contra o código
correto. Só deltas acima de 2048 s caem lá. Do terceiro ponto em diante, série regular ⇒
`D = 0` ⇒ 1 bit.

**NOTA B — a armadilha P5:** as faixas do paper são **assimétricas**: `[-63, 64]`, não
`[-64, 63]`. Sete bits em complemento de dois representam `[-64, 63]`, então `D = 64`
**precisa** caber no bucket de 7 bits e `D = -64` **não** cabe. Escrever `D` em 7 bits com a
faixa do paper exige codificar `D` em uma representação que cubra `[-63, 64]` — a mais simples
é gravar `D` como valor de 7 bits em complemento de dois e tratar `64` como caso especial, ou
gravar `D - 1`. **Decida, documente no código e teste os dois extremos.** Não deixe implícito.

## Decoder de timestamp

```
decode_timestamp(r, state):
    if r.read_bit() == 0:  D = 0
    elif r.read_bit() == 0: D = signed(r.read_bits(7))     # prefixo consumido: 10
    elif r.read_bit() == 0: D = signed(r.read_bits(9))     # 110
    elif r.read_bit() == 0: D = signed(r.read_bits(12))    # 1110
    else:                   D = signed(r.read_bits(32))    # 1111
    delta = state.prev_delta + D
    tn    = state.prev_ts + delta
    state.prev_ts, state.prev_delta = tn, delta
    return tn
```

O decoder lê o prefixo **bit a bit** — os prefixos formam um código de prefixo livre
(`0`, `10`, `110`, `1110`, `1111`), então não há ambiguidade.

## Encoder de valor — R1 §4.1.2

```
encode_first_value(w, v):
    w.write_bits(bits64(v), 64)           # primeiro valor SEM compressão
    state.prev_bits  = bits64(v)
    state.prev_lead  = None               # ver NOTA C
    state.prev_trail = None

encode_value(w, state, v):
    x = bits64(v) XOR state.prev_bits
    if x == 0:
        w.write_bit(0)                                        # ~51% dos casos
    else:
        w.write_bit(1)
        lead  = 64 - bit_length(x)
        trail = trailing_zeros(x)
        if state.prev_lead is not None
           and lead >= state.prev_lead and trail >= state.prev_trail:
            w.write_bit(0)                                    # control '10'
            w.write_bits(x >> state.prev_trail,
                         64 - state.prev_lead - state.prev_trail)
        else:
            w.write_bit(1)                                    # control '11'
            w.write_bits(lead, 5)                             # até 31 zeros à esquerda
            w.write_bits(64 - lead - trail, 6)                # comprimento significativo
            w.write_bits(x >> trail, 64 - lead - trail)
            state.prev_lead, state.prev_trail = lead, trail
    state.prev_bits = bits64(v)
```

**NOTA C — o ponto mais fácil de errar:** R1 diz que o esquema usa *"o valor anterior E o XOR
anterior"*. `prev_lead`/`prev_trail` só são atualizados no ramo `11` — no ramo `10` eles
**permanecem**, porque é justamente por caberem na janela anterior que o ramo é barato. Atualizar
no ramo `10` produz um encoder que decodifica errado. Foi medido: nos perfis homogêneos,
`prev_lead`/`prev_trail` estabilizam e 99% dos valores caem no ramo `10`
(`specs/datasets/perfis-de-serie.md` §C3/C4).

**NOTA D — a armadilha que só aparece em dado patológico (achada no micro-check S7 da Fase 5):**
o campo de comprimento tem 6 bits, que representam 0..63, mas **o comprimento significativo
pode ser 64** — quando o XOR tem o bit 63 **e** o bit 0 setados. Caso mínimo:

```
-inf (0xFFF0000000000000) XOR 5e-324 (0x0000000000000001) = 0xFFF0000000000001
  → lead = 0, trail = 0, significante = 64
```

Gravar 64 em 6 bits trunca para 0 e o decodificador lê comprimento zero. R1 não fecha essa
codificação — é a mesma classe de lacuna das faixas assimétricas. **Solução adotada: gravar
`significant - 1`, cobrindo 1..64** (o comprimento de um XOR não-zero é sempre ≥ 1, então 0
nunca foi valor legítimo). Um codec com este bug **passa em todos os perfis realistas** e só
quebra em dado patológico — por isso `-inf` seguido de subnormal é teste obrigatório de CA-1.

## Distribuições esperadas — critério de fidelidade ao paper (R1 Fig. 3 e 5)

| Caminho | % esperado | Custo médio |
|---|---|---|
| Timestamp `D == 0` | **~96%** | 1 bit |
| Valor `x == 0` | **~51%** | 1 bit |
| Valor control `10` | **~30%** | 26,6 bits |
| Valor control `11` | **~19%** | 36,9 bits |
| Total, bloco de 2 h | — | **1,37 B/ponto** |

⚠️ Esses percentuais são de um universo de séries **heterogêneas** de produção. A sondagem da
Fase 0 mediu séries **individuais e homogêneas** e obteve 0% no ramo `11` após os primeiros
pontos — diferença do método de amostragem, **não** do algoritmo. Não "corrija" o codec por
causa disso.

## Layout de F1 — R6, formatos de `struct` literais

```
Metadata     '>2LfL'  = 16 B : aggregationType, maxRetention, xFilesFactor, archiveCount
ArchiveInfo  '>3L'    = 12 B : offset, secondsPerPoint, points
Point        '>Ld'    = 12 B : timestamp (4 B), value (8 B)
```

Big-endian (`>`) fixo — **nunca** ordem nativa (armadilha P4).

**Validade de slot (E4 de V(3)):** a posição de um ponto de timestamp `t` num archive é
`((t // spp) % points)`, e o slot é **válido apenas se** o timestamp gravado nele for igual a
`t - (t % spp)`. É assim que o Whisper distingue dado de lixo, e é por isso que a volta do
round-robin **é** a expiração — não há dois mecanismos.

## Regra de alinhamento (LIN-07 de V(3))

```
is_aligned(ts, spp)  :=  ts % spp == 0          # época Unix
align_down(ts, spp)  :=  ts - (ts % spp)        # é o 'interval' do Whisper
```

Vale para os dois formatos. F1 **exige** alinhamento (`aligned_writes_required=True`) e
**rejeita** o que não está alinhado; F2 aceita qualquer timestamp monotônico. Nenhum dos dois
quantiza em silêncio.

## Ordem de verificação sugerida na Fase 5 (S7)

1. `bitstream`: escrever e ler campos de 1..64 bits, incluindo valor com o bit 63 setado (P1).
2. `gorilla-codec` timestamps: os 5 buckets + `D = 64` e `D = -64` (P5).
3. `gorilla-codec` valores: `x == 0`, ramo `10`, ramo `11`, e uma sequência que force o ramo
   `10` **depois** do `11` (NOTA C).
4. Round-trip com os casos-limite IEEE-754 comparando **bytes**, nunca `==` (P2).
5. Só então os formatos.
