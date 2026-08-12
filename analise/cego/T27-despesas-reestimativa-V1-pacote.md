# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Fila de aprovação de despesas com alçadas por valor e delegação temporária

## A arquitetura

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dominio-despesa | entidade Despesa, estados e transições válidas, valor em centavos; guarda INV-9, INV-11, INV-12 | `criar(solicitante, valorCentavos, descricao) -> Despesa \| ErroValidacao` · `aprovarNivel(despesa, nivel) -> Despesa` · `rejeitar(despesa, motivo) -> Despesa \| ErroMotivoAusente` | — |
| M-02 | matriz-doa | papéis, níveis e limites; monta a cadeia de aprovação para (valor, papel do solicitante); guarda INV-1, INV-10, INV-13 | `cadeiaPara(valorCentavos, papelSolicitante) -> Papel[] \| ErroAcimaDoTeto \| ErroSemAutoridadeAcima` · `limiteDe(papel) -> centavos` · `papelTopo() -> Papel` | — |
| M-03 | dominio-delegacao | entidade Delegação, vigência, revogação, estado efetivo contra um instante; guarda INV-3, INV-5 | `podeCriar(delegante, delegado, inicio, fim, ativasDoDelegante, ativasDoDelegado) -> ok \| ErroSoD` · `ativaEm(delegacoes, delegante, instante) -> Delegacao \| null` · `revogar(delegacao, instante) -> Delegacao` | relogio (só o tipo `Instante`) |
| M-04 | autoridade | responde "quem pode decidir este item agora e sob qual autoridade"; único ponto onde alçada e delegação se cruzam; guarda INV-2, INV-4, INV-6 | `resolver(despesa, usuarioAtuante, trilhaDaDespesa, delegacoesAtivas, instante) -> { permitido: true, emNomeDe: Usuario \| null, limiteExercido: centavos } \| ErroSoD(codigo, mensagem)` | matriz-doa, dominio-delegacao, trilha |
| M-05 | bandeja | monta a fila de um aprovador: pendências próprias + recebidas por delegação ativa; FIFO, valor e origem visíveis | `listar(usuario, instante) -> ItemBandeja[]` onde `ItemBandeja = { despesa, nivel, origem: 'propria' \| { emNomeDe: Usuario } }` | matriz-doa, dominio-delegacao, autoridade, portas-repositorio |
| M-06 | trilha | registro append-only de transições e decisões, com ator efetivo, em-nome-de, instante e limite exercido; guarda INV-7, INV-8 | `registrar(evento: Evento) -> void` · `de(despesaId) -> Evento[]` · `decisoesDe(despesaId) -> Decisao[]` | portas-repositorio |
| M-07 | relogio | porta `Clock` + adaptador real + adaptador controlável com avanço manual | `agora() -> Instante` · (só no adaptador de teste/demo) `avancar(ms) -> void` · `fixarEm(instante) -> void` | — |
| M-08 | portas-repositorio | contratos de persistência por agregado + contrato de transação | `DespesaRepo{ salvar, porId, pendentesDe(nivel) }` · `DelegacaoRepo{ salvar, ativasEm(instante), porDelegante }` · `UsuarioRepo{ porId, todos }` · `TrilhaRepo{ anexar, porDespesa }` · `emTransacao<T>(fn) -> T` | — |
| M-09 | sqlite-adaptador | implementa as portas em SQLite: schema, transação leitura-para-atualização, seed da matriz DoA e dos usuários | implementa integralmente M-08; `abrir(caminho) -> Repositorios` · `migrar() -> void` · `semear() -> void` | portas-repositorio |
| M-10 | casos-de-uso | orquestra UC-1..UC-7 dentro de uma transação; traduz violação de invariante em erro nomeado | `solicitar` · `aprovar` · `rejeitar` · `delegar` · `revogar` · `verBandeja` · `verTrilha` — cada um `(comando, atuante) -> Resultado \| ErroNomeado` | dominio-despesa, matriz-doa, dominio-delegacao, autoridade, bandeja, trilha, relogio, portas-repositorio |
| M-11 | api-http | Fastify: rotas, validação de entrada, identidade simulada, tradução erro de domínio → status HTTP | `POST /despesas` · `POST /despesas/:id/aprovar` · `POST /despesas/:id/rejeitar` · `POST /delegacoes` · `POST /delegacoes/:id/revogar` · `GET /bandeja` · `GET /despesas/:id` · `POST /relogio/avancar` | casos-de-uso |
| M-12 | ui-web | 6 telas server-rendered: seleção de usuário, nova despesa, bandeja, detalhe + trilha, delegações, auditoria | páginas HTML servidas por M-11; formulários POST; sem build, sem SPA | api-http |

