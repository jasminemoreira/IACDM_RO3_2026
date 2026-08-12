# Limiares de renovação antecipada — parâmetros e suas fontes

Fase 0, HSA Nível 1. Cada valor abaixo é rastreável a `specs/references/normative-references.md`.
Data: 2026-08-09.

## Decisão do operador (P0)

Gatilho da renovação antecipada = **limiar de dias configurável** antes de `notAfter`.
Rejeitado nesta iteração: limiar por fração da vida útil.

## Parâmetros candidatos

| Parâmetro | Valor proposto | Fonte | Observação |
|---|---|---|---|
| Alerta nível 1 (aviso) | 90 dias antes de `notAfter` | R4 (NIST SP 1800-16) | válido só para certificados de vida > ~120 d |
| Alerta nível 2 (atenção) | 60 dias | R4 | idem |
| Alerta nível 3 (crítico) | 30 dias | R4; também o limiar fixo clássico de clientes ACME (R3) | |
| Escalação por inação | após o nível 3 sem ação | R4 | notificar responsável central |
| Validade máxima emitida hoje | 200 dias | R2 (SC-081v3, vigente desde 2026-03-15) | cai para 100 d em 2027-03-15 |
| Jitter de dispersão | 0–72 h | R3 (prática Shopify) | evita pico de renovações simultâneas |
| `notAfter` sentinela "sem expiração" | `99991231235959Z` | R1 (RFC 5280 §4.1.2.5) | não tratar como data real |

## O conflito normativo (ponto que a Fase 2 vai atacar)

R4 fixa 90/60/30 dias. R2 encolhe a vida máxima do certificado para 200 d (hoje),
100 d (2027) e 47 d (2029). Consequências aritméticas diretas:

| Vida do certificado | 90 d antes = | 30 d antes = | Situação |
|---|---|---|---|
| 398 d (regime antigo) | 77% da vida decorrida | 92% | 90/60/30 funciona |
| 200 d (hoje) | 55% | 85% | 90 d já é quase metade da vida |
| 100 d (2027) | limiar ≥ vida → alerta desde a emissão | 70% | nível 1 e 2 degeneram |
| 47 d (2029) | impossível | impossível (30 > 47 seria alerta imediato... 36% da vida) | 90/60 sem sentido |
| 45 d (Let's Encrypt, R3) | impossível | impossível | idem |

**Invariante que o sistema precisa garantir:** um limiar configurado só é válido se
`limiar < (notAfter − notBefore)`. Um limiar maior ou igual à vida total do
certificado gera alerta permanente desde a emissão — ruído que treina o operador a
ignorar o alerta, que é exatamente a falha que R4 quer evitar.

**Mitigação mínima compatível com a decisão do operador (dias fixos):** validar o
limiar contra a vida do certificado no momento do cadastro/varredura e sinalizar
configuração inválida, em vez de emitir alerta permanente em silêncio. Isso preserva
"dias configuráveis" sem herdar a fragilidade. A alternativa (fração da vida) fica
registrada como caminho rejeitado nesta iteração, com esta seção como justificativa
caso seja preciso reabrir.

## Fonte de tempo

`notBefore`/`notAfter` são UTC por norma (R1). Toda comparação de vencimento deve ser
feita em UTC, com a fonte de tempo injetada (não `now()` embutido) — sem isso o
comportamento de vencimento não é testável de forma determinística na Fase 6.
