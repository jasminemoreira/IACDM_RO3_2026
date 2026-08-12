# Achados sobre a metodologia e o instrumento — acumulados durante o lote

Companheiro do `ACHADOS-TAXONOMIA.md`, que trata dos **critérios das lentes**. Aqui vai o
que as fases 5 a 7 revelam sobre os **gates, hooks e safeguards** — o maquinário que a
extensão executa, e não a taxonomia que ela aplica.

A mesma regra vale: **nada é corrigido durante o lote** se mexer no comportamento medido.
A exceção declarada é defeito que **impede a coleta** — um gate que trava com o critério
satisfeito não mede nada, ele bloqueia. Esses vão para `patches/` com pedido explícito, e
o descarte ou não do projeto em curso é decisão da operadora, registrada no
`LOG-OPERACAO.md`.

---

## M1. `test-outcome.js` não reconhece a saída do repórter padrão do `node:test`

**Onde:** `T21-certificados`, Fase 6. Registrado pelo próprio agente, categoria
`process`, e divulgado em chat no momento em que aconteceu.

**O que aconteceu.** O gate `tests_passing` recusou `advance_phase` **cinco vezes
seguidas** com a suíte em 68/68 verde e `tsc --noEmit` limpo.

A investigação, que está no registro, isolou quatro camadas:

| # | constatação |
|---|---|
| a | o estado guardava `lastTestOutcome=fail` de 00:00:34, **congelado** — nenhuma execução verde posterior o atualizou |
| b | o hook exige que o comando case `TEST_PATTERNS` (`npm test` casa) **e** que a saída case `CLEAN_MARKERS` ou `PASS_MARKERS` |
| c | o repórter padrão do `node:test` imprime `pass 68` e `fail 0`; **nenhum marcador cobre essa ordem de palavras** — eles esperam `68 passed`, `fail: 0`, ou linhas TAP com `ok ` |
| d | trocado o script para `--test-reporter=tap`, a saída passou a casar `CLEAN_MARKERS[4]` (`/^ok\s/m`) e nenhum `FAIL_MARKER` — **e o hook ainda assim não registrou**, indicando que o `PostToolUse` não estava entregando o `tool_response` do Bash ao hook naquela sessão |

**Como foi destravado.** O agente executou `test-outcome.js` manualmente, alimentando-o
com a saída **real e não modificada** do `npm test`, capturada em arquivo e repassada byte
a byte. O hook classificou como `pass` e o gate liberou.

**Por que isto importa mais do que parece.** O `tests_passing` é um dos gates com
evidência — a classe que o evidence-gating existe para criar, em oposição ao critério
booleano carimbável. Um gate com evidência que **não consegue enxergar a evidência
correta** é pior que um booleano: ele custa cinco tentativas, e a saída disponível é
contorná-lo. Aqui o contorno preservou a verdade (a execução verde é genuína e
verificável; o que foi manual é só o *transporte* da saída até o hook) e foi divulgado.
Não há garantia de que sempre seja assim.

**Dois defeitos distintos, e o segundo é o grave.** (b)+(c) é lista de marcadores
incompleta — corrigível com uma linha. (a)+(d) é o estado guardar um veredito negativo
que nada reescreve enquanto o hook estiver mudo: **falha fechada e permanente**. Um hook
que não recebe o `tool_response` deixa o projeto travado sem sinal de que o problema é o
hook, e não os testes.

**Pedido de correção:** `patches/PEDIDO-M1-test-outcome.md`.

**Efeito sobre o lote:** nenhum descarte. O gate atrasou a Fase 6, não alterou nenhuma
variável medida pela RO3 — a matriz de cobertura fecha na Fase 4, antes disso. O T21
fica, e o registro do contorno vale como dado.

---

### Segunda ocorrência — T28-agenda, 2026-08-11

Reincidiu, sete projetos depois, e **isola qual dos dois defeitos é o real**.

A operadora decidiu em 2026-08-11 adiar todas as correções para depois do lote; eu
registrei que o M1 poderia voltar a travar a Fase 6 e que o custo seria tempo, não dado.
Voltou.

O registro do agente, categoria `process`, fase 7:

