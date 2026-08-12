# coverage-matrix (fixture: 00-valido)

| id | módulo | lente | severidade | descrição |
|---|---|---|---|---|
| P-01 | quota | Assumptions | 🔴 | assume relógio monotônico; salto de NTP zera a janela |
| S-01 | quota | Security | 🔴 | chave vem do header sem validação — spoof de identidade |
| R-01 | bucket | Resilience | 🟡 | store indisponível → allow() falha aberto, sem degradação |
| C-01 | bucket | Control Engineering | 🟡 | recarga sem amortecimento oscila sob carga pulsada |
| R-02 | backoff | Resilience | 🔴 | backoff sem jitter sincroniza os clientes — retry storm |
| O-01 | backoff | Observability / Operability | 🟢 | sem métrica de recusa por chave |
| A-01 | quota | Architectural | 🟡 | duplica: P-01 — mesmo defeito de relógio, visto pelo acoplamento ao store |
| N-01 | bucket | NENHUMA | 🟡 | custo de licença do store não cabe em nenhuma lente do conjunto |
