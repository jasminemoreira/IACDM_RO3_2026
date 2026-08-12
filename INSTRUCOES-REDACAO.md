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
concentram-se em SUS (11), OBS (10), CTR (9), RES (7), MEC (6), ETI (5), e **35 delas são
unidirecionais**.

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

# 7. ARQUIVOS DE APOIO

| arquivo | conteúdo |
|---|---|
| `RESULTADO-RO3.md` | **fonte única dos números** |
| `analise/saidas/AGREGADO-12.md` | Passos 1–5 do §4 sobre os doze |
| `analise/saidas/T*-FECHAMENTO.md` | fechamento por projeto |
| `T*/RETRABALHO.md` | defeitos pós-entrega (zero em doze) e achados pré-entrega |
| `ACHADOS-TAXONOMIA.md` | achados sobre os critérios das lentes, com histórico das revisões |
| `ACHADOS-METODO.md` | M1 a M8, sobre gates, hooks e safeguards |
| `CLASSIFICACAO-FORMA-VS-QUALIDADE-FASE2.md` | a regra que autoriza uma trava — **normativo** |
| `patches/MELHORIAS-POS-LOTE.md` | o que corrigir, com evidência por item |
| `LOG-OPERACAO.md` | os 12 projetos, os 7 descartes, as violações de protocolo |

---

# 8. UMA FRASE PARA O ABSTRACT, SE FOR ÚTIL

> A taxonomia passa no teste de ortogonalidade; o critério que decide quando aplicá-la não
> passa; e o método produz compromissos — premissas, resoluções de achados críticos — que
> nenhum mecanismo reconfronta com o artefato construído.

Três resultados, um deles não planejado, todos com evidência no corpus.