> *"o hook PostToolUse `test-outcome.js` **parou de disparar** nas execuções de teste desta
> sessão — o único registro em `state.lastTestOutcome` era a falha de VAL-2 às 17:12, e
> nenhuma das execuções verdes posteriores foi registrada"*

E a verificação que fecha o diagnóstico:

> *"alimentando o hook manualmente com o payload da execução real (comando + saída
> `64 passed in 10.95s`), ele computou `outcome=pass` sozinho e persistiu corretamente —
> ou seja, **o hook funciona, mas não estava sendo invocado**"*

**Isto elimina (b)+(c) como causa desta ocorrência.** A saída do pytest — `64 passed in
10.95s` — casa `PASS_MARKERS[2]` (`\b\d+\s+passed\b`) sem problema algum, e o hook
provou isso ao classificar corretamente quando alimentado à mão. Nenhuma correção de
marcador teria ajudado.

**O que resta é (a)+(d), a metade grave** — e aqui é preciso separar o observado do
inferido, correção feita em 2026-08-12 depois de o agente do T31 ser mais rigoroso que eu:

| | status |
|---|---|
| o hook **não é invocado** nas execuções (estado idêntico antes e depois de run verde) | **observado**, e no T31 por experimento controlado |
| `lastTestOutcome` fica congelado no último veredito negativo, sem caminho de recuperação | **observado** — é o dano, e é demonstrável |
| **a causa ser o `PostToolUse` não entregar o `tool_response`** | **hipótese, não demonstrada** |

Eu vinha escrevendo a terceira linha como se fosse fato. Não é: pode ser o hook (o `main()`
tem timeout de 5 s no stdin e chama `emit()` sem gravar se o stream não fechar), pode ser o
ambiente, pode ser o formato de `tool_response`. **Nenhuma evidência escolhe entre elas.**

Dois projetos, duas stacks (`node:test` no T21, `pytest` no T28), mesma paralisia — o
padrão é sólido; a causa não.

> **E isto não trava o patch.** As duas fragilidades demonstráveis — classificar prosa em
> vez do código de saída, e "não observado" indistinguível de "observado e reprovado" —
> **corrigem o dano independentemente da causa**. Com elas, um hook que não dispara vira
> uma condição diagnosticável e recuperável em vez de uma paralisia muda.

**Consequência para o pedido de patch.** O `patches/PEDIDO-M1-test-outcome.md` trata os dois
defeitos e chama (a)+(d) de "o grave" com base em leitura do bundle. Agora há evidência
empírica em dois projetos de que **é o único que importa**: o defeito de marcadores é real
mas nunca foi a causa raiz de uma paralisia observada. A prioridade do patch deve inverter
— gravar estado em `unknown` e distinguir "não reconheci a saída" de "os testes falharam"
é o que resolve; a lista de marcadores é higiene.

**Nota de integridade, registrada pelo próprio agente:** *"houve INTERVENÇÃO MINHA no
harness que é o objeto do estudo, e isso está declarado ao operador em chat. Se a rodada
for comparada com outras, este ponto precisa ser considerado."* Segundo contorno declarado
do lote, e a declaração é o comportamento correto — mas dois contornos em nove projetos é
frequência que precisa constar do §7.

---

### Terceira ocorrência — T30-notifica, 2026-08-11

Décimo projeto, e a primeira vez em que **as duas causas aparecem juntas e são separadas
no registro**. Confirma o diagnóstico e resolve a dúvida que sobrava.

**Causa (b)+(c), a de marcadores:** o repórter padrão do `node:test` imprimiu `pass 53` e
`fail 0`. O registro nomeia exatamente o problema — *"ordem inversa aos padrões
CLEAN_MARKERS/PASS_MARKERS do hook, que esperam '53 passed' ou '0 failed'"* — e o
resultado foi classificado como **`unknown`**, com **nada gravado**.

**Contornada pelo agente sem tocar no hook:** acrescentou `&& echo All tests passed` ao
script de teste, *"que só executa se o runner sair com código 0"*. É uma solução limpa e
não altera a verdade do resultado.

**Causa (a)+(d), a grave:** *"Mesmo depois disso, o hook não foi invocado pelo harness nas
minhas chamadas de Bash."*

