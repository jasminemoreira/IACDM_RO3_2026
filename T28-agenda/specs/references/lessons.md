# Lições deste projeto (ciclo v1.0)

Lições sobre **este projeto** — domínio, stack, padrões e premissas que se
revelaram erradas. Não sobre a metodologia.

## Domínio: sincronização de calendários

**L1 — "Conflito" é uma palavra que esconde dois sistemas diferentes.**
O enunciado dizia "detecção e resolução de conflito". Em calendário isso pode
significar *reconciliação de réplicas divergentes* ou *sobreposição temporal* —
e as duas produzem arquiteturas distintas: a primeira gira em torno do ancestral
persistido, a segunda em torno do expansor de recorrência. Descobrir isso na
Fase 0 custou uma pergunta. Descobrir na Fase 5 teria custado metade da
implementação. **Qualquer projeto de sincronização deve qualificar o termo antes
de desenhar qualquer coisa.**

**L2 — Sem ancestral persistido não existe detecção de conflito, só heurística.**
É a definição formal (Balasubramaniam & Pierce, MobiCom '98): conflito é
divergência **concorrente** de ambas as réplicas contra um ancestral comum. Sem
guardar o estado da última sincronização, "A mudou" e "A e B mudaram" são
indistinguíveis, e o sistema degrada para "o mais recente vence" — perdendo
edições em silêncio. Todo produto do levantamento que funciona guarda ancestral;
os que não guardam evitam o problema virando unidirecionais.

**L3 — O ancestral precisa guardar o CONTEÚDO, não só um hash.**
Aprendido do jeito caro: a iteração 2 do loop 2↔3 redefiniu o ancestral como
`{fingerprint, versão, sequence}` para fechar o eco — e quebrou silenciosamente o
merge por campo, que precisa dos **valores** ancestrais para saber o que mesclar.
A iteração 3 pegou (ASS-10). **Otimizar o que se guarda quebra quem lê.**

**L4 — O eco da própria escrita é o bug estrutural do sync bidirecional.**
Toda escrita volta no delta seguinte como "mudança externa". Neutralizar por
ETag não basta: o provedor pode renormalizar o recurso ao gravar (truncar
`DESCRIPTION`, recalcular `DTSTAMP`), e aí o que volta difere do que foi enviado.
A única forma que fecha é **gravar no ancestral o que o provedor devolveu**, não
o que foi enviado. O `provider-beta` deste projeto trunca a descrição de
propósito, justamente para que o teste exercite isso.

**L5 — Remoção vinda de provedor com janela temporal não é deleção.**
`calendarView/delta` do estilo Graph só observa `[start, end]`. Um evento movido
para fora da janela **aparece como removido**. Propagar isso como deleção apaga
dados reais do usuário por artefato de protocolo — a falha mais destrutiva que
este sistema pode ter. A defesa que sobreviveu foi decidir presença **pela
janela declarada**, sem consultar o provedor: além de custar zero, depende de
dado local em vez da disponibilidade de um serviço externo.

**L6 — `SEQUENCE` não é comparável entre provedores.**
A RFC 5546 §2.1.5 define precedência por `SEQUENCE`, mas cada provedor o
incrementa a seu próprio critério (e muitas edições por UI não o incrementam).
Comparar valores absolutos entre dois provedores é comparar réguas diferentes. O
que funciona é o **delta relativo ao ancestral daquele lado**.

## Stack

**L7 — `icalendar` 7.2.2 gera `VTIMEZONE` a partir de `zoneinfo`.**
`Timezone.from_tzinfo(ZoneInfo(tzid), first_date, last_date)`. Sem isso, emitir
`.ics` interoperável com `TZID` não-UTC seria escrever serialização de regras de
transição à mão — Tier 3 escondido dentro de um requisito de conformidade. Foi
descoberto **verificando por execução**, não presumindo.

**L8 — Valores `DATE` (all-day) não carregam `TZID`.**
São flutuantes por definição (RFC 5545 §3.3.4). A regra "all-day ocupa
`[00:00,24:00)` no fuso de origem" exige que o fuso venha do **calendário**, por
parâmetro — é propriedade do provedor, não do evento. Um round-trip ingênuo
silenciosamente reinterpreta tudo como UTC.

**L9 — O gargalo do SQLite foi fsync, não algoritmo.**
VAL-2 (< 5 s para 1.000 eventos/lado) falhou por 8× — 41 s. Medindo:
`load_all_ancestors` = 0,08 s, parsing = 0,03 s por 200 chamadas, mas **200
transações = 7,53 s** (~37 ms por commit com `synchronous=FULL`).
`journal_mode=WAL` + `synchronous=NORMAL` resolveu, mantendo a durabilidade que
importa aqui (morte de processo). Lição prática: em código com uma transação por
item, **meça o fsync antes de otimizar o algoritmo**.

**L10 — Escrita em autocommit multiplica o custo silenciosamente.**
`isolation_level=None` faz de cada `execute` uma transação. O mapeamento de
identidade rodava assim, e o eco das próprias escritas devolvia o lote inteiro
no ciclo seguinte — 300 fsyncs avulsos. Agrupar isso numa transação foi metade
do ganho. O que **não** se agrupa é a transação por ação aplicada: ela é a
garantia de atomicidade escrita+ancestral.

## Premissas de P0/P1 que se revelaram erradas

| premissa | o que aconteceu |
|---|---|
| "`AncestorSide` só precisa de fingerprint" (V(3)) | falso — quebrou POL-4; corrigido em V(4) com snapshot por lado |
| "`write()` devolver a versão basta" (V(1)) | falso — a Regra 1 exige o recurso devolvido; contrato corrigido |
| "uma janela só" | falso — `observability_window` e `expansion_window` são coisas distintas, e conflacioná-las propaga deleção |
| "o ciclo cabe em 5 s sem tuning" (PR-8) | falso — só depois de WAL + transação agrupada |
| "o fingerprint fecha o eco" | parcialmente — fecha o de metadados; o de normalização semântica só fecha guardando o que o provedor devolveu |

## Premissas que continuam vivas

- **PR-2 — os simuladores são fiéis o bastante.** Não é falsificável neste ciclo
  por construção: só um provedor real diria. É a maior incerteza que sobra.
- **`Present(partial=True)`** — o ramo existe e nenhum simulador o exercita. Se
  um adaptador real vier, é o primeiro lugar a quebrar.

## Para um eventual v2.0

1. Adaptador real (Google ou Graph) atrás da porta `Provider` — é o único teste
   possível de PR-2, e o que descobrir vira lição do próximo ciclo.
2. Exercitar manualmente os edge cases interativos: interrupção no meio do ciclo,
   ids inexistentes, execução concorrente. Estão cobertos por teste automatizado,
   mas ninguém julgou se as mensagens fazem sentido para quem não escreveu o código.
3. Retenção do ancestral de eventos deletados dos dois lados (a poda cobre o
   journal; o ancestral cresce).
