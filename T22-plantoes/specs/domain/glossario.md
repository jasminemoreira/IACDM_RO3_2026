# Glossário do domínio — distribuidor de plantões hospitalares

> Fase 0, Nível 1. Vocabulário fixado ANTES da arquitetura. Termos marcados
> ⚠️ eram ambíguos no enunciado congelado e foram desambiguados por decisão do
> operador — a ambiguidade original fica registrada.

| Termo | Definição adotada | Sinônimo a EVITAR |
|---|---|---|
| **Plantão** (*shift*) | Ocorrência concreta de um turno em uma data e unidade, com demanda de N profissionais de uma dada habilitação. É a unidade alocável. | "turno" quando se quer dizer a ocorrência |
| **Tipo de turno** (*shift type*) | Classe do plantão (ex.: diurno 12h, noturno 12h, sobreaviso). Carrega limites de consecutividade e sucessões legais. | — |
| **Escala** (*roster*) | Conjunto de alocações pessoa×plantão para um horizonte de planejamento. É o artefato entregue. | "grade", "tabela" |
| **Alocação** (*assignment*) | Par (pessoa, plantão) afirmado como válido na escala. | — |
| **Horizonte de planejamento** | Intervalo coberto por uma execução da distribuição (ex.: 4 semanas). Fronteiras do horizonte carregam estado (ver `history`). | — |
| **Habilitação / skill** | Competência exigida por um plantão e possuída por uma pessoa (especialidade, nível). H4 do INRC-II. | "cargo" |
| **Contrato** | Conjunto de limites individuais: total de plantões no horizonte, máx./mín. de dias consecutivos, máx. de fins de semana, regime (12×36 etc.). | "vínculo" |
| **Restrição rígida** (*hard*) | Condição que toda escala válida cumpre. Violação = escala inviável, não escala ruim. Origem legal ou operacional. | — |
| **Restrição flexível** (*soft*) | Condição desejável cuja violação é penalizada com peso. Define a QUALIDADE da escala. | "preferência" (preferência é UM tipo de soft, não sinônimo) |
| **Custo da escala** | Σ (violações soft × peso). Menor é melhor. Só é definido sobre escalas viáveis. | "score" |
| ⚠️ **Distribuir** | **Gerar automaticamente** a alocação a partir de pessoas + plantões + restrições. NÃO é registrar nem validar escala feita por humano. | "montar", "publicar" |
| ⚠️ **Restrição** | Termo guarda-chuva. Sempre qualificar: rígida/flexível E legal/interna. Uma restrição legal violada é ilegalidade; uma interna violada é política. | usar "regra" solto |
| ⚠️ **Troca** (*swap*) | Permuta de plantões entre **duas pessoas identificadas**, iniciada por uma delas. Distinta de *pedido* (folga/turno sem contraparte). | "substituição" |
| ⚠️ **Aprovação** | Ato que transforma uma troca pendente em efetiva. Envolve até dois consentimentos distintos: o do par e o do gestor. | "confirmação" |
| **Pendente** | Estado de primeira classe de uma troca: submetida, ainda não decidida, de duração indeterminada. Durante ele a escala pode mudar por outra via. | — |
| **Cobertura** | Nº de pessoas alocadas a um plantão × habilitação. Tem piso (mínimo, hard H2) e alvo (ótimo, soft S1). | "lotação" |
| **Fairness / equidade** | Distribuição equilibrada de carga indesejável (noturnos, fins de semana, feriados) entre pessoas. Expressa-se como termo soft na função objetivo. | "justiça" sem métrica |
| **Interjornada** | Descanso mínimo entre duas jornadas. 11h por CLT art. 66. | "intervalo" (art. 71 é intrajornada — outro instituto) |
| **RSR** | Repouso semanal remunerado: 24h consecutivas, CLT art. 67. | "folga" |
| **12×36** | Regime de 12h trabalhadas / 36h de descanso ininterrupto, CLT art. 59-A. | — |
| **Sobreaviso** | Disponibilidade para ser acionado, sem presença física obrigatória. Regime e remuneração distintos do plantão presencial. | "plantão à distância" |

## Campo teórico e metodologias

- **Disciplina:** Pesquisa Operacional — otimização combinatória; especificamente
  *personnel scheduling* / *nurse rostering*. Ver `specs/references/nrp-inrc2.md`.
- **Metodologia estabelecida:** formulação hard/soft com função objetivo
  penalizada; benchmark público INRC-II com pesos publicados.
- **Segunda disciplina, não redutível à primeira:** modelagem de processo de
  negócio multi-ator (troca → consentimento → homologação), com máquina de
  estados. A literatura de rostering não a cobre; a fonte é
  `specs/competitors/analise.md`.
- **Terceira:** conformidade normativa trabalhista brasileira
  (`specs/references/clt-jornada.md`).

O projeto tem, portanto, **três domínios distintos** — otimização, workflow e
conformidade legal. Isso já é, por si só, sinal de complexidade suficiente para
justificar a metodologia (gatilho T5).