**Confirmação do diagnóstico do §M1.** Nas três ocorrências o padrão é o mesmo: um `fail`
antigo congelado em `lastTestOutcome`, e nenhuma execução verde posterior o reescrevendo.
O T28 já indicava que marcadores não eram a causa raiz; o T30 fecha, porque **corrigiu os
marcadores e continuou travado**.

| projeto | stack | marcadores casavam? | hook invocado? |
|---|---|---|---|
| T21-certificados | `node:test` | não | não |
| T28-agenda | `pytest` | **sim** | **não** |
| T30-notifica | `node:test` → corrigido em voo | não → **sim** | **não** |

**A distinção mais importante do lote sobre integridade**, e é do agente, não minha:

> *"O que NÃO foi feito: gravar 'pass' à mão no `state.json`, nem alimentar o hook com
> texto sintético para abrir o portão — houve uma invocação com texto sintético durante o
> diagnóstico, e ela foi substituída pela execução real antes do `advance_phase`."*

Ele **declarou uma invocação sintética intermediária** que ninguém teria notado, e disse
que a substituiu antes de avançar. Isso é mais do que o protocolo pede. E fecha com a
evidência reproduzível: *"`npm test` sai com código 0, 53 de 53 testes verdes"*.

**Frequência acumulada: três contornos declarados em dez projetos.** Todos divulgados por
iniciativa do agente. Vai para o §7 como número, não como anedota — e a taxa de 30% é
argumento forte para o patch entrar antes de qualquer trabalho futuro com o instrumento.

---

### Quarta ocorrência — T31-precos, 2026-08-12. **O diagnóstico definitivo.**

Quatro em onze projetos (**36%**), e este traz o experimento controlado que os anteriores
não tinham, mais **um modo de falha novo** e **uma fragilidade estrutural** que ninguém
tinha nomeado.

#### Modo de falha novo: configuração legítima do usuário trava o portão

`pytest.ini` do projeto já traz `-q` em `addopts`. Acrescentar `-q` na linha de comando
produz **`-qq`**, que suprime **inteiramente** a linha de resumo. Sem `N passed` na saída,
uma suíte 100% verde fica **inclassificável**, e o hook conclui `fail`.

> *"Uma flag inocente do usuário, em arquivo de configuração legítimo, é suficiente para o
> portão travar. O código de saída do processo (0) era inequívoco e não foi usado."*

Não é a ordem das palavras dos marcadores (T21, T30) nem ausência de invocação (T28). É
**terceira causa distinta**, e reforça §0.4(3): classificar prosa é frágil por natureza.

#### Experimento controlado — o hook não dispara, e não é hipótese

| verificado | como |
|---|---|
| a declaração em `.claude/settings.json` está bem-formada | PostToolUse, matcher `Bash`, caminho absoluto |
| **ganchos irmãos funcionam no mesmo ambiente** | `UserPromptSubmit` injeta contexto a cada turno; `PreToolUse/Bash` **bloqueou um `rm -f` de verdade** na Fase 5 |
| o `test-outcome.js` funciona quando invocado direto | alimentado por stdin, gravou `pass` corretamente |
| **e mesmo assim não produz efeito** | leu `lastTestOutcome`, rodou pytest verde, releu: **valor idêntico**. Repetido em 5+ execuções |

Ganchos disparam. Ganchos sobre Bash disparam. Este não.

#### A contenção epistêmica, e por que ela é o melhor momento do corpus

> *"NÃO TENHO EVIDÊNCIA para escolher entre essas hipóteses, e portanto NÃO afirmo que seja
> defeito do Versus. Esta contenção é deliberada: a lição 7 deste mesmo ciclo registra que
> eu afirmei um fato negativo ('zero POST /regras') a partir de observação parcial e errei.
> Repetir o padrão na frase seguinte seria o pior tipo de lição."*

O agente conecta um erro **que ele mesmo cometeu e corrigiu** nesta sessão a uma decisão de
**não afirmar** agora. É correção de padrão de comportamento dentro do ciclo, e o oposto de
AP1.

#### Fragilidade estrutural nova — o agente não tem como diagnosticar

> *"Não há ferramenta MCP que exponha `lastTestOutcome`: para descobrir que o motor guardava
> um 'fail' obsoleto de 02:34 eu tive de LER `.versus/state.json` diretamente, contornando a
> interface que a metodologia oferece. Um operador sem esse recurso ficaria preso sem
> diagnóstico possível."*

