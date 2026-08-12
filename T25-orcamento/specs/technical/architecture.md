# Arquitetura — T25 (painel de consumo com teto e corte automático)

Documento vivo. Cada iteração do laço Fase 2 ↔ Fase 3 **acrescenta** uma seção
`## V(N+1)`; nenhuma versão anterior é sobrescrita. A última seção é a vigente.

---

## V(1) — Fase 1, iteração 1

### Contexto congelado (herdado da Fase 0)

- Gateway no caminho da requisição; decisão de corte **síncrona**, antes de gastar.
- Teto em moeda, janela mensal, virada à **meia-noite UTC** do dia 1.
- Teto **global E por entidade**; o mais restritivo vence.
- Apenas provedor Anthropic. Instância única. Banco embutido em arquivo.
- Critério de acerto: **invariante do teto sob concorrência**.

### Padrões adotados

| Dimensão | Escolha |
|---|---|
| Stack | Python + asyncio; `sqlite3` da biblioteca padrão; SDK oficial `anthropic` |
| Arquitetural | Monolito modular |
| Princípios | KISS + YAGNI, SOLID (com ênfase em SRP e inversão de dependência) |
| Concorrência | Event loop único (seção crítica sem `await`) + transação de banco |
| GoF | Strategy (upstream real/simulado), Adapter (formato `usage` → modelo interno) |
| Domínio (Fowler) | Transaction Script |
| Dados (Fowler) | Repository sobre SQL direto |
| Identidade | Chave virtual emitida pelo gateway |

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | gateway-http | recebe a requisição, orquestra reserva → envio → reconciliação, repassa resposta e streaming ao cliente | `POST /v1/messages`; `GET /*` serve a SPA | identidade, escrow, upstream, precificador |
| M-02 | identidade | resolve chave virtual → entidade; emite e revoga chaves; autentica o operador do painel | `resolver(chave) -> Entidade \| None`; `emitir(entidade) -> chave`; `autenticar_operador(segredo) -> bool` | persistencia |
| M-03 | escrow | seção crítica: decide permitir/negar contra os dois tetos e reserva o pior caso; depois reconcilia com o custo real | `reservar(entidade, valor, instante) -> Decisao{permitido, id_reserva, motivo}`; `reconciliar(id_reserva, custo_real)`; `liberar(id_reserva)` | persistencia, janela |
| M-04 | precificador | custo real a partir do `usage`; estimativa de pior caso antes da chamada | `custo(usage, modelo, instante) -> Decimal`; `pior_caso(modelo, tokens_entrada, max_tokens, instante) -> Decimal` | rate-card |
| M-05 | rate-card | carrega e valida a tabela de preços com vigência; nega modelo desconhecido | `preco(modelo, categoria_token, instante) -> Decimal` — levanta `ModeloSemPreco` se ausente | — |
| M-06 | janela | calcula a janela mensal vigente em UTC e o instante do próximo reset | `janela_de(instante) -> Janela{inicio, fim}`; `proximo_reset(instante) -> datetime` | — |
| M-07 | upstream | Strategy: cliente real (SDK `anthropic`) ou simulado; Adapter traduz `usage` da API para o modelo interno | `enviar(requisicao) -> Resposta{usage, conteudo, stop_reason}`; variante de streaming | — |
| M-08 | persistencia | conexão, schema, migração e transação; repositórios de contadores Escrow e de eventos de uso | `transacao()` (context manager); `contadores.ler/aplicar`; `eventos.registrar/consultar` | — |
| M-09 | painel-api | endpoints de leitura de consumo/saldo/tetos e de configuração de tetos, protegidos por senha de operador | `GET /api/consumo`; `GET /api/tetos`; `PUT /api/tetos/{entidade}`; `POST /api/login` | persistencia, janela, identidade |
| M-10 | painel-web | SPA servida pelo gateway: consumo por entidade, saldo, teto, estado de corte e próximo reset em UTC | página HTML/CSS/JS que consome painel-api | painel-api |

**Contagem: 10 módulos** — dentro do porte congelado de 8 a 12 (`ENUNCIADO.md` §2).

### Contratos que carregam o invariante

