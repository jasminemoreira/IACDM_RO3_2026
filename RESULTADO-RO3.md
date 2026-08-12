# RO3 — resultado do experimento

**Fechado em 2026-08-12.** Doze projetos válidos, instrumento único (`versus-claude
0.14.2`), 1.100 achados, 1.029 defeitos distintos.

Todos os números deste documento foram recomputados da fonte no fechamento. Onde uma
leitura anterior foi contrariada por dado posterior, o histórico está preservado — a
correção é parte do resultado, não constrangimento a esconder.

---

# 0. O corpus

| | |
|---|---|
| projetos válidos | **12** |
| descartados | **7**, todos com motivo registrado no `LOG-OPERACAO.md` |
| instrumento | `versus-claude 0.14.2`, **única versão instalada**, nos doze |
| achados | **1.100** — 195 críticos, 657 importantes, 248 sugestões |
| defeitos distintos | **1.029** (clusters por `duplica` do modelo gerador) |
| módulos | 130 |
| execução | **37 h** · 1,1 a 5,3 h por projeto, mediana 3,3 h |
| iterações do laço 2↔3 | 28 no total — nove projetos com 2, dois com 3, um com 4 |
| agente gerador | Claude, em todos os doze |

**Cobertura das 12 condicionais** (projetos em que ativou):

| RES | UX | SUS | PRO | GOV | CTR | LIN | MEC | OBS | JOG | ETI | MIG |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | 12 | 12 | 12 | 12 | 12 | 12 | 10 | 9 | 7 | 5 | 4 |

As sete universais rodaram nos doze por definição. **Nenhuma lente ficou abaixo do piso de
3 projetos** que o §2 declara como mínimo para distinguir "não detecta" de "não foi
exercitada".

---

# 1. RESULTADO PRINCIPAL — a ortogonalidade se sustenta

## 1.1 O enunciado

**Nenhuma das 19 lentes tem contribuição exclusiva zero.** Toda lente que ativou produziu
ao menos um defeito que nenhuma outra lente encontrou, em todo projeto em que ativou.

## 1.2 Por que o veredito binário do §4 é insuficiente sozinho

O §4 declara uma lente removível quando **100%** dos seus defeitos são compartilhados. Essa
barra é praticamente inalcançável, e dizer "ninguém a atingiu" seria fraco.

O resultado real é a **distribuição**:

| | valor |
|---|---|
| sobreposição média | **11%** |
| menor | ARQ, **2%** |
| maior | SUS, **33%** |
| lentes acima de 15% | quatro — SUS 33%, DES 20%, JOG 20%, ETI 17% |

E a esparsidade da co-ocorrência: de **171 pares possíveis de lentes, 41 (24%) compartilham
ao menos um defeito**. O maior é `DES × SUS`, com 9 defeitos em comum e Jaccard **0,10**.

## 1.3 A predição do protocolo que não se confirmou

O §4 nomeia **`ARQ × PRE`** como par suspeito *a priori* — a intuição de que "premissas" e
"arquitetura" perguntariam a mesma coisa.

**Medido: Jaccard de defeitos 0,00.** A suspeita da própria teoria não se confirmou. Isto é
evidência mais forte que confirmar uma expectativa, porque era uma predição que podia
falhar e falhou contra a intuição de quem escreveu o método.

## 1.4 Robustez — o teste mais duro que o desenho permite

A medida depende de quem marca duplicata. Para testar, a marcação foi refeita **às cegas**
por três avaliadores independentes sobre um pacote que remove lente, renomeia ids, embaralha
a ordem e apaga as marcações originais.

Contribuição exclusiva sob quatro clusterizações:

| lente | gerador | qwen full | gpt-5.4 | **união dos 4** |
|---|---|---|---|---|
| PRE | 98 | 85 | 62 | **53** |
| ARQ | 88 | 75 | 57 | **47** |
| LIN | 76 | 57 | 42 | **27** |
| SEG | 74 | 65 | 46 | **38** |
| UX | 73 | 68 | 44 | **39** |
| IMP | 70 | 53 | 32 | **22** |
| PRO | 60 | 60 | 38 | **31** |
| RES | 56 | 52 | 28 | **16** |
| CIE | 55 | 48 | 45 | **37** |
| GOV | 52 | 48 | 34 | **25** |
| DES | 47 | 44 | 29 | **24** |
| CTR | 42 | 37 | 27 | **18** |
| MEC | 42 | 36 | 30 | **22** |
| OBS | 36 | 34 | 23 | **23** |
| REG | 34 | 36 | 27 | **18** |
| SUS | 26 | 28 | 16 | **13** |
| JOG | 20 | 25 | 24 | **17** |
| ETI | 15 | 18 | 13 | **11** |
| **MIG** | 14 | 9 | 7 | **3** |
| **clusters** | **1029** | 960 | 788 | **668** |

