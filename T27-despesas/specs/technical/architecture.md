# Arquitetura — T27 (fila de aprovação de despesas com alçadas e delegação temporária)

Fase 1, iteração 1. Padrões: **Hexagonal (Ports & Adapters)**, **KISS + YAGNI** (único
princípio transversal selecionado), **Domain Model**, **Repository (porta) + mapeamento
manual**, **nenhum padrão GoF**, concorrência **single-threaded + transação SQLite com
leitura-para-atualização**.

Stack: TypeScript · Fastify · better-sqlite3 · UI server-rendered · Vitest.

---

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

**Regra de dependência (hexagonal):** M-01 a M-08 são o núcleo e não importam nada de
M-09, M-11 nem M-12. As setas de dependência apontam sempre para dentro. `autoridade`
(M-04) é deliberadamente o único ponto de cruzamento entre alçada e delegação.

**Granularidade (E = I₀/C):** cada módulo é implementável em uma única interação tendo em
contexto apenas este documento + a interface dos módulos de que depende.

---

## Invariantes por módulo

| Invariante | Módulo guardião |
|---|---|
| INV-1 `valor ≤ limite` (fronteira inclusiva) | M-02 |
| INV-2 ninguém aprova a própria despesa | M-04 |
| INV-3 delegação não transitiva | M-03 |
| INV-4 mesmo ator não decide duas vezes na mesma cadeia | M-04 |
| INV-5 sem vigências sobrepostas do mesmo delegante | M-03 |
| INV-6 autoridade avaliada no instante do ato | M-04 |
| INV-7 decisão grava ator / em-nome-de / limite exercido | M-06 |
| INV-8 trilha append-only | M-06 |
| INV-9 rejeição exige motivo | M-01 |
| INV-10 valor acima do teto máximo recusado na criação | M-02 |
| INV-11 rejeição é terminal | M-01 |
| INV-12 dinheiro em inteiro de centavos | M-01 |
| **INV-13** solicitante do papel de topo é recusado na criação (não há autoridade acima) | M-02 |

INV-13 nasceu nesta fase: a decomposição de M-02 expôs que "a cadeia começa acima do papel
do solicitante" não tem resposta quando o solicitante ocupa o topo. Resolvido por decisão
do operador, pela mesma lógica de INV-10 — nunca existe pendência sem aprovador possível.

---

## Premissas (AP4 — o que o sistema assume como verdadeiro)

| id | Premissa | Consequência se for falsa |
|---|---|---|
| A1 | a hierarquia de papéis é linear, ordenada e sem lacunas | a cadeia de M-02 fica indefinida |
| A2 | cada usuário ocupa exatamente um papel, imutável durante o ciclo | o limite exercido registrado em INV-7 vira ambíguo |
| A3 | a matriz DoA não muda durante a vida de uma despesa (seed fixo) | INV-6 exigiria versionar a matriz e resolver retroatividade |
| A4 | um único processo escreve no banco | a trava por transação deixa de bastar; precisaria de trava otimista por versão |
| A5 | **a identidade informada é confiável (sem autenticação)** | **toda invariante SoD é contornável por quem chame a API direto — ACEITA EXPLICITAMENTE: o sistema impõe SoD contra engano, não contra adversário** |
| A6 | instantes em UTC, relógio monotônico | vigências de delegação ficam ambíguas na fronteira |
| A7 | volume pequeno (dezenas a centenas de despesas) | a bandeja sem paginação degrada |
| A8 | delegação é global e no máximo uma ativa por delegante | M-04 teria de escolher entre delegações concorrentes |

---

## Escopo negativo (o que o sistema deliberadamente NÃO faz)

Não autentica (A5) · não notifica (e-mail/push) · **não agenda nada** — sem cron nem timer:
a expiração de delegação é avaliada sob demanda contra o relógio, no momento em que a
bandeja é montada ou a decisão é tentada · não edita a matriz DoA em runtime · não pagina
nem oferece busca · não versiona API pública · não é multi-tenant · não anexa arquivos ·
não converte moeda · não permite delegação transitiva (INV-3) · não permite override
administrativo em despesa travada · não escalona por tempo/SLA.

---

## V(2) — Simplificação (Fase 3, iteração 1)