**Regra de dependência (hexagonal):** M-01 a M-08 são o núcleo e não importam nada de
M-09, M-11 nem M-12. As setas de dependência apontam sempre para dentro. `autoridade`
(M-04) é deliberadamente o único ponto de cruzamento entre alçada e delegação.

**Granularidade (E = I₀/C):** cada módulo é implementável em uma única interação tendo em
contexto apenas este documento + a interface dos módulos de que depende.

---

## Invariantes por módulo

| Invariante | Módulo guardião |
|---|---|
| INV-1 `valor ≤ limite` (fronteira inclusiva) | M-02 |
| INV-2 ninguém aprova a própria despesa | M-04 |
| INV-3 delegação não transitiva | M-03 |
| INV-4 mesmo ator não decide duas vezes na mesma cadeia | M-04 |
| INV-5 sem vigências sobrepostas do mesmo delegante | M-03 |
| INV-6 autoridade avaliada no instante do ato | M-04 |
| INV-7 decisão grava ator / em-nome-de / limite exercido | M-06 |
| INV-8 trilha append-only | M-06 |
| INV-9 rejeição exige motivo | M-01 |
| INV-10 valor acima do teto máximo recusado na criação | M-02 |
| INV-11 rejeição é terminal | M-01 |
| INV-12 dinheiro em inteiro de centavos | M-01 |
| **INV-13** solicitante do papel de topo é recusado na criação (não há autoridade acima) | M-02 |

INV-13 nasceu nesta fase: a decomposição de M-02 expôs que "a cadeia começa acima do papel
do solicitante" não tem resposta quando o solicitante ocupa o topo. Resolvido por decisão
do operador, pela mesma lógica de INV-10 — nunca existe pendência sem aprovador possível.

---

## Premissas (AP4 — o que o sistema assume como verdadeiro)

| id | Premissa | Consequência se for falsa |
|---|---|---|
| A1 | a hierarquia de papéis é linear, ordenada e sem lacunas | a cadeia de M-02 fica indefinida |
| A2 | cada usuário ocupa exatamente um papel, imutável durante o ciclo | o limite exercido registrado em INV-7 vira ambíguo |
| A3 | a matriz DoA não muda durante a vida de uma despesa (seed fixo) | INV-6 exigiria versionar a matriz e resolver retroatividade |
| A4 | um único processo escreve no banco | a trava por transação deixa de bastar; precisaria de trava otimista por versão |
| A5 | **a identidade informada é confiável (sem autenticação)** | **toda invariante SoD é contornável por quem chame a API direto — ACEITA EXPLICITAMENTE: o sistema impõe SoD contra engano, não contra adversário** |
| A6 | instantes em UTC, relógio monotônico | vigências de delegação ficam ambíguas na fronteira |
| A7 | volume pequeno (dezenas a centenas de despesas) | a bandeja sem paginação degrada |
| A8 | delegação é global e no máximo uma ativa por delegante | M-04 teria de escolher entre delegações concorrentes |

---

## Escopo negativo (o que o sistema deliberadamente NÃO faz)

Não autentica (A5) · não notifica (e-mail/push) · **não agenda nada** — sem cron nem timer:
a expiração de delegação é avaliada sob demanda contra o relógio, no momento em que a
bandeja é montada ou a decisão é tentada · não edita a matriz DoA em runtime · não pagina
nem oferece busca · não versiona API pública · não é multi-tenant · não anexa arquivos ·
não converte moeda · não permite delegação transitiva (INV-3) · não permite override
administrativo em despesa travada · não escalona por tempo/SLA.

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
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | External dependencies (APIs, DBs, queues, third-party services) |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | Replacing or modifying existing production system |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | Automated decisions about people (scoring, classification, moderation) |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | Multi-actor flows, state machines, or business processes |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | Production systems with operational requirements |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | State synchronization, runtime configuration affecting behavior, self-correcting or feedback-driven systems |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | Multiple independent actors, public API, external integrations, marketplace or platform design |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Inter-component communication, protocol definitions, message formats, interface contracts between independent teams |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | Module maintenance, system evolution, long-lived systems with technical debt accumulation |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T27-despesas",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
