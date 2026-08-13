# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Importador de extratos de múltiplas fontes externas, com deduplicação e conciliação

## A arquitetura

## V(1) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | domain-model | Entidades, value objects e os 5 estados terminais de conciliação. Garante os invariantes I1-I8 na construção do objeto | `Dinheiro(Decimal,2)`, `Transacao`, `Lancamento`, `Casamento`, `Pendencia`, `Resolucao`, `EstadoConciliacao{casado, casado-com-divergencia, orfao-no-extrato, orfao-no-livro, pendente-de-revisao}` | — |
| M-02 | canonicalizer | Normalização (descrição, data, sinal, encoding) e cálculo do hash canônico | `normalizar(bruto, perfil) -> Transacao\|Lancamento`; `hash_canonico(item) -> str` | domain-model |
| M-03 | ofx-adapter | Adapta OFX (v1 SGML / v2 XML) à porta FonteDeExtrato, via ofxtools | `ler(caminho, fonte) -> Iterable[RegistroBruto]` | domain-model |
| M-04 | csv-adapter | Parser CSV dirigido por perfil declarativo; 3 perfis de banco + perfil do livro | `carregar_perfil(nome) -> PerfilCSV`; `validar_perfil(p) -> [Erro]`; `ler(caminho, perfil) -> Iterable[RegistroBruto]` | domain-model |
| M-05 | repository | Portas de persistência + Data Mapper SQLite. UNIQUE sobre a identidade; import atômico | `salvar_transacoes(lote) -> ResultadoImport`; `buscar_por_identidade(chave)`; `salvar_casamentos(cs)`; `salvar_pendencia(p)`; `buscar_resolucao(par) -> Resolucao\|None` | domain-model |
| M-06 | matcher | Geração de candidatos por blocking + score de similaridade par-a-par (pesos estilo Fellegi-Sunter, rapidfuzz) | `candidatos(a, b, chave_bloco) -> Iterable[Par]`; `score(par) -> float` | domain-model |
| M-07 | dedup-engine | Chain of Responsibility L0→L5: decide duplicata, pendência ou distinta, registrando a camada que decidiu e a evidência | `classificar(nova, existentes) -> DecisaoDedup{veredito, camada, evidencia}` | domain-model, matcher, repository |
| M-08 | reconcile-engine | Casamento 1:1 extrato × livro; atribui exatamente um dos 5 estados; janela de data e tolerância de valor configuráveis | `conciliar(transacoes, lancamentos, config) -> ResultadoConciliacao` | domain-model, matcher, repository |
| M-09 | review-queue | Fila de pendências e resoluções humanas persistidas; alimenta a camada L0 do dedup-engine | `listar(filtro) -> [Pendencia]`; `resolver(id, acao) -> Resolucao` | domain-model, repository |
| M-10 | reporter | Relatórios: contagem por estado (soma = total) e sub-rotulação de órfão esperado vs anômalo por idade do item | `resumo(escopo) -> Relatorio`; `render(relatorio, formato)` | domain-model, repository |
| M-11 | cli | Superfície do operador: import, reconcile, review, report. Composition root — monta adapters e injeta as portas | `main(argv) -> int` | todos |
| M-12 | fixture-generator | Gerador sintético determinístico (seed fixa): fixtures OFX/CSV, duplicatas de reimportação e cross-source plantadas, colisões legítimas plantadas, carga de 50k e ground truth rotulado | `gerar(seed, n, perfil) -> (arquivos, GroundTruth)` | domain-model, csv-adapter |

### Fronteiras

O núcleo — `domain-model`, `canonicalizer`, `matcher`, `dedup-engine`, `reconcile-engine` — **não
importa** `ofxtools`, `sqlite3` nem `csv`. Os adapters (`ofx-adapter`, `csv-adapter`, `repository`)
e o composition root (`cli`) são os únicos pontos de contato com o mundo externo.

### Interfaces (Design by Contract)

- **Portas de entrada:** `FonteDeExtrato`, implementada por `ofx-adapter` e `csv-adapter`.
- **Portas de saída:** `RepositorioTransacoes`, `RepositorioCasamentos`, `RepositorioResolucoes` —
  implementadas por `repository` e por dublês em memória nos testes.
- `matcher` recebe itens já canônicos; não sabe de qual formato vieram.
- `DecisaoDedup` **sempre** carrega qual camada decidiu (L0-L5) e a evidência. Sem isso não há como
  auditar um falso positivo — e VAL-2 exige zero deles.

---

## Premissas (AP4 — declaradas, não implícitas)

| id | Premissa | Fragilidade | Origem |
|---|---|---|---|
| A1 | O `FITID` é estável entre downloads da mesma transação | **Alta** | Contra-evidência documentada em `specs/references/fontes-externas.md` §1.2. Se falso, L1 falha e o caso cai em L2/L3 |
| A2 | CSV de banco não traz ID nativo, logo a identidade depende do hash canônico | Média | Fase 0, N1 |
| A3 | O layout do CSV do livro interno é estável e declarado | Média | Fase 0, N3 |
| A4 | O blocking mantém blocos pequenos (b ≤ 50) | **Alta** | `specs/technical/parametros-matching.md` §Orçamento. Tarifas de valor redondo repetido produzem bloco degenerado e reintroduzem O(n²) |
| A5 | Todo par tem uma resposta certa quanto a "é o mesmo evento?", e o humano a conhece | Média | Fase 0, N4 |
| A6 | A descrição da contraparte é comparável entre fontes | **Alta** | O banco escreve `PIX ENVIADO JOAO`, o ERP escreve `João da Silva ME`. Se a similaridade de descrição for ruído, o score cross-source perde poder discriminante |
| A7 | `abs(valor)` como chave de bloco não confunde estorno com duplicata | **Alta** | Ambiguidade 4 da Fase 0, deixada deliberadamente em aberto para a crítica |

## Escopo negativo

O sistema deliberadamente **não**: categoriza contabilmente transações · casa 1:N/N:1
automaticamente (esses casos viram pendência) · trata multi-moeda ou câmbio · expõe UI web, rede ou
autenticação · lê CAMT.053 ou API de agregadora · funde sob evidência fraca (prefere pendência a
falso positivo) · sobrescreve decisão humana registrada.

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
  "projeto": "T26-extratos",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
