# Arquitetura — V(1)

Projeto: **T31 — motor de regras de preço com faixas, histórico e explicação da
decisão, substituindo uma tabela legada**.
Fase 1, iteração 1. Validado pelo operador (Human-AV) em 2026-08-12.

## Decisões estruturantes

| Dimensão | Escolha |
|---|---|
| Stack | Python 3 + FastAPI + SQLite + Jinja2 (`decimal`, `csv`, `sqlite3` da stdlib) |
| Padrão arquitetural | **Hexagonal (Ports & Adapters)** |
| Princípios | KISS + YAGNI · DDD tático · SOLID (ênfase SRP e DIP) |
| Concorrência | Single-threaded |
| GoF adotados | **Strategy** (efeito da regra) · **Facade** (serviço de aplicação) |
| GoF rejeitado | Chain of Responsibility — o validador é uma lista de funções de checagem (KISS) |
| Fowler — domínio | **Domain Model** |
| Fowler — dados | **Repository + Data Mapper** |
| Armazenamento | SQLite único; publicação atômica em transação |

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

# V(2) — resposta unificada à crítica da Iteração 1

Fase 3, iteração 1. Responde aos 60 achados de `specs/design/coverage-matrix.md`
com visão unificada: 8 respostas integradas, não 60 correções isoladas.

**Princípio que dita a resposta:** a análise de concentração mostrou que 60% dos
achados estão nos quatro módulos de **fronteira**, e apenas 7 no núcleo
algorítmico — que é justamente a parte que recebeu especificação normativa na
Fase 0. As falhas estão onde faltou spec, não onde o problema é difícil. Logo a
correção é **especificar fronteiras**, não redesenhar módulos. Saldo de peças:
`prova-paridade` some (funde em `importador-csv`), `ui-editor-regras` nasce —
12 módulos antes, 12 depois, com o motor **desacoplado da persistência**.

## V(2) — Módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dinheiro | Valor monetário decimal exato (I-5); parsing BR tolerante (moeda, milhar, espaço não-quebrável, menos unicode); half-up 2 casas só no resultado final | `de_texto(s) -> Dinheiro \| ErroFormato`, `multiplicar(qtd)`, `aplicar_pct(pct)`, `__eq__` | — |
| M-02 | modelo-dominio | Entidades e VOs com invariantes. **Mudanças V(2):** `Veredito.casou:bool` REMOVIDO e substituído por `codigo: MotivoCodigo` + `detalhe` estruturado; `Produto` exige preço base no construtor; `VersaoDeRegras` ganha `autor` e `origem`; `Decisao` ganha `solicitante` | dataclasses imutáveis; `Efeito.aplicar(preco_base)`; `Faixa.contem(qtd)`; `Vigencia.contem(data)`; `Regra.avaliar(sku,qtd,data) -> MotivoCodigo` | dinheiro |
| M-03 | motor-precificacao | Selecionar candidatas, aplicar o efeito vencedor, montar trace exaustivo. **Mudança V(2):** recebe uma LISTA DE REGRAS e um `Produto` já resolvido — não conhece `VersaoDeRegras` persistida nem `sku` cru. Fica testável e utilizável sobre rascunho | `precificar(regras, produto, qtd, data) -> Decisao` | modelo-dominio, resolvedor-precedencia |
| M-04 | resolvedor-precedencia | Prioridade decrescente → especificidade → `EmpateInsoluvel` (I-6). Registra o código de derrota de cada perdedora | `resolver(candidatas) -> (vencedora, derrotas)` | modelo-dominio |
| M-05 | validador-coerencia | Checar rascunho antes da publicação. **Especificado em V(2):** a sobreposição é detectada **entre escopos comparáveis** — duas regras colidem quando escopo, faixa e vigência se interceptam E prioridade e especificidade empatam; lacuna é aviso com reconhecimento registrado | `validar(rascunho, produtos) -> Relatorio{erros[], avisos[]}` | modelo-dominio |
| M-06 | explicador | Renderizar frase pt-BR **a partir dos códigos** do trace. **Mudança V(2):** não reinterpreta semântica de faixa/vigência — só traduz código+detalhe em texto, o que apaga a lógica duplicada com o motor | `explicar(decisao) -> str` | modelo-dominio |
| M-07 | repositorio-sqlite | Data Mapper das portas; publicação atômica; **V(2):** parâmetros ligados obrigatórios, índices em `decisao(data_pedido)` e `decisao(sku)`, falha de I/O traduzida em erro acionável | `publicar(rascunho, autor, origem) -> Resultado`, `vigente_em(data)`, `versao(n)`, `salvar_rascunho`, `rascunho_atual`, `registrar(decisao)`, `listar`, `obter` | modelo-dominio |
| M-08 | importador-csv | Ida **e volta** do formato legado. Importar (normalizar, rejeitar com motivo, limites de 5 MB / 20.000 linhas), provar paridade sobre o rascunho, e **exportar** rascunho/versão de volta ao CSV legado. *Nome mantido de V(1) para preservar a rastreabilidade dos 9 achados que o nomeiam* | `importar(bytes) -> Resultado{rascunho, rejeitadas, produtos}`, `verificar_paridade(linhas, rascunho, produtos) -> Relatorio`, `exportar(regras, produtos) -> bytes` | modelo-dominio, dinheiro, motor-precificacao |
| M-09 | servico-aplicacao | **Facade + fronteira única de validação de entrada** (o núcleo declara pré-condições e assume entrada válida). Mantém a versão vigente em cache, invalidado na publicação. Ciclo de publicação com estados fechados | `precificar(sku, qtd, data, solicitante)`, `importar(bytes, substituir:bool)`, `validar_rascunho()`, `publicar(autor)`, `republicar(n, autor)`, `exportar()`, `historico(filtros)`, `recalcular(id)` | motor-precificacao, validador-coerencia, explicador, repositorio-sqlite, importador-csv |
| M-10 | api-http | Adapter REST. **V(2):** bind obrigatório em `127.0.0.1`, limite de payload, códigos de erro distintos para entrada inválida / SKU desconhecido / nenhuma versão publicada / empate insolúvel; `preco_unitario` serializado como **decimal em string ISO** (`"21.90"`), com a forma pt-BR num campo separado de apresentação | rotas REST + `GET /saude` (versão vigente, latência p95) | servico-aplicacao |
| M-11 | ui-web | **3 telas**: simulador (trace resumido por padrão, exaustivo sob demanda), importação (rejeitadas, paridade, validação, exportar) e histórico (registrado × recalculado lado a lado, rotulados). Autoescape do Jinja2 explícito | rotas `/simular`, `/importar`, `/historico` | servico-aplicacao |
| M-12 | ui-editor-regras | **1 tela**, separada por ser onde mora toda a complexidade: grade de regras com **edição em massa e colagem vinda da planilha**, rascunho, resultado da validação com correção no local, e publicar | rota `/regras` | servico-aplicacao |