`escrow.reservar` é o **único** ponto do sistema autorizado a negar uma requisição.
Seu contrato:

1. **Atômico sobre os dois contadores** — global e da entidade — numa única transação.
   Reservar em um e falhar no outro é proibido: deixaria saldo preso.
2. **Não contém `await` de rede.** A chamada ao provedor acontece depois, fora da
   seção crítica. Esta é a motivação original do método Escrow (O'Neil, 1986): a
   transação é longa e não pode bloquear as demais.
3. **Formato do contador: par `(confirmado, reservado)`**, não escalar. A decisão lê
   `confirmado + reservado` contra o teto; a reconciliação move valor de `reservado`
   para `confirmado`, sempre para menos ou igual.

`escrow.reconciliar` é **idempotente por `id_reserva`** — aplicar a mesma
reconciliação duas vezes não pode debitar duas vezes. Sem isso, uma retentativa
interna corrompe o acumulado.

`rate-card.preco` **levanta exceção** em vez de devolver zero ou um padrão. Um
preço ausente que virasse zero tornaria o invariante do teto verdadeiro por omissão
de dados — a falha mais perigosa possível neste sistema.

### Fluxo principal (UC-1 / UC-2 / UC-3)

```
requisição
  → identidade.resolver(chave virtual)                    [nega se desconhecida]
  → precificador.pior_caso(modelo, ...)                   [nega se modelo sem preço]
  → TRANSAÇÃO { escrow.reservar(entidade, pior_caso) }    [SEÇÃO CRÍTICA, sem await]
        └─ negado → responde 402/429 ao cliente, nada é enviado ao provedor
  → upstream.enviar(...)                                  [longo, FORA da transação]
  → precificador.custo(usage)
  → TRANSAÇÃO { escrow.reconciliar(id_reserva, custo_real); eventos.registrar(...) }
  → repassa a resposta ao cliente
```

### Premissas (AP4 — a premissa não declarada é a maior fonte de falha)

| # | Premissa | Estado | Consequência se falsa |
|---|---|---|---|
| A1 | `max_tokens` é limite rígido, logo a reserva de pior caso é finita | ✅ documentado em specs/technical/token-accounting.md | A reserva seria ilimitada e o portão inútil |
| A2 | `usage` está presente em toda resposta bem-sucedida | ✅ documentado | Reconciliação impossível; reservas nunca fechariam |
| A3 | Um único processo escritor acessa o banco | ⚠️ garantida por operação, não por código | Dois processos → *lost update* → teto furado |
| A4 | O relógio do host é confiável para decidir a virada da janela | ❌ **não verificada** | Reset cedo demais libera gasto; tarde demais mantém corte indevido |
| A5 | Apps consumidores não possuem a chave real do provedor | ⚠️ depende de operação | O gateway é contornável e o corte vira cooperativo |
| A6 | `count_tokens` não é cobrado em tokens | ❌ **não verificada** | Cada decisão de admissão passa a ter custo próprio não contabilizado |
| A7 | A transação do SQLite basta contra *lost update* neste padrão de acesso | ❌ **não verificada** | É exatamente o modo de falha que o critério de acerto mede |

A4, A6 e A7 são entrada direta para a crítica adversarial da Fase 2.

### Escopo negativo — o que o sistema deliberadamente NÃO faz

Herdado da Fase 0: multi-provedor · hierarquia de entidades (org→projeto→chave) ·
degradação/throttle/downgrade · alertas e notificações · rateio, faturamento e
cobrança · múltiplas instâncias e alta disponibilidade.

Acrescentado na Fase 1, por decisão de arquitetura:

| Item | Razão |
|---|---|
| Retentativa automática ao provedor | Retentar é decisão do app. Retentar às cegas contra teto esgotado é o retry storm que a Fase 0 identificou ao separar limite de taxa de teto de orçamento |
| Cache de respostas do LLM | Reduz custo, mas é outro produto; obscureceria a relação entre requisição e consumo, que é o que o painel existe para mostrar |
| Integração com provedor de identidade externo | Uma senha de operador cobre o caso de uso; OAuth/SSO é infraestrutura, não o problema |
| Expiração automática de reserva órfã | A política ainda não foi decidida — vai à Fase 2. Inventá-la agora seria decidir sem crítica |

---

## V(2) — Fase 3, iteração 1 (resposta unificada aos 47 achados de V(1))

Princípio da assimetria: a Fase 2 atacou com 18 lentes independentes; esta resposta é
**única e integrada**. Correções individualmente corretas podem ser sistemicamente
contraditórias — por isso duas mudanças aqui resolvem quatro críticos de uma vez, e
nenhum módulo novo foi criado. **10 módulos em V(1), 10 módulos em V(2).**

### As duas simplificações estruturais

**1. A virada de janela deixa de ser um evento.** (resolve ARQ-03 e PRO-01)
A linha de `contador` é criada **preguiçosamente** no primeiro acesso dentro de uma
janela — `janela_inicio` já fazia parte da chave primária. Consequências: nenhum
módulo precisa ser dono do reset; janela nova = linha inexistente = consumo zero;
e como a `reserva` grava a própria `janela_inicio`, reconciliar depois da virada
debita **a janela em que o gasto ocorreu**. Removeu-se uma responsabilidade inteira
em vez de acrescentar um agendador.

**2. Expiração preguiçosa de reserva.** (resolve RES-01, CTL-01, RES-03, PRO-02)
Ao ler `reservado_nano`, toda reserva `'aberta'` mais velha que o TTL é liberada
dentro da mesma transação. Sem trabalhador de fundo, sem módulo novo, sem estado
adicional. O laço de controle ganha realimentação e o desvio monotônico desaparece.
**TTL padrão: 15 minutos**, configurável — fonte do valor: o timeout padrão de
requisição dos SDKs oficiais é de 10 minutos (`specs/technical/token-accounting.md`),
e o TTL precisa ser estritamente maior que a requisição mais longa possível.

### Tabela de módulos — V(2)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | gateway-http | **apenas proxy**: recebe a requisição, orquestra reserva → envio → reconciliação, repassa streaming e emite log estruturado de toda decisão. Não serve mais a SPA | `POST /v1/messages` | identidade, escrow, upstream, precificador |
| M-02 | identidade | **apenas** chave virtual → entidade; emissão e revogação. Autenticação de operador saiu daqui | `resolver(chave) -> Entidade \| None`; `emitir(entidade) -> chave` | persistencia |
| M-03 | escrow | seção crítica **intencionalmente bloqueante e curta**: expira reservas vencidas, aplica teto de `max_tokens` da entidade, decide contra os dois tetos, reserva; reconcilia. Devolve motivo como **código enumerado** | `reservar(entidade, valor, instante) -> Decisao{permitido, id_reserva, codigo_motivo, escopo_estourado, reset_em}`; `reconciliar(id_reserva, custo_real)` | persistencia, janela |
| M-04 | precificador | custo real a partir do `usage`; pior caso = `max_tokens × preço_saída`. **Não chama `count_tokens`** | `custo(usage, modelo, instante)`; `pior_caso(modelo, max_tokens, instante)` | rate-card |
| M-05 | rate-card | preços com `vigente_desde` **e `vigente_ate`**; valida na inicialização e recusa modelo sem preço vigente | `preco(modelo, categoria, instante)` — levanta `ModeloSemPreco`; `validar_na_inicializacao()` | — |
| M-06 | janela | **função pura**, sem estado e sem evento de virada | `janela_de(instante) -> Janela`; `proximo_reset(instante) -> datetime` | — |
| M-07 | upstream | Strategy (real/simulado) + Adapter; **verifica que as categorias conhecidas de token cobrem o total reportado** e falha alto se não cobrirem | `enviar(requisicao) -> Resposta{usage, conteudo, stop_reason}` | — |
| M-08 | persistencia | conexão, schema, transação; contadores com criação preguiçosa; eventos com retenção configurável; consulta de verificação do invariante I2 | `transacao()`; `contadores`; `eventos`; `verificar_invariantes()` | — |
| M-09 | painel-api | leitura de consumo/saldo/tetos, configuração de tetos **com trilha de auditoria**, **autenticação de operador**, **serviço da SPA por mapa de rotas explícito**, endpoint de saúde | `GET /api/consumo`; `PUT /api/tetos/{id}`; `POST /api/login`; `GET /health`; rotas estáticas nomeadas | persistencia, janela, identidade |
| M-10 | painel-web | SPA: consumo por entidade, saldo, teto, **qual teto estourou**, **instante do próximo reset em UTC** | página servida por painel-api | painel-api |

### Achados resolvidos, por id

| id | sev | Resolução em V(2) |
|---|---|---|
| ARQ-03, PRO-01 | 🔴🔴 | Simplificação 1 — virada preguiçosa; reserva grava sua janela |
| RES-01, CTL-01, RES-03, PRO-02 | 🔴🔴🟡🟡 | Simplificação 2 — expiração preguiçosa com TTL de 15 min |
| A-01, PERF-02 | 🔴🟡 | Decisão explícita: `sqlite3` síncrono; a seção crítica é declaradamente bloqueante e curta — é o que a torna atômica sem lock. Custo medido na Fase 6, não presumido |
| GAM-01 | 🔴 | Teto de `max_tokens` por entidade limita a reserva de pior caso; requisição acima é negada |
| SEG-01 | 🔴 | Senha em hash, comparação em tempo constante, limite de tentativas |
| SEG-02 | 🔴 | Rota curinga removida; SPA servida por mapa de rotas explícito, sem consulta ao sistema de arquivos |
| OBS-01 | 🔴 | Log estruturado de toda decisão como responsabilidade de escrow + gateway-http |
| ARQ-01 | 🟡 | gateway-http perde o serviço da SPA → volta a ser apenas proxy |
| ARQ-02 | 🟡 | identidade perde a autenticação de operador, que vai para painel-api, seu único consumidor |
| UX-01, UX-02, LIN-02, ETI-01 | 🟡 | Negação responde **HTTP 402** com corpo `{tipo, escopo_estourado, reset_em}` — código enumerado, diz qual teto estourou e quando volta. Distingue-se de 429 do provedor, matando o retry storm; e dá ao afetado a informação para agir |
| LIN-01 | 🟡 | Contrato de passagem especificado: apenas `POST /v1/messages`, lista explícita de cabeçalhos repassados, corpo repassado sem alteração |
| SEG-04, GOV-01 | 🟡 | Alteração de teto passa a registrar ator e instante |
| CIE-01, MEC-01, GOV-02 | 🟡 | `vigente_ate` no rate card + validação na inicialização: o sistema recusa iniciar com tabela vencida, em vez de subcontabilizar em silêncio |
| MEC-02 | 🟡 | upstream verifica que as categorias conhecidas cobrem o total reportado |
| PERF-03, SUS-02 | 🟡🟢 | Retenção configurável de eventos de uso |
| OBS-02 | 🟡 | `verificar_invariantes()` exposto em `GET /health` |
| SUS-01, CIE-03 | 🟡🟡 | `count_tokens` removido do caminho crítico (arbitragem do operador). A premissa A6 deixa de existir |
| REG-01, ETI-02 | 🟡🟢 | Entidade passa a significar **identidade técnica** (projeto, serviço, chave) e nunca pessoa — decisão do operador. `evento_uso` deixa de ser dado pessoal por definição |
| PERF-01 | 🟡 | Aceito com justificativa: a serialização no contador global é **inerente** ao invariante. Bailis et al. (2014) — um invariante de limite exige coordenação. Remover a serialização removeria a garantia |
| A-02 | 🟡 | Aceito: relógio confiável vira premissa declarada, mitigada por a janela ser função pura de um instante fornecido |
| A-03 | 🟡 | Aceito e declarado: gasto no provedor sem resposta ao gateway é subcontabilizado. O TTL limita o dano ao saldo, não à contabilidade |
| A-04, ARQ-04, PERF-04, UX-03 | 🟢🟢🟢🟢 | Sugestões diferidas com registro |

### Premissas — V(2)

| # | Premissa | Estado |
|---|---|---|
| A1 | `max_tokens` é limite rígido | ✅ documentado |
| A2 | `usage` presente em toda resposta bem-sucedida | ✅ documentado |
| A3 | Um único processo escritor | ⚠️ garantida por operação |
| A4 | Relógio do host confiável para a virada | ❌ não verificada — aceita, mitigada por `janela` ser função pura |
| A5 | Apps não possuem a chave real do provedor | ⚠️ depende de operação |
| A7 | Transação do SQLite basta contra *lost update* neste padrão | ❌ **não verificada** — é o que o critério de acerto mede na Fase 6 |
| ~~A6~~ | ~~`count_tokens` não é cobrado~~ | **extinta**: a chamada saiu do desenho |

### Escopo negativo — V(2)

Tudo de V(1), com uma remoção e três acréscimos:

- **Deixou de ser escopo negativo:** expiração de reserva órfã — agora é comportamento
  do sistema (simplificação 2).
- **Novo:** entidade consumidora nunca corresponde a uma pessoa (identidade técnica).
- **Novo:** o sistema não chama `count_tokens`.
- **Novo:** o sistema não tenta reconciliar gastos ocorridos no provedor cuja resposta
  nunca chegou (A-03 aceito e declarado).

---

## V(3) — Fase 3, iteração 2 (resposta aos 21 achados de V(2))

Diagnóstico da iteração 2: `escrow` recebeu 10 achados de 10 lentes — sinal de
**redesenho**, não de remendo. E os três críticos formam uma única cadeia causal:

> a reserva precisa durar a chamada longa → surgem reservas órfãs → cria-se um TTL para
> limpá-las → o TTL expira reservas **vivas** (RES-04) → a guarda de idempotência
> descarta a reconciliação tardia (RES-05).

Ajustar o TTL não quebra a cadeia; **remover o TTL** quebra.

### A simplificação estrutural desta rodada

**A vida da reserva passa a ser a vida da requisição, não um relógio.**
(resolve RES-04, RES-05, PRO-03, GOV-03, OBS-03, CTL-03, CIE-04)

Toda requisição em voo é um objeto vivo num processo único (premissa A3, já decidida).
A liberação ou reconciliação da reserva vai para um bloco `finally` de propriedade de
`gateway-http` — executado em **todos** os caminhos: sucesso, erro, timeout,
desconexão do cliente, exceção. Não existe caminho de saída que deixe reserva aberta.

Sobra um único caso: **queda do processo.** Tratado no arranque, deterministicamente —
num processo recém-iniciado nenhuma requisição pode estar em voo, logo **toda reserva
`'aberta'` encontrada no arranque é lixo de crash e é liberada**. Uma linha, sem
parâmetro, sem varredura periódica, sem relógio.

O que **desaparece** do desenho: o parâmetro TTL, o estado `'expirada'`, a varredura de
expiração, a necessidade de observar expirações, o laço de controle sem medição, e o
achado de que a expiração era mutação sem autoria. Sete achados mortos por remoção.

### O custo de entrada volta a ser reservado — sem chamada de rede

(resolve A-05, o crítico criado pela arbitragem de V(2))

Não se reintroduz `count_tokens`. Usa-se um **limite superior rigoroso e local**:
num tokenizador BPE sobre bytes UTF-8, **todo token consome ao menos 1 byte**, logo
`tokens_entrada ≤ bytes_do_corpo`. O corpo já está em memória; medir seu tamanho é
gratuito e não depende de nenhuma razão inventada (AP7 evitado).

```
pior_caso_nano = bytes_do_corpo × nano(modelo, 'entrada')
               + max_tokens     × nano(modelo, 'saida')
```

Superestima a entrada em ~3–4× na prática, o que é o lado seguro: a reserva nunca fica
curta. ⚠️ **A desigualdade `tokens ≤ bytes` é raciocínio derivado, não fonte citada** —
validar empiricamente na Fase 6 comparando `count_tokens` com o tamanho em bytes de uma
amostra. Se falhar, o invariante do critério de acerto cai junto.

### Tabela de módulos — V(3)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | gateway-http | proxy; **dono do ciclo de vida da reserva**: garante reconciliação ou liberação em `finally` por todos os caminhos de saída; log estruturado sem jamais registrar a chave virtual (só o id da entidade e uma impressão digital) | `POST /v1/messages` | identidade, escrow, upstream, precificador |
| M-02 | identidade | chave virtual → entidade; emissão e revogação | `resolver`, `emitir`, `revogar` | persistencia |
| M-03 | escrow | **enxuto**: decide contra os dois tetos, aplica teto de `max_tokens` e limite de reservas simultâneas por entidade, reserva, reconcilia, libera. Sem expiração, sem relógio, sem TTL | `reservar(...) -> Decisao`; `reconciliar(id, custo_real)`; `liberar(id)` | persistencia, janela |
| M-04 | precificador | custo real; pior caso = `bytes_do_corpo × preço_entrada + max_tokens × preço_saída` | `custo(...)`; `pior_caso(modelo, bytes_corpo, max_tokens, instante)` | rate-card |
| M-05 | rate-card | preços com vigência; **recusa apenas os modelos vencidos**, não a inicialização inteira; expõe o estado em `/health` | `preco(...)`; `modelos_vencidos()` | — |
| M-06 | janela | função pura; o instante é capturado **uma vez** na admissão e propagado | `janela_de(instante)`; `proximo_reset(instante)` | — |
| M-07 | upstream | Strategy + Adapter; verifica cobertura das categorias de token | `enviar(...)` | — |
| M-08 | persistencia | conexão, schema, transação; contadores preguiçosos; **recuperação de crash no arranque** (libera reservas `'aberta'`); **retenção aplicada no arranque**, nunca durante o tráfego; verificação de invariantes | `transacao()`; `contadores`; `eventos`; `recuperar_no_arranque()`; `verificar_invariantes()` | — |
| M-09 | painel-api | leitura, configuração de tetos com auditoria, autenticação de operador, rotas estáticas nomeadas, `/health` | `GET /api/consumo`; `PUT /api/tetos/{id}`; `POST /api/login`; `GET /health` | persistencia, janela, identidade |
| M-10 | painel-web | SPA: consumo, saldo, teto, qual teto estourou, próximo reset em UTC, **distingue "sem dados" de "consumo zero"** | página servida por painel-api | painel-api |

**10 módulos em V(1), V(2) e V(3).** Nenhum criado em duas rodadas de correção.

### Achados resolvidos nesta rodada

| id | sev | Resolução |
|---|---|---|
| RES-04, RES-05 | 🔴🔴 | Vida da reserva = vida da requisição; `finally` cobre todos os caminhos; crash tratado no arranque |
| A-05 | 🔴 | Reserva de entrada por limite superior `tokens ≤ bytes`, sem chamada de rede |
| PRO-03, GOV-03, OBS-03, CTL-03, CIE-04 | 🟡×5 | Extintos junto com o TTL — não havia o que declarar, observar, ajustar ou fundamentar |
| IMP-04 | 🟡 | `escrow` encolheu: perdeu expiração e relógio |
| GAM-03 | 🟡 | Limite de reservas simultâneas por entidade limita o agregado, não só a requisição |
| SEG-06 | 🟡 | Log nunca registra a chave virtual — apenas id da entidade e impressão digital |
| PERF-05 | 🟡 | Retenção movida para o arranque; nunca concorre com tráfego |
| MEC-03 | 🟡 | Recusa só os modelos vencidos; o gateway continua subindo |
| A-06 | 🟡 | Instante capturado uma vez na admissão e propagado; reconciliação usa a janela gravada na reserva |
| UX-04 | 🟡 | Painel distingue "sem dados" de "consumo zero" |
| ARQ-05, SEG-05 | 🟡🟡 | **Aceitos com justificativa**: servir 3 arquivos por mapa de rotas fixo não é responsabilidade que pague um módulo; e login no mesmo event loop é consequência direta da restrição de processo único, mitigada por contador de tentativas sem espera bloqueante |
| LIN-03, REG-02, SUS-03, ETI-03 | 🟢×4 | Sugestões e ausências de achado; sem ação |

### Premissas — V(3)

Inalteradas em relação a V(2), com uma extinta e uma nova:

- ~~TTL suficiente para cobrir a requisição mais longa~~ — **extinta com o TTL**.
- **A8 (nova):** `tokens_entrada ≤ bytes_do_corpo` para o tokenizador em uso.
  ❌ **não verificada** — raciocínio derivado, a validar empiricamente na Fase 6.
- **A7** segue não verificada e segue sendo o que o critério de acerto mede.

