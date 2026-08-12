# Arquitetura — T21 certificados

Fase 1, V(1). Padrão: **Hexagonal (Ports & Adapters)** · Princípios vinculantes:
**KISS + YAGNI** · Concorrência: **single-threaded, varredura sequencial** ·
GoF: **State** · Fowler: **Domain Model enxuto** + **Repository/Data Mapper**.

Stack aprovada: **TypeScript sobre Node 24 sem build** (`process.features.typescript
= "strip"`, verificado) · **`node:sqlite`** embutido · **HTML renderizado no servidor**
com formulários, sem JS de cliente · testes com **`node:test`** · única devDependency:
`typescript` (para `tsc --noEmit`).

Os nomes da coluna `module` são **estáveis e canônicos**: a Fase 2 critica por estes
nomes e a Fase 5 implementa com estes nomes.

## V(1) — Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

Grafo de dependências é acíclico e aponta sempre para dentro: `web-ui -> casos-de-uso
-> {domínio puro, portas}`. Os módulos M-01, M-02, M-04, M-05 não importam nada de
infraestrutura — é o que permite testar CA-1, CA-3, CA-5 e CA-6 sem rede e sem banco.

## As 4 respostas obrigatórias

**1. Decomposição.** 11 módulos em três anéis: domínio puro (certificado,
politica-limiar, pedido, reconciliacao, trilha, autorizacao), portas e adaptadores
(relogio, sonda-tls, repositorio), aplicação e entrada (casos-de-uso, web-ui). A
fronteira que mais importa: **nenhuma regra de negócio em web-ui, nenhuma I/O no
domínio**.

**2. Interfaces.** Contratos na tabela acima. Convenções: erros de domínio são
**valores de retorno** (`Ok | Erro`), não exceções — a exceção fica para falha
programática. Todo tempo entra por `relogio.agora()`. Nenhum módulo além de
`repositorio` conhece SQL; nenhum além de `sonda-tls` conhece rede.

**3. Premissas.** Ver lista abaixo — é o insumo direto da lente Assumptions na Fase 2.

**4. Escopo negativo.** O sistema deliberadamente NÃO: emite certificados (sem ACME,
sem CA, sem chave privada); importa PEM/DER nem aceita cadastro manual de metadados;
notifica por e-mail ou webhook; agenda varreduras (sem daemon, sem cron interno);
agrupa alvos que compartilham certificado; impõe segregação de funções; assina
decisões criptograficamente; ancora a trilha fora da máquina; monitora certificados
não expostos em TLS.

## Premissas assumidas (V(1))

| id | Premissa | Se for falsa |
|---|---|---|
| A1 | Todo certificado de interesse está exposto em porta TLS alcançável | certificados fora de TLS ficam invisíveis ao inventário |
| A2 | O relógio da máquina está correto | toda classificação de vencimento erra junto — **sem mitigação no V(1)** |
| A3 | Fingerprint diferente com `notAfter` avançado ⇒ houve emissão | mitigada por `reconciliacao`: sem pedido aprovado vira `troca-nao-autorizada` (CA-6) |
| A4 | Existe um humano para aprovar dentro da janela de alerta | pedidos ficam pendentes até o vencimento; `escalar` torna isso visível |
| A5 | A máquina que roda o sistema é confiável | a trilha é reescrevível por inteiro — é tamper-**evident**, não tamper-proof |
| A6 | Uma varredura por vez, disparada por pessoa | duas execuções simultâneas do processo poderiam intercalar escritas na cadeia de hash |
| A7 | O volume de alvos é pequeno (dezenas) | varredura sequencial fica lenta; sem paginação no painel |
| A8 | `node:sqlite` experimental não muda de API dentro do ciclo | upgrade de Node poderia quebrar `repositorio` — isolado atrás do Repository |

---

# V(2) — resposta unificada à crítica da Iteração 1

V(1) permanece acima, intacto. Esta é a versão corrente.