**Removido:** `prova-paridade` — a paridade passou a operar sobre o rascunho
(V(2) do motor) e virou uma responsabilidade de `importador-csv`; manter um
módulo para um laço de ~40 linhas era peça sem fronteira própria.
**Adicionado:** `ui-editor-regras` — a tela de regras concentrava UX-01 e IMP-01
e não cabia junto das outras três.

## Achados resolvidos, por id

| id | como foi resolvido em V(2) |
|---|---|
| ASS-01 🔴 | Validação de quantidade acontece **só** em `servico-aplicacao`; o núcleo declara a pré-condição `qtd ≥ 1` |
| ASS-02 🔴 | `motor-precificacao` recebe `Produto` resolvido; SKU desconhecido vira erro de fronteira e nunca alcança o motor |
| ASS-03 🟡 | `vigente_em()=None` vira erro de estado "nenhuma versão publicada", com código próprio na API — distinto de I-2 |
| ASS-04 🟡 | Gramática do CSV declarada: encoding detectado (UTF-8/BOM/latin-1), delimitador inferido entre `;` e `,`, cabeçalho casado sem acento e sem caixa |
| ASS-05 🟡 | `Produto` exige preço base no construtor; produto sem preço base não é construível |
| ASS-06 🟢 | `EmpateInsoluvel` é traduzido em erro pela Facade e nunca chega ao `explicador` |
| ARQ-01 🟡 | Paridade opera sobre **rascunho** — a circularidade validar↔publicar↔paridade deixa de existir |
| ARQ-02 🟡 | `servico-aplicacao` perde `prova-paridade` das dependências (5, não 6) e ganha responsabilidade coesa: fronteira de validação |
| ARQ-03 🟢 | Facade expõe as consultas de apresentação que a UI precisa (`historico(filtros)`, `rascunho_atual`) — sem atalho para o repositório |
| ARQ-04 🟡 | `explicador` renderiza a partir de códigos; a interpretação de faixa/vigência existe em um só lugar |
| IMP-01 🟡 | UI dividida em `ui-web` (3 telas) e `ui-editor-regras` (1 tela) |
| IMP-02 🟡 | Regra de colisão especificada: escopo × faixa × vigência se interceptam **e** prioridade e especificidade empatam |
| IMP-03 🟢 | Numeração de linha definida: 1-based contando o cabeçalho; linhas em branco são ignoradas sem consumir número |
| SCI-01 🟡 | **Aceito com justificativa** — decisão do operador na Fase 0; a limitação está declarada em `specs/references/fundamentos.md` |
| SCI-02 🟢 | **Aceito** — half-up 2 casas é a convenção do domínio; nenhum resultado depende de norma citável |
| SCI-03 🟡 | A analogia com DMN `PRIORITY` é **rebaixada a inspiração declarada**, não conformidade; o algoritmo normativo do projeto é o de `specs/domain/glossario.md` |
| SEC-01 🔴 | Bind em `127.0.0.1` é restrição do módulo `api-http`, não configuração |
| SEC-02 🔴 | Limite de 5 MB / 20.000 linhas na importação |
| SEC-03 🟡 | Autoescape do Jinja2 declarado explicitamente; nenhum campo vindo do CSV é renderizado sem escape |
| SEC-04 🟡 | Parâmetros ligados obrigatórios no contrato de `repositorio-sqlite` |
| SEC-05 🟢 | Limite de payload cobre o vetor; rate limit **aceito como ausente** (local, single-user) |
| PERF-01 🟡 | Cache da versão vigente em `servico-aplicacao`, invalidado na publicação |
| PERF-02 🟡 | Resolvido junto de PERF-01 (mesmo defeito) |
| PERF-03 🟢 | Índices em `decisao(data_pedido)` e `decisao(sku)` |
| PERF-04 🟢 | Custo O(n²) da validação declarado e limitado à publicação (não ao caminho quente) |
| REG-01 🟡 | **Aceito com registro**: nenhum requisito normativo foi levantado na Fase 0; fica documentado que guarda fiscal e CDC não foram mapeados — o operador decide se isso volta como escopo num v2 |
| REG-02 🟢 | Retenção infinita é decisão registrada do operador (ver SUS-01), não omissão |
| RES-01 🔴 | `publicar()` devolve resultado explícito; falha de I/O vira mensagem acionável, nunca stack trace |
| RES-02 🟡 | **Decisão do operador:** sem registro, sem preço — a requisição falha. Coerente com I-7 |
| RES-03 🟡 | Resolvido junto de ASS-04 (mesmo defeito) |
| RES-04 🟢 | Tela de importação com estado de progresso e desabilitação do botão durante o envio |
| UX-01 🔴 | `ui-editor-regras` com grade, edição em massa e colagem vinda da planilha — ataca o único critério em que o incumbente ganha |
| UX-02 🟡 | Correção no local: erros de validação e linhas rejeitadas são editáveis na própria grade, sem voltar à planilha |
| UX-03 🟡 | Histórico exibe registrado × recalculado **lado a lado, rotulados**, não como nota textual |
| UX-04 🟢 | Rótulos associados, navegação por teclado e contraste declarados como requisito das 4 telas |
| UX-05 🟡 | Trace resumido por padrão (as que casaram + as N mais próximas), exaustivo sob demanda — Miller aplicado de fato |
| MIG-01 🔴 | **Decisão do operador:** `exportar()` gera CSV no formato legado; rollback existe |
| MIG-02 🟡 | A tela de importação declara explicitamente que a planilha está aposentada a partir da publicação |
| MIG-03 🟡 | Reimportar sobre rascunho editado exige `substituir=true` explícito |
| MIG-04 🟢 | Linhas rejeitadas ficam no relatório persistido junto à versão |
| SUS-01 🟡 | **Decisão do operador:** trace completo, sem expurgo — o trace é a prova, podar destrói o que o produto existe para preservar. Tamanho medido na Fase 6 |
| SUS-02 🟢 | **Aceito**: cópia de regras por publicação é proporcional e o volume é medido |
| PRO-01 🔴 | Ao publicar, o rascunho vira **cópia da versão publicada** — estado órfão eliminado por definição |
| PRO-02 🟡 | Importar sobre rascunho editado exige confirmação (`substituir=true`) |
| PRO-03 🟡 | `republicar(n, autor)` cria nova versão com o conteúdo de N — reverte sem violar I-4 |
| PRO-04 🟢 | Publicar com avisos exige reconhecimento explícito, registrado na versão |
| GOV-01 🔴 | `VersaoDeRegras.autor` obrigatório — identidade **declarada, não autenticada**, e nomeada como tal |
| GOV-02 🟡 | `Decisao.solicitante` informado pelo chamador |
| GOV-03 🟡 | `VersaoDeRegras.origem` guarda nome do arquivo, sha256, instante e relatório de importação |
| GOV-04 🟢 | **Aceito**: single-user; o esquema reserva `autor` como o campo por onde a atribuição cresce |
| OBS-01 🟡 | Logging estruturado em stdout nas operações de fronteira (importar, publicar, falha de I/O) |
| OBS-02 🟡 | Latência medida por chamada e exposta em `GET /saude` |
| OBS-03 🟢 | `GET /saude` devolve versão vigente e latência |
| LIN-01 🔴 | `MotivoCodigo` enumerado + `detalhe` estruturado; a prosa é derivada. CS-2 vira verificável por teste |
| LIN-02 🟡 | `casou: bool` **deletado** — a ambiguidade some com o campo |
| LIN-03 🟡 | Cabeçalho casado sem acento e sem caixa, ordem de colunas irrelevante, delimitador inferido |
| LIN-04 🟢 | `preco_unitario` decimal em string ISO (`"21.90"`); a forma pt-BR vai em campo separado de apresentação |
| MEC-01 🟡 | Tolerância declarada sobre o **unitário**; o total é derivado e nunca comparado à parte |
| MEC-02 🟡 | Normalização por princípio: remover tudo que não é dígito/sinal decimal, inferir separador pelo padrão — não por lista de casos |
| MEC-03 🟢 | Versões fixadas: Python ≥ 3.11, FastAPI/Jinja2/uvicorn com faixa declarada |

