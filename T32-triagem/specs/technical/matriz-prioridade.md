# Matriz de prioridade — parâmetros com fonte

Todo número desta página aponta para uma fonte em
`specs/references/01-fontes-itil.md`. Nenhum valor foi inventado.

## Eixo IMPACTO (3 níveis) — fonte F1 (Tier B)

| Nível | Código | Definição (traduzida de F1) |
|---|---|---|
| Alto | `ALTO` | A organização inteira é afetada. Sistema central parado, operações do negócio interrompidas, ou risco a receita, conformidade regulatória ou reputação. |
| Médio | `MEDIO` | Um departamento ou grupo significativo de usuários é afetado. Fluxos-chave prejudicados, mas a organização segue parcialmente operante. |
| Baixo | `BAIXO` | Um único usuário ou um sistema não-crítico é afetado. O dia a dia do resto da organização continua normal. |

**Quem atribui:** o agente, após triagem (fonte F4). Não é declarado pelo solicitante.

## Eixo URGÊNCIA (3 níveis) — fonte F1 (Tier B)

| Nível | Código | Definição (traduzida de F1) |
|---|---|---|
| Alta | `ALTA` | Precisa ser resolvido imediatamente. Há prazo duro de negócio, uma operação sensível ao tempo está bloqueada, ou o atraso causará falhas em cascata. |
| Média | `MEDIA` | Precisa ser resolvido dentro do dia útil. Afeta produtividade, mas existe contorno de curto prazo ou o prazo é flexível. |
| Baixa | `BAIXA` | Pode ser agendado. Sem prazo imediato; a operação normal segue. |

**Quem atribui:** o solicitante, na abertura (fonte F4). É a declaração dele
sobre a própria dor — e por isso é o eixo que ele tem legitimidade plena para
contestar em recurso.

## Matriz IMPACTO × URGÊNCIA → PRIORIDADE — fonte F1 (Tier B)

| Impacto \ Urgência | ALTA | MEDIA | BAIXA |
|---|---|---|---|
| **ALTO** | **P1** | **P2** | **P3** |
| **MEDIO** | **P2** | **P3** | **P4** |
| **BAIXO** | **P3** | **P4** | **P5** |

Propriedades verificáveis desta matriz (viram teste na Fase 6):

- **Total, 9 células, sem buraco.** Todo par (impacto, urgência) tem prioridade.
- **Monótona.** Piorar um eixo mantendo o outro nunca melhora a prioridade.
  Formalmente: `P(i,u)` é não-crescente em i e em u (P1 é a mais severa).
- **Simétrica na diagonal anti-.** P(ALTO,BAIXA) = P(BAIXO,ALTA) = P3. Os dois
  eixos têm peso igual nesta matriz — uma escolha, não uma lei.
- **Derivável por soma.** Com ALTO/ALTA=1, MEDIO/MEDIA=2, BAIXO/BAIXA=3:
  `P = impacto + urgência - 1`, faixa 1..5. Equivalente à tabela acima; a
  tabela é a verdade normativa, a fórmula é conveniência de implementação.

## Metas de SLA por prioridade — fonte F1 (**Tier C — exemplo de fornecedor**)

⚠️ **Estes números NÃO são norma ITIL.** São exemplo publicado por um
fornecedor. Uso legítimo: **default configurável de projeto**. Uso ilegítimo:
afirmar ao usuário que "ITIL define 4 horas para P1".

| Prioridade | Reconhecer em (F1) | Resolver em (F1) |
|---|---|---|
| P1 | 10 minutos | 4 horas |
| P2 | 15 minutos | 8 horas |
| P3 | 1 hora | 2 dias úteis |
| P4 | 4 horas | 5 dias úteis |
| P5 | 1 dia útil | 10 dias úteis |

### Conversão para HORAS CORRIDAS — decisão de projeto (Fase 0)

**Não existe calendário de negócio neste sistema.** Sem jornada, sem fins de
semana, sem feriados, sem fuso. Todo prazo é contado em horas corridas a
partir da abertura do chamado. Isso elimina um módulo inteiro e toda a classe
de bugs de borda de expediente, ao custo de divergir dos números de F1 —
divergência declarada aqui, não escondida.

| Prioridade | Reconhecer (h corridas) | Resolver (h corridas) | Origem da conversão |
|---|---|---|---|
| P1 | 0,167 h (10 min) | **4 h** | idêntico a F1 |
| P2 | 0,25 h (15 min) | **8 h** | idêntico a F1 |
| P3 | 1 h | **48 h** | 2 dias úteis → 48 h corridas |
| P4 | 4 h | **120 h** | 5 dias úteis → 120 h corridas |
| P5 | 24 h | **240 h** | 10 dias úteis → 240 h corridas |

Prazos do rito de recurso, na mesma escala: **recorrer em 48 h corridas**
contadas da triagem; **julgar em 24 h corridas** contadas da abertura do
recurso. Também Tier C (defaults de projeto, sem fonte normativa).

⚠️ Um sistema real de service desk contaria dias úteis — um P4 aberto na
sexta-feira não vence no meio do domingo. A simplificação é consciente e
proporcional ao que este projeto investiga (o par reclassificação/recurso),
não uma omissão.

## Configurabilidade — fontes F2, F4

Nenhum produto ITSM pesquisado (Jira Service Management, GLPI) trata a matriz
como constante. F2 diz literalmente que os valores publicados "são apenas
exemplos". GLPI expõe a matriz em Setup > General > Assistance como grade
editável. **Consequência de design:** a matriz é dado, não código.

## O problema do recálculo — fontes F4, F5

Dois achados que colidem e precisam de decisão explícita na arquitetura:

- **F4:** alterar a matriz afeta apenas chamados novos; chamados abertos
  retêm a prioridade já calculada, salvo recálculo explícito.
- **F5:** mudar prioridade no meio do ciclo de vida deve ser evitado porque as
  ferramentas ITSM têm problemas para recalcular prazos de escalonamento e
  parâmetros de SLA.

Mas o enunciado deste projeto **exige** reclassificação e recurso — isto é,
exige exatamente a operação que F5 diz ser perigosa. Isso não invalida o
projeto: torna o **tratamento do relógio de SLA sob mudança de prioridade** um
requisito de primeira classe, não um detalhe. As opções são três, e uma delas
precisa ser escolhida e registrada:

| Opção | Relógio de SLA ao mudar P | Consequência |
|---|---|---|
| **Reiniciar** | zera, conta do zero na nova prioridade | Simples; permite lavar atraso reclassificando |
| **Continuar** | mantém o consumido, aplica a nova meta | Preserva histórico; pode nascer já estourado |
| **Recalcular retroativo** | recomputa desde a abertura com a nova meta | Mais fiel; um P5 antigo virando P1 nasce violado |

Nenhuma é "certa". A ausência de escolha é que é defeito.
