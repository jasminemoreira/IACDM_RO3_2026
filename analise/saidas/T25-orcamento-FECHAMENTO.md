# Fechamento — T25-orcamento

Quinto projeto válido do ciclo 2. Concluído 2026-08-10, 4,1 h, 8 fases, instrumento
**versus-claude 0.14.2**.

68 achados · 10 módulos · 2 iterações do laço 2↔3 · 63 defeitos distintos · 35 decisões.

Passos 1–5 em `T25-orcamento-passos.md`. Agregado dos cinco em `AGREGADO-5.md`.

---

## 1. Formato: limpo

Quinto consecutivo sem incidente. Sem aviso de delta — a arquitetura traz a tabela
completa em cada versão.

## 2. Ativação: 11 de 12, só MIG fora

Série: **11 · 9 · 9 · 10 · 11**, média **10 de 12**.

MIG segue em 1 de 5. Restam T26, T29 e T31 no desenho para exercitá-la.

## 3. Estimativa cega sobre a V(1) — a melhor rodada do lote

| | qwen3.6:27b | kimicode |
|---|---|---|
| coincidem | 8 | **11** |
| divergem | **1** (ETI) | **1** (ETI) |
| oscilaram | 3 (JOG, LIN, MEC) | **0** |

Os dois estimadores erraram **a mesma e única lente: ETI**. O Kimi não oscilou em nenhuma
das doze — primeira vez no lote.

**ETI é agora o caso mais limpo do descompasso pergunta × gatilho.** O gatilho diz
*"decisões automatizadas sobre pessoas (scoring, classificação, moderação)"*; o sistema
decide sobre **orçamento e corte de serviço**. Os dois leitores externos aplicam o gatilho
e recusam; a Fase 2 aplica a pergunta central — *"quem pode ser prejudicado?"* — e ativa,
com razão substantiva: cortar o atendimento de uma entidade por estouro de teto **afeta
alguém**, e o painel é o mecanismo de transparência que a pergunta cobra.

Terceira ocorrência de ETI divergindo na mesma direção (T21, T25, e fora em T24 e T23 nos
dois lados). É a candidata mais forte a reescrita de gatilho pós-lote.

### Concordância acumulada, cinco projetos

| projeto | qwen | kimi | F2 | q×k | q×F2 | k×F2 |
|---|---|---|---|---|---|---|
| T21-certificados | 7,3 | 9,7 | 11 | 7/8 | 7/10 | 10/10 |
| T24-catalogo | 5,3 | 4,3 | 9 | 8/9 | 7/10 | 7/11 |
| T22-plantoes | 9,0 | 10,3 | 9 | 6/7 | 8/10 | 6/8 |
| T23-canario | 6,3 | 9,3 | 10 | 8/10 | 8/11 | 11/11 |
| T25-orcamento | 8,7 | 10,0 | 11 | 9/9 | 8/9 | 11/12 |
| **total** | | | | **88%** | **76%** | **87%** |

Os três números pararam de se mexer: 88 · 87 · 76, praticamente os mesmos do T23. **Pela
primeira vez uma rodada não desmentiu a anterior.** Mantida a regra de nada direcional
antes dos doze, mas se isso se firmar, o padrão é: os dois estimadores e o Kimi × Fase 2
empatados no topo, e o **qwen consistentemente 11 pontos abaixo de todos**.

## 4. Remarcação cega

| | todos os pares | mesmo módulo |
|---|---|---|
| κ de Cohen | **0,249** | 0,497 (não informativo) |
| ambos: duplicata | 1 | 1 |
| só o modelo gerador | 5 | 1 |
| só o juiz cego | 1 | 1 |

Série completa: **0,000 · 0,000 · 0,362 · 0,115 · 0,249**. Nenhum valor acima de 0,4 em
cinco projetos.

O guard `MIN_POSITIVOS` fez seu trabalho na janela por módulo: κ=0,497 com apenas 3 pares
marcados em toda a matriz seria lido como "moderada" e descreveria ruído. O rótulo saiu
como **não informativo**, que é o correto.

**Inversão de direção:** aqui o gerador marcou mais que o juiz cego (5 contra 1) — segundo
caso em cinco, depois do T24. A tendência de o juiz enxergar mais sobreposição vale em 3
de 5, não é regra.

## 5. Ortogonalidade — agregado dos cinco

**396 achados · 371 defeitos distintos · nenhuma lente com contribuição exclusiva zero.**

Sobreposição média **10%**. Cinco lentes seguem em **0%**: ETI, OBS, **LIN**, MEC e MIG.

LIN chega a **26 defeitos, 26 exclusivos, 0% de sobreposição** em cinco projetos. É a
condicional mais claramente distinta do conjunto, e por uma margem que só cresce.

No outro extremo, **DES × SUS** permanece o par mais próximo. SUS em 43% e DES em 38% de
sobreposição são os dois maiores do lote, e eles se sobrepõem principalmente **um com o
outro**.

## 6. Método e instrumento

Detalhe em `T25-orcamento/RETRABALHO.md`. Zero defeitos pós-entrega.

**Uma quarta forma de teste verde que não testa**, distinta das três de §M4. O clamp
`custo = min(custo_real_nano, valor_reservado)` mantém o invariante do teto **por
construção** — logo **CA-1 passaria mesmo se a premissa A8 fosse falsa**, convertendo
estouro de teto em subcontagem silenciosa. Aqui o teste é válido, o critério é real e o
código está correto; o problema é que o teste é **insensível à premissa que o critério
pressupõe**. Um invariante garantido por construção não pode falhar, e por isso não
informa.

Encontrado pelo S7, e o registro diz como: *"só apareceu ao EXECUTAR o código, não ao
lê-lo"*. A Fase 5 registra *"6 defeitos encontrados por RODAR, nenhum por ler"*.

**A escolha de ferramenta de UI teve consequência medível.** O operador escolheu Playwright
em vez de testes só-HTTP, com o racional de que *"os testes HTTP não executam uma única
linha de `painel.js`"*. As 2 falhas do smoke test eram **defeito do produto**: `USD()`
formatava com 2 casas, e num domínio onde a requisição custa fração de centavo o painel
exibia `$0.01` para o teto **e** `$0.01` para o confirmado, com saldo `$0.00`. O operador
não distinguia teto de consumo. É a lente UX com consequência funcional — e teria passado
invisível sem navegador real.

---

## Estado do lote

5 de 12. Nenhuma lente candidata a remoção em nenhum projeto nem no agregado.

Cobertura: MIG **1/5** · ETI 4/5 · as outras dez em 5/5 ou 4/5. Só MIG segue abaixo do
piso de 3 do §2.

Procedência do human-AV: T24, T23 e T25 com operador executando e julgando; T21 e T22 com
o agente executando.

## Pendências

1. **Rótulo de κ para valores nulos-por-baixo** — corrigir uniformemente após os doze.
2. **`duplica` intra-lente** — a guidance tem a frase desde o C1, o gerador segue sem
   marcar.
3. **Patch M1 do `test-outcome.js`** — decidir se entra já ou espera o fim do lote.
4. **Tabela de módulos completa por versão** — candidato pós-lote, não afeta medida.
5. **Gatilho de ETI** — candidata mais forte a reescrita pós-lote; três divergências na
   mesma direção, com justificativa textual citando o gatilho.
