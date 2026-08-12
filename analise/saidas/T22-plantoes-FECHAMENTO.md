# Fechamento — T22-plantoes

Terceiro projeto válido do ciclo 2. Concluído 2026-08-10, 5,3 h, 8 fases, instrumento
**versus-claude 0.14.2**.

71 achados · 11 módulos · 2 iterações do laço 2↔3 · 66 defeitos distintos · 19 decisões.

Passos 1–5 em `T22-plantoes-passos.md`. Agregado dos três em `AGREGADO-3.md`.

---

## 1. Formato: limpo

Terceiro projeto consecutivo sem incidente de formato sob a 0.14.2.

## 2. Ativação: 9 de 12, com MEC fora nas duas iterações

Ativaram, sem mudança entre as iterações: RES · UX · SUS · ETI · PRO · GOV · CTR · JOG ·
LIN. Fora: **MIG · OBS · MEC**.

| projeto | condicionais ativas |
|---|---|
| T21-certificados | 11 |
| T24-catalogo | 9 |
| T22-plantoes | 9 |

Média 9,7. A hipótese da ativação quase universal segue enfraquecendo.

**MEC ficou fora inclusive contra a V(3)**, depois de duas voltas do laço. Não refuta a
hipótese de maturação — só mostra que duas iterações não bastam por si. Somado ao T21,
onde MEC entrou já na iteração 1, a hipótese de que ela é estruturalmente tardia perde
força pelos dois lados.

**MIG em 0 de 3.** O desenho cobre — `PROJETOS.md` mira MIG em T23-canario, T26-extratos,
T29-retencao e T31-precos, nenhum deles rodado. Se chegar a zero depois do T23 e do T26,
vira problema; agora não é.

## 3. Estimativa cega sobre a V(1) — a terceira leitura do mesmo dado

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 8 | 6 |
| divergem | 2 (OBS, LIN) | 2 (OBS, MEC) |
| oscilaram | 2 (CTR, MEC) | 4 (RES, MIG, SUS, CTR) |

**Os dois estimadores ativaram OBS, que a Fase 2 recusou** — divergência na direção oposta
à do T21, onde os dois recusaram ETI e JOG que a Fase 2 ativou.

Isso **refuta** o que eu registrei no T24. Contagem de ativações por rodada:

| projeto | qwen | kimi | **Fase 2** |
|---|---|---|---|
| T21-certificados | 7 · 8 · 7 → 7,3 | 11 · 9 · 9 → 9,7 | **11** |
| T24-catalogo | 6 · 6 · 4 → 5,3 | 4 · 4 · 5 → 4,3 | **9** |
| T22-plantoes | 9 · 8 · 10 → 9,0 | 9 · 11 · 11 → 10,3 | **9** |

Quatro células abaixo, uma em cima, uma empatada. **Não há viés direcional de contagem** —
o "4 de 4 abaixo" do T24 era coincidência de dois projetos.

### O que é estável nos três

| | concordância (só decisões 3/3 ou 0/3) |
|---|---|
| **estimador × estimador** | **21/24 = 88%** |
| kimi × Fase 2 | 23/29 = 79% |
| qwen × Fase 2 | 22/30 = 73% |

Dois modelos de famílias diferentes — um local quantizado, um remoto — lendo a mesma V(1)
convergem entre si mais do que qualquer um converge com a Fase 2, nos três projetos.

Consistente com a hipótese já registrada: os externos aplicam o **gatilho**, a Fase 2 a
**pergunta central**, e a Fase 2 tem a Fase 0. Mas **88% contra 73–79% são 3 projetos e
~30 decisões**, e esta entrada já foi reescrita duas vezes. Nada direcional entra no
relatório antes dos doze. O que já é sólido é negativo: **nem fraqueza do modelo local nem
permissividade de um estimador explicam a divergência — os dois modelos fazem a mesma
coisa.**

## 4. Remarcação cega: o primeiro κ não-nulo do ciclo 2

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **0,362** | **0,432** |
| pares avaliados | 2485 | 203 |
| **ambos: duplicata** | **2** | **2** |
| só o modelo gerador | 3 | 3 |
| só o juiz cego | 4 | 2 |

Depois de duas interseções vazias (T21 e T24), os juízes coincidiram em 2 pares. Sai de
"desprezível" para **fraca a moderada** — o discriminante continua dependendo de quem
marca, mas "a marcação é irreprodutível" precisa ceder para "pouco reprodutível".

Os quatro que só o juiz cego viu, nos achados que o próprio gerador produziu:
`ARQ-02+LIN-01`, `ARQ-05+ASS-01`, `GOV-01+RES-04`, `ARQ-05+LIN-05`. **Três envolvem ARQ**,
e dois cruzam ARQ com LIN — mesmo par que apareceu duas vezes no T21
(`ARC-03+LIN-06`, `ARC-04+LIN-01`). É o único par de lentes que reincide entre projetos
na marcação cega, e vale seguir.

## 5. Ortogonalidade

Sobreposição média **11%** (T21: 9%, T24: 6%). Nenhuma lente com exclusiva zero.

No agregado dos três: **256 achados, 242 defeitos distintos, nenhuma lente removível pelo
§4.** LIN é a condicional mais limpa — **18 achados, 18 exclusivos, 0% de sobreposição**
nos três projetos.

Cobertura das condicionais no ciclo 2: MIG **0/3** · OBS 1/3 · ETI e MEC 2/3 · as outras
oito em 3/3.

## 6. Método e instrumento

Detalhe em `T22-plantoes/RETRABALHO.md`. Zero defeitos pós-entrega.

- **O S7 achou duas divergências contra o INRC-II**, ambas declaradas e corrigidas com
  parâmetro publicado da própria fonte. A mais forte: o benchmark só penaliza cobertura
  **abaixo** do ótimo, então o solver entregou 183 alocações onde 150 bastavam — *"num
  hospital, escalar gente que não era necessária"*. É a lente CIE fazendo exatamente o que
  existe para fazer.
- **Poder de detecção medido**: 5 mutações deliberadas, todas detectadas. Único dos três
  projetos a medir se a suíte é capaz de reprovar, em vez de reportar "verde".
- **4 defeitos no exploratório com 39 testes verdes.** Dois deles são a mesma classe: o
  achado da Fase 2 estava certo, a correção da Fase 3 cobriu metade do que ele implicava, e
  a suíte herdou o recorte. Terceiro projeto seguido em que o exploratório rende o que a
  suíte não rende.

**Procedência do teste manual — os três projetos divergem, e isso precisa constar de
qualquer comparação:**

| projeto | quem executou | quem julgou | gate |
|---|---|---|---|
| T21-certificados | agente | operador | perguntas de julgamento em aberto |
| T24-catalogo | **operador** | **operador** | human-AV pleno (AP5) |
| T22-plantoes | agente | operador | agente **recusou carimbar** o gate e esperou |

## Estado do lote

3 de 12. Nenhuma lente candidata a remoção em nenhum projeto nem no agregado.

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — corrigir uniformemente após os doze.
2. **`duplica` intra-lente** — a guidance tem a frase desde o C1 e o gerador segue não
   marcando. Quarto caso de instrução sem trava.
3. **Patch M1 do `test-outcome.js`** — decidir se entra já ou espera o fim do lote.
4. **ARQ × LIN** — único par que reincide na marcação cega entre projetos (2 no T21, 2 no
   T22). Verificar no T23 se persiste.
