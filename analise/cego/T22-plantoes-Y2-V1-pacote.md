# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Distribuidor de plantões com restrições, trocas entre pessoas e aprovação

## A arquitetura

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dominio | entidades e objetos de valor do domínio; sem I/O, sem solver | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Troca, Violacao, Fronteira` | — |
| M-02 | catalogo-restricoes | declara cada restrição UMA vez (H1-H4, L1-L8, S1-S7, internas) com dois modos de uso | `aplicar(modelo, vars, ctx) -> None` · `verificar(escala, ctx) -> [Violacao]` · `catalogo(instancia) -> [Restricao]` | dominio |
| M-03 | avaliador | custo e violações de uma escala concreta | `avaliar(escala, ctx) -> Avaliacao{violacoes, custo, custo_por_restricao}` | dominio, catalogo-restricoes |
| M-04 | troca | máquina de estados da troca e regra de revalidação no aceite | `solicitar(escala, sol, dest, p1, p2) -> Troca` · `responder(troca, aceite, escala) -> ResultadoTroca` | dominio, avaliador |
| M-05 | fronteira | deriva contadores de fronteira da escala do mês anterior | `derivar(escala_anterior, pessoas) -> {pessoa_id: Fronteira}` | dominio |
| M-06 | solver-cpsat | adaptador do solver: monta o modelo CP-SAT a partir do catálogo, resolve, devolve Escala | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada}` | dominio, catalogo-restricoes, fronteira |
| M-07 | diagnostico | detecção estrutural de inviabilidade antes do solve, com conflito localizado | `analisar(instancia) -> [Conflito{plantao, exigidos, elegiveis}]` | dominio |
| M-08 | repositorio-json | adaptador de persistência em arquivos JSON | `salvar_escala/carregar_escala(id)` · `listar_trocas/salvar_troca` | dominio |
| M-09 | carregador | parse e validação da instância de entrada; aplica L4 (art. 59) como validação de configuração | `carregar(caminho) -> Instancia` (levanta `ErroDeValidacao`) | dominio |
| M-10 | gerador-sintetico | gera instâncias de teste reprodutíveis, incluindo instâncias inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-11 | cli | adaptador de entrada: os 5 casos de uso como comandos | `gerar · consultar · trocar · responder · conformidade` | todos |

**Fronteira arquitetural:** M-01…M-05 são núcleo puro — não importam `ortools`
nem tocam disco. M-06, M-08, M-09, M-11 são adaptadores. M-07 e M-10 são
serviços de domínio sem dependência externa.

**Invariante que sustenta a decomposição:** `catalogo-restricoes` é o **único
dono das regras**. `solver-cpsat` (modo *aplicar*) e `avaliador` (modo
*verificar*) são clientes iguais dele. Se uma regra passar a existir em dois
lugares, esta arquitetura falhou no ponto em que foi desenhada para não falhar.

## Mapa caso de uso → módulos

| UC | Fluxo |
|---|---|
| UC-1 gerar | cli → carregador → repositorio-json (mês anterior) → fronteira → diagnostico → solver-cpsat → repositorio-json (rascunho) |
| UC-2 consultar | cli → repositorio-json |
| UC-3 solicitar troca | cli → repositorio-json → troca (cria PENDENTE) |
| UC-4 responder troca | cli → repositorio-json → troca → avaliador → repositorio-json |
| UC-5 conformidade | cli → repositorio-json → avaliador |

## Premissas (AP4 — o que o sistema assume verdadeiro sem declarar em código)

| id | Premissa | Consequência se falsa |
|---|---|---|
| A1 | Tipos de turno têm horários fixos | a compilação de L1 em sucessões proibidas (`specs/technical/modelo-cpsat.md` §4) deixa de valer |
| A2 | Uma pessoa tem exatamente um contrato no horizonte | a natureza das restrições legais, que depende do regime, fica indefinida para ela |
| A3 | A escala do mês anterior, se existe, está publicada e cobre o mês inteiro | contadores S6/S7 sub-representados na virada (PR-4, aberta) |
| A4 | CP-SAT resolve 30×3×30 em ≤ 60 s | SC-2 falha (PR-2, aberta) |
| A5 | A identidade informada no comando é verdadeira | sem autenticação, qualquer um aceita troca em nome de qualquer um |
| A6 | O arquivo de instância não é hostil | entrada maliciosa não é modelada |
| A7 | Um operador por vez | sem trava de arquivo, execuções simultâneas se sobrescrevem |
| A8 | Os pesos do INRC-II são adequados ao contexto brasileiro | a escala é "ótima" segundo prioridades calibradas em outro país |

## Escopo negativo de V(1) (o que o sistema deliberadamente NÃO faz)

autenticação e permissões · UI gráfica, web ou API HTTP · notificações (e-mail,
push) · cálculo de remuneração ou folha · papel de gestor e homologação em duplo
estágio · calendário de feriados dedicado · otimização entre múltiplas unidades ·
linguagem genérica de regras (regras internas são parametrizadas, não
programáveis) · trava de arquivo contra execução concorrente · horizonte
diferente do mensal · equidade como critério de aceite (permanece termo flexível
com peso publicado).

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
  "projeto": "T22-plantoes",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
