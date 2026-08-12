# Resultados — esperado × obtido (Fase 7)

Confronto entre `criterios-aceitacao.md`, escrito na Fase 0 **antes de existir
código**, e o que a Fase 6 mediu.

## Critérios de sucesso

| id | Critério | Esperado | Obtido | |
|---|---|---|---|---|
| **CS-1** | Paridade com o legado | 26/26 linhas válidas, ±R$ 0,01 | **26/26**, divergência **zero** | ✅ |
| **CS-2** | Explicabilidade total | 0 traces vazios; toda candidata com motivo | 0 traces vazios; todo veredito com `MotivoCodigo` + detalhe | ✅ |
| **CS-3** | Validador pega as armadilhas | 13/13 | **13/13** — 6 rejeições (§C) + 6 coerência (§D) + R-06 (§C-bis) | ✅ |
| **CS-4** | Reprodutibilidade temporal | recálculo = preço registrado | igual quando as regras não mudam; **diverge corretamente** quando mudam | ✅ |
| **CS-5** | Latência | < 100 ms com ~1.000 regras | **11,21 ms** — folga de 9× | ✅ |

**A tolerância de R$ 0,01 nunca foi exercitada.** O fixture tem decimais
literais, então a igualdade sai exata. O caminho da tolerância existe e não tem
teste com divergência real — gap declarado, não coberto.

## Critérios de aceitação do operador (execução humana)

| # | Caso | Resultado |
|---|---|---|
| 1 | UC-2 importar pela UI | ✅ 33 regras, 6 rejeições nomeadas por linha |
| 2 | UC-3 publicar barrado por incoerência | ✅ barrou; e **falhou 11× por defeito da IA** antes de fechar (ver lições) |
| 3 | UC-4 ler por que a rival perdeu | ✅ |
| 4 | UC-5 registrado × recalculado | ✅ — veredito do operador sobre UX-03: **"está claro"** |
| 5 | UC-6 lacuna → preço base | ✅ exercitado sem intenção, comportamento correto de I-2 |

## Suíte automatizada

**86 testes, 100% verdes** — 79 pytest + 7 Playwright em Chromium real.
Ratio: 22 positivos / 12 negativos (1:1,8, acima do mínimo de 1:2).

## Defeitos reais encontrados no ciclo

Nenhum deles foi capturado pelas 4 rodadas de crítica (109 achados, 17 lentes):

| # | Defeito | Descoberto em |
|---|---|---|
| 1 | `precificar → Decisao` contradizia A-04 (motor leria o relógio) | ao escrever o tipo de retorno |
| 2 | A-06 "single-threaded, sem trava" era falsa — ASGI usa threadpool | 1ª requisição HTTP real |
| 3 | Mensagem de erro sem caminho de ação | operador repetindo 10× |
| 4 | **Trava de publicação volátil** — restart apagava o bloqueio | restart do servidor |
| 5 | Beco sem saída no conflito de preço base | operador tentando publicar |
| 6 | **Trava imortal** — iatrogênica, criada pelo conserto do nº 4 | operador, 11 tentativas |

Todos corrigidos, todos com teste de regressão. Os nº 4 e 6 são opostos e estão
presos pelas duas pontas: a trava sobrevive ao restart **e** cede quando deixa
de ter consequência. Consertar um sem o outro reintroduz o oposto.

## Pendências que vão para o ciclo 2

`V2-04` filtro na grade (UX-01 parcialmente resolvido) · `V2-05` correção no
local do preço base (dívida contra promessa escrita de U8/UX-02) · `V2-06`
CS-2 por amostragem, não exaustão · `V2-07` tolerância nunca exercitada ·
`V2-08` UX-04 verifica só rótulo · `V2-09` só Chromium.
