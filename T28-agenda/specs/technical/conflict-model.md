# Modelo de conflito — as duas acepções e os algoritmos de cada uma

> ⚠️ O enunciado diz "detecção e resolução de conflito" sem qualificar. Em
> calendários o termo é **ambíguo** e as duas leituras produzem arquiteturas
> diferentes. Este documento separa as duas; a Fase 0 decide qual (ou ambas) está
> em escopo.

---

## Acepção A — Conflito de sincronização (reconciliação de réplicas)

**Definição (REF-7):** dadas duas réplicas com um ancestral comum (o estado da
última sincronização bem-sucedida), há conflito quando **ambas** divergiram do
ancestral para a mesma entidade desde a última reconciliação. Se apenas uma
divergiu, é propagação simples, não conflito.

Corolário estrutural: **sem estado ancestral persistido não existe detecção de
conflito** — só heurística de timestamp. O ancestral (o "shadow"/last-synced
snapshot por par de eventos) é uma entidade de primeira classe do sistema.

### Matriz de decisão da reconciliação

Para cada entidade lógica, comparando `A` (lado A), `B` (lado B) e `S` (ancestral):

| A vs S | B vs S | Situação | Ação |
|---|---|---|---|
| igual | igual | nada mudou | no-op |
| mudou | igual | mudança unilateral em A | propagar A → B |
| igual | mudou | mudança unilateral em B | propagar B → A |
| mudou | mudou, **mesmo valor** | convergência acidental | no-op, atualizar S |
| mudou | mudou, valores diferentes | **CONFLITO** | aplicar política (abaixo) |
| deletado | mudou | delete-vs-update | **CONFLITO** — classe própria |
| mudou | deletado | update-vs-delete | **CONFLITO** — classe própria |
| deletado | deletado | ambos removeram | no-op, remover S |
| não existe | criado | criação unilateral | criar em A, mapear ids |
| criado | criado (mesmo UID) | criação concorrente | conflito de identidade ou eco de sync (A-5) |

Granularidade: a comparação pode ser **por entidade** (o evento inteiro é uma
unidade) ou **por campo** (merge de 3 vias — A mudou `location`, B mudou
`summary` ⇒ merge sem conflito). Merge por campo preserva mais informação (REF-7:
não perder informação sem consentimento) mas exige um mapa de campos canônico e
regras para campos estruturados (attendees, RRULE).

### Políticas de resolução (catálogo)

| id | Política | Regra | Perde informação? | Fonte |
|----|----------|-------|-------------------|-------|
| POL-1 | Normativa iCalendar | maior `SEQUENCE`; empate ⇒ `DTSTAMP` mais recente | sim (lado perdedor descartado) | REF-2 §2.1.5 |
| POL-2 | Last-Write-Wins (LWW) | timestamp de modificação mais recente vence | sim | prática corrente; **contraria REF-2** se ignorar SEQUENCE |
| POL-3 | Prioridade de fonte | um lado é sempre autoritativo (master/replica) | sim, deterministicamente | prática corrente |
| POL-4 | Merge 3-vias por campo | campos disjuntos mesclam; só campo em colisão real vira conflito | não, quando disjunto | REF-7, REF-8 |
| POL-5 | Fila de revisão manual | conflito é materializado e apresentado ao operador; nada é aplicado até decisão | não | prática corrente |
| POL-6 | Duplicação preservadora | mantém as duas versões (uma renomeada/anexada) | não | Unison/Dropbox-style |

Nota REF-8 (Syncpal): resolver conflitos **iterativamente, um por vez**,
reavaliando o estado após cada resolução — resolver em lote pode fazer a
resolução de um conflito invalidar a de outro.

### Prevenção de eco/loop (obrigatório em sync bidirecional)

Toda escrita feita **pelo sincronizador** volta no próximo delta do provedor
como mudança externa (A-5). Mecanismos conhecidos:
- gravar o novo `etag`/`SEQUENCE`/versão resultante da própria escrita no
  ancestral **na mesma transação** ⇒ o eco compara igual a S e vira no-op;
- marcar origem (campo de extensão / propriedade privada) — nem todo provedor
  preserva propriedades desconhecidas;
- contador de versão de sync incrementado pelo sincronizador.
O primeiro é o único que não depende de cooperação do provedor.

---

