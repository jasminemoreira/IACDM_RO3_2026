# Arquitetura — T24 catálogo

Documento canônico de módulos. O **nome do módulo** (coluna 2) é a chave estável entre
as fases: a matriz de cobertura da Fase 2 e a implementação da Fase 5 devem usar
exatamente estes nomes.

Regra de versionamento deste arquivo: cada iteração do laço Fase 2 ↔ Fase 3 **acrescenta**
uma seção `## V(N+1)` com sua própria tabela de módulos. Nunca sobrescrever a anterior —
um achado da iteração 1 pode nomear um módulo que a V(2) removeu, e apagar a V(1) quebra
a rastreabilidade exatamente onde o desenho mais mudou. A última seção é a corrente.

---

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

## V(2)

Resposta unificada aos 53 achados da Iteração 1. **Dois módulos removidos, nenhum criado:
11 → 9.** A V(1) acima permanece intacta: achados da Iteração 1 nomeiam `errors` e
`catalog-repository`, que esta versão elimina.

### Os três movimentos estruturais

1. **`errors` funde em `model`.** Passa a ser apenas tipos (`Violation`, `CatalogInvalid`).
   TODA renderização de string vira exclusiva de `formatters`. Mata ARC-02 🔴: o contrato
   `format_violations` tinha dois donos.
2. **`catalog-repository` é removido.** `catalog-mapper` vira função PURA que produz
   `LoadedCatalog` ou lista de `Violation`; o wiring de I/O volta para `cli`, que já era o
   composition root. Mata ARC-01 🟡 e a raiz dos 10 achados por 8 lentes daquele módulo.
3. **`LoadedCatalog` só é construível por `catalog-mapper`, após validação.** A assunção A8
   ("validação sempre antes de qualquer consulta") deixa de ser documentação e vira
   propriedade do sistema de tipos. Mata ARC-04 🟢: burlar a validação passa de
   desaconselhado a impossível.

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | model | Entidades, value objects e tipos de erro (absorve o antigo `errors`). `Owner` congelado e hasheável, identidade por contato normalizado. `Domain.name` e `Dataset.name` rejeitam ponto na construção. `RawDomainDoc`, `LoadedCatalog`, `Violation`, `CatalogInvalid` declarados. `ImpactResult` carrega `afetados` e `responsaveis` já agrupados | `DatasetId.parse(str) -> DatasetId`; `Owner` hasheável com igualdade por valor; `CatalogInvalid(list[Violation])` | — |
| M-02 | catalog | Agregado do Domain Model. Distingue dono DECLARADO (`Domain.owner`) de dono EFETIVO (após sobrescrita). Sobrescrita é total: dono parcial vira `Violation` | `effective_owner(DatasetId) -> Owner`; `has(DatasetId) -> bool`; `domains()`; `datasets()` | model |
| M-03 | lineage-graph | Grafo dirigido sobre NetworkX >= 3.0. Único módulo que conhece a lib | `downstream(DatasetId) -> set[DatasetId]`; `upstream(DatasetId) -> set[DatasetId]`; `find_cycle() -> list[DatasetId] \| None`; `is_acyclic() -> bool` | model, NetworkX>=3.0 |
| M-04 | validation | Invariantes INV-1..INV-6 sobre tipos do `model`; delega a aciclicidade a `lineage-graph` numa única chamada. Ordem das violações DETERMINÍSTICA: domínio em ordem lexicográfica, depois ordem de declaração | `validate(catalog, edges, graph) -> list[Violation]` | model, catalog, lineage-graph |
| M-05 | query-service | Impacto e procedência: travessia mais resolução de donos, deduplicados por identidade estável de `Owner`. Levanta `DatasetNotFound` para dataset inexistente — distinto de devolver resultado vazio | `impact(DatasetId) -> ImpactResult`; `provenance(DatasetId) -> ProvenanceResult` | model, catalog, lineage-graph |
| M-06 | yaml-loader | Lê apenas `*.yaml` e `*.yml` do diretório, com `yaml.safe_load` OBRIGATÓRIO. Erro de parse e campo desconhecido viram `Violation` com arquivo e linha, nunca exceção vazada | `load_files(Path) -> (list[RawDomainDoc], list[Violation])` | model, PyYAML>=6.0 |
| M-07 | catalog-mapper | PURA. Único ponto de inversão da aresta declarada (`alimentado_por: X` produz `X -> eu`) e ÚNICO construtor de `LoadedCatalog`. Monta catálogo e grafo, roda a validação e devolve catálogo validado ou as violações | `assemble(list[RawDomainDoc]) -> LoadedCatalog \| list[Violation]` | model, catalog, lineage-graph, validation |
| M-08 | formatters | Strategy: TextFormatter e JsonFormatter. ÚNICO módulo que produz string no sistema. Agrupa a saída de impacto por dono; imprime frase explícita para impacto vazio; declara na saída que o resultado é limite inferior do conjunto real | `format_impact(ImpactResult) -> str`; `format_provenance(ProvenanceResult) -> str`; `format_violations(list[Violation]) -> str` | model |
| M-09 | cli | Composition root: I/O de diretório, wiring das dependências, subcomandos `validar`/`impacto`/`procedencia`, flag `--json`, códigos de saída. Diretório inexistente ou ilegível produz erro nomeado | `main(argv: list[str]) -> int` | todos |