Resposta unificada aos 57 achados de V(1). Princípio: cada correção **remove** algo
(uma rota, um tipo de evento, uma dependência, um parâmetro ambíguo) ou **converte uma
premissa declarada em verificação executada**. Nenhum módulo foi acrescentado — os 12
nomes permanecem os mesmos, que é o que preserva a rastreabilidade da matriz.

### Os 8 movimentos

**R1 — Premissa declarada vira verificação executada** (responde à falha sistêmica da
análise de concentração: `Assumptions` atingiu 6 de 12 módulos). A matriz DoA é validada
UMA VEZ na carga e fica imutável em memória; `semear()` só roda em banco vazio. O processo
não sobe com matriz inválida. *Resolve A-01, A-02, IMP-05.*

**R2 — A cadeia deixa de ser ambígua e passa a ser função total.**
`cadeia(valor, papelSolicitante) = [ p : nivel(p) > nivel(papelSolicitante) e nivel(p) <= nivel(p*) ]`,
em ordem crescente de nível, onde `p*` é o **menor** papel cujo `limite >= valor`. O papel
final está incluído. `N` de CA-1 = `|cadeia|`. *Resolve IMP-01 e LING-02 (mesma ambiguidade).*

**R3 — Estado derivado deixa de ter sósia gravado.** O evento
`DEVOLVIDA_AO_DELEGANTE` é **removido**. A posse da pendência é 100% derivada de
(estado + delegações + relógio) — uma fonte de verdade só, portanto nada com que discordar.
Em compensação, a decisão grava `delegacao_id`: a atribuição fica completa em uma coluna,
sem cruzar duas trilhas. *Resolve PROC-02, CTRL-01 (duplicata) e GOV-01.*

**R4 — O relógio sai da superfície HTTP.** `POST /relogio/avancar` é **removido**. O tempo
é controlado por injeção direta nos testes e, na demonstração manual, pela variável de
ambiente `T27_RELOGIO=<ISO-8601>` lida na inicialização. Como só se fixa no boot, o relógio
é monótono dentro do processo. A porta de produção `Clock` expõe apenas `agora()`;
`avancar`/`fixarEm` vivem só no adaptador de teste, que não implementa a porta de produção.
*Resolve SEC-02, IMP-04, GOV-03, CTRL-02, ARQ-04 e A-04.*

**R5 — Uma borda, não N defesas.** `api-http` resolve e valida o usuário atuante em um
único ponto (id inexistente → 404, antes de qualquer caso de uso), aplica limite de tamanho
de corpo, e o renderizador de `ui-web` **escapa por padrão** — escape é a operação normal,
não uma chamada que se pode esquecer. A identidade vai explícita em cada requisição (campo
do formulário), **não em cookie de sessão**: sem cookie ambiente, o vetor CSRF clássico
deixa de existir por construção, sem token novo. `portas-repositorio` passa a exigir
prepared statements no contrato. *Resolve SEC-03, SEC-04, SEC-05, RES-03 e A-05.*

**R6 — A promessa é rebaixada ao que o código sustenta.** Nada de hash encadeado (seria
complexidade nova para um requisito que ninguém pediu). O documento passa a dizer o que é
verdade: INV-8 é *append-only pela aplicação* — `TrilhaRepo` não expõe caminho de UPDATE
nem DELETE —, e **não há proteção contra adulteração do arquivo SQLite por fora**. Retenção
ilimitada, sem expurgo, é decisão consciente justificada por A7. *REG-01, REG-02 e SUS-01
aceitos com justificativa registrada, não corrigidos por código.*

**R7 — Uma convenção de contrato, não N esclarecimentos.** Todo o núcleo (M-01..M-08)
**retorna** `Resultado<T, ErroDominio>` e **nunca lança**; exceção existe só na borda de
infraestrutura. `Instante` é `string` ISO-8601 UTC — um tipo só, sem conversão.
`Evento` é união discriminada com campos obrigatórios declarados por variante.
`DespesaRepo.pendentesDe(nivel)` é substituído por `pendentes()` (o parâmetro ambíguo
some; sob A7 a filtragem é em memória). `autoridade` **não depende de `trilha`**: recebe
`decisoesDaDespesa` por parâmetro, e o `depends-on` passa a dizer a verdade.
`dominio-delegacao` não depende de `relogio` — `Instante` é primitivo.
*Resolve LING-01, LING-03, LING-04, IMP-02, ARQ-01 e ARQ-05.*

