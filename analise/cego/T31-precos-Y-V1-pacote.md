# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Motor de regras de preço com faixas, histórico e explicação da decisão, substituindo uma tabela legada

## A arquitetura

## V(1) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dinheiro | Valor monetário decimal exato (I-5); parsing BR (`R$ 1.189,50`); arredondamento half-up 2 casas aplicado só no resultado final | `de_texto(s) -> Dinheiro \| ErroFormato`, `multiplicar(qtd:int) -> Dinheiro`, `aplicar_pct(pct) -> Dinheiro`, `__eq__`, `__str__` | — |
| M-02 | modelo-dominio | Entidades e objetos de valor com invariantes: `Produto`, `Faixa`, `Efeito` (Strategy), `Regra`, `Vigencia`, `VersaoDeRegras`, `Candidata`, `Veredito`, `Trace`, `Decisao` | dataclasses imutáveis + `Efeito.aplicar(preco_base) -> Dinheiro`; `Faixa.contem(qtd) -> bool`; `Vigencia.contem(data) -> bool` | dinheiro |
| M-03 | motor-precificacao | Selecionar candidatas (escopo × faixa × vigência), aplicar o efeito vencedor, montar o trace **exaustivo** (I-3). Nunca lê o relógio | `precificar(versao, produto, qtd, data) -> Decisao` | modelo-dominio, resolvedor-precedencia |
| M-04 | resolvedor-precedencia | Prioridade decrescente → desempate por especificidade (SKU vence `*`) → empate residual levanta `EmpateInsoluvel` (I-6). Registra o motivo da derrota de cada perdedora | `resolver(candidatas) -> (vencedora, derrotas)` | modelo-dominio |
| M-05 | validador-coerencia | Checar um rascunho antes da publicação: `min>max`, sobreposição de faixas no mesmo escopo, lacuna de cobertura (aviso), empate insolúvel, preço base inconsistente por SKU | `validar(rascunho, produtos) -> Relatorio{erros[], avisos[]}` | modelo-dominio |
| M-06 | explicador | Converter o trace exaustivo em frase contrastiva pt-BR (guardar tudo, mostrar pouco) | `explicar(decisao) -> str` | modelo-dominio |
| M-07 | repositorio-sqlite | Data Mapper das portas de saída declaradas pelo núcleo; publicação atômica em transação; consulta de versão vigente por data | `publicar(rascunho) -> VersaoDeRegras`, `vigente_em(data) -> VersaoDeRegras \| None`, `salvar_rascunho(r)`, `rascunho_atual()`, `registrar(decisao)`, `listar(filtros)`, `obter(id) -> Decisao` | modelo-dominio |
| M-08 | importador-csv | Ler a planilha legada, normalizar formato (moeda BR, milhar, `Ate` textual, SKU com espaço/caixa), rejeitar linha inválida **com motivo nomeado** | `importar(bytes) -> Resultado{rascunho, rejeitadas[{linha,motivo}], produtos}` | modelo-dominio, dinheiro |
| M-09 | prova-paridade | Reconsultar no motor cada linha válida da planilha e comparar com o preço original (CS-1), com tolerância de R$ 0,01 | `verificar(linhas_validas, versao) -> Relatorio{conferem, divergencias[]}` | motor-precificacao |
| M-10 | servico-aplicacao | **Facade** única que API e UI consomem; orquestra motor, repositório, log, importador e validador | `precificar(sku, qtd, data)`, `importar(bytes)`, `validar_rascunho()`, `publicar()`, `historico(filtros)`, `recalcular(decisao_id)` | motor-precificacao, validador-coerencia, explicador, repositorio-sqlite, importador-csv, prova-paridade |
| M-11 | api-http | Adapter de entrada REST: rotas, DTOs, serialização do trace. **Data é obrigatória** no contrato de máquina | `POST /preco`, `POST /importar`, `POST /rascunho/validar`, `POST /publicar`, `GET /historico`, `GET /decisao/{id}`, `POST /decisao/{id}/recalcular` | servico-aplicacao |
| M-12 | ui-web | Adapter de entrada HTML: **4 telas** (regras, simulador, importação, histórico) em Jinja2 + JS mínimo servido localmente. Preenche a data com "hoje" de forma **visível e editável** | rotas server-rendered `/regras`, `/simular`, `/importar`, `/historico` | servico-aplicacao |

