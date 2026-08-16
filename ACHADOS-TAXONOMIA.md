# Achados sobre a taxonomia — acumulados durante o lote

Observações sobre os **critérios das lentes** que só aparecem em uso real. Registradas
aqui à medida que surgem, com a evidência, para não dependerem da memória de ninguém
quando os doze fecharem.

**Nada aqui é corrigido durante o lote.** Mexer no critério de uma lente é mexer no
instrumento de medida no meio da coleta: obrigaria a nova versão da extensão, deixaria
os projetos já concluídos sob um critério e os seguintes sob outro, e — o principal —
**apagaria a evidência ao consertar o defeito**. Um critério que dois leitores
competentes interpretam de forma diferente é resultado da RO3, não bug a esconder.

Ajustar o instrumento *porque se viu divergência no dado* é o que o pré-registro existe
para impedir. Estes são candidatos a refinamento **pós-lote**.

---

## UX — "User-facing interface" não decide se CLI conta

**Texto atual da guidance:**

| campo | conteúdo |
|---|---|
| pergunta central | *Can the user complete their task without frustration, confusion, or error?* |
| classe de falha | fluxos confusos, estados sem saída, feedback ausente, falhas de acessibilidade |
| **gatilho** | *User-facing interface* |

É o gatilho mais curto dos doze, e não qualifica o que conta como interface.

**Evidência — três projetos, mesma divergência, sempre na mesma direção:**

| projeto | estimativa sobre a V(1) | Fase 2 declarou |
|---|---|---|
| T15-interchange | não | **SIM** |
| T02-scheduler | não | **SIM** |
| T14-loadbalancer | não | não |

Nos dois primeiros a interface é uma **CLI**. O T15 registrou na Fase 0: *"INTERFACE —
CLI, como módulo nomeado na decomposição da Fase 1"*. O estimador, lendo a arquitetura,
vê módulos de infraestrutura e conclui que não há usuário; a Fase 2, que passou pela
Fase 0, sabe que há uma pessoa operando por linha de comando.

**Leitura:** não é divergência de julgamento, é de **definição**. "Interface voltada ao
usuário" admite duas leituras — interface gráfica para usuário final, ou qualquer
superfície operada por humano, CLI inclusa — e o texto não escolhe. A Fase 2 vem
adotando a leitura ampla; o estimador, a estreita.

**Consequência para o lote:** a projeção de que UX ficaria sub-coberta estava errada.
UX ativou em 3 dos 3 projetos concluídos; quem não a vê é o preditor.

**Candidato a refinamento pós-lote:** qualificar o gatilho — por exemplo, *"qualquer
superfície operada por humano, incluindo CLI e ferramentas de operação"*. Fecharia a
ambiguidade sem mexer na pergunta central nem na classe de falha.

---

## GOV — pergunta central e gatilho medem coisas diferentes

**Texto atual:**

| campo | conteúdo |
|---|---|
| pergunta central | *Is every action attributable? Does every data entity have a defined owner?* |
| gatilho | *Multiple teams, data domains, or compliance (SOC2, LGPD, HIPAA)* |

A pergunta é sobre **auditabilidade**; o gatilho é **organizacional**. Um sistema com
registro de auditoria impecável, operado por uma pessoa, não aciona a lente.

**Evidência:** o T15 recebeu, de propósito, a cláusula *"registro de quem enviou o quê"*
no enunciado, escrita para ancorar GOV. Não ativou, e a justificativa da Fase 2 estava
correta: *"ator único (operador de migração); a Fase 0 recusou explicitamente a opção
'operador + auditor externo'; sem múltiplas equipes, sem domínios de dados distintos e
sem exigência de compliance declarada"*.

**Leitura:** o critério é preciso; quem errou foi o desenho do enunciado, ao mirar a
pergunta central em vez do gatilho. Diferente do caso de UX — lá o texto é ambíguo, aqui
é específico e foi mal lido por mim.

**Correção já aplicada, mas na amostra e não no instrumento:** T07, T08 e T10 ganharam o
gatilho que o critério reconhece (LGPD em dois; equipes distintas no terceiro), em
2026-08-07. Os dois estimadores passaram a projetar GOV em 4 projetos.

