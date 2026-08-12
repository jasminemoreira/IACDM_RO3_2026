# Matriz de cobertura — achados da crítica adversarial

Uma linha por ACHADO. Não é uma grade de severidades: este formato é o que permite
distinguir duas lentes achando o MESMO defeito (sobreposição) de duas lentes achando
defeitos DIFERENTES no mesmo módulo (ortogonalidade).

Cada rodada do laço Fase 2 ↔ Fase 3 ACRESCENTA uma seção `## Iteração N — V(N)`.
Nunca sobrescrever a anterior.

## Iteração 1 — V(1)

Lentes universais aplicadas: todas as 7.
Lentes condicionais ativadas: 9 de 12 (Resilience, UI/UX, Sustainability / Proportionality,
Process / Workflow, Governance / Accountability, Control Engineering, Game Theory,
Linguistics / Grammar, Mechanical Engineering).

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASM-01 | catalog-mapper | Assumptions | 🔴 | A10 (nomes sem ponto) está declarada mas nenhum módulo recebeu a responsabilidade de IMPÔ-LA. Um domínio nomeado `vendas.br` gera identidade `vendas.br.pedidos`, que `DatasetId.parse` lê como domínio `vendas` + dataset `br.pedidos` → resolve o dono ERRADO, silenciosamente |
| ASM-02 | catalog-repository | Assumptions | 🟡 | Assume que o diretório contém APENAS arquivos de catálogo. Um `README.md`, `.gitkeep` ou `.yaml.bak` no mesmo diretório tem comportamento indefinido: ignorar, falhar ou tentar parsear |
| ASM-03 | catalog | Assumptions | 🟡 | Assume que a sobrescrita de dono é TOTAL. Não está dito se um dataset pode sobrescrever só o contato mantendo o nome herdado — as duas leituras são defensáveis e produzem resultados diferentes no UC-5 |
| ASM-04 | query-service | Assumptions | 🟢 | A6 (impact exclui o próprio X) está declarada na arquitetura mas não aparece no nome nem na assinatura do contrato; quem implementar M-06 sem ler as assunções erra por um elemento |
| ASM-05 | model | Assumptions | 🟡 | Assume que `contato` em texto livre é acionável. A promessa do produto é "quem avisar"; nada no modelo garante que a string sirva para avisar alguém |
| ARC-01 | catalog-repository | Architectural | 🟡 | Acumula quatro responsabilidades (ler, mapear, construir grafo, validar). É o único módulo que não pode ser testado sem os outros quatro — viola SRP e é o ponto onde o Hexagonal vaza |
| ARC-02 | errors | Architectural | 🔴 | `format_violations(list[Violation]) -> str` está declarado em DOIS módulos: errors (M-02) e formatters (M-10). Dois donos para o mesmo contrato — a Fase 5 não tem como saber onde implementar, e o Strategy de saída fica pela metade |
| ARC-03 | validation | Architectural | 🟡 | Depende de lineage-graph, que depende de NetworkX. Testar as invariantes isoladamente exige construir um DiGraph real — acoplamento indireto do núcleo a uma lib de terceiro |
| ARC-04 | cli | Architectural | 🟢 | `depends-on: todos` não é verificável. Nada no desenho impede a CLI de chamar query-service pulando catalog-repository, contornando a validação obrigatória (A8) |
| ARC-05 | model | Architectural | 🟡 | `RawDomainDoc` circula entre yaml-loader e catalog-mapper mas não está na lista de tipos de `model` — tipo órfão, sem módulo dono declarado |
| IMPL-01 | validation | Implementability | 🟡 | `validate() -> list[Violation]` não define a ORDEM das violações. A9 exige reportar todas de uma vez; ordem não-determinística torna a saída de erro impossível de asserir em teste |
| IMPL-02 | catalog-repository | Implementability | 🟡 | O contrato diz "levanta erro se inválido", mas não diz QUAL erro nem como ele transporta a lista de Violations até a CLI para formatação |
| IMPL-03 | formatters | Implementability | 🟢 | Não está especificado se `--json` também troca o formato da SAÍDA DE ERRO, nem qual código de saída acompanha cada caso |
| IMPL-04 | model | Implementability | 🟡 | `LoadedCatalog` aparece na interface de catalog-repository mas não consta entre os tipos de `model` — segundo tipo sem dono, junto de ASM/ARC-05 |
| IMPL-05 | model | Implementability | 🔴 | A deduplicação de donos exige que `Owner` seja hasheável e comparável por valor; o contrato não declara isso. Sem essa propriedade o mesmo dono aparece repetido no resultado e o CRITÉRIO DE ACERTO do projeto falha diretamente |
| SCI-01 | lineage-graph | Scientific | 🟢 | As referências depositadas (Kahn 1962, Tarjan 1976, CLRS §22.4) não serão consumidas por código algum, já que a decisão foi NetworkX. O critério "algoritmo com referência" passa a ser satisfeito por delegação à lib, não por citação no código |
| SCI-02 | lineage-graph | Scientific | 🟡 | A assunção A6 repousa na semântica de `networkx.descendants` (não inclui a origem), lida da documentação. Nenhum teste de caracterização fixa esse comportamento: se a lib mudar, o critério de acerto muda em silêncio |
| SEC-01 | yaml-loader | Security | 🔴 | Se o parsing usar `yaml.load` sem `SafeLoader`, o YAML permite instanciar objetos Python arbitrários — carregar um catálogo vindo de fora executa código. O módulo lê arquivos de um diretório passado por argumento, então o vetor é direto |
| SEC-02 | catalog-repository | Security | 🟡 | O caminho do diretório vem por argumento e nada restringe a travessia: symlink apontando para fora, ou caminho absoluto arbitrário, fazem o carregador ler o que não deveria |
| SEC-03 | model | Security | 🟡 | Nome e contato de pessoas ficam em texto claro em repositório versionado; o histórico do git retém indefinidamente mesmo após remoção |
| SEC-04 | yaml-loader | Security | 🟢 | Sem limite declarado de tamanho de arquivo nem de profundidade de aninhamento — YAML com expansão de aliases (billion laughs) consome memória desproporcional |
| PERF-01 | catalog-repository | Performance | 🟡 | Recarrega, remapeia, reconstrói o grafo e revalida o catálogo INTEIRO a cada invocação, mesmo para consultar um único dataset. O custo é O(V+E) do catálogo por consulta, não da consulta |
| PERF-02 | validation | Performance | 🟢 | A detecção de ciclo roda em todo carregamento, inclusive no comando `validar` de um catálogo sem nenhuma aresta, onde o resultado é conhecido de antemão |
| REG-01 | model | Regulatory | 🟡 | duplica: SEC-03 — nome e e-mail corporativo são dado pessoal sob LGPD/GDPR; nenhum módulo tem rastreabilidade a base legal, finalidade ou política de retenção |
| REG-02 | cli | Regulatory | 🟢 | Nenhum requisito normativo do domínio (DCAT, OpenLineage) é obrigatório para este produto e nenhum módulo reivindica conformidade. Registro explícito de ausência de requisito regulatório de catálogo |
| RES-01 | yaml-loader | Resilience | 🟡 | Arquivo YAML sintaticamente inválido: a exceção do PyYAML vaza para o usuário sem dizer qual arquivo nem qual domínio a produziu |
| RES-02 | catalog-repository | Resilience | 🟡 | Diretório inexistente, vazio de permissão, ou arquivo ilegível no meio do lote — nenhum desses caminhos está especificado |
| RES-03 | catalog-repository | Resilience | 🟢 | Diretório existente mas sem nenhum arquivo: catálogo vazio é resultado válido ou erro? As duas leituras são defensáveis e nada decide |
| UX-01 | formatters | UI/UX | 🔴 | A promessa do produto é "quem eu preciso avisar", mas o contrato de saída não especifica AGRUPAMENTO POR DONO. Uma lista plana de 40 datasets afetados obriga o engenheiro a fazer o agrupamento na cabeça — o produto entrega o dado e não a resposta |
| UX-02 | cli | UI/UX | 🟡 | Consultar dataset inexistente e consultar dataset folha são situações distintas ("não existe" vs "existe e não afeta ninguém") e nada garante mensagens distintas — confundi-las leva o engenheiro a concluir que a mudança é segura |
| UX-03 | formatters | UI/UX | 🟡 | Impacto vazio: a borda foi identificada na Fase 0, mas nenhum contrato diz o que se imprime. Saída silenciosa é indistinguível de falha do comando |
| UX-04 | cli | UI/UX | 🟡 | Subcomandos em português (`validar`, `impacto`, `procedencia`) com flag em inglês (`--json`) e campos YAML em português (`alimentado_por`) — a interface mistura idiomas sem regra declarada |
| UX-05 | yaml-loader | UI/UX | 🟢 | O dono de domínio escreve YAML à mão sem schema, autocomplete ou comando que gere um arquivo modelo; o primeiro contato com o formato é por tentativa e erro |
| SUS-01 | catalog-repository | Sustainability / Proportionality | 🟢 | duplica: PERF-01 — a 10× o custo por consulta continua barato em absoluto, mas cresce com o tamanho do catálogo em vez de com o tamanho da pergunta |
| SUS-02 | lineage-graph | Sustainability / Proportionality | 🟡 | Uma dependência inteira (NetworkX) é trazida para usar três funções sobre um grafo de dezenas de nós. O footprint da dependência é desproporcional à operação que ela executa |
| PROC-01 | cli | Process / Workflow | 🟡 | O fluxo termina em "aqui estão os donos". O passo de NOTIFICAR está fora do sistema e nada registra que ele ocorreu — o UC-2 não fecha, e o handoff entre engenheiro e dono fica sem confirmação |
| PROC-02 | catalog-repository | Process / Workflow | 🔴 | INV-5 (aresta pendente é erro) trava a adoção incremental: o domínio A não consegue commitar um arquivo válido declarando `alimentado_por: b.x` enquanto B não existir. Não há caminho de exceção definido, e o primeiro domínio a adotar o catálogo fica impedido de declarar suas dependências reais |
| PROC-03 | catalog | Process / Workflow | 🟡 | Nenhum ator nem passo está definido para criar o domínio de um dataset que já é consumido mas ainda não tem dono — o processo pressupõe que todo domínio já existe |
| PROC-04 | cli | Process / Workflow | 🟢 | Nada no desenho garante que a validação rode no CI; a garantia de catálogo válido depende inteiramente de disciplina humana |
| GOV-01 | catalog | Governance / Accountability | 🟡 | O dono é atribuído mas nada no modelo registra QUEM fez a atribuição e QUANDO. A autoria existe só no histórico do git, fora do artefato que o sistema lê |
| GOV-02 | catalog-mapper | Governance / Accountability | 🟡 | Como a aresta cross-domínio é declarada pelo consumidor, o PRODUTOR passa a figurar na análise de impacto de terceiros sem ter consentido nem tomado ciência. Atribuição de responsabilidade sem conhecimento do atribuído |
| GOV-03 | model | Governance / Accountability | 🔴 | `Owner` não tem identidade estável: é `{nome, contato}` por valor. A mesma pessoa escrita de duas formas em dois domínios (`Maria Silva` / `maria silva`, ou dois e-mails) vira DOIS donos, e a deduplicação exigida pelo critério de acerto falha |
| CTRL-01 | catalog-repository | Control Engineering | 🔴 | O catálogo é um modelo declarado de um mundo real (pipelines) que muda sem avisar o sistema, e NENHUM módulo gera sinal de erro quando a declaração diverge da realidade. O drift é silencioso e indetectável: a análise de impacto continua respondendo com confiança total sobre um grafo obsoleto |
| CTRL-02 | validation | Control Engineering | 🟢 | A validação regula a consistência INTERNA do catálogo (invariantes entre declarações), nunca a externa. Registro explícito de onde termina o laço de controle |
| GAME-01 | catalog-mapper | Game Theory | 🔴 | O valor da análise de impacto do produtor depende inteiramente da diligência dos CONSUMIDORES em declarar `alimentado_por`. Quem omite não paga custo algum — apenas deixa de receber aviso — enquanto o custo da omissão recai sobre o produtor, que decide mudar com grafo incompleto. O desenho assume cooperação onde o incentivo aponta para omissão |
| GAME-02 | catalog | Game Theory | 🟡 | Um dono pode declarar contato genérico (`dados@empresa.com`) para não ser pessoalmente notificado: satisfaz a validação, esvazia o propósito. Nada no modelo distingue contato acionável de contato de fachada |
| LING-01 | catalog-mapper | Linguistics / Grammar | 🔴 | `alimentado_por` é declarado na direção INVERSA à aresta do grafo. Duas implementações corretas do contrato escrito podem tomar direções opostas e ambas parecerem certas — impacto e procedência trocados produzem resultado plausível e silenciosamente errado |
| LING-02 | model | Linguistics / Grammar | 🟡 | "dono" nomeia dois conceitos: o declarado no domínio e o efetivo resolvido após sobrescrita. `resolve_owner` devolve o efetivo, mas nenhum termo distingue os dois |
| LING-03 | formatters | Linguistics / Grammar | 🟡 | "impacto" nomeia três coisas: o subcomando, o conjunto de datasets afetados e o resultado já com donos. Três referentes, um termo |
| LING-04 | validation | Linguistics / Grammar | 🟢 | `Violation` não distingue erro de FORMA (YAML malformado, campo faltando) de violação de INVARIANTE (ciclo, órfão) — dois níveis de falha sob um único tipo |
| MEC-01 | yaml-loader | Mechanical Engineering | 🟡 | Nenhuma tolerância declarada para campo desconhecido no YAML. Rejeitar quebra arquivos quando o formato evoluir; ignorar em silêncio esconde erro de digitação (`alimentado_pro:` passa despercebido e a aresta some). O contrato não escolhe |
| MEC-02 | lineage-graph | Mechanical Engineering | 🟡 | Nenhuma versão mínima de NetworkX nem de PyYAML declarada. Sem pin, a build não é reprodutível e a semântica de `descendants` de que A6 depende fica à mercê da versão instalada |
| MEC-03 | model | Mechanical Engineering | 🟢 | O formato YAML não tem campo de versão — não existe caminho de evolução do contrato de declaração sem quebrar os catálogos já escritos |

