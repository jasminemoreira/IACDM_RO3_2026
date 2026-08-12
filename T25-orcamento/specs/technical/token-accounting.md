# Semântica de contagem de tokens, uso e limites de taxa

> **Fonte:** skill `claude-api` — `shared/token-counting.md`, `shared/prompt-caching.md`,
> `{lang}/claude-api/README.md` (§Verifying Cache Hits, §Stop Reasons),
> `shared/managed-agents-api-reference.md` (§Rate Limits), `shared/error-codes.md`.
> **Consultado em:** 2026-08-10.

## 1. O que a resposta reporta (campos de `usage`)

| Campo | Significado |
|---|---|
| `input_tokens` | tokens de entrada processados a preço cheio (o RESTO não-cacheado) |
| `cache_creation_input_tokens` | tokens escritos no cache nesta requisição (1.25× ou 2×) |
| `cache_read_input_tokens` | tokens servidos do cache nesta requisição (~0.1×) |
| `output_tokens` | tokens gerados |

**Armadilha documentada:** `input_tokens` NÃO é o tamanho do prompt. O prompt total é
`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. A doc alerta:
"se seu agente rodou por horas mas `input_tokens` mostra 4K, o resto veio do cache —
confira a soma, não o campo isolado". Um medidor de consumo que lê só `input_tokens`
subestima o volume e superestima a economia.

Fórmula de custo de uma requisição (moeda), com preços por 1M da rate card:

```
custo = (input_tokens            × preco_entrada
       + cache_read_tokens       × preco_entrada × 0.10
       + cache_creation_tokens   × preco_entrada × 1.25   # 2.00 se TTL=1h
       + output_tokens           × preco_saida) / 1_000_000
```

## 2. Contagem ANTES da chamada — e por que ela não basta

- Endpoint: `POST /v1/messages/count_tokens` (`client.messages.count_tokens(...)`).
  **A contagem é específica do modelo** — passa-se o mesmo `model` que será usado.
- ⚠️ **Não usar `tiktoken`.** É o tokenizador da OpenAI; subestima tokens Claude em
  ~15–20% em texto comum e muito mais em código ou texto não-inglês. Qualquer
  estimativa via `tiktoken`/`gpt-tokenizer` está errada para Claude
  (fonte: `shared/token-counting.md`, textual).
- O tokenizador **muda entre gerações**: Sonnet 5 produz ~30% mais tokens que
  Sonnet 4.6 para o mesmo texto; o tokenizador do Opus 4.7 gera ~1×–1.35× dos tokens
  do Opus 4.6. Contagens medidas num modelo não transferem para outro
  (fonte: `shared/model-migration.md`, seções de migração Sonnet 5 e Opus 4.7).

**Consequência crítica para T25:** `count_tokens` responde quantos tokens de ENTRADA a
requisição terá. Os tokens de **SAÍDA são desconhecidos até a resposta chegar** — e a
saída custa 5× a entrada na maioria dos modelos. Portanto:

> Não existe custo exato pré-chamada. Existe (a) um piso exato (entrada, via
> `count_tokens`) e (b) um teto de saída conhecido (`max_tokens`, que é um limite
> RÍGIDO imposto pela API).

Isso obriga o padrão **reserva → chamada → reconciliação**:

1. **Reserva (hold):** antes de chamar, debitar `custo_entrada_exato +
   max_tokens × preco_saida`. É o pior caso e é finito porque `max_tokens` é rígido.
2. **Chamada.**
3. **Reconciliação:** ao receber `usage`, substituir a reserva pelo custo real
   (sempre ≤ reserva) e devolver a diferença ao saldo.

Sem a reserva, N requisições concorrentes da mesma entidade passam todas pelo portão
com o mesmo saldo lido e estouram o teto em até N × (custo de uma requisição).

## 3. Streaming muda QUANDO o uso é conhecido

Em `stream: true`, o `usage` com `output_tokens` chega no evento `message_delta`, ao
final do stream (fonte: `{lang}/claude-api/streaming.md`, tabela de eventos). A
reconciliação é portanto assíncrona em relação ao início da resposta: a reserva fica
aberta durante toda a geração. Requisições longas mantêm reserva por minutos.

Além disso, respostas grandes exigem streaming: a skill recomenda `max_tokens ~16000`
para não-streaming (limite prático de timeout HTTP dos SDKs) e até 128K com streaming.

## 4. Motivos pelos quais uma resposta pode custar sem entregar valor

Estes casos precisam de política explícita de cobrança no T25 (o medidor não pode
assumir "resposta = sucesso"):

| `stop_reason` | Situação | Cobrança |
|---|---|---|
| `end_turn` | conclusão normal | normal |
| `max_tokens` | truncou no teto de saída | cobrado integralmente (saída gerada) |
| `refusal` | classificador recusou (HTTP 200, não é erro) | **recusa antes de qualquer saída não é cobrada — nem entrada nem saída, e não consome limite de taxa**; recusa no meio do stream cobra o parcial já transmitido (fonte: `shared/model-migration.md`, §refusal) |
| `pause_turn` | ferramenta server-side atingiu limite de iterações | cobrado; a retomada é outra requisição |
| `model_context_window_exceeded` | estourou a janela de contexto | cobrado |

## 5. Rate card é DADO, não código

Evidências acumuladas neste specs/ de que a tabela de preços é um dado versionado com
vigência, e não uma constante:

1. Preço promocional do Sonnet 5 com data de término explícita (2026-08-31).
2. Preço difere por provedor (Anthropic / Bedrock / Vertex / Foundry).
3. Modelos são aposentados e novos surgem (a própria skill lista modelos "Retired" e
   "Deprecated" com datas).
4. Multiplicadores (cache, batch, fast mode) alteram o preço efetivo do mesmo token.

→ Requisito derivado: o rate card é entidade de primeira classe com chave
(provedor, modelo, data de vigência) e o sistema deve falhar de forma explícita ao
encontrar um modelo sem preço conhecido (precedente: a própria API retorna 400 nesse
caso — ver `rate-card-llm.md` §4). Estimar preço de modelo desconhecido é AP7
(implementar sem referência).

## 6. Limites de taxa (rate limits) — dimensão ORTOGONAL ao orçamento

Fonte: `shared/managed-agents-api-reference.md` §Rate Limits, `shared/error-codes.md`.

- Limites são por organização e por modelo/família, em RPM (requisições/min),
  ITPM (tokens de entrada/min) e OTPM (tokens de saída/min).
- Ao exceder: HTTP **429** com corpo `rate_limit_error` e cabeçalho **`retry-after`**
  (segundos). Cabeçalhos `x-ratelimit-limit-*` e `x-ratelimit-remaining-*` informam a
  quota restante.
- Os SDKs oficiais já fazem retry automático de 408/409/429/5xx com backoff
  exponencial (`max_retries`, padrão 2).
- Modelos novos podem ter **pool separado**: "Claude Opus 5 não consome do pool
  combinado do Opus 4.x" (fonte: `shared/model-migration.md`).

**Distinção que o T25 precisa manter clara:** limite de taxa ≠ teto de orçamento.
Rate limit protege a plataforma e é temporal (por minuto, com retry). Teto de orçamento
protege o bolso e é acumulativo (por janela de faturamento, sem retry — só reset).
Um 429 é "tente de novo em N segundos"; um estouro de teto é "negado até o reset".
Confundir os dois produz retry storm contra um limite que nunca vai ceder.