**Candidato a refinamento pós-lote:** não o gatilho, que funciona, mas a **relação entre
pergunta e gatilho** — vale discutir se uma lente deve poder ter pergunta central mais
ampla que sua condição de ativação, ou se isso é fonte previsível de erro de desenho.

---

## MEC emerge com a maturação da arquitetura

**Evidência acumulada, três observações independentes:**

- **T14:** MEC **não** estava na iteração 1 e entrou na 2, contra a V(2), com
  justificativa registrada.
- **Pilotos descartados (T13 e T05):** a reestimativa cega sobre a V(final) ativou MEC
  nos dois, estável em três rodadas de cada, quando a declaração contra a V(1) não a
  incluía. Foi o achado que motivou a correção da redeclaração por iteração.
- **T15:** a estimativa sobre a V(1) não dá MEC de forma estável (2/3), mas a Fase 2
  declarou.

**Leitura:** o gatilho de MEC — *"module maintenance, system evolution, long-lived
systems with technical debt accumulation"* — descreve propriedades que uma arquitetura
**adquire ao ser criticada e revisada**, não propriedades do problema. É plausível que
MEC seja estruturalmente uma lente de iteração tardia.

**Por que importa para a RO3:** se MEC só ativa depois que a arquitetura amadurece, um
projeto que converge em uma iteração nunca a exercita — e a cobertura dela passa a
depender de quantas voltas o laço 2↔3 deu, não do domínio do projeto. Isso é
confundidor para a contagem do §2, que assume cobertura determinada pelo tipo de
projeto.

---

**Atualização de 2026-08-11 — a hipótese não se sustenta como propriedade da LENTE.**

Três observações do ciclo 2 vão contra:

| projeto | evidência | efeito |
|---|---|---|
| T21-certificados | MEC ativou **já na iteração 1**, contra a V(1) | contra: não é tardia |
| T22-plantoes | MEC **fora nas duas** iterações, inclusive contra a V(3) | contra: maturação não a traz |
| **T27-despesas** | **três voltas do laço, MEC fora nas três** | contra, e é o caso mais forte |

E o fenômeno de emergência tardia, que era o coração da hipótese, **apareceu — mas em outra
lente**: no T26-extratos foi **MIG** que entrou só na iteração 2, contra a V(3), num
projeto inteiramente sobre importar múltiplas fontes, onde ela "deveria" ativar por domínio
desde a V(1).

**A leitura corrigida.** Emergência tardia é real e está documentada, mas **não é
propriedade de MEC**. É propriedade de *quanto a arquitetura de um projeto específico muda
ao ser criticada* — qualquer lente cujo gatilho descreva uma característica que a revisão
introduz pode aparecer tarde. MEC foi a primeira a ser notada porque seu gatilho fala de
evolução e dívida técnica, o que a tornava candidata óbvia; MIG mostrou que não é
exclusividade dela.

**O confundidor do §2 permanece**, e agora melhor caracterizado: a cobertura de uma lente
depende de quantas iterações o projeto deu, e isso é independente do domínio. A análise
final deve correlacionar ativação por lente contra número de iterações — não só de MEC.

---

## A distinção condicional × universal pode ser empiricamente frágil

**Aberto em 2026-08-09, com 2 observações. Não fechado — decidir com 4.**

Os gatilhos de SUS, UX e GOV foram reescritos na v0.12.9 porque as três não conseguiam
ser exercitadas: GOV e SUS ficaram em **0 ativações de 7 projetos** no ciclo 1, e nenhuma
reescrita de enunciado resolvia. A correção trocou condição organizacional por propriedade
do sistema, e destravou a medida.

O efeito medido, no mesmo lote, antes e depois:

| | gatilhos estreitos (ciclo 1) | gatilhos largos (ciclo 2) |
|---|---|---|
| máximo de condicionais ativas num projeto | 8 de 12 | **11 de 12** |
| GOV | 0 de 7 projetos | ativou nos 2 |
| SUS | 0 de 7 projetos | ativou nos 2 |