## Premissas — mudanças em V(2)

- **A-04** (endurecida na Fase 1): mantida — o motor nunca lê o relógio.
- **A-14 (nova):** a identidade do autor é **declarada, não autenticada**. O
  sistema registra quem disse ser, não quem é. Explicitar isso é o que impede
  que o campo `autor` seja lido como garantia de autenticidade.
- **A-15 (nova):** o registro da decisão é parte da operação de precificar. Se o
  registro falha, a operação falha — não existe preço entregue e não auditado.
- **A-16 (nova):** a planilha legada está **aposentada** a partir da primeira
  publicação. A partir daí a fonte de verdade é o motor, e a volta ao legado se
  faz por `exportar()`.

## Escopo negativo — alterações

Removido do escopo negativo por decisão do operador: nada.
**Ampliação declarada:** `exportar()` para o formato legado, aprovada pelo
operador em resposta a MIG-01 (rollback). Registrada como ampliação consciente,
não como escopo silencioso.

---

# V(3) — resposta à crítica da Iteração 2

Fase 3, iteração 2. *(O contador do motor chama esta revisão de V(4); a matriz
de cobertura registra a equivalência. As seções deste documento são revisões de
desenho; o contador do motor conta transições de estado.)*

**Diretriz, extraída do dado da própria rodada:** 14 dos 22 achados caíram nos
dois módulos que V(2) mais alterou, e 7 achados foram **iatrogênicos** — gerados
pelas correções de V(2). Mas `motor-precificacao` também mudou em V(2) e zerou.
A diferença é o tipo de mudança: ele **perdeu** uma dependência, enquanto
`importador-csv` **ganhou** três responsabilidades. **V(3) subtrai.**

