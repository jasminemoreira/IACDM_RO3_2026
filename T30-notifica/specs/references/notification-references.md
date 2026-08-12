# Referências — T30 serviço de notificação

Bibliografia consultada na Fase 0. Toda decisão numérica em
`specs/technical/parameters.md` cita uma destas entradas.

## Normas e especificações (fonte primária)

| id | Título | URL | Usado para |
|----|--------|-----|-----------|
| R-01 | Standard Webhooks Specification | https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md | Contrato do canal webhook: headers, assinatura, idempotência, cronograma de retry |
| R-02 | RFC 8058 — Signaling One-Click Functionality for List Email Headers | https://www.rfc-editor.org/rfc/rfc8058 | Opt-out de e-mail: `List-Unsubscribe` + `List-Unsubscribe-Post` |
| R-03 | draft-ietf-httpapi-idempotency-key-header-07 — The Idempotency-Key HTTP Header Field | https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html | Chave de idempotência na API de ingestão; ciclo de vida e expiração são responsabilidade do recurso |
| R-04 | RFC 9110 §15.5.29 / RFC 6585 — 429 Too Many Requests, Retry-After | https://www.rfc-editor.org/rfc/rfc9110 | Semântica de resposta quando o teto de frequência é atingido |

## Engenharia (fonte secundária, autoral)

| id | Título | URL | Usado para |
|----|--------|-----|-----------|
| R-05 | Brooker, M. — *Exponential Backoff And Jitter*, AWS Architecture Blog | https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ | Fórmula de backoff do worker de entrega (Full Jitter) |
| R-06 | Richardson, C. — *Pattern: Transactional outbox*, microservices.io | https://microservices.io/patterns/data/transactional-outbox.html | Atomicidade entre persistir a notificação e enfileirar a entrega |
| R-07 | Stripe Engineering — *Scaling your API with rate limiters* | https://stripe.com/blog/rate-limiters | Escolha do algoritmo de teto de frequência (token bucket) |
| R-08 | Stripe Docs — *Receive Stripe events in your webhook endpoint* | https://docs.stripe.com/webhooks | Tolerância de timestamp na verificação de assinatura (padrão de mercado) |

## Estado da arte / concorrentes

| id | Título | URL | Usado para |
|----|--------|-----|-----------|
| R-09 | Courier — *How Top Platforms Handle Notification Quiet Hours & Delivery Windows* | https://www.courier.com/blog/quiet-hours-delivery-windows | Semântica de janela de silêncio: fila vs. descarte, exceção transacional, janela por canal |
| R-10 | Comparativo Novu × Knock × Courier (2026) | https://apiscout.dev/guides/novu-vs-knock-vs-courier-notification-api-2026 | Modelo de preferências por pessoa; ver `specs/competitors/landscape.md` |

## Lacunas conhecidas (assumidas, não pesquisadas)

- Não há norma pública que fixe **janela de deduplicação**. R-01 recomenda reter
  o `webhook-id` por 5 minutos no consumidor; adotamos isso como piso, não como
  verdade universal — ver PAR-05.
- Não há fonte que fixe **teto de frequência por pessoa**. É política de produto,
  não constante física. Registrado como premissa, não como parâmetro citado.
