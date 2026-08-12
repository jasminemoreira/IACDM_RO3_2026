# Casos-armadilha — ground truth do validador e da paridade

> **⚠️ Este arquivo precisa da sua revisão antes da Fase 6.**
> Ele foi gerado pela IA, e a IA também escreverá o código que ele julga. Sem
> revisão humana, CS-1 (paridade) e CS-3 (validador) viram autovalidação
> (AP1/AP5) — foi o risco residual acordado no Production Capacity Check da
> Fase 0.

Fonte: `specs/datasets/tabela-legada.csv` (39 linhas de dados, formato de
planilha brasileira exportada: separador `;`, decimal com vírgula, milhar com
ponto).

## Contrato de importação assumido

O CSV legado **não tem** coluna de prioridade nem de vigência — elas não existem
na planilha. O importador atribui a toda regra importada:

- `prioridade = 0` (todas empatam entre si → o desempate por especificidade e a
  detecção de sobreposição passam a ser o que separa uma versão coerente de uma
  incoerente);
- `vigência = [data da importação, ∞)`;
- `escopo = SKU` (a planilha não tem regra transversal `*`; regras `*` só nascem
  na UI).

`Preço base` vem repetido em cada linha (planilha denormalizada) — o importador
precisa consolidá-lo por SKU.

## A. Linhas VÁLIDAS — entram como regra e valem para a paridade (CS-1)

26 linhas. Para cada uma, o teste de paridade consulta o motor com uma
quantidade **dentro** da faixa e confere contra a coluna `Preco un.` original
(tolerância R$ 0,01).

| SKU | Faixa | Preço esperado | Qtd de teste |
|---|---|---|---|
| SKU-1001 | 1–9 | 2,50 | 5 |
| SKU-1001 | 10–49 | 2,30 | 30 |
| SKU-1001 | 50–199 | 2,10 | 100 |
| SKU-1001 | 200–∞ | 1,85 | 250 |
| SKU-1002 | 1–9 | 12,90 | 3 |
| SKU-1002 | 10–49 | 11,60 | 25 |
| SKU-1002 | 50–199 | 10,30 | 120 |
| SKU-1003 | 1–4 | 24,90 | 2 |
| SKU-1003 | 5–19 | 23,40 | 10 |
| SKU-1003 | 20–99 | 21,90 | 50 |
| SKU-1003 | 100–∞ | 19,90 | 150 |
| SKU-1004 | 1–9 | 4,75 | 4 |
| SKU-1004 | 10–99 | 4,20 | 40 |
| SKU-1004 | 100–∞ | 3,60 | 120 |
| SKU-1005 | 1–4 | 38,00 | 2 |
| SKU-1005 | 5–19 | 35,00 | 12 |
| SKU-1005 | 20–∞ | 31,50 | 30 |
| SKU-1006 | 1–2 | 189,90 | 1 |
| SKU-1006 | 3–9 | 179,90 | 5 |
| SKU-1006 | 10–∞ | 165,00 | 15 |
| SKU-1007 | 1–9 | 29,90 | 6 |
| SKU-1007 | 10–49 | 27,40 | 20 |
| SKU-1007 | 50–∞ | 24,90 | 80 |
| SKU-1008 | 1–4 | 79,00 | 3 |
| SKU-1008 | 5–19 | 72,50 | 8 |
| SKU-1008 | 20–∞ | 66,90 | 25 |

**Observação:** SKU-1009 e SKU-1010 têm linhas válidas mas participam de casos
de armadilha (lacuna e formato monetário) — tratados abaixo.

## B. Linhas com FORMATO a normalizar — devem ser importadas, não rejeitadas

| # | Linha | O que tem de errado | Comportamento esperado |
|---|---|---|---|
| **N-01** | `SKU-1001;…;200;acima de 200;1,85` | `Ate` textual em vez de vazio | Interpretar como faixa **aberta à direita** `[200, ∞)`. Preço 1,85 |
| **N-02** | `SKU-1006;…;10;;R$ 165,00` | Símbolo de moeda no valor | Normalizar para `165.00` decimal |
| **N-03** | `SKU-1010;…;1;2;R$ 1.299,00` | Moeda **+ separador de milhar** | Normalizar para `1299.00`. **É o caso que quebra parser ingênuo** que troca `,`→`.` sem remover o ponto de milhar |
| **N-04** | `SKU-1010;…;3;;R$ 1.189,50` | idem | `1189.50`, faixa `[3, ∞)` |
| **N-05** | ` sku-1002 ;…;200;;9,80` | SKU com **espaços** e em **minúsculas** | Normalizar (`trim` + caixa alta) → `SKU-1002`, faixa `[200, ∞)`, preço 9,80. **Se não normalizar**, nasce um produto fantasma `sku-1002` e a sobreposição com SKU-1002 fica invisível |

### N-06 — regra determinística de separador decimal (adicionada na Fase 3, iteração 2)

