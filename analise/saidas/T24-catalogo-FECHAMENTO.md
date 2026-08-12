# Fechamento — T24-catalogo

Segundo projeto válido do ciclo 2, e o **primeiro fora do slot T21**. Concluído
2026-08-09, 1,1 h, 8 fases, instrumento **versus-claude 0.14.2**.

75 achados · 9 módulos · 2 iterações do laço 2↔3 · 70 defeitos distintos · 24 decisões.

Passos 1–5 completos em `T24-catalogo-passos.md`. Aqui só o que precisa de leitura.

---

## 1. Formato: limpo

Validação sem recusas. Lentes canônicas, todas dentro do conjunto declarado para a
iteração de cada achado, `stateVersion=1` com `activatedLenses` em duas entradas.

Segundo projeto consecutivo em que a 0.14.2 passa sem incidente de formato.

## 2. Ativação: 9 de 12 — a hipótese da ativação quase universal enfraquece

Ativaram nas duas iterações, sem mudança: RES · UX · SUS · PRO · GOV · CTR · JOG · LIN ·
MEC. Fora, com justificativa: **MIG · ETI · OBS**.

| projeto | slot | condicionais ativas |
|---|---|---|
| T21-cofre (descartado) | T21 | 10 |
| T21-certificados | T21 | 11 |
| **T24-catalogo** | **T24** | **9** |

O T24 é o primeiro teste fora do slot T21, e vem abaixo. A hipótese registrada em
`ACHADOS-TAXONOMIA.md` — de que gatilhos redigidos como propriedade do sistema tornam a
distinção condicional/universal vazia — **fica mais fraca**, mas nem de perto refutada: 9
de 12 ainda é alto, e o piso de 3 projetos do §2 continua trivialmente satisfeito.

As justificativas das três não-ativações são específicas e verificáveis, o que é bom
sinal: MIG por ser greenfield sem legado nem rollback; ETI porque *"apenas reproduz uma
atribuição de propriedade declarada por humano"*; OBS porque *"a CLI é processo efêmero
invocado sob demanda, sem estado entre execuções"*. Nenhuma é genérica.

**ETI fora pela segunda vez consecutiva**, e desta vez pela Fase 2 — no T21 a Fase 2 a
ativou e os dois estimadores externos não. Vale seguir.

## 3. Estimativa cega sobre a V(1) — a explicação do T21 não sobrevive

Dois estimadores, 3 rodadas cada, sobre a V(1).

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 7 | 7 |
| divergem | 3 (SUS, CTR, JOG) | **4** (RES, SUS, PRO, CTR) |
| oscilaram | 2 (RES, LIN) | 1 (JOG) |

**No T21 o Kimi acertou 10 e o Qwen 7, e eu atribuí a diferença a permissividade do
Kimi. O T24 refuta isso.**

| projeto | qwen — ativas/rodada | kimi — ativas/rodada | Fase 2 |
|---|---|---|---|
| T21-certificados | 7 · 8 · 7 | 11 · 9 · 9 | **11** |
| T24-catalogo | 6 · 6 · 4 | 4 · 4 · 5 | **9** |

O Kimi caiu de ~10 ativações para ~4,3. Ele **não** é constitucionalmente permissivo — ele
segue o projeto, e no T24 segue para baixo demais. A vantagem dele no T21 foi
circunstancial.

### O que sobra, e é mais forte do que o que caiu

Nas quatro células, **todo estimador externo ativa menos que a Fase 2**:

| | média de ativações |
|---|---|
| qwen3.6:27b | 7,3 (T21) · 5,3 (T24) |
| kimicode | 9,7 (T21) · 4,3 (T24) |
| **Fase 2** | **11 · 9** |

Quatro de quatro abaixo, com dois modelos de famílias diferentes e dois projetos de
domínios diferentes. **A Fase 2 ativa sistematicamente mais lentes que qualquer leitor
externo olhando a mesma arquitetura V(1).**

Isso é direcional e reprodutível, e sustenta a explicação já registrada: a Fase 2 aplica a
**pergunta central**, os estimadores aplicam o **gatilho**; e a Fase 2 passou pela Fase 0,
que os estimadores não veem. O que **não** sustenta é a leitura de que um estimador é
melhor que o outro — eles erram em direções diferentes e trocam de posição entre projetos.