**Núcleo** = M-01..M-06. Não conhece SQLite, HTTP, CSV nem sistema de arquivos.
**Adapters de saída** = M-07 (persistência). **Adapters de entrada** = M-11, M-12.
M-08 e M-09 são adapters de dados sobre o núcleo. M-10 é a camada de aplicação.

### Portas declaradas pelo núcleo (DIP)

```
RepositorioDeVersoes: publicar, vigente_em, salvar_rascunho, rascunho_atual
LogDeDecisoes:        registrar, listar, obter
```
Implementadas por `repositorio-sqlite`. O núcleo depende das portas, nunca da
implementação — é o que torna `motor-precificacao` e `resolvedor-precedencia`
testáveis **sem banco**.

## Premissas (o que o sistema assume como verdade — AP4/Leveson)

| id | Premissa | Consequência se for falsa |
|---|---|---|
| A-01 | Quantidade é inteiro ≥ 1 | Faixas com fracionário (kg, m) quebram o matching |
| A-02 | SKU é chave, normalizável por `trim` + `upper` | Produto fantasma (` sku-1002 `) e sobreposição invisível |
| A-03 | Regra importada nasce com prioridade 0 e vigência aberta desde a data de importação | Todas empatam entre si — a validação passa a ser o que separa versão coerente de incoerente |
| A-04 | **O motor nunca lê o relógio.** Data é obrigatória no contrato da API; a UI preenche "hoje" de forma visível e editável | Determinismo (I-1) deixaria de ser testável, e o fuso do SO mudaria a versão vigente na virada do dia |
| A-05 | Preço base é único por SKU | Conflito (ex.: SKU-1007 com 29,90 e 31,00) é erro de importação, nunca média |
| A-06 | Processo single-user / single-threaded, sem trava | Publicação concorrente corromperia I-4 |
| A-07 | SQLite local, arquivo único; transação garante publicação atômica | Publicação parcial viola I-4 |
| A-08 | UI e API no mesmo processo e origem — sem CORS, sem auth | Exposição em rede muda o modelo de ameaça inteiro |
| A-09 | Frase em pt-BR, sem i18n; moeda única BRL | — |
| A-10 | Modelo **`volume`**: a faixa atingida vale para toda a quantidade | Toda a paridade (CS-1) depende disso |
| A-11 | Faixa é intervalo **fechado** `[min, max]`; `max` ausente = ∞ | Off-by-one nas bordas 19/20 (P-02/P-03) |
| A-12 | Versão publicada nunca é alterada nem removida | I-4 e I-7 |
| A-13 | Arredondamento half-up, 2 casas, aplicado **só no resultado final** do efeito | Arredondar em etapas muda centavos (P-09) |

## Escopo negativo (o que o sistema deliberadamente NÃO faz)

Autenticação, autorização, papéis, multiusuário · impostos, frete, moeda e câmbio ·
precificação em lote / reprecificação de catálogo · empilhamento ou composição de
descontos · categoria e hierarquia de produtos · publicação com vigência futura
agendada · bitemporalidade · **RETE / rede de discriminação** (descartado com
fundamento quantitativo) · i18n e multi-moeda · migração de schema (a v1 cria o
banco) · **qualquer dependência de rede em runtime** — nenhum CDN, todo asset é
servido localmente.

## Escopo progressivo

**Não se aplica.** O Delivery Target da Fase 0 é "Produto completo" e **não há
bloqueador técnico**: a Tech Feasibility confirmou todas as capacidades
essenciais, e o único componente Tier 3 (`resolvedor-precedencia`) é trivial e
dispensa PoC. Tudo é entregue em um único ciclo.

## Planejamento de sessões (ciclo desacoplado)

| Sessão | Contexto necessário |
|---|---|
| Design (Fases 0-4) | domínio + restrições → arquitetura + interfaces |
| Código (Fase 5) | este documento + a interface do módulo alvo + specs/ |
| Teste (Fase 6) | interface + contrato + `specs/datasets/casos-armadilha.md` |

Cada módulo cabe numa única interação com suas dependências (princípio
E = I₀/C): o maior deles, `servico-aplicacao`, é orquestração sobre 6 interfaces
já escritas acima — não precisa do código dos módulos, só dos contratos.

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
  "projeto": "T31-precos",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