Os 79 achados não foram tratados como 79 defeitos independentes: agrupam-se em quatro
problemas, e a resposta é integrada (princípio da assimetria — a Fase 2 ataca com
muitas lentes, a Fase 3 responde com visão única).

1. **Contratos declaram o que o módulo FAZ, não o que ele RECEBE** — `Assumptions` em
   8 de 11 módulos, mais `Implementability` e `Linguistics`. Resposta: pré-condições
   por contrato, forma canônica de `Ok | Erro`, DDL completo (`specs/models/schema.md`)
   e parâmetros com fonte (`specs/technical/parameters.md`). **Especificação, não módulo novo.**
2. **Dois módulos-deus** — `casos-de-uso` (10 dependências) e `repositorio`
   (4 agregados). Resposta: dividir o primeiro por fluxo; expor o segundo como
   **4 portas nomeadas atendidas por 1 adaptador** — separação sem módulo extra.
3. **Duas portas dos fundos na governança** — `SEC-01` (CSRF forja aprovação) e
   `GAM-01` (trocar direto no host não custa nada). Token CSRF resolve a primeira; a
   segunda foi arbitrada pelo operador (justificativa obrigatória).
4. **O sistema não sabe quando não sabe** — `RES-01`, `OBS-01/02`, `ASS-08`, `REG-04`.
   Resposta: estado `indisponivel` distinto, idade do dado visível, registro de
   varredura e detecção de retrocesso do relógio.

## V(2) — Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

## Convenção canônica de resultado (resolve `LIN-02`)

```ts
type Ok<T>  = { ok: true;  valor: T }
type Erro<E> = { ok: false; erro: E }
type Resultado<T, E> = Ok<T> | Erro<E>
```

Exceção é reservada a falha programática (bug), nunca a condição de domínio prevista.

## Resolução dos achados por id

**🔴 críticos — todos os 11 endereçados:**

| id | resolução em V(2) |
|---|---|
| IMP-01 | `web-ui` ganha contrato completo: 6 telas nomeadas, rotas GET/POST enumeradas, sessão especificada (cookie HttpOnly/SameSite, expiração 30 min) |
| IMP-02 | DDL completo em `specs/models/schema.md`: 7 tabelas, chaves, índices, CHECKs |
| SEC-01 | token CSRF por formulário, verificado em todo POST |
| SEC-02 | escape obrigatório de subject/issuer/SAN — declarado no contrato de `web-ui` |
| RES-01 | falha de sonda vira fato: tabela `falha_sonda`, estado `indisponivel` distinto de `expirado`, e `visto_ultima_vez` exibido no painel |
| UX-01 | tela `cadastro-de-alvo` acrescentada — UC-1 passa a ser executável |
| PRO-01 | estados `rejeitado` (com motivo obrigatório) e `cancelado` — arbitrado pelo operador |
| GOV-01 | `alvo-cadastrado`, `alvo-removido`, `limiar-alterado` e `ator-criado` entram na trilha |
| ETH-01 | `justificarTroca` — ator autenticado anexa justificativa como NOVA entrada, sem editar a anterior |
| GAM-01 | mesmo mecanismo: o destaque de troca não autorizada só sai com justificativa nomeada, o que torna burlar mais caro que cumprir |
| LIN-01 | contrato de `reconciliar` desambiguado: recebe `pedidoAprovado` (só aprovados), não recebe `estado`, e perde a dependência de `politica-limiar` |

**🟡 importantes — 48, todos endereçados ou aceitos com justificativa:**