**R8 — Acoplamento reduzido onde havia concentração.** Com R3 e R7, `bandeja` cai de 4
dependências para 2 e volta a ter uma responsabilidade: filtrar `pendentes()` por
`autoridade.resolver(...).permitido`. *Resolve ARQ-02.* `casos-de-uso` continua dependendo
do núcleo inteiro — é a camada de aplicação por definição, e 7 funções curtas cabem em uma
interação; dividi-la seria complexificar (AP2). *ARQ-03 aceito com justificativa.*

### Novas invariantes (nascidas da crítica, não de escopo novo)

| id | invariante | módulo guardião |
|---|---|---|
| INV-14 | a matriz DoA é válida: níveis contíguos a partir de 1, únicos, e limites estritamente crescentes com o nível — verificado na carga; o processo não sobe se falhar | matriz-doa |
| INV-15 | toda cadeia exigida tem titular: se algum papel da cadeia não tem nenhum usuário, a criação da despesa é recusada com mensagem explícita | matriz-doa |
| INV-16 | delegação não pode ser antedatada: `inicio >= agora` no momento da criação | dominio-delegacao |

INV-15 fecha a última porta do estado órfão (PROC-01): INV-10 tratava valor acima do teto,
INV-13 tratava solicitante no topo, e faltava o papel existente sem nenhuma pessoa.

### Módulos V(2)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

### Premissas revisadas

| id | Premissa | Estado em V(2) |
|---|---|---|
| A1 | hierarquia linear, ordenada, sem lacunas | **deixou de ser premissa** — virou INV-14, verificada na carga |
| A2 | um papel por usuário, imutável no ciclo | premissa mantida (seed fixo) |
| A3 | matriz imutável durante a vida da despesa | **deixou de ser premissa** — imposta por R1 (imutável em memória, seed só em banco vazio) |
| A4 | processo único escrevendo no banco | premissa mantida e agora explícita: com um processo, `SQLITE_BUSY` não ocorre (resposta a RES-02) |
| A5 | identidade informada é confiável | premissa mantida, **aceita explicitamente** pelo operador (SEC-01) |
| A6 | instantes UTC, relógio monotônico | **reforçada** por R4: o relógio só é fixado no boot, logo é monótono no processo |
| A7 | volume pequeno | **quantificada**: até ~1.000 despesas e ~100 usuários. Acima disso, PERF-01 (custo O(n·m) por render da bandeja) degrada de forma aceita e documentada (resposta a A-06) |
| A8 | delegação global, no máximo uma ativa por delegante | premissa mantida (INV-5) |

---

## V(3) — Simplificação (Fase 3, iteração 2)

Resposta aos 21 achados de V(2). A iteração 2 mostrou que 5 dos 6 críticos foram
**regressões criadas pelas correções de V(2)**. A conclusão que governa esta rodada:
V(2) respondeu acrescentando regras (INV-14, INV-15, INV-16, uma variável de ambiente).
V(3) responde **revogando** uma regra, **corrigindo** uma fórmula e **unificando** três
mecanismos em um. Nenhum mecanismo novo entra.

### Os 5 movimentos

**S1 — A cadeia deixa de negar e volta a escalar; e volta a ser função de dado de domínio
puro.** Três mudanças que são uma só ideia:

1. *A fórmula é corrigida.* `p*` é o menor papel **acima do solicitante** cujo `limite >= valor`
   — a âncora estava errada em V(2), e por isso a cadeia era vazia quando a alçada do próprio
   papel do solicitante já cobria o valor:
   ```
   cadeia(valor, papelSolicitante) =
     papéis p com nivel(p) > nivel(papelSolicitante), em ordem crescente de nível,
     até e incluindo o primeiro p com limite(p) >= valor
   ```
   A cadeia **nunca é vazia**: ou tem ao menos um papel, ou o resultado é
   `ErroSemAutoridadeAcima` (INV-13) / `ErroAcimaDoTeto` (INV-10). *Resolve IMP-06, PROC-07.*
2. *INV-15 é REVOGADA.* Nível intermediário sem aprovador elegível é **pulado**, não bloqueia
   — é o que a prática de DoA levantada em `specs/references` de fato faz. A recusa passa a
   existir só quando o **último** papel da cadeia (o que cobre o valor) não tem aprovador
   elegível, e a mensagem diz a verdade em vez de mandar pedir o impossível.
   *Resolve REG-04, UX-07 e a parte de criação de PROC-06.*
