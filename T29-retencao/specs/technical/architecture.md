# Arquitetura — T29 Compactador de séries temporais

Fase 1, iteração 1. **V(1)**

Padrões aprovados pelo operador: **Hexagonal (Ports & Adapters)** · **KISS+YAGNI** · **SOLID**
· **single-threaded declarado** · GoF **Strategy** e **Iterator/generator** · Fowler
**Transaction Script** (domínio) e **Repository + Data Mapper** (dados).

Plataforma: **Python 3.12, só stdlib** (`numpy` apenas no gerador de dataset; `pytest` só em teste).

---

## V(1) — Decomposição em módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | bitstream | Escrever/ler bits individuais e campos de largura arbitrária, mascarando em 64 bits | `BitWriter.write_bits(value:int, n:int)`, `.write_bit(b)`, `.to_bytes()->bytes`; `BitReader(data).read_bits(n)->int`, `.read_bit()->int`, `.eof()->bool` | — |
| M-02 | gorilla-codec | Codificar/decodificar UM ponto no esquema de R1 §4.1.1 (delta-of-delta) + §4.1.2 (XOR), mantendo o estado do stream | `CodecState(prev_ts, prev_delta, prev_bits, prev_lead, prev_trail)`; `encode_first(w, base_ts, t, v)`; `encode_point(w, st, t, v)`; `decode_first(r, base_ts)->(t,v)`; `decode_point(r, st)->(t,v)` | bitstream |
| M-03 | block | Um bloco de 2 h: header com `base_ts` alinhado, corpo append-only, iteração sequencial | `Block.open(base_ts)->Block`; `.append(t, v)`; `.points()->Iterator[Point]`; `.to_bytes()`, `Block.from_bytes(b)`; const `BLOCK_SECONDS=7200`, `MAX_BLOCK_SECONDS=14400` | bitstream, gorilla-codec |
| M-04 | series | Entidades e invariantes do domínio, sem I/O | `Point(ts:int, value:float)`; `TierSpec(seconds_per_point, retention_seconds, aggregation, x_files_factor)`; `Aggregate(ts, min, max, sum, count)`; `check_monotonic(points)` (I2) | — |
| M-05 | retention | Validar a configuração de tiers e COMPUTAR o plano de retenção (função pura, sem I/O) | `validate(tiers:list[TierSpec])` (levanta em I3/I6/I7); `plan(tiers, now, tier_state)->RetentionPlan{downsample:[(src,dst,range)], expire:[(tier, before_ts)]}` | series |
| M-06 | downsampler | Agregar um stream de pontos de uma resolução para outra, preservando min/max/sum/count e honrando `xFilesFactor` | `aggregate(points:Iterator[Point], src_res, dst_res, fn:str, xff:float)->Iterator[Aggregate]`; `AGGREGATIONS={average,sum,last,max,min}` (Strategy) | series |
| M-07 | store-port | O CONTRATO de armazenamento — mínimo comum entre formatos, com as diferenças declaradas em vez de vazadas | `Store` (Protocol): `capabilities()->Capabilities{random_access, mutable_slots, ts_bits, quantized}`; `write(series, tier, points:Iterator[Point])->WriteReport{written, rejected, reasons}`; `read(series, tier, t_from, t_to)->Iterator[Point]`; `tiers(series)->list[TierSpec]`; `expire(series, tier, before_ts)->int` | series |
| M-08 | store-f1 | Data Mapper do formato de slot fixo (R6): Metadata 16 B, ArchiveInfo 12 B, Point 12 B, big-endian | implementa `Store`; `capabilities()` → `random_access=True, mutable_slots=True, ts_bits=32, quantized=True` | store-port, series |
| M-09 | store-f2 | Data Mapper do formato de bitstream em blocos de 2 h (R1) | implementa `Store`; `capabilities()` → `random_access=False, mutable_slots=False, ts_bits=64, quantized=False` | store-port, block |
| M-10 | migrator | Migrar um acervo de um `Store` para outro, detectando perda ANTES de escrever | `precheck(src:Store, dst:Store)->list[LossRisk]`; `migrate(src, dst, series, allow_lossy=False)->MigrationReport{read, written, rejected, lossless:bool}` | store-port |
| M-11 | dataset-gen | Gerar os perfis de série de ground truth, determinístico por seed | `generate(profile:str, n:int, seed:int)->Iterator[Point]`; perfis: `gauge-stable, counter, temp-1dec, float-noise, jitter, gaps, ieee-edge` | series |
| M-12 | cli | Adaptador de entrada (argparse) + os 6 Transaction Scripts dos casos de uso UC-1..UC-6 | `tsz ingest`, `tsz read`, `tsz retain`, `tsz migrate`, `tsz validate-config`, `tsz report`, `tsz gen-dataset` | todos |

**12 módulos** — dentro dos 8–12 do enunciado.

### Por que `gorilla-codec` é UM módulo e não dois

Separar timestamp e valor pareceria mais SRP, mas o **estado do encoder é compartilhado e por
bloco**: `prev_delta` (timestamp) e `prev_lead`/`prev_trail` (valor) avançam juntos, ponto a
ponto, e nenhuma das metades é utilizável isolada — não existe "bloco Gorilla só de
timestamps". Dividir criaria uma costura de estado mutável entre dois módulos, que é
acoplamento pior do que o que a divisão evitaria. A responsabilidade única é *"codificar um
stream de pontos no esquema de R1 §4.1"*.

---

## As 4 perguntas que a arquitetura tem de responder

### 1. Decomposição — onde estão as fronteiras

Três anéis, com dependência apenas para dentro:

```
      ┌──────────────────────── cli (M-12) ─────────────────────────┐  adaptador de entrada
      │   6 Transaction Scripts: ingest read retain migrate ...     │
      └──────┬───────────────────────┬────────────────┬─────────────┘
             ▼                       ▼                ▼
   ┌─── retention (M-05) ──┐  ┌─ downsampler ─┐  ┌─ migrator (M-10) ─┐  núcleo (sem I/O)
   │  validate + plan      │  │   (M-06)      │  │ precheck + migrate│
   └───────────┬───────────┘  └───────┬───────┘  └─────────┬─────────┘
               └──────────────────────┼────────────────────┘
                                      ▼
                          ┌─ store-port (M-07) ─┐               A PORTA
                          └──────┬───────┬──────┘
                                 ▼       ▼
                    store-f1 (M-08)   store-f2 (M-09)           adaptadores de saída
                          │                 └── block (M-03) ── gorilla-codec (M-02) ── bitstream (M-01)
                          └─────────────────── series (M-04) ◄── (usado por todos)
```