| mecanismo | achados resolvidos |
|---|---|
| Pré-condições declaradas no contrato | ASS-02, ASS-03, ASS-04, ASS-06, MEC-02 |
| Serialização canônica + encoding fixado | ASS-05, IMP-05 |
| Detecção de retrocesso do relógio (evento `relogio-retrocedeu`) | ASS-08, REG-04 |
| Cadeia inteira em vez da folha | ASS-01 |
| Divisão `casos-de-uso` → `caso-varredura` + `caso-governanca` | ARC-01, PER-01 (parcial), RES-02 |
| Papel como valor, dependência removida | ARC-02 |
| 4 portas nomeadas / 1 adaptador | ARC-03, ARC-05 (sessão separada do render) |
| DDL + transação + statements parametrizados | IMP-02, RES-03, SEC-07, PER-03 (índices) |
| Parâmetros com fonte | IMP-03, IMP-04, SCI-01, SCI-02 |
| Contrato de segurança de `web-ui` | SEC-03 (bind 127.0.0.1), SEC-05 (flags e expiração) |
| Limite de cadeia e retentativa única | SEC-06, RES-04 |
| Observação gravada só na mudança + `visto_ultima_vez` | PER-04, SUS-01, SUS-02, OBS-02 |
| Registro de varredura | OBS-01, CTL-01 (o laço passa a deixar rastro) |
| Enum de urgência separado de `semExpiracao` | LIN-03 |
| Forma canônica de `Resultado` | LIN-02 |
| Faixa de Node declarada | MEC-01 |
| Truncamento de dias declarado | MEC-03, CTL-03 |
| Trilha registra alteração de limiar | CTL-02, GOV-01 |
| Coluna `dono` em `alvo` | GOV-02 |
| Evento `ator-criado` | GOV-03 |
| Justificativa nomeada | ETH-02 (retificação por anexação), GAM-02 (auto-aprovação fica marcada) |
| Transições novas | PRO-02 (`expirado-sem-emissao`), PRO-03 (aprovação expira junto com o pedido) |
| Aviso tamper-evident na tela de trilha | UX-04, SEC-08 |
| Estados `escalado` e `troca-nao-autorizada` no painel | UX-02 |
| Progresso da varredura por alvo na resposta | PER-02, UX-03 |

**Aceitos explicitamente, com justificativa registrada:**

| id | aceitação |
|---|---|
| ASS-02 | STARTTLS fica fora: o alvo declara exigir TLS direto e a limitação é visível, não silenciosa (arbitrado pelo operador) |
| REG-01 | escalação sem destinatário externo — decisão de P0 (sem e-mail/webhook); o estado `escalado` é o canal |
| PRO-04 | o papel Auditor permanece sem transição própria: ele lê e verifica a cadeia, e isso é responsabilidade suficiente neste ciclo |
| SEC-04 | sem limite de tentativas de login: aplicação local em 127.0.0.1, monousuário; o custo do mecanismo excede o risco nesta superfície |

**🟢 sugestões (20)** — deferidas conscientemente, exceto as que caíram junto na
resolução acima (`IMP-05`, `SUS-02`, `PER-04`, `ARC-04`, `CTL-03`, `MEC-03`, `MEC-04`,
`ETH-03`, `OBS-03`, `SEC-07`, `RES-05` parcial).

## Premissas V(2)

| id | Premissa | Situação em V(2) |
|---|---|---|
| A1 | Certificado de interesse exposto em porta TLS **direta** | mantida e agora **declarada ao operador** (ASS-02 aceito) |
| A2 | Relógio da máquina correto | **primeira mitigação**: `verificarMonotonia` detecta retrocesso e registra `relogio-retrocedeu`. Relógio consistentemente errado continua indetectável |
| A3 | Fingerprint diferente ⇒ emissão | mitigada em V(1) por CA-6 e agora reforçada: sem pedido aprovado exige justificativa nomeada |
| A4 | Existe humano para aprovar | mantida; `escalado` e `expirado-sem-emissao` tornam a ausência visível |
| A5 | Máquina confiável | mantida e **comunicada na UI** (tamper-evident, não tamper-proof) |
| A6 | Uma varredura por vez | agora **imposta**: trava exclusiva de escrita no banco |
| A7 | Volume de alvos pequeno (dezenas) | mantida; varredura sequencial e painel sem paginação |
| A8 | `node:sqlite` estável no ciclo | mantida, com faixa `>=24 <25` declarada |
| **A9** | O operador que cadastra o alvo sabe quem é o `dono` | **nova** — a coluna `dono` só tem valor se for preenchida com verdade |
| **A10** | A justificativa de troca não autorizada é honesta | **nova** — o mecanismo registra e atribui, não verifica o conteúdo |

