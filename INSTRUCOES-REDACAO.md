# Instruções para a redação do artigo — como usar os achados da RO3

Escrito em 2026-08-12, no fechamento do lote, para o chat que redige o `iacdm_arxiv.tex`.

**Fonte única dos números: `RESULTADO-RO3.md`.** Não recalcule nada a partir deste
documento nem de memória de conversas anteriores. Se um número que você tem não estiver
lá, ele está superado ou nunca existiu.

---

# REGRA ZERO — leituras intermediárias circularam e estão erradas

Durante o lote, sete afirmações foram feitas e depois contrariadas por dado posterior. Se
você viu qualquer uma delas em conversa anterior, **não use**:

| ❌ não escreva | ✅ o que o dado diz |
|---|---|
| "a marcação de duplicatas não é reprodutível" | é **imprecisa**: κ de 0,11 a 0,34, todos dezenas de vezes acima do acaso |
| "MEC ativa por maturação da arquitetura" | emergência tardia existe, mas **não é propriedade de MEC** — ocorreu com MIG, CTR e OBS |
| "o modelo local é pior por ser quantizado" | **refutado** — a versão full ficou abaixo |
| "o hook falha porque o PostToolUse não entrega o payload" | causa **não determinada**; o que é demonstrado são outras duas coisas |
| "os estimadores externos ativam menos que a Fase 2" | não há viés direcional de contagem |
| "os externos concordam entre si mais que com a Fase 2" | depende do estimador; não sustentável |
| "a distinção condicional/universal é quase vazia" | 9,7 de 12 em média — alto, mas não universal |

---

# 1. O QUE PODE SER AFIRMADO, E COM QUE FORÇA

## 1.1 Afirmação forte — use sem hedging

> **Nenhuma das 19 lentes apresentou contribuição exclusiva zero.**

Vale para os doze projetos, para o agregado, e sob **quatro clusterizações independentes**
do que conta como "mesmo defeito", incluindo a união de todas — que colapsa 1.029 defeitos
em 668 e ainda assim não zera nenhuma lente.

**Sempre acompanhe do argumento de distribuição**, porque o veredito binário sozinho é
fraco: o §4 exige 100% de sobreposição para remover uma lente, e a barra é praticamente
inalcançável. O que sustenta a conclusão é sobreposição média de **11%**, máximo de 33%, e
**41 de 171 pares** compartilhando algum defeito.

**Inclua `ARQ × PRE` = 0,00.** É o único par que o protocolo nomeia como suspeito *a
priori*, e a predição da própria teoria falhou. Predição que podia falhar e falhou vale
mais que confirmação de expectativa.

## 1.2 Afirmação forte — o achado não planejado

> **A taxonomia se sustenta; o critério que decide quando aplicá-la, não.**

Base: pergunta central e gatilho descrevem coisas de tipos diferentes em pelo menos cinco
lentes. **A evidência é textual, não estatística** — as justificativas dos estimadores citam
o gatilho literalmente. Cite pelo menos duas (ETI e JOG são as mais limpas).

E o achado **resistiu a um estimador que acerta 91%**: as divergências não se espalham,
concentram-se em SUS (11), OBS (10), CTR (9), RES (7), MEC (6), ETI (5).

> ⚠ **Correção (2026-08-12): NÃO use "35 divergências unidirecionais" como força de evidência.**
> Esse 35 é **por estimador, somado sobre três** — superestima em uma ordem de grandeza. Os
> **casos limpos** (os dois estimadores capazes concordando entre si *contra* a Fase 2) são
> **três**. E a adjudicação por contribuição exclusiva nesses três: **CTR e ETI produziram
> exclusivos** (6 defeitos, 1 crítico) — seguir os externos os teria perdido; **SUS não**
> (os 3 achados eram compartilhados, o que é o resultado de ortogonalidade de SUS, não veredito
> de ativação). A adjudicação é n=3, não-unânime, e **pega emprestada a variável dependente do
> estudo** (exclusividade). Por isso o warrant da reescrita é a **misleitura documentada** — os
> estimadores citam o gatilho estreito, evidência textual — **não** "a Fase 2 acerta".

## 1.3 Afirmação forte — o método não reverifica o que decide

> **Premissas da Fase 1 e resoluções da Fase 3 não são reconfrontadas com o código.**

