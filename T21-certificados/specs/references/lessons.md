# Lições deste projeto — ciclo v1.0

Escritas na Fase 7, sobre **este projeto** (domínio, stack, premissas erradas), não sobre a
metodologia. É o que um ciclo v2 — ou um post-mortem — precisa ler para não recomeçar do zero.

Data: 2026-08-09/10 · 12 módulos · 2174 LOC · 68 testes · 110 achados em 2 rodadas de crítica.

---

## 1. Domínio: as duas normas do vencimento não se conciliam em dias fixos

NIST SP 1800-16 manda alertar a **90/60/30 dias** e escalar por inação. O CA/Browser Forum
(SC-081v3) derrubou a validade máxima de certificados TLS para **200 dias em 2026-03-15**, e
ela cai para 100 em 2027 e 47 em 2029.

Aplicar 90/60/30 a um certificado de 47 dias significa alertar antes de ele existir. As duas
fontes são normativas e **incompatíveis por construção** — a reconciliação é decisão de
projeto, não fato pesquisável.

O que emergiu disso foi o invariante `limiar < (notAfter − notBefore)`, que virou o critério
`CA-5`. **Ele não estava no enunciado nem na cabeça de ninguém no início** — apareceu porque a
pesquisa da Fase 0 exigiu fonte para cada número e as fontes se contradisseram.

**Para o v2:** se a vida dos certificados continuar caindo, dias fixos deixam de funcionar
mesmo com o invariante. O caminho já mapeado e rejeitado nesta iteração é limiar por fração da
vida útil, ou consultar ARI (RFC 9773), em que a própria CA devolve a janela de renovação.

## 2. Domínio: o produto não impede a burla, e insistir nisso gera complexidade sem fim

O valor do produto é governança auditável, não monitoramento (que é commodity — cert-manager e
certbot fazem melhor). Mas o sistema **não tem poder algum sobre o host**: ele observa e
registra.

Cada controle que adicionamos criou a superfície de contorno seguinte:

```
CA-6 detecta troca não autorizada → destaque no painel
   → o burlador vê o próprio destaque      → exigimos justificativa nomeada
      → SEC-09: o burlador justifica a si mesmo → ...
```

A resposta certa foi **parar de correr atrás** e mudar o payoff em vez de tentar bloquear:
justificativa exige papel Aprovador, não apaga nada, referencia o evento e o contador de trocas
não autorizadas é permanente. O produto passou a **declarar o limite** em vez de prometer
enforcement que não pode entregar.

**Para o v2:** enforcement real exigiria sair da fronteira atual — integrar com a CA (recusar
emissão sem aprovação) ou com o provisionamento do host. Isso é outro produto, não um ajuste.

## 3. Stack: `node:sqlite` e type-stripping tornam Node 24 uma plataforma de zero dependências

O produto inteiro roda com **zero dependências de runtime**: `node:tls` para o handshake,
`crypto.X509Certificate` para o parsing (com `validToDate` como `Date` real), `node:sqlite` para
persistência transacional, `crypto.scryptSync` para senha, `node:http` para a UI, `node:test`
para os testes. TypeScript executa direto (`process.features.typescript === 'strip'`), sem build.

Custos reais encontrados:

- `node:sqlite` emite `ExperimentalWarning` e prende o projeto à linha 24 (`>=24 <25`).
- `scrypt` com os parâmetros da OWASP (N=2¹⁷, r=8, p=1) precisa de **~134 MB**, e o `maxmem`
  padrão do Node é **32 MB**: `scryptSync` lança sem o ajuste explícito. A saída fácil — baixar
  o N até caber — enfraqueceria o parâmetro em silêncio.
- `@types/node` teve de entrar como devDependency: sem ela `tsc --noEmit` não roda, e sem
  typecheck a verificação automatizada da Fase 5 deixa de existir.
- `PRAGMA journal_mode = WAL` foi **removido**: WAL existe para leitores concorrentes, e a trava
  exclusiva de escrita (uma varredura por vez) anula o motivo de usá-lo. Contradição que só
  apareceu na crítica da segunda rodada.

## 4. Premissas da Fase 0/1 que se mostraram erradas ou frágeis

| Premissa | O que aconteceu |
|---|---|
| **A3** — "fingerprint diferente + `notAfter` avançado ⇒ emissão" | Era premissa e virou **limite declarado**. Não distingue emissão legítima de troca que contornou a aprovação — daí `CA-6`, e daí toda a cadeia do item 2 |
| **A1** — "todo certificado de interesse está exposto em TLS" | Frágil de duas formas não previstas: **STARTTLS** (SMTP/IMAP/PostgreSQL negociam depois do protocolo em claro) e **a cadeia** — o design olhava só a folha, e um intermediário vencido derruba o serviço com a folha válida. A segunda foi corrigida; a primeira ficou como limitação declarada ao operador |
| **A2** — "o relógio da máquina está correto" | Nunca foi mitigável de verdade. Só se detecta **retrocesso** (`relogio-retrocedeu`); relógio consistentemente errado continua invisível e leva toda a classificação junto |
| "gravar observação só na mudança economiza" | Economia menor que a prevista: `visto_ultima_vez` precisa ser escrito a cada varredura de qualquer modo |
| `min(cadeia)` como driver do estado | Erro que teria virado alarme permanente: servidores servem cross-signed e raízes extras. A cadeia virou **sinalização**, e a classificação ficou com o `notAfter` da folha |

## 5. Padrões: o que funcionou e o que cobrou caro

**Funcionou:**

- **Relógio como porta injetada.** Nenhum módulo além de `relogio` chama `new Date()` — é o que
  torna `CA-1` testável de forma determinística com fixtures reais, fixando o "agora" em
  `notAfter − N`. Os testes valem hoje e daqui a um ano.
- **Estado do alvo derivado na leitura, nunca persistido.** Mudar o limiar reclassifica o
  inventário inteiro por construção, sem código de reconciliação e sem painel dessincronizado
  do histórico.
- **Token de transação no tipo.** As portas de escrita exigem um `Transacao` como parâmetro, o
  que torna escrever fora de `emTransacao` impossível de compilar — antes era regra escrita.
- **Erro de domínio como valor de retorno.** Deixou explícito, na assinatura, tudo que pode dar
  errado. E foi justamente onde o erro apareceu: colapsar variantes destruiu informação (item 6).

**Cobrou caro:**

- **Dividir `casos-de-uso` em dois foi certo; não poder dividir mais, não.** `caso-governanca`
  ficou com 10 operações e `web-ui` com sessão + CSRF + render + 7 telas porque um 13º módulo
  estouraria o limite de 12 do enunciado. São os dois módulos com mais achados e onde o LOC
  estourou a estimativa em 36%. **Limite de forma vira dívida de granularidade.**

## 6. Lição de método com efeito prático: a pergunta muda o resultado

Três defeitos reais foram achados perguntando **"onde isto diverge da especificação?"** e nenhum
teria sido achado perguntando "está funcionando?":

1. `CA-5` não estava garantido — o critério de aceitação nº 5 passava em silêncio.
2. As mensagens de erro vazavam código interno, e uma delas **descartava a causa** que o domínio
   já conhecia.
3. Um teste novo montava o cenário errado (limiares 90/60/30 contra certificado de 100 dias são
   **válidos**): ele exercitava o caminho feliz. Relaxar a asserção teria produzido cobertura
   fictícia de `CA-5`.

O terceiro é o mais instrutivo: **um teste verde pode não testar nada.** A primeira correção que
tentei tratou o sintoma (o número na asserção) e deixou o cenário inválido de pé.
