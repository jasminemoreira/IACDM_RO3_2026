# Domínio — Glossário e invariantes (T27, Fase 0, iteração 1)

Fonte primária: decisões do operador nas perguntas N1–N5 da Fase 0 (ver
`get_decisions(phase=0)`). Fonte secundária: `specs/references/dominio-aprovacao-despesas.md`.

## Glossário

| Termo | Definição operacional neste sistema | Sinônimo a evitar |
|---|---|---|
| **Alçada** (*approval limit*) | Limite monetário de decisão preso ao **papel**, não à pessoa. A pessoa exerce a alçada do papel que ocupa. | "permissão", "poder de compra" |
| **Papel** (*role*) | Posição hierárquica com nível ordenado e limite de alçada. Ex.: Coordenador < Gerente < Diretor. | "cargo" (usar papel) |
| **Matriz DoA** (*Delegation of Authority matrix*) | O conjunto papel → limite. Neste ciclo é **seed fixo**, não editável em runtime. | "tabela de permissões" |
| **Cadeia de aprovação** | Sequência de papéis, do menor nível para cima, que uma despesa percorre até que um papel cuja alçada cobre o valor dê o aval final. | "fluxo", "esteira" |
| **Escalonamento** | Passagem da despesa ao próximo nível da cadeia após aprovação do nível corrente. Aqui é **por valor**, nunca por tempo (SLA está fora de escopo). | "encaminhamento" |
| **Delegação** | Transferência **temporária** do poder de decisão de A (delegante) para B (delegado), com vigência início/fim. B decide **em nome de A**, exercendo **a alçada de A**. | "substituição", "procuração" |
| **Delegante / Delegado** | Quem cede a autoridade / quem a exerce. | "titular / suplente" |
| **Vigência** | Intervalo [início, fim] em que a delegação está ativa. | "prazo" |
| **Bandeja** (*inbox*, fila) | Lista de despesas pendentes de decisão de um aprovador: as próprias **+** as recebidas por delegação ativa. Ordenada. | "fila global", "pool" |
| **Ator efetivo / em nome de** | Par registrado em toda decisão: quem clicou e por quem. Sem delegação, os dois são o mesmo. | — |
| **Trilha** (*audit trail*) | Sequência imutável de transições de estado de uma despesa. | "log" |
| **SoD** (*Segregation of Duties*) | Conjunto de invariantes que impedem que uma só pessoa complete sozinha um ciclo de autorização. | "controle de acesso" |

## Termos vagos do enunciado, agora concretos

| Vago | Concreto |
|---|---|
| "alçadas por valor" | limite por **papel**; despesa escala em **cadeia sequencial** até o papel cujo limite cobre o valor |
| "delegação temporária" | vigência início/fim; delegado exerce a alçada **do delegante**; autoridade avaliada **no instante do ato** |
| "fila" | **bandeja por aprovador**, ordenada, própria + delegada. Não é pool global |

## Invariantes (INV) — o que o sistema nunca pode violar

| id | Invariante | Origem |
|---|---|---|
| INV-1 | Um papel aprova quando `valor ≤ limite_do_papel` (fronteira **inclusiva**) | N3(a) |
| INV-2 | Ninguém aprova a própria despesa — inclusive quando ocuparia o nível por delegação recebida | N3(b)1 — SoD clássico |
| INV-3 | Delegação **não é transitiva**: B não pode redelegar autoridade recebida de A (elimina ciclos A→B→C) | N3(b)2 |
| INV-4 | Um mesmo ator não decide duas vezes na mesma cadeia da mesma despesa | N3(b)3 — princípio dos quatro olhos |
| INV-5 | Um mesmo delegante não pode ter duas delegações ativas com vigências sobrepostas | N3(b)4 |
| INV-6 | Autoridade é avaliada **no instante do ato**: decisão válida quando tomada permanece válida para sempre, mesmo após expiração ou revogação da delegação | N2(When) |
| INV-7 | Toda decisão registra ator efetivo, em nome de, instante e **o limite vigente exercido** | N2(How)1 |
| INV-8 | A trilha é **append-only**: transição registrada não é editada nem apagada | N2(How)2 |
| INV-9 | Rejeição exige motivo textual não vazio | N2(How)4 |
| INV-10 | Despesa cujo valor excede o **maior** limite da hierarquia é recusada na criação — nunca existe pendência sem aprovador possível | N4(b) |
| INV-11 | Rejeição em qualquer nível é **terminal**: encerra a despesa, não retorna à fila | N4(a) |
| INV-12 | Dinheiro é **inteiro de centavos** (BRL). Nenhuma comparação de alçada usa ponto flutuante | N4/stack |