## Respostas

| # | Resposta | Achados | Natureza |
|---|---|---|---|
| **W1** | **Cache por número de versão, sem invalidação.** O erro de CTL-01 é a chave: cachear "a versão vigente" é cachear algo que depende da data. V(3) cacheia `numero → VersaoDeRegras`, e versões publicadas são **imutáveis por I-4** — logo o cache **nunca precisa ser invalidado**. A resolução data→número é um índice pequeno, ao qual publicar só faz *append*. O problema de invalidação some junto com a invalidação | CTL-01🔴 CTL-02🟡 RES-05🟢 | **subtrai** um mecanismo inteiro |
| **W2** | **A paridade sai de `importador-csv` e vai para `servico-aplicacao`.** O importador volta a ser parsing e serialização puros — testável sem o motor. A Facade, que já depende dos dois, orquestra importar→paridade | ARQ-05🟡 CTL-03🟢 | **subtrai** uma dependência |
| **W3** | **Índice por escopo no motor.** As regras passam a ser indexadas por SKU + a lista de regras `*`. O matching examina ~10 regras, não 1.000. Isso resolve o custo de PERF-05 sem tornar a paridade assíncrona, e o limite de importação cai de 20.000 para **2.000 linhas** — coerente com a escala declarada na Fase 0 (~1.000 regras), em vez de um número de segurança arbitrário que contradizia a própria escala | PERF-05🟡 | **subtrai** o conflito entre dois consertos |
| **W4** | **Formato de exportação estendido, com o legado como caso degenerado.** Um único formato CSV com colunas opcionais (`escopo`, `prioridade`, `vigencia_inicio`, `vigencia_fim`, `tipo_efeito`); ausentes, valem os *defaults* do legado. O ciclo importar→exportar→importar vira **idempotente** e o rollback restaura o estado real do motor. Células iniciadas por `=`, `+`, `-`, `@` recebem prefixo `'` na exportação | ASS-08🔴 MIG-05🟡 SEC-06🟡 | **subtrai** um formato (dois viram um) |
| **W5** | **`Trace.resultado` em vez de um sétimo `MotivoCodigo`.** "Nenhuma regra casou" não é veredito de regra nenhuma — é resultado do trace. `Trace` ganha `resultado: APLICOU_REGRA \| PRECO_BASE`; `MotivoCodigo` continua com 6 valores para vereditos de regra; `EmpateInsoluvel` permanece exceção, como deve ser | LIN-05🟡 | **separa** dois conceitos misturados |
| **W6** | **Regra monetária determinística, não inferência.** Havendo vírgula, ela é o separador decimal e o ponto é milhar. Não havendo vírgula, o ponto é decimal **apenas se seguido de exatamente 1 ou 2 dígitos**; caso contrário é milhar. `1.299` → 1299. A regra é declarada e testável, e entra como caso-armadilha novo | MEC-04🟡 | **substitui** inferência por regra |
| **W7** | **`republicar()` não toca o rascunho** — só `publicar()` o substitui pela cópia da versão publicada. `origem` ganha `tipo: IMPORTACAO \| EDICAO \| REVERSAO_DE(n)`, registrando a **intenção** | PRO-05🟡 GOV-05🟡 | refina regra existente |
| **W8** | **I-7 corrigida por subtração de alegação.** O log prova o que o motor **respondeu**, não o que foi **cobrado** — cobrar é ato do sistema consumidor. A afirmação forte era um exagero que ASS-07 expôs; retirá-la torna o registro honesto sem custar linha de código | ASS-07🟡 | **subtrai** uma alegação falsa |
| **W9** | **Dívida de spec de `ui-editor-regras` paga agora.** O achado era a ausência de especificação, então a correção é escrevê-la: colunas da grade, semântica da colagem (TSV do *clipboard*), validação por célula, salvar rascunho — em `specs/design/`. Declarado também o **modo degradado** (formulário por regra + área de colagem em massa) caso a grade estoure, para que a degradação seja escolha registrada e não descoberta. Base de template e CSS pertencem a `ui-web`, importados em uma direção só | IMP-04🟡 ARQ-06🟢 | paga dívida, não adiciona peça |
| **W10** | **"N mais próximas" definido:** as regras do mesmo SKU com faixa imediatamente inferior e imediatamente superior à quantidade pedida, mais **todas** as regras `*` avaliadas; a tela declara "mostrando X de Y". O campo ISO é **normativo**; a forma pt-BR é derivada e só de apresentação | UX-06🟡 LIN-06🟢 | especifica critério |

