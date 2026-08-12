# Verificação de viabilidade técnica — Nível 4 da HSA

**Lição da metodologia:** viabilidade da plataforma-alvo é VERIFICADA, não
assumida. Tudo abaixo foi executado nesta máquina em 2026-08-11, não inferido.

## Ambiente medido

```
node   v24.13.1
npm    11.8.0
```

## Mecanismos fundamentais × suporte da plataforma

| Mecanismo necessário | Essencial? | Suporte | Evidência |
|---|---|---|---|
| Servidor HTTP (ingestão + preferências) | ESSENCIAL | ✅ | `node:http` embutido |
| Persistência transacional (outbox, R-06) | ESSENCIAL | ✅ | `node:sqlite` embutido expõe `DatabaseSync`, `StatementSync`, `Session`, `backup`. Emite `ExperimentalWarning` — ver risco RSK-01. Alternativa madura disponível: `better-sqlite3@13.0.3` |
| HMAC-SHA256 para assinatura de webhook (PAR-07) | ESSENCIAL | ✅ | `node:crypto.createHmac('sha256',…).digest('base64')` executado com sucesso |
| Conversão de fuso IANA por pessoa (PAR-14, invariante 4) | ESSENCIAL | ✅ | ICU completo: `2026-08-11T23:30Z` → `20:30` em `America/Sao_Paulo`; `Asia/Tokyo` 08, `America/New_York` 19, `Europe/Lisbon` 00 |
| Envio SMTP real | ESSENCIAL | ✅ | `nodemailer@9.0.5` disponível no registry (`npm ping` PONG 229 ms) |
| Servidor SMTP local para receber e inspecionar (provider local) | ESSENCIAL | ✅ | `smtp-server@3.19.3` disponível |
| Receptor HTTP local para o canal webhook | ESSENCIAL | ✅ | `node:http` embutido — nenhuma dependência |
| Executor de testes | ESSENCIAL | ✅ | `node:test` embutido (`typeof test === 'function'`) |
| Agendamento de entrega adiada (janela de silêncio) | ESSENCIAL | ✅ | Timers do runtime + estado durável em SQLite. Não exige cron externo |

## Veredito

**Nenhuma capacidade essencial ausente. Sem BLOQUEADOR técnico.**

Capacidades DESEJÁVEIS ausentes (não bloqueiam):
- Concorrência real de múltiplos workers com `SELECT … FOR UPDATE SKIP LOCKED`
  (exigiria PostgreSQL). Com SQLite o worker é único — registrado como premissa
  arquitetural, não como defeito escondido.

## Riscos técnicos identificados

| id | Risco | Mitigação |
|----|-------|-----------|
| RSK-01 | `node:sqlite` é marcado experimental no Node 24 e "might change at any time" | A porta de persistência isola o driver. Trocar por `better-sqlite3` é mudança de adaptador, não de arquitetura. Decisão final do driver fica na Fase 1. |
| RSK-02 | Worker único ⇒ sem paralelismo de entrega | Aceitável no porte alvo. A premissa vai explícita na Fase 1 (pergunta 3: Premissas) para a lente de Performance atacar na Fase 2. |
| RSK-03 | Janela de silêncio 22:00–08:00 (PAR-14) **cruza a meia-noite** | É o caso de borda clássico de comparação de intervalos. Vai como caso de teste negativo obrigatório na Fase 6, não como detalhe de implementação. |
