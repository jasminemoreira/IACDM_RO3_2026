# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Catálogo de dados com donos declarados por domínio e linhagem entre eles

## A arquitetura

## V(1)

### Padrões vigentes

| Dimensão | Escolhido |
|---|---|
| Arquitetural | Hexagonal / Ports & Adapters |
| Princípios transversais | KISS + YAGNI, SOLID (ênfase em SRP e DIP) |
| Concorrência | Single-threaded |
| GoF | Strategy (apenas) — formatadores de saída |
| Fowler — domínio | Domain Model |
| Fowler — dados | Repository + Data Mapper |
| Stack | Python (constraint travado na Fase 0) |
| Grafo | NetworkX — Tier 1, decidido na Validação Tecnológica |

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | model | Entidades e value objects puros e imutáveis: DatasetId, Owner, Domain, Dataset, LineageEdge, ImpactResult, ProvenanceResult, Violation | `DatasetId.parse(str) -> DatasetId` (valida forma `dominio.nome`); tipos imutáveis sem comportamento de I/O | — |
| M-02 | errors | Hierarquia de erros de domínio e redação das mensagens acionáveis (ciclo nomeado, referência pendente, domínio sem dono) | `CatalogError` + subclasses; `format_violations(list[Violation]) -> str` | model |
| M-03 | catalog | Agregado do Domain Model: coleção de domínios e datasets. Resolução de dono por herança do domínio com sobrescrita no dataset; lookup de existência | `resolve_owner(DatasetId) -> Owner`; `has(DatasetId) -> bool`; `domains() -> list[Domain]`; `datasets() -> list[Dataset]` | model |
| M-04 | lineage-graph | Grafo dirigido sobre NetworkX. Construção a partir da lista de arestas e exposição mínima das operações de travessia | `downstream(DatasetId) -> set[DatasetId]`; `upstream(DatasetId) -> set[DatasetId]`; `find_cycle() -> list[DatasetId] \| None`; `is_acyclic() -> bool` | model, NetworkX |
| M-05 | validation | Verificação das invariantes INV-1..INV-6, devolvendo TODAS as violações encontradas (nunca apenas a primeira) | `validate(catalog, graph) -> list[Violation]` | model, catalog, lineage-graph |
| M-06 | query-service | Os dois casos de uso de consulta: travessia do grafo mais resolução dos donos, deduplicados | `impact(DatasetId) -> ImpactResult`; `provenance(DatasetId) -> ProvenanceResult` | model, catalog, lineage-graph |
| M-07 | yaml-loader | Leitura do diretório e parsing YAML; validação da FORMA (campos obrigatórios, tipos). Não conhece regra de domínio | `load_files(Path) -> list[RawDomainDoc]` | errors, PyYAML |
| M-08 | catalog-mapper | Data Mapper: dicionários crus para entidades de domínio. Isola a INVERSÃO da aresta declarada pelo consumidor (`alimentado_por: X` produz aresta `X -> eu`) | `to_catalog(list[RawDomainDoc]) -> (Catalog, list[LineageEdge])` | model, catalog, errors |
| M-09 | catalog-repository | Porta do Hexagonal e seu adaptador. Orquestra loader, mapper, construção do grafo e validação; devolve catálogo já validado ou levanta erro | `load(Path) -> LoadedCatalog` | yaml-loader, catalog-mapper, lineage-graph, validation |
| M-10 | formatters | Strategy: TextFormatter e JsonFormatter sobre os mesmos resultados de domínio | `format_impact(ImpactResult) -> str`; `format_provenance(ProvenanceResult) -> str`; `format_violations(list[Violation]) -> str` | model |
| M-11 | cli | Composition root: subcomandos `validar`, `impacto`, `procedencia`; flag `--json`; wiring das dependências; códigos de saída | `main(argv: list[str]) -> int` | todos |

### Fronteiras

