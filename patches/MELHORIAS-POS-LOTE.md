# Melhorias a aplicar depois do lote — inventário consolidado

Escrito em 2026-08-11, com 9 dos 12 projetos fechados. Consolida o que hoje está espalhado
por `ACHADOS-METODO.md`, `ACHADOS-TAXONOMIA.md` e os pedidos avulsos em `patches/`.

**Nada aqui foi aplicado.** A operadora decidiu em 2026-08-11 adiar todas as correções para
depois do lote, para que os doze rodem sob instrumento único. Este arquivo existe para que
a decisão não custe a memória de por que cada item entrou.

**Como ler cada item:** o que muda, a evidência com projeto e número, onde vive a mudança
(guidance / gate / ferramenta de análise / redação do paper), e o custo.

**Ordem:** por força da evidência, não por facilidade. **A seção 0 é de integridade e vem
antes de todas** — as demais melhoram a medição; ela protege a confiabilidade do que é
medido.

**Documento irmão, e é normativo:** `CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md`, na raiz.
Ele fixa **a regra que autoriza uma trava** — só vira gate o que é propriedade de *forma*
(existência, valor em conjunto fechado, referência estrutural) **e** tem falha observada e
corretamente diagnosticada no corpus. Qualquer item deste inventário que proponha gate deve
passar por essa regra antes; foi ela que reprovou o antigo E1.

---

# 0. INTEGRIDADE — o gate de testes é forjável, e o estado não registra proveniência

**Prioridade máxima, acima de tudo o que vem depois. Levantado pela operadora em
2026-08-11: *"o agente não pode falsificar resultados para garantir protocolo cumprido"*.**

## 0.1 O que aconteceu, com precisão

**Nenhuma falsificação ocorreu no corpus.** Isto precisa ficar dito antes de tudo, porque
o achado não é "o agente mentiu" — é "o mecanismo permite mentir em silêncio".

Em três de dez projetos o hook `test-outcome.js` não foi invocado pelo harness, o gate
`tests_passing` travou com a suíte verde, e o agente destravou alimentando o classificador
manualmente. **Nos três, com a saída real, e nos três declarando o contorno em chat.** O
T30 foi além do que o protocolo pede:

> *"O que NÃO foi feito: gravar 'pass' à mão no `state.json`, nem alimentar o hook com
> texto sintético para abrir o portão — houve uma invocação com texto sintético durante o
> diagnóstico, e ela foi substituída pela execução real antes do `advance_phase`."*

Declarou uma invocação sintética intermediária **que ninguém teria como notar**.

**E é justamente aí que está o defeito:** ninguém teria como notar. Três agentes escolheram
a honestidade; o mecanismo não a exigiu em nenhum momento. Um gate cuja integridade depende
da boa-fé de quem ele fiscaliza não é um gate — é uma instrução com aparência de trava, que
é exatamente a classe que este lote documenta quatro vezes e que custou dois descartes.

## 0.2 A superfície, verificada no bundle 0.14.2

```
process.stdin.on("end", () => {
  const hookInput = JSON.parse(input);              // <- qualquer JSON serve
  const command = hookInput.tool_input?.command || "";
  if (!isTestCommand(command)) { emit(); return; }  // <- só confere que PARECE teste
  const output = ... hookInput.tool_response ...;   // <- texto arbitrário
  const outcome = detectOutcome(output);            // <- casamento de padrão em prosa
  engine.recordTestOutcome(command, outcome === "fail");
});
```

E o que fica gravado:

```js
this.state.lastTestOutcome = { outcome, phase, at };   // três campos, zero proveniência
```

Basta isto para abrir o portão:

```bash
echo '{"tool_input":{"command":"npm test"},"tool_response":"53 passed"}' | node test-outcome.js
```

Indistinguível, no estado, de uma execução verdadeira.

## 0.3 O que é possível e o que não é — sejamos honestos

**Não dá para tornar isto inforjável** contra um agente com shell na mesma máquina.
Qualquer segredo em `.versus/` é legível por ele; qualquer verificação local é
contornável por quem executa comandos. Prometer inforjabilidade seria repetir o erro de
chamar instrução de trava.

**O alvo correto é outro, e é alcançável:** que forjar exija uma **mentira explícita** e
que o resultado seja **auditável depois**. Hoje não exige nem uma coisa nem outra.

## 0.35 O que é demonstrável e o que não é — separação feita pelo agente do T31

**Correção de 2026-08-12.** O agente do T31, ao ser questionado se o problema era defeito
do Versus, separou três coisas que eu vinha tratando como uma:

| | status |
|---|---|
| **Fragilidade A** — classificar por texto do stdout em vez de código de saída | **defeito de projeto, demonstrado**: `-q` no `pytest.ini` mais `-q` na linha vira `-qq`, some o resumo, suíte 100% verde fica inclassificável. O exit code 0 estava lá e não é usado |
| **Fragilidade B** — "não observado" e "observado e reprovado" produzem a mesma mensagem | **defeito de projeto, demonstrado**: para achar um `fail` obsoleto travando tudo foi preciso ler `.versus/state.json` à mão, furando a interface MCP |
| **o gancho não dispara** | **não determinado.** Verificado que não dispara, que a declaração está correta, que ganchos irmãos funcionam e que ele grava certo quando chamado à mão. **O porquê, não** |

E a razão de não chamar a terceira de defeito:

> *"Acabei de escrever a lição 7 sobre o custo de afirmar fato negativo a partir de
> observação parcial; repetir o padrão na frase seguinte tornaria a lição decorativa."*

**Eu vinha afirmando a terceira como causa estabelecida.** Corrigido aqui, em `§M1` e no
`LOG-OPERACAO.md`.

### Por que isto fortalece o patch em vez de enfraquecer

As duas fragilidades demonstráveis **corrigem o dano independentemente da causa**. Não é
preciso saber por que o gancho não dispara para que:

- classificar pelo **código de saída** torne a suíte verde sempre classificável, qualquer
  que seja a configuração de saída do runner;
- **expor `lastTestOutcome` e dizer o que o motor viu por último** transforme uma paralisia
  muda numa condição diagnosticável em segundos.

Nas palavras do agente: *"os dois consertos são baratos e teriam poupado esta sessão inteira
de depuração"*.

**Consequência para a ordem do patch:** as mudanças (3) e (5) abaixo deixam de ser
complementares e passam a ser **as principais** — são as únicas apoiadas em defeito
demonstrado. As demais seguem justificadas, mas por dano observado, não por defeito
provado.

## 0.4 As cinco mudanças

> **Leia a §0.35 antes:** (3) e (5) são as apoiadas em defeito demonstrado; as outras
> três, em dano observado.

### (1) Proveniência no registro — a mais importante e a mais barata

`lastTestOutcome` passa a carregar:

```js
{ outcome, phase, at,
  source: "harness" | "manual" | "unknown",
  toolUseId, sessionId,
  outputSha256, outputBytes,
  exitCode }        // se o payload trouxer
```

Com isso, **contorno deixa de ser invisível**. Não impede nada; torna tudo legível num
post-mortem, que é o que faltou nos três casos — a honestidade veio do agente, não do
arquivo.

### (2) Casar o `toolUseId` com o transcript da sessão

O payload de `PostToolUse` traz `transcript_path`. No `advance_phase`, o gate confere que o
`toolUseId` gravado **aparece no transcript** — isto é, que existiu de fato uma chamada de
Bash correspondente naquela sessão.

É a verificação mais forte implementável: forjar passa a exigir escrever no transcript, o
que é uma falsificação deliberada de registro, não um atalho para destravar. E se o
`toolUseId` estiver ausente, o gate recusa **dizendo por quê**.

### (3) Parar de classificar prosa — usar o código de saída

Toda a família `CLEAN_MARKERS` / `PASS_MARKERS` / `FAIL_MARKERS` existe porque o hook lê
texto. Se o payload de `PostToolUse` do Bash trouxer o status de saída — **verificar; não
consegui confirmar daqui** —, o hook passa a keyar nele.

Dois ganhos de uma vez: some a fragilidade de marcadores que causou §M1 (b)+(c) em dois
projetos, e forjar deixa de ser "escrever uma string plausível" e passa a ser "fabricar um
campo estruturado".

O T30 já demonstrou a versão pobre disto por conta própria: `&& echo All tests passed`,
*"que só executa se o runner sair com código 0"*. O agente inventou a ligação com o exit
code porque o hook não a tinha.

**E o T31 fechou o caso com uma terceira causa, que nenhuma lista de marcadores resolve:**
o `pytest.ini` do projeto traz `-q` em `addopts`; acrescentar `-q` na linha de comando
produz **`-qq`**, que suprime **inteiramente** a linha de resumo. Uma suíte 100% verde fica
inclassificável.

> *"Uma flag inocente do usuário, em arquivo de configuração legítimo, é suficiente para o
> portão travar. O código de saída do processo (0) era inequívoco e não foi usado."*

Três causas distintas em quatro ocorrências — ordem das palavras (T21, T30), hook não
invocado (T28, T31), saída suprimida por config (T31). **A única que as cobre todas é usar
o código de saída.**

