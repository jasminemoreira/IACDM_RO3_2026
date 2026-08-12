# Fechamento — T26-extratos

Sexto projeto válido do ciclo 2, e o maior. Concluído 2026-08-10, 2,7 h, 8 fases,
instrumento **versus-claude 0.14.2**.

112 achados · 12 módulos · 2 iterações · 108 defeitos distintos · 51 decisões.

Passos 1–5 em `T26-extratos-passos.md`. Agregado dos seis em `AGREGADO-6.md`.

---

## 1. Formato: limpo — e o primeiro conjunto de lentes que evolui

Validação sem recusas. E aconteceu o caso que motivou a v0.12.6: **MIG não está na
iteração 1 e entra na iteração 2**, contra a V(3), com `MIG-01` a `MIG-03` corretamente na
iteração 2.

| | condicionais |
|---|---|
| it1 vs V(1) | 9 — RES, UX, SUS, PRO, GOV, OBS, CTR, LIN, MEC |
| it2 vs V(3) | **10** — as mesmas mais **MIG** |

Antes da v0.12.6 a declaração era fixa contra a V(1) e esses três achados viriam de uma
lente formalmente inativa. O gate aceitou porque valida cada achado contra o conjunto **da
iteração dele** — a armadilha que o `PEDIDO-v0.14.0` sinalizava. **É a validação em
produção de uma correção que custou os descartes do T13 e do T05.**

## 2. Ativação: 9 na it1, 10 na it2

Série (it1): **11 · 9 · 9 · 10 · 11 · 9**, média 9,8 de 12.

MIG sobe para 2 de 6 — e agora com evidência de que ela **emerge com a revisão da
arquitetura**, não com o domínio. Mesmo padrão que se suspeitava de MEC, e desta vez o
projeto todo é sobre importação de fontes múltiplas: MIG "deveria" ativar na V(1) por
domínio e não ativou.

## 3. Estimativa cega — e um defeito meu que a corrigiu

Este projeto expôs um erro no meu comparador. Ele confrontava a estimativa sobre a **V(1)**
com a **união** das iterações, o que contava MIG como declarada. Nos cinco projetos
anteriores o conjunto era idêntico entre iterações, então união == it1 e o erro era
invisível.

Corrigido para comparar contra a declaração **daquela iteração** — que é exatamente a
equivalência informacional que justifica o módulo. Resultado:

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 9 | **11** |
| **divergem** | **0** | **0** |
| oscilaram | 3 | 1 |

**Zero divergências nos dois estimadores.** Os dois disseram "não" a MIG sobre a V(1), e
estavam certos: a Fase 2 também não a declarou ali.

Verifiquei que nada muda nos cinco anteriores — em todos o conjunto é idêntico entre
iterações.

### Concordância acumulada, seis projetos

| projeto | qwen | kimi | F2 | q×k | q×F2 | k×F2 |
|---|---|---|---|---|---|---|
| T21-certificados | 7,3 | 9,7 | 11 | 7/8 | 7/10 | 10/10 |
| T24-catalogo | 5,3 | 4,3 | 9 | 8/9 | 7/10 | 7/11 |
| T22-plantoes | 9,0 | 10,3 | 9 | 6/7 | 8/10 | 6/8 |
| T23-canario | 6,3 | 9,3 | 10 | 8/10 | 8/11 | 11/11 |
| T25-orcamento | 8,7 | 10,0 | 11 | 9/9 | 8/9 | 11/12 |
| **T26-extratos** | 8,7 | 8,3 | 9 | **8/8** | **9/9** | **11/11** |
| **total** | | | | **90%** | **80%** | **89%** |

Segunda rodada seguida sem desmentir a anterior, e as três subiram. O qwen segue ~10
pontos abaixo dos outros dois. Regra mantida: nada direcional antes dos doze.

## 4. Remarcação cega

κ = **0,000**. O juiz cego devolveu zero agrupamentos em 112 achados; o gerador marcou 2
grupos (7 pares).

