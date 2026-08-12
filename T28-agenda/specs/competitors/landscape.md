# Estado da arte — sincronizadores de calendário

> Levantamento da Fase 0. Objetivo: identificar o que o mercado já resolve
> (evita reinvenção, S6 Tier 1) e quais lacunas são conhecidas.

| Produto / projeto | Modelo | Como trata conflito | Lacuna conhecida |
|---|---|---|---|
| Vdirsyncer (open source) | CalDAV ↔ CalDAV/local, ancestral persistido em status file | detecta divergência concorrente e **para**, exige `conflict_resolution` explícito (`a wins`/`b wins`/command) | não faz merge por campo; conflito de agenda (acepção B) fora de escopo |
| DAVx⁵ (Android) | CalDAV ↔ store local do Android | ETag + CTag; conflito resolvido por prevalência do servidor | idem |
| Nylas / Unipile (APIs comerciais) | camada unificada sobre Google/Graph/CalDAV | normalizam o modelo de evento; expõem webhooks | proprietário; o problema de reconciliação é embutido, não é o produto |
| CalendHub / SyncThemCalendars / Reclaim / OneCal | sync entre contas de usuário final | tipicamente **one-way por par** ou espelho de "busy" (privacidade) | evitam bidirecional real justamente porque conflito é caro |
| Unison (file synchronizer, referência teórica) | 2 réplicas + ancestral | conflito **nunca** é resolvido silenciosamente: reporta e pede decisão | não é calendário, mas é a semântica correta (REF-7) |

## Padrões recorrentes observados

1. **Ancestral persistido é universal** nos que funcionam bem — quem não guarda
   estado da última sync degrada para LWW por timestamp e perde edições.
2. **Espelhamento "busy/free"** é a saída comum para evitar conflito: propagar só
   ocupação, sem conteúdo, torna o sync efetivamente unidirecional por par.
3. **Recorrência é a fonte nº 1 de bug** relatada (expansão, exceções, fusos) —
   nenhum produto sério implementa expansor próprio.
4. **Resolução manual existe em todos os que preservam informação** — a fila de
   conflitos é UI de primeira classe, não caso de erro.

Fontes: documentação pública dos projetos citados; ver também REF-7/REF-8 em
`specs/references/standards.md` para a fundamentação formal do item 1.