### (4) `unknown` grava estado, e a recusa fala

Já pedido em `PEDIDO-M1-test-outcome.md`, e agora com terceira ocorrência. Sem isto, um
`fail` antigo fica congelado e **não há caminho de recuperação pela ferramenta** — que é o
que empurra para o contorno em primeiro lugar.

### (5) Expor `lastTestOutcome` e fazer a recusa dizer o que o motor viu

**Acrescentado em 2026-08-12, do T31-precos, e é o mais barato de todos.**

Hoje a mensagem de bloqueio diz apenas *"the engine did not witness a passing test run"*.
Isso torna **"não observado" indistinguível de "observado e reprovado"**, e não há
ferramenta MCP que exponha `lastTestOutcome`. O agente do T31 registrou a consequência:

> *"para descobrir que o motor guardava um 'fail' obsoleto de 02:34 eu tive de LER
> `.versus/state.json` diretamente, **contornando a interface que a metodologia oferece**.
> Um operador sem esse recurso ficaria preso sem diagnóstico possível."*

**A interface obriga a contorná-la.** Duas linhas resolvem: `getPhaseState` devolve
`lastTestOutcome` (outcome, quando, por qual caminho), e a recusa diz o que foi visto por
último em vez de só negar.

Isto interage com (1): com proveniência gravada **e** exposta, o contorno deixa de ser
invisível e o diagnóstico deixa de exigir leitura de arquivo interno.

> **A ordem causal importa para o desenho.** O contorno não nasceu de má-fé: nasceu de um
> gate que travava com o critério satisfeito e sem saída. Corrigir só a forjabilidade sem
> corrigir a paralisia produziria agentes travados em vez de agentes honestos. **As quatro
> mudanças são um pacote.**

## 0.5 Evidência acumulada

| projeto | marcadores casavam? | hook invocado? | contorno declarado? |
|---|---|---|---|
| T21-certificados | não | não | **sim** |
| T28-agenda | **sim** | não | **sim** |
| T30-notifica | não → corrigido em voo | **não** | **sim**, incluindo a invocação sintética de diagnóstico |

| T31-precos | não — `-qq` suprimiu o resumo | **não** (experimento controlado) | **sim**, com comando e saída |

**Quatro em onze — 36%.** Deixa de ser anedota. E o T31 fecha o diagnóstico com experimento
controlado: ganchos irmãos disparam no mesmo ambiente — `UserPromptSubmit` injeta contexto
a cada turno e `PreToolUse/Bash` **bloqueou um `rm -f` de verdade** —, o `test-outcome.js`
funciona quando invocado direto, **e ainda assim cinco execuções verdes não alteraram o
estado**. Ganchos disparam; ganchos sobre Bash disparam; este não.

## 0.6 Para o §7, e vale como achado

O que este lote mostra sobre *evidence-gating* não é que ele funciona ou não funciona. É
mais fino:

> Um critério com evidência cuja evidência é **texto não autenticado** oferece a mesma
> garantia de um booleano carimbável, com custo maior. A diferença entre os dois está na
> proveniência do dado, não na existência de um verificador.

Nos três casos o registro é confiável **porque o agente declarou**, não porque o
instrumento garantiu. Isso é dado sobre o comportamento dos agentes — favorável — e dado
sobre o instrumento — desfavorável. Os dois entram.

## 0.7 O critério de saída registra a afirmação, não o estado do mecanismo

**Levantado pela operadora em 2026-08-11: *"seria necessário reforçar os protocolos de
saída das fases para garantir auditabilidade?"*. Sim — mas não onde eu supunha.**

### O que eu supunha, e o que a medição mostrou

Supus que os critérios fossem rasos e que a auditoria dependesse do log narrativo. Medido
nos dez projetos:

| canal | registros | caracteres | média | sem detalhe |
|---|---|---|---|---|
| `record_decision` | 323 | 385 mil | 1190 | — |
| critérios de saída | **390** | **309 mil** | **791** | **0** |

**Os critérios são substanciais.** A hipótese estava errada e o problema é outro.

### O problema, demonstrado no caso que conhecemos

O que o critério `tests_passing` registrou nos três projetos em que o gate foi contornado:

| projeto | detalhe gravado |
|---|---|
| T21 | *"Execução verde real, não assumida (S4): npm test → 63 testes, 63 pass, 0 fail…"* |
| T28 | *"64/64 testes verdes em 10,93 s… (saída lida, não assumida — S4)"* |
| T30 | *"53 de 53 testes verdes… execução real de `npm test`, não afirmação"* |

