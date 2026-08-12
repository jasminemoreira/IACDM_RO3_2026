# Ground truth — custo em nano por `usage` conhecido

Dados de referência usados pelos testes de CA-2 (exatidão contábil). Calculados
**à mão** a partir de `../technical/rate-card-llm.md` §1 e §2 — não extraídos do
código, sob pena de o teste validar a implementação contra ela mesma.

Todos os valores em nano-unidades monetárias (10⁻⁹ USD), aritmética inteira.

## D-1 — claude-opus-5, as quatro categorias

| categoria | tokens | nano/token | subtotal |
|---|---:|---:|---:|
| entrada | 1.000 | 5.000 | 5.000.000 |
| leitura de cache | 2.000 | 500 | 1.000.000 |
| escrita de cache 5m | 400 | 6.250 | 2.500.000 |
| saída | 300 | 25.000 | 7.500.000 |
| **total** | | | **16.000.000** |

Teste: `test_custo_quatro_categorias_exato`.

## D-2 — escrita de cache: 5 min vs 1 hora (mesmo `usage`)

| TTL | tokens | nano/token | total |
|---|---:|---:|---:|
| 5m (1,25×) | 1.000 | 6.250 | 6.250.000 |
| 1h (2,0×) | 1.000 | 10.000 | 10.000.000 |

O TTL vem da **requisição** (`cache_control.ttl`), nunca do `usage`.
Teste: `test_custo_cache_1h_e_16x_o_de_5m`.

## D-3 — vigência do preço promocional do Sonnet 5

| instante | entrada | saída |
|---|---:|---:|
| 2026-08-10 (promoção vigente) | 2.000 | 10.000 |
| 2026-09-01 (promoção encerrada) | 3.000 | 15.000 |

Teste: `test_preco_promocional_sonnet5_dentro_e_fora_da_vigencia`.

## D-4 — claude-haiku-4-5, verificação de que a aritmética é inteira

7 entrada + 3 leitura de cache + 1 escrita 5m + 11 saída
= 7×1.000 + 3×100 + 1×1.250 + 11×5.000 = **63.550** nano.

Teste: `test_aritmetica_e_inteira_sem_ponto_flutuante`.

## D-5 — reserva de pior caso (V(3))

Corpo de 94 bytes, `max_tokens` = 100, modelo claude-opus-5:
94 × 5.000 + 100 × 25.000 = **2.970.000** nano.

Teste: `test_pior_caso_inclui_prompt_e_saida`. Este é o número que apareceu na
execução real da Fase 5 e explicou por que `max_tokens=40` era negado com saldo
de 1.300.000: o custo do prompt consome 470.000 antes de qualquer token de saída.

## Lacuna

Não há ground truth de `usage` **real** do provedor — toda a suíte usa o upstream
simulado. Fechar isso exige uma chave real e é pré-requisito de CA-11 (premissa A8).
