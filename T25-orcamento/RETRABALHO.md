# RETRABALHO — T25-orcamento

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-10** |

CA-1 e CA-2, congelados na Fase 0 antes de codar, verificados na Fase 6: **50 testes
verdes** (12 precificação/janela, 14 escrow, 11 gateway, 11 painel-api, 2 na SPA em
navegador real com Playwright). O invariante do teto foi verificado **sob concorrência** —
20 requisições simultâneas contra um teto que comporta ~3 resultam em ≤3 aceitas,
`confirmado ≤ teto`, `reservado == 0` e I2 íntegro. Exatidão contábil verificada **ao nano**
contra ground truth calculado à mão. Razão 28 negativos para 22 positivos.

Veredito da Fase 7: o operador confirmou que atende, com o painel validado manualmente em
navegador (*"tudo certo"*).

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### Um teste que passa igual com a premissa verdadeira ou falsa

O micro-check S7 encontrou o caso mais interessante do projeto, e o registro é explícito
sobre como: *"só apareceu ao EXECUTAR o código, não ao lê-lo"*.

O clamp `custo = min(custo_real_nano, valor_reservado)` em `escrow.reconciliar` mantém o
invariante do teto **por construção**. A consequência não é óbvia: **CA-1 passaria mesmo se
a premissa A8 (`tokens_entrada <= bytes_do_corpo`) fosse falsa** — o excedente
simplesmente não seria contabilizado, convertendo um estouro do teto em **subcontagem
silenciosa**.

O teste do invariante, sozinho, não distingue *"A8 é verdadeira"* de *"A8 é falsa e o
clamp mascara"*.

Isto é uma **quarta forma** de teste verde que não testa, distinta das três já registradas
em `ACHADOS-METODO.md` §M4: aqui o teste é válido, o critério é real, e o código está
correto — mas o teste é **insensível à premissa que o critério pressupõe**. Não é cenário
errado, nem cobertura parcial, nem condição inalcançável: é um invariante garantido por
construção, que por isso não pode falhar e não informa nada.

### Seis defeitos encontrados por rodar, nenhum por ler

O registro da Fase 5 é enfático: *"6 defeitos encontrados por RODAR, nenhum por ler"*.
Dois valem citação:

**Cobrança errada de cache.** O objeto `usage` não informa o TTL do cache — quem informa é
a requisição. Sem varrer `cache_control.ttl` no payload, escrita de cache de 1 h (2,0×) era
cobrada como 5 min (1,25×). Subcontabilização silenciosa, invisível a qualquer leitura do
código.

**`sqlite3.connect` sem `check_same_thread=False`** falhava quando o servidor ASGI constrói
a app numa thread e serve noutra. Corrigido, e o registro justifica que a segurança vem do
**desenho** — processo único, event loop único, `BEGIN IMMEDIATE` — e não do guard da
biblioteca. Divergência declarada com a razão, não contornada.

### O painel arredondava exatamente a informação que existia para mostrar

As 2 falhas do smoke test de navegador foram **defeito do produto, não do teste** — e o
registro diz isso antes de corrigir.

`USD()` em `painel.js` formatava com 2 casas (`(centavos/100).toFixed(2)`). Neste domínio o
custo de uma requisição é fração de centavo: com teto de USD 0,01 a tela exibia `$0.01`
para o teto **e** `$0.01` para o confirmado, com saldo `$0.00`, enquanto a entidade seguia
ativa e comportava 64 tokens de saída. **O operador não distinguia teto de consumo nem
enxergava o saldo.**

É a lente UX com consequência funcional, não estética — e só apareceu porque o operador
escolheu Playwright em vez de testes só-HTTP. O racional registrado antecipa exatamente
isso: *"os testes HTTP não executam uma única linha de `painel.js`; sem navegador real o
módulo ficaria sem teste automatizado algum"*.

### Procedência do teste manual

Executado **pelo operador** no painel real, com plano apresentado antes: leitura como
operador, disparo de consumo até HTTP 402, alteração de teto pela própria tela e retomada
do atendimento. Resultado: *"tudo certo"*.

Terceiro dos cinco projetos com human-AV pleno (T24, T23, T25).
