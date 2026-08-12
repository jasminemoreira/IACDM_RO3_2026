# Matriz de cobertura — achados da crítica adversarial

## Iteração 1 — V(1)

Lentes aplicadas: 7 universais + 10 condicionais ativadas. Não ativadas:
Migration / Coexistence (greenfield), Observability / Operability (nó único
sem requisito operacional declarado).

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| PRE-01 | configuracao | Assumptions | 🔴 | assume-se que a matriz configurada é sempre válida. `derivar` faz consulta total sem fallback: célula ausente devolve `undefined`, que atravessa o sistema como se fosse Prioridade. Nada valida totalidade (9 células), monotonicidade nem domínio P1..P5 |
| PRE-02 | recurso | Assumptions | 🟡 | G5 calcula `agora − triadoEm` assumindo que `triadoEm ≠ null` quando o estado é TRIADO. O invariante `estado=TRIADO ⟹ triadoEm≠null` não está declarado em lugar nenhum |
| PRE-03 | relogio | Assumptions | 🟡 | assume-se relógio monotônico. Se `agora()` retroceder (ajuste NTP, mudança manual), um recurso prescrito volta a ser admissível e um chamado violado volta a não-violado |
| PRE-04 | chamado | Assumptions | 🟡 | assume-se que todos os solicitantes calibram urgência do mesmo modo. A urgência declarada é tratada como dado objetivo, mas é juízo subjetivo sem referência comum |
| PRE-05 | chamado | Assumptions | 🟢 | toda a regra de prazo depende de `abertoEm` ser imutável, o que nunca foi declarado como invariante |
| ARQ-01 | casos-de-uso | Architectural | 🟡 | depende de 9 dos 12 módulos. Impossível testar isolado; concentra transação, autorização, domínio e trilha. A regra "toda mudança gera trilha" mora aqui, não no domínio |
| ARQ-02 | ui-web | Architectural | 🟡 | `ui-web` depende de `api-http`, mas a UI é renderizada no servidor. Ou a UI chama casos-de-uso direto (e a dependência declarada está errada) ou faz HTTP para o próprio processo. A decomposição não resolve qual |
| ARQ-03 | trilha | Architectural | 🟡 | os eventos carregam `antes`/`depois` como json sem contrato. Sem esquema, o módulo não pode ser testado isoladamente contra nada |
| ARQ-04 | repositorio | Architectural | 🟡 | acumula portas, Data Mapper, esquema, seed e transação — cinco responsabilidades. O seed é dado de domínio morando na infraestrutura |
| ARQ-05 | chamado | Architectural | 🟢 | a entidade depende de `sla`, logo conhece o cálculo de prazos. Testar `chamado` sem `sla` é impossível |
| IMP-01 | casos-de-uso | Implementability | 🟡 | duplica: ARQ-01 — para implementar em sessão única é preciso o contrato de 9 módulos, o que estoura o princípio de granularidade E = I₀/C |
| IMP-02 | ui-web | Implementability | 🟡 | 6 telas especificadas sem declarar motor de template nem como o papel da sessão chega à página. Não implementável em sessão única sem decidir isso antes |
| IMP-03 | sla | Implementability | 🟡 | `somarHoras` aparece em specs/examples mas não pertence a nenhum dos 12 módulos da tabela de arquitetura |
| CIE-01 | configuracao | Scientific | 🟡 | o prazo de 48 h para recorrer foi justificado por caber no SLA de P3/P4, e aplicado uniformemente. Para P1 (resolve em 4 h) e P2 (8 h) o chamado estará encerrado muito antes de o prazo de recurso acabar — o parâmetro não vale na faixa onde foi aplicado |
| CIE-02 | configuracao | Scientific | 🟢 | "2 dias úteis → 48 h" foi obtido por 2×24, não por equivalência com a fonte F1. Dois dias úteis só equivalem a 48 h corridas se não houver fim de semana no meio |
| CIE-03 | prioridade | Scientific | 🟡 | a matriz 3×3 vem de F1, um blog de fornecedor (Tier B). Nenhum texto normativo ITIL 4 oficial foi lido — a afirmação "prática consolidada" repousa em convergência entre fornecedores, não em norma |
| SEG-01 | autorizacao | Security | 🔴 | sem autenticação (A8), `pode(usuario, …)` confia num usuário que o próprio cliente declara. Qualquer pessoa escolhe ser GESTOR e julga qualquer recurso. A autorização é real, mas decorativa |
| SEG-02 | ui-web | Security | 🔴 | justificativa e fundamentação são texto livre exibido nas 6 telas para os três papéis. Nenhuma decisão de design menciona escape na renderização → XSS armazenado |
| SEG-03 | api-http | Security | 🔴 | o design rejeita `prioridade` como entrada, mas nada impede enviar `impacto` no endpoint de abertura (onde só urgência é legítima) ou `urgencia` no de triagem. A separação de autoridade dos eixos — a descoberta central do projeto — não tem guarda declarada por endpoint |
| SEG-04 | casos-de-uso | Security | 🟡 | ids de chamado são sequenciais e `consultarChamado` não declara verificação de propriedade. Enumerar ids expõe chamados alheios (IDOR); a matriz de autorização diz "ver o próprio chamado" sem guarda correspondente no contrato |
| PER-01 | repositorio | Performance | 🟡 | a fila ordena por "violado primeiro", e `violado` é função de `agora` — não indexável. Cada render avalia todos os chamados abertos: O(n) por requisição, com n crescendo sem limite |
| PER-02 | trilha | Performance | 🟢 | `doChamado(id)` cresce sem limite e T-4 renderiza tudo, sem paginação. Um chamado longevo trava a própria tela |
| PER-03 | repositorio | Performance | 🟢 | better-sqlite3 é síncrono e o modelo é thread única: toda transação bloqueia o event loop. Irrelevante com 3 usuários, mas é o teto de escala do desenho |
| REG-01 | recurso | Regulatory | 🟡 | ISO 10002 (F6) exige informar o reclamante do recebimento e do desfecho. Notificações estão no escopo negativo e nenhum módulo é responsável por comunicar o desfecho — o solicitante precisa voltar à tela e descobrir sozinho |
| REG-02 | recurso | Regulatory | 🟡 | ISO 10002 exige prazo declarado por nível de escalonamento. O prazo de 24 h para julgar existe como número, mas não é guarda nem gera consequência: um recurso pode ficar ABERTO indefinidamente sem que nada aconteça |
| REG-03 | trilha | Regulatory | 🟡 | a trilha é imutável e sem política de retenção, contendo nome de pessoa e texto livre sobre problemas. Nenhum módulo tem responsabilidade por exclusão ou anonimização — direito ao esquecimento colide frontalmente com o invariante A4 |
| RES-01 | repositorio | Resilience | 🟡 | nada declara o comportamento sob SQLITE_BUSY, arquivo corrompido ou disco cheio. `emTransacao` falha e o design não diz o que a UI mostra nem se há repetição |
| RES-02 | configuracao | Resilience | 🟡 | o arquivo de configuração pode estar ausente ou malformado na inicialização. Não há default de emergência declarado nem falha explícita — o sistema sobe sem matriz |
| UX-01 | ui-web | UI/UX | 🟡 | T-3 mostra "Prioridade resultante: P4" antes de submeter. Ou o cálculo é ao vivo (exige JavaScript, contrariando "templates server-side sem cadeia de build") ou o agente tria às cegas. O design não escolhe |
| UX-02 | ui-web | UI/UX | 🔴 | não triados ficam em seção própria "porque não têm prioridade", e nada declara a ordenação DENTRO dessa seção. O chamado não triado mais antigo pode ficar invisível indefinidamente |
| UX-03 | ui-web | UI/UX | 🟡 | o solicitante só descobre que o prazo de recurso corria quando ele já passou: nenhuma tela informa o prazo antes de o botão sumir |
| UX-04 | ui-web | UI/UX | 🟢 | a troca de papel é um seletor de usuário no canto. Nada sinaliza que trocar de usuário troca o contexto inteiro de autorização |
| SUS-01 | trilha | Sustainability / Proportionality | 🟡 | somente-inserção e nunca apagada (A4), sem política de retenção. O armazenamento cresce proporcionalmente ao uso, para dados cujo valor decai com o tempo |
| SUS-02 | repositorio | Sustainability / Proportionality | 🟢 | duplica: PER-01 — chamados encerrados nunca são arquivados e continuam sendo avaliados na consulta de fila; o custo cresce com o histórico, não com o trabalho ativo |
| ETI-01 | chamado | Ethical / Human Impact | 🔴 | duplica: PRE-04 — a calibração da urgência varia com letramento, hierarquia e assertividade. Solicitantes menos assertivos são sistematicamente despriorizados pela mesma dor, e a única correção disponível (o recurso) exige exatamente a assertividade que lhes falta |
| ETI-02 | recurso | Ethical / Human Impact | 🟡 | instância única e final: o solicitante com recurso improvido não tem via ulterior. ISO 10002 prevê escalonamento externo; a segunda instância foi removida por escopo negativo |
| ETI-03 | trilha | Ethical / Human Impact | 🟡 | a decisão de "transparência sem penalidade" produz estatística de recursos por solicitante. Vigiar quem exerce um direito inibe o exercício legítimo — exatamente o efeito que a recusa de punir queria evitar |
| PRO-01 | chamado | Process / Workflow | 🔴 | não existe prazo para TRIAR. O SLA só começa a correr na triagem, então um chamado pode ficar NÃO TRIADO para sempre sem violar coisa alguma. O único estado sem governo de tempo é justamente a porta de entrada |
| PRO-02 | ui-web | Process / Workflow | 🔴 | a transição `reconhecer` existe no modelo e tem meta de prazo por prioridade, mas nenhuma das 6 telas tem ação de reconhecer. Transição sem superfície: o prazo de reconhecimento é inatingível |
| PRO-03 | ui-web | Process / Workflow | 🟡 | duplica: PRO-02 — `encerrar` também não tem ação declarada em nenhuma das 6 telas |
| PRO-04 | chamado | Process / Workflow | 🔴 | G2 impede abrir recurso em chamado encerrado, mas nada impede encerrar um chamado que tem recurso ABERTO. O recurso fica órfão: não pode ser julgado com efeito e não tem estado terminal |
| GOV-01 | trilha | Governance / Accountability | 🟡 | duplica: SEG-01 — a trilha grava `atorId`, mas sem prova de identidade a autoria é auto-declarada. Auditoria nominal, não atribuível |
| GOV-02 | configuracao | Governance / Accountability | 🔴 | a matriz e as metas de SLA não têm dono nem trilha. Alterar uma célula muda a prioridade de todos os chamados futuros, e é a única decisão do sistema sem autor, sem instante e sem registro |
| GOV-03 | trilha | Governance / Accountability | 🟢 | não há registro de quem leu a trilha, embora ela contenha texto livre escrito por solicitantes |
| CTL-01 | configuracao | Control Engineering | 🔴 | alterar a matriz muda `derivar()` para chamados novos, enquanto os abertos mantêm a prioridade gravada (herdado de F4). Passam a existir dois valores de verdade para a mesma pergunta — o gravado e o recalculável — e nada reconcilia. Deriva de estado sem sinal de erro |
| CTL-02 | sla | Control Engineering | 🟡 | `violado` é calculado sob demanda e não gera ação: o sistema observa a violação mas não repriorioriza, não escala e não avisa. Malha aberta — mede o erro e não o corrige |
| JOG-01 | chamado | Game Theory | 🔴 | o agente atribui o impacto e é medido pela violação de SLA que esse mesmo impacto produz. Impacto BAIXO gera prazo maior e menos risco de violação: o incentivo aponta para subestimar. A premissa A7 declara boa-fé do solicitante — ninguém declarou a do agente |
| JOG-02 | recurso | Game Theory | 🔴 | recontar prazos desde a abertura faz o provimento de um recurso CRIAR uma violação de SLA contada contra a própria equipe do gestor. O julgador tem incentivo direto a improver, e é da casa |
| JOG-03 | chamado | Game Theory | 🟡 | declarar urgência é grátis e recorrer uma vez é grátis. Declarar ALTA sempre é estratégia dominante fraca: garante no mínimo P3 qualquer que seja o impacto |
| LIN-01 | relogio | Linguistics / Grammar | 🟡 | `Instante` não tem representação declarada (epoch ms, ISO 8601, Date). As sessões desacopladas da Fase 5 podem escolher representações incompatíveis entre `relogio`, `sla` e `repositorio` |
| LIN-02 | trilha | Linguistics / Grammar | 🔴 | `antes`/`depois` são "json" sem esquema. Duas implementações corretas do contrato — uma serializando o chamado inteiro, outra só o campo alterado — produzem trilhas mutuamente ilegíveis, e CA-3 depende de ler exatamente isso |
| LIN-03 | autorizacao | Linguistics / Grammar | 🟡 | `Permissao` não enumera os motivos possíveis. B-3 (prescrição) e B-5 (legitimidade) exigem motivos distinguíveis, mas o contrato não declara quais existem |
| LIN-04 | recurso | Linguistics / Grammar | 🟡 | PARCIALMENTE_PROVIDO só tem sentido com dois eixos contestados. Contestar um eixo e receber "parcialmente provido" é sintaticamente válido e semanticamente vazio — o contrato admite o absurdo |
| MEC-01 | repositorio | Mechanical Engineering | 🟡 | better-sqlite3 é módulo nativo compilado contra a ABI do Node. A spec declara "Node 20+", faixa aberta que inclui ABIs incompatíveis: a tolerância declarada é maior que a real |
| MEC-02 | configuracao | Mechanical Engineering | 🟡 | as metas aceitam qualquer número, sem faixa válida declarada. Uma configuração com prazo de reconhecimento maior que o de resolução é aceita sem reclamação |