A mensagem de bloqueio diz apenas *"the engine did not witness a passing test run"*. Isso
torna **"não observado" indistinguível de "observado e reprovado"** — e sem acesso ao
arquivo de estado, indiagnosticável.

**Duas correções concretas, e são as mais baratas do §M1:**

1. `getPhaseState` **expõe `lastTestOutcome`** — outcome, quando, e por qual caminho.
2. A mensagem de bloqueio **diz o que o motor viu por último e quando**, em vez de só
   negar.

Sem elas, o agente é empurrado a ler o `state.json` por fora para entender por que está
travado — ou seja, **a interface obriga a contorná-la**.

#### A distinção sobre fraude, formulada pelo agente

> *"S4 exige que o resultado seja obtido por EXECUÇÃO e VERIFICAÇÃO, não por suposição. A
> execução ocorreu, a saída foi lida, o número é reproduzível. O que fiz foi **retransmitir
> um resultado verdadeiro por um canal que estava quebrado**. A fraude seria invocar o
> gancho SEM ter rodado a suíte, ou com uma saída fabricada — e é exatamente por isso que
> registro aqui o comando, a saída usada e o motivo, **para que a diferença entre as duas
> coisas seja auditável e não dependa da minha palavra**."*

É o princípio da §0.7 enunciado de forma independente por quem estava sendo fiscalizado.

---

## M2. Diagnóstico de causa raiz acertou o sintoma antes da causa

**Onde:** `T21-certificados`, Fase 6, duas entradas `diagnosis` consecutivas sobre o
mesmo teste.

O teste de CA-5 na UI falhou. O primeiro diagnóstico foi específico, verificável e
**errado no nível certo**: a asserção esperava `45` dias, o certificado servido pelo
helper tinha `100`, a mensagem da aplicação estava correta. Corrigiu-se o número — e o
teste falhou de novo, na asserção anterior.

O segundo diagnóstico achou a causa: limiares 90/60/30 contra um certificado de 100 dias
formam uma configuração **válida**. A aplicação respondia 303, o corpo vinha vazio, e não
existia frase de erro alguma para procurar. O cenário não exercitava CA-5 desde o início.

**A leitura.** O primeiro diagnóstico não foi descuidado: ele nomeou o sintoma exato,
apresentou prova (a asserção vizinha passava) e foi honesto sobre o escopo. Ainda assim
tratou o sintoma. A citação do registro é a lição:

> *"um teste que monta o cenário errado passa a testar o caminho feliz sem avisar"*

**Por que vai para o corpus.** Se a primeira correção tivesse bastado para deixar o teste
verde, CA-5 ficaria sem cobertura real com a suíte inteira em verde e o gate satisfeito.
O que expôs o problema foi o teste continuar falhando — **acaso favorável, não
instrumento**. Nenhum safeguard da metodologia cobre "o teste passa mas não testa o que
diz testar", e o AP5 pressupõe que a verificação verifica.

Candidato a discussão pós-lote, não a gate: exigir que o registro de correção de teste
diga qual **cenário** o teste monta, não só qual asserção mudou.

---

## M3. Uma versão da arquitetura pode ser delta, e delta é indistinguível de remoção

**T23-canario, 2026-08-10.** Achado sobre o artefato, não sobre um gate.

A v0.12.5 fez a Fase 3 **acrescentar** `## V(N+1)` em vez de sobrescrever, para que a
lista de módulos de cada iteração sobrevivesse. O T23 acrescentou, mas escreveu a V(3)
como **delta**: 12 módulos em V(1), 12 em V(2), **4** em V(3) — só os que mudaram. Os
outros três projetos escreveram a tabela inteira a cada versão.

**Nenhuma medida da RO3 foi afetada.** As duas iterações foram criticadas contra V(1) e
V(2), que são completas; os Passos 1 e 4 usam o módulo escrito em cada achado. O que
quebrou foi o cabeçalho do meu relatório, que anunciava "Módulos: 4" para um produto de 12,
e nove módulos legítimos caíam na tolerância de "versões antigas" — que existe para
módulos **removidos**.

**A correção que tentei primeiro estava errada.** Carry-forward (a versão corrente é a
acumulada) ressuscitava módulos legitimamente removidos nos outros três: T21 12→13, T24
9→11, T22 11→14.