**Aceitos com justificativa:** SCI-04 🟢 (`MotivoCodigo` é enumeração autoral e
está declarada como tal — não existe taxonomia padronizada de vereditos em
motores de regras), REG-03 🟢 (duplica REG-01, já aceito), SUS-03 🟢 (com o
limite reduzido a 2.000 linhas em W3, o relatório de importação volta a ser
proporcional ao volume de regras), OBS-04 🟢 → resolvido de graça: `GET /saude`
passa a expor os números de versão em cache.

## V(3) — Módulos

Sem módulos adicionados nem removidos. **12 módulos**, os mesmos nomes de V(2).

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | dinheiro | Valor decimal exato; **regra determinística** de separador (W6); half-up 2 casas no resultado final | `de_texto(s) -> Dinheiro \| ErroFormato`, `multiplicar(qtd)`, `aplicar_pct(pct)` | — |
| M-02 | modelo-dominio | Entidades e VOs. **V(3):** `Trace.resultado: APLICOU_REGRA \| PRECO_BASE`; `MotivoCodigo` permanece com 6 valores de veredito de regra | dataclasses imutáveis; `Efeito.aplicar`; `Faixa.contem`; `Vigencia.contem`; `Regra.avaliar -> MotivoCodigo` | dinheiro |
| M-03 | motor-precificacao | Selecionar candidatas e aplicar o vencedor. **V(3):** indexa as regras por escopo (SKU + lista `*`) internamente — avalia ~10 regras, não 1.000. Interface inalterada | `precificar(regras, produto, qtd, data) -> Decisao` | modelo-dominio, resolvedor-precedencia |
| M-04 | resolvedor-precedencia | Prioridade → especificidade → `EmpateInsoluvel` | `resolver(candidatas) -> (vencedora, derrotas)` | modelo-dominio |
| M-05 | validador-coerencia | Colisão = escopo × faixa × vigência se interceptam **e** prioridade e especificidade empatam; lacuna é aviso com reconhecimento | `validar(rascunho, produtos) -> Relatorio` | modelo-dominio |
| M-06 | explicador | Traduz código + detalhe em frase pt-BR; **V(3):** também traduz `Trace.resultado` | `explicar(decisao) -> str` | modelo-dominio |
| M-07 | repositorio-sqlite | Data Mapper; publicação atômica; parâmetros ligados; índices. **V(3):** `origem.tipo` registra IMPORTACAO / EDICAO / REVERSAO_DE(n) | `publicar(rascunho, autor, origem)`, `vigente_em(data)`, `versao(n)`, `salvar_rascunho`, `rascunho_atual`, `registrar`, `listar`, `obter` | modelo-dominio |
| M-08 | importador-csv | **V(3): parsing e serialização puros — a paridade saiu.** Importar (formato estendido ou legado, limite de 2.000 linhas) e exportar (formato estendido, com escape de fórmula). Testável sem o motor | `importar(bytes) -> Resultado`, `exportar(regras, produtos) -> bytes` | modelo-dominio, dinheiro |
| M-09 | servico-aplicacao | Facade + fronteira única de validação. **V(3):** cache `numero → VersaoDeRegras` **sem invalidação** (I-4 garante); orquestra a prova de paridade; `republicar` não toca o rascunho | `precificar`, `importar(bytes, substituir)`, `verificar_paridade`, `validar_rascunho`, `publicar(autor)`, `republicar(n, autor)`, `exportar`, `historico`, `recalcular` | motor-precificacao, validador-coerencia, explicador, repositorio-sqlite, importador-csv |
| M-10 | api-http | REST; bind `127.0.0.1`; limite de payload; códigos de erro distintos. **V(3):** campo ISO é **normativo**, pt-BR é derivado; `GET /saude` expõe versão vigente, latência e versões em cache | rotas REST + `GET /saude` | servico-aplicacao |
| M-11 | ui-web | 3 telas (simulador, importação, histórico). **V(3):** critério de "próximas" declarado; dona da base de template e CSS | `/simular`, `/importar`, `/historico` | servico-aplicacao |
| M-12 | ui-editor-regras | 1 tela: grade com edição em massa e colagem. **V(3):** spec escrita em `specs/design/`; modo degradado declarado | `/regras` | servico-aplicacao, ui-web (base visual) |