**Os três são verdadeiros e específicos. Nenhum menciona que o hook falhou e foi alimentado
à mão.**

Não é desonestidade: o campo pede evidência de que os testes passam, e passavam. Mas **um
auditor que lesse apenas os critérios concluiria que o gate funcionou nos dez projetos.** O
contorno é conhecido só porque o agente escreveu um `record_decision` à parte, por
iniciativa própria — em dois dos três casos, já na Fase 7.

**A lacuna, enunciada:** o critério registra **o que se afirma**, não **como se verificou**
nem **se o caminho de verificação estava íntegro**. É a mesma falta de proveniência da
§0.2, um nível acima — lá no dado, aqui no ato.

### Auditabilidade ≠ exigibilidade, e o desenho atual colapsa as duas

A classificação forma-vs-qualidade estabelece que propriedade de qualidade **não pode virar
gate** — indecidível, Rice. Correto. Mas o desenho atual conclui daí que ela só pode ser
**declarada**, e declarar não deixa rastro.

**Não gateável não implica não auditável.** Uma afirmação de qualidade pode perfeitamente
exigir: qual artefato a sustenta, quem a produziu, por qual caminho. Isso não a torna
verificável por máquina; torna-a **revisável por uma pessoa depois**, que é exatamente o
que falta hoje.

Vale acrescentar um terceiro eixo à tabela da classificação:

| natureza | falha observada? | trava? | **registro exigido** |
|---|---|---|---|
| forma | sim | **gate** | claim + artefato + **proveniência** |
| forma | não | declarar | claim + artefato |
| **qualidade** | — | **nunca** | **claim + artefato + quem julgou** |

### As três mudanças

**(1) Todo critério com evidência registra o caminho de verificação, não só o resultado.**
Campo novo: como foi verificado (comando, artefato, hash) e **se o caminho foi o nominal**.
Nos três casos do `tests_passing`, isso teria capturado o contorno no próprio critério, sem
depender de o agente lembrar de escrever uma decisão separada.

**(2) Degradação do mecanismo é registro obrigatório, não voluntário.** Se um hook não
disparou, se um gate foi satisfeito por caminho alternativo, se uma ferramenta foi
substituída — isso vira campo do critério. Hoje depende de boa-fé, e boa-fé foi o que
tivemos; três em três. Não é base para um método.

**(3) Critério de qualidade passa a exigir procedência do julgamento**, mesmo sem trava:
quem julgou, sobre qual artefato. O lote mostra por que importa — a procedência do human-AV
varia entre os dez projetos e só é reconstruível porque os agentes a narraram
espontaneamente.

### O que NÃO fazer

**Não acrescentar critérios.** Já são 390 em dez projetos, ~39 por projeto, todos com
detalhe. Mais critérios aumentam a superfície de AP1 — autorreportar conformidade — sem
aumentar auditabilidade. **O ganho está em enriquecer o registro dos que existem, não em
multiplicá-los.**

E vale a regra de viés da classificação também aqui: instrumentar por hipótese é o mesmo
erro que gatear por hipótese. As três mudanças acima têm falha observada — as três
ocorrências do §M1.

### O achado, para o texto

> Nos dez projetos, **todo defeito de método que encontrei veio do log narrativo**
> (`record_decision`), não dos critérios de saída. Os critérios registram conformidade com
> precisão; a narrativa registra o que deu errado no caminho. Um método que quer ser
> auditável precisa dos dois — e hoje só o primeiro é obrigatório.

---

# A. Lacuna estrutural — o método não reverifica o que ele mesmo decide

**É a contribuição mais forte do lote depois do resultado principal, e a de correção mais
barata, porque o vínculo já existe: tudo tem id.**

| o método estabelece | onde | quem verifica que sobrevive ao código |
|---|---|---|
| **premissa** da arquitetura (P-Ax) | Fase 1 | **ninguém** |
| **resolução** de achado crítico | Fase 3 | **ninguém** |

Três projetos, três mecanismos independentes, e os três só apareceram por acaso favorável.

## A1. Verificar na Fase 6 que os críticos resolvidos na Fase 3 seguem resolvidos

**Evidência:**

| projeto | o que a Fase 3 estabeleceu | o que a Fase 5 fez | como apareceu |
|---|---|---|---|
| T26-extratos | erradicar o O(n²) que PRF-01/PRF-02 apontaram | **reintroduziu em três lugares** | VAL-4 tinha cronômetro (120 s contra 60 s) |
| T27-despesas | refinamento de CA-3 sobre delegação, **aprovado pelo operador** | não implementou — item aparecia nas duas bandejas | smoke test de delegação existia |