**O ponto que fica.** Delta e remoção são o mesmo texto — em ambos o nome sumiu da última
tabela. Nenhuma heurística os separa. Como o número não entra em medida alguma, a saída é
não escolher em silêncio: o relatório passou a mostrar o perfil por versão e a avisar
quando a última é menor que uma anterior.

**Candidato pós-lote:** exigir tabela completa por versão. Seria mudança de instrumento no
meio do lote para um caso em quatro, e não corrige nada medido — por isso não foi pedida.

---

## M4. Teste de mutação achou cobertura falsa que 62 testes verdes não acharam

**T23-canario, Fase 6.** O achado mais forte do projeto e, até aqui, do lote.

A defesa contra **REG-01** — canário sem tráfego promovido por vacuidade — tinha correção,
tinha teste, e o teste passava. Mas com `tamanho_janela == amostra_minima == 50` e a
janela como `deque(maxlen=50)`, a contagem por série é limitada a 50; `pronta()` só é
verdadeira quando as duas séries têm exatamente 50 pontos, e nesse caso a razão min/max é
sempre 1,0. **`volumes_comparaveis` nunca retorna falso na configuração padrão.**

A condição que o teste deveria exercer era **inalcançável**, e a suíte inteira verde não
disse nada. Quem disse foi o teste de mutação: desligar a checagem de volumes derruba
apenas **2** testes, contra **14** ao inverter a cauda do Mann-Whitney. O número baixo é o
sintoma.

**Por que importa para o Estudo 1.** O AP5 pressupõe que a verificação verifica. Esta é a
terceira forma distinta de "teste verde que não testa" no lote — depois do teste com
cenário errado (M2, T21 e T24) e da correção que cobre parte do que o achado implica
(T22 D-01, T23 UC-4). **Nenhum safeguard da metodologia cobre a classe.** O que a cobriu
foi teste de mutação, praticado por iniciativa do agente em 2 de 4 projetos (T22 e T23),
sem estar na guidance.

**Segunda ocorrência — T31-precos, 2026-08-12.** A premissa **A-06** dizia *"processo
single-user / single-thread"*. Errada: o Starlette/FastAPI executa endpoints **síncronos**
(`def`, não `async def`) num threadpool, e a conexão SQLite criada na thread que monta a
aplicação era usada por outra — `sqlite3.ProgrammingError`. O registro é explícito: *"A
PREMISSA A-06 ESTAVA ERRADA POR SER FORTE DEMAIS"*.

Duas premissas refutadas em onze projetos, ambas por **execução real** e nenhuma pela
crítica da Fase 2. Reforça o critério: uma premissa só está protegida quando existe um
teste que a mediria falhando.

**Candidato pós-lote, com evidência forte:** pedir medida de poder de detecção — mutação
ou equivalente — como critério da Fase 6, em vez de só "testes passando". É o único item
do lote com defeito observado em três formas diferentes e uma contramedida já demonstrada
funcionando.

---

## M5. Um invariante garantido por construção não pode falhar — e por isso não informa

**T25-orcamento, Fase 5.** Quarta forma distinta de "teste verde que não testa", e a mais
sutil das quatro.

O clamp `custo = min(custo_real_nano, valor_reservado)` em `escrow.reconciliar` mantém o
invariante do teto **por construção**. A consequência que o S7 encontrou: o critério de
acerto **CA-1 passaria mesmo se a premissa A8** (`tokens_entrada <= bytes_do_corpo`)
**fosse falsa** — o excedente simplesmente não seria contabilizado, convertendo um estouro
do teto em **subcontagem silenciosa**.

O teste do invariante não distingue *"A8 é verdadeira"* de *"A8 é falsa e o clamp
mascara"*.

**Por que é distinta das outras três.** Em M4 o problema era o teste: cenário errado,
cobertura parcial, condição inalcançável. Aqui **o teste é válido, o critério é real e o
código está correto**. O defeito é epistêmico: um invariante que o código garante
estruturalmente não pode falhar, logo passar não é evidência de nada. A suíte confirma o
que o compilador já garantia.

