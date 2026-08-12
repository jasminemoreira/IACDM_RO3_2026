# Glossário do domínio — T28-agenda

> Vocabulário fixado na Fase 0. Sinônimos a EVITAR estão marcados: usar o termo
> canônico em código, testes, commits e documentos.

| Termo canônico | Definição | Sinônimo a evitar | Fonte |
|---|---|---|---|
| **Evento** | Componente `VEVENT` do modelo canônico interno | "compromisso", "entrada", "item" | RFC 5545 §3.6.1 |
| **UID** | Identificador do evento, estável entre provedores | "id" (id é o identificador **local do provedor**, coisa diferente) | RFC 5546 §2.1.5 |
| **Chave de identidade** | O par `(UID, RECURRENCE-ID)` — identifica um evento simples ou uma instância destacada | "chave primária" sem qualificar | RFC 5546 §2.1.5 |
| **Série** | Evento-mestre com `RRULE`, que gera instâncias | "evento repetido" | RFC 5545 §3.8.5.3 |
| **Instância** | Ocorrência gerada pela expansão da `RRULE` numa janela | "repetição" | RFC 5545 |
| **Exceção** | Instância destacada, identificada por `RECURRENCE-ID`, com valores próprios | "override", "instância modificada" | RFC 5545 §3.8.4.4 |
| **SEQUENCE** | Inteiro de revisão; maior valor obsoleta os menores | "versão" (ambíguo com ETag) | RFC 5546 §2.1.5 |
| **ETag / versão do provedor** | Token opaco de versão do recurso **no provedor** | "hash", "revisão" | RFC 4791 |
| **Ancestral** | Snapshot do evento no momento da última sincronização bem-sucedida — a base das três vias | "cache", "cópia local", "snapshot" | REF-7 |
| **Mapa de identidade** | Tabela que liga `UID` canônico ↔ id local do provedor A ↔ id local do provedor B | "tabela de correlação" | — |
| **Delta** | Conjunto de mudanças desde um token de estado, **incluindo remoções** | "diff" (diff é entre dois estados; delta é o que o provedor devolve) | REF-3/5/6 |
| **Tombstone** | Marcação de remoção dentro de um delta (`status=cancelled`, `@removed`, `404`) | "deleção" | REF-3/5/6 |
| **Token de estado** | String **opaca** que representa o ponto de sincronização no provedor | "cursor", "timestamp de sync" (não é timestamp e não é ordenável) | RFC 6578 §3.2 |
| **Token de paginação** | String que indica "há mais páginas neste round" — **não** é token de estado | confundir com token de estado é bug de classe A-2 | REF-5/6 |
| **Ciclo de sincronização** | Uma execução completa: pull dos deltas → reconciliar → aplicar → persistir | "rodada", "job" | — |
| **Reconciliação** | Comparação A × B × ancestral produzindo o plano de ações | "merge" (merge é uma das políticas) | REF-7 |
| **Conflito de sincronização** (acepção A) | Divergência **concorrente** de A e B em relação ao mesmo ancestral | "conflito" sem qualificar | REF-7 |
| **Conflito de agenda** (acepção B) | Sobreposição temporal entre dois eventos | "conflito" sem qualificar; "choque" | — |
| **Sobreposição** | `x.start < y.end ∧ y.start < x.end` (intervalos semiabertos) | "colisão", "overlap parcial" | — |
| **Eco de sync** | A escrita do próprio sincronizador retornando no delta seguinte como mudança externa | "loop" | A-5 |
| **Política de resolução** | Regra plugável que decide um conflito (POL-1..POL-6) | "estratégia" (ok informalmente; canônico é política) | conflict-model.md |
| **Fila de conflitos** | Coleção **persistida** de conflitos aguardando decisão humana | "lista de erros" | POL-5 |
| **Full resync** | Descarte do token de estado e nova sincronização completa após invalidação | "reset" | REF-5 §410 |

## Termos vagos do enunciado — resolvidos na Fase 0

| Termo vago | Resolução registrada |
|---|---|
| "conflito" | **Ambas** as acepções em escopo (A: sincronização; B: agenda) — subsistemas distintos |
| "calendários externos" | Dois provedores **simulados heterogêneos**: um com semântica estilo Google, outro estilo Microsoft Graph |
| "sincronizador" | **Bidirecional completo**, ambos os lados autoritativos |
| "resolução" | Política configurável (POL-1..POL-4) + merge por campo padrão + fila manual (POL-5) |