**A leitura.** Redigido como propriedade do sistema, o gatilho de UX — *"qualquer
superfície operada por uma pessoa, incluindo CLI"* — cobre quase todo software; o de SUS
— *"decide, aloca ou consome recurso cujo custo cresce com o uso"* — também. Se quase toda
condicional ativa em quase todo projeto, a distinção entre lente **condicional** e
**universal** deixa de existir na prática, e o §2 desenhou a cobertura supondo ativação
seletiva por sinal do projeto.

**Por que NÃO foi corrigido durante o lote**, ao contrário dos gatilhos de SUS/UX/GOV:

Aqueles ajustes eram obrigatórios porque **impediam medição** — 0 ativações significam
nenhum dado, e não se distingue "não detecta" de "nunca rodou". Ativação ampla é o
oposto: dá mais dado por lente, faz o Passo 2 e o Passo 4 funcionarem melhor, e satisfaz
o piso de 3 projetos com folga. **Não bloqueia nada — é resultado.**

Estreitar o gatilho agora seria ajustar o instrumento porque o resultado não agradou, sem
a justificativa que os anteriores tinham. Seria também a quarta mudança nos gatilhos, e
custaria o descarte do projeto em curso mais o desenho de cobertura dos doze, que foi
feito contra os gatilhos atuais.

**Atualização de 2026-08-09 — o T24 enfraquece a hipótese.** Primeiro projeto fora do
slot T21: **9 de 12**, com MIG, ETI e OBS fora, cada uma com justificativa específica e
verificável (greenfield sem legado; nenhuma decisão automatizada sobre pessoas; CLI
efêmera sem estado entre execuções).

| projeto | slot | condicionais ativas |
|---|---|---|
| T21-cofre (descartado) | T21 | 10 |
| T21-certificados | T21 | 11 |
| **T24-catalogo** | **T24** | **9** |

Nove de doze ainda é alto, e o piso de 3 projetos do §2 segue trivialmente satisfeito —
mas a leitura de "quase universal" não se sustenta com uma não-ativação em cada quatro. A
decisão de não mexer nos gatilhos durante o lote fica **mais** justificada: se tivesse
estreitado depois do T21, teria corrigido um padrão que o projeto seguinte já não
mostrava.

**O que fazer com isso.** Se o padrão se confirmar em quatro projetos, entra no relatório
como achado — *a distinção condicional/universal é frágil quando os gatilhos são redigidos
como propriedade do sistema* —, com o antes e o depois medidos no mesmo lote. A reescrita
dos gatilhos vira recomendação de trabalho futuro, não intervenção na coleta.

---

## A pergunta central mais larga que o gatilho não é caso isolado de GOV

**Três lentes de uma vez, no mesmo projeto: ETI, JOG e LIN. T21-certificados, 2026-08-09.**

A entrada de GOV acima tratou o descompasso entre pergunta central e gatilho como
peculiaridade daquela lente. Não é: a reestimativa cega do T21 expôs o mesmo padrão em
três outras, e desta vez com os dois lados documentados.

| lente | gatilho canônico | leitura do estimador restritivo | Fase 2 |
|---|---|---|---|
| JOG | *"Multiple independent actors, **public API, external integrations, marketplace or platform design**"* | *"sem mercado aberto, API pública ou incentivos econômicos entre entidades independentes"* → **não** | SIM |
| ETI | *"Automated decisions **about people** (scoring, classification, moderation)"* | *"classifica certificados X.509, não pessoas"* → **não** | SIM |
| LIN | *"…interface contracts **between independent teams**"* | *"contratos internos em TypeScript no mesmo repositório"* → **não** | SIM |

**A leitura restritiva é a textualmente correta.** O sistema decide sobre certificados, não
sobre pessoas; não tem API pública nem mercado; os contratos de interface são internos a um
monólito modular. Quem ativou as três foi a Fase 2, aplicando a **pergunta central** — e
com razão substantiva: o `lessons.md` do projeto documenta o jogo de escalada entre quem
burla e os controles, que é exatamente o objeto de JOG, mas **não** é nenhuma das condições
que o gatilho lista.