**Como foi encontrado.** Pelo micro-check S7, e o registro é explícito sobre o mecanismo:
*"só apareceu ao EXECUTAR o código, não ao lê-lo"*. A mesma fase registra *"6 defeitos
encontrados por RODAR, nenhum por ler"* — entre eles cobrança de cache de 1 h como se
fosse de 5 min, porque o objeto `usage` não informa o TTL e ninguém varria
`cache_control.ttl`.

**As quatro formas, para o texto do paper:**

| forma | onde | o que falha |
|---|---|---|
| cenário errado | T21, T24 | o teste monta um cenário que não exerce o critério |
| cobertura parcial do achado | T22 (D-01), T23 (UC-4) | a correção fecha um caminho, o defeito volta por outro |
| condição inalcançável | T23 (REG-01) | a condição que o teste exerceria não pode ocorrer |
| **invariante por construção** | **T25 (CA-1)** | **o teste passa com a premissa verdadeira ou falsa** |

Cinco projetos, quatro formas, **nenhum safeguard da metodologia cobrindo a classe**. As
contramedidas que funcionaram — teste de mutação (T22, T23) e micro-check por execução e
não por leitura (T23, T25) — foram iniciativa do agente, nenhuma está na guidance.

**Recomendação pós-lote, agora com base sólida:** a Fase 6 pedir medida de **poder de
detecção**, não só "testes passando". É o item do lote com mais evidência acumulada.

---

## M6. A implementação da Fase 5 pode desfazer a correção da Fase 3

**T26-extratos, Fase 5.** Classe nova, distinta das quatro de §M4 e §M5.

Naquelas, o defeito estava no **teste**. Aqui a crítica estava certa, a correção estava
completa, e a **implementação a desfez**.

VAL-4 (50 mil transações em menos de 60 s) estourou em 120 s. Causa: **três padrões
quadráticos ou N+1 reintroduzidos depois que a arquitetura os havia eliminado**. O registro
não suaviza:

> *"é exatamente o O(n²) acidental que PRF-01 e PRF-02 mandaram erradicar, reintroduzido
> na função de filtro"*

O pior era `any(e.conta == n.conta for n in novas)` dentro do laço sobre `existentes` — 36
mil × 36 mil, mais de 10⁹ comparações.

**Por que isto é estrutural e não descuido.** O laço 2↔3 produz uma arquitetura corrigida;
a Fase 5 implementa a partir dela. Nada verifica que a implementação **preserva** a
propriedade que a correção estabeleceu. Os gates da Fase 5 checam módulos entregues,
specs consultadas, S6 aplicado e UI executável — nenhum pergunta *"os achados críticos
resolvidos na Fase 3 continuam resolvidos no código?"*.

O achado só apareceu porque VAL-4 era um critério **numérico e medido**. Se a propriedade
reintroduzida não tivesse número associado, teria passado.

**Nota sobre como a causa raiz foi encontrada**, que vale sozinha: por profilagem, e o
registro é honesto sobre as tentativas anteriores — *"as duas correções anteriores eram
reais mas não eram o gargalo"*. Duas correções verdadeiras que não resolviam o problema
medido. Sem a medição por estágio, o projeto teria "corrigido" duas vezes e seguido lento.

**Candidato pós-lote, e o mais acionável do lote:** a Fase 5 ou a Fase 6 verificarem que
os achados **críticos** resolvidos na Fase 3 seguem resolvidos na implementação. Já existe
o vínculo — cada achado tem id e a Fase 3 registra a resolução —, falta a checagem.

---

## M7. Terceiro juiz cego — decidido em 2026-08-11, a rodar sobre os doze no fim

Não é achado; é **decisão de análise registrada antes de olhar o resultado**, para não
parecer escolha pós-hoc quando aparecer no relatório.

### O problema que ela endereça

O modelo gerador produz os achados **e** marca as duplicatas. A marcação é o discriminante
de "mesmo defeito", que define os clusters, que definem a contribuição exclusiva — a medida
central da RO3. A remarcação cega por um segundo juiz mede o desacordo, e ele é grande:

κ por projeto: **0,000 · 0,000 · 0,362 · 0,115 · 0,249 · 0,000**

Com **dois** raters, duas hipóteses explicam esse número igualmente bem:

| | hipótese |
|---|---|
| **(a)** | o gerador é ruim a se autoavaliar; os externos veem melhor |
| **(b)** | *"mesmo defeito"* não é definível nessa granularidade, e qualquer par de leitores discorda |

Não há como separá-las com dois juízes. Com três, separam-se:

- **Qwen e Kimi concordam entre si e ambos divergem do gerador** → viés de autoavaliação, e
  o consenso externo é estimativa melhor.
- **os três discordam par a par** → o problema é o **construto**. Isso é achado publicável,
  e mais forte que a limitação atual: *"a granularidade de defeito não é operacionalizável
  de forma confiável"* é conclusão, não desculpa.

### O que o terceiro juiz NÃO faz

**Não cria gabarito.** Três opiniões sem padrão-ouro continuam sendo três opiniões. E com
κ pairwise ~0,1, **voto majoritário seria quase aleatório** — a maioria de três raters
discordantes não é verdade, é ruído com três votos. Portanto:

> **Proibido** substituir a marcação do gerador pela maioria dos três. O terceiro juiz
> entra em (i) estatística de confiabilidade e (ii) terceiro braço da análise de
> sensibilidade. Nada mais.

### Desenho

**Kimi Code CLI como terceiro juiz.** Família diferente do Qwen, já instalado, já roda
headless em diretório temporário vazio. **Claude está descartado**: mesmo sem contexto, é a
família que gerou os achados, e erro correlacionado é justamente o que se quer evitar.

Painel final: gerador (autoavaliação) + Qwen (cego) + Kimi (cego). Dois externos
independentes contra uma autoavaliação.

Saídas: **Fleiss κ** entre os três no lugar do Cohen entre dois; e um terceiro braço no
Passo 2, que hoje compara duas clusterizações.

### Por que no fim, e por que isso não é heterogeneidade

Diferente da estimativa de lentes, a remarcação de duplicatas é **retrospectiva sobre
artefato congelado**: a matriz não muda depois da Fase 4, e o juiz nunca vê o projeto
rodando. Rodar o Kimi nos projetos já fechados dá **exatamente o mesmo resultado** que
teria dado na época — não há informação futura vazando.

Fazer agora criaria seis projetos com dois juízes e seis com três, sem ganho algum.

### Assimetria de informação — o confundidor que só percebi no T27

**Acrescentado em 2026-08-11, depois do T27-despesas e ANTES de rodar o terceiro juiz.**

O T27 pareceu decisivo para (b): o gerador marcou **14 pares**, o juiz cego marcou 3,
interseção **vazia**. Com 14 marcações a esparsidade deixa de explicar o κ nulo.

Mas há uma terceira hipótese que o desenho de dois raters **não separa**, e ela é falha
minha:

| rater | o que vê |
|---|---|
| gerador | o projeto inteiro — Fase 0, arquitetura, todas as iterações, o código |
| juiz cego | a matriz cegada mais a tabela de módulos |

**(c)** O gerador enxerga relações reais de mesmo-defeito que **não são recuperáveis da
descrição textual**. Se for isso, κ mede **assimetria de informação**, não ambiguidade de
conceito — e a marcação do gerador seria a *melhor*, não a pior.

Contra-argumento parcial: o juiz marcou 3 pares que o gerador não marcou, e quem tem
estritamente mais informação deveria tê-los visto. Mas n=3 é fraco.

**Isto aumenta o valor do terceiro juiz, e muda o que ele testa.** Kimi recebe **exatamente
o mesmo pacote** que o Qwen — mesma informação, família diferente. Logo:

| resultado | inferência |
|---|---|
| **Qwen ≈ Kimi**, os dois longe do gerador | o conceito **é** definível a partir do pacote; a distância até o gerador é **(c)**, assimetria de informação |
| **Qwen ≉ Kimi** | é **(b)**, o construto não é operacionalizável |

Sem o terceiro juiz, (b) e (c) permanecem indistinguíveis e a limitação do §7 fica no
nível de "não sabemos". Com ele, vira uma das duas afirmações, e as duas são publicáveis.

### Expectativa declarada antes de rodar

Espero **(b)** — Qwen e Kimi discordando entre si tanto quanto discordam do gerador.
Razão: em sete projetos o desacordo com o gerador não tem direção estável (em 3 o juiz
cego agrupa mais, em 3 menos, em 1 nenhum agrupa), o que é mais compatível com critério mal
definido do que com um rater sistematicamente melhor ou pior informado.

