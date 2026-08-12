# Glossário de domínio — T21 certificados

Fase 0, HSA Nível 1. Termos com definição **operacional** (o que significa dentro
deste sistema), não definição de dicionário. Sinônimos proibidos marcados.

| Termo | Definição operacional neste sistema | Exemplo |
|---|---|---|
| **Certificado** | Certificado digital X.509 servido por um host em porta TLS. NÃO inclui certificado documental (treinamento, ISO, alvará) nem certificado não exposto em TLS (code signing, e-CNPJ em token). | o cert apresentado por `api.exemplo.com:443` |
| **Validade** | O par `notBefore`/`notAfter` do X.509 (RFC 5280 §4.1.2.5), sempre em UTC. | `notAfter=Sep 23 20:37:03 2026 GMT` |
| **Vida total** | `notAfter − notBefore`. Distinta de "restante". Um cert de 45 d de vida tem 45 d de vida no dia da emissão e no dia anterior ao vencimento. | 45.00 dias |
| **Restante** | `notAfter − agora(UTC)`. É o que os limiares comparam. | 12,3 dias |
| **Limiar** | Número de dias antes de `notAfter` que dispara um nível de alerta. Configurável. Inválido se `>=` vida total. | 30 dias |
| **Alvo de varredura** | Par `host:porta` cadastrado para inspeção periódica. É o que o operador cadastra — não o certificado. | `api.exemplo.com:443` |
| **Varredura** | Ato de conectar em todos os alvos, obter o certificado servido e atualizar o inventário. Única fonte de verdade do inventário. | execução das 03:00 |
| **Identidade do certificado** | `fingerprint` SHA-256 do DER. É como o sistema sabe que "o certificado mudou". Alternativa normativa: par (`issuer`, `serialNumber`). | `1B:C8:C7:...` |
| **Pedido** (de renovação) | Registro que abre o fluxo de governança para um alvo cujo certificado está vencendo. Estados: `pendente` → `aprovado` → `fechado`. | pedido #7 para `api.exemplo.com:443` |
| **Aprovação** | Ato de um **Aprovador autenticado** autorizar um pedido. Sem sessão autenticada não existe aprovação. Não confundir com "fechar o pedido". | Ana aprovou o pedido #7 |
| **Emissão** | Fato externo ao sistema: alguém obteve um certificado novo e o colocou no host. O sistema **não emite** — apenas comprova por varredura. | novo cert instalado no nginx |
| **Fechamento** | Transição automática do pedido quando a varredura encontra fingerprint diferente **com `notAfter` avançado**. É a prova da emissão. | pedido #7 fechado em 12/08 |
| **Escalado** | Estado de um alvo cujo nível crítico (30 d) passou **sem pedido aberto**. Exibido em destaque no painel. | `web.exemplo.com` escalado |
| **Trilha** | Sequência append-only de eventos, cada entrada carregando o hash da anterior. | cadeia de 431 entradas |
| **Tamper-evident** | Propriedade real da trilha: adulteração pontual é **detectável**. NÃO é tamper-proof — quem controla a máquina pode reescrever a cadeia inteira. | verificador retorna INVÁLIDA |
| **Papéis** | `Solicitante` (abre pedido), `Aprovador` (único que aprova), `Auditor` (só lê a trilha). Um mesmo humano pode ter mais de um papel nesta iteração. | Ana = Aprovadora |

## Sinônimos a NÃO usar (evitam ambiguidade nas fases seguintes)

- "expirado" ≠ "vencendo" ≠ "escalado" — são estados distintos.
- "renovação" (o fato externo) ≠ "pedido" (o registro interno).
- "monitorar" não implica "emitir" nem "instalar": o sistema observa e governa, não age no host.
- não usar "certificado" para se referir ao alvo `host:porta` — o alvo persiste, o certificado é substituído.
