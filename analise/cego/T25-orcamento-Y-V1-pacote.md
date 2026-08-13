# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Painel de consumo com teto de orçamento e corte automático ao atingir o limite

## A arquitetura

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
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | The work changes something that already exists and is in use — replacing, modifying, or coexisting with a running system, a stored data format, or a live contract, with an old state that must survive or be transitioned. Apply the central question wherever there is an "old" to preserve; it does not require a formal "production system". |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | The system makes or automates a consequential decision that can harm or exclude a party subject to it — a person, but also an entity (a budget cut, an access denial, a flag acted on). Apply the central question — who can be harmed? — do not require the decision to be "about people". |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | The system has a process with states, handoffs, or exception paths — one actor or many. Apply the central question wherever a flow can be left incomplete; "multi-actor" is one case, not the requirement. |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | The system runs somewhere it can degrade or fail after it ships, and someone would need to tell WHY without changing code. Apply the central question wherever a running system can fail silently; it does not require a formal "production" or "ops" label. |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | The system reacts to a signal and adjusts state toward a target — a sync, a retry/backoff, a runtime setting that changes behavior, any feedback loop that can oscillate or drift. Apply the central question wherever the system regulates rather than just reacts; the list is illustrative. |
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
  "projeto": "T25-orcamento",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
