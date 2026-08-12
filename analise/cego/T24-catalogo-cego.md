# Reagrupamento cego de achados — T24-catalogo

Você recebe 75 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
módulo onde ocorre, a severidade e uma descrição de uma linha.

**Sua tarefa:** agrupar os achados que apontam o MESMO DEFEITO.

Atenção a defeitos **replicados**: quando dois módulos são implementações irmãs do
mesmo contrato, o mesmo defeito pode aparecer em ambos. Se uma única correção na
abstração compartilhada resolveria os dois, é o mesmo defeito.

**Critério, e é o único que vale:**

> Dois achados são o mesmo defeito quando apontam o mesmo problema no mesmo local,
> com a mesma causa raiz. Regra operacional: **se corrigir um resolveria
> automaticamente o outro, é o mesmo defeito.** Se cada um exige uma correção
> própria, são defeitos distintos — mesmo que estejam no mesmo módulo e sejam
> parecidos.

**Viés conservador, obrigatório:** na dúvida, **NÃO** agrupe. Agrupar a mais é o erro
mais caro aqui.

Não explique, não comente, não reordene. Responda **só** com este JSON:

```json
{"grupos": [["F-03", "F-07"], ["F-11", "F-02", "F-19"]]}
```

Cada lista interna é um grupo de achados que são o mesmo defeito. Achados que não
são duplicata de nenhum outro **não aparecem** — grupos de um só elemento são
implícitos. Se nenhum achado for duplicata de outro, responda `{"grupos": []}`.

## A arquitetura

Os módulos do sistema, para você saber o que cada nome significa e quais são irmãos
entre si:

| id | módulo | responsabilidade | interface | depende-de |
|---|---|---|---|---|
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
| M-01 | model | Entidades, value objects e tipos de erro (absorve o antigo `errors`). `Owner` congelado e hasheável, identidade por contato normalizado. `Domain.name` e `Dataset.name` rejeitam ponto na construção. `RawDomainDoc`, `LoadedCatalog`, `Violation`, `CatalogInvalid` declarados. `ImpactResult` carrega `afetados` e `responsaveis` já agrupados | `DatasetId.parse(str) -> DatasetId`; `Owner` hasheável com igualdade por valor; `CatalogInvalid(list[Violation])` | — |
| M-02 | catalog | Agregado do Domain Model. Distingue dono DECLARADO (`Domain.owner`) de dono EFETIVO (após sobrescrita). Sobrescrita é total: dono parcial vira `Violation` | `effective_owner(DatasetId) -> Owner`; `has(DatasetId) -> bool`; `domains()`; `datasets()` | model |
| M-03 | lineage-graph | Grafo dirigido sobre NetworkX >= 3.0. Único módulo que conhece a lib | `downstream(DatasetId) -> set[DatasetId]`; `upstream(DatasetId) -> set[DatasetId]`; `find_cycle() -> list[DatasetId] \| None`; `is_acyclic() -> bool` | model, NetworkX>=3.0 |
| M-04 | validation | Invariantes INV-1..INV-6 sobre tipos do `model`; delega a aciclicidade a `lineage-graph` numa única chamada. Ordem das violações DETERMINÍSTICA: domínio em ordem lexicográfica, depois ordem de declaração | `validate(catalog, edges, graph) -> list[Violation]` | model, catalog, lineage-graph |
| M-05 | query-service | Impacto e procedência: travessia mais resolução de donos, deduplicados por identidade estável de `Owner`. Levanta `DatasetNotFound` para dataset inexistente — distinto de devolver resultado vazio | `impact(DatasetId) -> ImpactResult`; `provenance(DatasetId) -> ProvenanceResult` | model, catalog, lineage-graph |
| M-06 | yaml-loader | Lê apenas `*.yaml` e `*.yml` do diretório, com `yaml.safe_load` OBRIGATÓRIO. Erro de parse e campo desconhecido viram `Violation` com arquivo e linha, nunca exceção vazada | `load_files(Path) -> (list[RawDomainDoc], list[Violation])` | model, PyYAML>=6.0 |
| M-07 | catalog-mapper | PURA. Único ponto de inversão da aresta declarada (`alimentado_por: X` produz `X -> eu`) e ÚNICO construtor de `LoadedCatalog`. Monta catálogo e grafo, roda a validação e devolve catálogo validado ou as violações | `assemble(list[RawDomainDoc]) -> LoadedCatalog \| list[Violation]` | model, catalog, lineage-graph, validation |
| M-08 | formatters | Strategy: TextFormatter e JsonFormatter. ÚNICO módulo que produz string no sistema. Agrupa a saída de impacto por dono; imprime frase explícita para impacto vazio; declara na saída que o resultado é limite inferior do conjunto real | `format_impact(ImpactResult) -> str`; `format_provenance(ProvenanceResult) -> str`; `format_violations(list[Violation]) -> str` | model |
| M-09 | cli | Composition root: I/O de diretório, wiring das dependências, subcomandos `validar`/`impacto`/`procedencia`, flag `--json`, códigos de saída. Diretório inexistente ou ilegível produz erro nomeado | `main(argv: list[str]) -> int` | todos |
| M-01 | model | APENAS entidades e value objects: `DatasetId`, `Owner`, `Domain`, `Dataset`, `LineageEdge`, `RawDomainDoc`, `LoadedCatalog`. `Owner` congelado e hasheável, chave por contato normalizado. `Domain.name` e `Dataset.name` rejeitam ponto. `LoadedCatalog` tem construtor AUTO-VALIDANTE: recebe as violações e recusa construir se houver alguma | `DatasetId.parse(str) -> DatasetId`; `LoadedCatalog(catalog, graph, violations)` levanta se `violations` não vazio | — |
| M-02 | catalog | Agregado do Domain Model. Distingue dono DECLARADO (`Domain.owner`) do EFETIVO (após sobrescrita). Sobrescrita é total | `effective_owner(DatasetId) -> Owner`; `has(DatasetId) -> bool`; `domains()`; `datasets()` | model |
| M-03 | lineage-graph | Grafo dirigido sobre NetworkX >= 3.0 e sua CONSTRUÇÃO a partir das arestas. Único módulo que conhece a lib | `build(list[LineageEdge]) -> LineageGraph`; `downstream(DatasetId) -> set`; `upstream(DatasetId) -> set`; `find_cycle() -> list \| None`; `is_acyclic() -> bool` | model, NetworkX>=3.0 |
| M-04 | validation | Dona de `Violation` e `CatalogInvalid`. Verifica INV-1..INV-6 e CERTIFICA: é a única função que produz um `LoadedCatalog`. Ordem determinística: violações SEM domínio primeiro, por nome de arquivo; depois as com domínio, em ordem lexicográfica e então de declaração | `certify(catalog, graph) -> LoadedCatalog`, levantando `CatalogInvalid(list[Violation])` | model, catalog, lineage-graph |
| M-05 | query-service | Dona de `ImpactResult`, `ProvenanceResult` e `DatasetNotFound`. Travessia mais resolução de donos, deduplicados por identidade estável de `Owner` | `impact(DatasetId) -> ImpactResult`; `provenance(DatasetId) -> ProvenanceResult`; levanta `DatasetNotFound` | model, catalog, lineage-graph |
| M-06 | yaml-loader | Lê apenas `*.yaml` e `*.yml`, com `yaml.safe_load` OBRIGATÓRIO. Erro de parse, arquivo ilegível e campo desconhecido viram `Violation`. Contrato explícito: se houver qualquer violação, os docs parciais NÃO são usados — o fluxo aborta | `load_files(Path) -> LoadResult(docs, violations)` | model, validation, PyYAML>=6.0 |
| M-07 | catalog-mapper | PURA e com DUAS responsabilidades apenas: mapear dicionários para entidades e INVERTER a aresta declarada (`alimentado_por: X` produz `X -> eu`). Não constrói grafo, não valida, não certifica | `to_catalog(list[RawDomainDoc]) -> (Catalog, list[LineageEdge], list[Violation])` | model, catalog, validation |
| M-08 | formatters | Strategy: TextFormatter e JsonFormatter. ÚNICO módulo que produz string. Agrupa impacto por dono; frase explícita para impacto vazio; a ressalva de limite inferior aparece UMA vez, em rodapé no modo texto e como campo `escopo: "declarado"` no modo JSON | `format_impact`; `format_provenance`; `format_violations` | model, validation, query-service |
| M-09 | cli | Composition root: I/O de diretório, wiring, subcomandos `validar`/`impacto`/`procedencia`, flag `--json`, códigos de saída. Diretório inexistente ou ilegível produz erro nomeado | `main(argv: list[str]) -> int` | todos |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | formatters | 🟡 | Impacto vazio: a borda foi identificada na Fase 0, mas nenhum contrato diz o que se imprime. Saída silenciosa é indistinguível de falha do comando |
| F-02 | model | 🟡 | nome e e-mail corporativo são dado pessoal sob LGPD/GDPR; nenhum módulo tem rastreabilidade a base legal, finalidade ou política de retenção |
| F-03 | errors | 🔴 | `format_violations(list[Violation]) -> str` está declarado em DOIS módulos: errors (M-02) e formatters (M-10). Dois donos para o mesmo contrato — a Fase 5 não tem como saber onde implementar, e o Strategy de saída fica pela metade |
| F-04 | catalog-mapper | 🔴 | A10 (nomes sem ponto) está declarada mas nenhum módulo recebeu a responsabilidade de IMPÔ-LA. Um domínio nomeado `vendas.br` gera identidade `vendas.br.pedidos`, que `DatasetId.parse` lê como domínio `vendas` + dataset `br.pedidos` → resolve o dono ERRADO, silenciosamente |
| F-05 | model | 🟡 | Identidade de `Owner` por contato normalizado COLAPSA pessoas distintas que compartilham caixa (`dados@empresa.com` vira um dono só, com nome escolhido arbitrariamente entre os dois). É o defeito inverso de GOV-03, introduzido pela correção de GOV-03 |
| F-06 | lineage-graph | 🟡 | Uma dependência inteira (NetworkX) é trazida para usar três funções sobre um grafo de dezenas de nós. O footprint da dependência é desproporcional à operação que ela executa |
| F-07 | catalog-repository | 🟡 | O contrato diz "levanta erro se inválido", mas não diz QUAL erro nem como ele transporta a lista de Violations até a CLI para formatação |
| F-08 | lineage-graph | 🟢 | As referências depositadas (Kahn 1962, Tarjan 1976, CLRS §22.4) não serão consumidas por código algum, já que a decisão foi NetworkX. O critério "algoritmo com referência" passa a ser satisfeito por delegação à lib, não por citação no código |
| F-09 | model | 🟢 | Normalizar contato para minúsculas pode colidir endereços distintos: a RFC 5321 permite local-part sensível a maiúsculas, ainda que a prática dominante não use |
| F-10 | catalog-repository | 🟢 | Diretório existente mas sem nenhum arquivo: catálogo vazio é resultado válido ou erro? As duas leituras são defensáveis e nada decide |
| F-11 | catalog | 🟡 | O dono é atribuído mas nada no modelo registra QUEM fez a atribuição e QUANDO. A autoria existe só no histórico do git, fora do artefato que o sistema lê |
| F-12 | validation | 🟢 | A detecção de ciclo roda em todo carregamento, inclusive no comando `validar` de um catálogo sem nenhuma aresta, onde o resultado é conhecido de antemão |
| F-13 | cli | 🟢 | A adoção big-bang aceita em PROC-02 não tem passo de processo definindo QUEM coordena a entrada simultânea de todos os domínios |
| F-14 | model | 🟢 | O formato YAML não tem campo de versão — não existe caminho de evolução do contrato de declaração sem quebrar os catálogos já escritos |
| F-15 | lineage-graph | 🟡 | Nenhuma versão mínima de NetworkX nem de PyYAML declarada. Sem pin, a build não é reprodutível e a semântica de `descendants` de que A6 depende fica à mercê da versão instalada |
| F-16 | lineage-graph | 🟢 | nenhum algoritmo novo foi introduzido pela V(2); as referências permanecem satisfeitas por delegação ao NetworkX |
| F-17 | yaml-loader | 🔴 | Se o parsing usar `yaml.load` sem `SafeLoader`, o YAML permite instanciar objetos Python arbitrários — carregar um catálogo vindo de fora executa código. O módulo lê arquivos de um diretório passado por argumento, então o vetor é direto |
| F-18 | catalog-repository | 🔴 | INV-5 (aresta pendente é erro) trava a adoção incremental: o domínio A não consegue commitar um arquivo válido declarando `alimentado_por: b.x` enquanto B não existir. Não há caminho de exceção definido, e o primeiro domínio a adotar o catálogo fica impedido de declarar suas dependências reais |
| F-19 | cli | 🟡 | O fluxo termina em "aqui estão os donos". O passo de NOTIFICAR está fora do sistema e nada registra que ele ocorreu — o UC-2 não fecha, e o handoff entre engenheiro e dono fica sem confirmação |
| F-20 | catalog-repository | 🟡 | Diretório inexistente, vazio de permissão, ou arquivo ilegível no meio do lote — nenhum desses caminhos está especificado |
| F-21 | model | 🟢 | `model` cresceu absorvendo `errors` e continua sem versão de contrato: a superfície que precisa evoluir sem quebrar aumentou |
| F-22 | yaml-loader | 🟡 | Arquivo ilegível por permissão não tem linha nem conteúdo para preencher a `Violation` com arquivo e linha que RES-01 exige; falta a forma degradada do contrato |
| F-23 | catalog-repository | 🟡 | Assume que o diretório contém APENAS arquivos de catálogo. Um `README.md`, `.gitkeep` ou `.yaml.bak` no mesmo diretório tem comportamento indefinido: ignorar, falhar ou tentar parsear |
| F-24 | model | 🟡 | Nome e contato de pessoas ficam em texto claro em repositório versionado; o histórico do git retém indefinidamente mesmo após remoção |
| F-25 | query-service | 🟡 | A6 passa a ser "fixada por teste de caracterização na Fase 6", mas nada na V(2) impede a Fase 5 de implementar sobre `descendants` antes desse teste existir — a garantia é cronológica, não estrutural |
| F-26 | yaml-loader | 🟡 | Arquivo YAML sintaticamente inválido: a exceção do PyYAML vaza para o usuário sem dizer qual arquivo nem qual domínio a produziu |
| F-27 | formatters | 🟡 | "impacto" nomeia três coisas: o subcomando, o conjunto de datasets afetados e o resultado já com donos. Três referentes, um termo |
| F-28 | yaml-loader | 🟢 | O dono de domínio escreve YAML à mão sem schema, autocomplete ou comando que gere um arquivo modelo; o primeiro contato com o formato é por tentativa e erro |
| F-29 | query-service | 🟢 | A6 (impact exclui o próprio X) está declarada na arquitetura mas não aparece no nome nem na assinatura do contrato; quem implementar M-06 sem ler as assunções erra por um elemento |
| F-30 | catalog-mapper | 🟡 | Como a aresta cross-domínio é declarada pelo consumidor, o PRODUTOR passa a figurar na análise de impacto de terceiros sem ter consentido nem tomado ciência. Atribuição de responsabilidade sem conhecimento do atribuído |
| F-31 | cli | 🟢 | Nada no desenho garante que a validação rode no CI; a garantia de catálogo válido depende inteiramente de disciplina humana |
| F-32 | lineage-graph | 🟡 | A assunção A6 repousa na semântica de `networkx.descendants` (não inclui a origem), lida da documentação. Nenhum teste de caracterização fixa esse comportamento: se a lib mudar, o critério de acerto muda em silêncio |
| F-33 | catalog-mapper | 🟢 | A V(2) não alterou o laço de controle: continua sem sinal de divergência entre catálogo e realidade — coerente com a limitação aceita em CTRL-01 |
| F-34 | model | 🔴 | `Owner` não tem identidade estável: é `{nome, contato}` por valor. A mesma pessoa escrita de duas formas em dois domínios (`Maria Silva` / `maria silva`, ou dois e-mails) vira DOIS donos, e a deduplicação exigida pelo critério de acerto falha |
| F-35 | catalog-repository | 🟡 | O caminho do diretório vem por argumento e nada restringe a travessia: symlink apontando para fora, ou caminho absoluto arbitrário, fazem o carregador ler o que não deveria |
| F-36 | yaml-loader | 🟡 | `load_files -> (list[RawDomainDoc], list[Violation])` não diz o que significa devolver docs PARCIAIS junto de violações: o chamador prossegue com o que veio ou aborta? Duas implementações corretas do contrato divergem |
| F-37 | formatters | 🟡 | A ressalva "resultado é limite inferior" (exigida pela arbitragem de GAME-01) não tem lugar definido: repetida em toda saída vira ruído, e em `--json` não se sabe se é campo, comentário ou ausente |
| F-38 | catalog-repository | 🟡 | Recarrega, remapeia, reconstrói o grafo e revalida o catálogo INTEIRO a cada invocação, mesmo para consultar um único dataset. O custo é O(V+E) do catálogo por consulta, não da consulta |
| F-39 | formatters | 🟢 | A ressalva de limite inferior é textual; em `--json` um consumidor programático a ignora sem custo algum |
| F-40 | validation | 🟡 | A ordem determinística definida (domínio em ordem lexicográfica, depois ordem de declaração) NÃO cobre violações sem domínio — erro de parse de um arquivo que sequer chegou a ter o campo `dominio` lido |
| F-41 | validation | 🟢 | A validação regula a consistência INTERNA do catálogo (invariantes entre declarações), nunca a externa. Registro explícito de onde termina o laço de controle |
| F-42 | model | 🟡 | "dono" nomeia dois conceitos: o declarado no domínio e o efetivo resolvido após sobrescrita. `resolve_owner` devolve o efetivo, mas nenhum termo distingue os dois |
| F-43 | validation | 🟡 | `validate() -> list[Violation]` não define a ORDEM das violações. A9 exige reportar todas de uma vez; ordem não-determinística torna a saída de erro impossível de asserir em teste |
| F-44 | cli | 🟡 | Subcomandos em português (`validar`, `impacto`, `procedencia`) com flag em inglês (`--json`) e campos YAML em português (`alimentado_por`) — a interface mistura idiomas sem regra declarada |
| F-45 | formatters | 🟢 | Não está especificado se `--json` também troca o formato da SAÍDA DE ERRO, nem qual código de saída acompanha cada caso |
| F-46 | formatters | 🟢 | Agrupar por dono torna visível quem tem mais dependentes, criando incentivo a subdeclarar para "parecer menos crítico" — o agrupamento que resolve UX-01 cria pressão nova |
| F-47 | model | 🟡 | `RawDomainDoc` circula entre yaml-loader e catalog-mapper mas não está na lista de tipos de `model` — tipo órfão, sem módulo dono declarado |
| F-48 | model | 🔴 | "LoadedCatalog só é construível por catalog-mapper" é CONVENÇÃO, não garantia: Python não tem construtor privado. Sem mecanismo concreto (módulo privado com factory, token de construção, ou tipo interno encapsulado), ARC-04 da Iteração 1 não foi resolvido — foi redocumentado com outra palavra |
| F-49 | cli | 🟢 | Nenhum requisito normativo do domínio (DCAT, OpenLineage) é obrigatório para este produto e nenhum módulo reivindica conformidade. Registro explícito de ausência de requisito regulatório de catálogo |
| F-50 | yaml-loader | 🟢 | Sem limite declarado de tamanho de arquivo nem de profundidade de aninhamento — YAML com expansão de aliases (billion laughs) consome memória desproporcional |
| F-51 | cli | 🟢 | `depends-on: todos` não é verificável. Nada no desenho impede a CLI de chamar query-service pulando catalog-repository, contornando a validação obrigatória (A8) |
| F-52 | cli | 🟡 | `cli` absorveu o wiring do repositório removido e segue dependendo de todos os módulos: passou a ser o único ponto do sistema onde um erro de composição não é detectável por tipo |
| F-53 | validation | 🟡 | Depende de lineage-graph, que depende de NetworkX. Testar as invariantes isoladamente exige construir um DiGraph real — acoplamento indireto do núcleo a uma lib de terceiro |
| F-54 | formatters | 🔴 | A promessa do produto é "quem eu preciso avisar", mas o contrato de saída não especifica AGRUPAMENTO POR DONO. Uma lista plana de 40 datasets afetados obriga o engenheiro a fazer o agrupamento na cabeça — o produto entrega o dado e não a resposta |
| F-55 | model | 🟡 | Assume que `contato` em texto livre é acionável. A promessa do produto é "quem avisar"; nada no modelo garante que a string sirva para avisar alguém |
| F-56 | catalog | 🟡 | Um dono pode declarar contato genérico (`dados@empresa.com`) para não ser pessoalmente notificado: satisfaz a validação, esvazia o propósito. Nada no modelo distingue contato acionável de contato de fachada |
| F-57 | model | 🟡 | `LoadedCatalog` aparece na interface de catalog-repository mas não consta entre os tipos de `model` — segundo tipo sem dono, junto de ASM/ARC-05 |
| F-58 | catalog-repository | 🟡 | Acumula quatro responsabilidades (ler, mapear, construir grafo, validar). É o único módulo que não pode ser testado sem os outros quatro — viola SRP e é o ponto onde o Hexagonal vaza |
| F-59 | catalog | 🟡 | Assume que a sobrescrita de dono é TOTAL. Não está dito se um dataset pode sobrescrever só o contato mantendo o nome herdado — as duas leituras são defensáveis e produzem resultados diferentes no UC-5 |
| F-60 | cli | 🟡 | Consultar dataset inexistente e consultar dataset folha são situações distintas ("não existe" vs "existe e não afeta ninguém") e nada garante mensagens distintas — confundi-las leva o engenheiro a concluir que a mudança é segura |
| F-61 | validation | 🟢 | `Violation` não distingue erro de FORMA (YAML malformado, campo faltando) de violação de INVARIANTE (ciclo, órfão) — dois níveis de falha sob um único tipo |
| F-62 | catalog-mapper | 🔴 | `alimentado_por` é declarado na direção INVERSA à aresta do grafo. Duas implementações corretas do contrato escrito podem tomar direções opostas e ambas parecerem certas — impacto e procedência trocados produzem resultado plausível e silenciosamente errado |
| F-63 | yaml-loader | 🟡 | Nenhuma tolerância declarada para campo desconhecido no YAML. Rejeitar quebra arquivos quando o formato evoluir; ignorar em silêncio esconde erro de digitação (`alimentado_pro:` passa despercebido e a aresta some). O contrato não escolhe |
| F-64 | catalog-mapper | 🔴 | O valor da análise de impacto do produtor depende inteiramente da diligência dos CONSUMIDORES em declarar `alimentado_por`. Quem omite não paga custo algum — apenas deixa de receber aviso — enquanto o custo da omissão recai sobre o produtor, que decide mudar com grafo incompleto. O desenho assume cooperação onde o incentivo aponta para omissão |
| F-65 | catalog-repository | 🟢 | a 10× o custo por consulta continua barato em absoluto, mas cresce com o tamanho do catálogo em vez de com o tamanho da pergunta |
| F-66 | catalog-repository | 🔴 | O catálogo é um modelo declarado de um mundo real (pipelines) que muda sem avisar o sistema, e NENHUM módulo gera sinal de erro quando a declaração diverge da realidade. O drift é silencioso e indetectável: a análise de impacto continua respondendo com confiança total sobre um grafo obsoleto |
| F-67 | cli | 🟢 | a recarga completa por invocação permanece; remover o repositório não mudou o perfil de consumo |
| F-68 | model | 🔴 | A deduplicação de donos exige que `Owner` seja hasheável e comparável por valor; o contrato não declara isso. Sem essa propriedade o mesmo dono aparece repetido no resultado e o CRITÉRIO DE ACERTO do projeto falha diretamente |
| F-69 | catalog-mapper | 🟢 | Montar catálogo, grafo e rodar validação numa passada pura não altera a complexidade O(V+E). Registro de que a fusão não custou desempenho |
| F-70 | catalog-mapper | 🟡 | Retorno em união `LoadedCatalog \ | list[Violation]` sem discriminante obriga `isinstance` no chamador, e o contrato não define como distinguir os dois casos |
| F-71 | catalog | 🟡 | Nenhum ator nem passo está definido para criar o domínio de um dataset que já é consumido mas ainda não tem dono — o processo pressupõe que todo domínio já existe |
| F-72 | model | 🟡 | A fusão de `errors` resolveu ARC-02 mas ENGORDOU M-01, que já era o módulo mais atacado da Iteração 1 (10 achados por 7 lentes). Agora acumula entidades, value objects, tipos de erro e tipos de resultado |
| F-73 | catalog-mapper | 🔴 | Acumula cinco responsabilidades: mapear dicionários, inverter a aresta, montar o catálogo, construir o grafo, chamar a validação e construir `LoadedCatalog`. A sobrecarga que motivou a remoção de `catalog-repository` MIGROU para cá em vez de desaparecer — a V(2) moveu a concentração, não a eliminou |
| F-74 | catalog-mapper | 🟢 | O nome do módulo (`mapper`) não descreve mais o que ele faz: mapeia, monta, valida e constrói. Nome herdado da V(1), mantido para preservar rastreabilidade entre fases |
| F-75 | model | 🟢 | a fusão de `errors` não alterou o tratamento de dado pessoal |