3. *`titulares` sai da assinatura.* Com INV-15 revogada, `cadeiaPara` volta a ser função de
   (valor, papel) — dado de domínio puro. Quem sabe de pessoas é `casos-de-uso`, que consulta
   elegibilidade nível a nível. *Resolve ARQ-06 — a contradição que R1 havia recriado.*

**S2 — Delegação é caminho adicional, não transferência de posse.** Quando o delegado é
inelegível para um item específico (INV-2 ou INV-4), aquele item **permanece com o
delegante** em vez de sumir da fila de todo mundo. Nenhum mecanismo novo: é a mesma
`resolver()` respondendo por dois usuários em vez de um. *Resolve a parte de decisão de
PROC-06 — o órfão que a delegação reabria.*

**S3 — O relógio deixa de ser fixável e passa a ser deslocável.** `T27_RELOGIO` (instante
fixo) é substituída por `T27_RELOGIO_OFFSET_MS` (inteiro): `agora() = relógio real + offset`.
O relógio **volta a andar** — cronologia preservada, FIFO bem definido, vigências expiram
sozinhas — e a demonstração de expiração é feita reiniciando com offset maior. Offset ausente
é 0; offset mal formado impede a subida do processo, igual à matriz inválida (INV-14).
Toda data de vigência trafega com hora e fuso, ou é normalizada para `00:00Z` do dia
escolhido, regra escrita no contrato. *Resolve CTRL-03, RES-04 e A-07.*

**S4 — Identidade: cookie para navegar, campo para escrever, igualdade exigida.** O cookie
carrega a identidade corrente (some da query string, some do histórico e do `Referer`);
todo POST envia o mesmo valor em campo e o servidor **exige que os dois coincidam** — a
defesa clássica de duplo envio, uma comparação. Um só mecanismo resolve os dois lados sem
reabrir CSRF. *Resolve SEC-06, UX-06 e mantém SEC-03 resolvido.*

**S5 — A convenção de contrato passa a valer sem exceção.** `registrar(evento)` retorna
`Resultado<void, ErroPersistencia>` como todo o resto do núcleo (*resolve LING-05*), e o
"escape por padrão" ganha o mecanismo que faltava: a renderização é **uma única função
`render(template, dados)` que escapa todos os valores de `dados`** — não há caminho de
interpolação crua exposto, portanto não há `${}` a esquecer. *Resolve IMP-07.*

### Aceitos com justificativa nesta rodada

| id | por quê |
|---|---|
| GOV-04 | a informação está completa (vigência gravada + instante da decisão); falta apenas pré-computada. Registrar o evento exigiria o agendador que o escopo negativo exclui — a resposta é a mesma de R6: não prometer o que o código não sustenta |
| A-08 | A7 é premissa de operação, não invariante de runtime; verificar volume em código seria mecanismo novo para um limite que ninguém vai cruzar em uma sessão |
| PERF-04, SUS-03 | duplicatas de PERF-01, já aceito sob A7 quantificada |
| GOV-05, GT-04 | duplicatas de GOV-02 e GT-02, ambos já aceitos pelo operador |
| SCI-04 | **resolvido**, não aceito: o mapeamento DW-RBAC → `resolver()` foi escrito em `specs/technical/dw-rbac-mapeamento.md` |

### Invariantes em V(3)

INV-1 a INV-13 permanecem. **INV-14** permanece (matriz válida na carga).
**INV-15 é REVOGADA** — substituída pela regra de pular nível vazio (S1.2).
**INV-16** permanece, agora com a regra de normalização de fuso de S3.
**INV-17 (nova, de S1.2):** a despesa só é recusada por falta de aprovador quando o
**último** papel da cadeia não tem nenhum aprovador elegível.

### Módulos V(3) — o que mudou em relação a V(2)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

---

## V(4) — Simplificação (Fase 3, iteração 3)

Resposta aos 17 achados de V(3). Diagnóstico da rodada: os 5 críticos são **quatro
escolhas que V(3) deixou em aberto e uma regra que faltou** — não falhas estruturais.
V(4) faz as escolhas e devolve ao domínio o que V(3) tinha empurrado para fora dele.

### Os 5 movimentos