Correção: a nota de taxa-base que registrei no T21 atribuía permissividade ao Kimi como
traço. Não é traço. O efeito de taxa-base sobre a concordância bruta continua real — com
11 de 12 ativas, concordar é barato —, mas o mecanismo é o **undershoot sistemático dos
externos**, não a generosidade de um deles.

## 4. Remarcação cega: o juiz cego não agrupou nada

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **0,000** | **0,000** |
| pares avaliados | 2775 | 296 |
| ambos: duplicata | 0 | 0 |
| só o modelo gerador | 7 | 5 |
| **só o juiz cego** | **0** | **0** |

O gerador marcou 3 grupos (5 marcações `duplica`, 70 clusters); o juiz cego devolveu
`{"grupos": []}` — nenhum agrupamento em 75 achados.

Segundo projeto seguido com **interseção vazia** entre as duas marcações. No T21 os dois
marcaram e não coincidiram; aqui um marcou e o outro não marcou nada. A conclusão é a
mesma e agora com duas observações: **a marcação de duplicatas não é reprodutível entre
juízes.**

Nota sobre o rótulo, pela segunda vez: o script imprime *"desprezível"* para κ=0,000, o que
aqui está correto. No T21 o valor caiu marginalmente abaixo de zero (−0,001) e disparou o
rótulo mais duro. Segue como pendência a corrigir uniformemente **depois** dos doze.

Como o juiz não agrupou nada, a análise de sensibilidade do Passo 2 que fiz no T21 não tem
contrapartida aqui: sob a marcação do juiz, todos os 75 achados seriam defeitos distintos e
**toda** contribuição exclusiva subiria. A leitura conservadora continua sendo a do
gerador, que é a que os Passos usam.

## 5. Ortogonalidade

Sobreposição média **6%** (T21: 9%). Nenhuma lente com contribuição exclusiva zero.
Máximos: REG e SUS com 50% (2 defeitos cada, 1 compartilhado) — números pequenos demais
para significarem muito isoladamente.

ARQ e IMP lideram com 8 achados e **8 exclusivos cada**, 0% de sobreposição.

O §4 exige 100% de sobreposição para declarar uma lente removível. Nenhuma chega perto,
pelo segundo projeto.

## 6. Método e instrumento

Detalhe em `T24-catalogo/RETRABALHO.md`. Zero defeitos pós-entrega, e **nenhuma pendência
apontada para um v2** — diferente do T21, que nomeou duas dívidas de granularidade.

Dois pontos que vão para o corpus:

- **O S7 pegou o defeito do `--json`** que a suíte não pegaria: a flag só funcionava antes
  do subcomando, e *"a ordem que o usuário escreve naturalmente é a que quebra"*. A
  micro-checagem pergunta *"onde diverge de specs/?"* em vez de *"está bom?"*, e a
  diferença de formulação produziu o achado. Instrumento funcionando.
- **Teste errado, código certo — verificado antes de concluir.** Mesma classe do M2 do
  T21, conduta diferente: lá o primeiro diagnóstico tratou o sintoma e o teste falhou de
  novo; aqui o registro traz a verificação antes da conclusão. Dois casos não fazem
  tendência; anotado para comparar.

**Diferença de procedência que precisa constar de qualquer comparação T21 × T24:** aqui o
teste manual foi **executado e julgado pelo operador** (*"Testei e está bom"*), com as 5
perguntas de julgamento humano respondidas por pessoa. No T21 o agente executou a pedido, e
as perguntas de julgamento ficaram declaradamente em aberto. **O T24 tem human-AV no
sentido do AP5; o T21 não tinha.**

---

## Estado do lote

2 de 12 concluídos. Nenhuma lente candidata a remoção. Duas condicionais ainda sem nenhuma
ativação no ciclo 2: **MIG** (0 de 2) e **OBS** (1 de 2, só no T21). ETI em 1 de 2.

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — corrigir uniformemente após os doze.
2. **`duplica` intra-lente** — no T21 três dos seis agrupamentos do juiz cego eram
   intra-lente e o gerador não marcou nenhum; aqui o juiz não marcou nada. A guidance tem a
   frase desde o C1 e não mudou o comportamento.
3. **Patch M1 do `test-outcome.js`** — decidir se entra já ou espera o fim do lote.
