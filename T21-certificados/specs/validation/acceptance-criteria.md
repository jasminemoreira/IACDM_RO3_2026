# Critérios de aceitação — T21 certificados

Fase 0, HSA Nível 5. **Escritos antes de qualquer linha de código**, conforme o
enunciado congelado (`ENUNCIADO.md`: "critério de acerto objetivo, escrito antes de
codar" — é o que torna o retrabalho mensurável).

O produto é APROVADO se e somente se **os 5 critérios forem verdadeiros**. Cada um é
binário, verificável por teste automatizado e independente de julgamento estético.

| id | Critério | Como se verifica | Fonte |
|---|---|---|---|
| **CA-1** | A varredura classifica corretamente 5 certificados nos estados `OK`, `aviso-90d`, `atenção-60d`, `crítico-30d`, `expirado` | fixtures geradas com `openssl req -x509 -days N` para N escolhido em cada faixa; comparar estado calculado × estado esperado | R4 (NIST SP 1800-16: 90/60/30) |
| **CA-2** | Um pedido de renovação NÃO sai de `pendente` sem Aprovador autenticado; o ator autenticado fica gravado na trilha | tentativa de aprovar sem sessão → recusada; com sessão → aprovado e trilha contém o identificador do ator | enunciado ("quem aprovou cada emissão") |
| **CA-3** | Trocar o certificado servido pelo host faz a varredura seguinte **fechar o pedido automaticamente**, anexando fingerprint/serial/`notAfter` novos como evidência | servidor TLS local passa a servir um segundo certificado; rodar varredura; pedido deve transitar para `fechado` com evidência | R1 (identidade do cert = issuer+serial; fingerprint SHA-256) |
| **CA-4** | A verificação da trilha retorna **VÁLIDA** na cadeia intacta e **INVÁLIDA** após adulteração de 1 registro | executar verificador sobre a trilha; alterar um registro; reexecutar | requisito de trilha tamper-evident |
| **CA-5** | Limiar configurado `>=` vida total do certificado é **rejeitado como configuração inválida** | configurar limiar de 90 d contra certificado de 45 d → erro de configuração, não alerta permanente | R2 + R4 (ver `technical/renewal-thresholds.md`) |
| **CA-6** | Certificado novo detectado **sem pedido aprovado** gera evento `troca não autorizada` na trilha e destaque no painel — não fecha nada silenciosamente | trocar o cert do host de teste **sem** abrir/aprovar pedido; rodar varredura; verificar o evento na trilha e o destaque no painel | resolve a premissa A3 (ver decisão "AMBIGUIDADES DA ITERAÇÃO 1") |

**CA-6 é o critério que protege a razão de existir do produto.** Sem ele, contornar a
aprovação sai mais barato do que passar por ela, e o sistema registraria sucesso onde
houve burla — um monitor que dá cobertura à falha que deveria expor.

---

## RESULTADOS OBTIDOS (Fase 7 — esperado × obtido)

Execução final: **68 testes, 68 PASS, 0 FAIL**; `tsc --noEmit` com 0 erros.

| id | Esperado | Obtido | |
|---|---|---|---|
| CA-1 | classificação correta nos 5 estados | 8 testes contra fixture real de 200 d com relógio fixado em `notAfter − N`; mais `ainda-nao-valido` e truncamento (29,9 d → `critico`) | ✅ |
| CA-2 | pedido não sai de pendente sem Aprovador; ator gravado | auditor e solicitante recusados com `papel-insuficiente`; aprovação grava `aprovadorId`; dupla aprovação recusada | ✅ |
| CA-3 | troca do cert fecha o pedido com evidência | integração com servidor TLS real: pedido → `fechado`, `evidenciaId` preenchido, `pedido-fechado` na trilha com fingerprint e `notAfter` | ✅ |
| CA-4 | VÁLIDA intacta / INVÁLIDA após adulterar 1 registro | ambos, mais remoção e reordenação de entrada quebrando a cadeia, e o índice exato da quebra | ✅ |
| CA-5 | limiar ≥ vida total rejeitado | verificado em três camadas: função pura, cadastro/alteração e estado derivado exibido no painel como "config inválida" | ✅ |
| CA-6 | troca sem aprovação detectada e registrada | evento na trilha, badge no painel e contador permanente; justificar não zera o contador | ✅ |

**Defeito encontrado pela própria verificação (S7, Fase 5):** `CA-5` **não** estava garantido na
primeira implementação — `cadastrarAlvo` validava contra `Infinity` por não haver certificado
observado ainda, e nada revalidava depois da varredura. Um limiar de 90 dias sobre certificado
de 45 passava em silêncio. Corrigido movendo a validação para o estado derivado.

**Defeitos encontrados pelo teste exploratório (Fase 6):** mensagens de erro vazando código
interno (`alvo-duplicado`) e, pior, **perda de informação** — `rejeitar sem motivo` devolvia
`transicao-invalida` porque a camada de aplicação colapsava todo erro de transição num tipo só,
descartando a causa que o domínio já conhecia. Corrigido e coberto por regressão.

## O que NÃO é critério de aprovação (decisão explícita)

Limites de rede — host inalcançável, DNS inexistente, timeout, porta fechada — **não**
entram na barra de aceitação desta iteração. Permanecem como caso de teste desejável
na Fase 6 e como material da lente **Resiliência** na Fase 2. Registrado assim para
que, se a Fase 2 os levantar, seja tratado como decisão já tomada e não como achado
novo — e para que, se virarem obrigatórios, isso seja uma mudança de escopo consentida.

## Distinção que precisa sobreviver às fases seguintes

"Trilha imutável" neste produto significa **tamper-evident verificável**, não
tamper-proof. Quem controla a máquina pode reescrever a cadeia inteira; o que o sistema
garante é que uma alteração *pontual* é detectável (CA-4). Sem âncora externa não há
mais que isso — e prometer mais nos textos da UI seria falso.
