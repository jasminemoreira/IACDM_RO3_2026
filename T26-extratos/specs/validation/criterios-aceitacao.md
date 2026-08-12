# Critérios de aceitação e de sucesso — T26

Escrito na Fase 0, **antes de qualquer código** (exigência do §2 congelado: "critério de acerto
objetivo, escrito antes de codar — é o que torna o retrabalho mensurável").

Cada critério tem `id`, é **mensurável**, e nomeia como será verificado. A Fase 6 mapeia cada
`VAL-*` para pelo menos um teste que verifica o critério **exato** (não um proxy).

## Critérios de sucesso (numéricos)

| id | Critério | Limiar | Como se verifica |
|---|---|---|---|
| **VAL-1** | Dedup — falsos negativos | **0** | Sobre o ground truth rotulado: toda duplicata plantada (reimportação e cross-source) é detectada. |
| **VAL-2** | Dedup — falsos positivos | **0** | Nenhuma **colisão legítima** plantada (mesma data, mesmo valor, descrição igual, eventos distintos) é fundida. |
| **VAL-3** | Conciliação — cobertura de classificação | **100%** | Ao fim de `reconcile`, toda transação e todo lançamento carrega exatamente **um** dos 5 estados terminais. Zero itens sem estado; zero itens com dois estados. |
| **VAL-4** | Desempenho | **< 60 s** para 50.000 transações | Medição cronometrada do pipeline completo (import + dedup + reconcile) sobre a carga sintética. Teste mede o tempo real, não apenas "terminou". |
| **VAL-5** | Idempotência | estado **idêntico** | Importar o mesmo arquivo N vezes (N ≥ 3) produz o mesmo estado do banco que importar 1 vez. Verificado por digest do conteúdo das tabelas, não por contagem de linhas. |
| **VAL-6** | Casamento 1:1 | invariante nunca violado | Nenhuma transação casada com 2+ lançamentos e vice-versa, em qualquer execução. |
| **VAL-7** | Persistência da resolução humana | 100% reaplicada | Uma resolução gravada para um par é reaplicada em execução posterior e **nunca** sobrescrita por heurística. |
| **VAL-8** | Dinheiro em Decimal | 0 ocorrências de `float` em caminho monetário | Verificação estática/por teste: nenhum valor monetário transita como `float`. |

## Critérios de aceitação (o operador aceita quando…)

| id | Critério |
|---|---|
| **ACC-1** | O analista importa um OFX e um CSV com transações sobrepostas e o sistema reporta corretamente quantas linhas eram novas e quantas eram duplicata, por classe. |
| **ACC-2** | O analista roda `reconcile` contra o livro e recebe um relatório com os 5 estados, com a contagem de cada um somando o total de itens. |
| **ACC-3** | Casos ambíguos aparecem na fila de pendências com os candidatos e o score — não são decididos silenciosamente pelo sistema. |
| **ACC-4** | O analista resolve uma pendência e, ao reexecutar, aquela decisão é respeitada. |
| **ACC-5** | Reimportar o mesmo arquivo não polui a base. |
| **ACC-6** | Todo parâmetro numérico do matching tem fonte rastreável em `specs/technical/parametros-matching.md`. |

## Fronteira "teste verde" ≠ "spec atendida"

Falsas coberturas explicitamente proibidas neste projeto:

- VAL-4 diz "< 60s": um teste que só verifica "processou 50k sem erro" **não** cobre VAL-4.
- VAL-5 diz "estado idêntico": um teste que verifica "contagem de linhas não mudou" **não** cobre VAL-5 (valores podem ter sido sobrescritos).
- VAL-2 diz "0 falso-positivo": um teste sem colisões legítimas plantadas no dataset **não** cobre VAL-2 — não há como falhar.
- VAL-3 diz "exatamente um estado": um teste que verifica "todo item tem estado" **não** cobre a metade "exatamente um".

---

# Resultados medidos — Fase 7

Preenchido ao fim do ciclo. **Esperado × obtido**, com a evidência de cada linha.

| id | Limiar | Obtido | Como foi medido |
|---|---|---|---|
| VAL-1 | 0 falso negativo | **0** | 53/53 duplicatas de reimportação detectadas e 10/10 cross-source tratadas (7 fundidas, 3 escaladas), contra `ground-truth.json`. Teste `test_val1_zero_falsos_negativos` |
| VAL-2 | 0 falso positivo | **0** | 4/4 colisões legítimas plantadas preservadas. `test_val2_zero_falsos_positivos` |
| VAL-3 | 100% em um estado | **100%** | 399/399 no dataset pequeno, 61.872/61.872 na carga. As duas metades verificadas: soma bate **e** nenhum item em dois estados |
| VAL-4 | < 60 s para 50k | **4,9 s** | Pipeline completo (import + livro + conciliação) com 36.092 transações e 25.780 lançamentos, cronometrado |
| VAL-5 | estado idêntico | **idêntico** | Digest SHA-256 do conteúdo das tabelas após 3 rodadas completas de reimportação — não contagem de linhas |
| VAL-6 | 1:1 nunca violado | **0 violações** | `UNIQUE` nos dois lados de `casamento`; consulta procura a violação; `IntegrityError` no segundo casamento |
| VAL-7 | 100% reaplicada | **100%** | Após correção de um defeito real: L0 vincula na execução seguinte. `test_uc5_resolucao_reaplicada_em_execucao_posterior` |
| VAL-8 | 0 float monetário | **0** | `Dinheiro` levanta `ErroDominio` para `float` e para `str`; 0 ocorrências de `float()` no pacote |

Aceitação: **ACC-1 a ACC-6 confirmados pelo operador** — "Executei e funcionou" (execução dos casos
de uso) e "parece ok para mim" (aceitação do produto).

## O que o número não diz

VAL-1 e VAL-2 foram medidos contra um dataset **sintético**, cuja distribuição este projeto
escolheu. Zero falso positivo e zero falso negativo valem **para os casos plantados** — que incluem
deliberadamente os difíceis (colisão legítima, estorno, cross-source com descrição divergente), mas
não são extratos reais de banco. É a mesma ressalva que levou a remover a estimação de pesos m/u
por validação circular (SCI-06): medir bem contra o mundo que inventamos não é medir contra o mundo.

VAL-4 foi medido num banco **vazio**. O achado SUS-01 continua válido: o conjunto contra o qual o
dedup compara cresce com a história, e a janela de comparação de 90 dias (`Escopo.janela_dias`) é o
que impede o custo de crescer indefinidamente. Não há medição de desempenho com base acumulada de
vários meses.