A união colapsa **1.029 defeitos em 668** — 35% a menos. É a leitura mais agressiva
possível: todo par que **qualquer** avaliador agrupou conta como um só defeito.

**Nenhuma lente chega a zero sob nenhuma das quatro.** A mais baixa é MIG com 3, e ela
ativou em apenas 4 dos 12 projetos.

Nota para leitura: o efeito **não é monotônico** — SUS, REG, JOG e ETI *sobem* sob a
marcação do Qwen full, porque quando outros clusters se fundem uma lente pode passar a ser
a única presente onde antes dividia.

## 1.5 O que este resultado NÃO diz

Não diz que as 19 lentes são a taxonomia certa, nem que são suficientes, nem que a divisão
é ótima. Diz que **nenhuma é redundante** no corpus medido, sob o critério pré-registrado.

---

# 2. RESULTADO SECUNDÁRIO — o critério de ativação é a parte frágil

Não estava no desenho. Emergiu da medida de reprodutibilidade da ativação.

## 2.1 O mecanismo

Em várias lentes, a **pergunta central** e o **gatilho** descrevem coisas de tipos
diferentes, e leitores diferentes respondem a perguntas diferentes.

Exemplos textuais, com a justificativa do estimador citando o gatilho:

| lente | gatilho | leitura do estimador |
|---|---|---|
| **ETI** | *"Automated decisions **about people** (scoring, classification, moderation)"* | *"classifica certificados X.509, não pessoas"* → não ativa |
| **JOG** | *"…**public API, external integrations, marketplace** or platform design"* | *"sem mercado aberto, API pública ou incentivos econômicos entre entidades independentes"* |
| **LIN** | *"…interface contracts **between independent teams**"* | *"contratos internos em TypeScript no mesmo repositório"* |
| **GOV** | *"**Multiple teams**, data domains, or compliance"* | *"ator único; sem múltiplas equipes"* |

A Fase 2 aplica a **pergunta central**; os leitores externos aplicam o **gatilho**.

## 2.2 Quatro estimadores independentes, doze projetos

Estimativa cega sobre a arquitetura **V(1)** — a versão que o declarante da Fase 2 tinha à
vista —, três rodadas por projeto, mesmo pacote para todos.

| estimador | ativas/rodada | oscilações | concordância com a Fase 2 |
|---|---|---|---|
| qwen3.6:27b local (Q4_K_M) | 7,5 | 29 | 81% |
| qwen3.6-27b full | 6,5 | 26 | **74%** |
| kimicode (Kimi K2) | 8,6 | 17 | 89% |
| **gpt-5.4** | 9,7 | **7** | **91%** |

Concordância entre estimadores: `kimi × gpt` **94%**, `Q4 × kimi` 93%, `Q4 × full` 92%,
`full × kimi` 88%, `Q4 × gpt` 87%, `full × gpt` 78%.

## 2.3 A explicação por quantização foi testada e refutada

Hipótese natural: o estimador local é quantizado, logo pior.

**Falso.** O `qwen3.6-27b` em precisão full ficou **abaixo** do local (74% contra 81%), com
instabilidade equivalente (26 contra 29 oscilações), ativando **menos** lentes (6,5 contra
7,5). Os dois concordam entre si em **92%** — é o mesmo leitor.

A diferença entre estimadores é de **família de modelo**, não de precisão numérica. Isto
remove uma explicação fácil que teria enfraquecido o resultado.

## 2.4 O achado sobreviveu a um leitor que acerta 91%

As divergências dos três estimadores capazes **não se espalham** — concentram-se em poucas
lentes, e com direção:

| lente | divergências | Fase 2 ativou e não viram | Fase 2 recusou e viram |
|---|---|---|---|
| **SUS** | 11 | **11** | 0 |
| OBS | 10 | 6 | 4 |
| **CTR** | 9 | **8** | 1 |
| **RES** | 7 | **7** | 0 |
| **MEC** | 6 | 1 | **5** |
| **ETI** | 5 | **5** | 0 |
| LIN | 4 | 4 | 0 |
| JOG | 3 | 2 | 1 |
| PRO | 2 | 2 | 0 |

**SUS, RES, CTR, ETI e LIN erram numa direção só** — 35 divergências unidirecionais. Não é
ruído; é leitura sistematicamente diferente do critério.

