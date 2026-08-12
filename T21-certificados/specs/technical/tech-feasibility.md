# Viabilidade técnica — verificação empírica (Fase 0, HSA Nível 4)

Executado em 2026-08-09 na máquina alvo. **Nada aqui foi assumido: cada linha foi
provada com um comando cujo resultado está transcrito.** Lição da metodologia:
viabilidade da plataforma se verifica, não se supõe.

## Ambiente medido

| Componente | Versão | Comando |
|---|---|---|
| Node.js | v24.13.1 | `node --version` |
| Python | 3.12.1 | `python3 --version` |
| OpenSSL | 3.6.1 (27 Jan 2026) | `openssl version` |
| SQLite (CLI) | 3.41.2 | `sqlite3 --version` |
| Go | **ausente** | `go version` → not found |

## Mecanismos fundamentais — ESSENCIAL vs DESEJÁVEL

| # | Mecanismo | Necessidade | Verificado? | Evidência |
|---|---|---|---|---|
| 1 | Obter o certificado servido por um host via handshake TLS | ESSENCIAL | ✅ | `openssl s_client -connect` devolveu subject, issuer, serial, notBefore/notAfter, SHA-256 fingerprint e SAN de um servidor de teste |
| 2 | Parsear campos X.509 no runtime (sem shell-out) | ESSENCIAL | ✅ | `tls.TLSSocket.prototype.getPeerX509Certificate` = function; `crypto.X509Certificate` expõe subject, issuer, serialNumber, validFrom/To, **validFromDate/validToDate como `Date` real**, fingerprint256, subjectAltName |
| 3 | Inspecionar certificado INVÁLIDO/expirado | ESSENCIAL | ✅ | `rejectUnauthorized:false` em `tls.connect` e `-connect` do s_client expõem o certificado mesmo sem cadeia confiável — um monitor de vencimento precisa ver justamente os ruins |
| 4 | Persistência local transacional | ESSENCIAL | ⚠️ | `node:sqlite` (`DatabaseSync`) funciona, **mas emite `ExperimentalWarning: SQLite is an experimental feature and might change at any time`** |
| 5 | Hash para cadeia de auditoria | ESSENCIAL | ✅ | `crypto.createHash` = function |
| 6 | KDF de senha + comparação em tempo constante | ESSENCIAL | ✅ | `crypto.scryptSync` = function; `crypto.timingSafeEqual` = function |
| 7 | Comparação de vencimento determinística em UTC | ESSENCIAL | ✅ | `validToDate` é `Date`; `toISOString()` em UTC. Vida total calculada corretamente: certificado de teste emitido com `-days 45` → **45.00 dias** medidos |
| 8 | Gerar certificados de teste com validade controlada | ESSENCIAL (Fase 6) | ✅ | `openssl req -x509 -days N` produziu certificado com `notAfter` exatamente N dias à frente e SAN múltiplo |
| 9 | Servidor TLS local para varrer em teste | ESSENCIAL (Fase 6) | ✅ | `openssl s_server -accept` aceitou conexão e serviu o certificado |

**Nenhuma capacidade ESSENCIAL está ausente → sem BLOQUEADOR de plataforma.**

## Ressalva única (item 4) — decisão a tomar na Fase 1

`node:sqlite` é embutido (zero dependências) porém **experimental**: a API pode mudar
entre versões menores do Node. Três saídas, a decidir na Fase 1:

| Opção | Custo | Risco |
|---|---|---|
| `node:sqlite` embutido | zero dependências | API experimental pode quebrar em upgrade do Node |
| `better-sqlite3` (lib madura, S6 Tier 1) | 1 dependência nativa, requer build | baixo; API estável |
| Arquivo JSONL append-only | zero dependências, casa com a trilha append-only | sem transação nem consulta; concorrência por conta da aplicação |

## Não verificado de propósito

Varredura de host **remoto real** na internet: não testada (a máquina pode estar sem
saída, e o produto é local). Modos de falha de rede — timeout, DNS inexistente, porta
fechada, host que fala TLS mas não responde — são exatamente o material da lente
**Resiliência** na Fase 2, e devem virar casos de teste na Fase 6, não suposição aqui.
