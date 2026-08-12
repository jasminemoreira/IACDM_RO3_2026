# Remarcação cega — pacotes, respostas e o mapa

Este diretório é a evidência do teste de robustez do Resultado 1 e da estimativa de lentes.

| padrão | o que é |
|---|---|
| `T*-cego.md` | **o pacote entregue ao juiz** — matriz sem a coluna de lente, ids renomeados `F-01…`, ordem embaralhada por `sha256(taskId::id)`, marcações `duplica` removidas |
| `T*-mapa.json` | a tradução `F-nn → id real`. **Não é entregue ao juiz**; existe para a análise poder comparar |
| `T*-resposta.json` | resposta do juiz `qwen3.6:27b` local (Q4_K_M) |
| `T*-resposta-qwen3_6-27b.json` | resposta do `qwen3.6-27b` em precisão full, via DashScope |
| `T*-resposta-gpt-5_4-2026-03-05.json` | resposta do `gpt-5.4`, modelo pinado por data |
| `T*-reestimativa-V1-pacote.md` | pacote da estimativa de lentes, sobre a arquitetura **V(1)** |
| `T*-reestimativa-V1-<modelo>-r<n>.json` | estimativa, três rodadas por modelo e projeto |
| `EVIDENCIA-corrupcao-terminal-*` | saída crua que motivou trocar o CLI do Ollama pela API — ver o `LEIA` próprio |

O pacote de estimativa é **reproduzível byte a byte** a partir da V(1) congelada em
`specs/technical/architecture.md`. Verificado antes de acrescentar estimadores
retrospectivamente: não há informação futura vazando, o estimador vê a mesma arquitetura
que veria na época.