**MEC é o espelho**: em 5 de 6 os externos ativam o que a Fase 2 recusou.

## 2.5 Um segundo mecanismo — emergência tardia

Em **3 dos 12** projetos o conjunto de lentes **mudou entre iterações do laço 2↔3**, sempre
com a lente entrando contra uma versão posterior da arquitetura: MIG no T26 (contra V(3)),
CTR no T31 (contra V(3)), OBS no T32 (contra V(2)).

Isto **não é propriedade de uma lente específica**. A hipótese inicial de que MEC seria
estruturalmente tardia foi **refutada**: MEC entrou na iteração 1 no T21 e ficou fora das
três iterações do T27. É propriedade de **quanto a arquitetura de cada projeto muda ao ser
criticada**.

**Consequência para o §2:** a cobertura de uma lente depende de quantas voltas o laço deu,
o que é independente do domínio do projeto — confundidor para uma contagem que assume
cobertura determinada pelo tipo de projeto.

**Verificação de que a redeclaração é trabalho real, não formalidade:** as justificativas de
não-ativação foram comparadas entre iterações nos 12 projetos. **Zero textos idênticos**,
similaridade média de 0,09 a 0,65 — cada iteração reargumenta contra a versão nova.

---

# 3. RESULTADO SOBRE O MÉTODO — compromissos não são reverificados

Emergiu das fases 5 a 7 e consolidou-se como contribuição separada.

| o método estabelece | onde | quem verifica que sobrevive ao código |
|---|---|---|
| **premissa** da arquitetura (P-Ax) | Fase 1 | **ninguém** |
| **resolução** de achado crítico | Fase 3 | **ninguém** |

Quatro ocorrências, quatro mecanismos independentes:

| projeto | o que foi estabelecido | o que a implementação fez | como apareceu |
|---|---|---|---|
| T26 | erradicar o O(n²) que PRF-01/02 apontaram | **reintroduziu em três lugares** | VAL-4 tinha cronômetro |
| T27 | refinamento de CA-3 sobre delegação, aprovado na Fase 3 | não implementou | smoke test existia |
| T29 | premissa P-A8: *"migração é streaming via Iterator"* | 330 MB de RSS para 2 M de pontos, **linear na entrada** | teste de **outra** propriedade |
| T31 | premissa A-06: *"processo single-thread"* | Starlette roda endpoints síncronos em threadpool | erro de SQLite entre threads |

**Todos apareceram por acaso favorável.** Nenhum foi encontrado por um mecanismo desenhado
para encontrá-lo.

O critério de correção foi formulado pelo próprio registro do T29 e é generalizável:

> *"uma premissa só está protegida quando existe um teste que a mediria falhando"*

A correção é barata porque **o vínculo já existe**: premissas são numeradas na Fase 1,
achados têm id, a Fase 3 registra a resolução. Falta a checagem.

## 3.1 Catálogo irmão — cinco formas de teste verde que não testa

| forma | onde | o que falha |
|---|---|---|
| cenário errado | T21, T24 | o teste monta cenário que não exerce o critério |
| cobertura parcial do achado | T22, T23 | a correção fecha um caminho, o defeito volta por outro |
| condição inalcançável | T23 | a condição que o teste exerceria não pode ocorrer |
| invariante por construção | T25 | o teste passa com a premissa verdadeira **ou** falsa |
| teste que falha sem defeito | T30 | 5 diagnósticos, nenhum era defeito do produto |

O caso mais nítido é o **T23**: com `tamanho_janela == amostra_minima == 50` e
`deque(maxlen=50)`, `volumes_comparaveis` **nunca retornava falso**. A defesa contra REG-01
tinha correção, tinha teste, o teste passava, e a condição era inalcançável. **62 testes
verdes não notaram; o teste de mutação notou.**

## 3.2 Práticas que os agentes inventaram sozinhos

Nenhuma está na guidance. Todas produziram achado que o caminho padrão não produziria.

| prática | projetos | rendimento |
|---|---|---|
| **medição por estágio** antes de otimizar | T25, T26, T28, T29 | **4 de 12** — o palpite errou nos quatro |
| **micro-check por execução, não leitura** | T23, T25, T26, T29 | 4 de 12 — *"6 defeitos por RODAR, nenhum por ler"* |
| **teste de mutação** | T22, T23, T27, T32 | 4 de 12 — pegou a cobertura falsa do T23 |
| **mapa de testes derivado das specs** | T26, T29, T30 | 3 de 12 — encontra **erros nas specs**, não só no código |

