# Fontes consultadas — T25

Registro de proveniência. Regra do projeto (S6/AP7): **nenhum parâmetro numérico entra
no código sem uma linha aqui**.

## Consultado em 2026-08-10 (Fase 0, iteração 1)

| # | Fonte | Tipo | O que forneceu | Depositado em |
|---|---|---|---|---|
| F1 | Skill `claude-api` (bundle local `/tmp/claude-1000/bundled-skills/2.1.226/.../claude-api/`), seção "Current Models", snapshot `cached: 2026-06-24` | Documentação de fornecedor (local) | Tabela de preços por 1M tokens, janelas de contexto, IDs de modelo | `technical/rate-card-llm.md` §1 |
| F2 | `claude-api/shared/prompt-caching.md` | Documentação de fornecedor | Multiplicadores de cache (0.1× leitura, 1.25× escrita 5min, 2× escrita 1h), pontos de equilíbrio, campos `usage` de cache | `technical/rate-card-llm.md` §2, `technical/token-accounting.md` §1 |
| F3 | `claude-api/shared/token-counting.md` | Documentação de fornecedor | Endpoint `count_tokens`, especificidade por modelo, proibição do `tiktoken` (erro de 15–20%) | `technical/token-accounting.md` §2 |
| F4 | `claude-api/shared/model-migration.md` | Documentação de fornecedor | Variação de tokenizador entre gerações (~30% Sonnet 4.6→5; 1×–1.35× Opus 4.6→4.7), semântica de `stop_reason: refusal` e sua cobrança, pools de rate limit separados | `technical/token-accounting.md` §2, §4, §6 |
| F5 | `claude-api/shared/managed-agents-core.md`, §"Session budgets" | Documentação de fornecedor | **Precedente arquitetural direto**: teto em minor units como string, portão pré-requisição, overshoot de até 1 requisição por thread, pausa vs terminação, 400 para modelo sem preço | `technical/rate-card-llm.md` §4 |
| F6 | `claude-api/shared/managed-agents-api-reference.md` §Rate Limits; `claude-api/shared/error-codes.md` | Documentação de fornecedor | HTTP 429, cabeçalho `retry-after`, `x-ratelimit-*`, retry automático dos SDKs | `technical/token-accounting.md` §6 |
| F7 | `claude-api/{lang}/claude-api/batches.md` e SKILL.md §Batch | Documentação de fornecedor | Batch API a 50% do preço padrão | `technical/rate-card-llm.md` §2 |
| F8 | `claude-api/shared/tool-use-concepts.md` | Documentação de fornecedor | Preço de code execution (0.05 USD/h após 1.550 h/mês grátis) | `technical/rate-card-llm.md` §3 |

## Fontes canônicas ao vivo (não consultadas na primeira rodada de pesquisa)

Registradas para verificação futura e para a Fase 7 (atualização de specs). O snapshot
local (F1) é de 2026-06-24; se a Fase 5 depender de um preço com mais de ~2 meses,
revalidar contra a página de preços antes de codar.

- Preços: https://platform.claude.com/docs/en/pricing.md
- Catálogo de modelos: https://platform.claude.com/docs/en/about-claude/models/overview.md
- Limites de taxa: https://platform.claude.com/docs/en/api/rate-limits.md
- Contagem de tokens: https://platform.claude.com/docs/en/build-with-claude/token-counting.md
- Cache de prompt: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Preço de parceiros: https://aws.amazon.com/bedrock/pricing/ ·
  https://cloud.google.com/vertex-ai/generative-ai/pricing#claude-models

## Lacunas conhecidas (a fechar antes da Fase 5)

| Lacuna | Impacto | Onde resolver |
|---|---|---|
| Preços de provedores não-Anthropic (OpenAI, Google, etc.) | Se o gateway for multi-provedor, cada um precisa de rate card citado | Depende da decisão de escopo do Nível 3 |
| `specs/competitors/` vazio | Estado da arte não analisado (LiteLLM, Helicone, Portkey, OpenRouter são candidatos óbvios) | Nível 1 — pendente |
| `specs/datasets/` vazio | Fase 6 precisa de ground truth: pares (usage, custo esperado) | Fase 6, ou geração sintética a partir do rate card |
