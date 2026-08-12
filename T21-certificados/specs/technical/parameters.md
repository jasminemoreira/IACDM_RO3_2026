# Parâmetros numéricos e suas fontes — V(2)

Depositado na Fase 3, em resposta aos achados `SCI-01`, `SCI-02`, `IMP-04`,
`MEC-01`, `MEC-03`, `CTL-03` da matriz de cobertura.

Regra: **nenhum destes valores pode ser alterado na Fase 5 sem alterar esta tabela.**
Se um valor não tem fonte, isso está dito explicitamente — inventar uma citação seria
pior que admitir a ausência.

## Credencial (módulo `autorizacao`)

| Parâmetro | Valor | Fonte |
|---|---|---|
| KDF | scrypt | OWASP Password Storage Cheat Sheet — Argon2id é a primeira escolha; scrypt é o fallback recomendado quando Argon2id não está disponível. Node 24 não traz Argon2 embutido e o projeto proíbe dependência de runtime |
| N (custo CPU/memória) | 2¹⁷ = 131072 | OWASP: mínimo 2^17 |
| r (block size) | 8 | OWASP: mínimo 8 |
| p (paralelismo) | 1 | OWASP: 1 |
| salt | 16 bytes de `crypto.randomBytes` | RFC 9106 §4 recomenda salt de 16 bytes |
| keylen | 32 bytes | tamanho de saída equivalente a SHA-256 |
| comparação | `crypto.timingSafeEqual` | evita vazamento por tempo |

URL: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

⚠️ **Nota de implementação obrigatória:** com N=2¹⁷ e r=8 o scrypt precisa de
`128 × N × r ≈ 134 MB`. O default de `maxmem` do Node é 32 MB — `scryptSync` lançará
erro se `maxmem` não for elevado explicitamente. Isto não é ajuste de gosto: baixar N
para caber no default seria enfraquecer o parâmetro sem registrar, exatamente o que
AP7 proíbe.

## Sonda (módulo `sonda-tls`)

| Parâmetro | Valor | Fonte |
|---|---|---|
| timeout de handshake | **10 s** | Implementação de referência: `net/http.DefaultTransport` da biblioteca padrão do Go usa `TLSHandshakeTimeout: 10 * time.Second`. **Não existe fonte normativa** (RFC 8446 não define timeouts) — este é um valor de implementação madura adotado deliberadamente, não um número inventado |
| tamanho máximo da cadeia aceita | 10 certificados | limite defensivo contra `SEC-06`; sem fonte normativa, valor declarado por decisão de projeto |
| retentativas | 1 (uma retentativa, sem backoff) | resposta mínima a `RES-04`; mais que isso multiplicaria o tempo total da varredura sequencial |

URL: https://github.com/golang/go/blob/master/src/net/http/transport.go

## Classificação de vencimento (módulo `politica-limiar`)

| Parâmetro | Valor | Fonte |
|---|---|---|
| limiar aviso | 90 dias | NIST SP 1800-16 |
| limiar atenção | 60 dias | NIST SP 1800-16 |
| limiar crítico | 30 dias | NIST SP 1800-16 |
| unidade de comparação | dias inteiros por **truncamento** (`floor`) do restante em UTC | decisão de projeto — resolve `MEC-03` e `CTL-03`: a regra de arredondamento passa a ser determinística, e um alvo em 29,9 dias é `critico` sem ambiguidade nem oscilação entre varreduras |
| invariante | `limiar < (notAfter − notBefore)` | derivado de CA/B SC-081v3 vs NIST SP 1800-16 — ver `renewal-thresholds.md` |

## Ambiente (todos os módulos)

| Parâmetro | Valor | Fonte |
|---|---|---|
| faixa de Node suportada | `>=24.0.0 <25` | resposta a `MEC-01`: o projeto depende de `node:sqlite` (experimental) e de type-stripping nativo, ambos ligados à linha 24. Verificado em v24.13.1 |
| encoding do hash da trilha | hexadecimal minúsculo (`digest('hex')`) | resposta a `IMP-05`; escolha declarada para que duas implementações produzam a mesma cadeia |
| serialização canônica do evento | JSON com **chaves ordenadas** e datas em `toISOString()` UTC | resposta a `ASS-05`: sem canonicalização, a cadeia acusa adulteração inexistente e CA-4 vira falso-positivo |