> Quando quatro execuções independentes convergem para a mesma prática não prescrita, a
> prática pertence ao método.

---

# 4. O INSTRUMENTO — o que o lote descobriu sobre si mesmo

## 4.1 O gate de testes é forjável, e travou em 4 de 12 projetos

O hook `test-outcome.js` deixou de registrar resultado em **T21, T28, T30 e T31 (33%)**. Nos
quatro o agente destravou alimentando o classificador com a **saída real** de uma execução
real, e **nos quatro declarou o contorno por iniciativa própria** — um deles declarou até
uma invocação sintética feita durante o diagnóstico e substituída antes de avançar.

**Nenhuma falsificação ocorreu. O defeito é que o mecanismo não a impediria:** o hook aceita
qualquer JSON no stdin e o estado grava apenas `{outcome, phase, at}` — sem proveniência.

Três causas distintas, e a terceira mata a explicação simples:

| projeto | causa |
|---|---|
| T21, T30 | marcadores não cobrem a ordem de palavras do repórter do `node:test` |
| T28 | marcadores **casavam** e o hook não foi invocado |
| T31 | `-q` no `pytest.ini` + `-q` na linha = `-qq`, some o resumo, suíte verde fica inclassificável |

**Dois defeitos de projeto demonstrados** (separação feita pelo agente do T31): classificar
prosa em vez do código de saída, e *"não observado"* indistinguível de *"observado e
reprovado"*. **A causa de o hook não disparar permanece não determinada** — e isso está
dito assim de propósito.

## 4.2 O critério de saída registra a afirmação, não o estado do mecanismo

Os critérios de saída são substanciais: **390 registros, 791 caracteres de média, zero
vazios**. Mas nos quatro projetos em que o gate foi contornado, o critério `tests_passing`
registrou o resultado corretamente e **não mencionou que o mecanismo falhara**.

Um auditor que lesse apenas os critérios concluiria que o gate funcionou nos doze. O
contorno é conhecido **apenas porque o agente escreveu um `record_decision` separado**.

> **Todo defeito de método deste relatório veio do log narrativo, não dos critérios de
> saída.** Os critérios registram conformidade com precisão; a narrativa registra o que deu
> errado no caminho.

## 4.3 Instrução sem trava não muda comportamento

Quatro ocorrências no lote, **duas custaram descarte de projeto**: vocabulário de lente,
redeclaração por iteração, reset do laço 2↔3, e `duplica` intra-lente.

O último é instrutivo porque **não admite trava**: reconhecer que dois achados descrevem o
mesmo defeito é propriedade de qualidade, indecidível mecanicamente — e o próprio κ do lote
é a prova empírica. Mostra o limite do evidence-gating.

---

# 5. LIMITAÇÕES — medidas, não declaradas

## 5.1 A marcação de duplicatas é imprecisa, não irreprodutível

Esta é a correção mais importante em relação a leituras intermediárias do lote.

Painel completo, **51.565 pares avaliáveis** nos doze projetos:

| par de avaliadores | pares em comum | esperado ao acaso | κ de Cohen |
|---|---|---|---|
| **qwen full × gpt-5.4** | **84** | 1,01 | **0,338** |
| gerador × qwen full | 33 | 0,21 | 0,293 |
| gerador × gpt-5.4 | 45 | 0,47 | 0,217 |
| gerador × qwen Q4 local | 13 | 0,12 | 0,163 |
| Q4 local × qwen full | 17 | 0,26 | 0,140 |
| Q4 local × gpt-5.4 | 24 | 0,57 | 0,110 |

Pares marcados: gerador **71**, Q4 local 87, Qwen full 153, GPT **340**.

**Todos os pares estão dezenas de vezes acima do acaso.** O que varia é a **taxa de
marcação**, não o julgamento. O GPT recuperou **63%** das marcações do gerador lendo apenas
as descrições cegadas; o Qwen full, 46%.

**Vinte e sete pares foram confirmados pelos três** — gerador, Qwen full e GPT.

**Consequência:** a hipótese de que o gerador enxergaria relações irrecuperáveis do texto
(assimetria de informação) está **eliminada** — um leitor cego reencontra dois terços delas.
E a hipótese de que o construto seria indefinível fica **enfraquecida**.

## 5.2 O modelo local quantizado é outlier

O `qwen3.6:27b` Q4_K_M marcou **87 pares — mais que o gerador** — e compartilha só 17 com
sua própria versão full e 24 com o GPT. **Não marca pouco: marca outra coisa.**

