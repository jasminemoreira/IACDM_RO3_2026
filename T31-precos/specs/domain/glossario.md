# Glossário e regras de domínio — Motor de regras de preço

Fixado na Fase 0 (iteração 1). Toda ambiguidade do enunciado foi resolvida com o
operador via AskUserQuestion; este arquivo é a definição operacional.

## Vocabulário

| Termo | Definição operacional | Exemplo | Sinônimo a evitar |
|---|---|---|---|
| **Faixa** (*tier*) | Intervalo fechado de **quantidade** `[min, max]` que, quando contém a quantidade pedida, torna a regra candidata. `max` ausente = aberto à direita. | `10–49 un` | "banda", "escalonamento" (ambíguos com desconto progressivo) |
| **Regra** | Unidade de decisão: escopo + faixa + efeito + prioridade + vigência. | "SKU-1003, 50–199 un, R$ 21,90/un, prio 10, desde 01/01/2026" | "linha da tabela" |
| **Escopo** | A que a regra se aplica: um **SKU** específico ou **qualquer produto** (regra transversal). Não existe categoria. | `sku=SKU-1003` ou `sku=*` | "filtro" |
| **Efeito** | O que a regra faz com o preço: `PRECO_UNITARIO` (valor absoluto por unidade) ou `DESCONTO_PCT` (percentual sobre o preço base). | `PRECO_UNITARIO 21,90` / `DESCONTO_PCT 10` | "ação", "desconto" (genérico demais) |
| **Prioridade** | Inteiro por regra; **maior vence**. Empate resolve por especificidade. | `prio 100` | "peso", "ordem" |
| **Especificidade** | Critério de desempate: regra de SKU **vence** regra `sku=*`. | — | — |
| **Preço base** | Preço unitário cadastrado no produto. É a base do `DESCONTO_PCT` **e** o resultado quando nenhuma regra casa. | `R$ 24,90` | "preço de tabela" |
| **Vigência** | Intervalo de datas `[início, fim]` em que a regra vale (*valid time*). `fim` ausente = vigente indefinidamente. | `01/01/2026 – 31/03/2026` | "validade" (confunde com validação) |
| **Versão de regras** | Conjunto imutável de regras publicado num instante. Publicar exige aprovação do validador. | `v7, publicada 03/02/2026` | "snapshot" |
| **Rascunho** | Conjunto mutável de regras em edição pelo analista. Não precifica nada até ser publicado. | — | — |
| **Decisão** | Registro persistido de uma precificação executada: entrada, saída, trace, instante. | — | "log" (genérico) |
| **Trace** | Estrutura com **todas** as regras candidatas avaliadas, cada uma com veredito casou/não-casou **e o motivo**, mais a vencedora e o cálculo. | — | "explicação" (é o par trace+frase) |
| **Explicação** | Trace estruturado **+** frase legível derivada dele. Saída de primeira classe do motor, não log. | "Aplicada a regra de faixa 10–49 un do SKU-1003: R$ 21,90/un." | — |
| **Tabela legada** | Planilha/CSV mantida à mão que o motor substitui. Fonte da prova de paridade. | `specs/datasets/tabela-legada.csv` | — |
| **Paridade** | Propriedade verificável: cada linha válida da planilha, reconsultada no motor, devolve o mesmo preço (tolerância R$ 0,01). | — | "compatibilidade" |

## Termos vagos do enunciado, agora concretos

| Vago | Concreto |
|---|---|
| "faixas" | intervalos de **quantidade**, não de valor, cliente, região ou data |
| "histórico" | **duas** coisas: versionamento temporal das regras **e** log de auditoria das decisões |
| "explicação da decisão" | trace estruturado **+** frase humanível; deve responder *"por que NÃO ganhei o desconto X"* |
| "tabela legada" | planilha CSV mantida por humanos, com dado sujo real |
| "rápido" | **< 100 ms** por precificação unitária |
| "escalável" | **~1.000** regras ativas, **~10.000** decisões, **single-user** |

## Invariantes do domínio

1. **I-1 Determinismo.** A mesma entrada `(sku, quantidade, data)` sobre a mesma
   versão de regras produz sempre o mesmo preço e o mesmo trace. Nenhuma
   desambiguação depende de ordem de arquivo, de iteração de hash ou do relógio.
2. **I-2 Totalidade.** Toda entrada válida produz um preço. Ausência de regra
   aplicável **não é erro**: cai no preço base, e o trace declara isso.
3. **I-3 Explicação não-vazia.** Nenhuma resposta do motor sai sem trace. Um
   preço sem trace é um defeito, não um caso rápido.
4. **I-4 Imutabilidade da versão publicada.** Uma versão publicada nunca é
   alterada. Correção se faz publicando outra versão.
5. **I-5 Exatidão monetária.** Todo cálculo de dinheiro usa aritmética decimal
   exata. Ponto flutuante binário é proibido no caminho do preço.
6. **I-6 Coerência antes da vigência.** Uma versão incoerente (faixas
   sobrepostas no mesmo escopo, `min > max`, empate de prioridade insolúvel) não
   pode ser publicada. O erro é detectado na **validação**, nunca na precificação.
7. **I-7 O log é a verdade do que foi cobrado.** Se as regras de uma data
   passada forem reeditadas, o recálculo pode divergir da decisão registrada. O
   log prova o que foi cobrado; o recálculo prova o que as regras atuais dizem
   sobre aquela data. Os dois papéis são distintos e devem ser distinguíveis na UI.

## Resolução de conflito (algoritmo normativo)

Dada a entrada `(sku, quantidade, data)`:

1. **Candidatas** = regras da versão vigente em `data`, cuja vigência contém
   `data`, cujo escopo casa (`regra.sku == sku` ou `regra.sku == *`) e cuja faixa
   contém `quantidade`.
2. Se `candidatas == ∅` → **preço base** do produto; trace registra "nenhuma
   regra casou".
3. Ordena por `prioridade` **decrescente**.
4. Empate no topo → **especificidade**: `sku` explícito vence `*`.
5. Empate persistente → **não pode ocorrer em runtime** (I-6). Se ocorrer, é
   defeito do validador: o motor deve falhar ruidosamente, não escolher.
6. A vencedora aplica seu efeito: `PRECO_UNITARIO` → preço direto;
   `DESCONTO_PCT` → `preço_base × (1 − pct/100)`, arredondado a 2 casas
   (half-up).
7. O trace registra **todas** as candidatas e também as regras **descartadas**
   com o motivo (faixa não contém a quantidade, vigência não contém a data,
   escopo diferente, perdeu por prioridade, perdeu por especificidade).

## Fora de escopo (com justificativa)

| Item | Por que não |
|---|---|
| Auth, papéis, multiusuário | Single-user local; custo alto, valor zero para as duas dores |
| Impostos, frete, moeda/câmbio | Domínios inteiros à parte, ausentes do enunciado |
| Precificação em lote | Contrato é 1 chamada = 1 item |
| Empilhamento de descontos | Decorre da resolução de conflito: **uma** regra vence |
| Categoria / hierarquia de produtos | Escolhido escopo de 2 níveis (SKU / `*`); hierarquia adiciona entidade e regra de especificidade sem atacar as dores |
| Vigência futura agendada | Faria duas versões válidas coexistirem e colocaria um relógio dentro da precificação |
| Bitemporalidade | Excesso (AP2) para ~1k regras; valid-time único basta para CS-4 |