---

# V(3) — resposta à crítica da Iteração 2

V(1) e V(2) permanecem acima. Esta é a versão corrente. **A decomposição não mudou:**
os mesmos 12 módulos, o mesmo grafo de dependências. Esta rodada refina contratos e
comportamento — é convergência, não redesenho.

## O crítico da rodada e a admissão que ele força

`SEC-09`/`GAM-04` (🔴): `justificarTroca` aceitava qualquer ator autenticado — e quem
burla o processo tem acesso ao sistema por definição. Ele justificava a própria troca e
o destaque sumia.

Acrescentar mais um mecanismo aqui seria AP2 (complexidade como falsa solução): cada
controle novo criou uma superfície de contorno nova — CA-6 gerou o destaque, o destaque
gerou a justificativa, a justificativa gerou `SEC-09`. **A correção é reconhecer o
limite real:** um sistema sem poder sobre o host não pode impedir a burla, só torná-la
cara e permanente. V(3) muda o payoff em vez de tentar bloquear:

1. `justificarTroca` exige papel **Aprovador** — não qualquer ator autenticado.
2. A justificativa **não apaga nada**: ela referencia o índice `i` da entrada
   `troca-nao-autorizada` e é anexada como entrada nova. O evento original permanece.
3. O alvo carrega **contador permanente** de trocas não autorizadas, visível na
   auditoria e que nada zera. A justificativa limpa apenas o destaque operacional.

O burlador continua podendo justificar-se. O que ele não consegue mais é fazer o
registro desaparecer, nem fazê-lo sem que a justificativa fique atribuída ao seu nome.
Isso é o máximo honesto — e está declarado, não prometido a mais.

## Mudanças de contrato em V(3)

| módulo | mudança | achados |
|---|---|---|
| certificado | classificação passa a usar `notAfterFolha`; `notAfterEfetivo` da cadeia vira **sinalização separada**, não driver do estado — cross-signed deixa de gerar alarme que renovação nenhuma resolve | ASS-10 |
| politica-limiar | **o estado do alvo é sempre derivado na leitura** (observação + limiar vigente), nunca persistido: mudar a política reclassifica tudo por construção, sem dessincronizar painel e histórico | ASS-11, CTL-04 |
| pedido | invariante: **no máximo um pedido não-terminal por alvo**; `cancelar` só a partir de `pendente` | ASS-09, PRO-07 |
| reconciliacao | `mudanca-sem-avanco` ganha consumidor: vira `rollback-detectado` na trilha e, sem pedido aprovado, também `troca-nao-autorizada` | LIN-05 |
| trilha | entrada de justificativa referencia o índice `i` da troca que justifica; recusa anexar se `relogio` acusa retrocesso | ASS-12, ETH-04, RES-07 |
| autorizacao | comando de inicialização cria o primeiro Aprovador e registra `ator-criado` — o sistema não nasce travado | ASS-06 |
| relogio | comportamento definido: `agora() < ultimoCarimbo` **recusa a operação** com erro claro e registra `relogio-retrocedeu` | RES-07 |
| sonda-tls | retentativa **só para `timeout`**; `recusado` e `dns` são determinísticos e não se repetem — pior caso volta a ~N×10 s | PER-05 |
| repositorio | as 4 portas passam a **exigir um token de transação como parâmetro**: escrever fora de `emTransacao` deixa de ser proibido por convenção e passa a ser impossível pelo tipo · remoção de alvo é **lógica** (`removido_em`), nunca física · `falha_sonda` deduplicada por (alvo, tipo) com contador · **WAL removido** (contradizia a trava exclusiva) · nomes uniformizados nas 4 portas | SEC-11, REG-05, SUS-03, MEC-05, LIN-06 |
| caso-varredura | `varredura` gravada em transação própria no início e no fim; na abertura, varredura com `concluida_em` NULL é marcada `interrompida` · chama `expirarSemEmissao` quando o alvo vence com pedido aberto | IMP-06, RES-06, PRO-06 |
| caso-governanca | `justificarTroca` exige Aprovador, referencia o evento e não apaga o histórico | SEC-09, GAM-04, ASS-12, ETH-04 |
| web-ui | **7ª tela: gestão de atores** · CSRF especificado: token de 32 bytes por sessão, campo oculto em todo formulário, comparado com `timingSafeEqual`, expira com a sessão · **rotação do identificador de sessão após login** · justificativa fica na tela `alvo/:id` · `dono` vira referência a `ator(id)` no formulário | UX-06, IMP-07, SEC-10, UX-07, GOV-05 |