Isto vale como dado próprio sobre o uso de modelos locais quantizados em tarefas de
julgamento semântico fino, e como advertência metodológica.

## 5.3 Autoavaliação

Os achados e as marcações primárias de duplicata vêm do **mesmo modelo gerador**. A
remarcação cega mede o tamanho do problema; não o elimina neste desenho.

## 5.4 Procedência da verificação humana varia

| procedência | projetos |
|---|---|
| operador executou e julgou | T23, T24, T25, T27, T28, T30, T31, T32 (**8**) |
| agente executou, operador julgou | T21, T22, T26 (3) |
| **operador aceitou sem executar** | **T29** (1) |

O T29 virou experimento natural não planejado: foi o único sem verificação humana, e
**quatro defeitos apareceram depois do *"parece tudo bem"*** do operador — três tracebacks
vazando para o usuário e a premissa P-A8 refutada. Aprovação não é verificação, e a prova
veio do projeto onde a verificação foi declinada.

## 5.5 Contornos declarados do harness

**Quatro em doze projetos (33%)**, todos divulgados por iniciativa do agente. A frequência
é dado; a integridade dos registros dependeu de boa-fé, não do mecanismo.

## 5.6 O que foi medido não é a taxonomia publicada

**Crítico para a redação.** Os gatilhos de **SUS, UX e GOV** foram reescritos na v0.12.9,
durante o ciclo 1, porque GOV e SUS ficaram em **0 ativações de 7 projetos** e nenhuma
reescrita de enunciado resolvia. Sem a correção, três lentes não teriam dado nenhum dado.

O paper, tanto no `baseline` quanto na versão atual, ainda traz o gatilho antigo de UX
(*"User-facing interface"*). **A RO3 mediu a taxonomia corrigida.** O descompasso é achado,
não erro a esconder — mas precisa estar no texto.

## 5.7 Escopo

Um agente gerador (Claude), doze projetos de porte comparável (8 a 12 módulos, sessão única
de 2 a 4 h), domínios escolhidos para cobrir as condicionais. Não é amostra aleatória de
software real.

---

# 6. CORREÇÕES FEITAS DURANTE O LOTE

Registradas porque a trajetória é parte do resultado, e porque leituras intermediárias
circularam.

| # | o que se afirmou | o que o dado mostrou depois |
|---|---|---|
| 1 | o Kimi acerta mais por ser **permissivo** | T24: caiu de 9,7 para 4,3 ativações |
| 2 | os externos ativam **sistematicamente menos** que a Fase 2 | T22: 9,0 e 10,3 contra 9 declaradas |
| 3 | os externos **concordam entre si** mais que com a Fase 2 | T23: kimi × Fase 2 subiu a 87% |
| 4 | **MEC** ativa por maturação da arquitetura | MEC entrou na it1 no T21 e ficou fora das 3 do T27; quem emergiu tarde foi MIG |
| 5 | a marcação de duplicatas **não é reprodutível** | painel de 4 avaliadores: todos dezenas de vezes acima do acaso |
| 6 | a causa do gate travar é o `PostToolUse` não entregar o payload | **não demonstrado** — corrigido para "causa não determinada" |
| 7 | o baixo desempenho do Qwen vem da **quantização** | o full ficou **abaixo** do Q4 |

Sete correções, cinco delas de leituras minhas contrariadas por projeto posterior. A entrada
sobre estimadores foi reescrita **quatro vezes**.

---

# 7. NÚMEROS DE REFERÊNCIA RÁPIDA

```
corpus            12 projetos · 1.100 achados · 1.029 defeitos · 130 módulos · 37 h
severidade        195 críticos · 657 importantes · 248 sugestões
descartes         7, todos documentados
ortogonalidade    0 lentes com contribuição exclusiva zero, em 4 clusterizações
sobreposição      média 11% · min 2% (ARQ) · max 33% (SUS)
pares de lentes   41 de 171 (24%) compartilham algum defeito · maior Jaccard 0,10 (DES×SUS)
ARQ × PRE         Jaccard 0,00 — a suspeita a priori do §4 não se confirma
robustez          união dos 4 avaliadores: 1.029 → 668 clusters, nenhuma lente em zero
ativação          9,7 de 12 condicionais por projeto (it1) · 3 projetos com conjunto evoluindo
estimadores       gpt 91% · kimi 89% · qwen Q4 81% · qwen full 74% (× Fase 2)
duplicatas        κ 0,110 a 0,338 · todos ≫ acaso · GPT recupera 63% do gerador
gate de testes    travou em 4 de 12 · 4 contornos declarados
```