Resposta a **MEC-04 🟡**: "inferir o separador pelo padrão" era ambíguo. A regra
de V(3) é determinística e, por isso, testável:

> **Havendo vírgula**, ela é o separador decimal e o ponto é milhar.
> **Não havendo vírgula**, o ponto é decimal *apenas se* seguido de exatamente
> 1 ou 2 dígitos; caso contrário é separador de milhar.

| entrada | resultado esperado | por quê |
|---|---|---|
| `1.299,00` | `1299.00` | há vírgula → ponto é milhar |
| `1.189,50` | `1189.50` | idem |
| `21,90` | `21.90` | idem |
| **`1.299`** | **`1299.00`** | **sem vírgula, 3 dígitos após o ponto → milhar** (era o caso ambíguo) |
| `21.90` | `21.90` | sem vírgula, 2 dígitos após o ponto → decimal |
| `2.5` | `2.50` | sem vírgula, 1 dígito após o ponto → decimal |
| `1.234.567` | `1234567.00` | dois pontos → ambos milhar |
| `R$ 1.299` | `1299.00` | moeda removida antes da regra |

**Limitação declarada:** um arquivo exportado em *en-US* com `1.299` querendo
dizer "um vírgula duzentos e noventa e nove" será lido como 1299. A regra
escolhe pt-BR de propósito — a planilha de origem é brasileira — e a escolha
está aqui para ser contestada, não para ser descoberta em produção.

## C. Linhas INVÁLIDAS — devem ser REJEITADAS com motivo (relatório do importador)

| # | Linha | Motivo esperado da rejeição |
|---|---|---|
| **R-01** | `SKU-1002;…;100;50;9,90;REVISAR` | **Faixa invertida**: `De (100) > Ate (50)` |
| **R-02** | `SKU-1004;…;200;;;confirmar com fornecedor` | **Preço ausente** (célula vazia) |
| **R-03** | `SKU-1004;…;500;;-1,00` | **Preço negativo** |
| **R-04** | `SKU-1005;…;50;;-10%;desconto negociado` | **Valor não-monetário em campo de preço** (percentual). É o registro humano de um desconto que a planilha não sabia expressar — motiva o efeito `DESCONTO_PCT` do modelo novo, mas **não pode ser adivinhado** pelo importador |
| **R-05** | `SKU-1008;…;a partir de 50;;62,00` | **`De` não numérico** |
| **R-07** | `SKU-1007;…;10;49;27,40` (2ª ocorrência) | **Linha duplicada exata** — importar as duas cria empate de prioridade insolúvel entre regras idênticas |

> **R-06 RECLASSIFICADO na Fase 5 — o defeito estava neste arquivo, não no código.**
> A versão original exigia rejeitar `SKU-9999` por "SKU inexistente no catálogo".
> Ao implementar `importador-csv` ficou claro que **a planilha legada não tem
> catálogo separado — o catálogo é derivado dela mesma**, então `SKU-9999`, que
> traz seu próprio preço base, se auto-cadastra. O critério escrito
> ("não aparece em nenhuma outra linha como produto ativo") não é decidível por
> máquina: `SKU-1009` e `SKU-1010` também têm poucas linhas e são legítimos. O
> que marca `SKU-9999` como descontinuado é a anotação humana em `Obs` — e `Obs`
> não é atributo de regra (V(5)/Y6).
> **R-06 passa a ser caso de REIMPORTAÇÃO** (§C-bis), cenário em que existe
> catálogo preexistente e a checagem é real. Arbitrado pelo operador.

### §C-bis — R-06 como caso de reimportação

| # | Cenário | Comportamento esperado |
|---|---|---|
| **R-06** | Publicar uma versão SEM `SKU-9999`, depois importar um CSV que contenha uma regra de escopo `SKU-9999` **sem** linha de preço base | Rejeitar com "SKU inexistente no catálogo: SKU-9999". Na primeira importação, com catálogo derivado da própria planilha, este caso **não existe** |

**Critério:** o relatório precisa nomear a **linha** e o **motivo**. "7 linhas
rejeitadas" sem discriminação não atende CS-3.

## D. Casos de COERÊNCIA — validador deve barrar a PUBLICAÇÃO (CS-3)

Estes não são erros de formato: cada linha é individualmente válida, e o defeito
só existe no **conjunto**. É a classe que a planilha jamais detecta e a razão de
o validador existir.

