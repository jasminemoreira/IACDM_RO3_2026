# Concorrentes / estado da arte — priorização automática em ITSM

Levantado na Fase 0 para responder: o que já está resolvido no mercado (não
reinventar) e onde estão as lacunas (onde este projeto pode dizer algo).

## Comparativo

| Produto | Matriz | Quem declara urgência / impacto | Prioridade editável à mão? | Recurso do solicitante | Fonte |
|---|---|---|---|---|---|
| **GLPI** | 5×5, editável em Setup > General > Assistance | Urgência: solicitante · Impacto: agente | Sim (agente pode sobrepor) | Não existe como rito. Solicitante comenta; o agente decide | F4 |
| **Jira Service Management** | Configurável (exemplo 4×4), aplicada por regra de automação na criação | Campos Impacto/Urgência no formulário de requisição | Sim — o campo Priority é editável | Não existe. Há "aprovações" e escalonamento interno | F2, F3 |
| **ServiceNow** | 3×3 padrão (Impact × Urgency → Priority 1..5), configurável em Data Lookup Rules | Ambos no formulário; impacto tipicamente do agente | Sim | Não como rito formal do solicitante | conhecimento de domínio; não verificado por fetch nesta sessão |
| **Zendesk / osTicket** | Sem matriz — prioridade é campo direto de 4 valores | Agente | Sim, é o mecanismo primário | Não | conhecimento de domínio; não verificado por fetch |

⚠️ As duas últimas linhas não foram verificadas por acesso direto à
documentação nesta sessão. Estão marcadas como não verificadas de propósito —
tratá-las como fato citável seria exatamente o AP7. Se virarem base de decisão
de design, verificar antes.

## A lacuna que este projeto ocupa

Os quatro produtos convergem em três coisas:

1. **A prioridade é derivada de dois eixos** (exceto Zendesk/osTicket, que
   nem derivam).
2. **A derivação é configurável, não codificada.**
3. **A prioridade continua editável à mão** — ou seja, a derivação é uma
   sugestão que o agente sobrepõe à vontade.

E divergem — ou melhor, são todos omissos — em uma:

4. **Nenhum tem recurso do solicitante como rito.** O solicitante que discorda
   da classificação comenta no chamado e torce. Não há prazo, não há julgador
   nomeado, não há desfecho registrado, não há trilha de por que a
   classificação mudou ou deixou de mudar.

**Portanto:** triagem com prioridade automática é problema resolvido — é Tier 1
(usar o que existe: matriz do domínio, sem inventar fórmula). O que este
projeto tem de próprio é o **par reclassificação/recurso como processo
simétrico e auditável**, que é justamente onde o mercado é omisso e, não por
acaso, onde ficam as decisões difíceis: relógio de SLA, autoridade,
prescrição, e o que impede o recurso de virar canal de furar fila.

## Consequência direta para o design

Se a prioridade permanecer **editável à mão** (como em todos os concorrentes),
o recurso perde o objeto: não se contesta uma derivação, contesta-se o humor
do agente, e a explicabilidade morre. A decisão "prioridade é estritamente
derivada, nunca digitada" é o que dá sentido ao resto do sistema — e é uma
divergência consciente do estado da arte, não um esquecimento.
