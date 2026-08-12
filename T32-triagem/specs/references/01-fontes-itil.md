# Fontes — Priorização e triagem de chamados (ITIL)

Pesquisa realizada na Fase 0, Nível 1 (HSA), com autorização do operador.
Toda fonte tem URL. Cada parâmetro numérico usado no design DEVE apontar para
uma linha desta tabela (antídoto AP7 — "não implementar algoritmo sem
referência bibliográfica verificável").

## Classificação do lastro (declarada, não presumida)

| Tier | Significado | Uso permitido |
|---|---|---|
| **A — Normativo** | Padrão publicado (ITIL 4, ISO/IEC 20000, ISO 10002) | Estrutura do modelo; pode ser afirmado como "padrão" |
| **B — Convergência de mercado** | Mesma prática em ≥2 produtos ITSM independentes | Default de projeto; pode ser afirmado como "prática consolidada" |
| **C — Exemplo de fornecedor** | Número publicado por um blog/vendor, sem norma | Valor **default configurável**; NUNCA afirmar como "padrão ITIL" |

> Regra de honestidade: os **eixos** e a **estrutura** da matriz são Tier A/B.
> Os **minutos de SLA** são Tier C. Um design que apresentar "P1 = 4 horas"
> como norma ITIL está inventando lastro. É default configurável.

## Fontes

| # | Fonte | URL | Tier | O que sustenta |
|---|---|---|---|---|
| F1 | InvGate — ITIL Priority Matrix | https://blog.invgate.com/itil-priority-matrix | B/C | Matriz 3×3 Impacto×Urgência → P1..P5 (B); definições textuais dos níveis (B); metas de SLA por prioridade (C) |
| F2 | Atlassian — Calculating priority automatically (JSM Data Center) | https://confluence.atlassian.com/servicemanagementserver/calculating-priority-automatically-939926661.html | B | Matriz 4×4 alternativa; confirma que a matriz é **configurável**, não fixa ("the priority values listed above are just examples") |
| F3 | Atlassian — Create an impact urgency priority matrix (JSM Cloud) | https://support.atlassian.com/jira-service-management-cloud/docs/how-do-i-create-a-matrix-using-impact-and-urgency-values/ | B | Prioridade derivada por automação a partir dos campos Impacto e Urgência |
| F4 | ITčko — Urgency × impact matrix in GLPI | https://itcko.sk/en/empower-your-it-support-with-glpis-incident-management-feature/ | B | Matriz 5×5; **urgência é do solicitante, impacto é do agente após triagem**; chamados abertos retêm a prioridade já calculada salvo recálculo explícito |
| F5 | Advisera (20000 Academy) — ITIL & ISO 20000 Incident Classification | https://advisera.com/20000academy/knowledgebase/incident-classification/ | A/B | Classificação de incidentes sob ISO/IEC 20000; **mudar prioridade durante o ciclo de vida do incidente deve ser evitada** porque ferramentas ITSM têm problemas para recalcular prazos de escalonamento e parâmetros de SLA |
| F6 | ISO 10002:2018 — Complaints handling (amostra pública) | https://cdn.standards.iteh.ai/samples/71580/7f69224e30304ee5922a3563fe707eb1/ISO-10002-2018.pdf | A | Rito de reclamação: níveis de escalonamento declarados, critérios e prazos por nível, autoridade definida por nível; escalonamento disponível a quem discorda da resolução proposta |
| F7 | Purple Griffon — Incident Categorisation | https://purplegriffon.com/blog/incident-categorisation | B | Categorização correta roteia ao grupo certo; categorias analisáveis ao longo do tempo revelam padrões |
| F8 | Freshworks — ITIL Ticket Types | https://www.freshworks.com/itil/ticket-types/ | B | Os quatro tipos ITIL: incidente, problema, mudança, requisição de serviço |

## Achados que viram restrição de design (não apenas referência)

1. **F4 — separação de autoridade nos eixos.** Urgência é declarada pelo
   solicitante; impacto é atribuído pelo agente após triagem. Isso não é
   detalhe de UI: define *quem pode contestar o quê* no recurso. O solicitante
   contesta legitimamente a urgência (é dele); contestar o impacto é pedir
   revisão de um juízo do agente.

2. **F5 — reprecificação de prioridade é perigosa em voo.** Alterar a
   prioridade de um chamado já aberto quebra prazos de SLA já contados.
   Qualquer reclassificação precisa decidir explicitamente o que acontece com
   o relógio do SLA: reinicia, continua, ou recalcula retroativamente. As três
   respostas são defensáveis; ausência de resposta é um defeito.

3. **F4 — mudar a matriz não muda o passado.** Chamados abertos mantêm a
   prioridade já calculada salvo recálculo explícito. Se a matriz é
   configurável, a prioridade gravada e a prioridade recalculável divergem —
   é preciso decidir qual é a verdade.

4. **F6 — recurso tem rito, não só botão.** ISO 10002 exige níveis de
   escalonamento declarados, critérios e prazos por nível, e autoridade
   definida por nível. Um "recurso" sem prazo e sem julgador nomeado não é
   recurso, é caixa de sugestões.

5. **F2 — a matriz é configurável por design, em todos os produtos.** Nenhum
   fornecedor trata a matriz como constante do código. Cravá-la em código é
   divergir da prática consolidada do domínio.
