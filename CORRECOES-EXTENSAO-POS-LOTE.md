# Correções na extensão Versus — especificação pós-lote

Escrita em 2026-08-12, com os doze projetos fechados. Contra a **v0.14.2**, o bundle que
rodou o lote inteiro.

**Escopo deste documento: só o que muda na extensão.** Guidance, gates, hooks, estado e
ferramentas MCP. O que é ferramenta de análise minha está em
`patches/MELHORIAS-POS-LOTE.md` §F; o que é decisão de taxonomia está no §D do mesmo
arquivo e resumido aqui na parte IV.

**Regra que governa tudo abaixo:** `CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md`. Só vira
trava o que é propriedade de **forma** (existência, valor em conjunto fechado, referência
estrutural) **e** tem falha observada e corretamente diagnosticada no corpus. Todo item
aqui passou por essa regra.

**Cada item traz:** o que muda, a superfície exata no código, a evidência, e o custo.

---

## Índice por prioridade

| # | item | tipo | custo |
|---|---|---|---|
| **I.1** | `unknown` grava estado no `test-outcome.js` | hook | baixo |
| **I.2** | expor `lastTestOutcome` em `get_phase_state` | MCP | **trivial** |
| **I.3** | recusa do `tests_passing` diz o que o motor viu | gate | trivial |
| **I.4** | classificar por código de saída, não por prosa | hook | médio |
| **I.5** | proveniência no `lastTestOutcome` | estado | baixo |
| **I.6** | casar `toolUseId` com o transcript | gate | médio |
| **II.1** | critério de saída registra o caminho de verificação | estado | médio |
| **II.2** | degradação de mecanismo é registro obrigatório | estado | baixo |
| **III.1** | Fase 6 confere críticos resolvidos na Fase 3 | gate | baixo |
| **III.2** | Fase 6 confere premissas da Fase 1 | gate | baixo |
| **III.3** | Fase 6 pede poder de detecção | gate | médio |
| **III.4** | tabela de módulos completa por versão | gate | trivial |
| **IV** | guidance — quatro práticas e o registro de cenário | texto | baixo |
| **V** | taxonomia — a decisão de fundo sobre gatilhos | texto | alto em cuidado |

---

# PARTE I — INTEGRIDADE DO GATE DE TESTES

**Prioridade máxima.** O `tests_passing` travou em **4 de 12 projetos (33%)** com a suíte
verde. Nos quatro o agente destravou alimentando o classificador com a saída real, e nos
quatro **declarou o contorno por iniciativa própria**.

**Nenhuma falsificação ocorreu.** O defeito é que o mecanismo não a impediria. Um gate cuja
integridade depende da boa-fé de quem ele fiscaliza é instrução com aparência de trava.

**Os seis itens formam pacote.** Corrigir a forjabilidade sem corrigir a paralisia produz
agentes travados em vez de agentes honestos — o contorno nasceu de um gate que travava com
o critério satisfeito e sem saída.

## I.1 — `unknown` deve gravar estado

**Superfície:** `test-outcome.js`, no `main()`:

```js
const outcome = detectOutcome(output);
if (outcome === "unknown") {
  emit();        // ← sai SEM chamar recordTestOutcome
  return;
}
```

E `isPhaseTestPassing()` lê o estado, não a execução:

```js
const t = this.state?.lastTestOutcome;
return !!t && t.outcome === "pass" && t.phase === phase;
```

**A composição é falha fechada e permanente.** Gravado um `fail`, qualquer execução
posterior classificada como `unknown` deixa o `fail` no lugar. Rodar os testes de novo, em
verde, **não muda nada**.

**O que muda:**

1. `unknown` **grava**, com valor próprio, distinto de `pass` e `fail`.
2. `isPhaseTestPassing()` recusa `unknown` como recusa `fail` — o gate segue fechado, o que
   está certo.
3. `unknown` **não conta** para o `loopCounter` do S6. Saída ilegível não é teste falhando.
4. O `catch { emit() }` no fim de `main()` também grava `unknown` — hoje um JSON malformado
   some sem rastro.

