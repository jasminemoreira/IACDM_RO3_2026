# Reagrupamento cego de achados — T32-triagem

Você recebe 78 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | repositorio | 🟡 | nada declara o comportamento sob SQLITE_BUSY, arquivo corrompido ou disco cheio. `emTransacao` falha e o design não diz o que a UI mostra nem se há repetição |
| F-02 | configuracao | 🟡 | a versão da configuração dá autoria à IMPLANTAÇÃO, não a uma pessoa. GOV-02 foi resolvido pela metade: sabe-se qual configuração agiu, não quem a escreveu |
| F-03 | casos-de-uso | 🟡 | depende de 9 dos 12 módulos. Impossível testar isolado; concentra transação, autorização, domínio e trilha. A regra "toda mudança gera trilha" mora aqui, não no domínio |
| F-04 | configuracao | 🔴 | a matriz e as metas de SLA não têm dono nem trilha. Alterar uma célula muda a prioridade de todos os chamados futuros, e é a única decisão do sistema sem autor, sem instante e sem registro |
| F-05 | trilha | 🟡 | somente-inserção e nunca apagada (A4), sem política de retenção. O armazenamento cresce proporcionalmente ao uso, para dados cujo valor decai com o tempo |
| F-06 | trilha | 🟡 | V(2) diz "união discriminada fechada" mas não enumera os construtores do evento. Um contrato que se descreve como fechado sem listar os casos é, na prática, tão aberto quanto o json que substituiu |
| F-07 | recurso | 🟡 | G5 calcula `agora − triadoEm` assumindo que `triadoEm ≠ null` quando o estado é TRIADO. O invariante `estado=TRIADO ⟹ triadoEm≠null` não está declarado em lugar nenhum |
| F-08 | configuracao | 🟡 | o prazo de 48 h para recorrer foi justificado por caber no SLA de P3/P4, e aplicado uniformemente. Para P1 (resolve em 4 h) e P2 (8 h) o chamado estará encerrado muito antes de o prazo de recurso acabar — o parâmetro não vale na faixa onde foi aplicado |
| F-09 | recurso | 🔴 | a guarda "não encerra chamado com recurso ABERTO" (MOV-4) transformou um problema benigno em bloqueio: como o prazo de julgamento não expira (REG-02, aceito na iteração 1), um recurso nunca julgado impede o encerramento do chamado indefinidamente |
| F-10 | chamado | 🔴 | não existe prazo para TRIAR. O SLA só começa a correr na triagem, então um chamado pode ficar NÃO TRIADO para sempre sem violar coisa alguma. O único estado sem governo de tempo é justamente a porta de entrada |
| F-11 | ui-web | 🟡 | `encerrar` também não tem ação declarada em nenhuma das 6 telas |
| F-12 | api-http | 🔴 | o esquema por endpoint (MOV-4) permite ao agente alterar `urgencia` na reclassificação — o eixo do solicitante. Como o prazo de recurso conta da TRIAGEM e prescreve em 48 h, uma reclassificação tardia da urgência ocorre depois de prescrito o recurso: o solicitante perde o eixo que é seu, sem instrumento para contestar |
| F-13 | sla | 🟡 | `violado` é calculado sob demanda e não gera ação: o sistema observa a violação mas não repriorioriza, não escala e não avisa. Malha aberta — mede o erro e não o corrige |
| F-14 | configuracao | 🟡 | MOV-5 tirou o seed de `repositorio` e o pôs em `configuracao`, que agora carrega matriz, metas, prazos e seed. Dado de política (muda comportamento) e dado de arranque (popula a base) são coisas distintas — o acúmulo foi movido, não removido |
| F-15 | recurso | 🟡 | ISO 10002 exige prazo declarado por nível de escalonamento. O prazo de 24 h para julgar existe como número, mas não é guarda nem gera consequência: um recurso pode ficar ABERTO indefinidamente sem que nada aconteça |
| F-16 | repositorio | 🟡 | better-sqlite3 é módulo nativo compilado contra a ABI do Node. A spec declara "Node 20+", faixa aberta que inclui ABIs incompatíveis: a tolerância declarada é maior que a real |
| F-17 | recurso | 🟡 | ISO 10002 (F6) exige informar o reclamante do recebimento e do desfecho. Notificações estão no escopo negativo e nenhum módulo é responsável por comunicar o desfecho — o solicitante precisa voltar à tela e descobrir sozinho |
| F-18 | repositorio | 🟡 | acumula portas, Data Mapper, esquema, seed e transação — cinco responsabilidades. O seed é dado de domínio morando na infraestrutura |
| F-19 | configuracao | 🔴 | assume-se que a matriz configurada é sempre válida. `derivar` faz consulta total sem fallback: célula ausente devolve `undefined`, que atravessa o sistema como se fosse Prioridade. Nada valida totalidade (9 células), monotonicidade nem domínio P1..P5 |
| F-20 | trilha | 🟡 | a trilha grava `atorId`, mas sem prova de identidade a autoria é auto-declarada. Auditoria nominal, não atribuível |
| F-21 | ui-web | 🔴 | a transição `reconhecer` existe no modelo e tem meta de prazo por prioridade, mas nenhuma das 6 telas tem ação de reconhecer. Transição sem superfície: o prazo de reconhecimento é inatingível |
| F-22 | configuracao | 🟡 | MOV-1 derruba o processo com configuração inválida e não há default de emergência. Num reinício automático com config quebrada, o sistema fica fora do ar sem rede de segurança — falha rápida sem plano B |
| F-23 | casos-de-uso | 🟡 | para implementar em sessão única é preciso o contrato de 9 módulos, o que estoura o princípio de granularidade E = I₀/C |
| F-24 | sla | 🟡 | as metas estão em horas fracionárias (P1 = 0,167 h para reconhecer). 0,167 h não é 10 minutos exatos, e `somarHoras` com fração produz milissegundos quebrados: o prazo desliza segundos em relação à meta declarada. A tolerância nunca foi declarada, e metas em minutos inteiros eliminariam a questão |
| F-25 | ui-web | 🟢 | a troca de papel é um seletor de usuário no canto. Nada sinaliza que trocar de usuário troca o contexto inteiro de autorização |
| F-26 | repositorio | 🔴 | a ordenação unificada por prazo crescente (a "solução elegante" de V(2) para PER-01) mistura duas grandezas na mesma coluna: prazo de triagem para não triados e prazo de resolução para triados. Um não triado com prazo de 8 h aparece na frente de um P1 com prazo de 4 h. A fila deixa de ordenar por severidade |
| F-27 | recurso | 🟡 | instância única e final: o solicitante com recurso improvido não tem via ulterior. ISO 10002 prevê escalonamento externo; a segunda instância foi removida por escopo negativo |
| F-28 | configuracao | 🟢 | "2 dias úteis → 48 h" foi obtido por 2×24, não por equivalência com a fonte F1. Dois dias úteis só equivalem a 48 h corridas se não houver fim de semana no meio |
| F-29 | sla | 🟡 | `somarHoras` aparece em specs/examples mas não pertence a nenhum dos 12 módulos da tabela de arquitetura |
| F-30 | trilha | 🟢 | `doChamado(id)` cresce sem limite e T-4 renderiza tudo, sem paginação. Um chamado longevo trava a própria tela |
| F-31 | ui-web | 🟡 | o cookie de sessão assinado (mitigação de SEG-01) pressupõe uma tela de entrada que não existe nas 6 telas declaradas em specs/design/telas.md. São 7 telas agora, e o documento de design não registra a sétima |
| F-32 | trilha | 🔴 | MOV-5 removeu a estatística de recursos por solicitante. A decisão da Fase 0 — "transparência + prescrição, SEM penalidade" — apoiava-se explicitamente em "o abuso fica visível e é tratado fora do sistema". V(2) removeu a visibilidade e manteve a ausência de penalidade: agora nada contém abuso, e uma decisão da Fase 0 foi esvaziada por uma simplificação da Fase 3 |
| F-33 | ui-web | 🔴 | não triados ficam em seção própria "porque não têm prioridade", e nada declara a ordenação DENTRO dessa seção. O chamado não triado mais antigo pode ficar invisível indefinidamente |
| F-34 | ui-web | 🟡 | `ui-web` depende de `api-http`, mas a UI é renderizada no servidor. Ou a UI chama casos-de-uso direto (e a dependência declarada está errada) ou faz HTTP para o próprio processo. A decomposição não resolve qual |
| F-35 | chamado | 🔴 | G2 impede abrir recurso em chamado encerrado, mas nada impede encerrar um chamado que tem recurso ABERTO. O recurso fica órfão: não pode ser julgado com efeito e não tem estado terminal |
| F-36 | configuracao | 🟢 | MOV-1 assume que reiniciar o processo é aceitável para mudar a matriz. Verdadeiro neste nó único, mas nunca declarado |
| F-37 | configuracao | 🟡 | `prazoTriagem` é um parâmetro inteiramente novo, sem fonte — nem Tier C. Nenhum dos quatro produtos pesquisados em specs/competitors tem prazo de triagem, logo nem convergência de mercado o sustenta |
| F-38 | ui-web | 🟡 | T-3 passou a exibir a matriz 3×3 estática (correção de UX-01). Efeito colateral: o agente vê o resultado de cada impacto antes de escolher e pode fazer engenharia reversa do alvo — "quero P3, logo marco MEDIO". A tela ensina exatamente a manobra que JOG-01 descreve |
| F-39 | recurso | 🟡 | ISO 10002 exige prazo por nível de escalonamento. V(2) manteve o prazo de julgamento sem expiração e ainda o tornou bloqueante do encerramento |
| F-40 | configuracao | 🔴 | alterar a matriz muda `derivar()` para chamados novos, enquanto os abertos mantêm a prioridade gravada (herdado de F4). Passam a existir dois valores de verdade para a mesma pergunta — o gravado e o recalculável — e nada reconcilia. Deriva de estado sem sinal de erro |
| F-41 | recurso | 🔴 | recontar prazos desde a abertura faz o provimento de um recurso CRIAR uma violação de SLA contada contra a própria equipe do gestor. O julgador tem incentivo direto a improver, e é da casa |
| F-42 | chamado | 🟡 | o `prazoTriagem` pode ser ultrapassado e nada acontece: não há estado, não há evento, e a fila não distingue não triado dentro do prazo de não triado violado. MOV-3 criou o prazo e não criou a consequência |
| F-43 | trilha | 🟢 | não há registro de quem leu a trilha, embora ela contenha texto livre escrito por solicitantes |
| F-44 | api-http | 🟡 | com `ui-web` passando a depender de `casos-de-uso`, existem duas portas de entrada para o mesmo núcleo: páginas por `ui-web` (GET) e ações por `api-http` (POST). As regras de sessão precisam ser idênticas nas duas, e a divergência entre elas seria invisível |
| F-45 | trilha | 🟡 | a premissa A15 declara que a trilha vive enquanto o chamado vive, mas nenhum chamado morre: não há arquivamento nem exclusão. A premissa descreve um limite que na prática é "para sempre" |
| F-46 | chamado | 🔴 | a calibração da urgência varia com letramento, hierarquia e assertividade. Solicitantes menos assertivos são sistematicamente despriorizados pela mesma dor, e a única correção disponível (o recurso) exige exatamente a assertividade que lhes falta |
| F-47 | casos-de-uso | 🔴 | MOV-2 afirmou tornar a trilha "impossível de violar". O que ficou impossível é **não produzir** o evento; ainda é perfeitamente possível **não gravá-lo** — `casos-de-uso` recebe `eventos[]` e pode simplesmente não chamar `trilha.registrar`. CA-3 continua dependendo de disciplina, ao contrário do que V(2) declarou |
| F-48 | recurso | 🟡 | PARCIALMENTE_PROVIDO só tem sentido com dois eixos contestados. Contestar um eixo e receber "parcialmente provido" é sintaticamente válido e semanticamente vazio — o contrato admite o absurdo |
| F-49 | configuracao | 🔴 | a `versao` é declarada pelo humano DENTRO do próprio arquivo. Nada impede editar a matriz e esquecer de incrementá-la — dois conteúdos distintos com a mesma versão, e a rastreabilidade que GOV-02 e CTL-01 ganharam vira disciplina humana em vez de propriedade do sistema |
| F-50 | casos-de-uso | 🟡 | ids de chamado são sequenciais e `consultarChamado` não declara verificação de propriedade. Enumerar ids expõe chamados alheios (IDOR); a matriz de autorização diz "ver o próprio chamado" sem guarda correspondente no contrato |
| F-51 | relogio | 🟡 | `Instante` não tem representação declarada (epoch ms, ISO 8601, Date). As sessões desacopladas da Fase 5 podem escolher representações incompatíveis entre `relogio`, `sla` e `repositorio` |
| F-52 | autorizacao | 🟡 | `Permissao` não enumera os motivos possíveis. B-3 (prescrição) e B-5 (legitimidade) exigem motivos distinguíveis, mas o contrato não declara quais existem |
| F-53 | chamado | 🔴 | o agente atribui o impacto e é medido pela violação de SLA que esse mesmo impacto produz. Impacto BAIXO gera prazo maior e menos risco de violação: o incentivo aponta para subestimar. A premissa A7 declara boa-fé do solicitante — ninguém declarou a do agente |
| F-54 | prioridade | 🟡 | a matriz 3×3 vem de F1, um blog de fornecedor (Tier B). Nenhum texto normativo ITIL 4 oficial foi lido — a afirmação "prática consolidada" repousa em convergência entre fornecedores, não em norma |
| F-55 | chamado | 🟢 | toda a regra de prazo depende de `abertoEm` ser imutável, o que nunca foi declarado como invariante |
| F-56 | repositorio | 🟡 | a fila ordena por "violado primeiro", e `violado` é função de `agora` — não indexável. Cada render avalia todos os chamados abertos: O(n) por requisição, com n crescendo sem limite |
| F-57 | chamado | 🟡 | declarar urgência é grátis e recorrer uma vez é grátis. Declarar ALTA sempre é estratégia dominante fraca: garante no mínimo P3 qualquer que seja o impacto |
| F-58 | trilha | 🟡 | a decisão de "transparência sem penalidade" produz estatística de recursos por solicitante. Vigiar quem exerce um direito inibe o exercício legítimo — exatamente o efeito que a recusa de punir queria evitar |
| F-59 | autorizacao | 🔴 | sem autenticação (A8), `pode(usuario, …)` confia num usuário que o próprio cliente declara. Qualquer pessoa escolhe ser GESTOR e julga qualquer recurso. A autorização é real, mas decorativa |
| F-60 | chamado | 🟡 | assume-se que todos os solicitantes calibram urgência do mesmo modo. A urgência declarada é tratada como dado objetivo, mas é juízo subjetivo sem referência comum |
| F-61 | ui-web | 🟡 | o solicitante só descobre que o prazo de recurso corria quando ele já passou: nenhuma tela informa o prazo antes de o botão sumir |
| F-62 | recurso | 🔴 | MOV-2 fez `recurso.julgar` devolver `{recurso, chamado?, eventos}`. O `chamado?` significa que o agregado Recurso **modifica outra entidade**, e o recálculo de prazos passa a existir em DOIS lugares — `chamado.reclassificar` e `recurso.julgar`. A regra que V(1) protegia por assinatura única foi duplicada por V(2) |
| F-63 | trilha | 🔴 | `antes`/`depois` são "json" sem esquema. Duas implementações corretas do contrato — uma serializando o chamado inteiro, outra só o campo alterado — produzem trilhas mutuamente ilegíveis, e CA-3 depende de ler exatamente isso |
| F-64 | configuracao | 🟡 | o processo se recusa a subir, mas nada declara COMO o operador descobre qual célula da matriz está errada. Falha rápida sem mensagem diagnóstica é opacidade — o operador só sabe que não subiu |
| F-65 | api-http | 🔴 | o design rejeita `prioridade` como entrada, mas nada impede enviar `impacto` no endpoint de abertura (onde só urgência é legítima) ou `urgencia` no de triagem. A separação de autoridade dos eixos — a descoberta central do projeto — não tem guarda declarada por endpoint |
| F-66 | configuracao | 🟡 | as metas aceitam qualquer número, sem faixa válida declarada. Uma configuração com prazo de reconhecimento maior que o de resolução é aceita sem reclamação |
| F-67 | ui-web | 🟡 | 6 telas especificadas sem declarar motor de template nem como o papel da sessão chega à página. Não implementável em sessão única sem decidir isso antes |
| F-68 | configuracao | 🟡 | o arquivo de configuração pode estar ausente ou malformado na inicialização. Não há default de emergência declarado nem falha explícita — o sistema sobe sem matriz |
| F-69 | trilha | 🟡 | a trilha é imutável e sem política de retenção, contendo nome de pessoa e texto livre sobre problemas. Nenhum módulo tem responsabilidade por exclusão ou anonimização — direito ao esquecimento colide frontalmente com o invariante A4 |
| F-70 | ui-web | 🟡 | T-3 mostra "Prioridade resultante: P4" antes de submeter. Ou o cálculo é ao vivo (exige JavaScript, contrariando "templates server-side sem cadeia de build") ou o agente tria às cegas. O design não escolhe |
| F-71 | repositorio | 🟢 | better-sqlite3 é síncrono e o modelo é thread única: toda transação bloqueia o event loop. Irrelevante com 3 usuários, mas é o teto de escala do desenho |
| F-72 | chamado | 🟡 | o `prazoTriagem` mede a VELOCIDADE da triagem e nunca a qualidade. Triar rápido com qualquer impacto satisfaz o prazo — MOV-3 acrescentou um incentivo que empurra na mesma direção de JOG-01 |
| F-73 | relogio | 🟡 | assume-se relógio monotônico. Se `agora()` retroceder (ajuste NTP, mudança manual), um recurso prescrito volta a ser admissível e um chamado violado volta a não-violado |
| F-74 | trilha | 🟡 | os eventos carregam `antes`/`depois` como json sem contrato. Sem esquema, o módulo não pode ser testado isoladamente contra nada |
| F-75 | chamado | 🟢 | a entidade depende de `sla`, logo conhece o cálculo de prazos. Testar `chamado` sem `sla` é impossível |
| F-76 | repositorio | 🟢 | chamados encerrados nunca são arquivados e continuam sendo avaliados na consulta de fila; o custo cresce com o histórico, não com o trabalho ativo |
| F-77 | ui-web | 🔴 | justificativa e fundamentação são texto livre exibido nas 6 telas para os três papéis. Nenhuma decisão de design menciona escape na renderização → XSS armazenado |
| F-78 | trilha | 🟡 | assume-se que o evento devolvido pelo domínio é serializável. Ele carrega `Prioridade`, que é tipo com marca: serializar e ler de volta devolve uma prioridade que não passou por `derivar` — o CA-negativo tem uma porta dos fundos pela trilha |