A fronteira **codec ↔ política** é a mesma que os 6 sistemas estudados respeitam sem exceção
(`specs/competitors/analise.md` §2): o codec não sabe de retenção, a retenção não sabe de
codec, e a interface entre eles é o `Store`. Isso não é preferência — é o padrão observado.

`retention` e `downsampler` são **funções puras sem I/O**: recebem config/streams e devolvem
plano/agregados. Toda escrita passa pelo `cli`, via porta. Consequência: os dois módulos com a
lógica de domínio mais delicada (invariantes I3/I6/I7 e `xFilesFactor`) são testáveis sem
tocar disco.

### 2. Interfaces — e a decisão que o achado da Fase 0 exigia

A porta `Store` (M-07) é onde F1 e F2 se encontram, e ela toma **três decisões explícitas**:

**(a) O contrato expõe apenas iteração sequencial.** `read()` devolve `Iterator[Point]`. Não
existe `get(ts)` na porta. O acesso aleatório de F1 é otimização interna, **não** parte do
contrato — porque F2 não pode honrá-lo (o estado do decodificador exige leitura sequencial do
bloco, R1 §4.1.2). O mínimo comum é o contrato; a capacidade extra não vaza.

**(b) As diferenças são DECLARADAS, não escondidas.** `capabilities()` devolve
`{random_access, mutable_slots, ts_bits, quantized}`. Quem precisa saber, pergunta. Um
`Store` não finge ser o outro.

**(c) `write()` devolve `rejected`, não engole.** F1 não pode representar todo ponto que F2
aceita (timestamp quantizado no slot, 4 bytes ⇒ teto 2106, dois pontos no mesmo intervalo
colidem). Em vez de sobrescrever em silêncio, `WriteReport.rejected` conta e `reasons`
explica.

Sobre a assimetria da migração (achado registrado na Fase 0): `migrator.precheck()` compara
`capabilities()` de origem e destino **antes de escrever**. Se o destino é mais restritivo,
devolve os `LossRisk`. Política: **aborta por padrão**; `--allow-lossy` prossegue; e o
`MigrationReport.lossless` sempre diz o que aconteceu. Ou seja, `F1→F2` passa direto e
`F2→F1` exige consentimento explícito. **A decisão da Fase 1 é (b) da alternativa registrada
na Fase 0: declarar a perda e rejeitar, não restringir F2 na escrita.** Restringir F2 ao
domínio de F1 puniria o formato bom por causa do limitado.

### 3. Premissas — o que o sistema assume como verdadeiro

| # | Premissa | Origem / estado |
|---|---|---|
| P-A1 | Python faz round-trip `double ↔ uint64` bit-exato, inclusive `-0.0`, `NaN` com payload, subnormais | ✅ **verificado por execução** (`viabilidade-plataforma.md`) |
| P-A2 | **Escritor único.** Nenhum outro processo escreve o mesmo acervo simultaneamente | ⚠️ declarada, **não** garantida — sem lock, sem WAL. Escolha do operador na Fase 1 |
| P-A3 | Uma série = um acervo identificado por nome; sem índice de labels nem cardinalidade | ⚠️ premissa aceita por default na Fase 0 (A5) |
| P-A4 | Timestamps de entrada são estritamente crescentes (I2); fora de ordem é **erro**, não é reordenado | declarada — `series.check_monotonic` |
| P-A5 | Bloco de 2 h ≤ 4 h, teto imposto pelo primeiro delta de 14 bits (R1 nota 1) | ✅ verificado em R1; `MAX_BLOCK_SECONDS` existe para falhar alto |
| P-A6 | Resolução de ingestão default 60 s, configurável | ⚠️ default aceito na Fase 0, sem confirmação explícita |
| P-A7 | O disco não corrompe bytes. Um bit trocado em F2 perde **o resto do bloco**, não um ponto | declarada — sem checksum. Cenário para a lente Resilience |
| P-A8 | Todo o acervo de uma série cabe em memória durante a migração? **NÃO** — a migração é streaming ponto a ponto via `Iterator` | decisão de projeto (Iterator/generator), não premissa |
| P-A9 | `xFilesFactor` default 0.5 (R6/R7) e agregados preservados são min/max/sum/count (R9) | ✅ com fonte |
| P-A10 | A razão de compressão depende do perfil da série, não do algoritmo — nenhum limiar é prometido | ✅ **medido** (`perfis-de-serie.md`); é o motivo da forma de CA-4 |

**P-A2, P-A3, P-A6 e P-A7 são as premissas frágeis** e estão nomeadas de propósito: são o
alvo esperado da lente Assumptions na Fase 2. Declarar é o antídoto a AP4.

### 4. Escopo negativo — o que o sistema deliberadamente NÃO faz

Herdado da Fase 0: Parquet/Arrow · Chimp/Chimp128/Elf · *compaction* (fusão de blocos) ·
índice de séries e cardinalidade de labels · concorrência, WAL e durabilidade contra crash ·
servidor/API/rede · linguagem de consulta · throughput como requisito · compressão *lossy* de
valores · retenção puramente destrutiva por tamanho.

Novos, decididos nesta fase:

| Item | Razão |
|---|---|
| `get(ts)` / acesso aleatório na porta `Store` | F2 não pode honrá-lo. Pôr na porta seria mentir sobre o contrato |
| Migração *lossy* silenciosa | `precheck` aborta; `--allow-lossy` é consentimento explícito |
| Lock de arquivo / detecção de escritor concorrente | operador escolheu "single-threaded declarado" em vez de "+ lock". Vira premissa P-A2 auditável |
| Checksum / detecção de corrupção | fora dos três eixos do enunciado. Registrado em P-A7 como risco conhecido |
| Reordenar entrada fora de ordem | I2 é invariante: fora de ordem é erro. Reordenar seria esconder um problema do produtor do dado |
| Backfill / reescrita de bloco fechado | F2 é append-only por construção (R1). Permitir isso exigiria descomprimir+recomprimir, que é o custo que a arquitetura evita |