**Evidência:** T21, T28, T30, T31. Em todos, `lastTestOutcome` congelado num `fail` antigo.

## I.2 — Expor `lastTestOutcome` em `get_phase_state`

**O item mais barato do documento, e resolve o pior sintoma.**

**Superfície:** `handleGetPhaseState`, o objeto `result`. Hoje devolve 11 campos:

```js
const result = {
  projectName, projectDescription, projectSpec, currentPhase, currentIteration,
  phase0Score, decisionsCount, recentDecisions, safeguards, updatedAt
};
```

**`lastTestOutcome` não está entre eles** — o motor tem, a ferramenta MCP filtra.

**Consequência registrada pelo agente do T31:**

> *"para descobrir que o motor guardava um 'fail' obsoleto de 02:34 eu tive de LER
> `.versus/state.json` diretamente, **contornando a interface que a metodologia oferece**.
> Um operador sem esse recurso ficaria preso sem diagnóstico possível."*

**A interface obriga a contorná-la.** Acrescentar uma linha ao `result` resolve.

## I.3 — A recusa deve dizer o que o motor viu

**Superfície:** a mensagem de `verify: "test-pass"`:

> *"[Phase 6] tests_passing: the engine did not witness a passing test run in this phase.
> Run your test suite so the result is verified by the test-outcome hook…"*

Ela torna **"não observado" indistinguível de "observado e reprovado"**, e não diz quando.
O agente do T21 tentou cinco vezes sem sinal de que o problema era o hook.

**O que muda:** a mensagem passa a citar `lastTestOutcome` — outcome, horário, comando — ou
a dizer explicitamente que **nada foi registrado nesta fase**. São duas frases.

## I.4 — Classificar por código de saída, não por prosa

Toda a família `CLEAN_MARKERS` / `PASS_MARKERS` / `FAIL_MARKERS` existe porque o hook lê
texto. **Três causas distintas de falha em quatro ocorrências**, e nenhuma lista de
marcadores cobre as três:

| projeto | causa |
|---|---|
| T21, T30 | o repórter do `node:test` imprime `pass 68` / `fail 0` — ordem inversa à esperada |
| T28 | os marcadores **casavam** (`64 passed in 10.95s`) e o hook não foi invocado |
| T31 | `-q` no `pytest.ini` + `-q` na linha = **`-qq`**, some o resumo, suíte 100% verde fica inclassificável |

O T31 é decisivo: *"Uma flag inocente do usuário, em arquivo de configuração legítimo, é
suficiente para o portão travar. O código de saída do processo (0) era inequívoco e não foi
usado."*

**O que muda:** se o payload de `PostToolUse` do Bash trouxer o status de saída —
**verificar; não foi possível confirmar do lado de fora** —, o hook passa a keyar nele. Os
marcadores viram fallback.

**Ganho duplo:** some a fragilidade, e forjar deixa de ser "escrever uma string plausível"
para ser "fabricar um campo estruturado".

O T30 já implementou a versão pobre disto por conta própria: `&& echo All tests passed`,
*"que só executa se o runner sair com código 0"*. O agente inventou a ligação com o exit
code porque o hook não a tinha.

## I.5 — Proveniência no `lastTestOutcome`

**Superfície:** `recordTestOutcome`, hoje:

```js
this.state.lastTestOutcome = { outcome, phase, at };   // três campos, zero proveniência
```

Basta isto para abrir o portão:

```bash
echo '{"tool_input":{"command":"npm test"},"tool_response":"53 passed"}' | node test-outcome.js
```

Indistinguível, no estado, de uma execução verdadeira.

**O que muda:**

```js
{ outcome, phase, at,
  source: "harness" | "manual" | "unknown",
  toolUseId, sessionId,
  outputSha256, outputBytes,
  exitCode }
```