Quatro ocorrências, quatro mecanismos independentes, **todas descobertas por acaso
favorável**. Este é o achado com correção mais óbvia e mais barata, porque o vínculo já
existe: premissas numeradas, achados com id, resoluções registradas.

Use a formulação do corpus: *"uma premissa só está protegida quando existe um teste que a
mediria falhando"*.

## 1.4 Afirmação moderada — cinco formas de teste verde que não testa

Catalogue as cinco com um exemplo cada. **A mais forte é a condição inalcançável do T23**,
porque tem número: desligar a checagem derrubava 2 testes contra 14 de outra mutação, e o
número baixo era o sintoma.

Diga que **nenhum safeguard da metodologia cobre a classe**, e que as contramedidas que
funcionaram foram inventadas pelos agentes.

## 1.5 Afirmação moderada — instrução sem trava não muda comportamento

Quatro ocorrências, duas com descarte de projeto. **Enquadre como validação empírica do
evidence-gating**, que é desenho da própria metodologia.

E use o caso limite: `duplica` intra-lente **não admite trava**, porque é propriedade de
qualidade. Isso mostra a fronteira do princípio, e é mais interessante que os casos que
funcionaram.

## 1.6 Afirmação fraca — use com ressalva explícita

Emergência tardia de lentes (3 de 12 projetos). Diferença de capacidade entre estimadores
como fator da concordância. Ambas são observações com n pequeno.

---

# 2. O QUE NÃO PODE SER AFIRMADO

**Nunca escreva que as 19 lentes são a taxonomia certa, suficiente ou ótima.** O
experimento mostra que **nenhuma é redundante** no corpus medido, sob o critério
pré-registrado. Não testou completude, nem se outra divisão seria melhor.

**Nunca apresente a concordância entre estimadores como medida de qualidade da taxonomia.**
Ela mede reprodutibilidade da ativação — coisa diferente.

**Nunca afirme causa para o gate de testes não disparar.** Duas fragilidades estão
demonstradas; a causa não. O agente do T31 recusou-se a afirmar e a razão dele deve ser
respeitada no texto.

**Nunca use os κ sem a taxa de marcação ao lado.** κ baixo com taxas muito diferentes não
significa discordância — foi exatamente o erro que este lote cometeu e corrigiu.

**Nunca chame de falsificação o que houve com o gate.** Não houve. O achado é que o
mecanismo não impediria.

---

# 3. O DESCOMPASSO QUE PRECISA APARECER NO TEXTO

**Os gatilhos de SUS, UX e GOV foram reescritos durante o experimento**, na v0.12.9, porque
GOV e SUS ficaram em 0 ativações de 7 projetos e nenhuma reescrita de enunciado resolvia.
Sem a correção, três lentes não produziriam dado nenhum.

**O paper ainda traz o gatilho antigo de UX** — *"User-facing interface"* —, tanto no
`baseline-2026-08-03` quanto na versão atual.

Portanto: **a RO3 mediu a taxonomia corrigida, não a publicada.**

Isto tem de estar dito, e não como nota de rodapé envergonhada. É achado: um gatilho
redigido como condição organizacional (*"múltiplas equipes"*) não consegue ser exercitado
por uma pergunta central que é sobre propriedade do sistema (*"toda ação é atribuível?"*).
O texto do artigo precisa ser atualizado com os gatilhos medidos, e a mudança precisa ser
declarada.

> **Atualização (2026-08-12): o conjunto Y final das 12 já existe e está medido.** Os nove
> gatilhos restantes foram reescritos sob a mesma regra e **medidos nos dois leitores** (ver §6-bis
> e o `DIFF-TAXONOMICO-GATILHOS-CONDICIONAIS.md`). O texto do artigo pode citar o conjunto Y
> completo como a taxonomia corrigida — sempre sob o enquadramento do §6-bis (RO3 mediu X; Y é a
> correção; testar Y é trabalho futuro). **X está congelada e citável: DOI 10.5281/zenodo.21908907.**

---

# 4. COMO TRATAR AS CORREÇÕES DE PERCURSO

Sete leituras foram contrariadas por dado posterior; a entrada sobre estimadores foi
reescrita quatro vezes. **Isto é força, não fraqueza, e deve aparecer.**