### Módulos removidos em relação à V(1)

| módulo V(1) | destino |
|---|---|
| `errors` | Tipos absorvidos por `model`; renderização absorvida por `formatters` |
| `catalog-repository` | Composição pura absorvida por `catalog-mapper`; I/O e wiring absorvidos por `cli` |

### Assunções — mudanças em relação à V(1)

- **A6** permanece, mas agora é fixada por teste de caracterização de
  `networkx.descendants` na Fase 6 (resolve SCI-02).
- **A8** deixa de ser assunção e vira garantia de tipo (`LoadedCatalog` inconstruível sem
  validação).
- **A10** deixa de ser assunção e vira validação de construção em `Domain.name` e
  `Dataset.name` (resolve ASM-01 🔴).
- **A1, A2, A3, A4, A5, A7, A9** permanecem inalteradas.

### Limitações aceitas explicitamente pelo operador (Iteração 1)

Não são defeitos pendentes: são fronteiras conscientes, arbitradas pelo operador.

| achado | decisão |
|---|---|
| PROC-02 🔴 | INV-5 mantida: aresta pendente é ERRO. O catálogo só é válido quando completo; a adoção é big-bang. Preserva a garantia que motivou a regra — todo afetado tem dono resolvível, nunca há resposta silenciosamente incompleta. Resolve PROC-03 por consequência |
| CTRL-01 🔴 | O catálogo é uma DECLARAÇÃO, não um espelho verificado. Detectar drift exigiria o scan automático posto fora de escopo na Fase 0. A correção do grafo é responsabilidade humana |
| GAME-01 🔴 | A completude do grafo é propriedade SOCIAL, não técnica — nenhuma arquitetura corrige incentivo. Consequência de desenho: a saída de impacto declara que o resultado é LIMITE INFERIOR do conjunto real de afetados |
| SEC-03 🟡 / REG-01 🟡 | Contato profissional, finalidade explícita (notificação técnica), mínimo necessário. O histórico do git retém; remoção exigiria reescrita de histórico |
| ASM-05 🟡 / GAME-02 🟡 | `contato` é texto livre; validar "acionabilidade" não é possível |
| SEC-02 🟡 | O caminho vem do operador que executa a CLI na própria máquina, sem elevação de privilégio |
| PERF-01 🟡 / SUS-02 🟢 | Recarga completa por invocação é consequência do escopo negativo "sem cache" somado a A7 |
| PROC-01 🟡 | Notificar está FORA da fronteira do sistema. Construir notificação seria AP9 |
| GOV-01 🟡 | A autoria da atribuição vive no histórico do git, fora do artefato lido pelo sistema |
| GOV-02 🟡 | Consequência direta da decisão da Fase 0 de declarar a aresta pelo consumidor |
| SCI-01 🟢 | As referências de algoritmo passam a valer por delegação ao NetworkX, não por citação em código |

---

## V(3)

