# Critérios de aceitação — T30

Escritos na Fase 0, **antes de qualquer código**, conforme exigência do
`ENUNCIADO.md`. É o que torna o retrabalho mensurável. A Fase 6 constrói o Test
Map contra este arquivo, não contra a implementação.

## Critério de acerto objetivo (barra de aprovação)

O projeto é aprovado se e somente se os quatro forem verdadeiros:

| id | Critério | Como se verifica | Verificação |
|----|----------|------------------|-------------|
| AC-1 | Os 8 casos de uso UC-1..UC-8 executáveis ponta a ponta contra o serviço em execução | `curl` na API + CLI + caixa do SMTP local + log do receptor de webhook | Human-AV (Fase 6, teste manual) |
| AC-2 | Suite automatizada verde, ≥1 positivo e ≥1 negativo por UC, razão mínima 1 neg : 2 pos | `node --test` | Automated-AV |
| AC-3 | Os 4 motivos de supressão distinguíveis via CLI para uma notificação específica | `t30 explain <notification-id>` retorna `opt_out` / `quiet_hours` / `rate_limited` / `duplicate` | Human-AV + teste |
| AC-4 | **Durabilidade:** matar o processo com entrega pendente e ela retomar após reiniciar | `kill -9` durante retry ⇒ reiniciar ⇒ entrega conclui | Human-AV + teste |

## Critérios por caso de uso

| UC | Critério verificável | Parâmetro governante |
|----|---------------------|---------------------|
| UC-1 | Uma notificação para pessoa com e-mail+webhook ativos produz exatamente 2 entregas, uma por canal | — |
| UC-2 | POST às 02:00 no fuso da pessoa ⇒ status `deferred`, entrega ocorre às 08:00 no fuso dela, **não** no do servidor | PAR-14, PAR-15 |
| UC-3 | Após opt-out em `marketing`, notificação de `marketing` ⇒ `suppressed(opt_out)`; notificação de `security` ⇒ entregue | — |
| UC-4 | Duas notificações com a mesma chave de dedup em <5 min ⇒ 1 entrega, a 2ª com `suppressed(duplicate)` | PAR-05 |
| UC-5 | 15 notificações em 1 h ⇒ 10 entregues, 5 com `suppressed(rate_limited)` | PAR-11, PAR-12 |
| UC-6 | Destino retornando 500 ⇒ tentativas seguem `random(0, min(24h, 5s·2^n))`, no máx. 5, depois dead-letter | PAR-01..04, PAR-09 |
| UC-7 | Notificação transacional para pessoa com opt-out, às 03:00, acima do teto ⇒ **entregue**. A mesma repetida com a mesma chave de dedup ⇒ **suprimida** | invariante 2 |
| UC-8 | Para qualquer notificação, a CLI informa: estado, motivo da supressão (se houver) e histórico de tentativas | AC-3 |

## Casos de borda que DEVEM ter teste negativo

| id | Caso de borda | Por quê |
|----|---------------|---------|
| EDGE-1 | Janela de silêncio 22:00–08:00 **cruzando a meia-noite** | RSK-03 — o erro clássico é `hora >= 22 && hora < 8`, que nunca é verdadeiro |
| EDGE-2 | Pessoa sem fuso horário definido | Invariante 4 exige o fuso da pessoa; a ausência precisa de comportamento declarado, não de crash |
| EDGE-3 | URL de webhook inválida ou host inexistente | Distinguir falha permanente (não retentar) de transitória (retentar) |
| EDGE-4 | Timeout do destino (PAR-10, 10 s) | Timeout é falha transitória, não permanente |
| EDGE-5 | Preferência ausente para a categoria | Invariante 3: ausência ≠ opt-out, resolve pelo padrão da categoria |
| EDGE-6 | Mesma `Idempotency-Key` reenviada | Não cria segunda notificação (R-03); distinto de dedup por chave lógica |
| EDGE-7 | Notificação transacional duplicada | Invariante 2: transacional ignora tudo, **menos** deduplicação |
| EDGE-8 | Assinatura de webhook com timestamp fora da tolerância de 300 s | PAR-06 — proteção contra replay |

## Atualização para V(3) — estados terminais diferem por canal (achado PRO-07 🟡)

A crítica adversarial apontou que este arquivo descrevia o comportamento de V(1).
Correções, sem mudança de escopo — os UCs e a barra AC-1..AC-4 continuam valendo:

| Onde | Antes (V1) | Agora (V3) |
|---|---|---|
| UC-1 | "exatamente 2 entregas" | Exatamente 2 entregas, com **estados terminais distintos**: `email → sent` (submetido ao provedor; bounce é assíncrono e não é observável na entrega) e `webhook → delivered` (2xx confirmado, PAR-09) |
| UC-6 | "após 5 tentativas → dead-letter" | Idem, mas `attempts` é incrementado **na reivindicação**: um processo morto durante a tentativa consome uma tentativa. O teste de AC-4 deve contar isso |
| UC-5 | "5 suprimidas com `rate_limited`" | Idem, e o motivo agora carrega o parâmetro aplicado: `rate_limited(cap=10/1h)` |
| UC-3 | opt-out avaliado no ingresso | Opt-out é reavaliado **também na entrega**: uma entrega adiada pela madrugada não sai se a pessoa descadastrar antes de a janela abrir |
| UC-7 | transacional declarado pelo emissor | Transacional vem do **catálogo de categorias** (operador). O emissor informa só a categoria |
| UC-8 | `explain <id>` | Mais `explain --recipient <id> --since <t>` e, no relato da supressão, o valor do parâmetro vigente |

### Casos de borda acrescentados pela crítica

| id | Caso de borda | Achado de origem |
|----|---------------|------------------|
| EDGE-9 | Processo morre entre a reivindicação e o resultado ⇒ a entrega volta a ser devida após o lease (PAR-20) e **não** reprocessa infinitamente | RES-06 🔴 |
| EDGE-10 | Envio que ultrapassa PAR-10 é abortado; a entrega nunca é reivindicada em duplicidade enquanto o primeiro envio está em voo | RES-05 🔴 |
| EDGE-11 | Escrita de resultado com fencing token vencido é rejeitada | RES-05 🔴 |
| EDGE-12 | URL de webhook que resolve para IP privado, e URL pública que responde 302 para IP privado | SEC-10, SEC-11 🟡 |
| EDGE-13 | Dois emissores com a mesma `Idempotency-Key` não colidem | SEC-08 🟡 |
| EDGE-14 | Entrega que falhou E entrou em janela de silêncio: prevalece `max(nextAttempt, deferUntil)` | PRO-05 🟡 |

## RESULTADOS OBTIDOS (Fase 7 — esperado × obtido)

| Critério | Esperado | Obtido | |
|---|---|---|---|
| AC-1 | 8 UCs executáveis ponta a ponta | 8/8 cobertos por teste automatizado **e** executados manualmente pelo operador, que confirmou o funcionamento | ✅ |
| AC-2 | Suite verde, ≥1 positivo e ≥1 negativo por UC, razão ≥1:2 | 53 testes, 53 verdes, 0 falhas em 4,9 s. **30 negativos / 23 positivos = 1,30** | ✅ |
| AC-3 | 4 motivos distinguíveis na CLI | `opt_out`, `duplicate`, `rate_limited` (com `cap=10/1h`) e `quiet_hours` (no histórico de tentativas) | ✅ |
| AC-4 | Matar o processo com entrega pendente e ela retomar | `SIGKILL` em processo separado após a reivindicação: entrega retomou ao expirar o lease, concluiu com `attempts=2` e chegou **uma única vez** ao destino | ✅ |
| UC-5 (número exato) | 15 emitidas → 10 entregues, 5 suprimidas | 10 e 5, com `suppressedDetail = cap=10/1h` | ✅ |
| Faixa de módulos | 8–12 | 12 | ✅ |
| Parâmetros com procedência | nenhum número sem `PAR-xx` | 26 constantes, todas com o id no nome do símbolo | ✅ |

**Falhas durante a construção da suite:** 4, todas defeito **do teste**, nenhuma do código de produção — dobra de header RFC 5322, encoding quoted-printable, *unsettled top-level await* somado a listener de `exit` tardio, e ordenação temporal entre ingestão e tick. Cada uma teve a causa nomeada antes da execução seguinte.

**Lacuna que permanece:** EDGE-14 (precedência `max(nextAttempt, deferUntil)`) está implementada e **não** provada — o cenário exige backoff maior que a abertura da janela, o que não ocorre naturalmente com esperas de até ~80 s.

## Fora da barra (não são critério de aceitação)

- Desempenho sob carga (não há requisito de throughput no enunciado).
- Cobertura de código percentual — o que se mede é cobertura de *spec* (Fase 6,
  Step 4), não de linha.
- Entrega por SMS/push, digest, feed in-app — fora de escopo declarado.