**Não impede nada — torna o contorno legível num post-mortem.** Foi o que faltou nos quatro
casos: a honestidade veio do agente, não do arquivo.

## I.6 — Casar `toolUseId` com o transcript

O payload de `PostToolUse` traz `transcript_path`. No `advance_phase`, o gate confere que o
`toolUseId` gravado **aparece no transcript** — ou seja, que existiu de fato uma chamada de
Bash correspondente na sessão.

**É a verificação mais forte implementável.** Forjar passa a exigir escrever no transcript,
o que é falsificação deliberada de registro, não atalho para destravar.

> **Honestidade sobre o limite:** não dá para tornar isto inforjável contra um agente com
> shell na mesma máquina. Qualquer segredo em `.versus/` é legível por ele. O alvo correto
> é que forjar **exija uma mentira explícita** e seja **auditável depois** — hoje não exige
> nem uma coisa nem outra.

## I.7 — O que NÃO afirmar sobre a causa

O agente do T31 fez o experimento controlado e separou o demonstrado do inferido:

| | status |
|---|---|
| classificar por texto é frágil | **demonstrado** |
| "não observado" = "observado e reprovado" | **demonstrado** |
| o hook não é invocado | **observado** (estado idêntico antes e depois de run verde, 5× ) |
| **por que** não é invocado | **não determinado** |

Verificado que a declaração em `.claude/settings.json` está bem-formada, que **ganhos irmãos
funcionam no mesmo ambiente** (`UserPromptSubmit` injeta contexto a cada turno;
`PreToolUse/Bash` bloqueou um `rm -f` real), e que o `test-outcome.js` grava certo quando
invocado à mão.

**Os itens I.1 a I.6 corrigem o dano independentemente da causa.** Não é preciso saber por
que o hook não dispara para que um hook que não dispara deixe de travar o projeto.

---

# PARTE II — AUDITABILIDADE DOS CRITÉRIOS DE SAÍDA

## II.0 O diagnóstico, com número

Os critérios de saída **não são rasos**: 390 registros nos doze projetos, **791 caracteres
de média, zero vazios**.

Mas apenas **2 dos 39 critérios têm evidência** (`verify:`):

| com evidência | `activated_lenses_recorded` (f2), `tests_passing` (f6) |
|---|---|
| **booleanos carimbáveis** | **os outros 37** |

E nos quatro projetos em que o gate foi contornado, o `tests_passing` registrou o resultado
**corretamente** e **não mencionou que o mecanismo falhara**:

> T21: *"Execução verde real, não assumida (S4): npm test → 63 testes, 63 pass, 0 fail…"*
> T30: *"53 de 53 testes verdes… execução real de `npm test`, não afirmação"*

Um auditor que lesse apenas os critérios concluiria que o gate funcionou nos doze. **O
contorno é conhecido só porque o agente escreveu um `record_decision` separado.**

> **Todo defeito de método do relatório veio do log narrativo, não dos critérios.** Os
> critérios registram conformidade com precisão; a narrativa registra o que deu errado no
> caminho.

## II.1 — O critério registra o caminho de verificação

**O que muda:** cada critério com evidência ganha campo para **como foi verificado**
(comando, artefato, hash) e **se o caminho foi o nominal**.

Nos quatro casos do `tests_passing`, isso teria capturado o contorno no próprio critério,
sem depender de o agente lembrar de escrever uma decisão à parte.

## II.2 — Degradação de mecanismo é registro obrigatório

Hook que não disparou, gate satisfeito por caminho alternativo, ferramenta substituída:
vira **campo do critério**, não decisão voluntária.

Hoje depende de boa-fé — e boa-fé foi o que tivemos, **quatro em quatro**. Não é base para
um método.

## II.3 — O que NÃO fazer

**Não acrescentar critérios.** Já são 39 por projeto, todos com detalhe. Mais critérios
aumentam a superfície de AP1 — autorreportar conformidade — sem aumentar auditabilidade.
**O ganho está em enriquecer o registro dos que existem.**

