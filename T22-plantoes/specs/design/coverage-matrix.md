# Matriz de cobertura — crítica adversarial

Lentes: 7 universais + 9 condicionais ativadas (Resilience, UI/UX,
Sustainability / Proportionality, Ethical / Human Impact, Process / Workflow,
Governance / Accountability, Control Engineering, Game Theory,
Linguistics / Grammar). Não ativadas: Migration / Coexistence,
Observability / Operability, Mechanical Engineering.

Modo generativo (AP1): cada linha é um cenário de falha produzido, não um
julgamento de qualidade.

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASS-01 | catalogo-restricoes | Assumptions | 🔴 | `verificar(escala, ctx)` assume que quem chama montou o `ctx` completo, inclusive a fronteira do mês anterior. UC-5 roda sobre uma escala publicada sem obrigação de carregar o mês anterior → L1/H3 na virada não são verificados e o relatório afirma "0 violações" sobre escala que quebra o art. 66 no dia 1º |
| ASS-02 | fronteira | Assumptions | 🟡 | A-3 assume mês anterior publicado e completo. O código não distingue "não existe mês anterior" (primeiro mês, correto) de "existe mas não foi encontrado" (caminho errado) — os dois produzem fronteira vazia e escala silenciosamente ilegal na virada |
| ASS-03 | troca | Assumptions | 🟡 | Assume que os dois plantões da troca pertencem à MESMA escala. Troca entre 30/09 e 01/10 (meses diferentes) não é modelada, e a escala é a unidade de revalidação |
| ASS-04 | solver-cpsat | Assumptions | 🟢 | Assume que toda pessoa é elegível a todo plantão da sua habilitação: não há noção de unidade/setor. Com duas unidades, a pessoa é alocada em ambas em dias alternados sem que nada perceba a distância |
| ARQ-01 | cli | Architectural | 🟡 | A orquestração do UC-1 (carregar→fronteira→diagnóstico→solver→salvar) mora no `cli`, que depende dos 10 outros módulos. Não há como testar o fluxo do caso de uso sem passar por `argparse` |
| ARQ-02 | catalogo-restricoes | Architectural | 🔴 | Nada obriga uma restrição a implementar `aplicar` e `verificar` coerentemente. Uma restrição pode aplicar corretamente no solver e ter `verificar` devolvendo lista vazia — o gerador respeita a regra, o relatório nunca a fiscaliza, e o defeito passa em silêncio |
| ARQ-03 | fronteira | Architectural | 🟢 | Módulo de função única dependendo só de `dominio`; poderia ser função de `avaliador`. Granularidade abaixo do útil — custa arquivo e import sem ganhar isolamento testável |
| ARQ-04 | dominio | Architectural | 🟡 | Domain Model declarado diz "Escala sabe calcular seu custo", mas o cálculo mora em `avaliador` (M-03). Ou `Escala` ganha o método e passa a depender de `catalogo-restricoes` (ciclo dominio→catalogo→dominio), ou o modelo é parcialmente anêmico. A contradição não está resolvida |
| IMP-01 | catalogo-restricoes | Implementability | 🔴 | O módulo concentra ~19 restrições (H1-H4, L1-L8, S1-S7 e internas) × 2 modos ≈ 38 implementações, mais a lógica de natureza-por-regime. Não cabe em uma única interação com o contexto disponível → viola o princípio de granularidade E=I₀/C declarado na Fase 1 |
| IMP-02 | solver-cpsat | Implementability | 🟡 | A codificação de S2/S3 (consecutividade com mínimo e máximo, atravessando a fronteira) é a parte mais intrincada e `specs/technical/modelo-cpsat.md` só nomeia o idioma, sem pseudocódigo. Risco de implementação por intuição (AP7) |
| IMP-03 | diagnostico | Implementability | 🟡 | A abordagem (2), relaxação por camadas, está descrita como ideia: não define quais camadas nem em que ordem. Se a (1) não explicar o caso, não há referência para implementar na sessão |
| CIE-01 | catalogo-restricoes | Scientific | 🟡 | O peso das regras internas é arbitrado (o exemplo INT-01 usa 25, que não vem de lugar nenhum) e compete na MESMA função objetivo com os pesos calibrados do INRC-II. Um peso interno mal escolhido domina S1-S7 sem que ninguém perceba |
| CIE-02 | solver-cpsat | Scientific | 🟢 | A premissa A8 (pesos do INRC-II adequados ao contexto brasileiro) está declarada mas nenhum critério de aceitação a testa — premissa científica sem plano de verificação |
| CIE-03 | fronteira | Scientific | 🟡 | Não há referência para "derivar contadores a partir de uma escala pronta". O INRC-II define `history` como DADO DE ENTRADA da competição, não como algo derivado; a derivação é invenção nossa, sem fonte bibliográfica |
| SEC-01 | cli | Security | 🔴 | A identidade vem por parâmetro (A5) e não há autenticação: `responder --pessoa p02 --aceitar` consente uma troca em nome de outra pessoa. Como o consentimento do par é a ÚNICA aprovação do produto, o mecanismo de aprovação inteiro é falsificável por um argumento de linha de comando |
| SEC-02 | carregador | Security | 🟡 | JSON carregado sem limite de tamanho nem de profundidade; A6 assume entrada não hostil. Instância com 10^6 plantões esgota memória antes de qualquer validação |
| SEC-03 | repositorio-json | Security | 🟡 | Caminhos derivados de ids vindos da entrada (`escala_<id>.json`): id contendo `../` escreve fora do diretório de dados — path traversal na escrita |
| PER-01 | solver-cpsat | Performance | 🟡 | PR-2 (≤60 s) foi verificada com 9 variáveis, não com as ~2.700 do porte alvo. São três ordens de grandeza sobre um problema NP-difícil, sem nenhuma medição intermediária |
| PER-02 | avaliador | Performance | 🟡 | UC-4 reavalia a escala INTEIRA (~19 restrições × 30 dias × 30 pessoas) a cada resposta de troca que altera 2 alocações. Não existe avaliação incremental, e essa é a operação interativa mais frequente |
| PER-03 | repositorio-json | Performance | 🟢 | Toda leitura recarrega o arquivo completo e `listar_trocas` relê tudo a cada chamada. Irrelevante no porte alvo; degrada linearmente |
| REG-01 | catalogo-restricoes | Regulatory | 🔴 | L3 (12×36) só existe como MODIFICADOR da natureza de outras regras (L1, L2, L4, L6, L7) — nenhum módulo verifica que o próprio regime está sendo cumprido (12h seguidas de 36h ininterruptas). O regime desliga quatro restrições e não é ele mesmo fiscalizado: uma escala 12×24 passa |
| REG-02 | catalogo-restricoes | Regulatory | 🟡 | L6/L7 (adicional noturno, hora ficta) constam da tabela normativa mas nenhum módulo as implementa, porque cálculo de remuneração está fora de escopo. Requisito normativo listado sem módulo dono — rastreabilidade quebrada |
| REG-03 | carregador | Regulatory | 🟢 | L4 vira validação de entrada e a mensagem deve citar o art. 59, mas não há especificação do catálogo de mensagens normativas — cada mensagem seria improvisada na hora |
| RES-01 | solver-cpsat | Resilience | 🟡 | `UNKNOWN` e `MODEL_INVALID` são tratados igual ("falha com o status bruto"), mas significam coisas opostas: MODEL_INVALID é defeito nosso, UNKNOWN é tempo esgotado sem solução viável. Colapsá-los apaga a informação que decidiria o que fazer |
| RES-02 | repositorio-json | Resilience | 🔴 | Gravação não atômica: `salvar_escala` sobrescreve o arquivo. Interrupção no meio (Ctrl-C, disco cheio) deixa corrompida a escala publicada — que é simultaneamente a fonte da fronteira do mês seguinte e o alvo de todas as trocas. Não há backup nem escrita-e-troca-de-nome |
| RES-03 | carregador | Resilience | 🟡 | Sem especificação de erro por campo para JSON malformado ou campo ausente: o modo de falha padrão é stacktrace bruto para um plantonista |
| UX-01 | cli | UI/UX | 🟡 | Sem notificações (fora de escopo) o destinatário só descobre a troca consultando — mas não existe comando "listar minhas trocas pendentes" na decomposição. Os 5 UCs cobrem solicitar e responder, não TOMAR CIÊNCIA. O fluxo de troca não tem como começar |
| UX-02 | cli | UI/UX | 🟡 | A rejeição cita a regra violada, mas não há especificação de mensagem legível: "H3 violado" é inútil para o usuário-alvo; "você ficaria com 9h de descanso entre 14/09 e 15/09 e a lei exige 11h (CLT art. 66)" é o que o produto promete |
| UX-03 | cli | UI/UX | 🟢 | UC-2 (consultar escala) não tem formato de saída definido; JSON cru é ilegível para quem só quer saber em que dias trabalha |
| SUS-01 | solver-cpsat | Sustainability / Proportionality | 🟡 | Não há caminho barato para re-geração parcial: mudar um plantão custa o mesmo que gerar o mês do zero. A dor declarada na Fase 0 é "tempo do gestor" e a re-geração é justamente o caso comum |
| SUS-02 | avaliador | Sustainability / Proportionality | 🟢 | duplica: PER-02 — reavaliação total da escala a cada troca, custo desproporcional à mudança de 2 alocações |
| ETI-01 | solver-cpsat | Ethical / Human Impact | 🔴 | O sistema decide automaticamente quem trabalha noites, fins de semana e feriados — decisão de impacto material sobre a vida das pessoas — e não há mecanismo de recurso: não existe ator que possa contestar uma alocação. A única saída é achar um par que aceite trocar; se ninguém aceitar, não há recurso algum |
| ETI-02 | catalogo-restricoes | Ethical / Human Impact | 🟡 | Preferência tem peso 10, o menor do conjunto: sacrificá-la é sempre matematicamente a saída mais barata. A escala "ótima" tende a violar sistematicamente as preferências das MESMAS pessoas (as mais flexíveis por contrato), e equidade foi removida dos critérios de aceite — o viés não tem métrica que o detecte |
| ETI-03 | avaliador | Ethical / Human Impact | 🟡 | Não há relatório de distribuição por pessoa (quantos noturnos, fins de semana e feriados cada um recebeu). A injustiça produzida é invisível ao próprio sistema que a produz |
| PRO-01 | troca | Process / Workflow | 🔴 | Estado órfão: uma troca PENDENTE cuja escala-base foi re-gerada com `--force` referencia plantões que podem não existir mais. A máquina de estados não tem transição para "a escala de referência desapareceu" — a troca fica pendente apontando para o vazio |
| PRO-02 | troca | Process / Workflow | 🟡 | EXPIRADA é derivada da data, não persistida: a troca "expira" no momento em que alguém a consulta. Nada grava quando expirou, e uma auditoria não consegue dizer em que momento o estado mudou |
| PRO-03 | troca | Process / Workflow | 🟡 | Não existe caminho para o solicitante CANCELAR a própria troca. Quem pediu por engano só pode esperar o par recusar ou o plantão passar |
| PRO-04 | cli | Process / Workflow | 🟢 | duplica: UX-01 — o processo não tem passo em que o destinatário toma ciência da troca pendente |
| GOV-01 | repositorio-json | Governance / Accountability | 🔴 | Não há trilha de auditoria: as trocas mutam a escala publicada in loco. Após três trocas não existe registro da escala original nem de quem alterou o quê. A motivação declarada na Fase 0 é "conformidade auditável" e o artefato central é sobrescrito sem histórico |
| GOV-02 | troca | Governance / Accountability | 🟡 | `decidida_em` registra quando, mas nada registra QUEM executou o comando (só quem era o destinatário esperado). Combinado com SEC-01, nenhuma ação do sistema é atribuível a uma pessoa |
| GOV-03 | dominio | Governance / Accountability | 🟢 | `Escala` não tem versão nem carimbo de geração: duas escalas do mesmo período são indistinguíveis, e não se sabe qual veio antes |
| CTL-01 | fronteira | Control Engineering | 🔴 | A fronteira deriva do mês anterior sem nenhuma correção de erro: se M-1 foi gerado com defeito ou alterado por trocas, o erro se propaga para M, M+1… sem sinal. Não há reconciliação nem detecção de deriva — o estado acumulado nunca é confrontado com a realidade |
| CTL-02 | fronteira | Control Engineering | 🟡 | S6/S7 acumulam ao longo do horizonte CONTRATUAL, que pode ser maior que um mês. Derivar apenas de M-1 perde o acúmulo dos meses anteriores a ele: a realimentação enxerga um passo atrás e trata isso como se fosse o histórico completo |
| GAM-01 | troca | Game Theory | 🟡 | Incentivo assimétrico: nada impede alguém de propor sistematicamente trocas que despejam plantões indesejados e aceitar só as vantajosas. Não há limite de propostas nem visibilidade do padrão — o design assume cooperação |
| GAM-02 | catalogo-restricoes | Game Theory | 🟡 | Preferências são auto-reportadas e influenciam a alocação via S4, sem custo nem limite. Declarar tudo como indesejado é estratégia dominante: quem declara mais preferências recebe mais consideração |
| GAM-03 | cli | Game Theory | 🟢 | duplica: SEC-01 — sem autenticação, o "acordo entre pares" pode ser executado unilateralmente por qualquer um |
| LIN-01 | catalogo-restricoes | Linguistics / Grammar | 🔴 | `aplicar` e `verificar` são duas implementações do mesmo contrato semântico e nada no contrato as obriga a concordar. É o caso literal de duas implementações corretas do mesmo contrato com comportamentos incompatíveis. Falta uma propriedade de consistência declarada — do tipo "toda escala gerada com as restrições aplicadas deve verificar sem violações" |
| LIN-02 | carregador | Linguistics / Grammar | 🟡 | `Preferencia` aceita `plantao_id` OU `data`: duas gramáticas para a mesma coisa, sem precedência definida quando ambos vêm preenchidos, e sem definir o que `data` significa sem tipo de turno (todos os turnos daquele dia?) |
| LIN-03 | dominio | Linguistics / Grammar | 🟡 | `TipoDeTurno` com `fim` < `inicio` (noturno 19:00→07:00) significa implicitamente "vira o dia", e isso não está no contrato. Uma implementação razoável calcularia duração negativa — e é exatamente esse cálculo que sustenta a compilação de L1 em sucessões proibidas |
| LIN-04 | repositorio-json | Linguistics / Grammar | 🟢 | `estado` nomeia duas máquinas de estados diferentes (da Escala e da Troca) no mesmo formato de arquivo — leitor e escritor podem discordar sobre qual vocabulário vale |

