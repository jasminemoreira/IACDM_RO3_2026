# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Triagem de chamados com prioridade automática, reclassificação e recurso do solicitante

## A arquitetura

## V(1)

Padrões: Arquitetura Limpa · KISS+YAGNI · SOLID · DDD tático · Adapter
(relógio, repositório) · Domain Model · Repository + Data Mapper.
Stack: TypeScript + Node · Fastify · better-sqlite3 · templates no servidor ·
Vitest · Playwright. Concorrência: thread única, transação serializada.

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | relogio | fonte de tempo abstrata; impl. de sistema e impl. controlável para teste | `agora(): Instante`; `avancar(horas)` (só teste) | — |
| M-02 | configuracao | carrega matriz, metas de SLA e prazos do rito como dado | `matriz(): Celula[]`; `metas(): Meta[]`; `prazosRito(): {recorrer, julgar}` | — |
| M-03 | prioridade | deriva P = matriz(impacto, urgencia); única origem de uma Prioridade | `derivar(impacto, urgencia): Prioridade` | configuracao |
| M-04 | sla | prazos em horas corridas contados da abertura; avaliação de violação | `prazos(p, abertoEm): Prazos`; `violado(prazos, agora): boolean` | configuracao |
| M-05 | chamado | entidade Chamado: ciclo de vida, invariantes, triagem e reclassificação | `abrir`; `triar`; `reclassificar`; `reconhecer`; `encerrar` | prioridade, sla |
| M-06 | recurso | agregado Recurso: admissibilidade, julgamento, efeito do provimento | `abrir(chamado, autor, eixos, justificativa, agora)`; `julgar(recurso, gestor, desfecho, fundamentacao, agora)` | chamado, configuracao |
| M-07 | trilha | eventos somente-inserção; reconstrução do histórico de classificação | `registrar(evento): Evento`; `doChamado(id): Evento[]` | — |
| M-08 | autorizacao | RBAC + legitimidade; devolve permissão com motivo | `pode(usuario, acao, alvo): Permissao` | — |
| M-09 | repositorio | portas de persistência, Data Mapper SQLite, esquema, seed, transação atômica | `emTransacao(fn)`; `chamados`; `recursos`; `trilha`; `usuarios` | chamado, recurso, trilha |
| M-10 | casos-de-uso | orquestra UC-1..UC-6: transação, autorização, domínio, trilha | `abrirChamado`; `triar`; `reclassificar`; `abrirRecurso`; `julgarRecurso`; `consultarFila`; `consultarChamado` | M-01..M-09 |
| M-11 | api-http | rotas Fastify, sessão de papel, validação, rejeição de `prioridade` como entrada | rotas HTTP | casos-de-uso |
| M-12 | ui-web | 6 telas server-side: abrir, fila, triar, chamado (com trilha), recorrer, julgar | páginas HTML | api-http |

Grafo acíclico. M-01 a M-08 são núcleo puro — testáveis sem servidor e sem disco.

### Contratos que carregam regra (não são só assinaturas)

- **`relogio.agora()`** é a única forma de obter o instante atual. Nenhum outro
  módulo chama a data do sistema. Testes injetam relógio controlável e avançam
  48 h em microssegundos.
- **`prioridade.derivar()`** é a única função que produz uma `Prioridade`. O
  tipo não tem construtor público nem setter — o CA-negativo passa a ser
  garantia do compilador, não promessa.
- **`sla.prazos(p, abertoEm)`** recebe `abertoEm`, nunca "agora". A regra
  "recontar desde a abertura" está na assinatura: é impossível calcular prazo a
  partir do instante da reclassificação, porque a função não aceita esse dado.
- **`repositorio.emTransacao(fn)`** envolve toda escrita: mudança de
  classificação + recálculo de prazos + evento de trilha, tudo ou nada.
- **`autorizacao.pode()`** devolve permissão **com motivo** — inadmitido por
  prescrição (B-3) precisa ser distinguível de inadmitido por falta de
  legitimidade (B-5).

### Premissas (lista — antídoto AP4)

| # | Premissa | Origem | Validada? |
|---|---|---|---|
| A1 | Nenhum módulo lê o relógio do sistema | decisão P0 | sim, por construção |
| A2 | Prioridade não tem setter em lugar nenhum | CA-negativo | sim, por tipo |
| A3 | Toda escrita é transacional: mudança + prazos + trilha são atômicos | decisão P0 | sim, por construção |
| A4 | A trilha é somente-inserção e nunca reescrita | CA-3 depende disso | sim, por construção |
| A5 | Nó único, thread única — sem escritas concorrentes no mesmo chamado | decisão P1 | sim, por construção |
| A6 | Os dois eixos têm peso igual (matriz simétrica) | P0 | **NÃO — declarada sem evidência** |
| A7 | O solicitante age de boa-fé; abuso é visível, não punido | P0 | **NÃO — declarada sem evidência** |
| A8 | Identidade é declarada, não provada (sem senha) | P0 | risco aceito explicitamente |
| A9 | Não há calendário de negócio; prazos em horas corridas | P0 | sim, decisão registrada |
| A10 | Categoria é rótulo: não roteia e não afeta prioridade | P0 | sim, decisão registrada |

A6 e A7 sustentam o desenho sem evidência por trás. São alvo declarado da
lente Premissas na Fase 2.

### Escopo negativo

Autenticação com senha · atendimento técnico e atribuição a técnico ·
notificações · reabertura e pesquisa de satisfação · segunda instância de
recurso · relatórios e dashboards · i18n e acessibilidade avançada ·
calendário de expediente · roteamento por categoria · **edição manual de
prioridade** (esta não é omissão: é o requisito central invertido).

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
  "projeto": "T32-triagem",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
