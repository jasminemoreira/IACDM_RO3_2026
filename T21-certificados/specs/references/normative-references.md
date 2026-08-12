# Referências normativas — monitor de validade de certificados X.509

Depositado na Fase 0 (HSA Nível 1), pesquisa autorizada pelo operador.
Data da coleta: **2026-08-09**. Toda afirmação numérica abaixo tem fonte citada.

Regra vinculante para a Fase 5: **nenhum parâmetro numérico entra no código sem
uma linha desta tabela (ou de `specs/technical/`) como fonte.** Antídoto AP7.

---

## R1 — RFC 5280: Internet X.509 PKI Certificate and CRL Profile

- URL: https://www.rfc-editor.org/rfc/rfc5280
- Campo de validade: `Validity ::= SEQUENCE { notBefore Time, notAfter Time }` (§4.1.2.5).
- `Time` é `UTCTime` (anos 1950–2049, formato `YYMMDDHHMMSSZ`) ou `GeneralizedTime`
  (≥2050, `YYYYMMDDHHMMSSZ`). **Sempre em UTC (Zulu).**
- Certificados sem data de expiração conhecida usam `notAfter = 99991231235959Z`
  (GeneralizedTime, §4.1.2.5). Um monitor deve tratar esse valor como "não expira",
  não como "expira no ano 9999".
- Identidade do certificado para deduplicação/inventário: par
  (`issuer` DN, `serialNumber`) é único por CA (§4.1.2.2). O SHA-256 do DER
  (fingerprint) é o identificador global usual na prática.
- Nomes DNS cobertos: extensão `subjectAltName` (§4.2.1.6). O `CN` do subject é
  **legado** — não usar como fonte de verdade de hostname.

## R2 — CA/Browser Forum, Ballot SC-081v3 (aprovado abril/2025)

- URL: https://cabforum.org/2025/04/11/ballot-sc081v3-introduce-schedule-of-reducing-validity-and-data-reuse-periods/
- Cronograma de redução da validade máxima de certificados TLS publicamente confiáveis:

  | A partir de | Validade máxima |
  |---|---|
  | 2025-03-15 (vigente até) | 398 dias |
  | **2026-03-15** | **200 dias** ← vigente hoje (2026-08-09) |
  | 2027-03-15 | 100 dias |
  | 2029-03-15 | 47 dias |

- Confirmação secundária: https://www.digicert.com/blog/tls-certificate-lifetimes-will-officially-reduce-to-47-days
  e https://www.sectigo.com/blog/200-day-ssl-certificate-expiration-risk
- **Consequência de design:** a vida útil dos certificados encolhe ~8× em 3 anos.
  Qualquer limiar expresso em *dias fixos* que hoje é razoável se torna maior que a
  própria vida do certificado no futuro. Ver `specs/technical/renewal-thresholds.md`.

## R3 — RFC 9773: ACME Renewal Information (ARI)

- URL da publicação: https://letsencrypt.org/2025/09/16/ari-rfc
- Caso de uso em produção: https://letsencrypt.org/2026/03/17/acme-renewal-information-ari
- A CA expõe um endpoint `renewalInfo` que devolve
  `"suggestedWindow": { "start": <ts>, "end": <ts> }` — a janela em que a CA quer
  que aquele certificado específico seja renovado.
- Algoritmo recomendado (não obrigatório): **escolher um instante aleatório uniforme
  dentro da janela sugerida**. Serve para dispersar carga e para reagir a revogação
  em massa (a CA encolhe a janela e o cliente renova cedo).
- Let's Encrypt isenta de rate limit as renovações feitas dentro da janela ARI.
- Prática relatada (Shopify): substituíram limiar fixo de **30 dias** por consulta
  ao ARI; antes usavam jitter aleatório de **0–72 h** para dispersar renovações.
- Let's Encrypt está migrando para certificados de **45 dias**.
- **Consequência de design:** existe uma fonte autoritativa por-certificado para
  "quando renovar". Um limiar local é uma aproximação dela — legítima, mas é uma
  *decisão*, e deve ser registrada como tal.

## R4 — NIST SP 1800-16: Securing Web Transactions — TLS Server Certificate Management

- URL: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1800-16.pdf
- Volume B (guia): https://www.nccoe.nist.gov/publication/1800-16/VolB/
- Práticas recomendadas relevantes a este projeto:
  1. **Inventário central único** de todos os certificados TLS do estado.
  2. **Notificação escalonada antes do vencimento: 90, 60 e 30 dias.**
  3. Se nenhuma ação for tomada após os alertas, **escalar automaticamente** para um
     time/responsável central de conformidade.
  4. Monitorar o inventário para expiração, operação correta e problemas de segurança;
     alertar quando houver desvio do estado normal estabelecido.
  5. Renovação **proativa**, antes do vencimento, como estratégia declarada — a
     motivação explícita é evitar interrupção de serviço.
- **Consequência de design:** 90/60/30 é a referência citável para o escalonamento
  de alertas, e a escalação por inação é requisito normativo, não enfeite.

---

## Lacuna conhecida (registrar como ambiguidade da Fase 0)

R4 (90/60/30 dias) foi escrito no regime de certificados de 398 dias. Sob R2, a
validade máxima hoje é 200 dias e cai para 47 em 2029. Aplicar 90/60/30 literalmente
a um certificado de 47 dias significa alertar antes mesmo de ele existir. As duas
fontes normativas **não são conciliáveis por dias fixos** — a reconciliação é uma
decisão de projeto, não um fato pesquisável. Ver `specs/technical/renewal-thresholds.md`.