Resposta aos 22 achados da Iteração 2. **9 módulos, os mesmos nomes** — nenhum criado,
nenhum removido. O trabalho desta rodada foi REMOVER responsabilidade de onde ela se
acumulou, não movê-la de novo.

Diagnóstico que orientou a rodada: três dos 22 achados (ARC-06, ARC-07, GOV-04) eram
efeitos colaterais das correções da Iteração 1 — em dois casos a correção deslocou
complexidade, no terceiro criou o defeito inverso do que corrigiu.

### As três correções de raiz

1. **ARC-06 🔴 — `catalog-mapper` volta a duas responsabilidades: mapear e inverter.**
   A construção do grafo vai para `lineage-graph` (`build(edges)`, que é o trabalho dele).
   A certificação vai para `validation`: quem valida é quem certifica. A concentração que
   migrou de `catalog-repository` para `catalog-mapper` é DISSOLVIDA entre os donos
   naturais, sem criar módulo.
2. **IMPL-06 🔴 — a garantia muda de natureza.** Em vez de "só `catalog-mapper` pode
   construir `LoadedCatalog`" (inexequível: Python não tem construtor privado),
   `LoadedCatalog.__init__` EXIGE a lista de violações e RECUSA a construção se ela não
   estiver vazia. Deixa de importar QUEM constrói — construir um catálogo inválido passa a
   ser impossível para qualquer chamador. Garantia de linguagem, não de convenção.
3. **ARC-07 🟡 — `model` ENCOLHE em vez de crescer.** `Violation` e `CatalogInvalid` vão
   para `validation`, seu produtor natural. `ImpactResult`, `ProvenanceResult` e
   `DatasetNotFound` vão para `query-service`. `model` fica apenas com entidades e value
   objects. Zero módulos criados; o módulo mais atacado em duas rodadas seguidas fica menor.

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | model | APENAS entidades e value objects: `DatasetId`, `Owner`, `Domain`, `Dataset`, `LineageEdge`, `RawDomainDoc`, `LoadedCatalog`. `Owner` congelado e hasheável, chave por contato normalizado. `Domain.name` e `Dataset.name` rejeitam ponto. `LoadedCatalog` tem construtor AUTO-VALIDANTE: recebe as violações e recusa construir se houver alguma | `DatasetId.parse(str) -> DatasetId`; `LoadedCatalog(catalog, graph, violations)` levanta se `violations` não vazio | — |
| M-02 | catalog | Agregado do Domain Model. Distingue dono DECLARADO (`Domain.owner`) do EFETIVO (após sobrescrita). Sobrescrita é total | `effective_owner(DatasetId) -> Owner`; `has(DatasetId) -> bool`; `domains()`; `datasets()` | model |
| M-03 | lineage-graph | Grafo dirigido sobre NetworkX >= 3.0 e sua CONSTRUÇÃO a partir das arestas. Único módulo que conhece a lib | `build(list[LineageEdge]) -> LineageGraph`; `downstream(DatasetId) -> set`; `upstream(DatasetId) -> set`; `find_cycle() -> list \| None`; `is_acyclic() -> bool` | model, NetworkX>=3.0 |
| M-04 | validation | Dona de `Violation` e `CatalogInvalid`. Verifica INV-1..INV-6 e CERTIFICA: é a única função que produz um `LoadedCatalog`. Ordem determinística: violações SEM domínio primeiro, por nome de arquivo; depois as com domínio, em ordem lexicográfica e então de declaração | `certify(catalog, graph) -> LoadedCatalog`, levantando `CatalogInvalid(list[Violation])` | model, catalog, lineage-graph |
| M-05 | query-service | Dona de `ImpactResult`, `ProvenanceResult` e `DatasetNotFound`. Travessia mais resolução de donos, deduplicados por identidade estável de `Owner` | `impact(DatasetId) -> ImpactResult`; `provenance(DatasetId) -> ProvenanceResult`; levanta `DatasetNotFound` | model, catalog, lineage-graph |
| M-06 | yaml-loader | Lê apenas `*.yaml` e `*.yml`, com `yaml.safe_load` OBRIGATÓRIO. Erro de parse, arquivo ilegível e campo desconhecido viram `Violation`. Contrato explícito: se houver qualquer violação, os docs parciais NÃO são usados — o fluxo aborta | `load_files(Path) -> LoadResult(docs, violations)` | model, validation, PyYAML>=6.0 |
| M-07 | catalog-mapper | PURA e com DUAS responsabilidades apenas: mapear dicionários para entidades e INVERTER a aresta declarada (`alimentado_por: X` produz `X -> eu`). Não constrói grafo, não valida, não certifica | `to_catalog(list[RawDomainDoc]) -> (Catalog, list[LineageEdge], list[Violation])` | model, catalog, validation |
| M-08 | formatters | Strategy: TextFormatter e JsonFormatter. ÚNICO módulo que produz string. Agrupa impacto por dono; frase explícita para impacto vazio; a ressalva de limite inferior aparece UMA vez, em rodapé no modo texto e como campo `escopo: "declarado"` no modo JSON | `format_impact`; `format_provenance`; `format_violations` | model, validation, query-service |
| M-09 | cli | Composition root: I/O de diretório, wiring, subcomandos `validar`/`impacto`/`procedencia`, flag `--json`, códigos de saída. Diretório inexistente ou ilegível produz erro nomeado | `main(argv: list[str]) -> int` | todos |