## Premissas — mudanças em V(3)

- **I-7 corrigida (W8):** o log prova o que o motor **respondeu**; cobrar é ato
  do sistema consumidor. A formulação anterior ("prova o que foi cobrado") era
  mais forte do que o sistema pode sustentar.
- **A-17 (nova):** versões publicadas são imutáveis (I-4), portanto cacheáveis
  por número **sem invalidação**. Se I-4 for algum dia relaxada, o cache passa a
  ser incorreto — a dependência entre as duas está declarada aqui de propósito.
- **A-18 (nova):** o limite de importação é 2.000 linhas, derivado da escala
  declarada na Fase 0 (~1.000 regras), não de um teto arbitrário de segurança.

---

# V(4) — resposta à crítica da Iteração 3

Fase 3, iteração 3. *(Contador do motor: V(6).)*

**Diretriz:** três rodadas confirmaram que **o módulo alterado numa rodada é o
que a rodada seguinte encontra** — `servico-aplicacao` liderou as três. V(4)
minimiza o que toca, e onde tocar seria oscilar, **aceita com justificativa**.

| # | Resposta | Achados |
|---|---|---|
| **X1** | **Cache LRU com teto de 8 versões.** Sem invalidação (I-4 mantém a corretude), mas com **expulsão** — a subtração de W1 tinha levado junto o mecanismo que tirava coisas do cache. 8 = a versão vigente + as poucas tocadas em recálculo histórico. O índice `data→número` também vive em memória, carregado no *start* e apendado na publicação, de modo que uma falha do SQLite não derruba precificação de versão já cacheada. `GET /saude` passa a expor **quanto** o cache ocupa, não só quais versões | ASS-09🟡 SUS-04🟢 RES-06🟢 OBS-05🟢 |
| **X2** | **Ordem de vigência pelo NÚMERO, não pelo relógio.** A versão guarda `vigente_desde: date` (data, não carimbo), e `vigente_em(D)` devolve a de **maior número** entre as com `vigente_desde ≤ D`. O número é sequencial por construção, logo imune a ajuste de relógio | CTL-04🟡 |
| **X3** | **O `'` de escape é removido na importação**, como parte da normalização — e entra no contrato e como caso-armadilha. Fecha a idempotência que o próprio escape havia furado | LIN-07🟡 |
| **X4** | **Gramática do formato fechada:** não existem "dois formatos". Existe **um** conjunto de colunas, algumas opcionais. O cabeçalho é casado por nome normalizado (sem acento, sem caixa, ordem irrelevante); coluna desconhecida é **ignorada e preservada** (é o caso de `Obs`); coluna ausente recebe o *default* legado | LIN-08🟡 |
| **X5** | **`ConjuntoDeRegras` — o índice nasce com o dado.** Objeto de valor em `modelo-dominio` que indexa por escopo **na construção** e expõe `regras_de(sku)`. Tanto uma `VersaoDeRegras` quanto um rascunho produzem um. O motor recebe o mesmo parâmetro conceitual de antes ("as regras"), agora tipado — continua sem saber de persistência, e **para de reconstruir o índice a cada chamada** | PERF-06🟡 |
| **X6** | **ARQ-07 aceito com justificativa, e a oscilação declarada.** A paridade saiu de `servico-aplicacao` em V(2) e voltou em V(3); movê-la outra vez seria oscilar entre duas casas igualmente defensáveis — que é sintoma, não conserto. **Critério de parada declarado:** as 9 operações da Facade são 9 delegações finas, não 9 algoritmos; **se qualquer operação passar a conter lógica além de orquestração, ela vira módulo.** O teste é objetivo e fica escrito | ARQ-07🟡 |
| **X7** | **MEC-05: parsear pela regra declarada, mas não em silêncio.** `2.500` continua sendo lido como 2500 conforme a regra determinística — e toda ocorrência de ponto seguido de exatamente 3 dígitos **sem vírgula no valor** entra no relatório de importação como **aviso de ambiguidade**, com linha e valor. A regra deixa de errar caladamente | MEC-05🟡 |
| **X8** | **UX-07: teto de 10 vereditos** por padrão (as faixas adjacentes + as regras `*` de maior prioridade), com "mostrando X de Y — ver todas". O critério deixa de ter um caso em que ele mesmo falha | UX-07🟡 |
| **X9** | **Invariante no tipo:** `Trace` valida na construção que `resultado == PRECO_BASE` ⟺ nenhum veredito é `VENCEU`. O invariante entre dois campos passa a viver no tipo que os contém (DDD), não na cabeça de quem implementa | IMP-05🟢 |
| **X10** | `origem` ganha `justificativa: str`, **obrigatória** quando `tipo = REVERSAO_DE(n)`. A auditoria passa a ter o porquê, não só o quê | GOV-06🟢 |

