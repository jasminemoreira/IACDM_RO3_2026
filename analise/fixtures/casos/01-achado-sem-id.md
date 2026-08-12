# coverage-matrix (fixture: 01-achado-sem-id)

Cinco colunas, mas a primeira não é um id. Separa este modo de falha do
`07-campo-faltando` — sem isso, remover o id removia junto uma coluna e os dois
casos disparavam o mesmo erro.

| id | módulo | lente | severidade | descrição |
|---|---|---|---|---|
| P-01 | quota | Assumptions | 🔴 | ok |
| — | quota | Security | 🔴 | primeira coluna sem id |
| R-01 | bucket | Resilience | 🟡 | ok |