---

## Granularidade (E = I₀/C)

Cada módulo é implementável numa interação única com apenas seu contrato + as specs citadas:

| module | contexto necessário | Tier S6 |
|---|---|---|
| bitstream | nada além da armadilha P1 | 3 (trivial) |
| gorilla-codec | `codec-gorilla.md` §2 e §3 + interface de `bitstream` | **2** |
| block | `codec-gorilla.md` §2.1, §4 | **2** |
| series | `glossario.md` (I2) | 3 (trivial) |
| retention | `politica-retencao.md` §B.2, §B.3 (I3, I6, I7) | **2** |
| downsampler | `politica-retencao.md` §B.3 | **2** |
| store-port | este documento §2 | 3 (trivial) |
| store-f1 | `formatos-armazenamento.md` §F1 (bytes exatos) | **2** |
| store-f2 | `formatos-armazenamento.md` §F2 + `block` | **2** |
| migrator | `viabilidade-implementacao.md` §migrador | 3 |
| dataset-gen | `perfis-de-serie.md` | 1 |
| cli | interfaces acima + `criterios-aceitacao.md` | 1 (argparse) |

Nenhum módulo precisa do **código** de outro — só da interface. É o que permite uma sessão por
módulo na Fase 5 (antídoto a AP3).

## Rastreabilidade caso de uso → módulos

| UC | Script no `cli` | Módulos exercitados |
|---|---|---|
| UC-1 ingerir e comprimir | `ingest` | series → store-f1/f2 → block → gorilla-codec → bitstream |
| UC-2 ler intervalo | `read` | store-f1/f2 → block → gorilla-codec → bitstream |
| UC-3 aplicar retenção | `retain` | retention → downsampler → store-port |
| UC-4 migrar formato | `migrate` | migrator → store-f1 + store-f2 |
| UC-5 validar config | `validate-config` | retention |
| UC-6 medir e reportar | `report` | store-port + dataset-gen |
| (ground truth) | `gen-dataset` | dataset-gen |

Todos os 12 módulos aparecem em pelo menos um caso de uso. Nenhum módulo órfão.

---
---

# V(2) — Resposta unificada à crítica da Iteração 1

Fase 3, iteração 1. Responde aos 68 achados (60 defeitos distintos) de
`specs/design/coverage-matrix.md` §Iteração 1. **V(1) acima permanece intacta** — um achado da
iteração 1 pode nomear um módulo que V(2) removeu, e a rastreabilidade tem de sobreviver.

## As cinco decisões que respondem a tudo

A crítica encontrou 60 defeitos, mas eles não são 60 problemas independentes. As duas
concentrações (`cli` 14 achados/8 lentes, `retention` 12/9) e os três padrões sistêmicos
colapsam em cinco decisões — e **quatro delas removem** estrutura:

### D1 — `Aggregate` deixa de existir. Um tier é uma série de `Point`.
*Resolve: SCI-01, SCI-02, IMP-04, LIN-05, SUS-03.*

SCI-02 era uma contradição real entre as fontes: R6 fixa um valor de 8 bytes por slot em F1,
R9 preserva quatro agregados. A leitura correta de R6 desfaz o impasse — **o Whisper guarda UM
valor por slot e o método de agregação no header** (`aggregationType`), não os quatro
agregados. Os quatro agregados de R9 são propriedade do formato do Thanos, não do domínio.

Consequência: `Aggregate(ts,min,max,sum,count)` é eliminado. Um tier derivado é uma série de
`Point` cujo valor foi produzido pelo método declarado em `TierSpec.aggregation` (os cinco de
R6). Quem quiser min *e* max configura dois tiers. **Um tipo a menos atravessando a porta, um
modelo de agregação em vez de dois.**

### D2 — Cascata permitida, mas `average` só é derivável do CRU.
*Resolve: SCI-01 (raiz), SCI-03, e sustenta D1.*

D1 elimina `Aggregate`, o que levanta a objeção óbvia: sem `sum`+`count`, derivar 1h a partir
de 5m acumula erro de re-agregação — o motivo declarado pelo qual R9 guarda quatro agregados.

A resposta é aritmética, não um meio-termo. Dos cinco métodos de R6, **quatro são associativos
sob re-agregação**: `min(min(a),min(b)) = min(a∪b)`, idem `max`, `sum` é somável e `last` de
`last`s é o `last`. **Só `average` não é** — e é exatamente por causa dele que R9 precisa de
`sum`+`count`.

Regra de V(2): **cascata é permitida; um tier com `aggregation='average'` só pode ser derivado
do tier cru.** `retention.validate` recusa uma configuração que alimente um tier a partir de um
tier `average`. Assim a cascata sobrevive (o cru não precisa ser retido por 10 dias para que o
tier de 1h exista) e D1 permanece correta com um valor por ponto.

Descartada explicitamente a alternativa "derivar tudo do cru": ela eliminaria a cadeia de
comparações de I7, mas forçaria `retention_seconds(cru) ≥ min_age(tier mais grosseiro)` —
com os números de R9, guardar o cru por 10 dias, o que briga com o propósito do produto.
**A simplificação teria custado a função.**

Consequência para I7/SCI-03: a invariante permanece uma cadeia, mas agora **formalizada e
verificável** (em V(1) o campo nem existia):
`retention_seconds(tier_i) ≥ min_age_seconds(tier_{i+1}) + seconds_per_point(tier_{i+1})`
para todo par adjacente — que é precisamente a regra de bolso do Thanos, escrita como código.

### D3 — `tier_state` é uma marca d'água. Um inteiro por tier, no header do acervo.
*Resolve: IMP-03, ASM-02, PRC-01, CTL-01, CTL-02, CTL-03, LIN-06.*

O vazio de onde nasciam quatro críticos: `retention.plan()` recebia `tier_state` que ninguém
modelava. V(2) define `TierState(derived_through_ts)` — **um inteiro**, persistido no header do
acervo (a mesma fonte de verdade que o dado, logo não pode divergir dele: ASM-02).

`retain` deriva apenas o intervalo `(derived_through_ts, floor(now) − min_age]`. Isso torna a
operação **idempotente por construção** (PRC-01, CTL-01: rodar duas vezes não agrega duas
vezes) e define a borda (CTL-02: `now` é truncado para `seconds_per_point`, intervalos são
semiabertos). `retention_seconds` conta a partir de `floor(now)`, declarado (LIN-06).

