# RETRABALHO — T28-agenda

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-11** |

Os três gates do critério de acerto objetivo, escritos **antes de codar** (ENUNCIADO §2):
G1 — UC-1 a UC-8 cobertos com ≥1 positivo e ≥1 negativo cada; G2 — suíte de **64 testes
verde em ~11 s**; G3 — operador executando UC-1, UC-2, UC-4 e UC-7 na CLI. Todos
satisfeitos.

Escopo temporal completo entregue: RRULE, EXDATE, exceções por RECURRENCE-ID, fusos IANA
com DST e all-day. Veredito da Fase 7: *"Atende — critério de acerto cumprido"*.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### VAL-2 violado por 8× — e a causa não era onde se procuraria

O ciclo de 1.000 eventos levou **41 s contra limite de 5 s**. A causa não era parsing nem
algoritmo: era **custo de `fsync` do SQLite**. A medição por estágio está no registro e é
o que torna o achado utilizável:

| operação | tempo |
|---|---|
| `load_all_ancestors` com 300 ancestrais | 0,08 s |
| `to_canonical` × 200 | 0,03 s |
| `to_ics` × 200 | 0,03 s |
| **200 transações BEGIN/COMMIT** | **7,53 s** |

Cerca de **37 ms por commit** com `synchronous=FULL` e rollback journal, e o ciclo faz uma
transação por ação aplicada — necessária, porque a marcação no journal e o ancestral
precisam ser atômicos.

É o terceiro projeto do lote em que a causa raiz de um critério numérico só aparece por
**medição por estágio**, depois de hipóteses plausíveis e erradas (T26 e T25 foram os
outros). Palpite sobre desempenho errou nos três.

### O hook do harness parou de disparar — segunda ocorrência do M1

Detalhado em `ACHADOS-METODO.md` §M1. Resumo do que este projeto acrescenta:

A saída era `64 passed in 10.95s`, que **casa os marcadores sem problema**. O agente
provou alimentando o hook à mão — ele classificou `pass` sozinho e persistiu corretamente.
Conclusão registrada: *"o hook funciona, mas não estava sendo invocado"*.

Isso **elimina a hipótese de marcadores** para esta ocorrência e isola a metade grave: o
`PostToolUse` não entrega o `tool_response`, o hook não roda, e `lastTestOutcome` fica
congelado no último veredito negativo. Duas stacks (`node:test` no T21, `pytest` aqui),
mesma paralisia.

**Nota de integridade escrita pelo próprio agente**, e é o comportamento correto:

> *"houve INTERVENÇÃO MINHA no harness que é o objeto do estudo, e isso está declarado ao
> operador em chat. Se a rodada for comparada com outras, este ponto precisa ser
> considerado."*

Segundo contorno declarado do lote em nove projetos. A frequência precisa constar do §7.

### Procedência do teste manual

O operador executou pessoalmente na CLI, ao final da Fase 5, os casos UC-1 (primeira
sincronização, 11 escritas), UC-2 (segundo ciclo com **0 escritas**), UC-4 (conflito
materializado, chave bloqueada, `conflicts show`, `resolve --take a`, `sync` aplicando) e
UC-7 (sobreposições corretas, sem falso positivo no par encostado).

Quinto dos oito projetos com human-AV pleno (T24, T23, T25, T27, T28).
