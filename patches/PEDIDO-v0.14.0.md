# Pedido de correção — v0.14.0

Contra a **v0.13.1**. Dois blocos que compõem: o primeiro põe a declaração de lentes em
estado estruturado; o segundo usa esse estado para validar a coluna `lente` de cada
achado. Sozinho, nenhum dos dois resolve o caso que motivou o pedido.

**O que motivou.** No T21-quotas (ciclo 2, projeto 1), quatro achados — SUS-01 a SUS-04 —
trazem `Sustainability` na coluna de lente, em vez do nome canônico
`Sustainability / Proportionality`. A v0.12.1 fixou o vocabulário **na guidance**
("use o nome exato, nunca abreviação ou tradução"), mas nada verifica: o gate
`artifactRows` só confere que a linha tem um id no primeiro campo, e a coluna de lente
passa sem checagem. É a terceira vez no lote que instrução sem trava se mostra
insuficiente.

Consequência da correção: **o T21 será descartado** (segundo descarte do mesmo slot) para
que os doze rodem sob instrumento único.

---

## Bloco 1 — declaração de lentes como estado estruturado

Já existe implementado e testado em
`RO3/patches/lentes-estruturadas.patch`, contra a 0.12.4. **Precisa ser reaplicado sobre
a 0.13.1**, que mudou `phases.ts` e `engine.ts` desde então — provavelmente não aplica
limpo, e o conteúdo abaixo descreve o que ele faz para você reimplementar ou rebasear.

### 1.1 `src/rules/lenses.ts` (novo) — as 19 lentes como dado

Hoje os nomes existem só como prosa dentro da tabela da Fase 2, então nada pode
validá-los. Fonte única, exportando `UNIVERSAL_LENSES` (7), `CONDITIONAL_LENSES` (12),
`ALL_LENSES`, e `canonicalLens(raw)` — que tolera caixa e espaço em volta da barra
(`UI / UX` = `UI/UX`) mas **não** traduções nem abreviações.

### 1.2 `record_activated_lenses(conditional, notActivated)` — ferramenta MCP nova

Substitui a declaração em prosa livre. O `enum` do schema aceita só os 12 nomes
condicionais, então uma abreviação é recusada **na chamada**, não descoberta meses depois
na agregação. Exige que **as 12** estejam contabilizadas — ativada, ou não-ativada **com
motivo**. Faltar uma é erro: "não ativei" e "esqueci" não podem parecer a mesma coisa.

Quatro bugs foram encontrados por bateria adversarial contra a versão original e já estão
corrigidos no patch guardado — vale reproduzi-los como testes:

- mesma lente em `conditional` **e** `notActivated` → recusa (o registro se contradiria);
- lente duplicada dentro de `conditional` → recusa (infla a contagem passando pela
  checagem de completude);
- lente **universal** passada como condicional → recusa (a contagem de condicionais é
  variável medida da RO3; `canonicalLens` sozinho aceita as 19 e deixa passar);
- `notActivated` com lente universal → mesma recusa.

### 1.3 `state.activatedLenses` — campo estruturado

`{ universal: string[], conditional: string[], notActivated: {lens, reason}[], iteration: number, againstVersion: number, recordedAt: string }`

**Uma entrada por iteração**, não uma acumulada — a v0.12.6 já exige redeclaração a cada
volta do laço, e o histórico por iteração é o que permite casar cada achado com o
conjunto vigente quando ele foi produzido.

### 1.4 `activated_lenses_recorded` passa a ter evidência

`verify: "lenses-recorded"` — o campo estruturado precisa existir **para a iteração
corrente**. Hoje o critério é booleano carimbável, o único da Fase 2 sem evidência.

Compatibilidade: projetos iniciados antes disso não devem ser bloqueados
retroativamente. O patch guardado aceita, como fallback, a decisão em prosa com os
marcadores `ACTIVATED LENSES` ou `LENTES ATIVADAS`.