### Fluxo de carregamento em V(3)

`cli` lê o diretório → `yaml-loader.load_files` → (aborta se houver violação) →
`catalog-mapper.to_catalog` → `lineage-graph.build` → `validation.certify` →
`LoadedCatalog` → `query-service`.

Cada passo tem um dono único e o último é o único capaz de produzir o objeto que
autoriza a consulta.

### Demais achados da Iteração 2 resolvidos

| id | resolução |
|---|---|
| GOV-04 🟡 | Dois nomes distintos com o MESMO contato geram `Violation` exigindo desambiguação. O conflito vira explícito em vez de colapso silencioso — e GOV-03 não reabre |
| LING-05 🟡 | `LoadResult` com contrato explícito: havendo violação, docs parciais não são usados e o fluxo aborta |
| IMPL-07 🟡 | A união de retorno DESAPARECE: `certify()` levanta `CatalogInvalid` |
| IMPL-08 🟡 | Violações sem domínio vêm primeiro, ordenadas por nome de arquivo |
| RES-04 🟡 | `Violation.arquivo` obrigatório; `Violation.linha` opcional, ausente quando não aplicável |
| UX-06 🟡 | Ressalva de limite inferior: uma vez, em rodapé (texto) ou campo `escopo` (JSON) |
| ASM-06 🟡 | O teste de caracterização de `descendants`/`ancestors`/`find_cycle` vira requisito de SAÍDA DA FASE 5 para `lineage-graph`, não da Fase 6 |
| ARC-08 🟡 | Mitigado: o construtor auto-validante remove o risco principal de um erro de composição em `cli` passar despercebido |

### Precisão acrescentada a A9 na Fase 6

Um teste falhando revelou que A9 ("erros de carregamento são agregados") era imprecisa.
**A agregação é POR ESTÁGIO, e o estágio de FORMA porteia o estágio SEMÂNTICO.**

Motivo, e ele não é conveniência de implementação: rodar a validação semântica sobre o
catálogo PARCIAL — só os arquivos que passaram na forma — geraria FALSOS POSITIVOS, pois
toda aresta apontando para dataset do arquivo rejeitado seria reportada como "aresta
pendente", um defeito que não existe. Reportar defeito inexistente é pior que exigir uma
segunda rodada.

O que A9 garante, então: o operador enfrenta no máximo DUAS rodadas (corrigir a forma,
depois a semântica), nunca N rodadas de um erro por vez — que era o atrito que A9 existe
para evitar. Coberto pelos testes `test_violacoes_de_forma_agregadas`,
`test_violacoes_semanticas_agregadas` e
`test_forma_porteia_semantica_para_nao_gerar_falso_positivo`.

Aceitos sem mudança: SEC-05 🟢 (normalização em minúsculas segue a prática dominante),
GOV-05 🟢, LING-06 🟢 (nome do módulo mantido para preservar rastreabilidade entre fases),
GAME-03 🟢, MEC-04 🟢, PERF-04 🟢, PROC-05 🟢, e as três duplicatas.