**Por que isso é diferente do caso UX.** Em UX o gatilho é *ambíguo* — "user-facing
interface" admite duas leituras e o texto não escolhe. Aqui o gatilho é **específico e
específico demais**: ele enumera condições que a pergunta central não exige. Não há
divergência de interpretação; há duas perguntas diferentes dentro da mesma lente, e cada
leitor responde a uma.

**Não é artefato do modelo local.** A justificativa se repete quase palavra por palavra nas
3 rodadas, e cita o gatilho. Um modelo instável demais para a tarefa oscilaria. Registrado
porque a hipótese foi levantada e testada, não descartada por conveniência.

**Consequência para a leitura do §3.** A pergunta era *dada a mesma informação, leitores
independentes ativam as mesmas lentes?*. Com pergunta e gatilho apontando para conjuntos
diferentes, a resposta depende de **qual campo o leitor toma como critério** — e isso é
propriedade da taxonomia, não dos leitores. Reportar como divergência entre estimadores
seria atribuir ao instrumento um defeito do objeto medido.

**Candidato a refinamento pós-lote**, e agora com peso maior que na entrada de GOV: decidir
se o gatilho é *condição necessária* ou *lista de exemplos típicos*, e redigir os 12
uniformemente sob a escolha. Hoje SUS diz explicitamente *"e.g. (but NOT only)… apply the
central question, do not just match the examples"* — nenhum dos outros diz, e o
comportamento observado é que os leitores tratam os outros como condição fechada.

---

## Concordância na ativação — quatro projetos, e a leitura mudou quatro vezes

**Esta entrada já foi reescrita três vezes. A quarta redação é deliberadamente descritiva:
paro de interpretar até os doze.**

| versão | afirmava | refutada por |
|---|---|---|
| T21 | o Kimi acerta mais porque é **permissivo** | T24: caiu de 9,7 para 4,3 ativações |
| T24 | os externos ativam **sistematicamente menos** que a Fase 2 | T22: 9,0 e 10,3 contra 9 declaradas |
| T22 | os externos **concordam entre si** mais que com a Fase 2 (88% × 73–79%) | T23: kimi × Fase 2 subiu a 85%, empatando com estimador × estimador |

### Ativações médias por rodada

| projeto | qwen3.6:27b | kimicode | **Fase 2** |
|---|---|---|---|
| T21-certificados | 7,3 | 9,7 | **11** |
| T24-catalogo | 5,3 | 4,3 | **9** |
| T22-plantoes | 9,0 | 10,3 | **9** |
| T23-canario | 6,3 | 9,3 | **10** |

Cinco células abaixo, duas acima, uma empatada. **Não há viés direcional de contagem.**

### Concordância acumulada (só decisões 3/3 ou 0/3)

| par | T21 | T24 | T22 | T23 | total |
|---|---|---|---|---|---|
| estimador × estimador | 7/8 | 8/9 | 6/7 | 8/10 | **29/34 = 85%** |
| kimi × Fase 2 | 10/10 | 7/11 | 6/8 | 11/11 | **34/40 = 85%** |
| qwen × Fase 2 | 7/10 | 7/10 | 8/10 | 8/11 | **30/41 = 73%** |

**O que é estável em quatro projetos:** só o qwen, em 73%, e ele é o mais baixo dos três
pares em todos. As outras duas linhas oscilam de 6/8 a 11/11 e o ranking entre elas já
inverteu duas vezes.

**O que NÃO pode ser afirmado**, e cada tentativa foi desmentida pelo projeto seguinte:
que um estimador é melhor, que os externos divergem sistematicamente da Fase 2 numa
direção, ou que os externos formam bloco. Com ~10 decisões estáveis por projeto, a margem
de erro cobre todas essas leituras.

**O que já é sólido, e é negativo:** nem fraqueza do modelo local nem permissividade de um
estimador explicam a divergência. Os dois modelos, de famílias diferentes, produzem
ranking instável entre si — o que aponta para o critério, não para os leitores. O
mecanismo candidato segue sendo o registrado em [pergunta central × gatilho], que tem
evidência **textual** (as justificativas citam o gatilho) e não estatística.

