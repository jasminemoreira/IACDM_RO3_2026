# Concorrentes / estado da arte — coordenadores canário

Analisado na Fase 0. Serve para (a) não reinventar mecanismo já resolvido
(S6 Tier 1/2) e (b) delimitar o que este projeto **não** vai fazer.

| Ferramenta | Substrato | Divisão de tráfego | Decisão | Rollback |
|---|---|---|---|---|
| **Argo Rollouts** | Kubernetes (CRD `Rollout`) | Service mesh / ingress (Istio, SMI, ALB, NGINX) | `AnalysisTemplate` com expressões `successCondition` / `failureCondition` sobre provedores de métrica | Aborta, devolve peso do canário a **zero**, marca `Degraded` |
| **Flagger** | Kubernetes (CRD `Canary`) | Service mesh / ingress | Verificações periódicas; contador de falhas até `threshold` | Roteia tudo para a primária, escala canário a zero, marca falho |
| **Spinnaker + Kayenta** | Multi-nuvem | Fora do Kayenta (o Kayenta só julga) | **Mann-Whitney U**, 98% de confiança, score ponderado vs. limiares marginal/pass | Decisão devolvida ao pipeline do Spinnaker, que executa |

## O que se aprende da comparação

**1. Julgar e agir são responsabilidades separadas.** O Kayenta é literalmente um
serviço que só julga — recebe séries temporais, devolve um score. Quem executa o
rollback é o Spinnaker. Argo e Flagger acoplam as duas coisas. A separação é a
escolha mais defensável: permite testar o julgamento sem mover tráfego, o que
neste projeto (substrato simulado) é a diferença entre um teste determinístico e
um teste que depende de efeito colateral.

**2. Existem duas escolas de decisão, e elas não são intercambiáveis.**
- *Baseada em regra* (Argo, Flagger): expressão booleana sobre a métrica,
  contador de falhas, limiar. Simples, auditável, explicável ao operador.
- *Baseada em estatística* (Kayenta): teste de hipótese entre duas distribuições,
  score agregado. Robusta a ruído comum às duas versões, mas exige amostra
  (≥50 pontos, R-03) e é mais difícil de explicar quando reprova.

A decisão `SINAL DE DECISÃO` deste projeto (comparação concorrente canário vs.
estável) aponta para a segunda escola. O custo dessa escolha é a amostra mínima,
e a amostra mínima colide com a janela de sessão — está registrado como conflito
aberto em `specs/technical/canary-decision-parameters.md` §6.

**3. Todas as três param o avanço antes de reverter.** Uma verificação falha
detém a promoção; só o acúmulo dispara o rollback (R-07 explicitamente). Um
coordenador com apenas dois estados — "promovendo" e "revertido" — não consegue
representar "suspeito, aguardando mais evidência", e vai reverter com um único
ponto ruim.

**4. Nenhuma delas trata o erro de coleta como métrica ruim.** Argo separa
`failure` (total) de `error` (consecutivo, com padrão 4 e reset ao recuperar).
Kayenta tem `Nodata` como classe própria, excluída do denominador do score. Um
coordenador que trate "não consegui medir" como "mediu mal" reverte por queda do
provedor de métricas.

## Delimitação (insumo para o Out of Scope do Nível 5)

Este projeto **não** é um concorrente dessas ferramentas. As três dependem de
Kubernetes real, service mesh real e provedor de métricas real — exatamente o que
a decisão `SUBSTRATO DE EXECUÇÃO` colocou fora. O que se herda delas é o
**modelo de decisão**, não a implantação: máquina de estados de promoção,
separação julgar/agir, separação falha/erro, e os parâmetros com fonte.