### Totais

| Severidade | Quantidade |
|---|---|
| 🔴 Crítico | 10 |
| 🟡 Importante | 29 |
| 🟢 Sugestão | 14 |
| **Total** | **53** |

Achados marcados `duplica:` — 2 (REG-01 duplica SEC-03; SUS-01 duplica PERF-01).
Contribuição exclusiva: 51 defeitos distintos.

---

## Iteração 2 — V(2)

Lentes universais aplicadas: todas as 7.
Lentes condicionais ativadas: as mesmas 9 da Iteração 1, RE-EXAMINADAS contra V(2) — nenhum
sinal do projeto mudou com a remoção de `errors` e `catalog-repository`.

Alvo desta rodada: a V(2) e, em particular, se a simplificação criou defeito novo.
`errors` e `catalog-repository` não aparecem — não existem mais.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ARC-06 | catalog-mapper | Architectural | 🔴 | Acumula cinco responsabilidades: mapear dicionários, inverter a aresta, montar o catálogo, construir o grafo, chamar a validação e construir `LoadedCatalog`. A sobrecarga que motivou a remoção de `catalog-repository` MIGROU para cá em vez de desaparecer — a V(2) moveu a concentração, não a eliminou |
| IMPL-06 | model | Implementability | 🔴 | "LoadedCatalog só é construível por catalog-mapper" é CONVENÇÃO, não garantia: Python não tem construtor privado. Sem mecanismo concreto (módulo privado com factory, token de construção, ou tipo interno encapsulado), ARC-04 da Iteração 1 não foi resolvido — foi redocumentado com outra palavra |
| ARC-07 | model | Architectural | 🟡 | A fusão de `errors` resolveu ARC-02 mas ENGORDOU M-01, que já era o módulo mais atacado da Iteração 1 (10 achados por 7 lentes). Agora acumula entidades, value objects, tipos de erro e tipos de resultado |
| ARC-08 | cli | Architectural | 🟡 | `cli` absorveu o wiring do repositório removido e segue dependendo de todos os módulos: passou a ser o único ponto do sistema onde um erro de composição não é detectável por tipo |
| GOV-04 | model | Governance / Accountability | 🟡 | Identidade de `Owner` por contato normalizado COLAPSA pessoas distintas que compartilham caixa (`dados@empresa.com` vira um dono só, com nome escolhido arbitrariamente entre os dois). É o defeito inverso de GOV-03, introduzido pela correção de GOV-03 |
| LING-05 | yaml-loader | Linguistics / Grammar | 🟡 | `load_files -> (list[RawDomainDoc], list[Violation])` não diz o que significa devolver docs PARCIAIS junto de violações: o chamador prossegue com o que veio ou aborta? Duas implementações corretas do contrato divergem |
| IMPL-07 | catalog-mapper | Implementability | 🟡 | Retorno em união `LoadedCatalog \| list[Violation]` sem discriminante obriga `isinstance` no chamador, e o contrato não define como distinguir os dois casos |
| IMPL-08 | validation | Implementability | 🟡 | A ordem determinística definida (domínio em ordem lexicográfica, depois ordem de declaração) NÃO cobre violações sem domínio — erro de parse de um arquivo que sequer chegou a ter o campo `dominio` lido |
| RES-04 | yaml-loader | Resilience | 🟡 | Arquivo ilegível por permissão não tem linha nem conteúdo para preencher a `Violation` com arquivo e linha que RES-01 exige; falta a forma degradada do contrato |
| UX-06 | formatters | UI/UX | 🟡 | A ressalva "resultado é limite inferior" (exigida pela arbitragem de GAME-01) não tem lugar definido: repetida em toda saída vira ruído, e em `--json` não se sabe se é campo, comentário ou ausente |
| ASM-06 | query-service | Assumptions | 🟡 | A6 passa a ser "fixada por teste de caracterização na Fase 6", mas nada na V(2) impede a Fase 5 de implementar sobre `descendants` antes desse teste existir — a garantia é cronológica, não estrutural |
| GOV-05 | formatters | Governance / Accountability | 🟢 | A ressalva de limite inferior é textual; em `--json` um consumidor programático a ignora sem custo algum |
| LING-06 | catalog-mapper | Linguistics / Grammar | 🟢 | O nome do módulo (`mapper`) não descreve mais o que ele faz: mapeia, monta, valida e constrói. Nome herdado da V(1), mantido para preservar rastreabilidade entre fases |
| SEC-05 | model | Security | 🟢 | Normalizar contato para minúsculas pode colidir endereços distintos: a RFC 5321 permite local-part sensível a maiúsculas, ainda que a prática dominante não use |
| GAME-03 | formatters | Game Theory | 🟢 | Agrupar por dono torna visível quem tem mais dependentes, criando incentivo a subdeclarar para "parecer menos crítico" — o agrupamento que resolve UX-01 cria pressão nova |
| MEC-04 | model | Mechanical Engineering | 🟢 | `model` cresceu absorvendo `errors` e continua sem versão de contrato: a superfície que precisa evoluir sem quebrar aumentou |
| PERF-04 | catalog-mapper | Performance | 🟢 | Montar catálogo, grafo e rodar validação numa passada pura não altera a complexidade O(V+E). Registro de que a fusão não custou desempenho |
| SUS-03 | cli | Sustainability / Proportionality | 🟢 | duplica: PERF-01 — a recarga completa por invocação permanece; remover o repositório não mudou o perfil de consumo |
| CTRL-03 | catalog-mapper | Control Engineering | 🟢 | A V(2) não alterou o laço de controle: continua sem sinal de divergência entre catálogo e realidade — coerente com a limitação aceita em CTRL-01 |
| PROC-05 | cli | Process / Workflow | 🟢 | A adoção big-bang aceita em PROC-02 não tem passo de processo definindo QUEM coordena a entrada simultânea de todos os domínios |
| SCI-03 | lineage-graph | Scientific | 🟢 | duplica: SCI-01 — nenhum algoritmo novo foi introduzido pela V(2); as referências permanecem satisfeitas por delegação ao NetworkX |
| REG-03 | model | Regulatory | 🟢 | duplica: REG-01 — a fusão de `errors` não alterou o tratamento de dado pessoal |

### Totais — Iteração 2

| Severidade | Quantidade |
|---|---|
| 🔴 Crítico | 2 |
| 🟡 Importante | 9 |
| 🟢 Sugestão | 11 |
| **Total** | **22** |

Achados marcados `duplica:` — 3 (SUS-03 duplica PERF-01; SCI-03 duplica SCI-01; REG-03 duplica REG-01).
Contribuição exclusiva: 19 defeitos distintos.

Comparação entre rodadas: 53 → 22 achados; 10 → 2 críticos. Sinal de convergência.