## Aceitos explicitamente nesta rodada

| id | aceitação |
|---|---|
| ARC-06 | `caso-governanca` mantém 10 operações: separar auditoria (2 delas, leitura pura) criaria um 13º módulo e o enunciado limita a 12. Registrado como dívida de granularidade conhecida |
| ARC-07 | `web-ui` mantém sessão e render juntos, pelo mesmo motivo de contagem de módulos |
| OBS-04 | varredura segue em POST síncrono sem progresso incremental: progresso exigiria JavaScript de cliente, que está fora de escopo por decisão da Fase 1 |
| PER-06 | `verificar` da trilha continua O(n) — com dezenas de alvos (A7) a cadeia não atinge tamanho problemático neste ciclo |
| SCI-05 | expiração de sessão em 30 min **não tem fonte normativa**; é decisão de projeto, declarada como tal em vez de receber citação inventada |
| SCI-06 | limite de 10 certificados na cadeia, idem |

## Premissas V(3)

Mantidas A1–A10, com duas mudanças e uma nova:

- **A3** deixa de ser premissa de detecção e vira **limite declarado**: o sistema não
  impede a troca sem aprovação, apenas a registra de forma permanente e atribuível.
- **A6** (uma varredura por vez) agora é imposta por trava exclusiva, sem WAL.
- **A11 (nova):** o operador que justifica uma troca não autorizada é um Aprovador — o
  sistema verifica o papel, nunca a veracidade do que ele escreve.

---

# Fechamento do ciclo v1.0 — o que a implementação mudou em relação a V(3)

Registrado na Fase 7. Divergências encontradas ao codar e testar, todas registradas
como decisão em vez de aplicadas em silêncio:

| # | Divergência | Resolução |
|---|---|---|
| 1 | `repositorio` foi especificado com **4 portas**, mas V(2) criou as tabelas `varredura` e `falha_sonda` sem atualizar a lista | acrescentada `PortaVarreduras` — quinta porta do **mesmo** adaptador; continua um módulo (M-09) |
| 2 | Restrição "`typescript` é a única devDependency" | `@types/node` acrescentada: sem ela `tsc --noEmit` não roda e o Automated-AV da Fase 5 deixa de existir. É *type-only*; **zero dependências de runtime** segue intacto |
| 3 | `CA-5` não estava garantido: `cadastrarAlvo` validava contra `Infinity` (não há certificado observado no cadastro) e nada revalidava após a varredura | validação movida para o **estado derivado** (`estadoDoAlvo`), onde o certificado observado existe |
| 4 | Erros de transição colapsavam em `transicao-invalida`, descartando a causa que o domínio já sabia | `ErroGovernanca` ganhou `motivo-obrigatorio` e `estado-invalido`; a UI passou a ter frase própria para toda variante |
| 5 | Auto-aprovação era permitida e **invisível** na trilha | passou a ser **marcada** (`dados.autoAprovacao`) — registrar não é proibir; segregação de funções segue fora de escopo |

Resultado final: **12 módulos, 2174 LOC, 68 testes verdes, `tsc --noEmit` limpo.**
Lições do ciclo em `specs/references/lessons.md`.

