# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Compactador de séries temporais com política de retenção e troca do formato de armazenamento

## A arquitetura

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

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo, e detecta uma classe de falha que as outras não detectam.

**Sete são universais** — rodam sempre e não estão em questão: Premissas, Arquitetura,
Implementabilidade, Rigor científico, Segurança, Desempenho, Conformidade regulatória.
**Não as inclua na resposta.**

**Doze são condicionais**, e são essas que você vai avaliar.

**A ativação é por SINAL DO PROJETO, e só.** Que outra lente pareça cobrir a mesma
classe de falha **não** é motivo para deixar uma de fora: não achar nada já é um
resultado válido, e decidir de antemão que duas lentes se sobrepõem é conclusão, não
premissa. Nunca marque `false` por redundância com outra lente — o motivo tem que ser
um sinal do projeto ("não há dependência externa", "não há superfície de usuário"),
nunca "já coberta pela lente X".


| lente | pergunta central | ativa quando |
|---|---|---|
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | The system depends on anything outside its own process that can fail, stall, or return unexpected data — a network service, a database, a queue, a file, a subprocess. Apply the central question wherever such a boundary exists; the list is illustrative, not the requirement. |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | The work must carry an existing, relied-upon state or contract across a change — a populated store, a format other code already reads, a live interface consumers depend on — that has to survive or roll back. Greenfield work, and a store only this version ever reads, do not activate. |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | The system makes or automates a consequential decision whose effect falls on people — directly, or through an entity they depend on (a budget cut borne by those it funds, an access denial, a flag acted on). Apply the central question — who can be harmed? — without requiring the decision be nominally "about people". A system that decides nothing consequential about anyone stays out. |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | The system has a process with states, handoffs, or exception paths — one actor or many. Apply the central question wherever a flow can be left incomplete; "multi-actor" is one case, not the requirement. |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | The system runs somewhere it can degrade or fail after it ships, and someone would need to tell WHY without changing code. Apply the central question wherever a running system can fail silently; it does not require a formal "production" or "ops" label. |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | The system regulates state over time rather than only reacting — state synchronization, a runtime setting that changes behavior, a retry/backoff, a self-correcting or feedback-driven loop that can oscillate or drift. Apply the central question wherever such regulation exists; the list is illustrative. |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | The design assumes some actor — a user, a client, an integrator, an operator — behaves as intended, and a self-interested one could deviate to its own benefit. Apply the central question wherever cooperation is assumed rather than enforced; a public API or marketplace is one case, not the requirement. |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Any contract two parties must agree on — a function signature, a message format, a protocol, a file schema — where two correct readings could diverge. Apply the central question wherever a contract can be read two ways; it does not require separate teams. |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | The system depends on something that can vary — a dependency version, an environment, an input range, a load — and could fail on small deviations. Apply the central question wherever variation is possible, not only in long-lived or maintenance-heavy systems. |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T29-retencao",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