## Iteração 2 — V(2)

Crítica da arquitetura V(2) (`specs/technical/architecture.md`, seção V(2)).
Mesmo conjunto de lentes, reexaminado contra o novo desenho. Foco nos módulos
novos (`diario`, `restricoes-legais`, `restricoes-modelo`) e reestruturados
(`avaliador`, `troca`, `repositorio-json`) — mas todas as lentes foram passadas
sobre os 12 módulos.

Nota de bookkeeping: `record_activated_lenses` carimbou esta rodada como
`againstVersion: 3` por causa do incremento no retorno do laço; a arquitetura
sob crítica é a V(2), última seção do documento de arquitetura.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| LIN-05 | diario | Linguistics / Grammar | 🔴 | `escala_vigente(id)` = snapshot + eventos aplicados em ordem, mas a ORDEM não está definida: por carimbo de tempo (relógio, sujeito a colisão e a ajuste do sistema) ou por posição no arquivo? Duas implementações razoáveis do mesmo contrato produzem escalas vigentes DIFERENTES a partir dos mesmos dados |
| RES-04 | diario | Resilience | 🔴 | Append-only só é seguro se o append for atômico. Escrita parcial de uma linha (disco cheio, Ctrl-C) corrompe o diário — e o diário passou a ser a ÚNICA fonte da escala vigente. D1 trocou um arquivo corrompível (V(1)) por um arquivo corrompível cujo dano é irrecuperável, porque não há mais estado redundante para reconstruir |
| ARQ-05 | diario | Architectural | 🔴 | `diario.escala_vigente()` e `repositorio-json.carregar_escala()` devolvem o MESMO tipo `Escala` com significados diferentes (vigente × snapshot publicado), e nada no tipo os distingue. UC-5 chamando o repositório em vez do diário relata conformidade de uma escala que não é a que vale — e a promessa central do produto é justamente esse relatório |
| GOV-04 | diario | Governance / Accountability | 🟡 | O diário grava "quem executou" a partir do mesmo parâmetro `--pessoa` que SEC-01 mostrou ser falsificável. A trilha é honesta sobre O QUE mudou e não sobre QUEM mudou; auditoria com autoria não verificável pode ser pior que nenhuma, por dar aparência de rigor a um registro que não a sustenta |
| SEC-04 | diario | Security | 🟡 | O diário é append-only por convenção do código, não do sistema de arquivos: qualquer pessoa edita o JSONL num editor de texto e reescreve a história. Sem encadeamento por hash, nada detecta a adulteração — a trilha de auditoria não é à prova de violação |
| PER-04 | diario | Performance | 🟡 | Toda leitura da escala vigente reprocessa todos os eventos desde o snapshot. Sem compactação nem novo snapshot, o custo de `consultar` cresce linearmente com o número de trocas do mês |
| PRO-05 | diario | Process / Workflow | 🟡 | O estado ORFA foi acrescentado à máquina de trocas, mas nada define QUEM ou O QUE dispara a transição: é detectada na leitura ou gera evento? Se for derivada na leitura, reintroduz exatamente o defeito que PRO-02 apontou — estado que muda sem registro |
| IMP-04 | diario | Implementability | 🟢 | Sem especificação do formato do evento (JSONL? um arquivo por escala?) nem do conjunto fechado de tipos de evento |
| SUS-03 | diario | Sustainability / Proportionality | 🟢 | duplica: PER-04 — reprocessamento integral do log a cada leitura, custo desproporcional a consultar dois plantões |
| ARQ-06 | restricoes-modelo | Architectural | 🟡 | Regras internas foram agrupadas com H1-H4/S1-S7 "porque têm a mesma forma paramétrica", mas têm origem e autoridade diferentes: uma vem de literatura com peso publicado, a outra é política local sem fonte. É o mesmo tipo de mistura que D2 acabou de desfazer no eixo legal × modelo, reintroduzido em outro eixo |
| IMP-05 | restricoes-modelo | Implementability | 🟡 | A divisão reduziu o tamanho do módulo, mas S2/S3 continuam sem pseudocódigo: IMP-02 não foi resolvido em V(2) nem aceito explicitamente — foi herdado por outro módulo sem tratamento |
| LIN-06 | restricoes-legais | Linguistics / Grammar | 🟡 | As duas famílias expõem a MESMA interface (`aplicar`/`verificar`) com semânticas de composição diferentes: legais são sempre rígidas e não somam custo; de modelo somam peso. Nada no contrato expressa a diferença — um chamador pode pedir o `peso` de uma restrição legal e receber algo sem sentido |
| REG-04 | restricoes-legais | Regulatory | 🟡 | A guarda "peso de regra interna ≤ 30" ficou no `carregador`, mas é semântica das restrições. Requisito sem dono claro: se outro caminho criar regra interna (o `gerador-sintetico`), a guarda não se aplica |
| CIE-04 | restricoes-legais | Scientific | 🟢 | L3 virou verificável ("12h seguidas de ≥36h ininterruptas"), mas o art. 59-A não define tolerância: uma escala com 35h59 de descanso é violação? Não há fonte para arbitrar a tolerância, e o código precisará de uma |
| ASS-05 | avaliador | Assumptions | 🟡 | "Recusa-se a propagar estado de escala com violações rígidas" assume que uma escala anterior violada é sempre erro. Mas ela pode estar legitimamente violada — troca efetivada antes de uma regra interna mudar, ou dado histórico anterior ao sistema. Sem caminho de override, UC-1 fica travado sem saída |
| ARQ-07 | avaliador | Architectural | 🟡 | Absorveu fronteira, custo, distribuição por pessoa e a fábrica de `Contexto`: quatro responsabilidades. A divisão do catálogo (D2) foi justificada por tamanho, e o `avaliador` cresceu no mesmo movimento sem passar pelo mesmo critério |
| CTL-03 | avaliador | Control Engineering | 🟡 | Ler N meses anteriores "conforme o horizonte contratual" não tem limite declarado: um contrato de horizonte anual faz UC-1 carregar e verificar 12 escalas. A realimentação ficou sem janela máxima |
| PRO-06 | troca | Process / Workflow | 🟡 | A máquina passou de 5 para 7 estados (+CANCELADA, +ORFA). Sintoma de AP2: a resposta à crítica de processo foi acrescentar estados. CANCELADA e RECUSADA são praticamente indistinguíveis (ambas terminam sem efetivar) e a distinção só serve à auditoria — que agora existe no diário e já registra quem encerrou |
| UX-04 | cli | UI/UX | 🟡 | `trocas --pessoa X` lista as pendentes DIRIGIDAS a ela, mas nada mostra as que ELA propôs e aguardam resposta. Metade do fluxo segue invisível — para o solicitante, o pedido some depois de enviado |
| ETI-04 | avaliador | Ethical / Human Impact | 🟢 | O relatório de distribuição por pessoa expõe a carga individual de todo mundo a quem rodar o comando: resolveu a visibilidade do viés (ETI-03) criando exposição de dado pessoal de terceiros |
| GAM-04 | troca | Game Theory | 🟢 | duplica: GAM-01 — com CANCELADA, propor muitas trocas e cancelar as inconvenientes gera ruído sem custo para quem propõe |
