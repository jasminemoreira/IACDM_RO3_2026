# Lições do projeto T30 — ciclo v1.0

Sobre ESTE projeto: o domínio, a stack, os padrões e as premissas que se
revelaram erradas. É o que um v2.0 — ou um post-mortem — precisa ler para não
redescobrir do zero.

---

## L1 — "Supressão" não é um filtro; é um pipeline com dois momentos distintos

O enunciado dizia "supressão" como se fosse uma coisa. A Fase 0 descobriu quatro
mecanismos (`opt_out`, `quiet_hours`, `rate_limited`, `duplicate`) e a Fase 1
descobriu que eles **não acontecem no mesmo instante**: opt-out e dedup são do
ingresso; janela e teto só fazem sentido no momento da entrega, porque quem
interrompe a pessoa é a entrega, não o registro.

O erro que isso evitou: um módulo `suppression` único com um parâmetro `stage`,
que a lente Arquitetural derrubou logo na primeira rodada (ARC-01 🔴) — servia a
dois mestres e tornava a cadeia de entrega intestável sem montar o contexto de
ingresso. **Se dois grupos de regras rodam em momentos diferentes do ciclo de
vida, são dois módulos, não um com bandeira.**

## L2 — Consertar um problema de concorrência cria outro, uma casa adiante

O ciclo mais instrutivo do projeto:

1. Iteração 1 apontou que uma entrega podia ficar presa para sempre se o processo
   morresse (RES-01 🔴) e que "worker único" era premissa não imposta (ASS-01 🔴).
2. A correção foi um **lease** com expiração.
3. Iteração 2 mostrou que o lease curou a perda e criou **duplicação**
   (RES-05 🔴, quando o envio dura mais que o lease) e **poison message**
   (RES-06 🔴, quando `attempts` não avançava em falha não capturada).
4. A correção final não trocou o mecanismo: acrescentou três travas —
   lote ≤ concorrência, abort duro no envio, fencing token na escrita — e
   **moveu o incremento de `attempts` para o momento da reivindicação**.

A inversão do incremento é a lição concentrada: contar a tentativa quando a
entrega é *tomada*, não quando o resultado *volta*, é o que faz uma falha
silenciosa caminhar para dead-letter em vez de girar eternamente. Custa uma
tentativa "desperdiçada" por crash — troca declarada e barata.

## L3 — Tirar poder de um ator o entrega a outro; o ganho é a auditabilidade, não a virtude

`transactional` era auto-declarado pelo emissor, que assim escapava de opt-out,
janela e teto (GAM-01 🔴). Movemos a decisão para um catálogo de categorias do
operador — e a iteração seguinte apontou (ETH-03 🟡) que o operador ganhou
exatamente o mesmo poder: marcar `marketing` como transacional anula o
consentimento de todo mundo, silenciosamente.

Não existia correção que removesse o poder sem mudar UC-7, que é escopo do
operador. O que se pôde fazer foi torná-lo **visível**: auditoria de quem alterou
a categoria, a CLI avisando em voz alta ao marcar algo como transacional, e o
endpoint de preferências informando à pessoa quais categorias ignoram o opt-out
dela. **Quando o poder não pode ser removido, o entregável é a transparência.**

## L4 — Node 24 muda a economia de um projeto TypeScript pequeno

`node arquivo.ts` roda direto: *type stripping* nativo, sem passo de build, sem
`tsc` no caminho, sem `ts-node`. Isso eliminou todo o scaffolding de compilação
de uma sessão de 2–4 h. Dois pedágios, ambos encontrados na prática:

- **Parameter properties não funcionam** (`constructor(private readonly x: T)`).
  O modo é *strip-only*: remove tipos, não transforma sintaxe. Erro
  `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`. Atribuição explícita resolve.
- `node:sqlite` é **experimental** e avisa em cada execução (`--disable-warning=
  ExperimentalWarning` limpa a saída). Vale isolá-lo atrás de um adaptador desde
  o primeiro dia — o que aqui já era exigência do arranjo hexagonal.

## L5 — Metade das falhas de teste foram do teste, não do código

Quatro falhas na construção da suite; **quatro eram defeito do arcabouço de
teste**:

| Sintoma | Causa real |
|---|---|
| Header `List-Unsubscribe` "ausente" | Nodemailer dobra headers longos (RFC 5322); a regex exigia espaço literal |
| Texto do rodapé "ausente" | Corpo em quoted-printable: `n=C3=A3o`, partido por quebra suave |
| Suite travou por 300 s | `await new Promise(()=>{})` faz o Node sair com código 13; e `on('exit')` registrado após o evento nunca dispara |
| `rate_limited` virou `delivered` | Instante do tick capturado **antes** da ingestão: a entrega venceu depois e só foi reivindicada num tick simulado dias à frente, com o balde já recarregado |

O padrão comum aos dois primeiros: **o teste verificava a formatação do
transporte em vez do critério da norma.** O antídoto que funcionou foi decodificar
de verdade (quoted-printable) em vez de relaxar a asserção — relaxar teria
passado a testar o encoding por acidente.

Corolário operacional: `comando | tail` bufferiza até EOF e esconde o progresso.
Diagnosticar um travamento exigiu rodar sem pipe.

## L6 — Premissas do desenho que a implementação derrubou ou reformulou

| Premissa | O que aconteceu |
|---|---|
| PRE-1 "worker único" | **Reformulada.** Deixou de ser premissa e virou consequência do mecanismo: com lease e fencing token, mais de um processo é seguro |
| PRE-4 "relógio confiável" | **Reduzida.** O tempo passou a vir do banco (`unixepoch()`), o que eliminou a premissa de relógios sincronizados que o lease havia introduzido (ASS-07) |
| PRE-8 "sem autorização por recurso" | **Reduzida, não removida.** A chave ganhou escopo de categorias e permissão separada para transacional; qualquer emissor autorizado ainda notifica qualquer pessoa |
| "9 tabelas" | **Errada por excesso.** Viraram 6: `attempts`, `idempotency_keys`, `quiet_windows` e `rate_buckets` eram relações 1:1 disfarçadas de tabela |
| "estado da notificação é uma coluna" | **Errada.** Derivar das entregas eliminou o problema de dono (PRO-01 🔴) em vez de resolvê-lo com mais mecanismo |
| "token de unsubscribe de uso único" | **Requisito desnecessário.** Descadastrar é idempotente; o que o token precisava era escopo e validade |

## L7 — O que a segunda iteração da crítica comprou

Números da sessão: **68 achados** em V(1) → **28** em V(2); **8 críticos** → **2**
→ **0**; mudança estrutural **75%** → **16,7%**. O módulo `delivery-worker`, que
a primeira rodada atingiu com 10 das 18 lentes, caiu para 1 achado depois de
virar mecanismo puro.

E o achado que só a segunda rodada podia dar: **toda correção da Fase 3 gerou um
defeito novo no lugar para onde a responsabilidade foi movida.** Lease → RES-05/06.
Catálogo → ETH-03. Extração de política → ARC-06. Catálogo em `preferences` →
ARC-07, que é literalmente a mesma violação de SRP que a rodada anterior havia
apontado em `suppression`. Segundo-sistema de Brooks em miniatura, e o motivo
pelo qual parar em uma rodada teria levado para o código um desenho cujas partes
novas ninguém havia olhado.

## L8 — Dívidas conscientes que o v2.0 herda

| Item | Por que ficou |
|---|---|
| **EDGE-14** — precedência `max(nextAttempt, deferUntil)` | Implementada, **não provada**: exige backoff maior que a abertura da janela, o que não ocorre com esperas de até ~80 s |
| **EDGE-10** — envio ultrapassando o lease | Exigiria destino travando >60 s; testadas a trava equivalente (abort em PAR-10) e a consequência (fencing token) |
| **ARC-07** — `preferences` com duas razões para mudar | Separar exigiria um 13º módulo, fora da faixa 8–12 do enunciado |
| **REG-01** — DKIM sobre os headers de unsubscribe | É do provedor de e-mail, não do serviço |
| **RES-03** — circuit breaker por destino | Com 8 envios em voo e Full Jitter, destino morto não bloqueia mais a fila |
| **GAM-02** — teto global compartilhado entre emissores | Decisão explícita da Fase 0; mudar alteraria semântica acordada |
| SEC-05, SUS-02, MEC-02, GAM-03, UX-04 | Adiados com registro |
| **Hook `tests_passing`** | Não disparou automaticamente nas chamadas de Bash desta sessão; o classificador espera `53 passed`/`0 failed` e o reporter do Node imprime `pass 53`/`fail 0` |
