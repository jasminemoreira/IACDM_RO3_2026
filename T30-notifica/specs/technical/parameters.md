# Parâmetros numéricos — T30

Regra da metodologia (S6/AP7): **nenhum parâmetro numérico no código sem fonte
citada aqui.** Ids `R-xx` remetem a `specs/references/notification-references.md`.
Parâmetros sem fonte externa estão marcados como POLÍTICA — são decisão de
produto, e a honestidade exigida é declará-los como tal, não inventar citação.

| id | Parâmetro | Valor | Fonte | Observação |
|----|-----------|-------|-------|-----------|
| PAR-01 | Fórmula de backoff entre tentativas | `sleep = random(0, min(cap, base * 2^tentativa))` (Full Jitter) | R-05 | O artigo compara Full/Equal/Decorrelated Jitter; Full Jitter faz o menor trabalho total e produz a menor carga no destino. É o padrão recomendado. |
| PAR-02 | `base` do backoff | 5 s | R-01 | Primeira espera do cronograma exemplo da Standard Webhooks: imediato → 5 s → 5 min → 30 min → 2 h → 5 h → 10 h → 14 h → 20 h → 24 h. |
| PAR-03 | `cap` do backoff | 24 h | R-01 | Último degrau do mesmo cronograma. |
| PAR-04 | Máx. de tentativas de entrega | 5 | R-01 (adaptado) | O cronograma de R-01 tem ~9 tentativas ao longo de 75 h. Reduzido a 5 por causa do timebox de sessão única — DESVIO CONSCIENTE da fonte, registrado aqui em vez de escondido. |
| PAR-05 | Janela de deduplicação | 5 min (padrão, configurável) | R-01 | "save the IDs in redis for 5 minutes" — recomendação da spec para a chave de idempotência do consumidor. Adotado como padrão do lado emissor. |
| PAR-06 | Tolerância de timestamp na assinatura do webhook | 300 s (5 min) | R-08, R-01 | R-01 exige tolerância mas não fixa valor; 300 s é o padrão das bibliotecas Stripe e o de facto do mercado. |
| PAR-07 | Algoritmo de assinatura do webhook | HMAC-SHA256, prefixo `v1` | R-01 | Conteúdo assinado literalmente: `msg_id.timestamp.payload`. Assinatura em Base64. |
| PAR-08 | Headers obrigatórios do webhook | `webhook-id`, `webhook-timestamp`, `webhook-signature` | R-01 | `webhook-timestamp` = unix inteiro em segundos. `webhook-signature` = lista separada por espaço. |
| PAR-09 | Critério de sucesso da entrega webhook | HTTP 2xx (200–299) | R-01 | Citação literal: "considered successful if it was responded to with a 2xx status code... a failure in any other scenario". |
| PAR-10 | Timeout de requisição do webhook | 10 s | POLÍTICA | Sem fonte normativa. Escolhido para que o timeout seja exercitável em teste dentro da sessão. |
| PAR-11 | Algoritmo do teto de frequência | Token bucket | R-07 | Stripe e AWS usam token bucket; semântica ("quantos tokens restam?") é diretamente inspecionável, ao contrário de GCRA, o que importa para depurar e para explicar a supressão ao usuário. |
| PAR-12 | Teto de frequência padrão por pessoa | 10 notificações / 1 h | POLÍTICA | Sem fonte normativa — é política de produto. Configurável por pessoa e por categoria. |
| PAR-13 | Código de resposta ao exceder o teto na API de ingestão | 429 + `Retry-After` | R-04 | Aplica-se ao rate limit da API pública, não à supressão por preferência (que retorna sucesso com status `suppressed`). |
| PAR-14 | Janela de silêncio padrão | 22:00–08:00 no fuso da pessoa | POLÍTICA | Sem fonte normativa; R-09 confirma apenas que a modelagem correta é por fuso da pessoa, não do servidor. |
| PAR-15 | Ação sobre notificação em janela de silêncio | Enfileirar até a janela abrir (não descartar) | R-09 | Courier, Customer.io, Knock e Novu enfileiram; Braze oferece as duas opções. Descarte silencioso é minoria e perde informação. |
| PAR-16 | Prazo para efetivar opt-out de e-mail | 48 h | R-02 | Exigência do RFC 8058 para o fluxo one-click. Nosso alvo é efetivar de forma síncrona, folgadamente dentro do prazo. |
| PAR-17 | Headers de opt-out em e-mail | `List-Unsubscribe` (URI HTTPS) + `List-Unsubscribe-Post: List-Unsubscribe=One-Click` | R-02 | O valor do segundo header é literal e não admite variação. |

## Parâmetros introduzidos em V(2) (Fase 3)

Todos nascidos de achados da crítica adversarial. Nenhum tem norma pública que o
fixe — todos marcados POLÍTICA, pelo mesmo critério de honestidade dos anteriores.

