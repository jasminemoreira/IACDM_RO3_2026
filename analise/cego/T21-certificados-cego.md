# Reagrupamento cego de achados — T21-certificados

Você recebe 110 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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
| M-01 | certificado | Modelo da observação de um certificado X.509 e cálculos derivados de validade. Domínio puro. | `deDer(der) -> Observacao{fingerprint256,issuer,serial,notBefore,notAfter,san[]}` · `vidaTotalDias(o) -> number` · `restanteDias(o, agora) -> number` · `semExpiracao(o) -> boolean` | — |
| M-02 | politica-limiar | Limiares configuráveis e classificação do estado de um alvo. Guarda o invariante `limiar < vidaTotal`. Domínio puro. | `validarLimiares(l, vidaTotalDias) -> Ok \| ErroConfig` · `classificar(o, l, agora) -> 'ok'\|'aviso'\|'atencao'\|'critico'\|'expirado'\|'sem-expiracao'` | certificado |
| M-03 | pedido | Entidade Pedido e sua máquina de estados `pendente -> aprovado -> fechado`. Transição inválida é impossível por construção. | `abrir(alvoId, solicitanteId, agora) -> Pedido` · `aprovar(p, aprovador, agora) -> Ok(Pedido) \| ErroTransicao` · `fechar(p, evidencia, agora) -> Ok(Pedido) \| ErroTransicao` | autorizacao |
| M-04 | reconciliacao | Compara a observação nova com a anterior e com os pedidos abertos, e decide o que aconteceu: emissão aprovada, troca não autorizada, ou escalação por inação. Domínio puro. | `reconciliar(anterior, atual, pedidoAberto, estado) -> Decisao[]` onde `Decisao = {tipo:'fechar-pedido',pedidoId,evidencia} \| {tipo:'troca-nao-autorizada',alvoId,evidencia} \| {tipo:'escalar',alvoId} \| {tipo:'nenhuma'}` | certificado, politica-limiar, pedido |
| M-05 | trilha | Trilha append-only encadeada por hash e sua verificação. Domínio puro. | `anexar(hashAnterior, evento) -> Entrada{i,evento,hashAnterior,hash}` · `verificar(entradas[]) -> {valida, quebraNoIndice?}` | — |
| M-06 | autorizacao | Atores, papéis (`solicitante`/`aprovador`/`auditor`) e verificação de credencial. | `criarAtor(nome, senha, papel) -> Ator` (scrypt) · `autenticar(ator, senha) -> boolean` (timingSafeEqual) · `podeAprovar(ator) -> boolean` | — |
| M-07 | relogio | Porta de tempo. Fonte única do "agora" em UTC — nenhum outro módulo chama `new Date()`. | `agora() -> Date` | — |
| M-08 | sonda-tls | Adaptador de saída: handshake TLS contra `host:porta` e devolução do certificado servido em DER. Inspeciona certificado inválido (`rejectUnauthorized: false`). | `sondar(host, porta, timeoutMs) -> Promise<Ok(der) \| ErroSonda{tipo:'timeout'\|'recusado'\|'dns'\|'tls'}>` | — |
| M-09 | repositorio | Porta de persistência (Repository) + Data Mapper sobre `node:sqlite`. Única fronteira com o banco. | `salvarAlvo(a)` · `listarAlvos()` · `ultimaObservacao(alvoId)` · `salvarObservacao(alvoId, o)` · `pedidoAbertoDe(alvoId)` · `salvarPedido(p)` · `anexarTrilha(entrada)` · `pontaTrilha()` · `listarTrilha(filtro)` · `buscarAtor(nome)` | certificado, pedido, trilha, autorizacao |
| M-10 | casos-de-uso | Camada de aplicação: orquestra domínio e portas. Único lugar onde a sequência de uma operação vive. | `varrer() -> RelatorioVarredura` · `abrirPedido(alvoId, solicitante)` · `aprovarPedido(pedidoId, aprovador)` · `auditar(filtro) -> Entrada[]` · `verificarIntegridade() -> {valida, quebraNoIndice?}` | todos os anteriores |
| M-11 | web-ui | Adaptador de entrada: servidor `node:http`, 5 telas em HTML renderizado e sessão. Nenhuma regra de domínio. | `GET /login \|/painel \|/alvo/:id \|/trilha` · `POST /login \|/alvos \|/varrer \|/pedidos \|/pedidos/:id/aprovar` | casos-de-uso |
| M-01 | certificado | Modelo da observação a partir da **cadeia inteira** servida e cálculos de validade. Domínio puro. | `deCadeia(ders[]) -> Ok(Observacao{fingerprint256,issuer,subject,serial,san[],notBefore,notAfterFolha,notAfterEfetivo,profundidade}) \| ErroParsing` · `vidaTotalDias(o)` · `restanteDias(o, agora)` · `semExpiracao(o)`. **Pré-condições:** `ders` não vazio; SAN ausente vira `[]`; subject vazio é aceito; `notAfter >= 2050` usa GeneralizedTime | — |
| M-02 | politica-limiar | Limiares por alvo, classificação de urgência e decisão de escalação. Guarda o invariante `limiar < vidaTotal`. Domínio puro. | `validarLimiares(l, vidaTotalDias) -> Ok \| ErroConfig` · `classificar(o, l, agora) -> {urgencia:'ok'\|'aviso'\|'atencao'\|'critico'\|'expirado'\|'ainda-nao-valido', semExpiracao:boolean}` · `deveEscalar(urgencia, temPedidoAberto) -> boolean`. Dias por **truncamento** | certificado |
| M-03 | pedido | Entidade e máquina de estados completa, **sem estado órfão**. Recebe o papel como valor. | estados: `pendente\|aprovado\|fechado\|rejeitado\|cancelado\|expirado-sem-emissao` · `abrir(alvoId, solicitanteId, agora)` · `aprovar(p, atorId, papel, agora)` · `rejeitar(p, atorId, papel, motivo, agora)` · `cancelar(p, atorId, agora)` · `fechar(p, evidenciaId, agora)` · `expirarSemEmissao(p, agora)` — todas devolvendo `Ok(Pedido) \| ErroTransicao` | — |
| M-04 | reconciliacao | Decide **exclusivamente** o que aconteceu com o certificado entre duas observações. Não classifica urgência, não escala. Domínio puro. | `reconciliar({anterior, atual, pedidoAprovado, agora}) -> 'primeira-observacao' \| 'sem-mudanca' \| 'emissao-aprovada' \| 'troca-nao-autorizada' \| 'mudanca-sem-avanco'`. **Pré-condições:** `anterior` pode ser `null` (⇒ `primeira-observacao`, nunca troca não autorizada); `pedidoAprovado` contém **apenas** pedidos em estado `aprovado` | certificado, pedido |
| M-05 | trilha | Cadeia append-only e sua verificação, com serialização canônica. Domínio puro. | `anexar(hashAnterior, evento, agora) -> Entrada{i,tipo,payload,hashAnterior,hash}` · `verificar(entradas[]) -> {valida, quebraNoIndice?}` · payload em JSON de chaves ordenadas, datas ISO UTC, hash sha256 hex. Tipos de evento: enumeração fechada em `specs/models/schema.md` | — |
| M-06 | autorizacao | Atores, papéis e credencial. Parâmetros de scrypt com fonte. | `criarAtor(nome, senha, papel) -> Ator` · `autenticar(ator, senha) -> boolean` · `papelDe(ator) -> Papel` · `desativar(ator)`. Parâmetros em `specs/technical/parameters.md` | — |
| M-07 | relogio | Fonte única do tempo **e** detecção de retrocesso. Nenhum outro módulo chama `new Date()`. | `agora() -> Date` (UTC) · `verificarMonotonia(ultimoCarimbo) -> Ok \| Retrocesso{delta}` | — |
| M-08 | sonda-tls | Handshake TLS e devolução da **cadeia completa** servida, preservando o erro original. | `sondar(host, porta) -> Promise<Ok(ders[]) \| ErroSonda{tipo:'timeout'\|'recusado'\|'dns'\|'tls'\|'cadeia-grande', detalhe}>`. Timeout 10 s, 1 retentativa, máximo 10 certificados. Exige TLS direto na porta | — |
| M-09 | repositorio | **Quatro portas nomeadas** atendidas por um adaptador `node:sqlite`. Única fronteira com SQL, statements sempre parametrizados. | `PortaAlvos{salvar,listar,remover,buscar}` · `PortaPedidos{salvar,abertoDe,aprovadoDe,listar}` · `PortaTrilha{anexar,ponta,listar}` · `PortaAtores{buscar,salvar}` · `emTransacao(fn)` — **única forma de escrita**. DDL em `specs/models/schema.md` | certificado, pedido, trilha, autorizacao |
| M-10 | caso-varredura | Fluxo de observação: sondar, reconciliar, decidir, persistir — tudo em uma transação por alvo. | `varrer(deps) -> RelatorioVarredura{varreduraId, total, ok, falhas[], decisoes[]}`. Falha de um alvo **não aborta** os demais; grava observação **só quando o fingerprint muda**; registra `varredura-iniciada`/`varredura-concluida` na trilha | sonda-tls, certificado, politica-limiar, reconciliacao, pedido, trilha, repositorio, relogio |
| M-11 | caso-governanca | Fluxo humano: inventário, política, pedidos e auditoria — **todos atribuíveis**. | `cadastrarAlvo` · `removerAlvo` · `alterarLimiares` · `abrirPedido` · `aprovarPedido` · `rejeitarPedido` · `cancelarPedido` · `justificarTroca` · `auditar(filtro)` · `verificarIntegridade()`. Toda operação exige ator autenticado e anexa entrada na trilha | pedido, autorizacao, politica-limiar, trilha, repositorio, relogio |
| M-12 | web-ui | Adaptador de entrada: 6 telas, sessão e proteção de formulário. Nenhuma regra de domínio. | telas: `login`, `painel`, `cadastro-de-alvo`, `alvo/:id`, `pedido/:id`, `trilha` · `GET /login /painel /alvos/novo /alvo/:id /pedido/:id /trilha` · `POST /login /logout /alvos /alvos/:id/remover /alvos/:id/limiares /varrer /pedidos /pedidos/:id/aprovar /pedidos/:id/rejeitar /pedidos/:id/cancelar /alvo/:id/justificar`. **Bind fixo em 127.0.0.1**; token CSRF por formulário; escape obrigatório de todo dado vindo de certificado; cookie `HttpOnly; SameSite=Strict`, sessão expira em 30 min | caso-varredura, caso-governanca |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | web-ui | 🟡 | a tela de trilha não declara como comunicar tamper-evident × tamper-proof. Sem isso o operador lê "válida" como "impossível de forjar" e confia além do que o sistema garante |
| F-02 | autorizacao | 🟡 | sem limite de tentativas nem atraso progressivo no login — força bruta contra a senha do Aprovador sem custo |
| F-03 | repositorio | 🟢 | as 4 portas nomeiam a mesma ideia de formas diferentes (`buscar` em Alvos e Atores, `abertoDe`/`aprovadoDe` em Pedidos, `ponta` em Trilha) — atrito desnecessário entre implementações feitas em sessões separadas |
| F-04 | repositorio | 🟢 | arquivo de banco ausente ou corrompido não tem caminho de recuperação nem de diagnóstico declarado |
| F-05 | trilha | 🟡 | auditoria exige carimbo temporal confiável; a trilha carimba com `relogio.agora()` da própria máquina, sem detecção de retrocesso do relógio — entradas podem ficar fora de ordem cronológica sem quebrar a cadeia de hash |
| F-06 | certificado | 🟡 | assume que "o certificado do host" é um só. `getPeerX509Certificate()` devolve o leaf; a cadeia servida pode ter intermediário que expira ANTES dele. Intermediário vencido derruba o serviço com o leaf válido — a falha que o produto existe para prevenir, invisível ao design. Premissa não declarada em A1-A8 |
| F-07 | repositorio | 🟡 | nenhuma entidade declara dono. "Quem responde por este certificado?" não tem resposta no modelo, embora seja a primeira pergunta de qualquer auditoria |
| F-08 | reconciliacao | 🟡 | o laço observar→comparar→corrigir não tem watchdog de si mesmo: se a varredura deixa de ser disparada, nada gera sinal de erro. O sistema não regula o próprio ciclo, só reage quando invocado |
| F-09 | trilha | 🟢 | `PER-03` não foi resolvido, apenas indexado: `verificar` continua lendo a cadeia inteira, e a cadeia só cresce |
| F-10 | web-ui | 🟡 | `POST /varrer` executa a varredura inteira dentro da requisição, sem progresso — o browser expira antes do fim em inventários grandes |
| F-11 | caso-governanca | 🟡 | `alterarLimiares` assume efeito só para frente. As observações já gravadas não são reclassificadas, então o painel pode exibir estado calculado sob a política antiga sem indicar isso |
| F-12 | repositorio | 🟡 | `verificarIntegridade()` lê a cadeia inteira e `listarTrilha` percorre estrutura que só cresce: custo O(n) crescente a cada varredura, sem índice nem paginação declarados |
| F-13 | caso-governanca | 🟡 | `removerAlvo` sem `ON DELETE` definido no DDL: auditoria exige que observações e pedidos históricos sobrevivam à remoção do alvo, e o esquema atual ou apaga em cascata ou falha por chave estrangeira |
| F-14 | repositorio | 🟡 | um único Repository para 4 agregados (certificado, pedido, trilha, autorizacao). Trocar a persistência de um força mexer no módulo inteiro; a fronteira não é substituível por partes |
| F-15 | caso-varredura | 🟡 | assume UM pedido aprovado por alvo. `PortaPedidos.aprovadoDe` pode devolver vários (dois aprovados para o mesmo alvo), mas `reconciliar` recebe `pedidoAprovado` no singular — qual deles a emissão fecha não está definido |
| F-16 | politica-limiar | 🟢 | CA/B SC-081v3 muda a validade máxima ao longo do tempo (200 d hoje, 100 d em 2027, 47 d em 2029). Nenhum módulo registra sob qual regime a classificação foi feita — auditoria futura não sabe qual regra valia |
| F-17 | web-ui | 🟢 | existe `POST /alvo/:id/justificar` mas nenhuma tela declarada onde a justificativa é escrita |
| F-18 | trilha | 🟡 | a trilha nomeia pessoas e é imutável por construção. Um registro errado (ator errado, sessão compartilhada) não pode ser retificado, apenas anexado — e nenhum procedimento de retificação está declarado |
| F-19 | web-ui | 🟡 | sessão sem expiração declarada e sem flags de cookie (HttpOnly, SameSite, Secure). Sessão esquecida aberta = aprovação disponível a quem sentar na máquina |
| F-20 | certificado | 🟡 | RFC 5280 §4.1.2.5 exige suportar UTCTime E GeneralizedTime; `deDer` não declara tratamento de `notAfter` a partir de 2050, faixa em que UTCTime deixa de valer |
| F-21 | reconciliacao | 🟡 | assume que existe observação anterior. Na PRIMEIRA varredura de um alvo `anterior = null` e o contrato não define o resultado — risco de classificar cadastro novo como troca não autorizada |
| F-22 | caso-governanca | 🔴 | `justificarTroca` aceita QUALQUER ator autenticado — inclusive o que fez a troca por fora. Quem burla tem, por definição, acesso ao sistema: ele mesmo justifica a própria troca e o destaque desaparece. O mecanismo criado na Fase 3 para encarecer a burla é operável pelo burlador |
| F-23 | pedido | 🔴 | a máquina de estados não tem caminho de rejeição nem de cancelamento. Pedido aberto por engano, ou recusado pelo Aprovador, fica `pendente` para sempre — estado órfão, e "recusar" é uma decisão de governança tão legítima quanto aprovar |
| F-24 | autorizacao | 🟡 | os parâmetros do scrypt não têm fonte citada. RFC 7914 e as recomendações OWASP dão valores concretos; nenhum aparece em specs/technical, violando a regra "nenhum parâmetro numérico sem referência" |
| F-25 | web-ui | 🟡 | nenhum endereço de bind declarado. Se o servidor escutar em 0.0.0.0, a aplicação "local" fica exposta à rede inteira, com login sem TLS |
| F-26 | pedido | 🟢 | o mesmo ator pode abrir e aprovar (segregação está fora de escopo por decisão), mas a trilha não MARCA a auto-aprovação como tal — o auditor não consegue filtrá-la |
| F-27 | caso-governanca | 🟢 | `cancelarPedido` não restringe o estado de origem: cancelar um pedido já aprovado apagaria o efeito de uma aprovação registrada |
| F-28 | repositorio | 🟢 | nenhuma declaração de uso de statements parametrizados; com Data Mapper escrito à mão, concatenação de SQL é o caminho de menor esforço |
| F-29 | web-ui | 🟢 | nada captura o que foi exibido ao Aprovador no momento da decisão; aprovar em lote sem examinar é indistinguível de aprovar com análise |
| F-30 | web-ui | 🟢 | expiração de sessão em 30 min entrou sem fonte citada — é o único parâmetro de V(2) que escapou de `specs/technical/parameters.md` |
| F-31 | trilha | 🟢 | `anexar` não define o formato canônico do evento nem o encoding do hash (hex ou base64) — duas implementações produzem cadeias incompatíveis |
| F-32 | relogio | 🟡 | a porta devolve o tempo do SO sem verificação de sanidade nem monotonia. A2 está declarada, porém NENHUM módulo consegue detectá-la falsa: relógio adiantado marca tudo expirado, atrasado esconde vencimento — e a trilha carimba com o mesmo relógio |
| F-33 | repositorio | 🟡 | trilha e observações crescem indefinidamente, sem política de retenção nem arquivamento. O custo cresce com o uso e nada no design o limita |
| F-34 | pedido | 🟡 | entidade de domínio depende de `autorizacao` só para consultar `podeAprovar`. Bastaria receber o papel como valor — acoplamento evitável entre agregado e identidade |
| F-35 | caso-governanca | 🟡 | a justificativa encerra o assunto sem revisão: nada distingue "justificada e aceita" de "justificada e contestada". Quem foi acusado escreve a própria defesa e ela vale como resolução final |
| F-36 | caso-governanca | 🟡 | 10 operações num módulo: herdou parte do problema que motivou dividir `casos-de-uso`. Auditoria (leitura pura, sem transação) e governança (escrita transacional atribuível) têm naturezas e dependências distintas |
| F-37 | casos-de-uso | 🟢 | persistir observação idêntica a cada varredura gasta armazenamento sem entregar informação |
| F-38 | sonda-tls | 🔴 | os 4 tipos de erro estão declarados, mas o design NÃO diz o que a varredura faz com eles. Se o alvo mantém o estado anterior, o painel exibe dado velho como atual — o monitor falha silenciosamente exatamente quando o host está com problema |
| F-39 | autorizacao | 🟡 | `criarAtor` não define os parâmetros do scrypt (N, r, p, keylen, tamanho e origem do salt) nem o formato de armazenamento do hash |
| F-40 | politica-limiar | 🟡 | limiar é configuração de runtime que reclassifica o inventário inteiro no instante em que muda. Um alvo pode oscilar entre `critico` e `ok` conforme alguém ajusta a configuração, sem que o estado anterior fique registrado |
| F-41 | politica-limiar | 🟡 | `validarLimiares(l, vidaTotalDias)` compara limiar global com vida POR certificado, mas não diz QUANDO validar: no cadastro do alvo (quando ainda não há certificado) ou a cada varredura? CA-5 depende dessa resposta |
| F-42 | repositorio | 🟡 | `emTransacao` como única forma de escrita é convenção, não imposição: nada no contrato impede um módulo de obter o handle do banco e escrever fora da transação e fora da trilha |
| F-43 | sonda-tls | 🟡 | sem retry nem backoff: host lento intermitente vira falso "inalcançável", e o operador aprende a ignorar |
| F-44 | web-ui | 🟡 | `troca-nao-autorizada` e `escalado` não têm representação declarada no painel. São as duas informações mais importantes do produto e não há onde exibi-las |
| F-45 | sonda-tls | 🟢 | o tipo de erro é classificado em 4 categorias mas o motivo original (mensagem do handshake) é descartado — diagnosticar por que um host falha exige alterar o código |
| F-46 | sonda-tls | 🟢 | `ErroSonda.tipo='tls'` é vago: cobre certificado ilegível, versão de protocolo incompatível e cadeia inválida sem distingui-los |
| F-47 | pedido | 🟡 | a convenção `Ok \ | Erro` não tem forma canônica declarada (`{ok:true,valor}` vs `{tipo:'ok'}` vs tupla). 11 módulos a implementarão independentemente e não vão compor |
| F-48 | web-ui | 🔴 | o contrato lista rotas mas não define o HTML das telas, os campos de cada formulário, nem o mecanismo de sessão (cookie? assinado? expira quando?). Uma sessão dedicada de implementação teria de inventar tudo isso — exatamente o que AP7 proíbe |
| F-49 | reconciliacao | 🟡 | aprovação não expira: um pedido `aprovado` cujo host só troca o certificado meses depois fecha com uma autorização velha, dissociada do contexto em que foi dada |
| F-50 | reconciliacao | 🔴 | contrato ambíguo em dois pontos: (a) `pedidoAberto` inclui estado `aprovado` ou apenas `pendente`? (b) recebe `estado` já classificado mas declara dependência de `politica-limiar` — duas implementações corretas do contrato divergem sobre quem classifica. Como a Fase 5 implementa módulos em sessões separadas, a ambiguidade vira incompatibilidade real |
| F-51 | web-ui | 🔴 | há `POST /alvos` mas nenhuma das 5 telas declaradas é o cadastro de alvo. UC-1 (colocar um host sob monitoramento) não pode ser executado pela interface — o caso de uso de entrada do produto não tem porta |
| F-52 | repositorio | 🔴 | nenhum esquema de banco definido: sem tabelas, colunas, tipos, chaves ou índices. 10 operações declaradas e zero DDL — o módulo não é implementável a partir do documento |
| F-53 | reconciliacao | 🟡 | `mudanca-sem-avanco` (fingerprint mudou, `notAfter` não avançou) é devolvido sem consumidor definido: `caso-varredura` não declara o que faz com esse valor — rollback de certificado fica sem tratamento |
| F-54 | web-ui | 🟡 | sessão de 30 min sem rotação do identificador após autenticação — fixação de sessão: um identificador conhecido antes do login continua válido depois dele |
| F-55 | relogio | 🟡 | `verificarMonotonia` detecta o retrocesso mas o contrato não diz o que o sistema FAZ com ele: aborta a varredura, registra e continua, ou recusa gravar na trilha? |
| F-56 | pedido | 🟢 | sem histerese nas fronteiras: com arredondamento de dias, um alvo em 30,0 dias pode alternar de estado entre varreduras consecutivas sem que nada real tenha mudado |
| F-57 | caso-varredura | 🟡 | "gravar observação só quando o fingerprint muda" ainda exige escrever `visto_ultima_vez` a cada varredura — a economia é menor que o previsto. Pior: mudança de política reclassifica sem nova observação, dessincronizando painel e histórico |
| F-58 | casos-de-uso | 🟡 | não declara se uma falha no meio da varredura aborta o restante ou continua. Um alvo com timeout pode impedir a varredura dos demais |
| F-59 | web-ui | 🟡 | sem qualquer feedback durante a varredura, o operador não distingue "processando" de "travado" e dispara de novo |
| F-60 | pedido | 🟡 | não há transição definida para o pedido cujo alvo atinge `expirado` antes da emissão — o pedido continua aberto sobre um certificado já morto |
| F-61 | repositorio | 🟡 | sem transação declarada envolvendo salvar observação + anexar trilha + fechar pedido. Falha entre as três deixa estado e trilha divergentes — e a trilha é a prova do produto |
| F-62 | caso-varredura | 🟡 | a retentativa única introduzida contra `RES-04` dobra o pior caso da varredura sequencial: 50 alvos inalcançáveis × 2 tentativas × 10 s = 16 min |
| F-63 | repositorio | 🟡 | `PRAGMA journal_mode = WAL` combinado com trava exclusiva de escrita é contraditório: WAL existe para permitir leitores concorrentes com um escritor, e a trava exclusiva anula o motivo de usá-lo |
| F-64 | web-ui | 🟡 | o painel não exibe a idade do dado. Um inventário varrido há um mês é visualmente idêntico a um varrido agora — a UI apresenta como fato presente o que é registro histórico |
| F-65 | trilha | 🟡 | assume serialização determinística do evento para o hash. Se o evento for serializado com `JSON.stringify`, ordem de chaves e formato de `Date` variam entre implementações/versões: a cadeia acusa adulteração onde não houve, tornando CA-4 falso-positivo |
| F-66 | politica-limiar | 🟢 | o estado `sem-expiracao` tem base normativa para o VALOR (sentinela 99991231235959Z, RFC 5280 §4.1.2.5) mas nenhuma fonte para a CONDUTA de um monitor diante dele |
| F-67 | certificado | 🟡 | `notAfterEfetivo = min(cadeia)` assume que todo certificado servido pertence à cadeia de confiança em uso. Servidores costumam servir cross-signed ou raízes extras; um certificado irrelevante com validade curta vira alarme permanente que nenhuma renovação resolve |
| F-68 | relogio | 🟢 | não declara que a implementação deve devolver UTC. Uma implementação que devolva hora local passa nos testes na máquina de origem e erra por horas em outro fuso |
| F-69 | casos-de-uso | 🔴 | o caminho de menor esforço para o operador é trocar o certificado direto no host e ignorar o sistema. O produto não tem poder algum sobre o host — só registra. Se a consequência de burlar é um destaque no painel que o próprio burlador administra, o equilíbrio racional é burlar |
| F-70 | pedido | 🟡 | `expirarSemEmissao` é transição declarada que nenhum caso de uso chama — `caso-varredura` não a lista entre suas operações. Transição órfã, o inverso do estado órfão de `PRO-01` |
| F-71 | trilha | 🟡 | `justificarTroca` assume que existe um evento `troca-nao-autorizada` ao qual se referir, mas nada no contrato liga a justificativa a um evento específico — com duas trocas não autorizadas no mesmo alvo, não se sabe qual foi justificada |
| F-72 | certificado | 🟡 | o contrato assume campos presentes. Certificado sem SAN, com subject vazio ou algoritmo incomum é variação normal do mundo real e não tem comportamento definido |
| F-73 | autorizacao | 🟡 | assume que existe pelo menos um Aprovador cadastrado. Nada no design diz quem cria o primeiro ator; sem ele nenhum pedido pode ser aprovado e o sistema nasce travado |
| F-74 | sonda-tls | 🟡 | `timeoutMs` aparece na assinatura sem valor nem fonte. Timeout de handshake é parâmetro operacional com prática documentada; será inventado na Fase 5 se não for depositado antes |
| F-75 | repositorio | 🟡 | nenhuma faixa de versão de Node declarada, embora o módulo dependa de API experimental (`node:sqlite`) e o projeto inteiro dependa de type-stripping nativo. O sistema só tolera a especificação exata da máquina onde foi escrito |
| F-76 | repositorio | 🟢 | `falha_sonda` grava uma linha por alvo falho por varredura, sem deduplicação: um host permanentemente fora produz uma linha nova a cada execução |
| F-77 | sonda-tls | 🟡 | `rejectUnauthorized:false` é necessário e correto aqui, mas não há limite declarado de tamanho de cadeia nem de tempo total: host malicioso responde com cadeia enorme e consome memória do monitor |
| F-78 | sonda-tls | 🟡 | assume TLS direto no `connect`. Serviços com STARTTLS (SMTP 587, IMAP 143, PostgreSQL 5432) negociam depois do protocolo em claro: a sonda falha e o certificado fica invisível, contradizendo A1 ("todo certificado de interesse exposto em TLS alcançável") |
| F-79 | casos-de-uso | 🟡 | não existe registro persistente das varreduras (quando rodou, quantos alvos, quantas falhas). O operador não consegue responder "a última varredura foi quando?" sem inspecionar o banco |
| F-80 | caso-varredura | 🟡 | processo morto no meio da varredura deixa `varredura.concluida_em` NULL para sempre, sem caminho de reconciliação — varreduras órfãs acumulam e a contagem de falhas fica errada |
| F-81 | caso-varredura | 🟡 | a relação entre "uma transação por alvo" e o registro global `varredura-iniciada`/`varredura-concluida` não está definida: em qual transação `varredura.concluida_em` é escrita, e o que acontece com ela se o último alvo falhar? |
| F-82 | trilha | 🟢 | SHA-256 escolhido sem referência de adequação para encadeamento de auditoria; a escolha é razoável mas não citada |
| F-83 | autorizacao | 🟡 | a criação de atores não é atribuível — quem criou o Aprovador não fica registrado, e é o ato que confere todo o poder do sistema |
| F-84 | web-ui | 🟡 | token CSRF é exigido mas não especificado: onde é gerado, onde é guardado, escopo por sessão ou por formulário, e qual o comportamento quando expira. Implementável de três formas incompatíveis |
| F-85 | politica-limiar | 🟡 | o enum mistura duas dimensões: `ok/aviso/atencao/critico/expirado` são níveis de urgência, `sem-expiracao` é propriedade do certificado. Forçar as duas num tipo só produz decisões arbitrárias (certificado sem expiração é `ok`?) |
| F-86 | web-ui | 🔴 | formulários POST com sessão por cookie e nenhuma proteção CSRF declarada. Uma página maliciosa aberta no mesmo browser submete `POST /pedidos/:id/aprovar` e forja a aprovação — destrói exatamente a garantia que o produto vende |
| F-87 | casos-de-uso | 🟡 | o papel Auditor não participa de nenhuma transição — existe como permissão de leitura, sem responsabilidade no processo. Ator declarado sem fluxo |
| F-88 | trilha | 🟢 | não há exportação da trilha; um auditor externo depende do próprio sistema auditado para ler o que ele registrou sobre si |
| F-89 | caso-varredura | 🟡 | `PER-02`/`UX-03` só foram parcialmente resolvidos: `RelatorioVarredura` é devolvido no fim, e o POST síncrono continua sem progresso incremental durante a execução |
| F-90 | reconciliacao | 🟢 | recebe `estado` já classificado E declara dependência de `politica-limiar` — ou classifica, ou recebe classificado. Dependência declarada sem uso claro |
| F-91 | casos-de-uso | 🔴 | cadastrar/remover alvo e alterar limiares não passam pela trilha. Afrouxar o limiar de 30 para 5 dias, ou remover um alvo do inventário, é mais poderoso que aprovar um pedido — e é o único ato do sistema sem autor atribuível |
| F-92 | repositorio | 🟢 | A6 declara "uma varredura por vez", mas nada impede duas instâncias do processo abrirem o mesmo arquivo SQLite — a premissa é sobre disciplina do operador, não sobre o sistema |
| F-93 | politica-limiar | 🟡 | assume `notBefore <= agora`. Certificado emitido com validade futura não tem estado no enum (`ok`..`expirado` não cobre "ainda não válido") — cai em `ok` e some do radar |
| F-94 | caso-governanca | 🔴 | o mesmo defeito pelo lado do incentivo. Se o burlador pode encerrar a própria acusação, o payoff de burlar não mudou em relação a V(1) e o mecanismo adicionado na Fase 3 não alterou o equilíbrio |
| F-95 | casos-de-uso | 🟡 | depende dos 10 demais módulos e concentra 5 operações heterogêneas (varrer, abrirPedido, aprovarPedido, auditar, verificarIntegridade). Testá-lo isolado exige 10 dublês; é o ponto onde o grafo colapsa |
| F-96 | web-ui | 🟢 | mensagens de erro não especificadas para senha incorreta, papel insuficiente e limiar inválido |
| F-97 | sonda-tls | 🟢 | limite de 10 certificados na cadeia é declarado como decisão de projeto sem fonte; o documento admite a ausência, o que é honesto, mas o parâmetro segue sem referência |
| F-98 | casos-de-uso | 🟡 | `varrer()` é sequencial com timeout por alvo: N alvos inalcançáveis × timeout. 50 alvos × 10 s = 8 min de espera, com a decisão de concorrência (single-threaded sequencial) tornando isso estrutural |
| F-99 | web-ui | 🟡 | `ARC-05` foi resolvido só no papel: sessão, CSRF, roteamento e render das 6 telas continuam no mesmo módulo. Não dá para substituir o render sem tocar na autenticação |
| F-100 | casos-de-uso | 🟢 | grava uma observação por alvo a cada varredura mesmo quando nada mudou — crescimento linear de dados sem informação nova |
| F-101 | caso-governanca | 🟡 | `dono` do alvo é texto livre, não referência a `ator(id)`. "Quem responde por este certificado" continua não sendo uma identidade do sistema — não dá para notificar, filtrar nem responsabilizar |
| F-102 | trilha | 🟡 | cadeia com hash simples, sem chave (não é HMAC). Quem escreve no banco recria a cadeia inteira e ela verifica como válida — A5 declara o limite, mas o sistema não distingue "íntegra" de "reescrita coerentemente" |
| F-103 | autorizacao | 🟢 | não há desativação de ator: quem sai da equipe permanece Aprovador válido indefinidamente |
| F-104 | autorizacao | 🟡 | solicitante e aprovador podendo ser a mesma pessoa reduz a zero o custo de "cumprir o processo", e a aprovação vira formalidade autoassinada |
| F-105 | reconciliacao | 🔴 | `troca-nao-autorizada` é uma acusação automatizada sobre conduta humana. Uma troca legítima de emergência é registrada como não autorizada, e a trilha é append-only: não existe caminho de contestação, correção ou contexto. Decisão automatizada sobre pessoas sem recurso |
| F-106 | casos-de-uso | 🟡 | NIST SP 1800-16 exige escalação automática ao responsável central por inação. O design produz o estado `escalar`, mas nenhum módulo tem destinatário ou responsável — a escalação morre no painel. Desvio consciente (decisão de P0), porém a rastreabilidade normativa fica incompleta |
| F-107 | web-ui | 🟡 | mesmo defeito de `UX-01` em outro lugar: `autorizacao` expõe `criarAtor` e `desativar`, e nenhuma das 6 telas é gestão de atores. Criar o primeiro Aprovador (`ASS-06`) continua sem porta na UI |
| F-108 | politica-limiar | 🟢 | tolerância de fronteira indefinida: 29,9 dias é `critico` ou `atencao`? A regra de arredondamento não está declarada e muda o resultado de CA-1 |
| F-109 | web-ui | 🔴 | subject, issuer e SAN vêm de terceiro NÃO CONFIÁVEL (o host varrido) e são renderizados em HTML sem escape declarado. Quem controla um host varrido injeta script na tela do aprovador — XSS armazenado por certificado |
| F-110 | web-ui | 🟡 | acumula roteamento, render das 5 telas e gestão de sessão. Sessão é preocupação de segurança, não de apresentação: não dá para substituir o render sem tocar na autenticação |