## Iteração 2 — V(2)

Lentes aplicadas: 7 universais + 11 condicionais. Mudança na declaração desta
rodada: **Observability / Operability passa a ser ativada** — MOV-1 criou o
sinal (o processo se recusa a subir com configuração inválida, e alguém
precisa diagnosticar isso sem alterar código). Não ativada: Migration /
Coexistence (segue greenfield).

Foco: os seis movimentos de V(2), que nenhuma lente havia atacado.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| PRE-06 | configuracao | Assumptions | 🟢 | MOV-1 assume que reiniciar o processo é aceitável para mudar a matriz. Verdadeiro neste nó único, mas nunca declarado |
| PRE-07 | trilha | Assumptions | 🟡 | assume-se que o evento devolvido pelo domínio é serializável. Ele carrega `Prioridade`, que é tipo com marca: serializar e ler de volta devolve uma prioridade que não passou por `derivar` — o CA-negativo tem uma porta dos fundos pela trilha |
| ARQ-06 | recurso | Architectural | 🔴 | MOV-2 fez `recurso.julgar` devolver `{recurso, chamado?, eventos}`. O `chamado?` significa que o agregado Recurso **modifica outra entidade**, e o recálculo de prazos passa a existir em DOIS lugares — `chamado.reclassificar` e `recurso.julgar`. A regra que V(1) protegia por assinatura única foi duplicada por V(2) |
| ARQ-07 | configuracao | Architectural | 🟡 | MOV-5 tirou o seed de `repositorio` e o pôs em `configuracao`, que agora carrega matriz, metas, prazos e seed. Dado de política (muda comportamento) e dado de arranque (popula a base) são coisas distintas — o acúmulo foi movido, não removido |
| ARQ-08 | api-http | Architectural | 🟡 | com `ui-web` passando a depender de `casos-de-uso`, existem duas portas de entrada para o mesmo núcleo: páginas por `ui-web` (GET) e ações por `api-http` (POST). As regras de sessão precisam ser idênticas nas duas, e a divergência entre elas seria invisível |
| IMP-04 | casos-de-uso | Implementability | 🔴 | MOV-2 afirmou tornar a trilha "impossível de violar". O que ficou impossível é **não produzir** o evento; ainda é perfeitamente possível **não gravá-lo** — `casos-de-uso` recebe `eventos[]` e pode simplesmente não chamar `trilha.registrar`. CA-3 continua dependendo de disciplina, ao contrário do que V(2) declarou |
| CIE-04 | configuracao | Scientific | 🟡 | `prazoTriagem` é um parâmetro inteiramente novo, sem fonte — nem Tier C. Nenhum dos quatro produtos pesquisados em specs/competitors tem prazo de triagem, logo nem convergência de mercado o sustenta |
| SEG-05 | api-http | Security | 🔴 | o esquema por endpoint (MOV-4) permite ao agente alterar `urgencia` na reclassificação — o eixo do solicitante. Como o prazo de recurso conta da TRIAGEM e prescreve em 48 h, uma reclassificação tardia da urgência ocorre depois de prescrito o recurso: o solicitante perde o eixo que é seu, sem instrumento para contestar |
| PER-04 | repositorio | Performance | 🔴 | a ordenação unificada por prazo crescente (a "solução elegante" de V(2) para PER-01) mistura duas grandezas na mesma coluna: prazo de triagem para não triados e prazo de resolução para triados. Um não triado com prazo de 8 h aparece na frente de um P1 com prazo de 4 h. A fila deixa de ordenar por severidade |
| REG-04 | recurso | Regulatory | 🟡 | duplica: PRO-06 — ISO 10002 exige prazo por nível de escalonamento. V(2) manteve o prazo de julgamento sem expiração e ainda o tornou bloqueante do encerramento |
| RES-03 | configuracao | Resilience | 🟡 | MOV-1 derruba o processo com configuração inválida e não há default de emergência. Num reinício automático com config quebrada, o sistema fica fora do ar sem rede de segurança — falha rápida sem plano B |
| OBS-01 | configuracao | Observability / Operability | 🟡 | o processo se recusa a subir, mas nada declara COMO o operador descobre qual célula da matriz está errada. Falha rápida sem mensagem diagnóstica é opacidade — o operador só sabe que não subiu |
| UX-05 | ui-web | UI/UX | 🟡 | T-3 passou a exibir a matriz 3×3 estática (correção de UX-01). Efeito colateral: o agente vê o resultado de cada impacto antes de escolher e pode fazer engenharia reversa do alvo — "quero P3, logo marco MEDIO". A tela ensina exatamente a manobra que JOG-01 descreve |
| UX-06 | ui-web | UI/UX | 🟡 | o cookie de sessão assinado (mitigação de SEG-01) pressupõe uma tela de entrada que não existe nas 6 telas declaradas em specs/design/telas.md. São 7 telas agora, e o documento de design não registra a sétima |
| SUS-03 | trilha | Sustainability / Proportionality | 🟡 | a premissa A15 declara que a trilha vive enquanto o chamado vive, mas nenhum chamado morre: não há arquivamento nem exclusão. A premissa descreve um limite que na prática é "para sempre" |
| ETI-04 | trilha | Ethical / Human Impact | 🔴 | MOV-5 removeu a estatística de recursos por solicitante. A decisão da Fase 0 — "transparência + prescrição, SEM penalidade" — apoiava-se explicitamente em "o abuso fica visível e é tratado fora do sistema". V(2) removeu a visibilidade e manteve a ausência de penalidade: agora nada contém abuso, e uma decisão da Fase 0 foi esvaziada por uma simplificação da Fase 3 |
| PRO-05 | chamado | Process / Workflow | 🟡 | o `prazoTriagem` pode ser ultrapassado e nada acontece: não há estado, não há evento, e a fila não distingue não triado dentro do prazo de não triado violado. MOV-3 criou o prazo e não criou a consequência |
| PRO-06 | recurso | Process / Workflow | 🔴 | a guarda "não encerra chamado com recurso ABERTO" (MOV-4) transformou um problema benigno em bloqueio: como o prazo de julgamento não expira (REG-02, aceito na iteração 1), um recurso nunca julgado impede o encerramento do chamado indefinidamente |
| GOV-04 | configuracao | Governance / Accountability | 🟡 | a versão da configuração dá autoria à IMPLANTAÇÃO, não a uma pessoa. GOV-02 foi resolvido pela metade: sabe-se qual configuração agiu, não quem a escreveu |
| CTL-03 | configuracao | Control Engineering | 🔴 | a `versao` é declarada pelo humano DENTRO do próprio arquivo. Nada impede editar a matriz e esquecer de incrementá-la — dois conteúdos distintos com a mesma versão, e a rastreabilidade que GOV-02 e CTL-01 ganharam vira disciplina humana em vez de propriedade do sistema |
| JOG-04 | chamado | Game Theory | 🟡 | o `prazoTriagem` mede a VELOCIDADE da triagem e nunca a qualidade. Triar rápido com qualquer impacto satisfaz o prazo — MOV-3 acrescentou um incentivo que empurra na mesma direção de JOG-01 |
| LIN-05 | trilha | Linguistics / Grammar | 🟡 | V(2) diz "união discriminada fechada" mas não enumera os construtores do evento. Um contrato que se descreve como fechado sem listar os casos é, na prática, tão aberto quanto o json que substituiu |
| MEC-03 | sla | Mechanical Engineering | 🟡 | as metas estão em horas fracionárias (P1 = 0,167 h para reconhecer). 0,167 h não é 10 minutos exatos, e `somarHoras` com fração produz milissegundos quebrados: o prazo desliza segundos em relação à meta declarada. A tolerância nunca foi declarada, e metas em minutos inteiros eliminariam a questão |
