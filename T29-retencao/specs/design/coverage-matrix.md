# Matriz de cobertura — crítica adversarial

Um achado por linha. Lentes universais (7) + condicionais ativadas (10) aplicadas aos 12
módulos de `specs/technical/architecture.md`. Modo generativo: cada linha é um cenário de
falha concreto, não um juízo de qualidade.

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASM-01 | store-f1 | Assumptions | 🔴 | P-A4 declara timestamps crescentes, mas o layout round-robin de F1 não tem noção de ordem e `check_monotonic` mora em `series`, não na porta. Se o `cli` esquecer de chamar, F1 aceita fora de ordem em silêncio: a invariante I2 é assumida, não imposta na fronteira |
| ASM-02 | retention | Assumptions | 🔴 | `plan(tiers, now, tier_state)` assume que `tier_state` reflete o disco. Se a execução anterior morreu no meio (sem transação), estado e acervo divergem e o plano age sobre uma realidade que não existe. Premissa não declarada: "plano e acervo estão sincronizados" |
| ASM-03 | block | Assumptions | 🟡 | O primeiro delta de 14 bits assume `t₀ ≥ base_ts`. Um ponto com ts anterior ao base do bloco gera delta negativo, não representável em 14 bits sem sinal. Nenhum contrato proíbe esse ponto |
| ASM-04 | downsampler | Assumptions | 🟡 | `xFilesFactor` precisa do denominador "quantos pontos deveriam existir no intervalo", derivado de `src_res`. Isso assume resolução nominal exata: com jitter (medido: 6,84 bits/ponto contra 1,00), o denominador é ficção e o `xff` decide com base num número inventado |
| ASM-05 | dataset-gen | Assumptions | 🟢 | Assume que `seed` fixa dá a mesma sequência entre versões. `random` da stdlib não é contratual entre major versions e `numpy` já trocou de gerador (`RandomState` → `Generator`). Reprodutibilidade do ground truth não declarada |
| ASM-06 | cli | Assumptions | 🟡 | Assume que o operador chama `retain` periodicamente. Retenção é um comando, não um processo: sem agendador externo, nada envelhece e o acervo cresce sem limite — o oposto do propósito do produto. Premissa não declarada |
| ARQ-01 | cli | Architectural | 🟡 | Depende dos 11 outros módulos. Não é testável em isolamento, e é o único lugar onde a execução do plano de retenção existe: trocar a interface exigiria reimplementar lógica de domínio |
| ARQ-02 | retention | Architectural | 🟡 | `plan()` é puro e devolve o plano, mas **quem executa o plano não tem módulo** — está no script do `cli`. Remover o `cli` remove a capacidade de aplicar retenção |
| ARQ-03 | store-f1 | Architectural | 🟢 | `capabilities().random_access=True` não é utilizável por ninguém: a porta não tem `get(ts)`. Ou o campo é morto, ou existe um caminho fora da porta — que quebraria o Hexagonal |
| ARQ-04 | migrator | Architectural | 🟡 | Para fazer `precheck`, o migrator precisa interpretar a semântica de `Capabilities` ("dst mais restritivo que src"). Isso é conhecimento sobre formatos vivendo no módulo que existe justamente para não saber de formatos |
| ARQ-05 | block | Architectural | 🟡 | `CodecState` é estado mutável compartilhado entre `block` (que o guarda) e `gorilla-codec` (que o avança). É exatamente o acoplamento que a fusão de ts-codec+value-codec queria evitar, reaparecendo uma fronteira acima |
| IMP-01 | store-f1 | Implementability | 🔴 | F1 guarda múltiplos archives num arquivo, mas nada especifica como os archives se relacionam com os `TierSpec` de `retention`: quem os cria, com quantos pontos, e o que acontece se a config mudar depois. Não implementável numa sessão sem essa decisão |
| IMP-02 | store-f2 | Implementability | 🔴 | `formatos-armazenamento.md` §F2 especifica o BLOCO, não o ARQUIVO. Como N blocos são organizados? Concatenação? Índice? Como se acha o bloco que contém `t_from`? Sem isso o módulo não é codificável |
| IMP-03 | retention | Implementability | 🟡 | `plan()` recebe `tier_state`, cujo tipo não é definido em nenhum módulo. Sem o tipo, `retention` não é implementável isoladamente |
| IMP-04 | downsampler | Implementability | 🟡 | `Aggregate(ts, min, max, sum, count)` sai do downsampler, mas `Store.write` recebe `Iterator[Point]` e `Point` tem um único `value`. Falta o mapeamento agregado → formato |
| IMP-05 | cli | Implementability | 🟡 | 6 Transaction Scripts + execução do plano de retenção num só módulo: é o maior do sistema e provavelmente não cabe numa sessão com todos os contratos em contexto (viola o princípio E = I₀/C que a própria Fase 1 adotou) |
| SCI-01 | downsampler | Scientific | 🟡 | Dois modelos de agregação coexistem sem decisão: `AGGREGATIONS={average,sum,last,max,min}` (5 métodos de R6) e `Aggregate(min,max,sum,count)` (4 agregados de R9). `average` não está entre os 4; `count` não está entre os 5 |
| SCI-02 | store-f1 | Scientific | 🔴 | R6 fixa `Point = 12 B` com UM valor de 8 bytes por slot. O downsample de R9 preserva QUATRO agregados. **F1 não pode representar um tier agregado** sem violar o layout que a própria fonte define. Contradição entre R6 (formato) e R9 (política) não resolvida |
| SCI-03 | retention | Scientific | 🟡 | I7 exige comparar a janela de retenção com a idade mínima para o downsample seguinte, mas `TierSpec(seconds_per_point, retention_seconds, aggregation, x_files_factor)` não tem campo de idade mínima. Os gatilhos citáveis de R9 (40 h, 10 dias) não têm onde morar |
| SEC-01 | store-f1 | Security | 🔴 | `series` é um nome que vira caminho de arquivo, sem sanitização declarada. `series="../../etc/cron.d/x"` escreve fora do acervo. É a única superfície de entrada externa do sistema |
| SEC-02 | store-f1 | Security | 🔴 | O leitor confia em `archiveCount` e `points` lidos do header. Um arquivo corrompido ou hostil com `points=2³²−1` provoca alocação enorme ou leitura fora dos limites. Nenhuma validação de header no contrato |
| SEC-03 | store-f2 | Security | 🟡 | `read_bits(n)` recebe `n` derivado do próprio stream (5 bits de lead, 6 de comprimento). Um bitstream adversário declara larguras que levam a consumo desproporcional. Sem limite declarado |
| SEC-04 | cli | Security | 🟢 | `--allow-lossy` destrói dado por design, sem confirmação interativa nem dry-run. Um erro de digitação num script apaga resolução irreversivelmente |
| SEC-05 | dataset-gen | Security | 🟡 | duplica: SEC-01 — escreve em caminho fornecido pelo operador, mesmo defeito de ausência de validação de caminho centralizada |
| PRF-01 | store-f2 | Performance | 🟡 | Sem índice de blocos no arquivo (ver IMP-02), `read(t_from, t_to)` é O(tamanho do arquivo) mesmo para um intervalo de 1 minuto. R1 declara o trade-off no nível do BLOCO; aqui ele vaza para o arquivo inteiro |
| PRF-02 | bitstream | Performance | 🟡 | Se o `BitWriter` acumular num único `int` de precisão arbitrária e deslocar, cada `write_bits` copia o acumulado ⇒ **O(n²)** por bloco. Com 7.200 pontos isso é mensurável. Nenhuma decisão de representação (bytearray + offset de bit) foi declarada |
| PRF-03 | migrator | Performance | 🟡 | duplica: RES-02 — sem escrita atômica, uma falha no meio de uma migração de acervo grande perde O(n) de trabalho e deixa o destino em estado ambíguo |
| REG-01 | store-port | Regulatory | 🟡 | A invariante I5 (retenção efetiva ≥ nominal, granularidade de descarte é o bloco) não tem módulo responsável. `expire(series, tier, before_ts) -> int` sugere granularidade de ponto, mas F2 só pode apagar blocos inteiros. Requisito sem rastreabilidade |
| REG-02 | store-port | Regulatory | 🟡 | CA-4 exige razão de compressão medida por perfil, mas `WriteReport{written, rejected, reasons}` conta PONTOS, não BYTES. O critério de aceitação não é computável com os contratos atuais |
| RES-01 | store-f2 | Resilience | 🔴 | Um bit trocado no meio de um bloco corrompe **todos os pontos seguintes** do bloco, porque o estado do decodificador (`prev_bits`, `prev_lead`, `prev_trail`) propaga o erro. Sem checksum, o operador lê valores plausíveis e errados. P-A7 declara a premissa; o cenário permanece sem mitigação |
| RES-02 | store-f2 | Resilience | 🔴 | Escrita não atômica: Ctrl-C, disco cheio ou kill no meio de `write()` deixa bloco truncado. Sem escrever-em-temporário-e-renomear, nem journal |
| RES-03 | store-f1 | Resilience | 🔴 | duplica: RES-02 — mesma ausência de atomicidade, manifestando-se como slots parcialmente escritos |
| RES-04 | store-f2 | Resilience | 🟡 | Um bloco truncado no fim do arquivo é indistinguível de um bloco válido: sem contagem de pontos no header nem marcador de fim, o `BitReader` lê padding como dado |
| RES-05 | cli | Resilience | 🟡 | `retain` agrega e depois expira. Falha entre as duas etapas consome o cru sem gravar o agregado (ou o inverso) ⇒ perda. A ordem obrigatória — gravar o agregado ANTES de expirar o cru — não está declarada em nenhum contrato |
| UX-01 | cli | UI/UX | 🟡 | `retain --now T` obrigatório inverte o modelo mental: o operador quer "aplique a retenção agora". `--now` é instrumento de teste promovido a interface primária |
| UX-02 | cli | UI/UX | 🔴 | Nenhum `--dry-run` em `retain` nem em `migrate`, que são as duas operações destrutivas e irreversíveis (I4). O operador não pode ver o que vai acontecer antes de acontecer |
| UX-03 | cli | UI/UX | 🟡 | `validate-config` valida, e `retain` também. Duas implementações da mesma regra ⇒ duas redações de erro para o mesmo problema, e o operador aprende dois vocabulários |
| UX-04 | cli | UI/UX | 🟡 | `WriteReport.rejected` existe no contrato, mas nada obriga o `ingest` a EXIBIR os rejeitados. Rejeição silenciosa na saída é indistinguível de sucesso |
| UX-05 | cli | UI/UX | 🟢 | O nome do executável (`tsz`) aparece só na tabela de interfaces; não há decisão registrada sobre nome do pacote, do comando nem do diretório de acervo |
| MIG-01 | migrator | Migration / Coexistence | 🔴 | Não há caminho de rollback. O contrato não diz se a origem é preservada ou removida: se removida e o destino estiver errado, não há volta; se preservada, nenhum módulo responde quem apaga e quando |
| MIG-02 | migrator | Migration / Coexistence | 🟡 | `precheck` decide com base em `capabilities()`, que é grosseiro. `ts_bits=32` sinaliza risco, mas a perda real depende DOS DADOS (só há perda se existir ts > 2³¹ ou colisão de slot). Migrações F2→F1 perfeitamente sem perda serão abortadas: falso positivo que bloqueia o caso de uso UC-4 |
| MIG-03 | migrator | Migration / Coexistence | 🟡 | Quando dois pontos de F2 caem no mesmo slot de F1, o contrato diz `rejected`, mas F1 é `mutable_slots=True` e o comportamento natural do formato é SOBRESCREVER. Contrato e formato discordam, e nenhum dos dois é obviamente o certo |
| SUS-01 | retention | Sustainability / Proportionality | 🟡 | A política decide o consumo de armazenamento, mas nenhum módulo reporta bytes por tier. O operador configura tiers sem saber quanto cada um custa; o custo a 10× de escala é invisível na hora da decisão |
| SUS-02 | store-f1 | Sustainability / Proportionality | 🟡 | F1 aloca o arquivo inteiro na criação. Um tier cru a 1 s com 15 dias de retenção = 1,296 M pontos × 12 B = **15,5 MB por série, vazio**. Contra F2 (~1,37 B/ponto do que existe), é 8,8× pior e pago adiantado |
| SUS-03 | downsampler | Sustainability / Proportionality | 🟢 | Preservar 4 agregados quadruplica o custo por ponto do tier reduzido; com resolução 5×/12× menor ainda compensa, mas a conta não está documentada em nenhum lugar |
| PRC-01 | retention | Process / Workflow | 🔴 | A máquina de estados do ponto (cru → 5m → 1h → expirado) não tem estado explícito em nenhum módulo. Sem saber se um intervalo já foi agregado, rodar `retain` duas vezes agrega o mesmo intervalo duas vezes |
| PRC-02 | cli | Process / Workflow | 🟡 | duplica: RES-05 — o caminho de exceção do `retain` (o que fazer se falhar entre agregar e expirar) não está definido |
| PRC-03 | retention | Process / Workflow | 🟡 | Caminho de exceção ausente: o que acontece quando a config de tiers muda DEPOIS de o acervo existir? Tiers removidos ou com resolução alterada deixam dado órfão, e nenhum ator é responsável por migrar a config |
| GOV-01 | retention | Governance / Accountability | 🔴 | O sistema destrói dado de forma irreversível (I4) e não há trilha de auditoria. Depois de um `retain`, ninguém pode responder "o que existia antes, o que foi agregado, o que foi apagado, e quando" |
| GOV-02 | store-port | Governance / Accountability | 🟡 | Nenhuma entidade tem proprietário. `series` é uma string; não há metadado de quem escreveu, quando, com qual versão do software. Um acervo é anônimo e não atribuível |
| GOV-03 | migrator | Governance / Accountability | 🟡 | `MigrationReport.lossless` é a prova de que a migração preservou o dado — e ela morre no stdout. Nada é persistido, logo a afirmação não é auditável depois |
| OBS-01 | store-f2 | Observability / Operability | 🔴 | duplica: RES-01 — sem contagem de pontos nem checksum no header do bloco, a degradação é INDETECTÁVEL sem alterar código: "os valores estão estranhos" não tem instrumento de diagnóstico |
| OBS-02 | cli | Observability / Operability | 🟡 | Nenhum comando de inspeção (`info`/`stat`): tiers existentes, contagem de pontos, bytes por tier, intervalo coberto. O operador não tem como responder "o que tem neste acervo?" |
| OBS-03 | cli | Observability / Operability | 🟡 | Nenhum log e nenhum `--verbose`. Todas as operações destrutivas são silenciosas exceto o que o script imprimir por acidente |
| OBS-04 | cli | Observability / Operability | 🟢 | `report` mede os perfis sintéticos do `dataset-gen`, não o acervo real do operador — cobre CA-4 no laboratório, não em produção |
| CTL-01 | retention | Control Engineering | 🔴 | duplica: PRC-01 — `retain` é um regulador que observa a idade do dado e corrige o acervo, mas nada garante idempotência. Executar com `now` ligeiramente diferente produz drift: agrega duas vezes, ou agrega um intervalo incompleto e nunca o revisita |
| CTL-02 | retention | Control Engineering | 🟡 | Sem histerese nem regra de arredondamento na fronteira: um ponto exatamente no limite da janela entra e sai conforme o `now` de cada execução. O comportamento na borda é indefinido |
| CTL-03 | retention | Control Engineering | 🟡 | O sinal de erro do regulador não é observável: `plan()` devolve o que fazer, mas nada expõe "estado desejado × estado real" de forma inspecionável antes da ação |
| LIN-01 | store-port | Linguistics / Grammar | 🔴 | Duas implementações corretas do MESMO contrato, comportamentos incompatíveis: `write()` com ts não alinhado ao slot — F1 quantiza (ou rejeita?), F2 aceita literalmente. O contrato não diz qual é o certo, logo o mesmo programa dá resultados diferentes conforme o formato |
| LIN-02 | store-port | Linguistics / Grammar | 🔴 | `write()` com o mesmo timestamp duas vezes: F1 (`mutable_slots`) sobrescreve; F2 (append-only) grava dois pontos e a leitura passa a violar I2. O contrato é silencioso sobre duplicatas |
| LIN-03 | store-port | Linguistics / Grammar | 🟡 | `read(t_from, t_to)` — intervalo fechado ou semiaberto? Não declarado. Duas implementações discordarão em exatamente um ponto por consulta, e o erro é invisível para qualquer teste que não olhe a borda |
| LIN-04 | store-port | Linguistics / Grammar | 🟡 | `expire(before_ts) -> int` devolve "int" de quê? F1 responderia em pontos apagados, F2 em blocos. Mesma assinatura, unidades diferentes |
| LIN-05 | store-port | Linguistics / Grammar | 🟡 | duplica: IMP-04 — `Aggregate` não é `Point` e o contrato não define como um tier agregado é escrito |
| LIN-06 | retention | Linguistics / Grammar | 🟡 | `TierSpec.retention_seconds` conta a partir de quando — do `now` ou do ponto mais novo do acervo? Ambíguo, e as duas leituras divergem exatamente quando a ingestão para |
| MEC-01 | store-f1 | Mechanical Engineering | 🔴 | Nenhum campo de versão de formato em F1 nem em F2. Um acervo escrito hoje e lido por uma versão futura com layout alterado é interpretado ERRADO em vez de rejeitado. Tolerância zero disfarçada de simplicidade |
| MEC-02 | gorilla-codec | Mechanical Engineering | 🟡 | O codec só entrega o ganho na especificação exata: com jitter de ±1 s a compressão de timestamp degrada 6,8× (1,00 → 6,84 bits/ponto, medido). O sistema funciona, mas a tolerância a variação do dado não está declarada em nenhum contrato |
| MEC-03 | dataset-gen | Mechanical Engineering | 🟡 | duplica: ASM-05 — variação de versão de `numpy` muda o gerador, muda o ground truth, e o resultado de CA-4 muda sem que nada no produto mude |
| MEC-04 | block | Mechanical Engineering | 🟡 | `BLOCK_SECONDS=7200` é constante de módulo e não é gravada no arquivo. Um acervo escrito com outro valor é decodificado errado em silêncio — parâmetro distinto do de MEC-01, mesma classe de intolerância |