Sugestão de enquadramento: o desenho previa análise incremental projeto a projeto, e cada
projeto novo teve poder de refutar a leitura anterior. Cinco refutações ocorreram. Um
resultado que sobreviveu a isso é mais confiável que um resultado computado uma vez no fim.

**Mencione especificamente que a hipótese registrada antes de rodar o terceiro avaliador
foi contrariada.** A expectativa declarada era que o construto fosse indefinível; o dado
mostrou o contrário. Registrar a expectativa antes e publicar a refutação é o que separa
pré-registro de decoração.

---

# 5. NÚMEROS QUE PRECISAM DE CUIDADO NA CITAÇÃO

| número | cuidado |
|---|---|
| **1.029 defeitos distintos** | é sob a marcação do **gerador**. Sob a união dos 4 avaliadores são **668**. Sempre diga qual clusterização |
| **sobreposição 11%** | é média sobre as 19 lentes, sob a marcação do gerador |
| **91% do gpt-5.4** | é concordância com a **declaração da iteração 1**, não com a união das iterações. A distinção importa: 3 projetos têm conjuntos diferentes por iteração |
| **37 h** | soma de `createdAt → updatedAt`, inclui pausas do operador. Não é esforço |
| **12 projetos** | houve **7 descartes**. O §4 do EXPERIMENT-PROTOCOL exige que exclusões sejam contadas e reportadas — reporte |
| **κ de Cohen** | par a par. Não há Fleiss no relatório; se quiser um número único entre três avaliadores, precisa ser calculado |
| **35 divergências unidirecionais** | **por estimador, somado sobre três.** Os casos limpos (dois capazes concordando contra a Fase 2) são **três**. Não citar 35 como força de evidência |

---

# 6. ESTRUTURA SUGERIDA PARA A SEÇÃO DE RESULTADOS

1. **Corpus e procedimento** — 12 projetos, instrumento único, 7 descartes com motivo.
2. **Resultado principal** — ortogonalidade, com a distribuição e o teste de robustez das
   quatro clusterizações.
3. **Resultado secundário** — o critério de ativação, com a evidência textual.
4. **Achados de método** — a lacuna de reverificação e as cinco formas de teste verde.
5. **Limitações medidas** — §5 do `RESULTADO-RO3.md`, inteira.
6. **Ameaças à validade** — autoavaliação, escopo, taxonomia corrigida × publicada.

A seção 5 **não é opcional e não deve ser encurtada**. O valor deste experimento está tanto
no que ele mediu quanto no que ele mediu sobre a própria medida.

---

# 6-bis. O EXPERIMENTO DOS GATILHOS Y — o que ele acrescenta ao artigo

Acrescentado em 2026-08-12, depois do fechamento do corpus. É **segundo grau**: não fala de
ortogonalidade, fala de **como se escreve um critério de ativação para um leitor-agente**.
Não misture com o Resultado 1.

## O desenho, que é o que dá valor

Os gatilhos propostos na correção (Y) foram aplicados aos doze pacotes de estimativa
**arquivados** e rodados com os dois estimadores capazes. O pacote Y difere do X em
**exatamente 18 linhas — os nove pares reescritos**; todo o resto é idêntico byte a byte.
Três lentes **não** foram reescritas e servem de **controle**.

| variação absoluta de ativação | GPT | Kimi |
|---|---|---|
| nas nove reescritas | **26** | **17** |
| nas três de controle | **1** | **3** |

É um experimento controlado sobre **formulação de critério**, com corpus fixo, leitores
fixos e uma única variável manipulada. Isso é raro de conseguir, e vale relatar pelo método
tanto quanto pelo resultado.

## Contribuição 1 — a forma não determina a seletividade; o conteúdo determina

**É o achado mais transferível do experimento inteiro**, e serve a qualquer pessoa que
desenhe ativação de lente, checklist ou heurística para agente.

A intuição natural — e a que a própria correção assumia como risco — é que trocar
*"lista fechada de exemplos"* por *"condição geral + exemplos ilustrativos + aplique a
pergunta"* faria o critério ativar em quase tudo.

**Falso, e o contraexemplo estava dentro do próprio instrumento.** SUS recebeu essa forma
na v0.12.9:

> *"The system decides, allocates, or consumes a resource whose cost grows with use — e.g.
> (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the
> central question, do not just match the examples"*

Se a forma universalizasse, SUS estaria em 12/12. Medido: **8–9 de 12 no GPT, 4–5 no
Kimi** — a **menos ativada de todas**, mais seletiva que qualquer lente ainda em forma
antiga.

O que separa SUS de uma condição que ativa em tudo é o **conteúdo**: *"consome recurso cujo
custo cresce com o uso"* exclui muito software. *"Decisão consequente que pode prejudicar
uma parte"* — a formulação proposta para ETI — não exclui quase nada, e mediu **+9**,
saindo de 3 para 12 de 12.

**Enunciado para o artigo:** um critério de ativação legível por agente precisa que a
condição seja substantivamente restritiva; a forma retórica não substitui isso. E há teste
barato — medir a ativação num corpus fixo.

## Contribuição 2 — a correção pode reproduzir o defeito que corrige

**CTR foi a única reescrita cujo efeito não replicou entre os dois leitores** — −3 no GPT,
0 no Kimi. É o único movimento negativo do lote.

Ou o texto novo é ambíguo o bastante para dois leitores capazes divergirem — que é
**exatamente a falha que a reescrita existe para eliminar** — ou é ruído. O dado não decide,
e isso é o ponto: **uma correção de critério precisa ser medida, não só argumentada**, pelo
mesmo motivo que o critério original precisava.

> **Resolução (2026-08-12, segundo round).** A dúvida fechou por medição. Uma segunda
> formulação de CTR — que **preserva a enumeração do X como ilustração** em vez da cláusula
> "regula vs. reage" — mediu **+1 nos dois leitores**. O efeito **replicou**, o que diagnostica
> a causa: era a **cláusula ambígua**, não ruído. Ou seja, a Contribuição 2 fica mais forte —
> a re-medição não só sinalizou o risco, **identificou-o**. CTR-conservador assentou em 9/7
> (abaixo dos 11/6 de X): recupera parte da seletividade, não toda.

## Contribuição 3 — a categoria "condicional" já era fraca antes de qualquer reescrita

Sob os gatilhos originais, **sete das doze condicionais ativam em 12/12**. E não é ativação
por inércia: cada uma produz **no mínimo 3 achados em todo projeto** (mediana 4 a 7).

Isso separa duas hipóteses que a contagem de ativação sozinha não separa: *ativa sempre
porque o gatilho é frouxo* × *ativa sempre porque a pergunta se aplica sempre*. Os números
apontam a segunda — o que é achado sobre a **arquitetura da taxonomia**, não sobre a
redação dos gatilhos.

## ⚠ A ressalva que precisa acompanhar qualquer número deste experimento

**Os leitores são os estimadores externos, que veem apenas a arquitetura V(1).** A Fase 2
real tem o contexto da Fase 0 — teach-back, ambiguidades resolvidas, fora-de-escopo — que
eles não têm.

Logo:

| | vale? |
|---|---|
| **o delta X → Y** | **sim** — mesmos leitores, mesmo pacote, uma variável |
| **o nível absoluto** ("sob Y, ETI ativa em 12/12") | **não é o comportamento do método** — é o de um leitor pobre em contexto |

Escrever *"sob Y, ETI ativaria em todos os projetos"* seria erro. O correto é *"sob Y, um
leitor externo ativa ETI em todos os projetos, contra 3 sob X"*.

## Contribuição 4 (segundo round) — nenhum leitor é privilegiado, e ETI o mostra

**A adjudicação corta nos dois sentidos.** A leitura fácil é que a Fase 2 é o leitor bom (acerta
onde os externos erram, como no T25). Mas em ETI a **Fase 2 sub-ativava**: nos quatro projetos em
que ela deixou ETI de fora, o material ético **apareceu mesmo assim** — carregado por tabela em
GOV, REG e PRO, cujas descrições traziam achados que são de ética. Isso é evidência **independente
da própria lente e do estimador externo** (vem dos achados do corpus), e sustenta que **9/12 é mais
correto que os 5 da Fase 2** — correção, não erosão.

Isso **qualifica a ressalva acima para ETI**: o nível absoluto de um leitor externo continua não
sendo o comportamento do método, mas aqui há evidência corpus-interna de que a ativação verdadeira
de ETI é maior que os 5 da Fase 2. **Prova por proxy** — busca de vocabulário de dano a pessoas nas
descrições em PT; o que convence é a **separação sem sobreposição** entre os grupos, não a contagem
absoluta. Fecho pleno opcional: ler os achados de GOV/REG desses quatro e confirmar que são
materialmente éticos.

**Enunciado para o artigo:** ao ajustar um critério de ativação, adjudique por evidência
**independente do próprio critério** — a Fase 2 não é o padrão-ouro, é mais um leitor.

## O que este experimento NÃO é

**Não valida Y.** As declarações da Fase 2 foram feitas sob X; comparar Y com elas seria
comparar dois instrumentos. O enquadramento do §3 continua: a RO3 mediu X, Y é a correção
derivada do achado, **testar Y é trabalho futuro**.

O que este experimento faz é substituir *"consequência de ativação projetada"* por
**consequência medida**, e isso mudou três das nove reescritas propostas.

> **Segundo round concluído (2026-08-12).** As três que a medição pegou (ETI, MIG, CTR) foram
> **re-formuladas e re-medidas** no mesmo pipeline, fechando as nove:
> - **MIG/Y2 — 3/3 nos dois leitores** (= X e = Fase 2). A cláusula "um armazém que só esta versão
>   lê não ativa" recuperou a seletividade inteira; MIG volta a ser condicional discriminadora.
>   (A projeção do primeiro diff, "MIG frouxa vai a 10/5", estava certa; a forma apertada a desfaz.)
> - **ETI/Y2 — 9/9**, convergente entre leitores. Restritiva o bastante para conter o alargamento a
>   "entidades", e — pela Contribuição 4 — 9 é o valor correto, não erosão.
> - **CTR-conservador — 9/7**, efeito replicado (Contribuição 2 acima).
>
> A extensão (Versus_Claude) já carrega as nove em Y (v0.16.2). O texto do artigo deve usar a
> tabela Y **final** (MIG 3 · ETI 9 · CTR 9/7 · OBS 12/11 · JOG 11/8 · demais 11–12), não os
> números do primeiro round (Y frouxa). **Ressalva metodológica:** o Kimi tem ±1–2 de variação de
> fundo por lente entre rodadas; movimentos dessa magnitude nele não são efeito. GPT é o leitor mais
> estável.

## Evidência

69 JSONs em `analise/cego/*-Y-V1-*`, com os pacotes ao lado. Gerador em
`analise/reestimar_Y.py`, que lê os gatilhos Y do documento de correção em tempo de
execução — nada transcrito à mão — e falha alto se o formato mudar, em vez de cair para X
em silêncio.

**Cobertura:** GPT nos doze; Kimi em **onze** — a cota da conta estourou no T32. Declarado
em toda tabela.

---

# 7. ARQUIVOS DE APOIO

| arquivo | conteúdo |
|---|---|
| `RESULTADO-RO3.md` | **fonte única dos números** |
| `analise/saidas/AGREGADO-12.md` | Passos 1–5 do §4 sobre os doze |
| `analise/saidas/T*-FECHAMENTO.md` | fechamento por projeto |
| `T*/RETRABALHO.md` | defeitos pós-entrega (zero em doze) e achados pré-entrega |
| `ACHADOS-TAXONOMIA.md` | achados sobre os critérios das lentes, com histórico das revisões |
| `ACHADOS-METODO.md` | M1 a M8, sobre gates, hooks e safeguards |
| `CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md` | a regra que autoriza uma trava — **normativo** (em `_tocheck/`) |
| `patches/MELHORIAS-POS-LOTE.md` | o que corrigir, com evidência por item |
| `LOG-OPERACAO.md` | os 12 projetos, os 7 descartes, as violações de protocolo |
| `DIFF-TAXONOMICO-GATILHOS-CONDICIONAIS.md` | X→Y das 12, medido; **insumo direto da §3 e §6-bis** (em `IACDM/`) |
| `patches/CORRECOES-EXTENSAO-POS-LOTE.md` | a spec executada; extensão aplicada até v0.16.2 |

---

# 8. UMA FRASE PARA O ABSTRACT, SE FOR ÚTIL

> A taxonomia passa no teste de ortogonalidade; o critério que decide quando aplicá-la não
> passa; e o método produz compromissos — premissas, resoluções de achados críticos — que
> nenhum mecanismo reconfronta com o artefato construído.

Três resultados, um deles não planejado, todos com evidência no corpus.