**Regra: nada direcional entra no relatório antes dos doze.** Concordância nunca vai
reportada sem a contagem de ativações ao lado; os doze rodam com os dois estimadores, n=3.

---

## Questão fechada — a redeclaração por iteração deve exigir reavaliação, não estabilidade

**Levantada pela operadora em 2026-08-11: *"nada garante a estabilidade das lentes entre
dois ciclos adversariais — essa garantia deve existir, uma vez que a nova arquitetura é
diferente da anterior?"*. Resposta: não deve, e o comportamento atual está correto.**

### O argumento

Ativação é função da arquitetura. V(N+1) é outra arquitetura. Travar o conjunto entre
iterações mandaria a Fase 2 **ignorar exatamente o que a Fase 3 acabou de mudar** — e
desfaria a correção da v0.12.6, que custou os descartes do T13 e do T05. Lá o problema era
o oposto: conjunto fixo contra a V(1), nunca reexaminado, com MEC ficando de fora em
projetos onde a reestimativa cega sobre a V(final) a ativava de forma estável.

**O risco real não é instabilidade — é a redeclaração virar formalidade**, com o agente
copiando o conjunto anterior sem reavaliar. Isso seria AP1: satisfazer o critério sem
fazer o trabalho.

### A medição que separa as duas coisas

Se a redeclaração fosse cópia, as justificativas de não-ativação seriam idênticas entre
iterações. Medido nos **12 projetos** do ciclo 2, comparando **iterações consecutivas**:

| | resultado |
|---|---|
| projetos com ≥2 iterações | 12 |
| comparações lente a lente | 36 |
| conjunto mudou entre iterações | 3 — T26 (MIG), T31 (CTR), T32 (OBS) |
| **justificativas idênticas** | **0 — nenhuma, em nenhum projeto** |
| Jaccard de tokens de palavra | 0,41 no conjunto · 0,23 a 0,59 por projeto |

Comando: `python3 analise/redeclaracao.py`. A tabela anterior media 11 projetos, comparava
it1 com a última iteração, e usava `difflib.SequenceMatcher` em caractere — cujo piso de
0,09 era artefato da heurística *autojunk*, que descarta espaço e vogais em textos longos.

Exemplo do T26, a mesma lente nas duas iterações:

> **it1** — *"Projeto greenfield: não substitui nem modifica sistema em produção, não há
> legado, dado a migrar nem caminho de rollback a projetar."*
> **it2** — *"V(2) segue greenfield: remover módulo de um desenho ainda não implementado
> não é migração — não há sistema em produção, dado a migrar nem rollback."*

Mesma conclusão, raciocínio **refeito contra a versão nova**, citando o que mudou.

### A leitura

O conjunto permanece igual em 9 de 11 **porque a conclusão é a mesma, não porque ninguém
olhou**. E os dois que mudaram provam que o mecanismo produz mudança quando há razão.

**A garantia correta é: reavaliação obrigatória, resultado livre.** Registro que minha
formulação anterior — *"o mecanismo permite mudança, não a força"* — sugeria que forçar
pudesse ser desejável. Não é.

### Consequência para a análise, e ela já mordeu uma vez

Se o conjunto pode mudar legitimamente, **contagem por união e comparação por iteração são
medidas diferentes** e não podem ser trocadas:

| pergunta | conjunto correto |
|---|---|
| a lente foi exercitada neste projeto? | **união** das iterações |
| dado o que o declarante via, ele ativou? | **a iteração** correspondente |

Trocar as duas foi o defeito que o T26 expôs no `reestimar_lentes.py`: eu comparava a
estimativa sobre a V(1) contra a união, o que contava MIG como declarada e transformava um
acerto dos dois estimadores em divergência falsa.

---

## Formato deste arquivo

Cada entrada: o texto atual da guidance, a evidência com projeto e número, a leitura, e
o candidato a refinamento. Sem correções aplicadas durante o lote.