E vale a regra de viés também aqui: instrumentar por hipótese é o mesmo erro que gatear por
hipótese. II.1 e II.2 têm falha observada, quatro vezes.

---

# PARTE III — O MÉTODO NÃO REVERIFICA O QUE DECIDE

| o método estabelece | onde | quem verifica que sobrevive ao código |
|---|---|---|
| **premissa** da arquitetura (P-Ax) | Fase 1 | **ninguém** |
| **resolução** de achado crítico | Fase 3 | **ninguém** |

Quatro ocorrências, quatro mecanismos independentes, **todas descobertas por acaso
favorável**.

## III.1 — Fase 6 confere os críticos resolvidos na Fase 3

**Evidência:**

| projeto | a Fase 3 estabeleceu | a Fase 5 fez | como apareceu |
|---|---|---|---|
| T26 | erradicar o O(n²) de PRF-01/02 | **reintroduziu em três lugares** | VAL-4 tinha cronômetro |
| T27 | refinamento de CA-3 sobre delegação, **aprovado pelo operador** | não implementou | smoke test existia |

Registro do T26: *"é exatamente o O(n²) acidental que PRF-01 e PRF-02 mandaram erradicar,
reintroduzido na função de filtro"*.

**O que muda:** novo critério de saída da Fase 6, **com evidência**: para cada achado
**crítico** resolvido na Fase 3, o teste que o cobre ou a razão de não haver.

**Custo baixo** — a matriz já tem id por achado e a Fase 3 já registra a resolução. É
casamento de listas.

## III.2 — Fase 6 confere as premissas da Fase 1

**Evidência:**

| projeto | premissa | o que o código fez |
|---|---|---|
| T29 | **P-A8**: *"a migração é streaming ponto a ponto via Iterator"* | pico linear na entrada — 330 MB de RSS para 2 M de pontos |
| T31 | **A-06**: *"processo single-user / single-thread"* | Starlette roda endpoints síncronos em threadpool → erro de SQLite entre threads |

**Por que a lente PRE não pega:** criticar a **plausibilidade** de uma premissa na Fase 2 é
outra coisa que **medir se ela vale** no que foi construído.

**O critério, formulado pelo registro do T29 e generalizável:**

> *"uma premissa só está protegida quando existe um teste que a mediria falhando"*

**O que muda:** a Fase 6 declara, para cada premissa numerada da Fase 1, o teste que a
protege ou a razão de não haver. Irmão de III.1.

## III.3 — Fase 6 pede poder de detecção

**Cinco formas de teste verde que não testa**, em seis projetos:

| forma | onde |
|---|---|
| cenário errado | T21, T24 |
| cobertura parcial do achado | T22, T23 |
| **condição inalcançável** | T23 |
| invariante por construção | T25 |
| teste que falha sem defeito | T30 |

O caso decisivo é o T23: com `tamanho_janela == amostra_minima == 50` e `deque(maxlen=50)`,
`volumes_comparaveis` **nunca retornava falso**. A defesa contra REG-01 tinha correção,
tinha teste, o teste passava, e a condição era inalcançável. **62 testes verdes não
notaram; o teste de mutação notou** — e o sintoma era numérico: desligar a checagem
derrubava **2** testes contra **14** de outra mutação.

**Evidência de que a prática pertence ao método:** teste de mutação foi adotado por
iniciativa própria em **4 de 12** projetos (T22, T23, T27, T32), sem estar na guidance.

**O que muda:** o `tests_passing` passa a admitir, ou exigir, uma medida de poder. **Custo
médio** — precisa decidir se é exigência ou recomendação forte, e o que conta em stacks sem
ferramenta de mutação pronta.

## III.4 — Tabela de módulos completa por versão

**Evidência — T23.** A V(3) foi escrita como **delta**: 12 módulos em V(1), 12 em V(2),
**4** em V(3). Os outros onze projetos escreveram a tabela inteira.

