# Fechamento — T27-despesas

Sétimo projeto válido do ciclo 2. Concluído 2026-08-11, 3,6 h, 8 fases, instrumento
**versus-claude 0.14.2**.

95 achados · 12 módulos · **3 iterações** · 84 defeitos distintos · 29 decisões.

Passos 1–5 em `T27-despesas-passos.md`. Agregado dos sete em `AGREGADO-7.md`.

---

## 1. Formato: limpo, e o primeiro com três voltas do laço

Validação sem recusas. Histórico: `0→1 1→2 2→3 3→2 2→3 3→2 2→3 3→4` — **três iterações**,
contra duas em todos os anteriores. Achados distribuídos 57 · 21 · 17.

O conjunto de lentes ficou **idêntico nas três**, o que é informação sobre o mecanismo de
redeclaração: ele permite mudança, não a força.

## 2. Ativação: 8 de 12 — o menor do lote

Ativas nas três iterações: RES · UX · SUS · PRO · GOV · CTR · JOG · LIN.
Fora: **MIG · ETI · OBS · MEC**.

Série: **11 · 9 · 9 · 10 · 11 · 9 · 8**, média 9,6.

**Três voltas do laço e MEC não ativou em nenhuma.** Somado ao T21, onde entrou já na
iteração 1, e ao T26, onde quem emergiu por maturação foi MIG e não MEC, a hipótese de
"MEC é estruturalmente tardia" fica difícil de sustentar como propriedade da **lente** —
parece propriedade da **arquitetura de cada projeto**. Atualizo o achado no
`ACHADOS-TAXONOMIA.md`.

## 3. Estimativa cega sobre a V(1)

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 7 | 9 |
| divergem | 2 (SUS, MEC) | 3 (SUS, CTR, MEC) |
| oscilaram | 3 | 0 |

**Os dois estimadores ativaram MEC, que a Fase 2 recusou nas três iterações** — divergência
na direção oposta à usual. E os dois recusaram SUS, que a Fase 2 ativou.

### Concordância acumulada, sete projetos

| projeto | qwen | kimi | F2 | q×k | q×F2 | k×F2 |
|---|---|---|---|---|---|---|
| T21-certificados | 7,3 | 9,7 | 11 | 7/8 | 7/10 | 10/10 |
| T24-catalogo | 5,3 | 4,3 | 9 | 8/9 | 7/10 | 7/11 |
| T22-plantoes | 9,0 | 10,3 | 9 | 6/7 | 8/10 | 6/8 |
| T23-canario | 6,3 | 9,3 | 10 | 8/10 | 8/11 | 11/11 |
| T25-orcamento | 8,7 | 10,0 | 11 | 9/9 | 8/9 | 11/12 |
| T26-extratos | 8,7 | 8,3 | 9 | 8/8 | 9/9 | 11/11 |
| **T27-despesas** | 7,0 | 7,0 | 8 | **9/9** | 7/9 | 9/12 |
| **total** | | | | **92%** | **79%** | **87%** |

Terceira rodada seguida sem inverter o ranking. Os dois estimadores concordaram
perfeitamente entre si (9/9) pelo terceiro projeto consecutivo em que isso acontece ou
quase.

O padrão que se firma: **os estimadores convergem entre si (92%) mais do que qualquer um
converge com a Fase 2 (87% e 79%)** — que foi a leitura que escrevi no T22 e o T23
desmentiu. Ela voltou, agora com sete projetos e uma margem maior. **Ainda não entra no
relatório**, pela regra registrada; mas vale anotar que a série se estabilizou depois do
T25.

## 4. Remarcação cega — a evidência mais forte para a hipótese (b) do M7

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **−0,001** | −0,004 |
| ambos: duplicata | **0** | **0** |
| só o modelo gerador | **14** | 14 |
| só o juiz cego | 3 | 1 |

Série: **0,000 · 0,000 · 0,362 · 0,115 · 0,249 · 0,000 · −0,001**.

**O que torna este projeto decisivo:** o gerador marcou **14 pares** — quase o triplo do
padrão do lote, que era 4 a 7 — e o juiz cego não reconheceu **nenhum**. Nos anteriores o
κ baixo podia ser esparsidade: 4 ou 5 marcações em milhares de pares tornam a concordância
esperada por acaso quase nula, e o κ pouco informativo. Aqui há material de sobra, e a
interseção continua vazia.

