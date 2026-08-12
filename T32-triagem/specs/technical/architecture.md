# Arquitetura — T32-triagem

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

## V(2)

Resposta unificada aos 50 defeitos distintos da Iteração 1. **Nenhum módulo
adicionado, nenhum removido, nenhum renomeado** — a rastreabilidade por nome
com a matriz de cobertura é preservada. Quatro módulos reestruturados,
sete com contrato ajustado, um intacto.

### Os seis movimentos

**MOV-1 — A configuração deixa de ser mutável em runtime.**
Carregada uma vez na inicialização, **validada na inicialização** (processo
não sobe com configuração inválida) e **imutável durante a execução**. Ganha
uma `versao` declarada no próprio arquivo, gravada em todo evento de
classificação. Resolve PRE-01, RES-02, MEC-02, GOV-02, CTL-01.
Por que simplifica: elimina a categoria inteira "estado que muda debaixo do
sistema em execução". A pergunta "por que este chamado é P4?" passa a ter
resposta única e datada — *porque a configuração vX, vigente naquele instante,
dizia isso* — em vez de duas verdades concorrentes.

**MOV-2 — O domínio produz os eventos; a trilha só os guarda.**
`chamado.triar(...)` e congêneres passam a devolver `{estado', eventos[]}`.
O evento é **união discriminada fechada**, não json livre. Resolve LIN-02,
ARQ-03, ARQ-01, IMP-01.
Por que simplifica: a regra "toda mudança gera trilha" sai de `casos-de-uso`
(onde era disciplina) e passa a ser **impossível de violar** — não existe
caminho que mude a classificação sem devolver o evento junto. CA-3 vira
garantia de tipo, como CA-negativo já era.

**MOV-3 — Um único prazo de triagem governa a porta de entrada.**
Um número na configuração: `prazoTriagem`, contado de `abertoEm`,
**independente de prioridade** — não se pode depender de uma prioridade que
ainda não existe. Resolve PRO-01 e UX-02.
Por que simplifica: dois críticos, um número. A ordenação dos não triados
deixa de ser questão em aberto porque passa a ser a mesma dos triados —
ordena-se por prazo, e agora eles têm um.

**MOV-4 — Guardas em vez de estados novos.**
Não se encerra chamado com recurso ABERTO (PRO-04). PARCIALMENTE_PROVIDO
exige dois eixos contestados (LIN-04). Cada endpoint aceita exatamente os
campos do ator competente (SEG-03).
Por que simplifica: nenhum estado novo, nenhum módulo novo. Três guardas
declarativas onde havia três buracos.

**MOV-5 — Remoções.**
Sai a estatística de recursos por solicitante (ETI-03) — nunca foi caso de
uso e contradiz o escopo negativo "relatórios e dashboards". Sai o `seed` de
`repositorio` e vira dado de `configuracao` (ARQ-04), onde dado mora.
Por que simplifica: menos superfície, menos responsabilidade por módulo.

**MOV-6 — Formatos declarados onde só havia nomes.**
`Instante` = inteiro de milissegundos desde a época, UTC (LIN-01). `Motivo` de
`autorizacao.pode` = enumeração fechada (LIN-03). Motor de template com escape
automático, nomeado (SEG-02, IMP-02). Evento de trilha com união fechada
(MOV-2). Resolve a falha sistêmica da lente Linguistics.
Por que simplifica: a Fase 5 implementa um módulo por sessão isolada a partir
do contrato apenas. Formato declarado é o que impede duas implementações
corretas de serem incompatíveis.

### Tabela de módulos — V(2)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | relogio | fonte de tempo abstrata; `Instante` = ms desde a época, UTC | `agora(): Instante`; `avancar(ms)` (só teste) | — |
| M-02 | configuracao | carrega, VALIDA e congela matriz, metas, prazos do rito, prazo de triagem e seed; expõe `versao` | `carregar(): Config \| erro`; `matriz()`; `metas()`; `prazoTriagem()`; `prazosRito()`; `versao()`; `seed()` | — |
| M-03 | prioridade | deriva P = matriz(impacto, urgencia); única origem de uma Prioridade | `derivar(impacto, urgencia): Prioridade` | configuracao |
| M-04 | sla | aritmética de instantes; prazos contados da abertura; prazo de triagem; avaliação de violação | `prazos(p, abertoEm)`; `prazoTriagem(abertoEm)`; `violado(prazos, agora)`; `somarHoras(i, h)` | configuracao |
| M-05 | chamado | entidade Chamado; toda operação devolve `{chamado, eventos[]}`; guardas de transição | `abrir`; `triar`; `reclassificar`; `reconhecer`; `encerrar` → `{chamado, eventos}` | prioridade, sla |
| M-06 | recurso | agregado Recurso; admissibilidade (5 guardas), julgamento, efeito; devolve `{recurso, chamado?, eventos[]}` | `abrir(...)`; `julgar(...)` → `{recurso, chamado?, eventos}` | chamado, configuracao |
| M-07 | trilha | guarda e devolve eventos de tipo fechado; NÃO os constrói | `registrar(eventos: Evento[])`; `doChamado(id): Evento[]` | — |
| M-08 | autorizacao | RBAC + legitimidade; devolve `Permitido \| {negado, motivo: Motivo}` com `Motivo` enumerado | `pode(usuario, acao, alvo): Permissao` | — |
| M-09 | repositorio | portas, Data Mapper SQLite, esquema, transação (o seed saiu) | `emTransacao(fn)`; `chamados`; `recursos`; `trilha`; `usuarios` | chamado, recurso, trilha |
| M-10 | casos-de-uso | orquestra: autoriza, chama o domínio, persiste estado e eventos devolvidos | `abrirChamado`; `triar`; `reclassificar`; `reconhecer`; `encerrar`; `abrirRecurso`; `julgarRecurso`; `consultarFila`; `consultarChamado` | M-01..M-09 |
| M-11 | api-http | rotas Fastify com esquema POR ENDPOINT; sessão de papel em cookie assinado | rotas HTTP | casos-de-uso |
| M-12 | ui-web | 6 telas com escape automático; ações reconhecer/encerrar em T-4; prazo de recurso visível; não triados ordenados por prazo de triagem | páginas HTML | casos-de-uso |

