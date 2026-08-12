# Arquitetura — fixture sintético

Base compartilhada por todos os casos. Três módulos, forma da Fase 1 (v0.12.2).

| id | módulo | responsabilidade | interface | depende-de |
|---|---|---|---|---|
| M-01 | quota | contabiliza consumo por chave | `consume(key, n)` | store |
| M-02 | bucket | token bucket com recarga | `allow(key)` | quota |
| M-03 | backoff | calcula espera na recusa | `delay(attempt)` | — |

## Premissas
- Relógio monotônico disponível.