> ⚠ **O fallback fura a garantia em projeto novo.** Se o modelo usar o `record_decision`
> antigo, o gate passa sem o enum e sem a checagem das 12. Para o lote, onde os doze são
> novos, o fallback deveria ser condicionado à idade do estado — por exemplo um
> `stateVersion` carimbado em `init_project`, com a prosa só aceita quando o marcador
> está ausente. Sem isso a garantia estrutural é opt-in via guidance, que é o que o
> evidence-gating deveria remover.

---

## Bloco 2 — validar a coluna `lente` de cada achado

É o que resolve o caso do T21, e depende do bloco 1 para a forma forte.

### 2.1 Forma mínima — nome canônico

Toda linha de achado da `coverage-matrix.md` precisa trazer, na **terceira** célula, um
dos 19 nomes canônicos de `lenses.ts`, ou o literal `NENHUMA` (o canal declarado no §4 do
protocolo para achado que não coube em nenhuma lente). Qualquer outra coisa bloqueia
`advance_phase`, nomeando a linha e o valor encontrado.

A comparação usa `canonicalLens()`: tolera caixa e espaçamento da barra, recusa
abreviação e tradução. `Sustainability` seria recusado; `sustainability / proportionality`
seria aceito.

### 2.2 Forma forte — pertencer ao conjunto declarado naquela iteração

Com o bloco 1 no lugar, o gate sabe quais lentes estão ativas em cada iteração. Então a
checagem passa a ser: **a lente do achado tem que estar entre as declaradas para a
iteração dele** (universais sempre valem).

A iteração vem do cabeçalho `## Iteração N — V(N)` que a v0.12.6 já exige.

> ⚠ **A armadilha aqui é a mesma do gate cruzado de módulos da v0.13.0**, e ela já custou
> caro uma vez: validar contra o conjunto **da iteração do achado**, nunca contra o da
> iteração corrente nem contra a união. Um achado da iteração 1 usando uma lente que só
> ela declarou é legítimo; a v0.12.6 existe justamente porque o conjunto muda entre
> rodadas (no T14 do ciclo 1, MEC entrou só na iteração 2). Um gate ingênuo aqui bloqueia
> todo projeto cujo conjunto de lentes evoluiu — que passou a ser o caso normal.

### 2.3 O que NÃO muda

**O formato da linha de achado continua congelado:** `id | módulo | lente | severidade |
descrição`, id na **primeira** célula. O §5 do protocolo o congelou, os 15 casos da suíte
adversarial testam contra ele, e o gate `artifactRows` casa
`\|\s*(?!M-)[A-Za-z]{1,4}-\d+\s*\|` — qualquer coluna nova antes do id quebra o gate da
própria extensão.

---

## Contrato que a análise vai ler

Se o bloco 1 entrar, `ler_lentes_ativas()` passa a preferir `state.activatedLenses`
(estruturado, por iteração) e a manter o parse da prosa só como fallback para projetos
antigos. Preciso saber:

1. **O nome exato dos campos** de `LensActivation`, para eu ler sem adivinhar.
2. Se há **uma entrada por iteração** ou uma lista dentro de um único campo.
3. Se `init_project` passa a carimbar algum marcador de versão de estado (o `stateVersion`
   da ressalva do 1.4), e qual o nome.

Com essas três respostas eu adapto o parser, amplio a suíte adversarial — lente fora do
canônico na matriz, lente de outra iteração, declaração estruturada ausente — e rodo tudo
antes do T21 recomeçar. Foi assim que a 0.12.6 não me pegou de surpresa, e foi não fazer
isso que deixou a 0.12.5 quebrar meu parser sem eu perceber.

---

## Verificação sugerida antes de empacotar

A bateria adversarial contra `record_activated_lenses` achou quatro bugs na primeira
rodada, numa superfície que parecia pronta. Vale repetir o exercício no bloco 2: matriz
com nome abreviado, com tradução, com `NENHUMA`, com lente válida mas não declarada
naquela iteração, e com lente declarada só numa iteração posterior.