**T1 — "Elegível" tem uma definição só, e ela mora no domínio.** Um nível é **decidível**
por `u` no instante `t` se e somente se `autoridade.resolver(...)` devolve sucesso para
`u`. Não existe segundo conceito. A pergunta "existe alguém que decida este nível?" vira
`autoridade.algumDecisor(despesa, nivel, titulares, decisoes, delegacoes, instante)` —
**em `autoridade`, não em `casos-de-uso`**: a invariante SoD volta para o domínio, e a
mesma função responde na criação e na decisão, com os dados de cada momento.
*Resolve LING-07, ARQ-08 (desfaz o deslocamento de S1.3) e A-09.*

**T2 — O pulo permanece, mas passa a ser registrado, generalizado e reconciliado com CA-1.**
Três amarrações de uma regra só:
1. Ao chegar ao nível `k`, se `algumDecisor` é falso, o nível é pulado — **em qualquer
   momento e por qualquer causa** (papel vago, INV-2 ou INV-4). Uma regra, avaliada sempre
   no ato, coerente com INV-6. *Resolve PROC-08.*
2. Todo pulo grava `NIVEL_PULADO(nivel, motivo)` na trilha. *Resolve GOV-06.*
3. **CA-1 é reescrito** (critério de aceite da Fase 0 — exige aprovação do operador):
   a despesa percorre exatamente os níveis da cadeia **que têm decisor**, e cada nível
   pulado aparece na trilha com o motivo. `N` = quantidade de níveis com decisor.
   *Resolve IMP-08 e REG-05.*
4. **INV-18 (nova):** a despesa só chega a APROVADA com **pelo menos uma aprovação humana
   registrada**. Se nenhum nível da cadeia tem decisor, a criação é recusada (INV-17
   generalizada). Isto é o que impede o pulo de degradar quatro olhos a zero olhos.

**T3 — O anti-CSRF passa a usar valor imprevisível.** O cookie deixa de carregar
identidade e passa a carregar **apenas um nonce aleatório**; todo POST envia o mesmo nonce
em campo e o servidor exige igualdade. Mesma quantidade de mecanismo de S4, com o valor
certo: o id do usuário é público (T1 o lista) e nunca serviu como token.
*Resolve SEC-07.*

**T4 — Identidade volta a ser por requisição.** Com o cookie ocupado só pelo nonce, a
identidade viaja em campo/parâmetro `u` a cada requisição — **duas abas, dois usuários**,
que é o que CA-3, CA-3b e o teste manual de CA-11 exigem. Uma URL vazada revela sob qual
identidade se navegava, mas **não permite escrever**, porque escrever exige o nonce do
cookie, que nenhuma página externa lê. *Resolve UX-08 e reduz SEC-06 a exposição de
identidade, coerente com A5.*

**T5 — As três amarras de contrato que sobraram.**
- `registrar` é chamado **dentro** de `emTransacao`, e seu `Resultado` de erro **aborta a
  transação inteira**: não existe decisão gravada sem trilha. *Resolve RES-05.*
- `render` ganha um tipo `Html` marcado: valores do tipo `Html` (produzidos por `render`
  aninhado) não são escapados; todo o resto é. Sub-templates deixam de ser ambíguos.
  *Resolve LING-06.*
- `validar` passa a cobrir o seed de usuários: todo usuário aponta para papel existente
  na matriz. *Resolve A-10.*

### Aceitos com justificativa nesta rodada

| id | por quê |
|---|---|
| CTRL-04 | o offset é ferramenta de demonstração operada pelo próprio operador; mover o tempo para trás entre reinícios é ação deliberada dele, não falha do sistema. Persistir o último offset seria mecanismo novo para impedir o operador de fazer o que quis fazer |
| IMP-09 | **resolvido por documentação**, não aceito: o procedimento de reinício com offset foi escrito em `specs/design/telas.md` e vai no README |
| PROC-09, GT-05 | coerentes com GT-01, já aceito pelo operador: o sistema não restringe para quem se delega, e não sinaliza que uma delegação foi inócua para um item |
| PERF-05, SEC-06 | 🟢/🟡 residuais sob A7 e A5 |

### Invariantes em V(4)

INV-1..INV-14, INV-16, INV-17 permanecem. INV-15 segue revogada.
**INV-18 (nova):** APROVADA exige ao menos uma aprovação humana registrada.

### Módulos V(4) — o que mudou em relação a V(3)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

---