Mudança na dependência de M-12: passa a depender de `casos-de-uso`, não de
`api-http` — a UI é renderizada no servidor e não faz HTTP para si mesma
(ARQ-02). `api-http` continua existindo para as ações (POST) e é onde vivem os
esquemas por endpoint.

### Premissas — V(2)

A1–A5, A8–A10 permanecem. Revisadas e acrescentadas:

| # | Premissa | Estado |
|---|---|---|
| A6 | Os dois eixos têm peso igual (matriz simétrica) | mantida, **declarada não validada** |
| A7 | Solicitante age de boa-fé | mantida, **declarada não validada** — e agora acompanhada de A11 |
| A11 | **O agente também age de boa-fé ao atribuir impacto** | NOVA — JOG-01 mostrou que a boa-fé do agente nunca havia sido declarada, embora o desenho dependa dela tanto quanto da do solicitante |
| A12 | `estado=TRIADO ⟹ triadoEm ≠ null` | NOVA — invariante que G5 já pressupunha (PRE-02) |
| A13 | `abertoEm` é imutável após a abertura | NOVA — toda a regra de prazo depende disso (PRE-05) |
| A14 | O relógio é monotônico e não retrocede | NOVA — declarada como premissa em vez de suposição tácita (PRE-03) |
| A15 | A trilha vive enquanto o chamado vive; não há arquivamento nesta entrega | NOVA — torna explícito o limite que REG-03 e SUS-01 expuseram |

---

## V(3)

Resposta à iteração 2. Sete movimentos, **seis deles subtrativos** — V(3) é
menor que V(2). Nenhum módulo adicionado, removido ou renomeado.

**MOV-7 — `configuracao` volta a ser só política.**
O `seed` sai do módulo e vira **arquivo de migração** executado por
`repositorio` na inicialização — deixa de ser responsabilidade de qualquer
módulo de domínio (ARQ-07). A `versao` deixa de ser declarada à mão e passa a
ser **derivada do conteúdo** (hash do arquivo de política), eliminando a
disciplina humana de que CTL-03 dependia. A validação ganha **mensagem
diagnóstica que nomeia a célula ou a meta inválida** (OBS-01).

**MOV-8 — o recálculo volta a ter um único dono.**
`recurso.julgar` **não modifica mais o chamado**: devolve
`{recurso, novosEixos?, eventos}`. Quem aplica é `chamado.reclassificar`, que
já é o único lugar do sistema que recalcula prioridade e prazos (ARQ-06).
`casos-de-uso.julgarRecurso` compõe as duas chamadas com `origem=RECURSO`.

**MOV-9 — gravar a trilha deixa de ser opcional.**
`repositorio` não expõe mais "salvar entidade". Expõe
`salvar(resultado: {entidade, eventos})` — **não existe função que grave o
estado sem os eventos** (IMP-04). O que MOV-2 prometia e não entregava passa a
valer por tipo. Um método no lugar de dois.

**MOV-10 — a fila ordena por severidade, em duas seções.**
Triados por (violado, prioridade, prazo); não triados por prazo de triagem.
Deixam de competir na mesma coluna (PER-04). A elegância de PER-01 sobrevive
dentro de cada seção: prazo crescente ainda põe os violados no topo.

**MOV-11 — o prazo de julgamento passa a ter consequência.**
Um desfecho terminal novo no enum existente: `PRESCRITO_SEM_JULGAMENTO`.
Recurso não julgado em 24 h prescreve, libera o encerramento do chamado e
registra na trilha que ninguém julgou (PRO-06, REG-04). Um valor de
enumeração, nenhuma máquina de estados nova.