## Acepção B — Conflito de agenda (sobreposição temporal / double-booking)

**Definição:** dois eventos cujos intervalos `[start, end)` se **interceptam** no
mesmo recurso (a pessoa/sala), possivelmente vindos de calendários distintos.

Predicado canônico de sobreposição (semiaberto, evita falso positivo em eventos
encostados):

```
overlap(x, y)  ⟺  x.start < y.end  ∧  y.start < x.end
```

Requisitos de correção:
- comparar em **instante absoluto (UTC)**; converter respeitando `VTIMEZONE`/`TZID` (REF-1);
- eventos **all-day** são `DATE`, não `DATE-TIME`: precisam de regra explícita
  (ex.: all-day ocupa `[00:00, 24:00)` no fuso do calendário, ou é tratado como
  não-bloqueante);
- séries recorrentes precisam ser **expandidas** na janela analisada antes de
  testar sobreposição (REF-9), respeitando `EXDATE` e exceções `RECURRENCE-ID`;
- eventos com `STATUS:CANCELLED` e (se disponível) `TRANSP:TRANSPARENT` /
  `showAs = free` não devem contar como ocupação;
- detecção eficiente: ordenar por `start` e varrer (sweep line) — O(n log n) —
  em vez do produto cartesiano O(n²); ou intervalo/segment tree se a janela for
  reconsultada muitas vezes.

Resoluções possíveis: sinalizar/reportar, mover um dos eventos, marcar
prioridade por calendário, ou rejeitar a propagação que criaria a sobreposição.

---

## Regras fixadas na Fase 0 (decididas pelo operador — vinculantes na Fase 5)

### R-A1 — Granularidade do merge por campo
Campos **escalares** (`summary`, `location`, `description`, `dtstart`, `dtend`,
`status`, transparência) participam do merge 3-vias: mudanças concorrentes em
campos **disjuntos** mesclam sem conflito.
Campos **estruturados** (`attendees`, `RRULE`/`EXDATE`, qualquer coleção) **não
mesclam** — qualquer mudança concorrente neles escala direto para a fila.
Motivo: mesclar duas `RRULE` divergentes não tem semântica definida pela norma, e
`attendees` pertence ao iTIP, fora de escopo. **Nunca inventar semântica de
mescla que o RFC não define.**

### R-A2 — Ocupação de evento all-day (acepção B)
Um evento all-day (valor `DATE`, RFC 5545) ocupa `[00:00, 24:00)` no **fuso do
calendário de origem**, convertido para instante absoluto UTC antes da
comparação, e **bloqueia** (sobrepõe eventos com horário no mesmo dia).
Consequência: all-day em `America/Sao_Paulo` vs. evento com horário em UTC
sobrepõem ou não conforme a conversão — é o caso de teste que expõe erro de fuso
(VAL-7/VAL-8).

### R-A3 — Saída-de-janela **não** é deleção (armadilha A-4)
A falha mais destrutiva possível deste sistema é apagar eventos reais por
artefato de protocolo. O provedor estilo-Graph só observa `[startDateTime,
endDateTime]`; um evento **movido para fora** da janela aparece no delta como
remoção.
Regra: **antes de propagar qualquer remoção originada do provedor com janela**,
verificar se a entidade ainda existe fora da janela observável.
- ainda existe → **saída de escopo observável**: suspende o mapeamento de
  identidade e o ancestral daquele par, **sem apagar nada no outro lado**, e
  registra o fato de forma inspecionável;
- confirmadamente inexistente → deleção real, propaga.

---

## Por que a distinção importa para a arquitetura

| | Acepção A (sync) | Acepção B (agenda) |
|---|---|---|
| Entidade central | ancestral (last-synced state) por par de eventos | intervalo temporal expandido |
| Módulo que domina | reconciliador + mapa de identidade | expansor de recorrência + detector de sobreposição |
| Algoritmo | matriz 3-vias + política | sweep line sobre intervalos |
| Falha típica | perda silenciosa de edição, loop de eco | falso positivo por fuso/all-day |

Um sincronizador com "detecção e resolução de conflito" **precisa** de A para ser
correto. B é uma capacidade adicional, e é o que um usuário final normalmente
chama de "conflito de agenda". As duas podem coexistir: A garante que a réplica
converge; B analisa o resultado consolidado.