### D4 — O contrato da porta especifica o COMPORTAMENTO, não só a assinatura.
*Resolve: LIN-01, LIN-02, LIN-03, LIN-04, MIG-02, MIG-03, REG-01, REG-02, ARQ-03, ARQ-04.*

A Fase 1 declarou *capacidades* e achou que resolvia; a lente Linguistics mostrou que a
ambiguidade estava nas *operações*. V(2) fecha cada uma:

| Ambiguidade | Regra de V(2) |
|---|---|
| ts não alinhado a `seconds_per_point` (LIN-01) | **Nenhuma implementação quantiza.** Se `capabilities().aligned_writes_required`, o ponto é **rejeitado** com motivo. Comportamento uniforme; a *pré-condição* difere e é declarada |
| ts duplicado (LIN-02, MIG-03) | **Erro em ambas.** F1 não sobrescreve, F2 não grava duas vezes. `rejected` + motivo |
| borda de `read` (LIN-03) | **Semiaberto `[t_from, t_to)`**, declarado |
| unidade de `expire` (LIN-04, REG-01) | `ExpireReport{points_removed, blocks_removed, effective_before_ts}`. `effective_before_ts` **é** a invariante I5: para F2 ele é alinhado ao bloco, e o contrato diz isso |
| `precheck` grosseiro (MIG-02) | `Capabilities` troca `ts_bits` por `min_ts`/`max_ts`/`aligned_writes_required`; a compatibilidade é verificada **contra os dados**, não contra uma flag ⇒ acaba o falso positivo que abortava F2→F1 sem perda |
| campo morto (ARQ-03) | `random_access` **removido** de `Capabilities`: não era alcançável pelo contrato |
| semântica de formato no migrador (ARQ-04) | `store-port.check_compatibility(src_caps, dst_caps, data_range)` — o conhecimento volta para quem define o contrato |
| CA-4 não computável (REG-02) | `WriteReport` ganha `bytes_written` |

### D5 — Dois interesses transversais ganham dono; o módulo-deus perde responsabilidade.
*Resolve: ARQ-01, ARQ-02, IMP-05, RES-02, RES-03, RES-05, PRC-02, PRF-03, GOV-01, GOV-02, GOV-03, OBS-01, OBS-02, OBS-03, SEC-01, SEC-05, RES-01, RES-04.*

- **Atomicidade sem módulo novo:** `store-port` passa a expor `atomic_write(path, writer_fn)`
  (temporário + `fsync` + `rename`), de uso obrigatório pelos dois mappers. ~15 linhas no
  módulo que já é dono do contrato.
- **Auditoria ganha módulo:** `journal` — log append-only por acervo, uma linha por operação
  mutante, com o relatório serializado. É *mecanismo*, não *feature* (a distinção que a Fase 3
  exige). Mata 6 defeitos sozinho.
- **`cli` deixa de ser módulo-deus:** os 6 Transaction Scripts saem para `usecases`, que é
  onde passa a viver a **ordem obrigatória de operações** que RES-05/PRC-02 exigiam:
  `derivar → gravar → verificar → avançar a marca d'água → expirar`. Expirar o cru antes de
  confirmar o agregado deixa de ser possível. `cli` volta a ser o que o Hexagonal manda: um
  adaptador de argparse.
- **Integridade no header do bloco:** `n_points` + `crc32` (stdlib `zlib`) tornam a corrupção
  **detectável** (RES-01, OBS-01) e o truncamento **distinguível** de um bloco válido (RES-04).
- **Caminho sanitizado num lugar só:** o acervo é um diretório; nome de série validado contra
  `^[A-Za-z0-9._-]+$` e nunca concatenado como caminho (SEC-01, SEC-05).