## Regras de tempo

- O tempo é dependência explícita (porta `Clock` injetável) com mecanismo de avanço para
  teste e demonstração. Nenhum módulo chama o relógio do sistema diretamente.
- Expiração da vigência **não é evento agendado**: é consequência de avaliar a delegação
  contra o relógio no momento em que a bandeja é montada ou a decisão é tentada. Isso é o
  que torna INV-6 implementável sem agendador (notificações e SLA estão fora de escopo).

## Estados da despesa (derivados das decisões, a consolidar na Fase 1)

`RASCUNHO?` → **PENDENTE(nível k)** → (aprovação no nível k) → PENDENTE(k+1) … →
**APROVADA** | (rejeição em qualquer k) → **REJEITADA** (terminal, com motivo).

Recusa na criação (INV-10) não gera despesa — é erro de validação, não estado.

---

## Reconciliação com as Fases 1-3 (estado final: V(4))

As invariantes acima (INV-1..INV-12) foram escritas na Fase 0. As Fases 1-3 acrescentaram,
revogaram e alteraram algumas. **Este é o conjunto vigente** — a Fase 5 deve implementar
esta lista, não a de cima isoladamente.

| id | invariante | origem | módulo guardião |
|---|---|---|---|
| INV-1..INV-12 | conforme a tabela acima | Fase 0 | ver `architecture.md` |
| **INV-13** | solicitante do papel de topo é recusado na criação (não há autoridade acima) | Fase 1, exposta pela decomposição de `matriz-doa` | matriz-doa |
| **INV-14** | a matriz DoA é válida: níveis contíguos a partir de 1, únicos, limites estritamente crescentes; e todo usuário aponta para papel existente. Verificado na carga — o processo não sobe se falhar | Fase 3, V(2)/R1 + V(4)/T5 (achados A-01, A-10) | matriz-doa |
| ~~INV-15~~ | ~~todo papel da cadeia tem titular, senão recusa a criação~~ — **REVOGADA em V(3)** | criada em V(2), revogada por REG-04 e UX-07: nenhuma prática de DoA bloqueia gasto por assento vago | — |
| **INV-16** | delegação não pode ser antedatada (`inicio >= agora`), com fuso normalizado por regra escrita | Fase 3, V(2)/R1 + V(3)/S3 (achados A-03, A-07) | dominio-delegacao |
| **INV-17** | a criação só é recusada por falta de aprovador quando **nenhum** nível da cadeia tem decisor | Fase 3, V(3)/S1.2 | autoridade |
| **INV-18** | uma despesa só chega a APROVADA com **pelo menos uma aprovação humana registrada** | Fase 3, V(4)/T2.4 — guarda contra a regra do pulo degradar quatro olhos a zero | autoridade |

### Regra do pulo (V(3)/S1.2, generalizada em V(4)/T2.1)

Ao chegar ao nível `k` da cadeia, se **nenhum usuário é decisor** daquele nível naquele
instante — por papel vago, por INV-2 ou por INV-4 —, o nível é **pulado** e o pulo grava
`NIVEL_PULADO(nivel, motivo)` na trilha. É uma regra só, avaliada sempre no ato (INV-6).
Contida por INV-17 (na criação) e INV-18 (na aprovação).

### Definição única de "decidível" (V(4)/T1)

Um nível é **decidível** por `u` no instante `t` **se e somente se** `autoridade.resolver`
devolve sucesso para `u`. Não existe segundo conceito de elegibilidade em lugar nenhum do
sistema — foi exatamente a ausência dessa definição única que gerou os achados LING-07,
A-09 e ARQ-08.

### Delegação é caminho adicional, não transferência de posse (V(3)/S2)

Quando o delegado é inelegível para um item específico (INV-2 ou INV-4), aquele item
**permanece com o delegante**. Refinamento de CA-3 aprovado explicitamente pelo operador.
