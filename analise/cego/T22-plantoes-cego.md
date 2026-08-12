# Reagrupamento cego de achados — T22-plantoes

Você recebe 71 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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
| M-01 | dominio | entidades e objetos de valor do domínio; sem I/O, sem solver | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Troca, Violacao, Fronteira` | — |
| M-02 | catalogo-restricoes | declara cada restrição UMA vez (H1-H4, L1-L8, S1-S7, internas) com dois modos de uso | `aplicar(modelo, vars, ctx) -> None` · `verificar(escala, ctx) -> [Violacao]` · `catalogo(instancia) -> [Restricao]` | dominio |
| M-03 | avaliador | custo e violações de uma escala concreta | `avaliar(escala, ctx) -> Avaliacao{violacoes, custo, custo_por_restricao}` | dominio, catalogo-restricoes |
| M-04 | troca | máquina de estados da troca e regra de revalidação no aceite | `solicitar(escala, sol, dest, p1, p2) -> Troca` · `responder(troca, aceite, escala) -> ResultadoTroca` | dominio, avaliador |
| M-05 | fronteira | deriva contadores de fronteira da escala do mês anterior | `derivar(escala_anterior, pessoas) -> {pessoa_id: Fronteira}` | dominio |
| M-06 | solver-cpsat | adaptador do solver: monta o modelo CP-SAT a partir do catálogo, resolve, devolve Escala | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada}` | dominio, catalogo-restricoes, fronteira |
| M-07 | diagnostico | detecção estrutural de inviabilidade antes do solve, com conflito localizado | `analisar(instancia) -> [Conflito{plantao, exigidos, elegiveis}]` | dominio |
| M-08 | repositorio-json | adaptador de persistência em arquivos JSON | `salvar_escala/carregar_escala(id)` · `listar_trocas/salvar_troca` | dominio |
| M-09 | carregador | parse e validação da instância de entrada; aplica L4 (art. 59) como validação de configuração | `carregar(caminho) -> Instancia` (levanta `ErroDeValidacao`) | dominio |
| M-10 | gerador-sintetico | gera instâncias de teste reprodutíveis, incluindo instâncias inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-11 | cli | adaptador de entrada: os 5 casos de uso como comandos | `gerar · consultar · trocar · responder · conformidade` | todos |
| M-01 | dominio | entidades e objetos de valor; sem I/O, sem solver. `Escala` é entidade de dados — o cálculo de custo mora em `avaliador` (resolve a contradição ARQ-04); Domain Model aplica-se a `Troca` e `Restricao`, que têm comportamento próprio | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Troca, Violacao, Contexto, Evento` | — |
| M-02 | restricoes-legais | restrições de origem legal (L1 interjornada, L2 RSR, L3 regime 12×36 verificável, L4 limite de jornada) e a lógica de natureza-por-regime | `aplicar(modelo, vars, ctx)` · `verificar(escala, ctx) -> [Violacao]` · `fonte -> 'CLT art. N'` | dominio |
| M-03 | restricoes-modelo | restrições do INRC-II (H1-H4, S1-S7 com pesos publicados) e regras internas paramétricas, que têm a mesma forma | mesma interface de M-02 · `peso` · `origem ∈ {modelo, interna}` | dominio |
| M-04 | avaliador | custo, violações e distribuição por pessoa de uma escala concreta; deriva a fronteira validando a escala de origem | `avaliar(escala, ctx) -> Avaliacao{violacoes, custo, custo_por_restricao, distribuicao}` · `derivar_fronteira(escalas_anteriores, pessoas) -> {pessoa_id: Fronteira}` · `montar_contexto(...) -> Contexto` | dominio, restricoes-legais, restricoes-modelo |
| M-05 | troca | máquina de estados (PENDENTE → EFETIVADA/REJEITADA/RECUSADA/EXPIRADA/CANCELADA/ORFA) e revalidação contra a escala vigente no aceite | `solicitar(...)` · `responder(troca, aceite, escala, quem)` · `cancelar(troca, quem)` · `pendentes_de(pessoa)` | dominio, avaliador |
| M-06 | solver-cpsat | adaptador do solver: monta o modelo a partir das duas famílias de restrições, resolve, traduz status | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada, motivo}` | dominio, restricoes-legais, restricoes-modelo, avaliador |
| M-07 | diagnostico | inviabilidade estrutural pré-solve, com conflito localizado (só a verificação de elegibilidade; sem relaxação por camadas) | `analisar(instancia) -> [Conflito{plantao, exigidos, elegiveis}]` | dominio |
| M-08 | repositorio-json | persistência de snapshots imutáveis, com escrita atômica e id sanitizado | `salvar_escala/carregar_escala(id)` · `carregar_instancia` | dominio |
| M-09 | diario | log append-only de eventos com autor e carimbo; reconstrói a escala vigente | `registrar(evento, quem) -> Evento` · `eventos_de(escala_id)` · `escala_vigente(escala_id) -> Escala` | dominio |
| M-10 | carregador | parse e validação da instância: L4 como validação de configuração, limites de tamanho, erro por campo, guarda de peso de regra interna | `carregar(caminho) -> Instancia` (levanta `ErroDeValidacao` com campo e artigo) | dominio, restricoes-legais |
| M-11 | gerador-sintetico | instâncias reprodutíveis por semente, incluindo inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-12 | cli | adaptador de entrada: os 5 UCs mais `trocas` (tomada de ciência), com saída legível e mensagens citando a regra e o artigo | `gerar · consultar · trocar · responder · trocas · conformidade` | todos |
| M-01 | dominio | entidades, objetos de valor e `Contexto` (construtor exige fronteira) | `Pessoa, Contrato, TipoDeTurno, Plantao, Preferencia, RegraInterna, Alocacao, Escala, Evento, Troca, Violacao, Contexto, Fronteira` | — |
| M-02 | restricoes-legais | L1 interjornada, L2 RSR, L3 regime 12×36 verificável, L4 jornada; natureza-por-regime. INV-2: sempre rígidas, sem peso | `aplicar(modelo, vars, ctx)` · `verificar(escala, ctx) -> [Violacao]` · `fonte -> 'CLT art. N'` | dominio |
| M-03 | restricoes-modelo | H1-H4, S1-S7 com pesos publicados, e regras internas paramétricas; dona da semântica de peso, inclusive a guarda ≤ 30 | mesma interface de M-02 · `peso` · `origem ∈ {modelo, interna}` | dominio |
| M-04 | avaliador | custo, violações, distribuição agregada e derivação de fronteira — tudo "percorrer a escala por pessoa" | `avaliar(escala, ctx) -> Avaliacao` · `derivar_fronteira(escalas, pessoas, horizonte_meses) -> {pessoa_id: Fronteira}` | dominio, restricoes-legais, restricoes-modelo |
| M-05 | troca | máquina de 5 estados (PENDENTE → EFETIVADA/REJEITADA/RECUSADA/EXPIRADA) e revalidação contra a escala vigente no aceite | `solicitar(...)` · `responder(troca, aceite, escala, quem)` · `cancelar(troca, quem)` → RECUSADA · `de(pessoa) -> {recebidas, enviadas}` | dominio, avaliador |
| M-06 | solver-cpsat | adaptador do solver: modelo a partir das duas famílias, resolve, traduz status | `gerar(instancia, fronteira, limite_s) -> ResultadoGeracao{escala, status, otimalidade_provada, motivo}` | dominio, restricoes-legais, restricoes-modelo |
| M-07 | diagnostico | inviabilidade estrutural pré-solve com conflito localizado | `analisar(instancia) -> [Conflito]` | dominio |
| M-08 | repositorio-json | dono do artefato único `snapshot + eventos`; escrita atômica; id sanitizado; expõe apenas a escala vigente | `carregar_escala(id) -> Escala` (vigente) · `criar_escala(escala)` · `anexar_evento(id, evento)` · `carregar_instancia(caminho)` | dominio |
| M-09 | carregador | parse e validação da instância: L4 como validação de configuração, limites de tamanho, erro por campo com artigo citado | `carregar(caminho) -> Instancia` | dominio, restricoes-legais |
| M-10 | gerador-sintetico | instâncias reprodutíveis por semente, incluindo inviáveis deliberadas | `gerar(n_pessoas, n_dias, semente, inviavel=False) -> Instancia` | dominio |
| M-11 | cli | 5 UCs + `trocas` (ciência), saída legível, mensagens citando regra e artigo | `gerar · consultar · trocar · responder · trocas · conformidade` | todos |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | troca | 🟡 | Assume que os dois plantões da troca pertencem à MESMA escala. Troca entre 30/09 e 01/10 (meses diferentes) não é modelada, e a escala é a unidade de revalidação |
| F-02 | diario | 🟡 | Toda leitura da escala vigente reprocessa todos os eventos desde o snapshot. Sem compactação nem novo snapshot, o custo de `consultar` cresce linearmente com o número de trocas do mês |
| F-03 | diario | 🟡 | O diário grava "quem executou" a partir do mesmo parâmetro `--pessoa` que SEC-01 mostrou ser falsificável. A trilha é honesta sobre O QUE mudou e não sobre QUEM mudou; auditoria com autoria não verificável pode ser pior que nenhuma, por dar aparência de rigor a um registro que não a sustenta |
| F-04 | avaliador | 🟢 | reavaliação total da escala a cada troca, custo desproporcional à mudança de 2 alocações |
| F-05 | catalogo-restricoes | 🔴 | L3 (12×36) só existe como MODIFICADOR da natureza de outras regras (L1, L2, L4, L6, L7) — nenhum módulo verifica que o próprio regime está sendo cumprido (12h seguidas de 36h ininterruptas). O regime desliga quatro restrições e não é ele mesmo fiscalizado: uma escala 12×24 passa |
| F-06 | troca | 🟡 | EXPIRADA é derivada da data, não persistida: a troca "expira" no momento em que alguém a consulta. Nada grava quando expirou, e uma auditoria não consegue dizer em que momento o estado mudou |
| F-07 | fronteira | 🔴 | A fronteira deriva do mês anterior sem nenhuma correção de erro: se M-1 foi gerado com defeito ou alterado por trocas, o erro se propaga para M, M+1… sem sinal. Não há reconciliação nem detecção de deriva — o estado acumulado nunca é confrontado com a realidade |
| F-08 | solver-cpsat | 🟡 | `UNKNOWN` e `MODEL_INVALID` são tratados igual ("falha com o status bruto"), mas significam coisas opostas: MODEL_INVALID é defeito nosso, UNKNOWN é tempo esgotado sem solução viável. Colapsá-los apaga a informação que decidiria o que fazer |
| F-09 | carregador | 🟡 | `Preferencia` aceita `plantao_id` OU `data`: duas gramáticas para a mesma coisa, sem precedência definida quando ambos vêm preenchidos, e sem definir o que `data` significa sem tipo de turno (todos os turnos daquele dia?) |
| F-10 | repositorio-json | 🟡 | Caminhos derivados de ids vindos da entrada (`escala_<id>.json`): id contendo `../` escreve fora do diretório de dados — path traversal na escrita |
| F-11 | repositorio-json | 🔴 | Gravação não atômica: `salvar_escala` sobrescreve o arquivo. Interrupção no meio (Ctrl-C, disco cheio) deixa corrompida a escala publicada — que é simultaneamente a fonte da fronteira do mês seguinte e o alvo de todas as trocas. Não há backup nem escrita-e-troca-de-nome |
| F-12 | restricoes-modelo | 🟡 | Regras internas foram agrupadas com H1-H4/S1-S7 "porque têm a mesma forma paramétrica", mas têm origem e autoridade diferentes: uma vem de literatura com peso publicado, a outra é política local sem fonte. É o mesmo tipo de mistura que D2 acabou de desfazer no eixo legal × modelo, reintroduzido em outro eixo |
| F-13 | catalogo-restricoes | 🟡 | L6/L7 (adicional noturno, hora ficta) constam da tabela normativa mas nenhum módulo as implementa, porque cálculo de remuneração está fora de escopo. Requisito normativo listado sem módulo dono — rastreabilidade quebrada |
| F-14 | avaliador | 🟡 | "Recusa-se a propagar estado de escala com violações rígidas" assume que uma escala anterior violada é sempre erro. Mas ela pode estar legitimamente violada — troca efetivada antes de uma regra interna mudar, ou dado histórico anterior ao sistema. Sem caminho de override, UC-1 fica travado sem saída |
| F-15 | carregador | 🟢 | L4 vira validação de entrada e a mensagem deve citar o art. 59, mas não há especificação do catálogo de mensagens normativas — cada mensagem seria improvisada na hora |
| F-16 | diario | 🔴 | `escala_vigente(id)` = snapshot + eventos aplicados em ordem, mas a ORDEM não está definida: por carimbo de tempo (relógio, sujeito a colisão e a ajuste do sistema) ou por posição no arquivo? Duas implementações razoáveis do mesmo contrato produzem escalas vigentes DIFERENTES a partir dos mesmos dados |
| F-17 | solver-cpsat | 🟢 | A premissa A8 (pesos do INRC-II adequados ao contexto brasileiro) está declarada mas nenhum critério de aceitação a testa — premissa científica sem plano de verificação |
| F-18 | restricoes-legais | 🟡 | A guarda "peso de regra interna ≤ 30" ficou no `carregador`, mas é semântica das restrições. Requisito sem dono claro: se outro caminho criar regra interna (o `gerador-sintetico`), a guarda não se aplica |
| F-19 | catalogo-restricoes | 🔴 | `verificar(escala, ctx)` assume que quem chama montou o `ctx` completo, inclusive a fronteira do mês anterior. UC-5 roda sobre uma escala publicada sem obrigação de carregar o mês anterior → L1/H3 na virada não são verificados e o relatório afirma "0 violações" sobre escala que quebra o art. 66 no dia 1º |
| F-20 | diario | 🟡 | O estado ORFA foi acrescentado à máquina de trocas, mas nada define QUEM ou O QUE dispara a transição: é detectada na leitura ou gera evento? Se for derivada na leitura, reintroduz exatamente o defeito que PRO-02 apontou — estado que muda sem registro |
| F-21 | troca | 🔴 | Estado órfão: uma troca PENDENTE cuja escala-base foi re-gerada com `--force` referencia plantões que podem não existir mais. A máquina de estados não tem transição para "a escala de referência desapareceu" — a troca fica pendente apontando para o vazio |
| F-22 | solver-cpsat | 🟡 | PR-2 (≤60 s) foi verificada com 9 variáveis, não com as ~2.700 do porte alvo. São três ordens de grandeza sobre um problema NP-difícil, sem nenhuma medição intermediária |
| F-23 | avaliador | 🟡 | UC-4 reavalia a escala INTEIRA (~19 restrições × 30 dias × 30 pessoas) a cada resposta de troca que altera 2 alocações. Não existe avaliação incremental, e essa é a operação interativa mais frequente |
| F-24 | carregador | 🟡 | Sem especificação de erro por campo para JSON malformado ou campo ausente: o modo de falha padrão é stacktrace bruto para um plantonista |
| F-25 | catalogo-restricoes | 🔴 | `aplicar` e `verificar` são duas implementações do mesmo contrato semântico e nada no contrato as obriga a concordar. É o caso literal de duas implementações corretas do mesmo contrato com comportamentos incompatíveis. Falta uma propriedade de consistência declarada — do tipo "toda escala gerada com as restrições aplicadas deve verificar sem violações" |
| F-26 | cli | 🔴 | A identidade vem por parâmetro (A5) e não há autenticação: `responder --pessoa p02 --aceitar` consente uma troca em nome de outra pessoa. Como o consentimento do par é a ÚNICA aprovação do produto, o mecanismo de aprovação inteiro é falsificável por um argumento de linha de comando |
| F-27 | avaliador | 🟡 | Absorveu fronteira, custo, distribuição por pessoa e a fábrica de `Contexto`: quatro responsabilidades. A divisão do catálogo (D2) foi justificada por tamanho, e o `avaliador` cresceu no mesmo movimento sem passar pelo mesmo critério |
| F-28 | troca | 🟢 | com CANCELADA, propor muitas trocas e cancelar as inconvenientes gera ruído sem custo para quem propõe |
| F-29 | solver-cpsat | 🔴 | O sistema decide automaticamente quem trabalha noites, fins de semana e feriados — decisão de impacto material sobre a vida das pessoas — e não há mecanismo de recurso: não existe ator que possa contestar uma alocação. A única saída é achar um par que aceite trocar; se ninguém aceitar, não há recurso algum |
| F-30 | solver-cpsat | 🟡 | A codificação de S2/S3 (consecutividade com mínimo e máximo, atravessando a fronteira) é a parte mais intrincada e `specs/technical/modelo-cpsat.md` só nomeia o idioma, sem pseudocódigo. Risco de implementação por intuição (AP7) |
| F-31 | diario | 🟢 | reprocessamento integral do log a cada leitura, custo desproporcional a consultar dois plantões |
| F-32 | cli | 🟡 | Sem notificações (fora de escopo) o destinatário só descobre a troca consultando — mas não existe comando "listar minhas trocas pendentes" na decomposição. Os 5 UCs cobrem solicitar e responder, não TOMAR CIÊNCIA. O fluxo de troca não tem como começar |
| F-33 | repositorio-json | 🔴 | Não há trilha de auditoria: as trocas mutam a escala publicada in loco. Após três trocas não existe registro da escala original nem de quem alterou o quê. A motivação declarada na Fase 0 é "conformidade auditável" e o artefato central é sobrescrito sem histórico |
| F-34 | solver-cpsat | 🟢 | Assume que toda pessoa é elegível a todo plantão da sua habilitação: não há noção de unidade/setor. Com duas unidades, a pessoa é alocada em ambas em dias alternados sem que nada perceba a distância |
| F-35 | troca | 🟡 | Não existe caminho para o solicitante CANCELAR a própria troca. Quem pediu por engano só pode esperar o par recusar ou o plantão passar |
| F-36 | catalogo-restricoes | 🟡 | O peso das regras internas é arbitrado (o exemplo INT-01 usa 25, que não vem de lugar nenhum) e compete na MESMA função objetivo com os pesos calibrados do INRC-II. Um peso interno mal escolhido domina S1-S7 sem que ninguém perceba |
| F-37 | restricoes-legais | 🟢 | L3 virou verificável ("12h seguidas de ≥36h ininterruptas"), mas o art. 59-A não define tolerância: uma escala com 35h59 de descanso é violação? Não há fonte para arbitrar a tolerância, e o código precisará de uma |
| F-38 | avaliador | 🟡 | Não há relatório de distribuição por pessoa (quantos noturnos, fins de semana e feriados cada um recebeu). A injustiça produzida é invisível ao próprio sistema que a produz |
| F-39 | repositorio-json | 🟢 | `estado` nomeia duas máquinas de estados diferentes (da Escala e da Troca) no mesmo formato de arquivo — leitor e escritor podem discordar sobre qual vocabulário vale |
| F-40 | fronteira | 🟡 | S6/S7 acumulam ao longo do horizonte CONTRATUAL, que pode ser maior que um mês. Derivar apenas de M-1 perde o acúmulo dos meses anteriores a ele: a realimentação enxerga um passo atrás e trata isso como se fosse o histórico completo |
| F-41 | catalogo-restricoes | 🔴 | O módulo concentra ~19 restrições (H1-H4, L1-L8, S1-S7 e internas) × 2 modos ≈ 38 implementações, mais a lógica de natureza-por-regime. Não cabe em uma única interação com o contexto disponível → viola o princípio de granularidade E=I₀/C declarado na Fase 1 |
| F-42 | cli | 🟢 | UC-2 (consultar escala) não tem formato de saída definido; JSON cru é ilegível para quem só quer saber em que dias trabalha |
| F-43 | restricoes-legais | 🟡 | As duas famílias expõem a MESMA interface (`aplicar`/`verificar`) com semânticas de composição diferentes: legais são sempre rígidas e não somam custo; de modelo somam peso. Nada no contrato expressa a diferença — um chamador pode pedir o `peso` de uma restrição legal e receber algo sem sentido |
| F-44 | dominio | 🟢 | `Escala` não tem versão nem carimbo de geração: duas escalas do mesmo período são indistinguíveis, e não se sabe qual veio antes |
| F-45 | catalogo-restricoes | 🟡 | Preferência tem peso 10, o menor do conjunto: sacrificá-la é sempre matematicamente a saída mais barata. A escala "ótima" tende a violar sistematicamente as preferências das MESMAS pessoas (as mais flexíveis por contrato), e equidade foi removida dos critérios de aceite — o viés não tem métrica que o detecte |
| F-46 | troca | 🟡 | A máquina passou de 5 para 7 estados (+CANCELADA, +ORFA). Sintoma de AP2: a resposta à crítica de processo foi acrescentar estados. CANCELADA e RECUSADA são praticamente indistinguíveis (ambas terminam sem efetivar) e a distinção só serve à auditoria — que agora existe no diário e já registra quem encerrou |
| F-47 | avaliador | 🟢 | O relatório de distribuição por pessoa expõe a carga individual de todo mundo a quem rodar o comando: resolveu a visibilidade do viés (ETI-03) criando exposição de dado pessoal de terceiros |
| F-48 | avaliador | 🟡 | Ler N meses anteriores "conforme o horizonte contratual" não tem limite declarado: um contrato de horizonte anual faz UC-1 carregar e verificar 12 escalas. A realimentação ficou sem janela máxima |
| F-49 | carregador | 🟡 | JSON carregado sem limite de tamanho nem de profundidade; A6 assume entrada não hostil. Instância com 10^6 plantões esgota memória antes de qualquer validação |
| F-50 | fronteira | 🟡 | Não há referência para "derivar contadores a partir de uma escala pronta". O INRC-II define `history` como DADO DE ENTRADA da competição, não como algo derivado; a derivação é invenção nossa, sem fonte bibliográfica |
| F-51 | cli | 🟡 | A rejeição cita a regra violada, mas não há especificação de mensagem legível: "H3 violado" é inútil para o usuário-alvo; "você ficaria com 9h de descanso entre 14/09 e 15/09 e a lei exige 11h (CLT art. 66)" é o que o produto promete |
| F-52 | fronteira | 🟡 | A-3 assume mês anterior publicado e completo. O código não distingue "não existe mês anterior" (primeiro mês, correto) de "existe mas não foi encontrado" (caminho errado) — os dois produzem fronteira vazia e escala silenciosamente ilegal na virada |
| F-53 | cli | 🟡 | `trocas --pessoa X` lista as pendentes DIRIGIDAS a ela, mas nada mostra as que ELA propôs e aguardam resposta. Metade do fluxo segue invisível — para o solicitante, o pedido some depois de enviado |
| F-54 | diario | 🟢 | Sem especificação do formato do evento (JSONL? um arquivo por escala?) nem do conjunto fechado de tipos de evento |
| F-55 | troca | 🟡 | `decidida_em` registra quando, mas nada registra QUEM executou o comando (só quem era o destinatário esperado). Combinado com SEC-01, nenhuma ação do sistema é atribuível a uma pessoa |
| F-56 | diario | 🔴 | `diario.escala_vigente()` e `repositorio-json.carregar_escala()` devolvem o MESMO tipo `Escala` com significados diferentes (vigente × snapshot publicado), e nada no tipo os distingue. UC-5 chamando o repositório em vez do diário relata conformidade de uma escala que não é a que vale — e a promessa central do produto é justamente esse relatório |
| F-57 | solver-cpsat | 🟡 | Não há caminho barato para re-geração parcial: mudar um plantão custa o mesmo que gerar o mês do zero. A dor declarada na Fase 0 é "tempo do gestor" e a re-geração é justamente o caso comum |
| F-58 | fronteira | 🟢 | Módulo de função única dependendo só de `dominio`; poderia ser função de `avaliador`. Granularidade abaixo do útil — custa arquivo e import sem ganhar isolamento testável |
| F-59 | cli | 🟢 | sem autenticação, o "acordo entre pares" pode ser executado unilateralmente por qualquer um |
| F-60 | diario | 🔴 | Append-only só é seguro se o append for atômico. Escrita parcial de uma linha (disco cheio, Ctrl-C) corrompe o diário — e o diário passou a ser a ÚNICA fonte da escala vigente. D1 trocou um arquivo corrompível (V(1)) por um arquivo corrompível cujo dano é irrecuperável, porque não há mais estado redundante para reconstruir |
| F-61 | diario | 🟡 | O diário é append-only por convenção do código, não do sistema de arquivos: qualquer pessoa edita o JSONL num editor de texto e reescreve a história. Sem encadeamento por hash, nada detecta a adulteração — a trilha de auditoria não é à prova de violação |
| F-62 | dominio | 🟡 | Domain Model declarado diz "Escala sabe calcular seu custo", mas o cálculo mora em `avaliador` (M-03). Ou `Escala` ganha o método e passa a depender de `catalogo-restricoes` (ciclo dominio→catalogo→dominio), ou o modelo é parcialmente anêmico. A contradição não está resolvida |
| F-63 | catalogo-restricoes | 🟡 | Preferências são auto-reportadas e influenciam a alocação via S4, sem custo nem limite. Declarar tudo como indesejado é estratégia dominante: quem declara mais preferências recebe mais consideração |
| F-64 | troca | 🟡 | Incentivo assimétrico: nada impede alguém de propor sistematicamente trocas que despejam plantões indesejados e aceitar só as vantajosas. Não há limite de propostas nem visibilidade do padrão — o design assume cooperação |
| F-65 | cli | 🟢 | o processo não tem passo em que o destinatário toma ciência da troca pendente |
| F-66 | restricoes-modelo | 🟡 | A divisão reduziu o tamanho do módulo, mas S2/S3 continuam sem pseudocódigo: IMP-02 não foi resolvido em V(2) nem aceito explicitamente — foi herdado por outro módulo sem tratamento |
| F-67 | dominio | 🟡 | `TipoDeTurno` com `fim` < `inicio` (noturno 19:00→07:00) significa implicitamente "vira o dia", e isso não está no contrato. Uma implementação razoável calcularia duração negativa — e é exatamente esse cálculo que sustenta a compilação de L1 em sucessões proibidas |
| F-68 | repositorio-json | 🟢 | Toda leitura recarrega o arquivo completo e `listar_trocas` relê tudo a cada chamada. Irrelevante no porte alvo; degrada linearmente |
| F-69 | cli | 🟡 | A orquestração do UC-1 (carregar→fronteira→diagnóstico→solver→salvar) mora no `cli`, que depende dos 10 outros módulos. Não há como testar o fluxo do caso de uso sem passar por `argparse` |
| F-70 | catalogo-restricoes | 🔴 | Nada obriga uma restrição a implementar `aplicar` e `verificar` coerentemente. Uma restrição pode aplicar corretamente no solver e ter `verificar` devolvendo lista vazia — o gerador respeita a regra, o relatório nunca a fiscaliza, e o defeito passa em silêncio |
| F-71 | diagnostico | 🟡 | A abordagem (2), relaxação por camadas, está descrita como ideia: não define quais camadas nem em que ordem. Se a (1) não explicar o caso, não há referência para implementar na sessão |