## V(2) — Decomposição em módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | bitstream | Escrever/ler bits e campos de largura arbitrária sobre `bytearray` + offset de bit, mascarando em 64 bits e limitado pelo comprimento | `BitWriter.write_bits(value:int, n:int)`, `.to_bytes()`; `BitReader(data).read_bits(n)->int`, `.bits_left()->int` (leitura além do fim é erro, não padding) | — |
| M-02 | gorilla-codec | O codec de R1 §4.1 **e o bloco que é sua unidade de estado**: header (`base_ts`, `block_seconds`, `n_points`, `crc32`), corpo append-only, iteração sequencial | `Chunk.open(base_ts, block_seconds)`; `.append(ts, value)`; `.points()->Iterator[Point]`; `.to_bytes()`, `Chunk.from_bytes(b)` (verifica crc32 e n_points); consts `BLOCK_SECONDS=7200`, `MAX_BLOCK_SECONDS=14400` | bitstream, series |
| M-03 | series | **Todos os tipos que atravessam interfaces** + invariantes | `Point(ts:int, value:float)`; `TierSpec(seconds_per_point, retention_seconds, aggregation, x_files_factor, min_age_seconds)`; `TierState(derived_through_ts)`; `ArchiveHeader(format_version, block_seconds, created_at, writer_version, series_name, tiers, tier_states)`; `validate_stream(points, expect_aligned_to=None)`; `validate_series_name(name)` | — |
| M-04 | retention | Validar config e computar o plano — função pura, sem I/O, agora com estado modelado | `validate(tiers:list[TierSpec])` (divisibilidade R6, `xff∈[0,1]`, e a invariante única de D2); `plan(tiers, tier_states, now)->RetentionPlan{derive:[(tier, t_from, t_to)], expire:[(tier, before_ts)]}` (idempotente: deriva só após a marca d'água) | series |
| M-05 | downsampler | Agregar do tier CRU para um tier derivado, produzindo `Point` alinhados | `aggregate(points:Iterator[Point], src_res, dst_res, fn:str, xff:float)->Iterator[Point]`; `AGGREGATIONS={average,sum,last,max,min}` (os 5 de R6, Strategy) | series |
| M-06 | store-port | O contrato **com comportamento especificado** + o núcleo compartilhado de escrita e de compatibilidade | `Store` (Protocol): `capabilities()->Capabilities{mutable_slots, min_ts, max_ts, aligned_writes_required}`; `header(series)->ArchiveHeader`; `write(series, tier, points)->WriteReport{written, rejected, reasons, bytes_written}`; `read(series, tier, t_from, t_to)->Iterator[Point]` **semiaberto**; `expire(series, tier, before_ts)->ExpireReport{points_removed, blocks_removed, effective_before_ts}`; `set_tier_state(series, tier, state)`. Helpers: `atomic_write(path, writer_fn)`, `check_compatibility(src_caps, dst_caps, data_range)->list[LossRisk]` | series |
| M-07 | store-f1 | Data Mapper do slot fixo (R6): Metadata 16 B, ArchiveInfo 12 B, Point 12 B, big-endian, header validado contra o tamanho do arquivo | implementa `Store`; `capabilities()` → `mutable_slots=True, min_ts=0, max_ts=2**32-1, aligned_writes_required=True` | store-port, series |
| M-08 | store-f2 | Data Mapper do bitstream: arquivo = `ArchiveHeader` + sequência de chunks, cada um prefixado por `(base_ts, byte_length, n_points, crc32)` — o prefixo **é** o índice de salto | implementa `Store`; `capabilities()` → `mutable_slots=False, min_ts=-2**63, max_ts=2**63-1, aligned_writes_required=False` | store-port, gorilla-codec |
| M-09 | journal | Trilha append-only por acervo: uma linha por operação mutante, com comando, horário, contadores e o relatório | `append(acervo, op:str, report:dict)`; `read(acervo)->Iterator[dict]` | — |
| M-10 | dataset-gen | Os 7 perfis de ground truth, **só stdlib** (`random` com seed explícita) | `generate(profile:str, n:int, seed:int)->Iterator[Point]`; perfis: `gauge-stable, counter, temp-1dec, float-noise, jitter, gaps, ieee-edge` | series |
| M-11 | usecases | Os 7 Transaction Scripts, e **a ordem obrigatória de operações** do `retain` | `ingest(...)`, `read(...)`, `retain(..., dry_run)`, `migrate(src, dst, allow_lossy, dry_run)`, `validate_config(...)`, `report(...)`, `info(...)` — cada um devolve um relatório e chama `journal.append` | retention, downsampler, store-port, journal, series |
| M-12 | cli | Adaptador de argparse: parsing, `--dry-run`, `--verbose`, formatação de saída. **Nenhuma lógica de domínio** | `tsz ingest|read|retain|migrate|validate-config|report|info|gen-dataset` | usecases |

**12 módulos** — mesma contagem de V(1). `block` foi absorvido por `gorilla-codec` e `migrator`
por `usecases`; entraram `journal` e `usecases`.

### Por que `block` foi absorvido por `gorilla-codec` (resolve ARQ-05)

`CodecState` era estado mutável atravessando a fronteira `block` ↔ `gorilla-codec` — o mesmo
acoplamento que a fusão de ts-codec+value-codec havia evitado, reaparecendo uma fronteira
acima. O bloco **é** a unidade de estado do codec: `base_ts`, `prev_delta`, `prev_lead`,
`prev_trail` nascem e morrem juntos. Juntá-los resolve ARQ-05 **por estrutura, não por
disciplina**, e MEC-04 de graça (`block_seconds` passa a ser gravado pelo mesmo módulo que o
usa).

### Por que `migrator` foi absorvido por `usecases`

Com MIG-01 resolvido (a migração **nunca remove a origem**: escreve num acervo novo e o
operador apaga a mão — rollback é a origem continuar lá, zero mecanismo) e ARQ-04 resolvido
(`check_compatibility` volta para `store-port`), o que restava do migrador era *ler por um
Store, escrever por outro, comparar contagens, registrar no journal*: um Transaction Script.

## Contabilidade de complexidade (AP2 — cada iteração tem de SIMPLIFICAR)

| Dimensão | V(1) | V(2) | |
|---|---|---|---|
| Módulos | 12 | **12** | igual |
| Tipos atravessando a porta | `Point` + `Aggregate` | **`Point`** | −1 |
| Modelos de agregação | 2 (5 métodos R6 + 4 agregados R9) | **1** | −1 |
| Regra de re-agregação | implícita (e incorreta com 1 valor/tier) | **explícita: `average` só do cru** | corrigida |
| Dependências externas | `numpy` | **nenhuma** | −1 |
| Campos de `Capabilities` | 4 (um morto) | 4 (nenhum morto) | igual, mais preciso |
| Comportamentos silenciosos | vários | **zero** | −vários |
| Lógica de domínio no adaptador | sim (`cli`) | **não** | − |

Nenhum módulo foi acrescentado em saldo, uma dependência saiu, um tipo saiu e um caminho de
código saiu — enquanto 19 críticos foram endereçados. **LOC:** não há baseline, porque nada foi
implementado ainda; a regra de justificar aumento >10% não se aplica nesta iteração.

## Achados aceitos com justificativa (não resolvidos, deliberadamente)

| id | Achado | Justificativa da aceitação |
|---|---|---|
| SUS-02 🟡 | F1 aloca o arquivo inteiro na criação (15,5 MB por série vazia no tier cru a 1 s / 15 d) | É inerente ao desenho round-robin de R6 e é o **preço** do tamanho previsível e da escrita O(1) por slot. Remover isso seria deixar de implementar F1. Mitigação: `info` mostra bytes por tier, então o custo é visível **antes** de o operador escolher o formato |
| MEC-02 🟡 | O codec só entrega o ganho na especificação exata (jitter degrada 6,8×) | Propriedade do algoritmo publicado, não defeito da arquitetura. Mitigado por **declaração** (o contrato aceita qualquer série monotônica) e por **medição** (`report` mostra a razão por perfil, incluindo o perfil `jitter`) — que é exatamente a forma de CA-4 |
| ASM-06 🟡 | Retenção é comando, não processo: sem agendador externo nada envelhece | Aceito e **declarado** como restrição do produto no README. Embutir um agendador seria feature, não arquitetura (proibido na Fase 3) |
| ASM-04 🟡 | O denominador do `xFilesFactor` é a contagem nominal esperada, e com jitter no cru a contagem real difere | É o comportamento do próprio Whisper (R6). Declarado no contrato de `aggregate`. Resolvido por construção para tiers derivados (que são alinhados); permanece uma aproximação declarada para o cru |

## Premissas de V(2) — o que mudou

`P-A2` (escritor único) e `P-A3` (uma série = um acervo) **permanecem** como premissas
declaradas e frágeis. `P-A7` (o disco não corrompe) **deixa de ser premissa**: o `crc32` por
chunk a transforma em condição verificada. `P-A4` (monotonicidade) deixa de ser premissa e
passa a ser **imposta na fronteira** por `store-port` via `series.validate_stream` (ASM-01).
`P-A5`, `P-A9`, `P-A10` inalteradas. `P-A8` inalterada (migração é streaming).
Nova: **`P-A11`** — o `journal` é append-only e ninguém o edita; ele é evidência, não fonte de
verdade (a fonte de verdade do estado é o `ArchiveHeader`).

---
---

# V(3) — Resposta unificada à crítica da Iteração 2

Fase 3, iteração 2. Responde aos 41 achados (36 defeitos distintos) de
`specs/design/coverage-matrix.md` §Iteração 2. **V(1) e V(2) permanecem intactas acima.**

## O diagnóstico que a rodada 2 devolveu

Os dois redesenhos que a rodada 1 exigiu funcionaram (`cli` 14 achados → 2, `retention`
12 → 4), mas os dois módulos criados para isso viraram os mais atacados (`journal` 8,
`usecases` 7). Deslocar a complexidade de novo seria AP2 em forma de rodízio.

E três dos cinco críticos distintos têm **a mesma raiz**: V(2) tentou guardar o estado novo
(marca d'água, `format_version`, especificação de tiers) **dentro dos formatos**, e os formatos
não foram feitos para isso — o Metadata de F1 tem 20 bytes fixados por R6 (IMP-06), o
round-robin de F1 já expira por conta própria (ASM-08), e o commit em duas escritas atômicas
travou (RES-06).

## As cinco decisões de V(3) — quatro delas DELETAM mecanismo

### E1 — O acervo é um diretório; os metadados moram num sidecar, fora do formato.
*Resolve: IMP-06 🔴, MIG-04, e habilita E2/E3.*

```
acervo-cpu.load/
├── meta.json          ← format_version, format, block_seconds, created_at,
│                        writer_version, series_name, tiers[]  (uma escrita atômica)
├── journal.jsonl
└── tier-0/ tier-1/ …  ← o dado, no layout do formato escolhido
```

O `ArchiveHeader` de V(2) não precisa caber em 20 bytes porque **não está no arquivo de dados**.
Consequência direta: **o arquivo de dados de F1 volta a ser byte-exato a R6** (Metadata 16 B,
ArchiveInfo 12 B, Point 12 B). A fidelidade à fonte, que V(2) tinha quebrado sem perceber, é
restaurada.

MIG-04 (dois acervos, nenhum marcado como vigente) vira **um campo**: `migrate` grava
`superseded_by: <caminho>` no `meta.json` da origem.

### E2 — F2 é um diretório de arquivos de chunk, um por bloco de 2 h, nomeado por `base_ts`.
*Resolve: PRF-04, SUS-05, ASM-07 🔴, OBS-05, e DELETA o índice de prefixo.*

| Consequência | Antes (V2) | Depois (V3) |
|---|---|---|
| Custo de acrescentar um chunk | `atomic_write` do arquivo inteiro ⇒ **O(acervo)**, O(N²) na vida | escrever **um arquivo pequeno** ⇒ O(chunk) |
| `rename` entre sistemas de arquivos (`EXDEV`) | premissa não declarada | **impossível**: o temporário nasce no diretório do chunk |
| Índice para achar o chunk de `t_from` | prefixo `(base_ts, byte_length, n_points, crc32)` no arquivo | **o nome do arquivo É o índice** — mecanismo deletado |
| Expirar | reescrever o arquivo sem os chunks velhos | **apagar arquivos**; I5 fica literal e óbvia |
| Varredura de integridade (OBS-05) | não existia | iterar os arquivos e verificar o `crc32` de cada |

É o que o Prometheus faz com diretórios de bloco (R8/R12) — e agora o custo de append é
proporcional ao que se acrescenta, não ao que já existe, num formato cuja razão de ser é ser
append-only.

### E3 — A marca d'água é DERIVADA do dado, não armazenada.
*Resolve: RES-06 🔴, PRC-04 🔴, ASM-02, ASM-11, CTL-04 — e DELETA o tipo `TierState`.*

V(2) acertou o diagnóstico (faltava modelar o estado) e errou a cura (guardá-lo). O estado não
precisa ser guardado, porque **o dado derivado já o contém**:

```
derived_through_ts(tier) = max(base_ts dos chunks do tier) + block_seconds
                           (em F1: o timestamp do slot válido mais recente)
```

O que isso mata, de uma vez:

- **RES-06 / PRC-04:** não há duas escritas atômicas, logo não há janela entre elas. Uma falha
  deixa o arquivo de chunk escrito ou não escrito; re-derivar produz **o mesmo nome de arquivo**,
  sobrescrito atomicamente. **Idempotente por construção**, e o travamento entre a correção de
  LIN-02 e a de PRC-01 desaparece porque a re-derivação não é mais um append duplicado.
- **ASM-02:** o estado não pode divergir do disco — o estado **é** o disco.
- **ASM-11:** duas escritas atômicas não formavam transação; agora há uma só.
- **CTL-04:** recomputar deixa de exigir mecanismo: o operador apaga o chunk derivado e ele é
  refeito na próxima execução. Um erro de configuração não fica mais congelado para sempre.
- **IMP-06** encolhe ainda mais: `tier_states` sai dos metadados por completo.

**Um tipo a menos, um mecanismo a menos, e o pior crítico da rodada resolvido por remoção.**

### E4 — F1 usa o layout de R6 **e** a semântica de validade-por-timestamp do Whisper.
*Resolve: ASM-08 🔴, LIN-08, REG-01.*

ASM-08 estava certo: um arquivo round-robin sobrescreve o slot mais antigo ao dar a volta, o
que é um segundo mecanismo de expiração. A resposta não é escolher entre os dois — é notar que
**no Whisper eles são o mesmo mecanismo**: um slot só é válido se o timestamp nele gravado
**for igual ao timestamp esperado daquela posição**. Ao dar a volta, o slot antigo passa a ter
timestamp que não corresponde e portanto **já está expirado, por definição**.

Consequência: `expire()` em F1 é um **no-op que reporta a fronteira efetiva** (calculada do
tamanho do arquivo), e é trivialmente idempotente (LIN-08). `ExpireReport.effective_before_ts`
continua sendo a invariante I5 (REG-01), agora com a mesma semântica nos dois formatos: F1 a
deriva do tamanho do arquivo, F2 do `base_ts` do chunk sobrevivente mais antigo.

### E5 — Os mecanismos de V(2) ganham contrato completo; o `journal` encolhe em vez de endurecer.
*Resolve: LIN-07 🔴, IMP-07, IMP-08, LIN-09, SEC-06, SEC-07, SCI-04, SCI-05, RES-07, GOV-04, GOV-05, ASM-09, SUS-04, PRF-05, OBS-06, UX-06, UX-07, MIG-05, MEC-05, MEC-06, REG-03, ASM-10, PRC-05.*

O padrão sistêmico da rodada 2 foi "cinco mecanismos acrescentados, nenhum especificado por
completo". Cada um recebe sua regra:

| Achado | Regra de V(3) |
|---|---|
| LIN-07 🔴 | **Alinhado significa `ts % seconds_per_point == 0`, época Unix.** É a definição do Whisper (`interval = ts − ts % secondsPerPoint`). Uma linha, e as duas implementações concordam |
| IMP-07 | **"Verificar" = reler o intervalo recém-escrito pela porta e comparar ponto a ponto com o que foi derivado.** O passo deixa de ser decorativo |
| REG-03 | CA-2 ganha verificador: `migrate --verify` compara ponto a ponto, não contagens |
| IMP-08, LIN-09, SEC-06 | Journal é **JSON Lines**; `op` vem de um **conjunto fechado** (`ingest, retain, migrate, expire`); os campos passam por `json.dumps`, o que escapa quebras de linha e **elimina a injeção de linha falsa de graça** |
| RES-07 | A linha é escrita **depois** do ponto de commit. Falha do journal não desfaz nada, e a operação registrada é sempre uma que aconteceu |
| GOV-04, SEC-07, SCI-05 | **Declarados, não mitigados:** o journal é evidência contra **erro operacional**, não contra alteração deliberada (não há encadeamento de hash). O `crc32` detecta corrupção **acidental** e não autentica. O `crc32` é escolha de engenharia (`zlib`) e **não** vem de R1 |
| ASM-09, SUS-04, PRF-05 | **Uma linha por comando invocado**, não por operação interna. Rotação é do operador, como qualquer log, e `info` reporta o tamanho do journal. Embutir rotação seria mecanismo novo num produto que já tem política de retenção — e seria confundir as duas |
| OBS-06 | `info --history` lê o journal. Sem comando novo |
| UX-06 | `--dry-run` imprime **o `now` que usou**, e `retain` aceita `--now` para reproduzir exatamente o plano previsto |
| UX-07 | `--on-reject=abort\|skip`, **`abort` por padrão**: o operador decide antes de metade estar dentro |
| MIG-05, MEC-05 | Política declarada: **recusar ler `format_version` maior que a do escritor**; igual aceita; não há migração de downgrade neste ciclo |
| MEC-06 | `block_seconds` vem do `meta.json` (dado externo) e é **validado contra `MAX_BLOCK_SECONDS` na carga**, não na decodificação |
| SCI-04 | Declarado: o `xFilesFactor` é aplicado **só contra a contagem nominal do tier de origem imediato**, e o estado "indefinido" **não propaga** — um ponto derivado existe ou não existe. É o comportamento do Whisper; R6 e R9 não formalizam a composição, e isso fica dito em vez de suposto |
| ASM-10, PRC-05 | Ponto atrasado (`ts` antes do fim do que já foi derivado) é **rejeitado com motivo** no tier cru, e o motivo diz que re-derivar exige apagar o chunk derivado. Sem correção silenciosa |

## V(3) — Decomposição em módulos

**Os 12 módulos de V(2) permanecem, com os mesmos nomes e as mesmas responsabilidades.** Nenhum
módulo entra, sai ou troca de papel — as mudanças são de **contrato e de formato**, não de
decomposição. As diferenças frente à tabela de V(2):

| id | module | o que mudou em V(3) |
|------|--------|---------------------|
| M-01 | bitstream | — (0 achados na rodada 2) |
| M-02 | gorilla-codec | O chunk deixa de carregar prefixo de arquivo; `to_bytes`/`from_bytes` seguem com `n_points` + `crc32` internos. `block_seconds` validado na carga (MEC-06) |
| M-03 | series | **`TierState` DELETADO** (E3). `ArchiveHeader` → `ArchiveMeta`, serializado em `meta.json`, sem `tier_states`. `is_aligned(ts, res)` definido (LIN-07) |
| M-04 | retention | `plan(tiers, derived_through, now)` recebe a marca d'água **derivada** em vez de estado persistido. Caminho de ponto atrasado explícito |
| M-05 | downsampler | Regra do `xFilesFactor` declarada (SCI-04) |
| M-06 | store-port | `atomic_write` documentado como **temporário no diretório de destino**; `derived_through(series, tier)` entra no contrato; `expire` idempotente com semântica única |
| M-07 | store-f1 | Arquivo de dados **byte-exato a R6** (metadados saíram para o sidecar). Validade-por-timestamp: staleness e expiração são o mesmo mecanismo (E4) |
| M-08 | store-f2 | **Diretório de arquivos de chunk**, um por bloco, nomeado por `base_ts` (E2). Índice de prefixo deletado |
| M-09 | journal | JSON Lines, `op` de conjunto fechado, escrito após o commit, uma linha por comando. Escopo **declarado** como evidência contra erro operacional |
| M-10 | dataset-gen | — (0 achados na rodada 2) |
| M-11 | usecases | Ponto de commit único; "verificar" definido; `--on-reject`; `migrate --verify` e `superseded_by` |
| M-12 | cli | `--on-reject`, `info --history`, `--dry-run` imprime o `now` |

## Contabilidade de complexidade (AP2) — a primeira rodada em que o número de mecanismos CAI

| Dimensão | V(2) | V(3) | |
|---|---|---|---|
| Módulos | 12 | **12** | igual |
| Tipos do domínio | `Point`, `TierSpec`, `TierState`, `ArchiveHeader` | `Point`, `TierSpec`, `ArchiveMeta` | **−1** |
| Escritas atômicas por operação | 2 (dado + header) | **1** | −1 |
| Índice de chunk | prefixo no arquivo | **o nome do arquivo** | mecanismo deletado |
| Custo de append em F2 | O(acervo), O(N²) na vida | **O(chunk)** | assintótica corrigida |
| Mecanismos de expiração em F1 | 2 (volta implícita + `expire`) | **1** (validade-por-timestamp) | −1 |
| Metadados dentro do formato | sim (não cabia em F1) | **não** (sidecar) | fidelidade a R6 restaurada |
| Mecanismos sem contrato completo | 5 | **0** | − |

## Achados aceitos com justificativa

| id | Achado | Justificativa |
|---|---|---|
| ARQ-07 🟡 | `usecases` herdou o fan-in de quase tudo | **Aceito, e é o que a camada existe para fazer.** Uma camada de Transaction Script tem fan-in alto por definição; "corrigir" isso exigiria inventar outra camada, que é exatamente o AP2 que esta rodada precisa evitar. ARQ-01 dizia que lógica de domínio morava num adaptador — isso foi resolvido; fan-in de orquestração não é o mesmo defeito |
| ARQ-06 🟡 | `store-port` acumula contrato + escrita atômica + compatibilidade | Aceito: os três são *o contrato de armazenamento* visto de ângulos diferentes, e separá-los criaria um módulo de 15 linhas mais uma dependência. Revisar se um quarto papel aparecer |
| ARQ-08 🟡 | `gorilla-codec` codifica e enquadra | Aceito e **reduzido** por E2: o enquadramento de arquivo saiu (o nome do arquivo é o índice), sobrando só o enquadramento do chunk, que é a unidade de estado do codec |
| SUS-02, MEC-02, ASM-06, ASM-04 | herdados da rodada 1 | Justificativas inalteradas; ASM-04 agora acompanhado da regra explícita de SCI-04 |
| GOV-04, SEC-07 | journal não é à prova de alteração; `crc32` não autentica | Aceitos **por declaração**: tornar a auditoria à prova de alteração exigiria encadeamento de hash, e autenticar o dado exigiria MAC com chave — ambos fora dos três eixos do enunciado, e ambos agora ditos em voz alta em vez de insinuados |

## Decisões finais e correções da implementação (preenchido na Fase 7)

V(3) sobreviveu à implementação **sem mudança de módulo nem de contrato**. O que a
implementação acrescentou foram decisões de *codificação* que as fontes deixam implícitas, e
uma correção numa premissa:

| Item | Decisão final |
|---|---|
| Faixas assimétricas de R1 §4.1.1 | Gravar `D - lo` em `payload_bits`, cobrindo exatamente `[lo, hi]`. É decisão nossa de representação; R1 fixa a faixa e cala sobre a codificação |
| Comprimento significativo do XOR | Gravar `significant - 1` em 6 bits, cobrindo 1..64. Necessário porque o comprimento **pode ser 64** (`-inf ⊕ 5e-324`) e 6 bits só chegam a 63 |
| `prev_delta` inicial | `0`, logo o 2º ponto do bloco cai no bucket do **próprio delta** (9 bits para 1 s ou 60 s) |
| `crc32` | `zlib`, escolha de **engenharia** — não vem de R1. Detecta corrupção acidental, **não autentica** |
| `nbits` no chunk | Campo `u32` após o header. Sem ele, o padding do último byte é indistinguível de dado |
| **`P-A8` (streaming)** | **Estava violada na 1ª implementação** — `write()` bufferizava toda a entrada (151 B/ponto, 330 MB para 2 M pontos). Corrigido para fluir por janela: memória **plana em 1,5 MB**. Protegido por teste que mede o pico entre 2 e 20 chunks cheios |
| Tratamento de entrada malformada | `main()` captura `ValueError` e `OSError` além de `SeriesError` — três caminhos vazavam *traceback* |
| `default_tiers()` | **Dois** tiers, não três: três com `average` encadeado violaria D2, e um default que a própria `validate()` recusa é pior que um default modesto |
| Ordem das verificações em `validate()` | Ordenação **antes** de divisibilidade — invertida, a mensagem confunde em vez de ajudar |

Algoritmos descartados e por quê, confirmado após medir: **Chimp** e **Elf** seguem fora, e a
justificativa se fortaleceu — o codec de R1 reproduziu os números da sondagem com desvio de
0,1%, então a base de comparação para um v2 existe e é sólida. **Parquet/Arrow** seguem fora:
zero dependência externa foi mantida do início ao fim, inclusive removendo `numpy` do gerador.

## Escopo negativo novo em V(3)

Decisões conscientes de NÃO fazer, todas nascidas de achados e declaradas em vez de insinuadas:

| Item | Razão |
|---|---|
| Encadeamento de hash no journal | Tornaria a auditoria à prova de alteração deliberada. Fora dos três eixos do enunciado. O journal é declarado como evidência contra **erro operacional** (GOV-04) |
| MAC/assinatura sobre o dado | Autenticar exigiria chave e gestão de chave. `crc32` detecta corrupção **acidental**, e isso está dito (SEC-07) |
| Rotação automática do journal | Rotação é do operador, como em qualquer log. Embutir rotação num produto que já tem política de retenção confundiria as duas coisas (ASM-09) |
| Migração de *downgrade* de `format_version` | Política: recusar ler versão maior que a do escritor. Migrar para trás exigiria manter leitores de todas as versões anteriores (MIG-05) |
| Reordenação de ponto atrasado | Ponto anterior ao já derivado é **rejeitado com motivo**; corrigir automaticamente esconderia um problema do produtor do dado (ASM-10) |
| Acesso aleatório na porta, lock de arquivo, WAL, backfill em bloco fechado | herdados de V(1)/V(2), inalterados |

## Premissas de V(3)

`P-A2` (escritor único) e `P-A3` (uma série = um acervo) seguem declaradas e frágeis — as duas
sobreviventes desde V(1). `P-A11` **cai**: o journal não é mais fonte de verdade de nada,
porque não existe mais estado persistido para ele contradizer. Nova **`P-A12`**: o nome do
arquivo de chunk (`base_ts`) é a única fonte de ordenação do acervo em F2 — renomear arquivos à
mão corrompe o acervo, e nada impede isso.