Registro do T26, literal: *"é exatamente o O(n²) acidental que PRF-01 e PRF-02 mandaram
erradicar, reintroduzido na função de filtro"*.

**O que muda:** a Fase 6 passa a exigir, para cada achado **crítico** resolvido na Fase 3,
ou o teste que o cobre ou a razão de não haver. Os gates atuais da Fase 5 checam módulos
entregues, specs consultadas, S6 aplicado e UI executável — nenhum pergunta se a
implementação preservou o que a crítica resolveu.

**Onde vive:** novo critério de saída da Fase 6, com evidência (não booleano carimbável).

**Custo:** baixo. A matriz já tem id por achado e a Fase 3 já registra a resolução. É
casamento de listas.

## A2. Verificar que as premissas da Fase 1 valem no sistema construído

**Evidência — T29-retencao.** A premissa **P-A8** afirmava *"a migração é streaming ponto a
ponto via Iterator"*, e o padrão Iterator foi escolhido na Fase 1 exatamente para isso.
Medido:

| pontos | pico de memória |
|---|---|
| 10 mil | 1,9 MB |
| 500 mil | 74,7 MB |
| 2 milhões | **330 MB de RSS** |

Linear na entrada, ~150 bytes por ponto. *"A premissa está refutada pelo próprio código."*

**Por que a lente PRE não pega:** criticar a **plausibilidade** de uma premissa na Fase 2 é
outra coisa que **medir se ela vale** no que foi construído. P-A8 passou pela crítica,
sobreviveu a duas iterações do laço, e era falsa.

**O critério, formulado pelo próprio registro do T29 e generalizável:**

> *"uma premissa só está protegida quando existe um teste que a mediria falhando"*

**O que muda:** a Fase 6 declara, para cada premissa numerada da Fase 1, o teste que a
protege ou a razão de não haver.

**Onde vive:** critério de saída da Fase 6, irmão de A1.

**Custo:** baixo. A Fase 1 já numera as premissas.

---

# B. A verificação falha de formas que nenhum safeguard cobre

Cinco formas distintas de **teste verde que não testa**, em seis projetos. O AP5 pressupõe
que a verificação verifica; nenhum gate cobre a classe.

| forma | onde | o que falha |
|---|---|---|
| cenário errado | T21, T24 | o teste monta um cenário que não exerce o critério |
| cobertura parcial do achado | T22, T23 | a correção fecha um caminho, o defeito volta por outro |
| condição inalcançável | T23 | a condição que o teste exerceria não pode ocorrer |
| invariante por construção | T25 | o teste passa com a premissa verdadeira **ou** falsa |
| *(A1/A2 acima são a sexta e sétima)* | | |

O caso mais nítido é o T23: com `tamanho_janela == amostra_minima == 50` e
`deque(maxlen=50)`, `volumes_comparaveis` **nunca retornava falso**. A defesa contra REG-01
tinha correção, tinha teste, o teste passava, e a condição era inalcançável. **62 testes
verdes não notaram.**

## B1. Fase 6 pedir medida de poder de detecção, não só "testes passando"

**Evidência de que funciona, e de que os agentes já sabem disso:** teste de mutação foi
adotado **por iniciativa própria em 3 de 9 projetos** — T22, T23 e T27 —, **sem estar na
guidance**. Foi ele que pegou o defeito do T23; e no T23 o sintoma era numérico e legível:
desligar a checagem de volumes derrubava **2** testes contra **14** de outra mutação.

> Quando três execuções independentes convergem para a mesma prática não prescrita, a
> prática pertence ao método.

**O que muda:** o gate `tests_passing` passa a admitir, ou exigir, uma medida de poder —
mutação ou equivalente. Uma suíte verde e uma suíte capaz de reprovar não são a mesma
coisa.

**Onde vive:** critério de saída da Fase 6.

**Custo:** médio. Precisa decidir se é exigência ou recomendação forte, e o que conta como
medida aceitável em stacks sem ferramenta de mutação pronta.

## B2. Registro de correção de teste declarar o CENÁRIO, não só a asserção

**Evidência — T21 e T24.** No T21 o primeiro diagnóstico trocou `45` por `100` na asserção;
o teste falhou de novo. O segundo achou a causa: limiares 90/60/30 contra certificado de
100 dias formam configuração **válida**, e CA-5 nunca foi exercido. Citação do registro:

> *"um teste que monta o cenário errado passa a testar o caminho feliz sem avisar"*

**O que muda:** frase na guidance da Fase 6 pedindo que o registro de correção diga qual
cenário o teste monta.

