# Gatilhos Y — de projeção a medida, e o que muda na decisão

Para o chat da extensão, em resposta ao `DIFF-TAXONOMICO-GATILHOS-CONDICIONAIS.md`.
Escrito em 2026-08-12.

**O que mudou:** a ressalva *"consequências de ativação = direção projetada, não medida"*
**deixou de ser necessária.** Os gatilhos Y foram extraídos do próprio diff, aplicados aos
doze pacotes de estimativa arquivados, e rodados com os dois estimadores capazes.

Isto **não** é validação da RO3 — as declarações da Fase 2 foram feitas sob X, e o
enquadramento do diff continua valendo palavra por palavra. É a **ativação medida de Y no
mesmo corpus**.

---

## O desenho, e por que a atribuição é limpa

O pacote Y difere do X em **exatamente 18 linhas — os nove pares reescritos**. Verificado
por `diff`: todo o resto é idêntico byte a byte. Mesma arquitetura V(1), mesma pergunta
central, mesma regra de ativação, mesmo template, mesmo modelo, três rodadas.

**Controle interno:** SUS, UI/UX e GOV não foram reescritas no diff. Em Y ficam idênticas
a X, e servem de linha de base.

| variação absoluta de ativação | GPT | Kimi |
|---|---|---|
| nas **nove reescritas** | **26** | **17** |
| nas **três de controle** | **1** | **3** |

O efeito é da reescrita, não do modelo.

**Cobertura:** GPT nos doze projetos; Kimi em **onze** — a cota da conta estourou no T32.
As colunas do Kimi são sobre 11, não 12.

---

## O resultado

| lente | Fase 2 (X) | GPT/X | **GPT/Y** | Δ | Kimi/X | **Kimi/Y** | Δ |
|---|---|---|---|---|---|---|---|
| **ETI** | 5 | 3 | **12** | **+9** | 3 | **9** | **+6** |
| **MIG** | 3 | 3 | **10** | **+7** | 3 | **5** | **+2** |
| **OBS** | 8 | 9 | **12** | **+3** | 6 | **10** | **+4** |
| JOG | 7 | 8 | 11 | +3 | 5 | 6 | +1 |
| RES | 12 | 10 | 11 | +1 | 10 | 11 | +1 |
| **CTR** | 11 | 11 | **8** | **−3** | 6 | 6 | **0** |
| MEC | 10 | 12 | 12 | 0 | 12 | 11 | −1 |
| LIN · PRO | 12 | 12 | 12 | 0 | 12·10 | 11 | −1·+1 |
| UX *(controle)* | 12 | 12 | 12 | 0 | 12 | 11 | −1 |
| GOV *(controle)* | 12 | 12 | 12 | 0 | 12 | 11 | −1 |
| SUS *(controle)* | 12 | 8 | 9 | +1 | 5 | 4 | −1 |

Média por projeto: Fase 2 **9,7** · GPT/X 9,3 → **GPT/Y 11,1** · Kimi/X 8,0 → **Kimi/Y 8,8**.

---

# O ACHADO QUE MUDA A DECISÃO

## A forma-condição **não** causa universalização. O conteúdo causa.

O diff monta o falso-binário assumindo que o Horn B — *"a pergunta larga decide"* —
colapsaria as condicionais em universais, e que a síntese herdaria parte desse risco.

**SUS refuta isso, e é o próprio precedente que o diff cita.** SUS já tem a forma-condição
desde a v0.12.9 — condição geral, exemplos rebaixados, a frase *"apply the central
question, do not just match the examples"*:

> `The system decides, allocates, or consumes a resource whose cost grows with use —
> e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure.
> Apply the central question, do not just match the examples`

Se a **forma** universalizasse, SUS estaria em 12/12. Medido: **8–9 no GPT, 4–5 no Kimi** —
a **menos ativada de todas** para os leitores externos, e mais seletiva que qualquer lente
ainda em forma-X.

**A diferença entre SUS e ETI não é de forma; é de conteúdo da condição.**

| | condição | é restritiva? |
|---|---|---|
| SUS | *"consome recurso cujo custo cresce com o uso"* | **sim** — muitos sistemas não |
| ETI/Y | *"decisão consequente que pode prejudicar ou excluir uma parte"* | **não** — quase todo software |
| MIG/Y | *"muda algo que já existe e está em uso"* | **não** — quase todo software |

**Consequência para a regra do V.1:** ela está certa, mas incompleta. A forma correta é

> O gatilho enuncia a condição que a pergunta implica, com exemplos rebaixados a
> ilustração — **e a condição precisa ser substantivamente restritiva, não apenas ter
> forma de condição.**

E existe teste: rodar a ativação medida no corpus arquivado, como acabou de ser feito.
Uma condição que ativa em 12/12 não é condição.

---

# VEREDITO POR LENTE

## Aplicar como está — 4 de 9

**RES, PRO, LIN, MEC.** Movimento nulo ou de ±1 nos dois estimadores. São reescritas de
**formulação**, exatamente como o diff prevê. LIN vale por si: conserta a misleitura
documentada (*"contratos internos no mesmo repo"* → recusa indevida) sem mexer na ativação.

## Aplicar, aceitando a erosão — 2 de 9