Isso é a evidência mais forte até agora para a hipótese **(b)** registrada em
`ACHADOS-METODO.md` §M7, escrita **antes** deste resultado: o problema não é um rater ser
pior que o outro, é *"mesmo defeito"* não ser operacionalizável nessa granularidade.

Nota de rótulo, terceira ocorrência: o script imprime *"pior que acaso — discordam
sistematicamente"* para κ=−0,001, que é indistinguível de zero. Segue como pendência a
corrigir uniformemente **depois** dos doze.

## 5. Ortogonalidade — agregado dos sete

**603 achados · 563 defeitos distintos · nenhuma lente com contribuição exclusiva zero.**

Sobreposição média **9%**, estável desde os quatro projetos. Três lentes em **0%**: ETI,
OBS e MIG.

**LIN saiu do zero** — 41 defeitos, 1 compartilhado, 2%. Mantém-se a condicional mais
distinta em volume, mas deixou de ser perfeitamente disjunta.

**DES × SUS** segue o maior par, e estabilizou: 0,23 → 0,15 → 0,16. Não há tendência de
crescimento.

## 6. Método e instrumento

Detalhe em `T27-despesas/RETRABALHO.md`. Zero defeitos pós-entrega.

**§M6 reapareceu, por outro mecanismo.** No T26 a Fase 5 reintroduziu o O(n²) que a Fase 3
mandara erradicar. Aqui o refinamento de CA-3 sobre delegação foi **aprovado pelo operador
na Fase 3** (V(3)/S2) e a Fase 5 **não o implementou**: a delegação acrescentava o delegado
sem remover o delegante, e o item aparecia nas duas bandejas. Dois projetos, dois
mecanismos — desempenho num, regra de negócio no outro —, mesma lacuna estrutural: **nada
verifica que a Fase 5 preserva o que a Fase 3 decidiu.**

**Terceira adoção espontânea de teste de mutação** (T22, T23, T27). O registro da Fase 7
fala em *"verificação anti-vacuidade por mutação"*. Três de sete agentes chegaram sozinhos
à contramedida da classe catalogada em §M4 e §M5, sem ela estar na guidance.

**Um contraponto útil ao T25.** Lá o operador escolheu Playwright e o navegador real pegou
um defeito de formatação invisível a testes HTTP. Aqui **recusou Playwright** por
`fastify.inject()`, com razão específica — UI server-rendered sem JS de cliente, toda
interação é link ou POST — e declarou o que `inject` não cobre. A mesma decisão com sinais
opostos em projetos diferentes, ambas registradas com o critério. É bom material sobre
escolha de ferramenta guiada por propriedade do sistema, não por hábito.

**Um defeito de fronteira entre vocabulários.** `st.usuarioPorId.get(id) as Usuario` —
cast sem mapeamento de coluna. O SQLite traz `papel_id`, o domínio espera `papelId`, e
`solicitante.papelId` vinha `undefined`. O registro nomeia: *"o cast silenciou o erro que o
mapeamento explícito teria evitado"*. Classe LIN, e o `as` do TypeScript é precisamente o
que impede o compilador de vê-lo.

---

## Estado do lote

7 de 12. Nenhuma lente candidata a remoção em nenhum projeto nem no agregado.

Cobertura: MIG **2/7** · ETI 4/7 · OBS 4/7 · MEC 5/7 · as outras oito em 6/7 ou 7/7.

Human-AV pleno em 4 dos 7 (T24, T23, T25, T27).

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — terceira ocorrência; corrigir
   uniformemente após os doze.
2. **`duplica` intra-lente** — sem mudança de comportamento desde o C1.
3. **Patch M1 do `test-outcome.js`** — adiado para depois do lote por decisão da operadora.
4. **Tabela de módulos completa por versão** — candidato pós-lote.
5. **Gatilho de ETI** — candidata mais forte a reescrita pós-lote.
6. **Verificar que os críticos resolvidos na Fase 3 seguem resolvidos** — §M6, agora com
   **dois** projetos e dois mecanismos distintos. Passou a ser o item com melhor caso.
7. **Terceiro juiz cego (Kimi) sobre os doze** — §M7, decidido em 2026-08-11.