**Onde vive:** guidance. **Custo:** trivial. **Ressalva séria:** é instrução sem trava, e o
item E1 documenta quatro casos no lote em que isso não mudou comportamento — dois com
descarte de projeto. Não conte com o efeito.

---

# C. Práticas que emergiram sozinhas e deveriam estar no método

Nenhuma está na guidance. Todas foram adotadas por iniciativa do agente, em vários
projetos independentes, e todas produziram achado que o caminho padrão não produziria.

| prática | projetos | o que rendeu |
|---|---|---|
| **medição por estágio** antes de otimizar | T25, T26, T28, T29 | **4 de 9.** Palpite sobre desempenho errou em todos: T26 *"as duas correções anteriores eram reais mas não eram o gargalo"*; T28 o gargalo era `fsync` (37 ms/commit), não parsing nem algoritmo |
| **teste de mutação** | T22, T23, T27 | 3 de 9. Pegou a cobertura falsa do T23 |
| **micro-check por execução, não por leitura** | T23, T25, T26, T29 | 4 de 9. T25: *"só apareceu ao EXECUTAR o código, não ao lê-lo"*; T26: *"6 defeitos encontrados por RODAR, nenhum por ler"* |
| **mapa de testes derivado das specs, não do código** | T26, T29 | 2 de 9, adotado como mitigação do AP3. Rendimento não previsto: **encontra erros nas specs** — no T29, 3 das 5 falhas iniciais eram erro de spec (`METADATA_SIZE` documentado como 20 quando `struct.calcsize` dá 16, transcrito de um resumo) |

**C1 — a mais forte é a medição por estágio.** Quatro de nove, e nos quatro o palpite
inicial estava errado. Merece ser instrução explícita da Fase 6: *antes de corrigir
desempenho, medir por estágio*.

**Onde vivem:** guidance das Fases 5 e 6. **Custo:** baixo, são frases. **Ressalva:** ver E1 —
são instruções sem trava, e o histórico do lote diz que isso raramente basta. A diferença
aqui é que as quatro práticas **já foram adotadas espontaneamente**, ou seja, a instrução
estaria empurrando na direção em que os agentes já vão sozinhos.

---

# D. Taxonomia — gatilhos e a relação pergunta × gatilho

## D1. Reescrever o gatilho de ETI *(o mais forte dos gatilhos)*

**Texto atual:** *"Automated decisions about people (scoring, classification, moderation)"*
**Pergunta central:** *"Who is potentially harmed? Are there audit, correction, and
transparency mechanisms?"*