| # | Situação | Regras envolvidas | Veredito esperado |
|---|---|---|---|
| **V-01** | **Sobreposição de faixas** no mesmo SKU | SKU-1003 `5–19` (23,40), `20–99` (21,90) e `15–60` (22,50) | 🔴 **Bloqueia publicação.** Qtd 17 casa com duas regras de prioridade 0 e mesma especificidade → empate insolúvel. Deve apontar **quais** regras colidem e **em que intervalo** (`15–19` e `20–60`) |
| **V-02** | **Sobreposição via SKU não normalizado** | SKU-1002 `50–199` e ` sku-1002 ` `200–∞` | 🟡 Após normalização (N-05) **não** há sobreposição — as faixas são contíguas. O caso existe para verificar que a normalização acontece **antes** da checagem de coerência, e não depois |
| **V-03** | **Lacuna de cobertura** | SKU-1009 `1–9` e `20–99` | 🟡 **Aviso**, não bloqueio: qtd 10–19 e 100+ caem no preço base (I-2, comportamento definido). Mas a lacuna precisa ser **reportada** ao analista — foi o que a planilha nunca fez |
| **V-04** | **Preço base inconsistente para o mesmo SKU** | SKU-1007 aparece com base `29,90` em 3 linhas e `31,00` em 1 | 🔴 **Bloqueia a publicação** (não rejeita a linha). Arbitrado na Fase 5: a DETECÇÃO fica em `importador-csv`, onde o dado bruto está; a DECISÃO de bloquear é de `validador-coerencia`. Rejeitar a linha faria o sistema escolher em silêncio um dos dois preços base e publicar — a própria dor #2 |
| **V-05** | **Empate de prioridade insolúvel** | duas regras de mesmo escopo, mesma faixa, prioridade igual (ex.: R-07 se fosse importada) | 🔴 **Bloqueia.** É o caso que I-6 existe para tornar impossível em runtime |
| **V-06** | **Faixa aberta duplicada** | duas regras `[200, ∞)` no mesmo SKU (SKU-1001 `200–∞` + hipotética) | 🔴 **Bloqueia.** Sobreposição infinita |

## E. Casos de PRECIFICAÇÃO — comportamento em runtime (CS-2, CS-4)

Executados **depois** de uma publicação válida (com V-01, V-04 corrigidos).

| # | Entrada | Saída esperada | O que prova |
|---|---|---|---|
| **P-01** | `SKU-1003, qtd 50` | 21,90; trace com a faixa `20–99` vencedora **e** as faixas `1–4`, `5–19`, `100–∞` listadas como não-casadas por quantidade | CS-2: trace exaustivo, não só a vencedora |
| **P-02** | `SKU-1003, qtd 19` | 23,40 — **borda inferior**: a faixa `5–19` inclui 19 | Intervalo **fechado** dos dois lados |
| **P-03** | `SKU-1003, qtd 20` | 21,90 — **borda superior**: contiguidade sem lacuna nem sobreposição | Erro clássico de faixa (off-by-one) |
| **P-04** | `SKU-1003, qtd 0` | **Erro de entrada** (quantidade deve ser ≥ 1) — não é lacuna, é entrada inválida | Distinguir entrada inválida de ausência de regra |
| **P-05** | `SKU-1009, qtd 15` | **3,20** (preço base); trace diz explicitamente "nenhuma regra casou → preço base" | I-2 + UC-6: lacuna não falha |
| **P-06** | `SKU-1010, qtd 3` | 1.189,50 | N-03/N-04: milhar sobreviveu à importação |
| **P-07** | Regra `*` (qualquer produto) `500–∞` `DESCONTO_PCT 10`, prio 50, vs. SKU-1001 `200–∞` `1,85` prio 0; entrada `SKU-1001, qtd 600` | Vence a regra `*` **por prioridade** (50 > 0) → `2,50 × 0,90 = 2,25`. Trace deve dizer que a regra de SKU **perdeu por prioridade**, não que não casou | Precedência `PRIORITY`; explicação contrastiva ("por que NÃO ganhei 1,85") |
| **P-08** | Mesmas duas regras, mas ambas com prio 50; entrada `SKU-1001, qtd 600` | Vence a de **SKU** por **especificidade** → 1,85. Trace nomeia o critério de desempate usado | Desempate por especificidade |
| **P-09** | `DESCONTO_PCT 33` sobre base `4,75` | `4,75 × 0,67 = 3,1825` → **3,18** (half-up, 2 casas). Nunca `3.1825000000000004` | I-5: decimal exato, sem float binário |
| **P-10** | `SKU-1003, qtd 50, data 10/02/2026` com a regra `20–99` vigente só a partir de 01/03/2026 | 24,90 (preço base) — a regra não estava vigente. Trace: "não casou por vigência" | CS-4 / UC-5: valid time |
| **P-11** | Precificar em D, depois republicar regras alterando a faixa, e recalcular D | O **log** devolve o preço cobrado; o **recálculo** devolve o novo. Ambos apresentados como coisas distintas | I-7: log ≠ recálculo |
| **P-12** | 1.000 regras carregadas, 1 precificação | < 100 ms | CS-5 |

## Resumo quantitativo

| Classe | Qtd | Critério que sustenta |
|---|---|---|
| Linhas válidas (paridade) | 26 | CS-1 |
| Normalizações de formato | 5 | CS-1 |
| Rejeições esperadas | 7 | CS-3 |
| Casos de coerência | 6 | CS-3 |
| Casos de precificação | 12 | CS-2, CS-4, CS-5 |
