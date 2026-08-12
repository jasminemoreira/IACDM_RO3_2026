# Concorrentes / estado da arte — aprovação de despesas com alçada e delegação

Levantamento da Fase 0 (2026-08-11). O objetivo não é copiar produto: é saber quais
mecanismos são considerados mesa posta no domínio, para que a arquitetura da Fase 1 não
reinvente nem omita por ignorância.

| Produto | Alçada por valor | Delegação temporária | O que faz que é relevante aqui | Fonte |
|---|---|---|---|---|
| **ApprovalMax** | sim, política DoA com faixas | sim | Política de DoA como artefato de primeira classe, com passo a passo de implantação | <https://blog.approvalmax.com/how-to-establish-a-delegation-of-authority-policy-and-stick-to-it-effortlessly> |
| **Stampli** (AP) | sim, matriz DoA | — | Tríade matriz + workflow + SoD; matriz codificada como regras de roteamento com limites em valor e cadeias por papel | <https://www.stampli.com/resources/delegation-of-authority-matrix-ap/> |
| **Workday** | sim | sim, por ausência | Distingue **delegação** (autoridade de aprovação, temporária) de **proxy** (acesso administrativo amplo). Distinção adotada no nosso glossário | <https://www.cloudapper.ai/workday-help/workday-delegate-proxy-access-manager-self-service-scale/> |
| **Oracle / worklist (Stanford)** | sim | sim, com vigência | Delegação de worklist com datas de início e fim — o mesmo modelo de vigência do nosso N2 | <https://fingate.stanford.edu/authority/delegate-or-share-oracle-approval-worklist> |
| **OpenIAM** | via workflow | sim, permanente ou com prazo | Aprovação delegada entra na **mesma** trilha da direta, registrando quem delegou e quem agiu — confirma INV-7 | <https://www.openiam.com/blog/workflow-approval-delegation-options-in-openiam> |
| **Wiise** (ERP) | sim, setup de DoA | sim | Configuração de DoA como setup de ERP | <https://docs.wiise.com/setup-a-delegation-of-authority> |
| **Aptly** | sim, gestão de matriz DoA | sim | Produto dedicado a gerir a matriz em si | <https://www.aptlydone.com/platform/delegation-of-authority> |
| **Tallyfy / altaFlow** | sim | — | Roteamento e escalonamento sem código; escalonamento **por tempo** (SLA) é padrão de mercado | <https://tallyfy.com/delegation-of-authority-matrix-template/> · <https://altaflow.com/use-case/approvals> |

## Lacunas e escolhas conscientes deste projeto

| Mecanismo comum no mercado | Neste ciclo | Por quê |
|---|---|---|
| Escalonamento por **tempo** (SLA, lembrete, auto-escalação) | **fora de escopo** | Decisão N5/YAGNI. Exigiria agendador; o enunciado pede alçada **por valor**, não por prazo |
| Notificação por e-mail | fora de escopo | Dependência externa, nenhuma regra de alçada exercitada |
| Matriz DoA **editável em runtime** | fora de escopo (seed fixo) | Decisão N5/Admin. Traria a questão de retroatividade sobre pendências — interessante, mas é escopo de um v2 |
| Delegação **transitiva / multi-passo** | proibida (INV-3) | Decisão N3. Ciclos e auditoria degradada; a literatura RBAC trata como caso caro |
| Anexos, multi-moeda, integração ERP | fora de escopo | Decisão N5/YAGNI |
| Aprovação delegada na mesma trilha, com par ator/em-nome-de | **adotado** | Convergência entre OpenIAM, Workday e a prática de tokens `act`/`obo` |
| Fronteira inclusiva do limite (`valor ≤ limite`) | **adotado** | Nenhum produto pesquisado documenta a fronteira explicitamente; decisão do operador (INV-1) |
