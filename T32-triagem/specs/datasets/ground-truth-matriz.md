# Ground truth — priorização e casos de borda

Verdade fundamental dos testes da Fase 6. Derivado de
`specs/technical/matriz-prioridade.md` (fonte F1). **Escrito antes do código.**

## GT-1 — As 9 células da matriz (CA-1)

Todos os prazos em **horas corridas** (decisão da Fase 0 — não há calendário
de negócio).

| # | Impacto | Urgência | Prioridade esperada | Reconhecer | Resolver |
|---|---|---|---|---|---|
| 1 | ALTO | ALTA | **P1** | 10 min | **4 h** |
| 2 | ALTO | MEDIA | **P2** | 15 min | **8 h** |
| 3 | ALTO | BAIXA | **P3** | 1 h | **48 h** |
| 4 | MEDIO | ALTA | **P2** | 15 min | **8 h** |
| 5 | MEDIO | MEDIA | **P3** | 1 h | **48 h** |
| 6 | MEDIO | BAIXA | **P4** | 4 h | **120 h** |
| 7 | BAIXO | ALTA | **P3** | 1 h | **48 h** |
| 8 | BAIXO | MEDIA | **P4** | 4 h | **120 h** |
| 9 | BAIXO | BAIXA | **P5** | 24 h | **240 h** |

Propriedades que devem valer sobre esta tabela (testes de propriedade):

- **Totalidade:** 9 células, nenhuma indefinida.
- **Monotonicidade:** agravar um eixo mantendo o outro nunca melhora a prioridade.
- **Simetria dos eixos:** célula 3 (ALTO,BAIXA) = célula 7 (BAIXO,ALTA) = P3.

## GT-2 — Cenário canônico do recurso provido (CA-2)

Relógio controlado. `T0` = abertura.

| Instante | Evento | Impacto | Urgência | P | Prazo resolver | Violado? |
|---|---|---|---|---|---|---|
| T0 | Solicitante abre, declara urgência MEDIA | — | MEDIA | — | — | — |
| T0 + 30 min | Agente tria: impacto BAIXO | BAIXO | MEDIA | **P4** | T0 + 120 h | não |
| T0 + 2 h | Solicitante recorre: "urgência é ALTA, fecho o balanço hoje" | BAIXO | MEDIA | P4 | T0 + 120 h | não |
| T0 + 5 h | Gestor julga **PROVIDO** (urgência → ALTA) | BAIXO | **ALTA** | **P3** | **T0 + 48 h** | não |

Note que o prazo novo é contado de **T0**, não de T0+5 h. Este é o coração de CA-2.

## GT-3 — Provimento que revela violação já ocorrida (VAL-12)

| Instante | Evento | P | Prazo resolver | Violado? |
|---|---|---|---|---|
| T0 | Abertura, urgência BAIXA | — | — | — |
| T0 + 1 h | Triagem: impacto BAIXO | **P5** | T0 + 240 h | não |
| T0 + 40 h | Recurso provido: impacto → ALTO, urgência → ALTA | **P1** | **T0 + 4 h** | **SIM** |

O chamado passa a constar violado no instante do provimento, porque o prazo
de P1 já havia vencido 36 horas antes. **É o comportamento correto:** a
urgência sempre existiu; o erro foi não tê-la visto na triagem. Um sistema que
"perdoasse" aqui tornaria o erro de triagem invisível.

## GT-4 — Casos de borda (testes negativos)

| # | Cenário | Resultado esperado |
|---|---|---|
| B-1 | Recurso em chamado NÃO TRIADO | Recusado — não há classificação a contestar |
| B-2 | Segundo recurso no mesmo chamado | Recusado — limite de um por chamado |
| B-3 | Recurso a 48 h + 1 min da triagem | Recusado **por prescrição** (motivo distinto dos demais) |
| B-4 | Recurso a 48 h − 1 min da triagem | Admitido — testa a fronteira exata |
| B-5 | Recurso aberto por usuário que não é o solicitante | Recusado — falta legitimidade |
| B-6 | Agente tenta julgar recurso | Recusado — só o Gestor julga |
| B-7 | Julgamento com fundamentação vazia | Recusado |
| B-8 | Recurso IMPROVIDO | Prioridade e prazos inalterados; trilha registra |
| B-9 | Reclassificação de MEDIO/BAIXA para BAIXO/MEDIA (P4 → P4) | Prioridade não muda; trilha registra a mudança dos eixos |
| B-10 | Requisição de API tentando enviar `prioridade` diretamente | Ignorada ou recusada — nunca aceita (CA-negativo) |
| B-11 | Recurso em chamado já encerrado | Recusado |
| B-12 | Solicitante tenta atribuir impacto | Recusado — impacto é do agente |

## GT-5 — Seed de usuários

| Nome | Papel |
|---|---|
| Ana | SOLICITANTE |
| Bruno | SOLICITANTE |
| Carla | AGENTE |
| Diego | AGENTE |
| Elena | GESTOR |

Dois solicitantes (para testar B-5), dois agentes (para testar que quem triou
não é quem julga) e um gestor.
