# Ground truth dos datasets sintéticos

Fixtures geradas por `generate.py` (determinísticas: âncora fixa em
`2026-11-02T12:00Z`, nenhum "agora", nenhum aleatório). Este arquivo é a **saída
esperada** — a Fase 6 testa contra ele, não contra o que o código produz.

## Cenário `basic` — UC-1, UC-2, UC-3, UC-4

| arquivo | UID | conteúdo |
|---|---|---|
| `so-em-a.ics` | `so-em-a@t28` | 2026-11-03 12:00Z, 60 min, "Revisao de arquitetura" |
| `so-em-b.ics` | `so-em-b@t28` | 2026-11-04 12:00Z, 30 min, "1:1 com a lider" |
| `compartilhado.ics` | `compartilhado@t28` | 2026-11-05 12:00Z, 90 min, location "Sala 4" |

Esperado com `so-em-a` + `compartilhado` no lado A e `so-em-b` no lado B:
- **ciclo 1:** 3 escritas (2 de A→B, 1 de B→A); 0 conflitos; ambos ficam com 3 eventos
- **ciclo 2 sem mudança externa:** **0 escritas**, 3 no-ops — é a evidência de VAL-4
- editar `location` em A e `summary` em B no `compartilhado`: POL-4 mescla, **0 conflitos**
- editar `summary` nos dois lados com valores diferentes: **1 conflito** `SAME_FIELD`, nada aplicado

## Cenário `recurring` — UC-8

| arquivo | conteúdo |
|---|---|
| `serie.ics` | `serie@t28`, semanal `COUNT=8` a partir de 2026-11-06 12:00Z, com `EXDATE` em 2026-11-20 |
| `serie-excecao.ics` | mesmo UID, `RECURRENCE-ID` 2026-11-13 12:00Z, deslocado +2 h |

Esperado: **duas chaves distintas** — `serie@t28` e
`serie@t28#2026-11-13T12:00:00+00:00`. Editar a exceção não altera a série-mestre.
Expansão em 2026-11-01..2026-12-31: **7 ocorrências** (8 da série − 1 `EXDATE`),
sendo a de 13/11 deslocada para 14:00Z.

## Cenário `timezone` — VAL-7, VAL-8, regra R-A2

| arquivo | conteúdo |
|---|---|
| `feriado.ics` | all-day (`VALUE=DATE`) em 2026-11-08 |
| `reuniao-sp.ics` | 2026-11-08 14:00Z, `TZID=America/Sao_Paulo` |

Esperado: com `calendar_tz = UTC`, o all-day ocupa `[2026-11-08 00:00Z,
2026-11-09 00:00Z)` e **bloqueia** ⇒ **1 sobreposição de 60 min** com a reunião.
Com `calendar_tz = America/Sao_Paulo`, a ocupação desloca 3 h e a interseção
muda — é exatamente o caso que expõe erro de fuso.

## Cenário `overlapping` — UC-7 e seu negativo

| par | horário (UTC) | esperado |
|---|---|---|
| `ov1` × `ov2` | 14:00-15:00 e 14:30-15:30 em 2026-11-10 | **sobrepõem**, 30 min |
| `ed1` × `ed2` | 09:00-10:00 e 10:00-11:00 em 2026-11-10 | **NÃO sobrepõem** — encostados, predicado semiaberto |

## Cenário `scale` — VAL-1, VAL-2

Gerado sob demanda: `python specs/datasets/generate.py <destino> 1000`.
1.000 eventos por lado distribuídos em 300 dias. Esperado: ciclo completo em
**< 5 s** (VAL-2), medido por cronômetro, não por proxy.