**Aceito:** SEC-07 🟢 — o formato estendido amplia a superfície de escrita, mas o
vetor é o mesmo *upload* já limitado a 2.000 linhas, num sistema single-user
local sem auth (A-08). Declarado, não ignorado.
**Pendente de decisão do operador:** PRO-06 🟡 — o modo degradado de
`ui-editor-regras` é redução de escopo pré-autorizada pela IA; a decisão é de
quem é dono do escopo (S5).

## V(4) — Módulos

Sem módulos adicionados nem removidos. **12 módulos**, mesmos nomes.
Alterações em relação a V(3), apenas onde há:

| id | module | alteração em V(4) |
|------|--------|-------------------|
| M-01 | dinheiro | Regra de separador inalterada; passa a **sinalizar ambiguidade** (`ponto + 3 dígitos, sem vírgula`) ao chamador, em vez de resolver calado (X7) |
| M-02 | modelo-dominio | **Novo VO `ConjuntoDeRegras`** — indexa por escopo na construção, expõe `regras_de(sku)` (X5); `Trace` valida o invariante `resultado ⟺ vereditos` na construção (X9); `VersaoDeRegras` ganha `vigente_desde: date` (X2) e `origem.justificativa` (X10) |
| M-03 | motor-precificacao | `precificar(conjunto, produto, qtd, data)` — mesmo parâmetro conceitual, agora tipado; **não reconstrói índice** (X5) |
| M-04 | resolvedor-precedencia | — |
| M-05 | validador-coerencia | — |
| M-06 | explicador | — |
| M-07 | repositorio-sqlite | `vigente_em(D)` = maior **número** entre `vigente_desde ≤ D` (X2); `justificativa` persistida (X10) |
| M-08 | importador-csv | Remove o `'` de escape na importação (X3); gramática de cabeçalho fechada, coluna desconhecida ignorada e preservada (X4); aviso de ambiguidade monetária no relatório (X7) |
| M-09 | servico-aplicacao | Cache **LRU com teto de 8**; índice `data→número` em memória (X1). **Fronteira inalterada** — e declarado o critério de parada: operação que ganhe lógica além de orquestração vira módulo (X6) |
| M-10 | api-http | `GET /saude` expõe o tamanho ocupado pelo cache (X1) |
| M-11 | ui-web | Teto de 10 vereditos no trace resumido, com "mostrando X de Y" (X8) |
| M-12 | ui-editor-regras | — *(modo degradado pendente de decisão do operador — PRO-06)* |

## Premissas — V(4)

- **A-19 (nova):** a ordem de vigência entre versões é dada pelo **número
  sequencial**, nunca pelo relógio. Substitui a premissa implícita de
  monotonicidade de carimbo que CTL-04 expôs.
- **A-20 (nova):** o cache comporta 8 versões. Acima disso, expulsa a menos
  usada. Correção não depende do teto (I-4 garante); só o consumo depende.

---

# V(5) — resposta à crítica da Iteração 4

Fase 3, iteração 4. *(Contador do motor: V(8).)*

**Diretriz:** metade dos achados da rodada foram iatrogênicos. Onde o conserto
anterior criou o problema, o conserto certo é **desfazer ou restringir**, não
empilhar mais um mecanismo.