## Correção do `depends-on` (Fase 5, S7 — divergência encontrada na micro-verificação)

A implementação expôs uma dependência real não declarada, exatamente da classe de ARQ-06 e
ARQ-07. Registrada aqui em vez de escondida:

| módulo | `depends-on` declarado em V(4) | dependência REAL no código | correção |
|---|---|---|---|
| `bandeja` | autoridade, portas-repositorio | + `matriz-doa` — `listar` precisa de `cadeiaPara` para saber qual papel decide cada pendência | **o documento passa a declarar `matriz-doa, autoridade, portas-repositorio`** |

Não é acoplamento novo: `bandeja` sempre precisou da cadeia; V(2)/R8 reduziu suas
dependências de 4 para 2 contando errado. Três dependências, uma responsabilidade — a
redução real de R8 foi de 4 para 3.

## Divergências código × specs corrigidas na Fase 5 (S7)

| # | divergência | correção |
|---|---|---|
| 1 | `solicitar` registrava `NIVEL_PULADO` **antes** de gravar a despesa; `evento_trilha.despesa_id` tem FK para `despesa(id)` com `PRAGMA foreign_keys=ON` → a criação com nível pulado falharia | despesa gravada primeiro, dentro da mesma transação; a recusa por INV-17 continua revertendo tudo |
| 2 | INV-16 comparava `inicio` (instante completo) com `agora.slice(0,10)` (só a data) — funcionava por acidente da ordem lexicográfica | ambos os lados normalizados para a data: `inicio.slice(0,10) < agora.slice(0,10)` |
| 3 | `api-http` exportava `novoId` e `delegacaoDom` sem consumidor | exports removidos |

---

## Decisões finais e alternativas descartadas (Fase 7)

Estado entregue: **V(4)**, 12 módulos, 2.076 LOC em `src/`, 43 testes verdes.
As seções V(1) a V(3) acima são **histórico** — a especificação vigente é V(4) mais as
correções de `depends-on` e as divergências registradas na Fase 5.

### Alternativas avaliadas e descartadas, com o motivo

| Alternativa | Onde foi avaliada | Por que foi descartada |
|---|---|---|
| React SPA + Vite | Fase 0, tabela de stacks | ~60% mais LOC e toolchain de build; o esforço migraria da regra de alçada para o encanamento |
| Python + FastAPI | Fase 0, tabela de stacks | equivalente em porte; a escolha foi por fluência do operador, que também executa o teste manual |
| `node:sqlite` (embutido no Node 24) | Fase 5, ao falhar a instalação | trocaria a lib aprovada em P1 por uma API experimental; subir `better-sqlite3` de 9 para 13 preserva a decisão |
| Playwright | Fase 6, ferramenta de UI | UI sem JS de cliente: ~200 MB de navegadores para exercitar pouco além do que `fastify.inject()` cobre |
| Padrões GoF (Strategy, State, Specification) | Fase 1 | sob KISS+YAGNI, nenhum se pagava: o domínio é regra + máquina de estados de 3 estados |
| Hash encadeado na trilha | Fase 3, R6 | mecanismo novo para requisito que ninguém pediu; a promessa foi rebaixada ao que o código sustenta |
| INV-15 (bloquear por papel sem titular) | criada em V(2), revogada em V(3) | nenhuma prática de DoA bloqueia gasto por assento vago; a convenção é pular e escalar |
| Papel "Conselho" acima do Diretor | Fase 1, lacuna do topo | empurra o problema um nível acima sem resolvê-lo |
| Aprovação por par do mesmo nível | Fase 1, lacuna do topo | segundo modo de roteamento em `matriz-doa` e `autoridade` — superfície extra sob KISS |
| Trava otimista por versão | Fase 1, concorrência | a transação síncrona do `better-sqlite3` em processo único já dá conflito determinístico (A4) |
| Persistir o último offset de relógio | Fase 3, CTRL-04 | mecanismo novo para impedir o operador de fazer algo deliberado |

### Versões fixadas e por quê

`better-sqlite3` **13.0.3** (a 9.x não tem prebuild para Node 24; `node-gyp` falha),
`fastify` **5.2** com `@fastify/formbody` **8** e `vitest` **3.0.5** — as versões anteriores
somavam 6 vulnerabilidades no `npm audit`, uma crítica. Resultado final: **0 vulnerabilidades**.
