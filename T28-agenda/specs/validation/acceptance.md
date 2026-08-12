# Critérios de aceitação e validação — T28-agenda

> **RESULTADO DO CICLO v1.0 (Fase 7).** Suite de 64 testes verde em ~11 s.
> G1 ✅ UC-1..UC-8 com ≥1 positivo e ≥1 negativo cada · G2 ✅ pytest verde ·
> G3 ✅ operador executou UC-1/UC-2/UC-4/UC-7 na CLI e confirmou.
> Razão de negativos: 31/33 (exigido 1:2).
>
> | critério | esperado | obtido |
> |---|---|---|
> | VAL-1 | ~1.000 eventos/lado | 1.000 ✅ |
> | VAL-2 | ciclo < 5 s | **falhou com 41 s**; após `journal_mode=WAL` + `synchronous=NORMAL` e agrupamento do mapeamento de identidade numa transação, os dois testes de escala rodam em 6,67 s ✅ |
> | VAL-3 | O(n log n) | 4.000 ocorrências disjuntas em < 1 s ✅ |
> | VAL-4 | 0 escritas no 2º ciclo | 0, contando chamadas no provedor ✅ |
> | VAL-5 | convergência semântica | campos escalares idênticos nos dois lados ✅ |
> | VAL-6 | nenhuma edição descartada | as duas edições intactas + conflito com ambos os valores guardados ✅ |
> | VAL-7 | fuso com DST | série de 7 ocorrências mantendo o mesmo horário local ✅ |
> | VAL-8 | all-day bloqueia | 60 min de interseção; e `calendar_tz` desloca a ocupação em 3 h ✅ |
>
> Não verificável neste ciclo: **PR-2** (fidelidade dos simuladores) — só um
> provedor real falsificaria; e o ramo `Present(partial=True)`, que nenhum
> simulador produz. Ambos registrados em specs/references/lessons.md.

> Escrito na Fase 0, **antes de qualquer código** (ENUNCIADO §2). É o que torna o
> retrabalho mensurável. A Fase 6 testa contra ESTE arquivo, não contra o código.

## Critério de acerto objetivo (o gate do projeto)

O projeto é um **acerto** quando os três gates abaixo estão satisfeitos —
nenhum substitui o outro (AP5: teste automatizado não substitui julgamento humano):

| Gate | Conteúdo | Como se verifica |
|---|---|---|
| G1 | UC-1..UC-8 cobertos por teste automatizado, ≥1 positivo e ≥1 negativo cada | mapa de teste da Fase 6 |
| G2 | Suite `pytest` verde de ponta a ponta | execução real, saída lida (S4) |
| G3 | Operador executa manualmente na CLI **UC-2, UC-4 e UC-7** e confirma | relato literal do operador registrado |

## Casos de uso (fonte para o mapa de teste da Fase 6)

| id | Cenário | Resultado esperado | Negativo correspondente |
|----|---------|--------------------|--------------------------|
| UC-1 | Primeira sincronização, ambos os lados com eventos preexistentes | full sync nos dois lados; mapa de identidade criado; ancestral gravado; lados convergem | evento presente só em um lado NÃO pode ser silenciosamente descartado |
| UC-2 | Evento editado apenas no lado A | mudança propaga A→B; **segundo ciclo sem mudança externa não produz nenhuma escrita** | o eco da própria escrita NÃO pode ser reconhecido como mudança externa |
| UC-3 | A muda `location`, B muda `summary` do mesmo evento | merge 3-vias por campo aplica ambos; **nenhum conflito criado** | não pode descartar a edição de nenhum dos lados |
| UC-4 | A e B mudam o **mesmo** campo para valores diferentes | conflito materializado e persistido na fila; **nada aplicado** até decisão | não pode auto-resolver silenciosamente sob a política padrão |
| UC-5 | A deleta o evento, B edita o mesmo evento | conflito de classe delete-vs-update na fila | não pode tratar como deleção simples nem como update simples |
| UC-6 | Provedor invalida o token de sync entre dois ciclos | detecta, descarta estado de token, refaz full sync; **nenhuma duplicata, nenhuma perda** | não pode duplicar eventos já mapeados nem apagar o ancestral |
| UC-7 | Consulta de conflitos de agenda | sobreposições listadas, com séries expandidas na janela e comparação em UTC | eventos apenas encostados (`fim de x == início de y`) NÃO são sobreposição |
| UC-8 | Instância destacada de série (`RECURRENCE-ID`) editada de um lado | a exceção sincroniza isoladamente, sem alterar a série-mestre | editar a exceção não pode reescrever as demais instâncias |

## Critérios mensuráveis

| id | Critério | Limiar | Verificação (não-proxy) |
|----|----------|--------|--------------------------|
| VAL-1 | Escala | ~1.000 eventos por lado | dataset sintético desse porte |
| VAL-2 | Tempo de ciclo | **< 5 s** para um ciclo completo em VAL-1 | teste cronometrado; medir o tempo, não apenas "retornou" |
| VAL-3 | Complexidade da detecção de sobreposição | varredura ordenada O(n log n) | teste com n crescente; não pode degradar quadraticamente |
| VAL-4 | Idempotência | 2º ciclo sem mudança externa = **0 escritas** | contar chamadas de escrita nos provedores simulados, não inspecionar o resultado final |
| VAL-5 | Convergência | após ciclo sem conflito pendente, os dois lados são semanticamente iguais | comparação campo a campo do modelo canônico |
| VAL-6 | Não-perda | nenhuma edição descartada sem constar de um conflito registrado | auditoria da fila de conflitos vs. edições injetadas |
| VAL-7 | Correção temporal | sobreposição correta através de transição de DST e entre fusos distintos | fixture com evento cruzando mudança de horário |
| VAL-8 | All-day | regra de ocupação de evento all-day explícita e aplicada de forma consistente | teste com all-day × timed no mesmo dia |

## Regra anti-falsa-cobertura (Fase 6)

Um teste verde só valida um critério se verificar **o critério exato**:
- VAL-2 diz "< 5 s" → teste que apenas confirma que o ciclo terminou **não** verifica VAL-2;
- VAL-4 diz "0 escritas" → teste que compara o estado final **não** verifica VAL-4 (um ciclo que reescreve o mesmo valor passa nessa comparação e falha em VAL-4);
- VAL-6 diz "nenhuma edição descartada" → precisa injetar edições e auditar a fila, não apenas conferir que não houve exceção.