| # | Resposta | Achados |
|---|---|---|
| **Y1** | **O teto de 8 vira parâmetro observável, não constante de fé.** Continua 8, mas `GET /saude` passa a expor **taxa de acerto** do cache além do tamanho — e fica declarado o critério de revisão: taxa abaixo de 80% em uso real significa que o teto está errado para o padrão de uso. O índice `data→número` passa a ser carregado **sob demanda**, não no *start* | ASS-10🟡 PERF-07🟢 OBS-06🟢 |
| **Y2** | **`vigente_desde` é atribuída pelo sistema, não escolhida pelo analista** — é a data da publicação. **Vigência retroativa entra no escopo negativo**, ao lado da futura agendada que V(1) já rejeitara. Subtrai uma capacidade que ninguém pediu e que teria reaberto a coexistência de versões | CTL-05🟡 |
| **Y3** | **O `'` só é removido quando precede caractere de fórmula** (`=`, `+`, `-`, `@`) — o inverso exato da condição em que o escape foi aplicado. Valor que legitimamente começa com apóstrofo sobrevive à ida-e-volta | LIN-09🟡 |
| **Y4** | **`ConjuntoDeRegras` nasce na fronteira de avaliação, nunca por tecla.** É construído uma vez ao carregar a versão no cache e uma vez ao validar ou precificar a partir do rascunho. A grade edita uma **lista simples**; o conjunto indexado só existe quando alguém vai avaliar | IMP-06🟡 |
| **Y5** | **A detecção de ambiguidade monetária sai de `dinheiro` e volta para `importador-csv`** — que já examina o texto bruto linha a linha e já tem relatório onde escrever. O contrato `de_texto(s) -> Dinheiro \| ErroFormato` fica **intacto**, sem precisar de um canal para "sucesso com ressalva". Desfaz X7 no lugar errado em vez de inventar um terceiro tipo de retorno | MEC-06🟡 |
| **Y6** | **"Ignorada e preservada" resolvido:** coluna desconhecida é preservada **no relatório de origem**, não no modelo de regra, e **não é reexportada**. Declarado: `Obs` é anotação humana, não atributo de regra — fica registrada na origem da versão, para consulta, e a exportação produz o conjunto de colunas conhecido | LIN-10🟢 |
| **Y7** | **`justificativa` obrigatória em TODA publicação**, não só na reversão. A edição direta é a operação que mais muda preço; exigir dela menos que da reversão era assimetria sem razão. Subtrai um caso especial | GOV-07🟢 |
| **Y8** | **Critério de corte do trace descorrelacionado da prioridade:** entram **sempre todas as que casaram**, depois as adjacentes por faixa, depois as demais — e sempre há "ver todas (Y)". O corte deixa de ser justamente contra a regra de prioridade baixa que o analista foi procurar | UX-08🟢 |
| **Y9** | **ARQ-08 aceito com justificativa:** `ConjuntoDeRegras` é VO imutável e o índice é detalhe **interno** dele — não vaza no contrato `regras_de(sku)`. Trocar a estratégia de indexação um dia é mudança confinada ao VO | ARQ-08🟢 |
| **Y10** | **Ordem declarada:** o índice em memória só é apendado **após** o *commit* da transação de publicação. Falha no meio deixa memória e banco coerentes por construção | RES-07🟢 |

## V(5) — Módulos

**Um único módulo alterado.** Os demais recebem especificação, não mudança de
fronteira ou contrato.

| id | module | alteração em V(5) |
|------|--------|-------------------|
| M-01 | dinheiro | **Contrato restaurado ao de V(3)** — `de_texto(s) -> Dinheiro \| ErroFormato`, sem canal de ressalva (Y5) |
| M-02 | modelo-dominio | Momento de construção do `ConjuntoDeRegras` declarado (Y4); índice aceito como detalhe interno do VO (Y9) |
| M-03 | motor-precificacao | — |
| M-04 | resolvedor-precedencia | — |
| M-05 | validador-coerencia | — |
| M-06 | explicador | — |
| M-07 | repositorio-sqlite | `vigente_desde` atribuída pelo sistema (Y2); `justificativa` obrigatória em toda publicação (Y7); *append* no índice só após *commit* (Y10) |
| M-08 | importador-csv | **ALTERADO:** absorve a detecção de ambiguidade monetária (Y5); *unescape* condicional (Y3); coluna desconhecida vai para o relatório de origem e não é reexportada (Y6) |
| M-09 | servico-aplicacao | Índice `data→número` carregado sob demanda (Y1) |
| M-10 | api-http | `GET /saude` expõe taxa de acerto do cache (Y1) |
| M-11 | ui-web | Critério de corte do trace descorrelacionado da prioridade (Y8) |
| M-12 | ui-editor-regras | Grade edita lista simples; o conjunto indexado é construído só na avaliação (Y4) |

## Escopo negativo — acréscimo

**Vigência retroativa** entra no escopo negativo (Y2), ao lado de vigência futura
agendada. A versão vale a partir da data em que foi publicada, e ponto.

## Premissas — V(5)

- **A-21 (nova):** `vigente_desde` é atribuída pelo sistema no ato da
  publicação. Nenhum ator escolhe a data de vigência de uma versão.
- **A-22 (nova):** o teto de 8 do cache é **parâmetro observável**, não
  constante justificada. O critério de revisão é a taxa de acerto exposta em
  `GET /saude`; abaixo de 80% em uso real, o teto está errado para o padrão de
  uso — e isso é mensurável na Fase 6, não uma promessa.