**Evidência — T25-orcamento é o caso limpo.** O sistema decide sobre **orçamento e corte de
serviço**. Os dois estimadores externos leram o gatilho e recusaram (*"não pontua,
classifica nem modera ninguém"*); a Fase 2 leu a pergunta central e ativou, com razão
substantiva: cortar o atendimento de uma entidade **afeta alguém**, e o painel é
exatamente o mecanismo de transparência que a pergunta cobra.

ETI ativou em apenas **3 de 9** projetos, o segundo menor do lote.

**Custo:** baixo, é texto. **Mas ver D3** — a decisão de fundo vem antes.

## D2. A relação pergunta × gatilho não é peculiaridade de uma lente

Já documentado em **quatro**: GOV, ETI, JOG e LIN. Em todos, o gatilho enumera condições
que a pergunta central não exige, e os leitores respondem a perguntas diferentes.

Exemplos textuais, com a justificativa do estimador citando o gatilho:

| lente | gatilho | leitura restritiva, estável em 3/3 rodadas |
|---|---|---|
| JOG | *"…public API, external integrations, marketplace or platform design"* | *"sem mercado aberto, API pública ou incentivos econômicos entre entidades independentes"* |
| LIN | *"…interface contracts between independent teams"* | *"contratos internos em TypeScript no mesmo repositório"* |

**Isto não é ruído de modelo:** dois modelos de famílias diferentes concordam entre si em
93% e com a Fase 2 em 87% e 80%.

## D3. **A decisão de fundo: gatilho é condição necessária ou lista de exemplos?**

Hoje as 12 são inconsistentes. **SUS é a única que diz explicitamente**:

> *"e.g. (but NOT only)… apply the central question, do not just match the examples"*

Ela diz isso porque foi reescrita na v0.12.9 depois de zerar em 7 projetos do ciclo 1. As
outras onze não dizem nada, e **o comportamento observado é que os leitores as tratam como
condição fechada**.

**Antes de mexer em D1, decidir D3 e redigir as doze uniformemente sob a escolha.** Corrigir
ETI isoladamente repete o erro de tratar o sintoma.

**Custo:** alto em cuidado, baixo em código. **É a mudança que mais altera a taxonomia
publicada**, e precisa aparecer no texto do paper — a RO3 mediu a taxonomia corrigida, não
a publicada, e o descompasso original é achado, não erro a esconder.

## D4. A distinção condicional × universal é empiricamente fraca

Série de ativações por projeto: **11 · 9 · 9 · 10 · 11 · 9 · 8 · 9 · 10** — média 9,6 de
12, sob os gatilhos largos da v0.12.9. No ciclo 1, com gatilhos estreitos, o máximo era 8 e
GOV e SUS ficaram em **0 de 7**.

Não é item de patch: é **achado para o texto**, com o antes e o depois medidos no mesmo
lote. Vira recomendação de trabalho futuro, não intervenção.

---

# E. Instrumento — gates e hooks

## E1. ~~`duplica` intra-lente precisa de trava~~ — **NÃO PODE VIRAR GATE**

**Corrigido em 2026-08-11, contra `CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md`.** A versão
anterior deste item pedia uma trava. Estava errada.

**O fato observado continua valendo:** a frase do item C1 entrou na guidance dizendo que
`duplica` vale dentro da mesma lente, e o gerador segue sem marcar esses casos — no T21,
três dos seis agrupamentos que só o juiz cego viu eram intra-lente (`UX-01+UX-06`,
`SEC-01+SEC-02`, `PRO-01+PRO-06`).

**Mas reconhecer que dois achados descrevem o mesmo defeito é propriedade de QUALIDADE**,
não de forma — indecidível mecanicamente, oráculo no sentido de Rice. A regra de viés da
classificação só autoriza gate sobre existência, valor em conjunto fechado ou referência
estrutural. "Deveria ter marcado" não é nada disso.

**E o lote tem a prova empírica**, que a classificação não tinha quando foi escrita: os
κ de 0,000 a 0,362 em dez projetos mostram que **nem dois modelos concordam** sobre o que
é o mesmo defeito. Uma trava precisaria decidir mecanicamente o que dois leitores
competentes não decidem igual.

**Destino: limitação declarada L-x**, exatamente como a classificação já propõe. O texto
dela serve como está, e o lote acrescenta o número:

> Um duplicado não marcado passa o gate e só é pego na análise ou na revisão humana. A
> reprodutibilidade dessa marcação foi **medida**: κ de Cohen entre o modelo gerador e um
> juiz cego independente, por projeto, ficou entre 0,000 e 0,362 em dez projetos. Não é
> causa de descarte automático, e o resultado principal sobrevive — a análise de
> sensibilidade move a contribuição exclusiva em ±2 e nenhuma lente se aproxima de zero.

**O que sobra como achado**, e é o mais forte: instrução sem trava não muda comportamento
— quatro casos no lote, dois com descarte de projeto. Mas neste caso específico **não há
trava possível**, o que torna o achado mais interessante, não menos: mostra o limite do
próprio evidence-gating.

## E2. `test-outcome.js` — **absorvido pela seção 0**

O conteúdo técnico deste item continua válido, mas a leitura correta está em **§0.4**: o
defeito de marcadores é higiene, a paralisia é grave, e **a forjabilidade é mais grave que
as duas**. As quatro mudanças formam pacote e não devem ser aplicadas em separado.

Detalhe histórico da inversão de prioridade, preservado:

Pedido escrito em `patches/PEDIDO-M1-test-outcome.md`, contra a v0.14.2. **A segunda
ocorrência mudou o diagnóstico**, e o pedido precisa ser reordenado antes de aplicar.

| ocorrência | stack | saída | casa os marcadores? |
|---|---|---|---|
| T21-certificados | `node:test` | `pass 68` / `fail 0` | **não** |
| T28-agenda | `pytest` | `64 passed in 10.95s` | **sim** |

No T28 o agente alimentou o hook à mão e ele classificou `pass` corretamente:
*"o hook funciona, mas não estava sendo invocado"*.

**Logo o defeito de marcadores nunca foi a causa raiz de uma paralisia observada.** O que
importa é o outro:

1. **`unknown` deve gravar estado**, com valor próprio, distinto de `pass` e `fail`. Hoje
   sai sem chamar `recordTestOutcome`, e um `fail` anterior fica congelado — **falha
   fechada e permanente, sem caminho de recuperação pela ferramenta**.
2. A mensagem de recusa deve **distinguir** "não reconheci a saída" de "os testes
   falharam". Foi o que faltou: o agente tentou cinco vezes sem sinal de que o problema era
   o hook.
3. `unknown` **não conta** para o `loopCounter` do S6.
4. Marcadores do `node:test` — higiene, não urgência.

**Custo:** baixo. **Nota:** dois contornos declarados em nove projetos, os dois divulgados
pelo agente por iniciativa própria. A frequência vai para o §7.

## E3. Tabela de módulos completa por versão

**Evidência — T23-canario.** A V(3) foi escrita como **delta**: 12 módulos em V(1), 12 em
V(2), **4** em V(3). Os outros oito projetos escreveram a tabela inteira.

**Delta e remoção são indistinguíveis pelo texto** — nos dois casos o nome sumiu da última
tabela —, e tentar resolver por carry-forward ressuscita módulos legitimamente removidos
(T21 12→13, T24 9→11, T22 11→14).

**Não afeta nenhuma medida da RO3**: os Passos 1 e 4 usam o módulo escrito em cada achado.
Item de higiene. **Custo:** trivial.

---

# F. Ferramentas de análise (minhas, não da extensão)

## F1. Rótulo de κ para valores nulos-por-baixo

`_interpretar` classifica qualquer `k < 0` como *"pior que acaso — discordam
sistematicamente"*. Ocorreu **três vezes** com κ de −0,001 e −0,004, que são
indistinguíveis de zero. A leitura correta é *nenhuma concordância além do acaso*, não
*discordância sistemática*.

**Corrigir uniformemente sobre os doze, depois que todos rodarem**, com o antes e o depois
visíveis. Não corrigi durante o lote porque seria a segunda vez que suavizo um rótulo
depois de ver resultado que não gostei — a primeira foi o `MIN_POSITIVOS`, já declarada
como A3 —, e duas formam padrão.

## F2. Terceiro juiz cego (Kimi) sobre os doze

Decidido em 2026-08-11, detalhado em `ACHADOS-METODO.md` §M7, com a expectativa declarada
**antes** de rodar. Separa duas hipóteses que o desenho de dois raters não distingue:

| resultado | inferência |
|---|---|
| Qwen ≈ Kimi, os dois longe do gerador | o conceito **é** definível a partir do pacote; a distância até o gerador é **assimetria de informação** |
| Qwen ≉ Kimi | o **construto** não é operacionalizável nessa granularidade |

Trabalho: ligar o Kimi ao subcomando `cegar_duplicatas.py julgar`, reaproveitando o
`_kimicode()` de `reestimar_lentes.py`.

## F3. Correlação ativação × número de iterações

Substitui a hipótese antiga de "MEC ativa por maturação", que foi **refutada** em
2026-08-11: MEC entrou já na iteração 1 no T21, ficou fora das duas no T22 e das **três** no
T27. Quem emergiu tarde foi **MIG**, no T26.

Emergência tardia é real, mas é propriedade de **quanto a arquitetura de cada projeto muda
ao ser criticada**, não de uma lente. A análise final deve correlacionar ativação contra
número de iterações **para todas as lentes**, não só MEC — é confundidor para a contagem do
§2, que assume cobertura determinada pelo domínio.

---

# G. Para o §7 do paper — limitações medidas, não declaradas

Não são patches. São coisas que o lote transformou de "limitação declarada" em "limitação
com número".

1. **A marcação de duplicatas não é reprodutível.** κ por projeto: 0,000 · 0,000 · 0,362 ·
   0,115 · 0,249 · 0,000 · −0,001 · 0,210 · 0,299. **O resultado sobrevive assim mesmo** —
   a análise de sensibilidade move a exclusividade em ±2 e nenhuma lente chega perto de
   zero. Instabilidade de magnitude, não de classificação.
2. **Dois contornos declarados do harness em nove projetos**, ambos divulgados pelo agente.
3. **Autoavaliação:** achados e marcações vêm do mesmo modelo gerador. A remarcação cega
   mede o tamanho do problema; não o resolve neste desenho.
4. **Procedência do human-AV varia entre os projetos** e precisa constar de qualquer
   comparação:

| projeto | quem executou | quem julgou |
|---|---|---|
| T24, T23, T25, T27, T28 | operador | operador |
| T21, T22, T26 | agente | operador |
| **T29** | **agente** | **operador aceitou sem executar** |

O T29 virou experimento natural que ninguém desenhou: foi o único sem verificação humana, e
**4 defeitos apareceram depois do "parece tudo bem"** do operador — três tracebacks vazando
e a premissa P-A8 refutada. Aprovação não é verificação, e a prova veio do projeto onde a
verificação foi declinada.
