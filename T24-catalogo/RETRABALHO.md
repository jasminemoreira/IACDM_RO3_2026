# RETRABALHO — T24-catalogo

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-09** |

CA-0 a CA-23, os 6 casos de uso e as 4 bordas, congelados na Fase 0 antes de codar, foram
verificados na Fase 6: 56 testes automatizados, 56 passando, com a saída da suíte
efetivamente lida (S4). Teste manual executado e **julgado pelo operador**: *"Testei e
está bom"*. Veredito da Fase 7: *"Atende — requisitos cumpridos"*, **sem nenhuma pendência
apontada para um v2** — diferente do T21, que nomeou duas dívidas de granularidade.

Meta-iteração oferecida e recusada; o ciclo encerra em v1.0.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### O S7 pegou um defeito que a suíte não pegaria

A micro-checagem adversarial da Fase 5 pergunta *"onde esta implementação DIVERGE de
`specs/`?"* — não *"está bom?"*. A diferença de formulação produziu o achado:

`--json` estava declarada só no parser principal, antes do `add_subparsers`. O argparse
exige que argumentos do parser principal venham **antes** do subcomando, então
`t24 procedencia financeiro.conciliacao --json` falha com *"unrecognized arguments"*
enquanto `t24 --json procedencia ...` funciona. **A ordem que o usuário escreve
naturalmente é a que quebra.**

Vale para o corpus por dois motivos. Primeiro, é o instrumento funcionando: uma pergunta
formulada em modo generativo achou o que uma pergunta de confirmação não acharia — é o
antídoto de AP1 operando. Segundo, o registro conecta o defeito à lente que o previa:
*"é exatamente a classe de atrito que a lente UI/UX existe para pegar — o achado UX-04 já
apontava inconsistência de interface na CLI"*.

### Um teste errado, e desta vez verificado antes de concluir

`test_violacoes_agregadas_em_uma_execucao` esperava ≥3 violações e recebeu 1. A causa: a
agregação é **por estágio**, e o estágio de forma porteia o semântico. A fixture planta um
defeito de forma e dois semânticos; havendo qualquer defeito de forma, `carregar` aborta
(resolução LING-05) e os semânticos nunca são avaliados.

O contraste com o T21 é o que interessa. Lá, o primeiro diagnóstico corrigiu o sintoma e o
teste falhou de novo. Aqui o registro traz a verificação **antes** da conclusão —
*"POR QUE O CÓDIGO ESTÁ CERTO E O TESTE ESTAVA ERRADO — verifiquei antes de concluir:
(a) `catalog_mapper` acessa `bruto['dono']` diretamente, e só pode fazê-lo porque
`yaml_loader` já garantiu…"*.

Dois projetos, mesma classe de erro (teste que monta o cenário errado), condutas
diferentes. Um caso não sustenta tendência; registro para comparar quando houver mais.

### Duas correções de arquitetura declaradas na entrada da Fase 5

Ciclo de importação entre `model` e `validation` (a V(3) alocava `LoadedCatalog` em
`model`, mas ele recebe `list[Violation]`, que vive em `validation`). Corrigido movendo
`LoadedCatalog` para `validation`, com o princípio já adotado na V(3) como justificativa
— *"quem valida é quem certifica"*.

O registro é explícito sobre a forma: *"registradas antes de codar em vez de desviadas em
silêncio"*. É o comportamento que a metodologia pede quando a Fase 5 descobre que a
arquitetura aprovada não fecha.

### Procedência do teste manual — diferente do T21

Aqui o roteiro foi **apresentado antes** e o **operador executou e julgou**, com
confirmação literal *"Testei e está bom"*. As 5 perguntas de julgamento humano (se as
mensagens dizem o que fazer e não só o que está errado; se o agrupamento por dono responde
à pergunta real) foram respondidas por pessoa.

No T21 o agente executou a pedido do operador, e as perguntas de julgamento ficaram
declaradamente em aberto. **Este projeto tem human-AV no sentido do AP5; o T21 não tinha.**
A diferença precisa constar de qualquer comparação entre os dois.
