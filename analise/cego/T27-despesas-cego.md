# Reagrupamento cego de achados — T27-despesas

Você recebe 95 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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
| M-01 | dominio-despesa | entidade Despesa, estados e transições válidas, valor em centavos; guarda INV-9, INV-11, INV-12 | `criar(solicitante, valorCentavos, descricao) -> Despesa \| ErroValidacao` · `aprovarNivel(despesa, nivel) -> Despesa` · `rejeitar(despesa, motivo) -> Despesa \| ErroMotivoAusente` | — |
| M-02 | matriz-doa | papéis, níveis e limites; monta a cadeia de aprovação para (valor, papel do solicitante); guarda INV-1, INV-10, INV-13 | `cadeiaPara(valorCentavos, papelSolicitante) -> Papel[] \| ErroAcimaDoTeto \| ErroSemAutoridadeAcima` · `limiteDe(papel) -> centavos` · `papelTopo() -> Papel` | — |
| M-03 | dominio-delegacao | entidade Delegação, vigência, revogação, estado efetivo contra um instante; guarda INV-3, INV-5 | `podeCriar(delegante, delegado, inicio, fim, ativasDoDelegante, ativasDoDelegado) -> ok \| ErroSoD` · `ativaEm(delegacoes, delegante, instante) -> Delegacao \| null` · `revogar(delegacao, instante) -> Delegacao` | relogio (só o tipo `Instante`) |
| M-04 | autoridade | responde "quem pode decidir este item agora e sob qual autoridade"; único ponto onde alçada e delegação se cruzam; guarda INV-2, INV-4, INV-6 | `resolver(despesa, usuarioAtuante, trilhaDaDespesa, delegacoesAtivas, instante) -> { permitido: true, emNomeDe: Usuario \| null, limiteExercido: centavos } \| ErroSoD(codigo, mensagem)` | matriz-doa, dominio-delegacao, trilha |
| M-05 | bandeja | monta a fila de um aprovador: pendências próprias + recebidas por delegação ativa; FIFO, valor e origem visíveis | `listar(usuario, instante) -> ItemBandeja[]` onde `ItemBandeja = { despesa, nivel, origem: 'propria' \| { emNomeDe: Usuario } }` | matriz-doa, dominio-delegacao, autoridade, portas-repositorio |
| M-06 | trilha | registro append-only de transições e decisões, com ator efetivo, em-nome-de, instante e limite exercido; guarda INV-7, INV-8 | `registrar(evento: Evento) -> void` · `de(despesaId) -> Evento[]` · `decisoesDe(despesaId) -> Decisao[]` | portas-repositorio |
| M-07 | relogio | porta `Clock` + adaptador real + adaptador controlável com avanço manual | `agora() -> Instante` · (só no adaptador de teste/demo) `avancar(ms) -> void` · `fixarEm(instante) -> void` | — |
| M-08 | portas-repositorio | contratos de persistência por agregado + contrato de transação | `DespesaRepo{ salvar, porId, pendentesDe(nivel) }` · `DelegacaoRepo{ salvar, ativasEm(instante), porDelegante }` · `UsuarioRepo{ porId, todos }` · `TrilhaRepo{ anexar, porDespesa }` · `emTransacao<T>(fn) -> T` | — |
| M-09 | sqlite-adaptador | implementa as portas em SQLite: schema, transação leitura-para-atualização, seed da matriz DoA e dos usuários | implementa integralmente M-08; `abrir(caminho) -> Repositorios` · `migrar() -> void` · `semear() -> void` | portas-repositorio |
| M-10 | casos-de-uso | orquestra UC-1..UC-7 dentro de uma transação; traduz violação de invariante em erro nomeado | `solicitar` · `aprovar` · `rejeitar` · `delegar` · `revogar` · `verBandeja` · `verTrilha` — cada um `(comando, atuante) -> Resultado \| ErroNomeado` | dominio-despesa, matriz-doa, dominio-delegacao, autoridade, bandeja, trilha, relogio, portas-repositorio |
| M-11 | api-http | Fastify: rotas, validação de entrada, identidade simulada, tradução erro de domínio → status HTTP | `POST /despesas` · `POST /despesas/:id/aprovar` · `POST /despesas/:id/rejeitar` · `POST /delegacoes` · `POST /delegacoes/:id/revogar` · `GET /bandeja` · `GET /despesas/:id` · `POST /relogio/avancar` | casos-de-uso |
| M-12 | ui-web | 6 telas server-rendered: seleção de usuário, nova despesa, bandeja, detalhe + trilha, delegações, auditoria | páginas HTML servidas por M-11; formulários POST; sem build, sem SPA | api-http |
| M-01 | dominio-despesa | inalterado desde V(1): entidade Despesa, estados e transições, valor em centavos; guarda INV-9, INV-11, INV-12 | `criar(...) -> Resultado<Despesa, ErroValidacao>` · `aprovarNivel(...)` · `rejeitar(despesa, motivo)` | — |
| M-02 | matriz-doa | papéis, níveis, limites; valida a matriz na carga; monta a cadeia como função total; guarda INV-1, INV-10, INV-13, INV-14, INV-15 | `validar(matriz) -> Resultado<MatrizValida, ErroMatriz>` · `cadeiaPara(valorCentavos, papelSolicitante, titulares) -> Resultado<Papel[], ErroAcimaDoTeto \| ErroSemAutoridadeAcima \| ErroPapelSemTitular>` · `limiteDe(papel)` | — |
| M-03 | dominio-delegacao | entidade Delegação, vigência, revogação, estado efetivo contra um instante; guarda INV-3, INV-5, INV-16 | `podeCriar(...) -> Resultado<ok, ErroSoD>` · `ativaEm(delegacoes, delegante, instante)` · `revogar(delegacao, instante)` | — |
| M-04 | autoridade | quem pode decidir este item agora e sob qual autoridade; guarda INV-2, INV-4, INV-6 | `resolver(despesa, atuante, decisoesDaDespesa, delegacoesAtivas, instante) -> Resultado<{ emNomeDe, delegacaoId, limiteExercido }, ErroSoD>` | matriz-doa, dominio-delegacao |
| M-05 | bandeja | filtra as pendentes por autoridade do usuário; FIFO por `criada_em`, valor e origem visíveis | `listar(usuario, instante) -> ItemBandeja[]` | autoridade, portas-repositorio |
| M-06 | trilha | registro append-only pela aplicação; grava ator, em-nome-de, `delegacao_id`, instante e limite exercido; guarda INV-7, INV-8 | `registrar(evento: Evento) -> void` · `de(despesaId) -> Evento[]` — `Evento` é união discriminada: `Criada \| AprovadaNivel \| Rejeitada` | portas-repositorio |
| M-07 | relogio | porta de produção `Clock` só de leitura; adaptador controlável separado, exclusivo de teste | `Clock { agora(): Instante }` · (só teste) `ClockControlavel { agora, avancar(ms), fixarEm(i) }` | — |
| M-08 | portas-repositorio | contratos de persistência por agregado + transação; exige prepared statements | `DespesaRepo{ salvar, porId, pendentes() }` · `DelegacaoRepo{ salvar, ativasEm(instante), porDelegante }` · `UsuarioRepo{ porId, todos, titularesPorPapel() }` · `TrilhaRepo{ anexar, porDespesa }` · `emTransacao<T>(fn)` | — |
| M-09 | sqlite-adaptador | implementa as portas; schema com índice em `evento_trilha.despesa_id`; `semear()` só em banco vazio; falha de abertura derruba o processo com mensagem | `abrir(caminho) -> Repositorios` · `migrar()` · `semear()` | portas-repositorio |
| M-10 | casos-de-uso | inalterado desde V(1): orquestra UC-1..UC-7 em uma transação; traduz erro de domínio em erro nomeado | `solicitar` · `aprovar` · `rejeitar` · `delegar` · `revogar` · `verBandeja` · `verTrilha` | dominio-despesa, matriz-doa, dominio-delegacao, autoridade, bandeja, trilha, relogio, portas-repositorio |
| M-11 | api-http | rotas, resolução e validação do usuário atuante em ponto único, limite de corpo, erro de domínio → status HTTP. **Sem rota de relógio** | `POST /despesas` · `/despesas/:id/aprovar` · `/despesas/:id/rejeitar` · `POST /delegacoes` · `/delegacoes/:id/revogar` · `GET /bandeja` · `GET /despesas/:id` | casos-de-uso |
| M-12 | ui-web | 6 telas server-rendered com **escape por padrão**; a tela de decisão exibe a autoridade exercida; identidade corrente visível em todas as telas; confirmação na rejeição | páginas HTML; identidade explícita em cada formulário, sem cookie de sessão | api-http |
| M-01 | dominio-despesa | inalterado desde V(1) | `criar` · `aprovarNivel` · `rejeitar` — todos `Resultado<T,E>` | — |
| M-02 | matriz-doa | **alterado**: fórmula da cadeia corrigida, INV-15 revogada, `titulares` removido; guarda INV-1, INV-10, INV-13, INV-14 | `validar(matriz) -> Resultado<MatrizValida, ErroMatriz>` · `cadeiaPara(valorCentavos, papelSolicitante) -> Resultado<Papel[], ErroAcimaDoTeto \| ErroSemAutoridadeAcima>` · `limiteDe(papel)` | — |
| M-03 | dominio-delegacao | inalterado desde V(2); INV-16 com regra de fuso explícita | `podeCriar` · `ativaEm` · `revogar` | — |
| M-04 | autoridade | **alterado**: delegação é caminho adicional — delegado inelegível não retira o item do delegante; guarda INV-2, INV-4, INV-6, INV-17 | `resolver(despesa, atuante, decisoesDaDespesa, delegacoesAtivas, instante) -> Resultado<{ emNomeDe, delegacaoId, limiteExercido }, ErroSoD>` | matriz-doa, dominio-delegacao |
| M-05 | bandeja | inalterado; `depends-on` agora declara o que já usava | `listar(usuario, instante) -> ItemBandeja[]` | autoridade, portas-repositorio (`DespesaRepo`, `TrilhaRepo`, `DelegacaoRepo`) |
| M-06 | trilha | **alterado**: `registrar` passa a devolver `Resultado` | `registrar(evento) -> Resultado<void, ErroPersistencia>` · `de(despesaId) -> Evento[]` | portas-repositorio |
| M-07 | relogio | **alterado**: offset em vez de instante fixo — o relógio anda | `Clock { agora(): Instante }`, `agora() = real + T27_RELOGIO_OFFSET_MS`; (só teste) `ClockControlavel` | — |
| M-08 | portas-repositorio | inalterado desde V(2) | `DespesaRepo{ salvar, porId, pendentes() }` · `DelegacaoRepo` · `UsuarioRepo{ porId, todos, titularesPorPapel() }` · `TrilhaRepo{ anexar, porDespesa }` · `emTransacao<T>` | — |
| M-09 | sqlite-adaptador | inalterado desde V(2); + offset inválido impede a subida | `abrir` · `migrar` · `semear` | portas-repositorio |
| M-10 | casos-de-uso | **alterado**: passa a consultar elegibilidade nível a nível (o que saiu de `matriz-doa` em S1.3) | `solicitar` · `aprovar` · `rejeitar` · `delegar` · `revogar` · `verBandeja` · `verTrilha` | núcleo M-01..M-08 |
| M-11 | api-http | **alterado**: identidade em cookie + campo, com igualdade exigida | rotas de V(2), sem rota de relógio | casos-de-uso |
| M-12 | ui-web | **alterado**: `render(template, dados)` escapa tudo; mensagem de recusa deixa de instruir o impossível | 6 telas de `specs/design/telas.md` | api-http |
| M-01 | dominio-despesa | inalterado | `criar` · `aprovarNivel` · `rejeitar` | — |
| M-02 | matriz-doa | inalterado desde V(3) | `validar(matriz, usuarios)` · `cadeiaPara(valor, papelSolicitante)` · `limiteDe` | — |
| M-03 | dominio-delegacao | inalterado | `podeCriar` · `ativaEm` · `revogar` | — |
| M-04 | autoridade | **alterado**: recebe de volta a decisão de elegibilidade; guarda INV-2, INV-4, INV-6, INV-17, INV-18 | `resolver(...)` · **`algumDecisor(despesa, nivel, titulares, decisoes, delegacoes, instante) -> boolean`** | matriz-doa, dominio-delegacao |
| M-05 | bandeja | inalterado | `listar(usuario, instante)` | autoridade, portas-repositorio |
| M-06 | trilha | **alterado**: novo evento `NivelPulado`; `registrar` obrigatoriamente dentro da transação | `registrar(evento) -> Resultado<void, ErroPersistencia>` · `de(despesaId)`; `Evento = Criada \| AprovadaNivel \| NivelPulado \| Rejeitada` | portas-repositorio |
| M-07 | relogio | inalterado desde V(3) | `Clock { agora() }` com offset | — |
| M-08 | portas-repositorio | inalterado | `DespesaRepo` · `DelegacaoRepo` · `UsuarioRepo` · `TrilhaRepo` · `emTransacao<T>` | — |
| M-09 | sqlite-adaptador | inalterado | `abrir` · `migrar` · `semear` | portas-repositorio |
| M-10 | casos-de-uso | **alterado**: devolve a elegibilidade a `autoridade` e apenas orquestra; aborta a transação se a trilha falhar | `solicitar` · `aprovar` · `rejeitar` · `delegar` · `revogar` · `verBandeja` · `verTrilha` | núcleo M-01..M-08 |
| M-11 | api-http | **alterado**: cookie carrega só o nonce anti-CSRF; identidade em campo/parâmetro por requisição | rotas de V(3) | casos-de-uso |
| M-12 | ui-web | **alterado**: tipo `Html` marcado no `render`; identidade por requisição em todo link e formulário | 6 telas | api-http |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | relogio | 🟡 | `avancar` muda o comportamento do sistema em runtime sem amortecimento: avançar e recuar faz delegações oscilarem entre ativa e expirada, e a autoridade exercida deixa de ser função monótona do tempo |
| F-02 | sqlite-adaptador | 🟡 | Nenhuma entidade tem dono declarado para efeito de correção. Com a matriz DoA fora de escopo para edição em runtime, um papel errado no seed não tem caminho de correção nenhum — nem por Admin |
| F-03 | ui-web | 🟡 | As 6 telas existem só por nome. `specs/design/` não tem wireframe nem lista de campos por tela — o implementador inventa a interface, e é justamente ela que CA-11 exige validar |
| F-04 | matriz-doa | 🟡 | `cadeiaPara` devolve `Papel[]` sem dizer a ordem nem se o papel final está incluído |
| F-05 | matriz-doa | 🔴 | despesa de valor coberto pela própria alçada do papel do solicitante fica sem nenhum aprovador na cadeia |
| F-06 | sqlite-adaptador | 🟢 | Mapeamento manual com SQL explícito abre espaço para concatenação de string; o contrato não exige prepared statements |
| F-07 | relogio | 🟡 | A6 assume relógio monotônico, mas o adaptador controlável aceita avanço arbitrário e nada proíbe retrocesso; delegações expiradas voltariam a ativas, e o adaptador real está sujeito a ajuste do sistema |
| F-08 | trilha | 🟡 | R3 removeu `DEVOLVIDA_AO_DELEGANTE` e a trilha da despesa deixou de registrar que uma delegação venceu com item pendente. Um auditor que pergunte "por que A decidiu isto em 21/08 se B era o delegado?" precisa inferir cruzando vigências — a resposta deixou de estar escrita e passou a ser reconstruída |
| F-09 | relogio | 🔴 | R4 trocou a rota de relógio por `T27_RELOGIO` lida no boot — mas fixar o instante torna `agora()` CONSTANTE durante todo o processo. Todas as despesas nascem com o mesmo `criada_em`, o FIFO da bandeja fica indefinido, a trilha perde cronologia interna e nenhuma vigência jamais expira enquanto o processo viver. A correção de SEC-02 quebrou o relógio |
| F-10 | ui-web | 🔴 | S4 pôs a identidade em cookie, logo **um navegador = um usuário**. Mas CA-3, CA-3b e o teste manual de CA-11 exigem operar delegante e delegado lado a lado: o operador terá de usar janela anônima ou dois navegadores para exercer o caso de uso central do produto. V(2) permitia duas abas |
| F-11 | matriz-doa | 🟢 | A fórmula de S1.1 assume que o papel do solicitante existe na matriz validada; se um usuário apontar para papel inexistente, `nivel(papelSolicitante)` é indefinido e a comparação falha em silêncio |
| F-12 | matriz-doa | 🟡 | Os limites do seed (5k/50k/500k) são declaradamente arbitrários — aceitável — mas a forma que os justifica ("uma ordem de grandeza por nível") vem de blogs comerciais (Stampli, AuraVMS), não de fonte revisada por pares |
| F-13 | dominio-despesa | 🟢 | Não existe estado de rascunho: `criar` já publica na fila. Coerente com o escopo, mas o solicitante não pode preparar sem submeter |
| F-14 | autoridade | 🟢 | A semântica de delegação foi ancorada em DW-RBAC (fonte revisada), mas a arquitetura não diz qual construção do paper corresponde a `resolver()`. Sem esse mapeamento, o "porte Tier 2" da Fase 5 vira reimplementação de memória (AP7) |
| F-15 | relogio | 🟢 | `avancar`/`fixarEm` moram na mesma porta que `agora()`. A porta de produção não deveria expor mutação de tempo |
| F-16 | autoridade | 🔴 | Contradição entre a tabela e a assinatura: `depends-on` declara M-06 (trilha), mas a interface recebe `trilhaDaDespesa` como parâmetro. Se a dependência for real, um módulo de domínio passa a depender do histórico persistido e deixa de ser testável isolado; se for só o parâmetro, a tabela mente sobre o grafo |
| F-17 | matriz-doa | 🔴 | INV-15 verifica se o papel tem TITULAR, não se tem titular ELEGÍVEL. O Diretor delega à única Gerente: ela decide o nível Gerente e, no nível Diretor, é bloqueada por INV-4 (mesmo ator duas vezes na cadeia). Ninguém mais pode decidir e a despesa fica órfã — o estado que INV-15 foi criada para eliminar, reintroduzido pela delegação |
| F-18 | casos-de-uso | 🟢 | A consulta de elegibilidade nível a nível na criação adiciona uma leitura de titulares por nível da cadeia; irrelevante com 3 papéis, mas é trabalho que V(2) não fazia |
| F-19 | dominio-delegacao | 🟡 | Declara depender de M-07 apenas pelo tipo `Instante`. Se `Instante` for `string` ISO, a dependência desaparece — acoplamento declarado sem necessidade |
| F-20 | api-http | 🟢 | `POST /relogio/avancar` não registra quem avançou o relógio: ação sem autor em um sistema cuja razão de ser é atribuir autoria. Relacionado a SEC-02, mas o defeito aqui é a ausência de registro, não a exposição |
| F-21 | sqlite-adaptador | 🟢 | a ausência de caminho de correção deixou de ser teórica: UX-07 mostra que ela agora aparece como instrução impossível na tela do usuário |
| F-22 | matriz-doa | 🟡 | O solicitante escolhe o valor: dividir R$60k em duas despesas de R$30k evita o nível superior inteiro. *Splitting* é o ataque clássico contra matriz DoA e não há nenhuma detecção — nem agregação por período, nem sinalização de despesas próximas do limite |
| F-23 | matriz-doa | 🔴 | `cadeiaPara(valor, papelSolicitante)` é ambígua no ponto que define o produto: solicitante Coordenador(1), valor R$80k, papéis acima = Gerente(50k) e Diretor(500k). A cadeia é [Gerente, Diretor] ou só [Diretor]? A Fase 0 sugere a primeira, mas CA-1 fala em "exatamente N aprovações" sem definir N por fórmula. Dois implementadores corretos produzem sistemas diferentes |
| F-24 | matriz-doa | 🔴 | A cadeia é montada sobre PAPÉIS, mas quem decide são PESSOAS. Se nenhum usuário ocupa um papel da cadeia (vago, ou o único titular ausente sem delegar), a despesa fica PENDENTE para sempre — o estado órfão que INV-10 e INV-13 pretendiam eliminar volta por outra porta |
| F-25 | bandeja | 🔴 | O modelo de dados prevê o evento `DEVOLVIDA_AO_DELEGANTE`, mas sem agendador ninguém o grava: a devolução é consequência de derivar a bandeja. Ou o evento nunca existe, ou nasce quando alguém abre a tela — duas fontes de verdade (trilha e derivação) que podem discordar |
| F-26 | ui-web | 🔴 | A tela de decisão não está especificada para mostrar sob qual autoridade o usuário está agindo. O delegado clica "aprovar" sem ver "em nome de A, exercendo o limite dele de R$50k" — é o modo de falha central deste produto: exercer autoridade alheia sem perceber |
| F-27 | autoridade | 🟢 | O registro do limite exercido atende à exigência de atribuição e é rastreável a M-06; sem correção a fazer |
| F-28 | matriz-doa | 🟡 | pular um nível degrada o princípio dos quatro olhos para dois, sem que nenhuma norma de DoA das fontes levantadas preveja essa degradação silenciosa |
| F-29 | casos-de-uso | 🟡 | S1.3 move a consulta de elegibilidade para `casos-de-uso`, e V(3) assume que "elegível na criação" e "elegível na decisão" são a mesma coisa. Não são: na criação não há decisões, logo INV-4 não pode ser avaliada; na decisão ela pode inelegibilizar um nível que na criação parecia ocupado |
| F-30 | ui-web | 🟡 | Com a identidade em cada formulário e em cada link, basta um link montado sem o parâmetro para o usuário perder a identidade no meio do fluxo — ou herdar a de quem lhe mandou a URL. O cabeçalho "Você é" passa a refletir o link, não a pessoa |
| F-31 | bandeja | 🟢 | o trabalho por render cresce com o histórico acumulado, não só com a fila; como a trilha nunca é expurgada (R6), o custo do caminho mais quente cresce para sempre |
| F-32 | matriz-doa | 🔴 | A fórmula de R2 produz cadeia VAZIA no caso mais comum do domínio. Coordenador (nível 1, limite R$5.000) solicita R$100: `p*` = Coordenador, e a cadeia `{p : nivel(p) > 1 e nivel(p) <= 1}` é vazia. Despesa sem nenhum aprovador — ou aprova sozinha, ou fica órfã. A fórmula precisa ancorar `p*` no menor papel ACIMA do solicitante cujo limite cobre o valor |
| F-33 | trilha | 🟢 | O modelo de dados não declara índice em `evento_trilha.despesa_id`; `de(despesaId)` vira varredura da tabela que mais cresce |
| F-34 | ui-web | 🔴 | A mensagem de INV-15 em T2 instrui: "peça ao Admin para cadastrar um titular". O Admin NÃO pode cadastrar — edição de usuários e da matriz está fora de escopo por decisão da Fase 0, e o seed só roda em banco vazio por R1. A tela manda o usuário executar uma ação que o sistema não oferece a ninguém |
| F-35 | trilha | 🟡 | O nível pulado por S1.2 não é registrado em lugar nenhum: a trilha não explica por que a despesa foi aprovada com menos aprovações do que a cadeia previa. É a mesma perda de explicabilidade de GOV-04, agora no caminho de aprovação |
| F-36 | autoridade | 🟢 | V(2) reescreveu a assinatura de `resolver()` sem mapear qual construção do DW-RBAC ela realiza; o achado da iteração 1 segue aberto contra a nova versão |
| F-37 | casos-de-uso | 🟡 | Assume-se que o usuário atuante existe e tem papel. A identidade vem do cliente (A5) — o comportamento com id inexistente ou papel ausente não está definido em nenhum contrato |
| F-38 | api-http | 🔴 | `POST /relogio/avancar` na mesma superfície permite avançar o relógio para expirar a delegação de outro, ou fixá-lo para trás e reabrir autoridade já encerrada. Corrompe a semântica temporal de INV-6 mesmo entre usuários honestos — não é coberto pelo aceite de A5 |
| F-39 | trilha | 🟡 | `registrar(evento) -> void` contradiz a convenção de R7 ("todo o núcleo retorna `Resultado<T, ErroDominio>` e nunca lança"). Uma implementação que lance ao violar a constraint e outra que engula o erro são ambas fiéis a `void` — e incompatíveis |
| F-40 | relogio | 🟡 | Com o offset lido só no boot, demonstrar a expiração de uma delegação (CA-5) no teste manual exige **reiniciar o processo** com outro offset — procedimento que nenhuma spec documenta, e que o operador precisa executar para fechar CA-11 |
| F-41 | matriz-doa | 🟢 | Cadeia recalculada a cada chamada sem memoização. Irrelevante com 3 papéis, mas está no mesmo caminho quente de PERF-01 |
| F-42 | bandeja | 🟢 | FIFO sem prazo torna adiar gratuito: nada no desenho pressiona o aprovador a decidir, e SLA está fora de escopo por decisão registrada |
| F-43 | casos-de-uso | 🟡 | "Elegível" passou a ser conceito central de V(3) (S1.2, S2, INV-17) e não está definido em nenhum contrato: é "existe titular", "existe titular que não é o solicitante" ou "existe titular que `resolver` aprovaria agora"? As três dão cadeias diferentes |
| F-44 | dominio-delegacao | 🟢 | INV-3 (não transitiva) é decisão do operador contra um espaço que a literatura descreve como multi-passo. Rastreabilidade existe e está registrada; sem correção a fazer |
| F-45 | ui-web | 🟡 | `motivo` de rejeição e `descricao` de despesa são texto livre renderizado em HTML server-rendered: sem escape, é XSS armazenado — e como a trilha é append-only (INV-8), o payload persiste para sempre sem caminho de remoção |
| F-46 | sqlite-adaptador | 🟢 | `semear()` não define idempotência nem o comportamento quando o banco já contém dados |
| F-47 | autoridade | 🟡 | `resolver(...) -> { permitido: true, … } \ | ErroSoD` não define se o erro é lançado ou retornado. Duas implementações corretas do mesmo contrato — uma que lança, outra que retorna — são incompatíveis com o mesmo consumidor |
| F-48 | sqlite-adaptador | 🟡 | Nenhum comportamento definido para arquivo de banco ausente, corrompido, sem permissão de escrita ou disco cheio. `abrir()` falha e o servidor faz o quê? |
| F-49 | trilha | 🟡 | A rastreabilidade que as referências de SoD/SOX descrevem pressupõe trilha à prova de adulteração. INV-8 é imposto só por disciplina de código (o repositório não expõe UPDATE); qualquer acesso direto ao arquivo SQLite reescreve tudo. Sem encadeamento por hash nem WORM, "imutável" é alegação fraca |
| F-50 | casos-de-uso | 🟡 | O solicitante não tem ação de cancelar a própria despesa pendente. O único caminho de saída é um aprovador rejeitar — não há saída pelo lado de quem criou |
| F-51 | trilha | 🟡 | A decisão grava `em_nome_de_id` mas não `delegacao_id`, e os eventos de delegação vivem em tabela separada. Reconstruir "sob qual delegação B agiu" exige cruzar duas trilhas por instante — atribuição incompleta exatamente no ponto que o produto existe para provar |
| F-52 | casos-de-uso | 🟡 | Depende de todos os oito módulos de núcleo. Ponto único por onde passa todo fluxo — sem regra que impeça, cresce para god module |
| F-53 | ui-web | 🟡 | `render(template, dados)` escapa todos os valores de `dados`, mas não distingue **fragmento de template** de **dado**: uma tela composta por sub-templates teria o HTML dos filhos escapado. Duas implementações fiéis ao contrato produzem páginas diferentes |
| F-54 | bandeja | 🟢 | o trabalho por render é proporcional ao tamanho da fila, não ao que mudou desde o último render |
| F-55 | trilha | 🟡 | `registrar(evento)` não define o tipo `Evento`: quais campos são obrigatórios por tipo de evento. O modelo de dados tem as colunas, o contrato do módulo não |
| F-56 | api-http | 🟡 | R5 tirou a identidade do cookie e a pôs em campo explícito, o que elimina CSRF — mas `GET /bandeja` é um link, logo a identidade viaja na query string: a URL vira credencial portátil, guardada em histórico, favoritos e no cabeçalho `Referer` de qualquer link externo |
| F-57 | dominio-delegacao | 🟡 | Revogação concorrente a uma decisão em andamento não tem ordem definida: B clica aprovar enquanto A revoga. Qual dos dois vence, e o que a trilha registra? |
| F-58 | casos-de-uso | 🟡 | Transação que falha por `SQLITE_BUSY` não tem política: repetir, falhar, com que mensagem? A arquitetura promete "erro de conflito determinístico" sem definir a resposta |
| F-59 | api-http | 🟡 | Formulários POST sem token anti-CSRF: com identidade em cabeçalho ou cookie simulado, uma página externa dispara aprovação em nome do usuário logado |
| F-60 | bandeja | 🟡 | R8 reduziu `bandeja` a `autoridade` + `portas-repositorio`, mas `resolver` agora exige `decisoesDaDespesa`: para montar a bandeja é preciso ler a trilha de cada pendente, logo `bandeja` depende de `TrilhaRepo` — dependência real não declarada |
| F-61 | bandeja | 🟡 | Quatro dependências (M-02, M-03, M-04, M-08) e duas responsabilidades: consultar pendências e decidir visibilidade por delegação. É o módulo mais acoplado do desenho |
| F-62 | dominio-delegacao | 🟡 | INV-16 (`inicio >= agora`) assume que o formulário envia instante comparável ao relógio. A tela T5 pede DATA, sem hora nem fuso: "hoje" comparado contra um `agora()` em UTC pode dar passado e recusar uma delegação legítima criada de manhã |
| F-63 | ui-web | 🟡 | Não há aviso de vigência prestes a terminar nem de pendências devolvidas. Como notificação está fora de escopo, o delegante descobre por acaso que voltou a ter itens |
| F-64 | ui-web | 🟡 | As 4 mensagens de SoD (CA-6) têm `codigo` e `mensagem` no contrato, mas nada garante que sejam acionáveis para um não-técnico: dizem o que foi bloqueado, não o que fazer em seguida |
| F-65 | trilha | 🟡 | Nenhuma política de retenção: SOX exige prazo definido de guarda, e o desenho não tem nem prazo nem módulo responsável |
| F-66 | matriz-doa | 🔴 | A1 (hierarquia linear, ordenada, sem lacunas) não é verificada em lugar nenhum. Um seed com dois papéis no mesmo nível, ou com níveis 1 e 3 sem o 2, produz cadeia silenciosamente errada — nenhum módulo valida a matriz na carga |
| F-67 | relogio | 🟡 | Reiniciar o processo com offset **menor** move o tempo para trás e reabre vigências encerradas: a oscilação que CTRL-02 apontava volta pela porta do reinício. O relógio é monótono dentro do processo, não entre processos |
| F-68 | relogio | 🟢 | `Instante` é tipo abstrato no contrato e `TEXT` ISO-8601 no modelo de dados: duas representações do mesmo conceito, sem regra de conversão declarada |
| F-69 | casos-de-uso | 🔴 | Não há regra para o nível que se torna inelegível **durante** a cadeia. Na criação o nível tinha titular; ao chegar nele, INV-4 barra o único elegível. Pula, como o nível vazio? Trava? Volta? S1.2 definiu o pulo só para o caso "sem titular", e este caso não é esse |
| F-70 | bandeja | 🟢 | A7 foi quantificada em ~1.000 despesas, mas nada em runtime verifica ou sinaliza a ultrapassagem — a premissa continua sendo uma frase, não um limite |
| F-71 | portas-repositorio | 🟡 | `DespesaRepo.pendentesDe(nivel)` é ambíguo entre "pendentes NO nível k" e "pendentes ATÉ o nível k", e não recebe usuário — logo não serve à bandeja, que é seu único consumidor previsto |
| F-72 | matriz-doa | 🔴 | V(2) mudou a assinatura para `cadeiaPara(valor, papelSolicitante, titulares)`: o módulo de domínio passou a precisar de dado de USUÁRIO para decidir (INV-15), mas seu `depends-on` continua `—`. A mesma contradição que ARQ-01 corrigiu em `autoridade` reapareceu em `matriz-doa`, criada pela própria correção |
| F-73 | trilha | 🟡 | S5 fez `registrar` devolver `Resultado`, mas nada obriga `casos-de-uso` a tratá-lo: um `Resultado` ignorado dentro da transação perde o evento de trilha enquanto a decisão é gravada — exatamente a divergência que INV-8 existe para impedir |
| F-74 | dominio-delegacao | 🟡 | Com S2, o item que o delegado não pode decidir volta a esperar o delegante — que está ausente, que é o motivo de existir a delegação. A delegação falha **em silêncio** para aquele item, sem sinal para nenhum dos dois |
| F-75 | dominio-delegacao | 🟡 | Nada impede criar delegação com `inicio` no passado. Não retroage decisões já tomadas, mas produz vigência antedatada que a auditoria não consegue distinguir de uma delegação legítima esquecida |
| F-76 | bandeja | 🟡 | `listar` recalcula a cadeia (M-02) e resolve autoridade (M-04) para cada pendência; como INV-4 exige ler a trilha de cada despesa, o custo é O(n·m) por carregamento de tela, no caminho mais quente do sistema |
| F-77 | dominio-delegacao | 🟡 | S2 dá ao delegante uma jogada nova: delegar a alguém inelegível para certos itens retém esses itens consigo enquanto o sistema o exibe como delegado — parecer ausente e continuar decidindo o que interessa |
| F-78 | matriz-doa | 🟡 | INV-15 recusa a despesa quando um papel da cadeia está sem titular: o controle NEGA o gasto em vez de escalar. Nenhuma prática de DoA das fontes levantadas bloqueia despesa por assento vago — a convenção é pular o nível vazio e escalar ao seguinte. O desenho inventou um bloqueio que o domínio não pratica |
| F-79 | bandeja | 🟢 | A7 ("volume pequeno, dezenas a centenas") não tem número, logo não é testável nem falseável |
| F-80 | casos-de-uso | 🔴 | S1.3 corrigiu ARQ-06 empurrando a decisão de elegibilidade de `matriz-doa` para `casos-de-uso` — ou seja, tirou uma invariante SoD do domínio e a pôs na camada de aplicação. Isso viola o padrão **Domain Model** escolhido na Fase 1 ("as invariantes moram nos objetos de domínio"). A correção trocou uma contradição de contrato por uma violação de padrão |
| F-81 | trilha | 🟡 | retenção infinita por desenho; o custo de armazenamento cresce linearmente com o uso sem valor proporcional após anos |
| F-82 | api-http | 🟡 | `POST /relogio/avancar` é rota de produção sem qualquer definição de como fica desabilitada fora de teste/demonstração |
| F-83 | dominio-delegacao | 🟡 | O delegante escolhe o delegado. INV-2 impede auto-aprovação, mas nada impede escolher um delegado complacente para as despesas da própria área, nem o par recíproco A↔B em que cada um exerce a autoridade do outro. O desenho assume cooperação onde há incentivo a defecção |
| F-84 | autoridade | 🔴 | A3 (matriz imutável durante a vida da despesa) é premissa não imposta. Se `semear()` reescrever limites com despesas pendentes, a cadeia delas muda retroativamente e INV-6 (autoridade no instante do ato) é violada sem que nada detecte |
| F-85 | ui-web | 🟡 | Rejeição é terminal e irreversível (INV-11), e a UI não prevê confirmação: um clique errado encerra a despesa para sempre, sem desfazer |
| F-86 | api-http | 🔴 | O duplo envio de S4 usa **o id do usuário** como valor a conferir — e esse id é público: a tela T1 lista todos. Defesa de duplo envio exige valor imprevisível; com valor adivinhável, uma página externa monta o formulário com o id certo e, batendo com o cookie da vítima, o POST passa. **CSRF volta**, agora com aparência de defesa |
| F-87 | matriz-doa | 🔴 | S1.2 (pular nível sem titular) **quebra CA-1**. O critério de aceite diz "despesa que exige N níveis percorre exatamente N aprovações"; com um nível pulado, o número de aprovações deixa de ser `\ | cadeia\ | ` e CA-1 passa a ser inverificável como está escrito. Ou CA-1 é reescrito, ou a regra do pulo é |
| F-88 | ui-web | 🟢 | Sem indicação persistente de "quem sou eu agora" em todas as telas, o usuário age como outra pessoa sem notar — agravado por não haver autenticação |
| F-89 | matriz-doa | 🟡 | INV-15 cria um incentivo novo na mesma direção: com o assento de Gerente vago, a saída para o solicitante é declarar valor abaixo do limite do próprio nível e evitar a cadeia inteira |
| F-90 | relogio | 🟡 | `T27_RELOGIO` com valor ausente, mal formado ou fora de faixa não tem comportamento definido: o processo sobe com `Invalid Date` e toda comparação de vigência passa a ser falsa em silêncio |
| F-91 | api-http | 🟢 | Sem limite de tamanho de corpo nem timeout definidos; uma descrição de despesa de 10 MB entra na trilha para sempre |
| F-92 | bandeja | 🔴 | a posse da pendência é estado derivado (matriz + delegações + relógio) e nunca é reconciliada com o que a trilha registrou. Não há sinal de erro nem malha de correção: se derivação e trilha divergirem, nada detecta |
| F-93 | api-http | 🔴 | A identidade atuante vem do cliente sem verificação: qualquer chamador age como qualquer usuário e toda invariante SoD é contornável em uma requisição. JÁ ACEITO explicitamente pelo operador na Fase 1 (premissa A5) — o sistema impõe SoD contra engano, não contra adversário |
| F-94 | bandeja | 🟡 | o custo O(n·m) deixou de ser consequência de implementação e virou exigência de contrato: `resolver` só decide com `decisoesDaDespesa` em mãos, então nenhuma implementação da bandeja pode evitar ler a trilha de cada pendente |
| F-95 | ui-web | 🟡 | R5 promete "escape por padrão", mas template de string em TypeScript não escapa nada: `${x}` interpola cru. "Por padrão" não é propriedade da linguagem — sem um mecanismo nomeado (template marcado, ou uma função de render que escapa e nunca expõe caminho cru), a promessa é uma intenção que o primeiro `${}` esquecido derruba |
