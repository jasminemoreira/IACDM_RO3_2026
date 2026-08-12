# Reagrupamento cego de achados — T29-retencao

Você recebe 109 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
módulo onde ocorre, a severidade e uma descrição de uma linha.

**Sua tarefa:** agrupar os achados que apontam o MESMO DEFEITO.

Atenção a defeitos **replicados**: quando dois módulos são implementações irmãs do
mesmo contrato, o mesmo defeito pode aparecer em ambos. Se uma única correção na
abstração compartilhada resolveria os dois, é o mesmo defeito.

**Critério, e é o único que vale:**

> Dois achados são o mesmo defeito quando apontam o mesmo problema no mesmo local,
> com a mesma causa raiz. Regra operacional: **se corrigir um resolveria
> automaticamente o outro, é o mesmo defeito.** Se cada um exige uma correção
> própria, são defeitos distintos — mesmo que estejam no mesmo módulo e sejam
> parecidos.

**Viés conservador, obrigatório:** na dúvida, **NÃO** agrupe. Agrupar a mais é o erro
mais caro aqui.

Não explique, não comente, não reordene. Responda **só** com este JSON:

```json
{"grupos": [["F-03", "F-07"], ["F-11", "F-02", "F-19"]]}
```

Cada lista interna é um grupo de achados que são o mesmo defeito. Achados que não
são duplicata de nenhum outro **não aparecem** — grupos de um só elemento são
implícitos. Se nenhum achado for duplicata de outro, responda `{"grupos": []}`.

## A arquitetura

Os módulos do sistema, para você saber o que cada nome significa e quais são irmãos
entre si:

| id | módulo | responsabilidade | interface | depende-de |
|---|---|---|---|---|
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

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | cli | 🟡 | `WriteReport.rejected` existe no contrato, mas nada obriga o `ingest` a EXIBIR os rejeitados. Rejeição silenciosa na saída é indistinguível de sucesso |
| F-02 | cli | 🟡 | `retain` agrega e depois expira. Falha entre as duas etapas consome o cru sem gravar o agregado (ou o inverso) ⇒ perda. A ordem obrigatória — gravar o agregado ANTES de expirar o cru — não está declarada em nenhum contrato |
| F-03 | retention | 🔴 | A máquina de estados do ponto (cru → 5m → 1h → expirado) não tem estado explícito em nenhum módulo. Sem saber se um intervalo já foi agregado, rodar `retain` duas vezes agrega o mesmo intervalo duas vezes |
| F-04 | store-f1 | 🔴 | F1 é round-robin (R6): ao dar a volta, **sobrescreve o slot mais antigo por construção**. Isso é um segundo mecanismo de expiração, implícito, coexistindo com o `expire()` explícito de V(2) — e a marca d'água pode apontar para dado que o round-robin já descartou. V(2) não declarou se F1 continua dando a volta |
| F-05 | dataset-gen | 🟢 | Assume que `seed` fixa dá a mesma sequência entre versões. `random` da stdlib não é contratual entre major versions e `numpy` já trocou de gerador (`RandomState` → `Generator`). Reprodutibilidade do ground truth não declarada |
| F-06 | journal | 🟡 | O journal é a evidência e nada o protege: arquivo editável no mesmo diretório, sem encadeamento de hash. Serve contra erro operacional, não contra alteração deliberada — e V(2) não declara qual dos dois pretende ser |
| F-07 | downsampler | 🟢 | Preservar 4 agregados quadruplica o custo por ponto do tier reduzido; com resolução 5×/12× menor ainda compensa, mas a conta não está documentada em nenhum lugar |
| F-08 | cli | 🟡 | `retain --now T` obrigatório inverte o modelo mental: o operador quer "aplique a retenção agora". `--now` é instrumento de teste promovido a interface primária |
| F-09 | store-port | 🟡 | A invariante I5 (retenção efetiva ≥ nominal, granularidade de descarte é o bloco) não tem módulo responsável. `expire(series, tier, before_ts) -> int` sugere granularidade de ponto, mas F2 só pode apagar blocos inteiros. Requisito sem rastreabilidade |
| F-10 | store-f1 | 🔴 | mesma ausência de atomicidade, manifestando-se como slots parcialmente escritos |
| F-11 | bitstream | 🟡 | Se o `BitWriter` acumular num único `int` de precisão arbitrária e deslocar, cada `write_bits` copia o acumulado ⇒ **O(n²)** por bloco. Com 7.200 pontos isso é mensurável. Nenhuma decisão de representação (bytearray + offset de bit) foi declarada |
| F-12 | block | 🟡 | O primeiro delta de 14 bits assume `t₀ ≥ base_ts`. Um ponto com ts anterior ao base do bloco gera delta negativo, não representável em 14 bits sem sinal. Nenhum contrato proíbe esse ponto |
| F-13 | cli | 🟢 | O nome do executável (`tsz`) aparece só na tabela de interfaces; não há decisão registrada sobre nome do pacote, do comando nem do diretório de acervo |
| F-14 | store-f1 | 🔴 | R6 fixa `Point = 12 B` com UM valor de 8 bytes por slot. O downsample de R9 preserva QUATRO agregados. **F1 não pode representar um tier agregado** sem violar o layout que a própria fonte define. Contradição entre R6 (formato) e R9 (política) não resolvida |
| F-15 | journal | 🟡 | Não é especificado se a linha é escrita antes ou depois da operação. Antes: audita o que pode não ter acontecido. Depois: operação sem auditoria se o disco encher. E o journal falhar não pode desfazer o que já ocorreu |
| F-16 | retention | 🔴 | `plan(tiers, now, tier_state)` assume que `tier_state` reflete o disco. Se a execução anterior morreu no meio (sem transação), estado e acervo divergem e o plano age sobre uma realidade que não existe. Premissa não declarada: "plano e acervo estão sincronizados" |
| F-17 | retention | 🔴 | O sistema destrói dado de forma irreversível (I4) e não há trilha de auditoria. Depois de um `retain`, ninguém pode responder "o que existia antes, o que foi agregado, o que foi apagado, e quando" |
| F-18 | usecases | 🔴 | o mesmo defeito como processo: falta o estado "derivado mas não confirmado", e sem ele o fluxo não tem caminho de recuperação |
| F-19 | store-f2 | 🔴 | Escrita não atômica: Ctrl-C, disco cheio ou kill no meio de `write()` deixa bloco truncado. Sem escrever-em-temporário-e-renomear, nem journal |
| F-20 | series | 🟡 | `writer_version` existe sem tolerância definida: ler acervo escrito por versão mais nova é erro ou aviso? |
| F-21 | migrator | 🟡 | Quando dois pontos de F2 caem no mesmo slot de F1, o contrato diz `rejected`, mas F1 é `mutable_slots=True` e o comportamento natural do formato é SOBRESCREVER. Contrato e formato discordam, e nenhum dos dois é obviamente o certo |
| F-22 | retention | 🟡 | A marca d'água assume que o cru nunca chega atrasado. Um ponto com `ts < derived_through_ts` **nunca será agregado** — o intervalo já foi derivado — e o tier derivado fica permanentemente errado, em silêncio |
| F-23 | store-port | 🔴 | `write()` rejeita ts desalinhado se `aligned_writes_required`, mas o contrato não diz **alinhado a partir de qual época**. Sem origem declarada, F1 e F2 podem discordar sobre o que "alinhado" significa — é LIN-01 reaparecendo um nível abaixo, na definição do próprio predicado |
| F-24 | block | 🟡 | `CodecState` é estado mutável compartilhado entre `block` (que o guarda) e `gorilla-codec` (que o avança). É exatamente o acoplamento que a fusão de ts-codec+value-codec queria evitar, reaparecendo uma fronteira acima |
| F-25 | store-f2 | 🟡 | Sem índice de blocos no arquivo (ver IMP-02), `read(t_from, t_to)` é O(tamanho do arquivo) mesmo para um intervalo de 1 minuto. R1 declara o trade-off no nível do BLOCO; aqui ele vaza para o arquivo inteiro |
| F-26 | downsampler | 🟡 | Dois modelos de agregação coexistem sem decisão: `AGGREGATIONS={average,sum,last,max,min}` (5 métodos de R6) e `Aggregate(min,max,sum,count)` (4 agregados de R9). `average` não está entre os 4; `count` não está entre os 5 |
| F-27 | store-f2 | 🔴 | Um bit trocado no meio de um bloco corrompe **todos os pontos seguintes** do bloco, porque o estado do decodificador (`prev_bits`, `prev_lead`, `prev_trail`) propaga o erro. Sem checksum, o operador lê valores plausíveis e errados. P-A7 declara a premissa; o cenário permanece sem mitigação |
| F-28 | retention | 🟡 | Caminho de exceção ausente: o que acontece quando a config de tiers muda DEPOIS de o acervo existir? Tiers removidos ou com resolução alterada deixam dado órfão, e nenhum ator é responsável por migrar a config |
| F-29 | store-port | 🟡 | Acumulou três papéis: o contrato (Protocol), o helper de escrita atômica e a regra de compatibilidade entre formatos. É o padrão que fez `cli` virar módulo-deus na rodada 1, em escala menor |
| F-30 | journal | 🟡 | `read(acervo)->Iterator[dict]` implica parsing, mas o formato da linha não é definido (JSON Lines? texto delimitado?). Não implementável isoladamente |
| F-31 | store-port | 🟡 | `Aggregate` não é `Point` e o contrato não define como um tier agregado é escrito |
| F-32 | migrator | 🔴 | Não há caminho de rollback. O contrato não diz se a origem é preservada ou removida: se removida e o destino estiver errado, não há volta; se preservada, nenhum módulo responde quem apaga e quando |
| F-33 | journal | 🟡 | Uma linha por operação mutante com o relatório serializado: um `retain` com vários tiers e intervalos gera muitas linhas, e em acervos pequenos a trilha cresce mais rápido que o dado |
| F-34 | retention | 🟡 | O sinal de erro do regulador não é observável: `plan()` devolve o que fazer, mas nada expõe "estado desejado × estado real" de forma inspecionável antes da ação |
| F-35 | migrator | 🟡 | Para fazer `precheck`, o migrator precisa interpretar a semântica de `Capabilities` ("dst mais restritivo que src"). Isso é conhecimento sobre formatos vivendo no módulo que existe justamente para não saber de formatos |
| F-36 | cli | 🟢 | `report` mede os perfis sintéticos do `dataset-gen`, não o acervo real do operador — cobre CA-4 no laboratório, não em produção |
| F-37 | retention | 🟡 | A marca d'água torna `retain` idempotente **e irreversível**: se a config mudar (um `xff` corrigido), o intervalo já derivado não é recomputado. Sem reset da marca d'água, um erro de configuração fica congelado no tier derivado para sempre |
| F-38 | migrator | 🟡 | sem escrita atômica, uma falha no meio de uma migração de acervo grande perde O(n) de trabalho e deixa o destino em estado ambíguo |
| F-39 | store-port | 🟡 | `expire(before_ts) -> int` devolve "int" de quê? F1 responderia em pontos apagados, F2 em blocos. Mesma assinatura, unidades diferentes |
| F-40 | store-f2 | 🔴 | sem contagem de pontos nem checksum no header do bloco, a degradação é INDETECTÁVEL sem alterar código: "os valores estão estranhos" não tem instrumento de diagnóstico |
| F-41 | store-f2 | 🟡 | `atomic_write` de arquivo inteiro a cada `write()`: acrescentar um chunk a um acervo de 100 MB reescreve 100 MB. A atomicidade de RES-02 foi comprada ao custo de O(tamanho do acervo) **por append** — num formato cuja razão de ser é ser append-only |
| F-42 | migrator | 🟡 | `MigrationReport.lossless` é a prova de que a migração preservou o dado — e ela morre no stdout. Nada é persistido, logo a afirmação não é auditável depois |
| F-43 | dataset-gen | 🟡 | escreve em caminho fornecido pelo operador, mesmo defeito de ausência de validação de caminho centralizada |
| F-44 | store-port | 🟡 | Nenhuma entidade tem proprietário. `series` é uma string; não há metadado de quem escreveu, quando, com qual versão do software. Um acervo é anônimo e não atribuível |
| F-45 | store-f1 | 🔴 | P-A4 declara timestamps crescentes, mas o layout round-robin de F1 não tem noção de ordem e `check_monotonic` mora em `series`, não na porta. Se o `cli` esquecer de chamar, F1 aceita fora de ordem em silêncio: a invariante I2 é assumida, não imposta na fronteira |
| F-46 | retention | 🟡 | ponto atrasado não tem caminho de exceção definido |
| F-47 | usecases | 🟡 | CA-2 (F1→F2→F1 preserva a série) não tem verificador: `migrate` compara **contagens**, não igualdade ponto a ponto. O critério de aceitação continua não computável, agora por outro motivo que na rodada 1 |
| F-48 | store-f1 | 🟢 | `capabilities().random_access=True` não é utilizável por ninguém: a porta não tem `get(ts)`. Ou o campo é morto, ou existe um caminho fora da porta — que quebraria o Hexagonal |
| F-49 | usecases | 🟡 | `journal.read()` existe no contrato e não é exposto por comando algum: `info` mostra o estado atual, e o histórico fica ilegível na prática |
| F-50 | cli | 🔴 | Nenhum `--dry-run` em `retain` nem em `migrate`, que são as duas operações destrutivas e irreversíveis (I4). O operador não pode ver o que vai acontecer antes de acontecer |
| F-51 | journal | 🟡 | trilha sem limite num produto cujo propósito é limitar crescimento, aqui pela lente do custo |
| F-52 | retention | 🔴 | `retain` é um regulador que observa a idade do dado e corrige o acervo, mas nada garante idempotência. Executar com `now` ligeiramente diferente produz drift: agrega duas vezes, ou agrega um intervalo incompleto e nunca o revisita |
| F-53 | store-f1 | 🔴 | `series` é um nome que vira caminho de arquivo, sem sanitização declarada. `series="../../etc/cron.d/x"` escreve fora do acervo. É a única superfície de entrada externa do sistema |
| F-54 | store-f2 | 🟡 | Um bloco truncado no fim do arquivo é indistinguível de um bloco válido: sem contagem de pontos no header nem marcador de fim, o `BitReader` lê padding como dado |
| F-55 | downsampler | 🟡 | `Aggregate(ts, min, max, sum, count)` sai do downsampler, mas `Store.write` recebe `Iterator[Point]` e `Point` tem um único `value`. Falta o mapeamento agregado → formato |
| F-56 | store-port | 🟡 | `read(t_from, t_to)` — intervalo fechado ou semiaberto? Não declarado. Duas implementações discordarão em exatamente um ponto por consulta, e o erro é invisível para qualquer teste que não olhe a borda |
| F-57 | store-f1 | 🔴 | Nenhum campo de versão de formato em F1 nem em F2. Um acervo escrito hoje e lido por uma versão futura com layout alterado é interpretado ERRADO em vez de rejeitado. Tolerância zero disfarçada de simplicidade |
| F-58 | retention | 🟡 | I7 exige comparar a janela de retenção com a idade mínima para o downsample seguinte, mas `TierSpec(seconds_per_point, retention_seconds, aggregation, x_files_factor)` não tem campo de idade mínima. Os gatilhos citáveis de R9 (40 h, 10 dias) não têm onde morar |
| F-59 | cli | 🟡 | 6 Transaction Scripts + execução do plano de retenção num só módulo: é o maior do sistema e provavelmente não cabe numa sessão com todos os contratos em contexto (viola o princípio E = I₀/C que a própria Fase 1 adotou) |
| F-60 | downsampler | 🟡 | D2 provou associatividade para o VALOR (`min`/`max`/`sum`/`last`), mas **não para o `xFilesFactor`**: compor "indefinido" do 5m para o 1h não está documentado em R6 nem em R9. A prova cobre metade do que a cascata faz |
| F-61 | journal | 🟡 | Assume que a trilha cabe em disco indefinidamente. Um produto cujo propósito é limitar o crescimento do dado não limita o crescimento da própria auditoria |
| F-62 | store-f1 | 🔴 | `ArchiveHeader` de V(2) tem 7 campos (`format_version`, `block_seconds`, `created_at`, `writer_version`, `series_name`, `tiers`, `tier_states`). O Metadata de R6 tem **20 bytes e 4 campos**. **Não cabe.** É SCI-02 reaparecendo: V(2) matou o `Aggregate` que F1 não podia representar e criou um header que F1 também não pode |
| F-63 | gorilla-codec | 🟡 | Ao absorver o bloco, passou a ter duas responsabilidades: codificar pontos e serializar um contêiner (header, `crc32`, `n_points`). E `store-f2` também sabe de contêiner (o prefixo no arquivo). A fronteira de quem é dono do enquadramento ficou dúbia |
| F-64 | dataset-gen | 🟡 | variação de versão de `numpy` muda o gerador, muda o ground truth, e o resultado de CA-4 muda sem que nada no produto mude |
| F-65 | cli | 🟡 | Assume que o operador chama `retain` periodicamente. Retenção é um comando, não um processo: sem agendador externo, nada envelhece e o acervo cresce sem limite — o oposto do propósito do produto. Premissa não declarada |
| F-66 | journal | 🟡 | O journal registra nomes e caminhos. Se a validação de nome vale para o acervo mas não para a escrita da linha, uma quebra de linha no campo injeta uma **linha falsa de auditoria** |
| F-67 | retention | 🟡 | `plan()` recebe `tier_state`, cujo tipo não é definido em nenhum módulo. Sem o tipo, `retention` não é implementável isoladamente |
| F-68 | journal | 🟡 | `append(acervo, op:str, report:dict)` — `op` é string livre. Duas partes do código escreverão `"retain"` e `"retention"`, e a trilha fica inagregável: é exatamente o defeito que a coluna `lens` desta matriz evita com nomes canônicos |
| F-69 | retention | 🟢 | `min_age` + marca d'água dão histerese real; CTL-02 da rodada 1 está resolvido e a lente não encontra oscilação nova |
| F-70 | usecases | 🔴 | A ordem `derivar→gravar→verificar→avançar marca d'água→expirar` tem DUAS escritas atômicas (o dado derivado e o header com a marca d'água). Falha entre elas ⇒ dado gravado, marca d'água não avançada ⇒ a próxima execução deriva o mesmo intervalo e, como ts duplicado agora é **erro** (LIN-02), `retain` passa a falhar **permanentemente**. **A correção de LIN-02 e a de PRC-01 se travam mutuamente** |
| F-71 | store-port | 🟡 | CA-4 exige razão de compressão medida por perfil, mas `WriteReport{written, rejected, reasons}` conta PONTOS, não BYTES. O critério de aceitação não é computável com os contratos atuais |
| F-72 | store-f2 | 🟡 | escrever N chunks custa O(N²) bytes gravados ao longo da vida do acervo; o desgaste de disco é desproporcional ao dado retido |
| F-73 | usecases | 🟡 | Herdou dependência de quase tudo (retention, downsampler, store-port, journal, series). ARQ-01 foi **movido**, não eliminado: o fan-in trocou de módulo |
| F-74 | usecases | 🟡 | `migrate` registra no journal da origem, do destino ou dos dois? Se só num, metade da história desaparece justamente na operação que move o acervo |
| F-75 | usecases | 🟡 | Com rejeição como padrão, ingerir um arquivo com um ponto duplicado faz o quê: rejeita o ponto e segue, ou aborta o arquivo? `WriteReport.rejected` sugere seguir, mas o operador provavelmente quer decidir antes de metade estar dentro |
| F-76 | store-f1 | 🔴 | F1 guarda múltiplos archives num arquivo, mas nada especifica como os archives se relacionam com os `TierSpec` de `retention`: quem os cria, com quantos pontos, e o que acontece se a config mudar depois. Não implementável numa sessão sem essa decisão |
| F-77 | block | 🟡 | `BLOCK_SECONDS=7200` é constante de módulo e não é gravada no arquivo. Um acervo escrito com outro valor é decodificado errado em silêncio — parâmetro distinto do de MEC-01, mesma classe de intolerância |
| F-78 | gorilla-codec | 🟡 | `MAX_BLOCK_SECONDS=14400` protege o campo de 14 bits, mas `block_seconds` agora vem do header do acervo — **dado externo**. Um acervo com `block_seconds=20000` é aceito na leitura e só falha ao decodificar: falta validação de tolerância na borda de entrada |
| F-79 | store-f1 | 🟡 | F1 aloca o arquivo inteiro na criação. Um tier cru a 1 s com 15 dias de retenção = 1,296 M pontos × 12 B = **15,5 MB por série, vazio**. Contra F2 (~1,37 B/ponto do que existe), é 8,8× pior e pago adiantado |
| F-80 | cli | 🟡 | Nenhum comando de inspeção (`info`/`stat`): tiers existentes, contagem de pontos, bytes por tier, intervalo coberto. O operador não tem como responder "o que tem neste acervo?" |
| F-81 | store-port | 🔴 | `write()` com o mesmo timestamp duas vezes: F1 (`mutable_slots`) sobrescreve; F2 (append-only) grava dois pontos e a leitura passa a violar I2. O contrato é silencioso sobre duplicatas |
| F-82 | gorilla-codec | 🟡 | O codec só entrega o ganho na especificação exata: com jitter de ±1 s a compressão de timestamp degrada 6,8× (1,00 → 6,84 bits/ponto, medido). O sistema funciona, mas a tolerância a variação do dado não está declarada em nenhum contrato |
| F-83 | gorilla-codec | 🟢 | `crc32` (zlib) não vem de R1 nem de nenhuma fonte do domínio — é escolha de engenharia. Aceitável, mas deve ser declarada como tal e não como se derivasse do paper |
| F-84 | store-f2 | 🟡 | `crc32` detecta corrupção **acidental**, não autentica: quem escreve recalcula o crc. D5 diz "torna a corrupção detectável" sem essa ressalva, o que superestima a garantia |
| F-85 | usecases | 🟡 | A ordem obrigatória inclui um passo "verificar". Verificar o quê, com qual critério? Não especificado — sem isso o passo é decorativo e a garantia de D5 é retórica |
| F-86 | cli | 🟡 | `--dry-run` de `retain` imprime um plano que depende da marca d'água e de `now`. Entre o preview e a execução real o plano muda — um preview que não corresponde à execução é pior que preview nenhum |
| F-87 | retention | 🟡 | `TierSpec.retention_seconds` conta a partir de quando — do `now` ou do ponto mais novo do acervo? Ambíguo, e as duas leituras divergem exatamente quando a ingestão para |
| F-88 | retention | 🟡 | Sem histerese nem regra de arredondamento na fronteira: um ponto exatamente no limite da janela entra e sai conforme o `now` de cada execução. O comportamento na borda é indefinido |
| F-89 | cli | 🟢 | `info` e `report` têm escopos vizinhos e nomes que não deixam claro qual mostra o quê |
| F-90 | store-port | 🔴 | `atomic_write` via temporário + `rename` assume que temporário e destino estão no MESMO sistema de arquivos: `rename` entre mounts falha com `EXDEV`. V(2) não declara que o temporário é criado no diretório do acervo, logo a atomicidade prometida por D5 pode simplesmente não existir no ambiente do operador |
| F-91 | store-port | 🟡 | `expire()` não declara se é idempotente nem o que devolve quando não há nada a expirar (`0` e `before_ts`? `None`?). Duas implementações vão escolher diferente |
| F-92 | store-port | 🔴 | Duas implementações corretas do MESMO contrato, comportamentos incompatíveis: `write()` com ts não alinhado ao slot — F1 quantiza (ou rejeita?), F2 aceita literalmente. O contrato não diz qual é o certo, logo o mesmo programa dá resultados diferentes conforme o formato |
| F-93 | downsampler | 🟡 | `xFilesFactor` precisa do denominador "quantos pontos deveriam existir no intervalo", derivado de `src_res`. Isso assume resolução nominal exata: com jitter (medido: 6,84 bits/ponto contra 1,00), o denominador é ficção e o `xff` decide com base num número inventado |
| F-94 | store-f2 | 🟡 | O `crc32` é verificado ao ler o chunk. Não há varredura de integridade do acervo: o operador só descobre a corrupção quando lê aquele intervalo específico |
| F-95 | cli | 🟡 | o caminho de exceção do `retain` (o que fazer se falhar entre agregar e expirar) não está definido |
| F-96 | retention | 🟡 | `plan()` é puro e devolve o plano, mas **quem executa o plano não tem módulo** — está no script do `cli`. Remover o `cli` remove a capacidade de aplicar retenção |
| F-97 | usecases | 🟡 | "A migração nunca remove a origem" resolveu o rollback e criou ambiguidade nova: dois acervos com o mesmo `series_name` em formatos diferentes, e **nada marca qual é o vigente**. A próxima ingestão pode ir para o antigo |
| F-98 | store-f1 | 🔴 | O leitor confia em `archiveCount` e `points` lidos do header. Um arquivo corrompido ou hostil com `points=2³²−1` provoca alocação enorme ou leitura fora dos limites. Nenhuma validação de header no contrato |
| F-99 | retention | 🟡 | A política decide o consumo de armazenamento, mas nenhum módulo reporta bytes por tier. O operador configura tiers sem saber quanto cada um custa; o custo a 10× de escala é invisível na hora da decisão |
| F-100 | migrator | 🟡 | `precheck` decide com base em `capabilities()`, que é grosseiro. `ts_bits=32` sinaliza risco, mas a perda real depende DOS DADOS (só há perda se existir ts > 2³¹ ou colisão de slot). Migrações F2→F1 perfeitamente sem perda serão abortadas: falso positivo que bloqueia o caso de uso UC-4 |
| F-101 | cli | 🟡 | Depende dos 11 outros módulos. Não é testável em isolamento, e é o único lugar onde a execução do plano de retenção existe: trocar a interface exigiria reimplementar lógica de domínio |
| F-102 | store-f2 | 🔴 | `formatos-armazenamento.md` §F2 especifica o BLOCO, não o ARQUIVO. Como N blocos são organizados? Concatenação? Índice? Como se acha o bloco que contém `t_from`? Sem isso o módulo não é codificável |
| F-103 | journal | 🟢 | Sem dependências, testável em isolamento, substituível. A lente passou e não encontrou acoplamento |
| F-104 | series | 🟡 | `format_version` existe, mas sem política: ler um acervo de versão anterior deve migrar ou recusar? Campo sem regra apenas move o problema de lugar |
| F-105 | series | 🟡 | `set_tier_state` é chamada separada de `write`. Duas escritas atômicas não formam uma transação: o header e o dado podem divergir mesmo com `atomic_write` correto em cada um |
| F-106 | store-f2 | 🟡 | `read_bits(n)` recebe `n` derivado do próprio stream (5 bits de lead, 6 de comprimento). Um bitstream adversário declara larguras que levam a consumo desproporcional. Sem limite declarado |
| F-107 | cli | 🟡 | `validate-config` valida, e `retain` também. Duas implementações da mesma regra ⇒ duas redações de erro para o mesmo problema, e o operador aprende dois vocabulários |
| F-108 | cli | 🟡 | Nenhum log e nenhum `--verbose`. Todas as operações destrutivas são silenciosas exceto o que o script imprimir por acidente |
| F-109 | cli | 🟢 | `--allow-lossy` destrói dado por design, sem confirmação interativa nem dry-run. Um erro de digitação num script apaga resolução irreversivelmente |