**Delta e remoção são indistinguíveis pelo texto** — nos dois o nome sumiu da última tabela.
Tentar resolver por carry-forward ressuscita módulos legitimamente removidos.

**Não afeta nenhuma medida da RO3.** Item de higiene, custo trivial: o gate `architecture_doc`
exige que cada `## V(N)` traga a tabela completa.

---

# PARTE IV — GUIDANCE

Texto, não trava. **Custo baixo, mas conte com efeito pequeno**: o lote tem quatro casos de
instrução sem trava que não mudou comportamento, dois deles com descarte de projeto.

**A diferença aqui é que as quatro práticas abaixo já são adotadas espontaneamente** — a
instrução empurra na direção em que os agentes já vão sozinhos.

| prática | projetos | rendimento |
|---|---|---|
| **medição por estágio antes de otimizar** | T25, T26, T28, T29 | **4 de 12 — o palpite errou nos quatro.** T26: *"as duas correções anteriores eram reais mas não eram o gargalo"*; T28: o gargalo era `fsync`, 37 ms/commit, não parsing nem algoritmo |
| **micro-check por execução, não por leitura** | T23, T25, T26, T29 | 4 de 12. T25: *"só apareceu ao EXECUTAR o código, não ao lê-lo"*; T26: *"6 defeitos encontrados por RODAR, nenhum por ler"* |
| **teste de mutação** | T22, T23, T27, T32 | 4 de 12 — ver III.3 |
| **mapa de testes derivado das specs, não do código** | T26, T29, T30 | 3 de 12. Rendimento não previsto: **encontra erros nas specs** — no T29, 3 das 5 falhas iniciais eram erro de spec (`METADATA_SIZE` documentado como 20 quando `struct.calcsize` dá 16) |

**Mais um item de texto:** o registro de correção de teste deve dizer **qual cenário o teste
monta**, não só qual asserção mudou. Evidência: T21, onde o primeiro diagnóstico trocou o
número e o teste falhou de novo — *"um teste que monta o cenário errado passa a testar o
caminho feliz sem avisar"*.

---

# PARTE V — TAXONOMIA

**Não aplique isoladamente. Leia inteiro antes de mexer em qualquer gatilho.**

## V.1 A decisão de fundo, que vem antes de tudo

**Gatilho é condição necessária ou lista de exemplos típicos?** Hoje as 12 condicionais são
inconsistentes. **SUS é a única que diz explicitamente:**

> *"e.g. (but NOT only)… apply the central question, do not just match the examples"*

Ela diz isso porque foi reescrita na v0.12.9 depois de ficar em **0 ativações de 7
projetos**. As outras onze não dizem nada, e **o comportamento observado é que os leitores
as tratam como condição fechada**.

**Decida isto e redija as doze uniformemente sob a escolha.** Corrigir uma lente isolada
repete o erro de tratar o sintoma.

## V.2 A evidência que sustenta a decisão

Descompasso entre **pergunta central** e **gatilho** documentado em pelo menos cinco lentes,
com evidência **textual** — as justificativas dos estimadores citam o gatilho:

| lente | gatilho | leitura do estimador |
|---|---|---|
| ETI | *"Automated decisions **about people**"* | *"classifica certificados X.509, não pessoas"* |
| JOG | *"…**public API, marketplace** or platform design"* | *"sem mercado aberto, API pública ou incentivos econômicos"* |
| LIN | *"…interface contracts **between independent teams**"* | *"contratos internos no mesmo repositório"* |
| GOV | *"**Multiple teams**, data domains, or compliance"* | *"ator único; sem múltiplas equipes"* |

E o achado **resistiu a um estimador que acerta 91%**. As divergências que restam aos três
estimadores capazes concentram-se, e **35 são unidirecionais**:

| lente | divergências | Fase 2 ativou, não viram | Fase 2 recusou, viram |
|---|---|---|---|
| **SUS** | 11 | **11** | 0 |
| OBS | 10 | 6 | 4 |
| **CTR** | 9 | **8** | 1 |
| **RES** | 7 | **7** | 0 |
| **MEC** | 6 | 1 | **5** |
| **ETI** | 5 | **5** | 0 |