**OBS** (+3, +4) e **JOG** (+3, +1). Erodem como previsto, nos dois leitores, com magnitude
moderada. A erosão é o preço declarado e o diff já a assume.

## Revisar antes de aplicar — 2 de 9

### ETI — a maior erosão do lote, e evitável

+9 e +6, indo a 12/12 e 9/11. A extensão de *"prejuízo a pessoas"* para *"prejuízo a
entidades"* torna a condição não-restritiva.

**E o caso que motivou a reescrita não exige isso.** No T25 o corte de orçamento afeta quem
depende do serviço — uma pessoa, pela via da entidade. Formulação sugerida:

> *"…uma decisão consequente cujo efeito recai sobre pessoas, diretamente ou pela entidade
> de que dependem. Aplique a pergunta central — quem pode ser prejudicado? — sem exigir que
> a decisão seja nominalmente 'sobre pessoas'."*

Conserta o T25, preserva a identidade da lente, e mantém a condição restritiva: software que
não decide nada consequente sobre ninguém continua fora.

**Risco medido de não revisar:** ETI já tem 17% de sobreposição, a quarta maior. `ETI × GOV`
está em Jaccard 0,00 e `ETI × REG` em 0,018 — há muito espaço para piorar, e alargar para
"entidades" empurra ETI para o território de governança e conformidade.

### MIG — a projeção do diff não se sustenta

O diff aposta que MIG *"permanece genuinamente condicional"* e seria *"a última que
discrimina"*. Medido: **3 → 10** no GPT e **3 → 5** no Kimi. Erode nos dois.

O Y de MIG aceita *"um formato de dado armazenado, um contrato vivo"* como o "velho" a
preservar — e praticamente todo sistema tem um.

**Duas saídas.** Ou apertar a condição de volta para algo restritivo — *"existe estado ou
contrato **já em uso por terceiros** que precisa sobreviver à transição"* — ou aceitar e
**corrigir a afirmação do diff**, que hoje anuncia uma sobrevivente que os dados não
mostram.

## Segurar — 1 de 9

### CTR — único efeito que **não replica** entre estimadores

**−3 no GPT, 0 no Kimi.** É o único movimento negativo do lote, e não se reproduz.

A cláusula *"regula em vez de apenas reagir"* é **mais restritiva** que o X, que listava
"sincronização de estado, configuração em tempo de execução". Ou o texto é ambíguo o
bastante para dois leitores capazes divergirem — que é **o mesmo defeito que Y existe para
corrigir** — ou é ruído do GPT. O dado não decide.

**E CTR é a lente com a adjudicação positiva mais forte do corpus:** no único caso em que a
Fase 2 a ativou contra os dois externos, ela produziu **3 defeitos exclusivos, 1 crítico**.
O Y a faz ativar menos justamente onde ela se mostrou produtiva.

**Recomendação: não aplicar CTR nesta rodada.** Reescrever preservando a enumeração do X
como ilustração — em vez de trocá-la pela cláusula "regula vs. reage" — e medir de novo.

---

# CORREÇÕES NECESSÁRIAS NO TEXTO DO DIFF

1. **A tabela de consequências deixa de ser projeção.** Substituir por medida, com as duas
   colunas de estimador e a nota de que Kimi cobre 11 de 12.
2. **A conclusão *"MIG fica como a única condicional viva"* está refutada.** Sob Y, MIG vai
   a 10 e 5. Ou apertar MIG, ou reescrever a conclusão.
3. **A projeção de ETI — "sobe de 5", erosão parcial — subestima.** É a maior do lote.
4. **CTR estava classificada como "formulação apenas, sem mudança de ativação".** Medido:
   −3 no GPT. Reclassificar.
5. **Acrescentar o achado do SUS**, que é o mais forte do documento inteiro: a forma-condição
   não universaliza; SUS a tem desde a v0.12.9 e é a mais seletiva de todas. Isso responde
   à objeção do Horn B com evidência em vez de argumento.

---

# O QUE NÃO MUDA

**O enquadramento do paper continua inegociável**, e a medição não o afeta: a RO3 mediu X;
Y é a correção derivada do achado; testar Y é trabalho futuro. Esta medida é ativação de Y
no corpus arquivado, **não** um novo veredito de acerto contra a Fase 2 — comparar Y com
declarações feitas sob X seria comparar dois instrumentos.

**O warrant continua sendo a misleitura**, não a exclusividade. A adjudicação por
contribuição exclusiva permanece n=3, não-unânime, e pega emprestada a variável dependente
do estudo — a objeção do diff está correta e deve ficar.

---

# EVIDÊNCIA

Os **69 JSONs** das rodadas Y estão em `analise/cego/*-Y-V1-*`, com os pacotes Y ao lado.
O gerador é `analise/reestimar_Y.py`, que **lê os gatilhos Y do próprio diff** em tempo de
execução — nada foi transcrito à mão — e **falha alto** se o formato mudar, em vez de cair
para X em silêncio. Uma "medição de Y" que na verdade mediu X seria o pior desfecho aqui.

Reproduzir:

```bash
OPENAI_API_KEY=... python3 analise/reestimar_Y.py T21-certificados --n 3
```
