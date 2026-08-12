# Vocabulário do domínio — T32-triagem

Universo semântico fixado na Fase 0, Nível 1. Termo canônico à esquerda;
sinônimos proibidos marcados para evitar deriva de nomenclatura entre fases.

## Termos centrais

| Termo | Entendimento | Exemplo concreto |
|---|---|---|
| **Chamado** | Unidade de trabalho registrada pelo solicitante. Neste projeto engloba incidente e requisição (F8). Sinônimo aceito: ticket. **Evitar:** "caso", "ocorrência", "protocolo". | "Impressora do 3º andar não imprime" |
| **Solicitante** | Quem abre o chamado e sofre o problema. Declara a urgência. **Evitar:** "cliente", "usuário" (ambíguo com operador). | Analista do financeiro |
| **Agente** | Quem tria, atribui impacto e resolve. **Evitar:** "atendente", "técnico" alternando. | Membro do service desk |
| **Triagem** | Ato de classificar um chamado recém-aberto: definir categoria e impacto, do que decorre a prioridade. Não é atendimento; é o que decide a ordem do atendimento. | Agente lê o chamado, marca categoria=Hardware, impacto=BAIXO |
| **Impacto** | Abrangência do efeito no negócio. 3 níveis (F1). Atribuído pelo **agente** (F4). | Organização inteira / departamento / um usuário |
| **Urgência** | Velocidade com que a situação degrada. 3 níveis (F1). Declarada pelo **solicitante** (F4). | Prazo duro hoje / dentro do dia / agendável |
| **Prioridade** | **Derivada**, nunca digitada: P1..P5, saída da matriz impacto × urgência. Que seja derivada é o que a torna explicável — e portanto recorrível. | Impacto MEDIO + urgência ALTA → P2 |
| **Categoria** | Taxonomia do assunto do chamado; roteia ao grupo certo (F7). Ortogonal à prioridade. | Hardware, Software, Rede, Acesso |
| **Reclassificação** | Mudança, após a triagem inicial, de um insumo da classificação (categoria, impacto ou urgência) — com a prioridade recalculada em consequência. Iniciativa do **agente**. | Agente descobre que o problema afeta o andar inteiro: impacto BAIXO → MEDIO |
| **Recurso** | Contestação formal do solicitante contra a classificação atribuída, com rito: prazo, julgador nomeado e desfecho registrado (F6). Iniciativa do **solicitante**. **Não é** reabertura, **não é** comentário. | "Marcaram urgência baixa mas eu fecho o balanço hoje" |
| **SLA** | Meta de tempo por prioridade: prazo de reconhecimento e prazo de resolução. Default configurável (Tier C, F1). | P1: reconhecer em 10 min, resolver em 4 h |
| **Fila** | Ordenação dos chamados abertos por prioridade e, dentro da prioridade, por algum critério de desempate. | P1s primeiro, depois P2s |

## Termos vagos do enunciado — resolvidos

| Termo vago no enunciado | Resolvido como |
|---|---|
| "prioridade automática" | Derivação determinística P = f(impacto, urgência) pela matriz 3×3 de F1, sem intervenção humana no cálculo e sem campo de prioridade editável à mão |
| "triagem" | Atribuir categoria + impacto a um chamado novo; a prioridade cai fora como consequência |
| "reclassificação" | Alteração pós-triagem de categoria/impacto/urgência por decisão do agente, com recálculo de prioridade e efeito declarado sobre o relógio de SLA |
| "recurso do solicitante" | Rito de contestação conforme ISO 10002 (F6): quem pode abrir, contra o quê, em que prazo, julgado por quem, com que desfechos possíveis |

## Assimetria de autoridade (a regra que organiza tudo)

Fonte F4. Não é convenção de interface — é a estrutura política do sistema:

| Eixo | Quem declara | Quem pode contestar | Instrumento |
|---|---|---|---|
| Urgência | Solicitante | Agente (na reclassificação) | Reclassificação |
| Impacto | Agente | Solicitante (no recurso) | Recurso |
| Prioridade | Ninguém — é derivada | Ninguém diretamente | Contesta-se um eixo, nunca o resultado |

Consequência: **recurso e reclassificação são o mesmo mecanismo visto dos dois
lados** — cada parte pode contestar o eixo que a outra declarou. Essa simetria
é a descoberta central do Nível 1 e deve sobreviver até a arquitetura.

## Campo teórico e padrões aplicáveis

- **Disciplina:** IT Service Management (ITSM), gestão de incidentes.
- **Padrões:** ITIL 4 (prática de Incident Management), ISO/IEC 20000
  (classificação de incidentes, F5), ISO 10002:2018 (tratamento de
  reclamações — aplicável ao rito de recurso, F6).
- **Ecossistema de referência:** ServiceNow, Jira Service Management, GLPI,
  Zendesk, osTicket, TOPdesk. Ver `specs/competitors/`.