**SUS é a candidata mais forte** — 11 divergências, todas no mesmo sentido. **ETI** é a
segunda, e é o caso mais limpo de descompasso: no T25 o sistema decide sobre corte de
orçamento, os externos leem o gatilho (*"decisões sobre pessoas"*) e recusam, a Fase 2 lê a
pergunta (*"quem pode ser prejudicado?"*) e ativa — com razão.

**MEC é o espelho** e precisa de tratamento próprio: em 5 de 6 os externos ativam o que a
Fase 2 recusou.

## V.3 A ressalva que precisa estar no artigo

**A RO3 mediu a taxonomia corrigida, não a publicada.** Os gatilhos de SUS, UX e GOV foram
reescritos durante o experimento. O paper ainda traz o gatilho antigo de UX
(*"User-facing interface"*), tanto no `baseline-2026-08-03` quanto na versão atual.

Qualquer reescrita adicional **amplia esse descompasso** e precisa ser declarada junto.

---

# PARTE VI — O QUE FOI CONSIDERADO E REPROVADO

Registrado para não voltar por esquecimento.

## VI.1 `duplica` intra-lente **não pode virar gate**

O item C1 do `CORRECOES-EXTENSAO-R2.md` pediu uma frase na guidance dizendo que `duplica`
vale dentro da mesma lente. A frase entrou; **o comportamento não mudou** — no T21, três dos
seis agrupamentos que só o juiz cego viu eram intra-lente.

Seria natural pedir uma trava. **A regra da classificação reprova:** reconhecer que dois
achados descrevem o mesmo defeito é propriedade de **qualidade**, indecidível
mecanicamente.

**E o lote traz a prova empírica:** quatro avaliadores independentes marcaram 71, 87, 153 e
340 pares sobre os mesmos achados. Uma trava precisaria decidir mecanicamente o que quatro
leitores competentes decidem de forma muito diferente.

**Destino: limitação declarada**, com o número medido — κ de 0,110 a 0,338, todos dezenas de
vezes acima do acaso.

> Isto é achado, não fracasso: mostra o **limite do evidence-gating**. Há critérios do
> método que não admitem trava, e o correto é declará-los, não fingir que travas os cobrem.

## VI.2 Fixar o conjunto de lentes entre iterações — **reprovado**

Levantado em 2026-08-11. Ativação é função da arquitetura, e V(N+1) é outra arquitetura;
travar o conjunto mandaria a Fase 2 ignorar o que a Fase 3 acabou de mudar, e desfaria a
v0.12.6, que custou dois descartes.

**A garantia correta já está implementada: reavaliação obrigatória, resultado livre.**

Verificado que a redeclaração é trabalho real: nos doze projetos, as justificativas de
não-ativação entre iterações consecutivas têm **zero textos idênticos** nas 36 comparações,
com Jaccard de tokens de 0,41. O conjunto permanece igual em 9 de 12 porque a conclusão é a
mesma, não porque ninguém olhou — e em 3 mudou (MIG no T26, CTR no T31, OBS no T32).

---

# PARTE VII — SUGESTÃO DE ORDEM

**Primeiro, e como pacote:** I.1, I.2, I.3. São baratos, e juntos transformam a paralisia
muda numa condição diagnosticável. **I.2 é uma linha.**

**Segundo:** I.4 e I.5. Removem a fragilidade de classificação e tornam o contorno legível.

**Terceiro:** III.1 e III.2. Melhor relação evidência/custo do lote — quatro ocorrências, e
o vínculo já existe.

**Depois:** II.1, II.2, III.3, III.4, IV.

**Por último, e com cuidado:** V — a decisão sobre gatilhos altera a taxonomia publicada e
precisa entrar no artigo junto.

**I.6 é opcional** e só faz sentido se houver intenção de rodar o método em contexto onde a
boa-fé do agente não possa ser assumida.
