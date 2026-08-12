# Tabela de preços de APIs de LLM (rate card)

> **Fonte primária:** skill `claude-api` (bundle local `claude-api/SKILL.md`, seção
> "Current Models"), snapshot marcado como `cached: 2026-06-24`.
> **Fonte canônica ao vivo:** https://platform.claude.com/docs/en/pricing.md e
> https://platform.claude.com/docs/en/about-claude/models/overview.md
> **Consultado em:** 2026-08-10.
>
> ⚠️ Este arquivo é um SNAPSHOT. O sistema NÃO deve embutir estes números em código —
> ver decisão de design em `token-accounting.md` §5 (rate card é dado de configuração
> versionado, com data de vigência).

## 1. Preço por 1M tokens (Anthropic API first-party, USD)

| Modelo | ID exato | Contexto | Entrada $/1M | Saída $/1M |
|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | 1M | 10.00 | 50.00 |
| Claude Mythos 5 | `claude-mythos-5` | 1M | 10.00 | 50.00 |
| Claude Opus 5 | `claude-opus-5` | 1M | 5.00 | 25.00 |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | 5.00 | 25.00 |
| Claude Opus 4.7 | `claude-opus-4-7` | 1M | 5.00 | 25.00 |
| Claude Opus 4.6 | `claude-opus-4-6` | 1M | 5.00 | 25.00 |
| Claude Sonnet 5 | `claude-sonnet-5` | 1M | 3.00 (2.00 promocional) | 15.00 (10.00 promocional) |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | 3.00 | 15.00 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | 1.00 | 5.00 |

**Preço promocional do Sonnet 5 vigente até 2026-08-31** (fonte: mesma tabela).
Hoje é 2026-08-10 → o preço promocional está EM VIGOR. Isso é evidência empírica de
que preço tem **data de vigência** e o modelo de dados precisa suportá-la (ver
`token-accounting.md` §5).

**Preços de parceiro divergem:** Amazon Bedrock e Google Vertex AI são operados por
terceiros e têm preço próprio (fontes: https://aws.amazon.com/bedrock/pricing/ e
https://cloud.google.com/vertex-ai/generative-ai/pricing#claude-models). Microsoft
Foundry cobra as tarifas first-party acima. Consequência: o preço é função de
(provedor, modelo, data), não apenas de (modelo).

## 2. Multiplicadores que alteram o custo do MESMO token

Estes são a razão pela qual "custo = tokens × preço" está errado sem qualificação.

| Mecanismo | Multiplicador sobre o preço de entrada | Fonte |
|---|---|---|
| Leitura de cache (`cache_read_input_tokens`) | ~0.1× | skill `claude-api`, `shared/prompt-caching.md` §Economics |
| Escrita de cache, TTL 5 min (`cache_creation_input_tokens`) | 1.25× | idem |
| Escrita de cache, TTL 1 h | 2.00× | idem |
| Batch API (`/v1/messages/batches`) | 0.50× sobre entrada E saída | skill `claude-api`, `{lang}/claude-api/batches.md` |
| Fast mode (`speed: "fast"`, Opus 5 / 4.8) | preço fixo 10.00 / 50.00 por 1M | skill `claude-api`, §Fast Mode |

**Ponto de equilíbrio do cache** (fonte: `shared/prompt-caching.md`): TTL de 5 min
compensa a partir de 2 requisições (1.25× + 0.1× = 1.35× vs 2× sem cache); TTL de 1 h
exige ≥ 3 requisições (2× + 0.2× = 2.2× vs 3×).

## 3. Ferramentas server-side com preço próprio (não-token)

| Item | Preço | Fonte |
|---|---|---|
| Web search | USD 10.00 por 1.000 buscas | skill `claude-api`, `shared/managed-agents-core.md` §Session budgets |
| Code execution | USD 0.05/hora após 1.550 h/mês grátis por organização | skill `claude-api`, `shared/tool-use-concepts.md` §Code Execution |
| Tempo de sessão (Managed Agents) | USD 0.08/hora | `shared/managed-agents-core.md` §Session budgets |

**Consequência de escopo:** custo NÃO é puramente proporcional a tokens. Um teto
expresso em moeda que só soma tokens subestima o gasto real quando há ferramentas
server-side. Registrar como premissa explícita ou como item fora de escopo.

## 4. Precedente de arquitetura na própria plataforma

A Anthropic implementa o mesmo padrão que T25 vai construir, em Managed Agents
(fonte: `shared/managed-agents-core.md` §Session budgets). Vale como referência de
design e como validação de que o problema é real:

- O teto é declarado em **unidades menores da moeda, como string inteira**
  (`{"amount": "2500", "currency": "USD"}` = USD 25.00) — explicitamente "string em vez
  de número para que nenhum arredondamento de ponto flutuante seja aplicado".
- A verificação é um **portão pré-requisição**: antes de cada chamada ao modelo,
  compara-se o custo consumido com o teto. A requisição que cruza o teto **completa**.
  Logo o estouro máximo é de "uma requisição de modelo por thread em execução".
  A documentação diz textualmente: "trate o orçamento como um limite sobre trabalho
  NOVO, não como uma parada exata".
- O custo reportado é **arredondado ao centavo** enquanto a comparação usa valores
  exatos — por isso o sinal de parada é o `stop_reason`, nunca o número exibido.
- Ao atingir o teto a sessão **pausa** (não termina) e só aceita "settle events"
  (eventos que resolvem trabalho já em andamento). Retomar exige alterar/remover o teto.
- Modelo sem preço de tabela **não pode ser orçado** (erro 400) — um modelo sem rate
  card conhecido é um buraco no sistema de orçamento, não um caso degradado silencioso.

Estes cinco pontos são entrada direta para as Fases 1 e 2 de T25.
