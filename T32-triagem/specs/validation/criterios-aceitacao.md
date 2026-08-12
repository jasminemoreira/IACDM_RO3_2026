# Critérios de aceitação — T32-triagem

Escritos na Fase 0, **antes de qualquer código** (exigência do ENUNCIADO.md:
"critério de acerto objetivo, escrito antes de codar... é o que torna o
retrabalho mensurável"). A Fase 6 testa contra este arquivo, não contra a
implementação.

## Critério de acerto (CA) — a condição de vitória do projeto

Todos os três devem valer. Qualquer um falhando, o projeto errou.

### CA-1 — A matriz está correta nas 9 células

As 9 combinações (impacto, urgência) produzem **exatamente** a prioridade de
`specs/technical/matriz-prioridade.md`. Nenhuma célula divergente, nenhuma
célula ausente.

Verificação: teste tabular sobre as 9 entradas do ground truth em
`specs/datasets/ground-truth-matriz.md`.

### CA-2 — Recurso provido tem efeito material

Um recurso com desfecho PROVIDO recalcula a prioridade **e** reconta os prazos
desde a abertura do chamado. Se a nova meta já foi ultrapassada, o chamado
passa a constar como **violado** — este resultado é correto, não é bug.

Verificação: teste de fluxo com relógio controlado, comparando prazos antes e
depois do provimento.

### CA-3 — A trilha reconstrói toda mudança de prioridade

Para todo chamado, a sequência de eventos da trilha permite reconstruir cada
mudança de prioridade com ator, instante, valor antes, valor depois e motivo.
**Nenhuma mudança de prioridade sem evento correspondente.**

Verificação: teste que altera prioridade por todos os caminhos possíveis
(triagem, reclassificação, provimento de recurso) e confere que a contagem de
eventos de mudança bate com a contagem de mudanças efetivas.

### CA-negativo — a falha silenciosa que invalida tudo

Se em **qualquer** caminho de código a prioridade for gravada por escrita
direta em vez de derivada da matriz, o projeto falhou — ainda que os três
critérios acima passem. Prioridade digitada é o defeito que esvazia o recurso
(não se contesta a derivação, contesta-se o humor do agente) e é justamente a
divergência consciente deste projeto em relação aos quatro concorrentes.

Verificação: inspeção mais teste de que não existe caminho de API que aceite
prioridade como entrada.

## Critérios de aceitação por caso de uso

| ID | Critério | Como se mede |
|---|---|---|
| VAL-1 | Chamado aberto nasce NÃO TRIADO, sem prioridade e sem prazo | Estado e campos nulos após UC-1 |
| VAL-2 | Triagem calcula prioridade pela matriz e prazos a partir de `aberto_em` | Prazos = aberto_em + meta(P), não triado_em + meta(P) |
| VAL-3 | Reclassificação recalcula prioridade e reconta prazos desde a abertura | Comparação antes/depois com relógio controlado |
| VAL-4 | Reclassificação que não altera a prioridade ainda registra evento na trilha | Trilha cresce mesmo com P inalterada |
| VAL-5 | Só o solicitante do próprio chamado pode recorrer | Tentativa de terceiro é recusada |
| VAL-6 | Recurso só é admitido após a triagem | Recurso em chamado não triado é recusado |
| VAL-7 | Máximo 1 recurso por chamado | Segundo recurso é recusado |
| VAL-8 | Recurso após 48 h úteis da triagem é inadmitido por prescrição | Relógio avançado além do prazo; recusa por prescrição, distinta de outras recusas |
| VAL-9 | Agente não pode julgar recurso; só o Gestor | Tentativa do agente é recusada |
| VAL-10 | Julgamento exige fundamentação não vazia | Julgamento sem fundamentação é recusado |
| VAL-11 | Recurso IMPROVIDO não altera prioridade nem prazos, mas registra trilha | Estado do chamado idêntico; trilha cresce |
| VAL-12 | Provimento pode resultar em chamado já violado | Cenário de borda do ground truth |
| VAL-13 | A fila ordena por prioridade e destaca violações | Ordenação verificada sobre seed conhecido |
| VAL-14 | Nenhum módulo lê o relógio do sistema diretamente | Testes determinísticos com relógio controlado passam sem espera real |
| VAL-15 | A prioridade não é aceita como entrada em nenhum endpoint | Tentativa de enviar prioridade é ignorada ou recusada |
| VAL-16 | A trilha do chamado é visível para os três papéis, com ator, instante, antes/depois e motivo | UC-6 executado por solicitante, agente e gestor |
| VAL-17 | Categoria filtra a fila e é reclassificável, sem rotear para ninguém | Filtro aplicado; reclassificação de categoria registra trilha |
| VAL-18 | Todos os prazos são horas corridas — não há calendário de negócio | Prazo de P4 = abertura + 120 h, inclusive atravessando fim de semana |

## UC-6 — Consultar a trilha (derivado da resolução da ambiguidade 3)

Qualquer um dos três papéis abre o chamado e lê o histórico completo de
classificação: cada mudança com ator, instante, valor antes, valor depois e
motivo. Sem assimetria de informação — o solicitante vê o mesmo que o gestor.
É o que torna a classificação contestável na prática: não se recorre do que
não se pode ler.

## Fora de escopo (YAGNI) — item e razão

| Item | Razão de não fazer |
|---|---|
| Autenticação com senha | Problema resolvido e ortogonal ao que o projeto investiga; consumiria 2–3 dos 8–12 módulos. A **autorização** por papel permanece no escopo e é testada |
| Atendimento técnico (diagnóstico, notas, base de conhecimento, atribuição a técnico) | O enunciado é sobre classificar, não sobre resolver |
| Notificações (e-mail, push) | Exigiria integração externa, contrariando a decisão de nó único autocontido |
| Reabertura e pesquisa de satisfação | Pós-encerramento; fora do par reclassificação/recurso |
| Segunda instância de recurso | Diferença de grau, não de natureza; duplicaria estados, prazos e telas |
| Relatórios e dashboards analíticos | A trilha já sustenta a consulta; visualização é v2 |
| Internacionalização e acessibilidade avançada | Sem operadores estrangeiros no cenário; contraste e navegação por teclado permanecem |

---

# Resultados obtidos — Fase 7 (esperado × obtido)

Suíte: **68 testes verdes** (51 domínio + 17 API), 468 ms, relógio controlado.
Verificação de tipos limpa. Verificados por mutação em 3 pontos críticos.

| Critério | Esperado | Obtido |
|---|---|---|
| CA-1 | 9 células conforme a matriz de referência | ✅ 9/9 tabulares + metas por célula + totalidade, monotonicidade e simetria como propriedades |
| CA-2 | provimento reconta desde a abertura | ✅ testado contra **os dois** valores possíveis; GT-2 e GT-3 reproduzidos, incluindo o chamado que nasce violado |
| CA-3 | trilha reconstrói toda mudança de prioridade | ✅ 3 mudanças, 3 eventos, com ator, instante, antes/depois, motivo, origem e versão da política |
| CA-negativo | prioridade nunca aceita como entrada | ✅ 400 em abertura, triagem e reclassificação; e o tipo com marca impede fabricá-la no código |
| VAL-1..VAL-18 | todos verificáveis | ✅ todos cobertos (VAL-12 e VAL-15 por testes que os contêm integralmente) |
| B-1..B-12 | todos os casos de borda | ✅ 12/12, com a fronteira da prescrição testada nos dois lados |

## Defeitos encontrados após o código pronto — e por quem

| # | Defeito | Encontrado por |
|---|---|---|
| 1 | Rotas GET de formulário sem checagem de papel | inspeção minha |
| 2 | `additionalProperties: false` apagava em silêncio (Fastify/AJV `removeAdditional`) | requisição real minha |
| 3 | Botões Reconhecer/Encerrar em chamado não triado; sem botão Triar | **operador**, teste manual |
| 4 | Confusão de autoria por troca de sessão entre abas | **operador**, teste manual |

Os 68 testes automatizados encontraram **zero** defeitos que o humano já não
tivesse encontrado. O humano encontrou **dois** que nem as 18 lentes de crítica
nem a suíte alcançaram — ambos de interação no tempo, classe que exige um ator
externo com sessão própria.