**MOV-12 — o prazo de recurso passa a contar da última mudança de
classificação**, não da triagem. Se o agente reclassifica a urgência no quinto
dia, o solicitante tem 48 h novas para contestar (SEG-05).

**MOV-13 — formatos e sinais.**
Metas em **minutos inteiros**, não horas fracionárias (MEC-03). Construtores
de evento **enumerados um a um** (LIN-05). A trilha guarda prioridade como
string simples — o tipo com marca só existe no domínio, de modo que ler da
trilha nunca produz uma `Prioridade` que não passou por `derivar` (PRE-07).
Não triado fora do prazo é sinalizado na fila como qualquer violado (PRO-05).
A sétima tela (entrada/seleção de usuário) entra em `specs/design/telas.md`
(UX-06).

### Tabela de módulos — V(3)

Alterações em relação a V(2) marcadas com ◆.

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | relogio | fonte de tempo; `Instante` = ms desde a época, UTC | `agora(): Instante`; `avancar(ms)` (só teste) | — |
| M-02 | configuracao ◆ | política e só política: matriz, metas (em minutos), prazos do rito, prazo de triagem; valida com diagnóstico nomeado; `versao` = hash do conteúdo | `carregar(): Politica \| ErroValidacao`; `matriz()`; `metas()`; `prazoTriagem()`; `prazosRito()`; `versao()` | — |
| M-03 | prioridade | deriva P = matriz(impacto, urgencia); única origem de uma Prioridade | `derivar(impacto, urgencia): Prioridade` | configuracao |
| M-04 | sla ◆ | aritmética de instantes em minutos inteiros; prazos da abertura; prazo de triagem; violação | `prazos(p, abertoEm)`; `prazoTriagem(abertoEm)`; `violado(prazos, agora)`; `somarMinutos(i, m)` | configuracao |
| M-05 | chamado ◆ | entidade Chamado; único dono do recálculo de prioridade e prazos; devolve `{chamado, eventos[]}` | `abrir`; `triar`; `reclassificar(eixos, origem)`; `reconhecer`; `encerrar` | prioridade, sla |
| M-06 | recurso ◆ | agregado Recurso; admissibilidade, julgamento, prescrição sem julgamento; **não modifica o chamado** | `abrir(...)`; `julgar(...)`; `prescrever(...)` → `{recurso, novosEixos?, eventos}` | configuracao |
| M-07 | trilha ◆ | guarda e devolve eventos de construtores enumerados; prioridade como string | `doChamado(id): Evento[]` | — |
| M-08 | autorizacao | RBAC + legitimidade; `Motivo` enumerado | `pode(usuario, acao, alvo): Permissao` | — |
| M-09 | repositorio ◆ | portas, Data Mapper, esquema, migração+seed, transação; **só sabe salvar estado COM eventos** | `emTransacao(fn)`; `salvar({entidade, eventos})`; consultas | chamado, recurso, trilha |
| M-10 | casos-de-uso ◆ | orquestra: autoriza, compõe domínio (inclusive recurso→chamado), persiste via `salvar` | UC-1..UC-6 | M-01..M-09 |
| M-11 | api-http ◆ | **única porta**: rotas GET e POST, esquema por endpoint, sessão em cookie assinado | rotas HTTP | casos-de-uso, ui-web |
| M-12 | ui-web ◆ | **só renderização**: 7 templates com escape automático, sem rota própria | `render(pagina, dados): HTML` | — |

`recurso` deixa de depender de `chamado` (MOV-8). `ui-web` deixa de depender
de qualquer coisa e passa a ser camada pura de renderização, invocada por
`api-http` — resolve ARQ-02 e ARQ-08 de uma vez, e elimina as duas portas.

### Premissas — V(3)

A1–A15 permanecem, com A15 corrigida. Nova:

| # | Premissa | Nota |
|---|---|---|
| A15 ◆ | Não há arquivamento nesta entrega; o crescimento da base é ilimitado e **conhecido** | corrigida — "a trilha vive enquanto o chamado vive" era enganoso, porque nenhum chamado morre (SUS-03) |
| A16 | Reiniciar o processo é aceitável para mudar a política | NOVA — verdadeiro neste nó único, agora declarado (PRE-06) |

**MOV-14 — contexto de decisão no lugar de relatório (arbitragem do operador
sobre ETI-04).** A tela de julgar (T-6) exibe ao gestor "este é o Nº recurso
de \<solicitante\> nos últimos 30 dias". Não é dashboard nem relatório: é
contexto de uma decisão específica, exibido a quem tem autoridade para
decidir, e não existe em nenhuma outra tela. Restaura a visibilidade de que a
política anti-abuso da Fase 0 dependia, sem violar o escopo negativo. Custo
reconhecido: dá razão parcial a ETI-03 — quem exerce o direito é, em alguma
medida, contado. A tensão entre ETI-03 e ETI-04 é real e foi arbitrada pelo
operador, não dissolvida.


