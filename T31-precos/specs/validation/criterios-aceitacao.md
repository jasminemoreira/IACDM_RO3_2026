# Critérios de aceitação — v1.0

Escritos na **Fase 0, antes de qualquer código** (§2 do enunciado: o critério de
acerto objetivo é o que torna o retrabalho mensurável). A Fase 6 testa contra
este arquivo, não contra a implementação.

## Critérios de sucesso

| id | Critério | Medição objetiva | Fonte da verdade |
|---|---|---|---|
| **CS-1** | **Paridade com o legado** | As **26** linhas válidas de `specs/datasets/tabela-legada.csv`, reconsultadas no motor com uma quantidade dentro da faixa, devolvem o mesmo `Preco un.` da planilha, com tolerância de **R$ 0,01**. Aprovação = 26/26 | `casos-armadilha.md` §A |
| **CS-2** | **Explicabilidade total** | Nenhuma resposta do motor com trace vazio. Toda regra candidata aparece no trace com veredito (casou / não casou) **e motivo** (faixa, vigência, escopo, prioridade, especificidade). Aprovação = 0 traces vazios e 0 candidatas sem motivo | `casos-armadilha.md` §E (P-01, P-07, P-08) |
| **CS-3** | **Validador pega as armadilhas** | As **7** linhas inválidas são rejeitadas com motivo nomeado por linha, e os **6** casos de coerência são detectados **antes** da publicação. Aprovação = 13/13 | `casos-armadilha.md` §C e §D |
| **CS-4** | **Reprodutibilidade temporal** | Recalcular um pedido de data D com as regras vigentes em D devolve exatamente o preço registrado na decisão original | `casos-armadilha.md` §E (P-10, P-11) |
| **CS-5** | **Latência** | < **100 ms** por precificação unitária, com ~1.000 regras carregadas | `casos-armadilha.md` §E (P-12) |

## Critérios de aceitação do operador

O resultado é aceito quando, **executado por um humano** (não simulado pela IA):

1. **UC-2 ponta a ponta** — subir o sistema, importar `tabela-legada.csv` pela
   UI, ver o relatório com as 7 rejeições nomeadas e o resultado da paridade.
2. **UC-3 ponta a ponta** — editar um rascunho introduzindo uma faixa sobreposta,
   tentar publicar, e ser **barrado** com a colisão apontada (quais regras, qual
   intervalo).
3. **UC-4 ponta a ponta** — simular `SKU-1001, qtd 600` com a regra transversal
   de P-07 ativa e ler, na tela, **por que a regra de SKU perdeu**.
4. **UC-5 ponta a ponta** — consultar uma decisão registrada e recalcular a mesma
   data, vendo os dois valores apresentados como coisas distintas (I-7).
5. **UC-6** — precificar `SKU-1009, qtd 15` e ler "nenhuma regra casou → preço
   base" no trace.

## Não são critérios (registrado para evitar deslize de escopo)

- Qualidade estética da UI; identidade visual.
- Desempenho acima de 1k regras / fora do single-user.
- Impostos, frete, câmbio, lote, empilhamento de desconto, auth.

## Pendências que afetam a aceitação

- **Revisão humana de `casos-armadilha.md`** antes da Fase 6. Enquanto não
  ocorrer, CS-1 e CS-3 são autovalidação (AP1/AP5) e não devem ser dados como
  atendidos — condição acordada no Production Capacity Check da Fase 0.
- **Tolerância de R$ 0,01** em CS-1: proposta pela IA a partir do risco de float
  da planilha; confirmar com o operador.