| id | Parâmetro | Valor | Fonte | Achado que o originou |
|----|-----------|-------|-------|----------------------|
| PAR-18 | Retenção de notificações e entregas terminais | 90 dias | POLÍTICA | SUS-01, PERF-02, REG-03 |
| PAR-19 | Envios em voo simultâneos no laço único | 8 | POLÍTICA | PERF-01 |
| PAR-20 | Duração do lease de reivindicação | 60 s | POLÍTICA | RES-01, ASS-01 |
| PAR-21 | Validade do token de unsubscribe | 30 dias | POLÍTICA — R-02 exige efetivar em 48 h, não fixa validade do link | SEC-02 |
| PAR-22 | SQLite: modo WAL + `busy_timeout` | WAL, 5000 ms | POLÍTICA (prática documentada do SQLite) | RES-04 |
| PAR-23 | Limiar de alarme para idade da entrega mais velha | 15 min | POLÍTICA | CTL-01, OBS-01 |
| PAR-24 | Intervalo do laço (`tick`) | 1 s | POLÍTICA | MEC-03 |
| PAR-25 | Dispersão na reabertura da janela de silêncio | uniforme 0–5 min | Deriva de R-05 (mesma ideia de jitter aplicada à reprogramação) | CTL-03 |
| PAR-26 | Tamanho máximo do payload de uma notificação | 64 KB | POLÍTICA | SEC-06 |

Nota sobre PAR-12 (teto): V(2) declara a recarga como **contínua e preguiçosa**
(proporcional ao tempo decorrido), não por hora fechada — a ambiguidade que
SCI-01 apontou.

## Decisões finais (Fase 7) — o que a implementação confirmou ou ajustou

| id | Situação após implementar e testar |
|----|-----------------------------------|
| PAR-01/02/03 | Confirmados por teste: 200 amostras por nível de tentativa, todas em `[0, min(cap, base·2ⁿ))`. O expoente é `attempts - 1`, porque `attempts` passou a ser incrementado na reivindicação |
| PAR-04 | Confirmado: dead-letter em exatamente 5 tentativas, e a entrega deixa de ser reivindicada depois |
| PAR-05 | Confirmado; a 2ª notificação com a mesma chave devolve `original=<id>` |
| PAR-06/07/08 | Confirmados: HMAC conferido byte a byte contra o esperado, e o timestamp provado em SEGUNDOS (a conversão de ms→s tem teste próprio) |
| PAR-10 | Ajustado em uso: além do timeout do socket, o worker aborta o envio por `AbortSignal` — é essa trava que mantém a posse da entrega muito abaixo do lease e fecha RES-05 |
| PAR-12 | Confirmado com o número exato de UC-5: 15 emitidas → 10 entregues, 5 `rate_limited`. A recarga é contínua e preguiçosa, e satura em zero se o relógio retroceder |
| PAR-14 | Confirmado, incluindo as bordas: 22:00 inclusivo, 08:00 exclusivo, e a janela cruzando a meia-noite |
| PAR-17 | Confirmado, com uma decisão nova: os headers acompanham só mensagens que a pessoa PODE recusar. Categoria transacional não os leva |
| PAR-18 | Precedência final: `categories.retention_days` sobrepõe o padrão global |
| PAR-19/20 | Relação declarada: o lote de reivindicação nunca excede a concorrência em voo, para que nenhuma entrega espere com o lease correndo |
| PAR-21 | O "uso único" foi abandonado — descadastrar é idempotente; sobraram escopo e validade |
| PAR-22 | Ativação tolerante: se o sistema de arquivos não suportar WAL, cai para o journal padrão em vez de derrubar o processo |
| PAR-25 | Limitado a `min(PAR-25, 10% da janela)` para não empurrar a entrega para fora de uma janela curta |
| PAR-26 | Confirmado com teste negativo |

**Algoritmos descartados e por quê** (para não serem re-propostos num v2.0):
Equal Jitter e Decorrelated Jitter (R-05) — Full Jitter faz menos trabalho total e
gera menos carga no destino. GCRA (R-07) — "quantos tokens restam?" não é pergunta
direta em GCRA, e a CLI de UC-8 precisa responder isso. PostgreSQL — traria
`SKIP LOCKED`, mas o paralelismo já era escopo negativo e a dependência de infra
externa foi recusada na Fase 0. Tabela `outbox` separada de `deliveries` —
duplicaria a mesma linha com o mesmo ciclo de vida.

## Desvios conscientes das fontes

1. **PAR-04 (5 tentativas em vez de ~9):** o cronograma completo de R-01 cobre
   75 h, o que não é observável numa sessão de 2–4 h. Mantemos a *forma* (Full
   Jitter, base 5 s, cap 24 h) e encurtamos a *cauda*. Registrado, não escondido.
2. **Janela de silêncio por canal:** R-09 aponta que janela por canal é rara
   (só Braze e Knock). Modelamos janela por pessoa, opcionalmente sobrescrita por
   canal — a estrutura suporta, o padrão é global.