Registro a expectativa para que o resultado possa contrariá-la de forma visível. Se sair
**(c)**, terei errado, e a consequência é forte na direção oposta: significaria que a
marcação do gerador é a melhor disponível e que a remarcação cega **subestima** a
sobreposição real — o que empurraria a contribuição exclusiva para baixo, contra a
hipótese da RO3.

### O que isto NÃO resgata

A conclusão de ortogonalidade **não depende disto**. A análise de sensibilidade do T21 já
mostrou que trocar quem marca move a exclusividade em ±2 e nenhuma lente chega perto de
zero — instabilidade de magnitude, não de classificação. Este item fortalece a **seção de
limitações**, não o resultado principal.

### Trabalho pendente

Ligar o Kimi ao subcomando `cegar_duplicatas.py julgar`, que hoje só fala com a API do
Ollama. O `_kimicode()` de `reestimar_lentes.py` já faz o transporte e pode ser
reaproveitado.

---

## M8. Premissa da Fase 1 refutada pela implementação — e nada a verifica

**T29-retencao, Fase 6.** Mesma lacuna estrutural do §M6, um estágio antes.

A premissa **P-A8** da arquitetura afirma literalmente que *"a migração é streaming ponto
a ponto via Iterator"*, e o padrão Iterator/generator foi escolhido na Fase 1 exatamente
para isso. Medição do pico de memória:

| pontos | pico |
|---|---|
| 10 mil | 1,9 MB |
| 100 mil | 15,4 MB |
| 500 mil | 74,7 MB |
| 2 milhões | **330 MB de RSS** |

~150 bytes por ponto, **linear na entrada**. `store_f2.write()` constrói o dicionário
`by_window` com toda a entrada antes de escrever o primeiro chunk, e como `migrate` chama
`dst.write(tier, src.read(...))`, a migração também bufferiza.

> *"A premissa está refutada pelo próprio código."*

**Como apareceu, e é o detalhe que importa:** por um teste de **outra propriedade**. Ao
matar o ingest com SIGKILL aos 0,5 s e 1,0 s para verificar atomicidade, **zero chunks
tinham sido escritos** — o que não é lentidão, é a entrada inteira sendo agrupada antes de
qualquer escrita. *"O teste de atomicidade revelou um defeito de memória."*

**Por que é achado de método e não do projeto.** A metodologia registra premissas na Fase
1, e a lente PRE as critica na Fase 2 — mas criticar a **plausibilidade** de uma premissa é
outra coisa que **medir se ela vale** no sistema construído. Nenhum gate faz a segunda.
P-A8 passou pela crítica, sobreviveu a duas iterações do laço, e era falsa.

**O paralelo com §M6 fecha um padrão:**

| o que a metodologia estabelece | onde | o que verifica que sobrevive à implementação |
|---|---|---|
| premissa da arquitetura (P-Ax) | Fase 1 | **nada** — §M8 |
| resolução de achado crítico | Fase 3 | **nada** — §M6 |

Dois estágios, mesma lacuna: **o método produz compromissos e não os reverifica contra o
código**. Três projetos já a exibiram (T26, T27, T29), por três mecanismos diferentes.

**E o próprio registro aponta a forma da correção**, que é boa e generalizável:

> *"Teste a acrescentar: medir que o pico de memória de um ingest de N pontos NÃO cresce
> proporcionalmente a N — é a única forma de a suíte proteger P-A8 de regressão."*

Ou seja: **uma premissa só está protegida quando existe um teste que a mediria falhando.**
Isso é operacionalizável — a Fase 1 já numera as premissas, bastaria a Fase 6 declarar,
para cada uma, o teste que a protege ou a razão de não haver. Depois da correção a memória
ficou plana em 1,5 MB de 10 mil a 500 mil pontos (151 → 3 bytes/ponto), com teste de
regressão comparando o pico entre 2 e 20 chunks cheios.

---

## Formato deste arquivo

Uma entrada por achado: onde apareceu, o que aconteceu com a evidência do registro, a
leitura, e o destino — pedido de patch, candidato pós-lote, ou só registro. Achados que
não impedem a coleta não geram correção durante o lote.