- **Núcleo puro:** M-01 a M-06. Nenhum conhece arquivo, YAML ou terminal.
- **Bordas (adaptadores):** M-07 a M-11.
- **Regra de dependência unidirecional:** borda → núcleo. Nunca o inverso.
- Motivação: o critério de acerto do projeto é igualdade exata de conjuntos sobre a
  consulta de impacto. Com o núcleo puro, essa asserção é feita sobre `query-service.impact`
  diretamente, sem atravessar arquivo nem stdout.

### Contratos de destaque

1. `catalog-repository.load(Path) -> LoadedCatalog` é a **única** porta de entrada de dados.
   Ou devolve catálogo válido, ou levanta erro. Não existe estado "carregado mas inválido"
   visível ao resto do sistema.
2. `query-service.impact(id) -> ImpactResult` recebe e devolve apenas tipos de `model`.
   É a função sobre a qual o critério de acerto é medido.
3. `formatters` recebe resultado de domínio e devolve string — nunca o inverso.
   Apresentação não vaza para dentro do núcleo.

Comunicação entre módulos: chamada direta de função com tipos de `model`. Sem eventos,
sem fila, sem estado global.

### Assunções

Herdadas da Fase 0:

- **A1** — Mover um dataset entre domínios MUDA sua identidade e invalida as arestas que o
  referenciam. Contraria diretamente a regra de estabilidade de nome da OpenLineage
  (ver `specs/references/data-catalog-standards.md` §2). Aceita como custo consciente.
- **A2** — Realimentação em pipeline (tabela agregada que volta a enriquecer a origem) NÃO é
  representável. Consequência do DAG estrito.
- **A3** — O diretório é carregado inteiro de uma vez; a ordem de cadastro dos domínios não
  importa dentro de um carregamento.
- **A4** — Impacto é transitivo completo, sem limite de saltos.
- **A5** — O resultado é um CONJUNTO de afetados, não os caminhos que levam a eles.

Acrescentadas na Fase 1:

- **A6** — `impact(X)` EXCLUI o próprio X; afetado é quem está a jusante. Segue a semântica de
  `networkx.descendants`, que não inclui a origem. Precisa ser explícito no contrato, ou a
  igualdade de conjuntos do critério de acerto falha por um elemento.
- **A7** — O grafo cabe em memória. O catálogo é declarado à mão, logo a ordem de grandeza é de
  dezenas a centenas de datasets.
- **A8** — A validação roda SEMPRE antes de qualquer consulta; não existe modo "consultar
  catálogo inválido". A documentação do NetworkX adverte que as funções de DAG não checam
  aciclicidade por conta própria.
- **A9** — Erros de carregamento são AGREGADOS: reporta todas as violações de uma vez, não
  apenas a primeira. Corrigir um erro por execução é atrito para o dono de domínio.
- **A10** — Nomes de domínio e de dataset NÃO contêm ponto. O ponto é o separador da
  identidade; sem essa restrição `a.b.c` é ambíguo.

### Escopo negativo

Herdado da Fase 0:
busca/descoberta · relatórios de auditoria agregados · linhagem em nível de coluna ·
scan automático ou importação OpenLineage · princípios 2-4 do Data Mesh.

Acrescentado no nível arquitetural:
sem persistência ou cache (recarrega a cada execução) · sem carregamento incremental ·
sem concorrência · sem rede, servidor ou autenticação · sem modo watch · sem arquivo de
configuração (o diretório vem por argumento) · sem escrita pelo sistema — a CLI só lê, quem
escreve o YAML é o humano.

### Invariantes que `validation` verifica

| # | Invariante |
|---|---|
| INV-1 | Todo dataset pertence a exatamente um domínio |
| INV-2 | Todo domínio tem dono |
| INV-3 | Nenhum dataset é órfão de dono |
| INV-4 | O grafo de linhagem é acíclico — ciclo é erro, com o ciclo nomeado |
| INV-5 | Toda aresta referencia datasets declarados nos dois extremos |
| INV-6 | Dependência entre domínios nunca é declarada, apenas derivada |

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
  "projeto": "T24-catalogo",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
