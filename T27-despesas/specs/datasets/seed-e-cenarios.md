# Seed e cenários de verdade-de-campo — T27

Dados de partida do sistema e os cenários que a Fase 6 usa como verdade de campo. Os
limites seguem a forma "uma ordem de grandeza por nível" justificada em
`specs/references/dominio-aprovacao-despesas.md`; os números em si são arbitrários por
natureza (configuração de uma empresa fictícia), como registrado no achado SCI-01.

## Matriz DoA (tabela `papel`) — deve passar em `validar` (INV-14)

| id | nome | nivel | limite_centavos | limite |
|---|---|---|---|---|
| `coordenador` | Coordenador | 1 | 500000 | R$ 5.000,00 |
| `gerente` | Gerente | 2 | 5000000 | R$ 50.000,00 |
| `diretor` | Diretor | 3 | 50000000 | R$ 500.000,00 |

Níveis contíguos a partir de 1, únicos, limites estritamente crescentes. ✅ INV-14.

## Usuários (tabela `usuario`)

| id | nome | papel |
|---|---|---|
| `ana` | Ana Silva | coordenador |
| `bruno` | Bruno Costa | coordenador |
| `carla` | Carla Dias | gerente |
| `dario` | Dário Melo | gerente |
| `elisa` | Elisa Rocha | diretor |
| `fabio` | Fábio Nunes | diretor |

**Dois titulares por papel** — necessário para exercitar INV-4 (mesmo ator em dois níveis)
e delegação lateral sem violar INV-2. O papel Admin é atributo de operação, não de alçada:
`elisa` acumula a função de Admin nas telas T6.

## Cenários de verdade de campo

Valores em centavos. "Cadeia" pela fórmula de V(3)/S1.1: papéis de nível estritamente acima
do solicitante, em ordem crescente, até e incluindo o primeiro cujo limite cobre o valor.

| # | cenário | entrada | cadeia esperada | resultado esperado | cobre |
|---|---|---|---|---|---|
| D-1 | 1 nível | `ana` pede 10000 (R$100) | [gerente] | 1 aprovação → APROVADA | CA-1 |
| D-2 | 2 níveis | `ana` pede 8000000 (R$80k) | [gerente, diretor] | 2 aprovações → APROVADA | CA-1 |
| D-3 | fronteira inclusiva | `ana` pede 5000000 (R$50.000,00 exatos) | [gerente] | Carla encerra; **não** sobe ao Diretor | CA-2 |
| D-4 | fronteira, um centavo acima | `ana` pede 5000001 | [gerente, diretor] | 2 aprovações | CA-2 (negativo) |
| D-5 | acima do teto | `ana` pede 200000000 (R$2mi) | — | recusada **na criação** | CA-7 |
| D-6 | solicitante no topo | `elisa` pede 100000 | — | recusada na criação (INV-13) | CA-7 |
| D-7 | delegação simples | `carla` delega a `bruno`, `ana` pede 8000000 | [gerente, diretor] | item na bandeja de `bruno`, não na de `carla` | CA-3 |
| D-8 | delegado inelegível | `carla` delega a `ana`; `ana` pede 8000000 | [gerente, diretor] | nível gerente fica com `carla` (INV-2 barra `ana`) | CA-3b |
| D-9 | autoridade exercida | `bruno` decide por `carla` | — | registro: ator=`bruno`, em nome de=`carla`, limite=5000000, delegacao_id preenchido | CA-4 |
| D-10 | expiração com item na fila | delegação `carla`→`bruno` vence com item pendente | — | item volta à bandeja de `carla`; aprovação que `bruno` deu antes segue válida | CA-5 |
| D-11 | revogação | `carla` revoga durante a vigência | — | idem D-10, e o evento de revogação fica registrado | CA-5 |
| D-12 | auto-aprovação | `carla` pede 8000000 e tenta decidir o nível diretor via delegação de `elisa` | — | bloqueada, mensagem de INV-2 | CA-6 |
| D-13 | duplo voto | `elisa` delega a `carla`; `carla` decide nível gerente e depois o nível diretor | — | segundo bloqueado por INV-4; nível diretor fica com `elisa` (V(4)/T4) | CA-6, CA-3b |
| D-14 | redelegação | `bruno` (exercendo por `carla`) tenta delegar | — | bloqueada, mensagem de INV-3 | CA-6 |
| D-15 | vigências sobrepostas | `carla` cria segunda delegação cruzando a primeira | — | bloqueada, mensagem de INV-5 | CA-6 |
| D-16 | rejeição sem motivo | `carla` rejeita sem texto | — | recusada | CA-8 |
| D-17 | rejeição com motivo | `carla` rejeita com "sem verba" | — | REJEITADA terminal; não volta à fila | CA-8 |
| D-18 | trilha completa | após D-2 | — | eventos CRIADA → APROVADA nível 2 → APROVADA nível 3, imutáveis | CA-9 |
| D-19 | restart | após D-2, reiniciar o processo | — | mesma bandeja, mesma trilha | CA-10 |
| D-20 | nível intermediário sem decisor | remover ambos os gerentes do seed; `ana` pede 8000000 | [gerente, diretor] | `diretor` aprova sozinha; trilha contém `NIVEL_PULADO(2, sem decisor)` | **CA-1b** |
| D-21 | nenhum nível com decisor | seed só com coordenadores; `ana` pede 8000000 | — | recusada na criação (INV-17/INV-18) | **CA-1c** |
| D-22 | concorrência | duas decisões simultâneas no mesmo item | — | a segunda falha com erro de conflito determinístico | — |

D-20 e D-21 exigem uma **variante do seed** (sem gerentes / só coordenadores); a suíte deve
montá-la em memória, não alterar o seed principal.

## Regras de conversão de valor

Entrada da UI em reais é convertida por parsing de string na borda (M-11), nunca por
`parseFloat(x) * 100`. `"50.000,00"` → `5000000`. `"19,99"` → `1999`.
