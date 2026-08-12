# Glossário de domínio — T26 (importação, deduplicação e conciliação de extratos)

Fase 0, Iteração 1. Termos fixados aqui são **vinculantes**: Fases 1-7 devem usar
exatamente estes nomes. Sinônimos listados são proibidos no código e nos artefatos.

## Vocabulário

| Termo | Definição operacional | Exemplo | Sinônimo PROIBIDO |
|---|---|---|---|
| **Fonte** (source) | Origem externa de dados de extrato, identificada por `(instituição, conta, formato)`. | `(BancoX, 0001/12345-6, OFX)` | "banco", "arquivo" |
| **Extrato** (statement) | Um lote de transações de uma fonte, cobrindo um período `[início, fim]`. | OFX de 01/07 a 31/07 | "importação" |
| **Transação** (transaction) | Um evento financeiro observado no extrato: data de postagem, valor com sinal, descrição, identificador nativo opcional. | `2026-07-14, -1250.00, "PIX ENVIADO JOAO"` | "lançamento" (reservado para o livro) |
| **Lançamento** (ledger entry) | Um registro do **livro interno** de valores esperados (contas a pagar / a receber). É o lado que a conciliação tenta casar. | `AP-4471, 2026-07-13, -1250.00, "Fornecedor João"` | "transação" |
| **Identidade nativa** | Identificador da transação atribuído pela instituição. Em OFX é o `FITID`. Chave real = `(FI, conta, FITID)` — ver `references/fontes-externas.md`. | `FITID=202607140001A` | "id" (ambíguo) |
| **Hash canônico** | Digest determinístico sobre a forma normalizada da transação `(conta, data, valor, descrição normalizada)`. Substituto de identidade quando não há identidade nativa (caso típico do CSV). | `sha256("...")` | "fingerprint" |
| **Duplicata** | Duas linhas importadas que representam **o mesmo evento financeiro real**. Ver as duas classes abaixo. | — | "repetido" |
| **Duplicata de reimportação** | Mesma fonte, períodos sobrepostos: a mesma transação chega duas vezes. Detectável por identidade nativa ou hash canônico. Classe **determinística**. | Importar julho e depois 15/07–15/08 | — |
| **Duplicata cross-source** | Mesmo evento chegando por **fontes distintas** (ex.: OFX do banco + CSV de outro export). Identidades nativas divergem por construção. Classe **probabilística**. | FITID do banco vs. linha CSV do cartão | — |
| **Colisão legítima** | Duas transações **realmente distintas** com mesma data, valor e descrição (dois cafés de R$ 12,00 no mesmo dia). **NÃO** é duplicata. É a fonte de falso-positivo do dedup. | — | — |
| **Conciliação** (reconciliation) | Processo de casar cada transação do extrato com no máximo um lançamento do livro, e vice-versa. | — | "matching" (genérico) |
| **Estado de conciliação** | Rótulo terminal de cada transação/lançamento. Conjunto fechado: `casado`, `casado-com-divergência`, `órfão-no-extrato`, `órfão-no-livro`, `pendente-de-revisão`. | — | — |
| **Divergência** | Par casado cujos atributos não coincidem exatamente (valor difere dentro da tolerância, ou data difere dentro da janela). | Extrato R$ 1250,00 em 14/07 × livro R$ 1250,00 em 13/07 | — |
| **Pendência** | Item na fila de revisão humana: o sistema encontrou evidência insuficiente ou ambígua e **se recusa a decidir sozinho**. | 1 transação × 3 lançamentos candidatos | — |
| **Resolução** | Decisão humana sobre uma pendência (`aceitar`, `rejeitar`, `casar-manual`). Persistida e **reaplicada** em execuções futuras sobre o mesmo par. | — | — |
| **Idempotência** | Reimportar o mesmo arquivo N vezes produz estado final idêntico ao de 1 importação. | — | — |
| **Diferença de tempo** (timing difference) | Transação existe no livro mas ainda não postou no banco (ou o inverso) — órfão **esperado**, não erro. Responde por 40-60% dos não-casados em conciliação real. | Cheque emitido não compensado | — |

## Termos vagos do enunciado → forma concreta

| Vago (ENUNCIADO.md) | Concretização (decidida na Fase 0) |
|---|---|
| "múltiplas fontes externas" | Exatamente 2 formatos: OFX/OFC e CSV com layout por banco. CAMT.053 e JSON de agregadora: fora de escopo. |
| "deduplicação" | Duplicata de reimportação (determinística) + duplicata cross-source (probabilística). Colisão legítima deve ser preservada. |
| "conciliação" | Extrato × livro interno de lançamentos esperados, com 5 estados terminais fechados. |
| "rápido" | 50.000 transações em < 60s. |
| "correto" | Dedup: 0 falso-negativo e 0 falso-positivo no dataset de referência. Conciliação: 100% classificadas em exatamente um estado. |

## Invariantes de domínio

1. **I1 — Dinheiro nunca é float.** Todo valor monetário é `Decimal` com escala fixa. Comparação de valores é exata; tolerância, quando aplicada, é explícita e em `Decimal`.
2. **I2 — Sinal é semântico.** Débito é negativo, crédito é positivo, na transação e no lançamento. Cada parser CSV declara sua convenção de sinal — nunca inferida.
3. **I3 — Todo item tem exatamente um estado terminal.** Nenhuma transação e nenhum lançamento pode ficar sem classificação ao fim de um `reconcile`.
4. **I4 — Casamento é 1:1.** Uma transação casa com no máximo um lançamento e vice-versa. Casos 1:N e N:1 (pagamento parcial, lote) **não são casados automaticamente** — viram pendência.
5. **I5 — Deduplicação nunca funde silenciosamente sob evidência fraca.** Sem identidade nativa coincidente, a fusão exige limiar alto; abaixo dele o par vai para a fila de pendências. Preserva colisões legítimas (I6).
6. **I6 — Colisão legítima é preservada.** Duas transações realmente distintas jamais podem ser fundidas por coincidirem em `(data, valor, descrição)`.
7. **I7 — Resolução humana é soberana e persistente.** Uma decisão humana sobre um par nunca é sobrescrita por heurística em execução posterior.
8. **I8 — Importação é idempotente.** Reprocessar a mesma entrada não altera o estado.

## Campo teórico

- **Record linkage / entity resolution** (Fellegi & Sunter, 1969) — base formal da deduplicação sem identificador comum. Ver `references/fontes-externas.md`.
- **Conciliação bancária contábil** — prática estabelecida; taxonomia de exceções e o conceito de *outstanding item*.
- **Normalização de dados / parsing tolerante** — heterogeneidade de layout CSV, formatos de data, separador decimal pt-BR.