Série completa: **0,000 · 0,000 · 0,362 · 0,115 · 0,249 · 0,000**. Três dos seis em zero
absoluto. A não-reprodutibilidade da marcação de duplicatas é o achado mais estável do
lote — mais estável que qualquer número de ortogonalidade.

## 5. Ortogonalidade — agregado dos seis

**508 achados · 479 defeitos distintos · nenhuma lente com contribuição exclusiva zero.**

Sobreposição média **9%**. Quatro lentes em **0%**: ETI, OBS, **LIN** e MIG.

LIN em **34 defeitos, 34 exclusivos, 0%** — a distância só cresce.

**O par DES × SUS enfraqueceu:** Jaccard de defeitos caiu de 0,23 (4 projetos) para 0,15
(6). Continua o maior do lote, mas a hipótese de que as duas lentes convergem para a mesma
pergunta perde força com mais dados, em vez de ganhar.

## 6. Método e instrumento

Detalhe em `T26-extratos/RETRABALHO.md`. Zero defeitos pós-entrega.

**Classe nova, §M6 — a implementação da Fase 5 desfez a correção da Fase 3.** VAL-4
estourou 120 s contra limite de 60 s por **três padrões quadráticos reintroduzidos** depois
que a arquitetura os havia eliminado: *"é exatamente o O(n²) acidental que PRF-01 e PRF-02
mandaram erradicar, reintroduzido na função de filtro"*.

É distinta das quatro formas de §M4 e §M5, onde o defeito estava no teste. Aqui a crítica
estava certa, a correção estava completa, e nada verifica que a implementação **preserva** a
propriedade estabelecida. Só apareceu porque VAL-4 era critério **numérico e medido** — sem
número associado, teria passado. É o candidato pós-lote mais acionável do lote, porque o
vínculo já existe: cada achado tem id, a Fase 3 registra a resolução, falta a checagem.

**Dez defeitos na Fase 5, nenhum achado lendo código.** Os registros nomeiam o mecanismo em
cada um: *"pela micro-verificação S7, não por teste"*, *"executando a rubrica do matcher,
não por teste formal"*, *"por MEDIÇÃO e não por palpite"*. E são honestos sobre as
tentativas falhas: *"as duas correções anteriores eram reais mas não eram o gargalo"*.

**Duas lentes anteciparam defeitos concretos, com o vínculo nomeado no registro:** LIN
previu o `|` usado como separador em dois níveis de estrutura sem escape; MEC-01 previu que
a biblioteca OFX recusaria arquivos não conformes — e quando isso aconteceu, o registro
concluiu que **o adapter estava correto e o fixture errado**. São os dois casos mais
limpos do lote de achado da Fase 2 antecipando falha da Fase 5.

**AP3 acionado explicitamente pela primeira vez.** A renovação de sessão foi oferecida com
recomendação favorável; o operador escolheu continuar; o registro declara o risco aceito —
viés de confirmação — e adota mitigação: mapa de testes derivado das **specs**, não do
código.

**E o agente limitou a força da própria evidência**, pela segunda vez no lote: sobre o
*"parece ok para mim, podemos fechar"* do operador, registrou *"para não superestimar a
evidência num post-mortem: o que houve foi VALIDAÇÃO DE ACEITAÇÃO"*.

---

## Estado do lote

6 de 12 — **metade**. Nenhuma lente candidata a remoção em nenhum projeto nem no agregado.

Cobertura: MIG **2/6** · ETI 4/6 · JOG 4/6 · as outras nove em 5/6 ou 6/6.

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — corrigir uniformemente após os doze.
2. **`duplica` intra-lente** — sem mudança de comportamento desde o C1.
3. **Patch M1 do `test-outcome.js`** — decidir se entra já ou espera o fim do lote.
4. **Tabela de módulos completa por versão** — candidato pós-lote.
5. **Gatilho de ETI** — candidata mais forte a reescrita pós-lote.
6. **Verificar na Fase 5/6 que os críticos resolvidos na Fase 3 seguem resolvidos** — §M6,
   o candidato mais acionável.