---

## Totais — Iteração 1

| | 🔴 Crítico | 🟡 Importante | 🟢 Sugestão | Total |
|---|---|---|---|---|
| Achados | **19** | **43** | **6** | **68** |

8 achados marcados `duplica:` ⇒ **60 defeitos distintos**.

---

## Iteração 2 — V(2)

Segunda passagem do loop 2↔3, contra a arquitetura V(2) de
`specs/technical/architecture.md`. Mesmo conjunto de lentes (10 condicionais ativadas),
re-declarado contra o novo desenho: os sinais de projeto não mudaram — sistema de arquivos como
dependência externa, CLI operada por pessoa, migração entre formatos, custo de armazenamento
que cresce com o uso, máquina de estados de tiers, destruição irreversível de dado, regulador
que corrige estado a cada execução, duas implementações de uma porta, formatos de vida longa.
As duas ausências (sem dado pessoal, ator único) também seguem valendo.

> **Nota de versionamento:** o contador interno do motor registra `againstVersion: 3` porque
> incrementa a cada iteração da Fase 3. A arquitetura efetivamente criticada nesta rodada é a
> **V(2)** — V(3) ainda não existe; ela será o produto da Fase 3 desta iteração. O cabeçalho
> segue o artefato real, que é o que a rastreabilidade por módulo precisa.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASM-07 | store-port | Assumptions | 🔴 | `atomic_write` via temporário + `rename` assume que temporário e destino estão no MESMO sistema de arquivos: `rename` entre mounts falha com `EXDEV`. V(2) não declara que o temporário é criado no diretório do acervo, logo a atomicidade prometida por D5 pode simplesmente não existir no ambiente do operador |
| ASM-08 | store-f1 | Assumptions | 🔴 | F1 é round-robin (R6): ao dar a volta, **sobrescreve o slot mais antigo por construção**. Isso é um segundo mecanismo de expiração, implícito, coexistindo com o `expire()` explícito de V(2) — e a marca d'água pode apontar para dado que o round-robin já descartou. V(2) não declarou se F1 continua dando a volta |
| ASM-09 | journal | Assumptions | 🟡 | Assume que a trilha cabe em disco indefinidamente. Um produto cujo propósito é limitar o crescimento do dado não limita o crescimento da própria auditoria |
| ASM-10 | retention | Assumptions | 🟡 | A marca d'água assume que o cru nunca chega atrasado. Um ponto com `ts < derived_through_ts` **nunca será agregado** — o intervalo já foi derivado — e o tier derivado fica permanentemente errado, em silêncio |
| ASM-11 | series | Assumptions | 🟡 | `set_tier_state` é chamada separada de `write`. Duas escritas atômicas não formam uma transação: o header e o dado podem divergir mesmo com `atomic_write` correto em cada um |
| ARQ-06 | store-port | Architectural | 🟡 | Acumulou três papéis: o contrato (Protocol), o helper de escrita atômica e a regra de compatibilidade entre formatos. É o padrão que fez `cli` virar módulo-deus na rodada 1, em escala menor |
| ARQ-07 | usecases | Architectural | 🟡 | Herdou dependência de quase tudo (retention, downsampler, store-port, journal, series). ARQ-01 foi **movido**, não eliminado: o fan-in trocou de módulo |
| ARQ-08 | gorilla-codec | Architectural | 🟡 | Ao absorver o bloco, passou a ter duas responsabilidades: codificar pontos e serializar um contêiner (header, `crc32`, `n_points`). E `store-f2` também sabe de contêiner (o prefixo no arquivo). A fronteira de quem é dono do enquadramento ficou dúbia |
| ARQ-09 | journal | Architectural | 🟢 | Sem dependências, testável em isolamento, substituível. A lente passou e não encontrou acoplamento |
| IMP-06 | store-f1 | Implementability | 🔴 | `ArchiveHeader` de V(2) tem 7 campos (`format_version`, `block_seconds`, `created_at`, `writer_version`, `series_name`, `tiers`, `tier_states`). O Metadata de R6 tem **20 bytes e 4 campos**. **Não cabe.** É SCI-02 reaparecendo: V(2) matou o `Aggregate` que F1 não podia representar e criou um header que F1 também não pode |
| IMP-07 | usecases | Implementability | 🟡 | A ordem obrigatória inclui um passo "verificar". Verificar o quê, com qual critério? Não especificado — sem isso o passo é decorativo e a garantia de D5 é retórica |
| IMP-08 | journal | Implementability | 🟡 | `read(acervo)->Iterator[dict]` implica parsing, mas o formato da linha não é definido (JSON Lines? texto delimitado?). Não implementável isoladamente |
| SCI-04 | downsampler | Scientific | 🟡 | D2 provou associatividade para o VALOR (`min`/`max`/`sum`/`last`), mas **não para o `xFilesFactor`**: compor "indefinido" do 5m para o 1h não está documentado em R6 nem em R9. A prova cobre metade do que a cascata faz |
| SCI-05 | gorilla-codec | Scientific | 🟢 | `crc32` (zlib) não vem de R1 nem de nenhuma fonte do domínio — é escolha de engenharia. Aceitável, mas deve ser declarada como tal e não como se derivasse do paper |
| SEC-06 | journal | Security | 🟡 | O journal registra nomes e caminhos. Se a validação de nome vale para o acervo mas não para a escrita da linha, uma quebra de linha no campo injeta uma **linha falsa de auditoria** |
| SEC-07 | store-f2 | Security | 🟡 | `crc32` detecta corrupção **acidental**, não autentica: quem escreve recalcula o crc. D5 diz "torna a corrupção detectável" sem essa ressalva, o que superestima a garantia |
| PRF-04 | store-f2 | Performance | 🟡 | `atomic_write` de arquivo inteiro a cada `write()`: acrescentar um chunk a um acervo de 100 MB reescreve 100 MB. A atomicidade de RES-02 foi comprada ao custo de O(tamanho do acervo) **por append** — num formato cuja razão de ser é ser append-only |
| PRF-05 | journal | Performance | 🟡 | Uma linha por operação mutante com o relatório serializado: um `retain` com vários tiers e intervalos gera muitas linhas, e em acervos pequenos a trilha cresce mais rápido que o dado |
| REG-03 | usecases | Regulatory | 🟡 | CA-2 (F1→F2→F1 preserva a série) não tem verificador: `migrate` compara **contagens**, não igualdade ponto a ponto. O critério de aceitação continua não computável, agora por outro motivo que na rodada 1 |
| RES-06 | usecases | Resilience | 🔴 | A ordem `derivar→gravar→verificar→avançar marca d'água→expirar` tem DUAS escritas atômicas (o dado derivado e o header com a marca d'água). Falha entre elas ⇒ dado gravado, marca d'água não avançada ⇒ a próxima execução deriva o mesmo intervalo e, como ts duplicado agora é **erro** (LIN-02), `retain` passa a falhar **permanentemente**. **A correção de LIN-02 e a de PRC-01 se travam mutuamente** |
| RES-07 | journal | Resilience | 🟡 | Não é especificado se a linha é escrita antes ou depois da operação. Antes: audita o que pode não ter acontecido. Depois: operação sem auditoria se o disco encher. E o journal falhar não pode desfazer o que já ocorreu |
| UX-06 | cli | UI/UX | 🟡 | `--dry-run` de `retain` imprime um plano que depende da marca d'água e de `now`. Entre o preview e a execução real o plano muda — um preview que não corresponde à execução é pior que preview nenhum |
| UX-07 | usecases | UI/UX | 🟡 | Com rejeição como padrão, ingerir um arquivo com um ponto duplicado faz o quê: rejeita o ponto e segue, ou aborta o arquivo? `WriteReport.rejected` sugere seguir, mas o operador provavelmente quer decidir antes de metade estar dentro |
| UX-08 | cli | UI/UX | 🟢 | `info` e `report` têm escopos vizinhos e nomes que não deixam claro qual mostra o quê |
| MIG-04 | usecases | Migration / Coexistence | 🟡 | "A migração nunca remove a origem" resolveu o rollback e criou ambiguidade nova: dois acervos com o mesmo `series_name` em formatos diferentes, e **nada marca qual é o vigente**. A próxima ingestão pode ir para o antigo |
| MIG-05 | series | Migration / Coexistence | 🟡 | `format_version` existe, mas sem política: ler um acervo de versão anterior deve migrar ou recusar? Campo sem regra apenas move o problema de lugar |
| SUS-04 | journal | Sustainability / Proportionality | 🟡 | duplica: ASM-09 — trilha sem limite num produto cujo propósito é limitar crescimento, aqui pela lente do custo |
| SUS-05 | store-f2 | Sustainability / Proportionality | 🟡 | duplica: PRF-04 — escrever N chunks custa O(N²) bytes gravados ao longo da vida do acervo; o desgaste de disco é desproporcional ao dado retido |
| PRC-04 | usecases | Process / Workflow | 🔴 | duplica: RES-06 — o mesmo defeito como processo: falta o estado "derivado mas não confirmado", e sem ele o fluxo não tem caminho de recuperação |
| PRC-05 | retention | Process / Workflow | 🟡 | duplica: ASM-10 — ponto atrasado não tem caminho de exceção definido |
| GOV-04 | journal | Governance / Accountability | 🟡 | O journal é a evidência e nada o protege: arquivo editável no mesmo diretório, sem encadeamento de hash. Serve contra erro operacional, não contra alteração deliberada — e V(2) não declara qual dos dois pretende ser |
| GOV-05 | usecases | Governance / Accountability | 🟡 | `migrate` registra no journal da origem, do destino ou dos dois? Se só num, metade da história desaparece justamente na operação que move o acervo |
| OBS-05 | store-f2 | Observability / Operability | 🟡 | O `crc32` é verificado ao ler o chunk. Não há varredura de integridade do acervo: o operador só descobre a corrupção quando lê aquele intervalo específico |
| OBS-06 | usecases | Observability / Operability | 🟡 | `journal.read()` existe no contrato e não é exposto por comando algum: `info` mostra o estado atual, e o histórico fica ilegível na prática |
| CTL-04 | retention | Control Engineering | 🟡 | A marca d'água torna `retain` idempotente **e irreversível**: se a config mudar (um `xff` corrigido), o intervalo já derivado não é recomputado. Sem reset da marca d'água, um erro de configuração fica congelado no tier derivado para sempre |
| CTL-05 | retention | Control Engineering | 🟢 | `min_age` + marca d'água dão histerese real; CTL-02 da rodada 1 está resolvido e a lente não encontra oscilação nova |
| LIN-07 | store-port | Linguistics / Grammar | 🔴 | `write()` rejeita ts desalinhado se `aligned_writes_required`, mas o contrato não diz **alinhado a partir de qual época**. Sem origem declarada, F1 e F2 podem discordar sobre o que "alinhado" significa — é LIN-01 reaparecendo um nível abaixo, na definição do próprio predicado |
| LIN-08 | store-port | Linguistics / Grammar | 🟡 | `expire()` não declara se é idempotente nem o que devolve quando não há nada a expirar (`0` e `before_ts`? `None`?). Duas implementações vão escolher diferente |
| LIN-09 | journal | Linguistics / Grammar | 🟡 | `append(acervo, op:str, report:dict)` — `op` é string livre. Duas partes do código escreverão `"retain"` e `"retention"`, e a trilha fica inagregável: é exatamente o defeito que a coluna `lens` desta matriz evita com nomes canônicos |
| MEC-05 | series | Mechanical Engineering | 🟡 | duplica: MIG-05 — `writer_version` existe sem tolerância definida: ler acervo escrito por versão mais nova é erro ou aviso? |
| MEC-06 | gorilla-codec | Mechanical Engineering | 🟡 | `MAX_BLOCK_SECONDS=14400` protege o campo de 14 bits, mas `block_seconds` agora vem do header do acervo — **dado externo**. Um acervo com `block_seconds=20000` é aceito na leitura e só falha ao decodificar: falta validação de tolerância na borda de entrada |

## Totais — Iteração 2

| | 🔴 Crítico | 🟡 Importante | 🟢 Sugestão | Total |
|---|---|---|---|---|
| Achados | **6** | **31** | **4** | **41** |

5 achados marcados `duplica:` ⇒ **36 defeitos distintos**.

### Comparação entre rodadas

| | Iteração 1 — V(1) | Iteração 2 — V(2) | |
|---|---|---|---|
| Achados | 68 | **41** | −40% |
| 🔴 Críticos | 19 | **6** | −68% |
| Defeitos distintos | 60 | **36** | −40% |
| Módulos com 🔴 | 8 | **5** | −38% |

A queda é evidência de convergência, não de crítica mais frouxa: as mesmas 17 lentes foram
aplicadas aos mesmos 12 módulos. Mas **dois dos 6 críticos são de uma classe nova e pior** —
são defeitos *criados pelas correções* da Fase 3 (RES-06 e IMP-06), que é precisamente o que o
princípio de assimetria prevê quando correções individualmente certas se encontram.
