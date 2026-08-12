# RETRABALHO — T30-notifica

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-11** |

AC-1 a AC-4, congelados na Fase 0 antes de codar, verificados na Fase 6: **53 testes
verdes em 4,9 s**, 30 negativos (razão 1,30 por positivo, contra o mínimo de 1:2), type
check com 0 erros. Durabilidade provada **matando o processo com SIGKILL**. Os 8 casos de
uso executados manualmente pelo operador.

Veredito da Fase 7: *"ATENDE — AC-1 a AC-4 cumpridos"*.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### Cinco diagnósticos na Fase 6, e **nenhum** era defeito do produto

Este é o dado que distingue o T30 dos outros nove. Todas as causas raiz estavam no teste ou
no arcabouço de teste:

| falha | causa |
|---|---|
| PAR-17, headers do RFC 8058 | o nodemailer aplica **dobra de header** conforme RFC 5322; a regex exigia o espaço literal, verificando *"um detalhe de FORMATAÇÃO que a norma não impõe"* |
| PAR-17, segunda | o corpo vem em **quoted-printable**; a asserção comparava contra UTF-8 cru |
| AC-4, durabilidade — travamento | `await new Promise(() => {})` para simular processo travado: o **Node 24 detecta como `unsettled top-level await` e encerra com código 13** — o filho morria sozinho após imprimir CLAIMED |
| AC-4, travamento remanescente | **duplo fechamento** do mesmo handle `DatabaseSync`; o `node:sqlite` **pendura** no segundo `close()` em vez de lançar. Isolado por bissecção |
| UC-8 / AC-3 | erro de **ordenação temporal no teste**: `now` capturado antes da ingestão, então `next_attempt_at <= now` era falso por milissegundos |

**Por que vai para o corpus.** As quatro formas de "teste verde que não testa" catalogadas
em `ACHADOS-METODO.md` §M4 e §M5 tratam de testes que **passam** sem verificar. Aqui é o
espelho: testes que **falham** sem que haja defeito. O custo é o mesmo — tempo de
diagnóstico — e a defesa é a mesma disciplina de nomear causa raiz antes de corrigir, que
o projeto seguiu nas cinco.

Vale registrar a decisão de qualidade numa delas: no caso do quoted-printable, o registro
recusa explicitamente a saída fácil — *"NÃO relaxar a regex para um trecho ASCII"* — e
decodifica em vez de enfraquecer a asserção.

### Terceira ocorrência do M1, com as duas causas separadas

Detalhado em `ACHADOS-METODO.md` §M1. O que este projeto acrescenta:

O repórter do `node:test` imprimiu `pass 53` / `fail 0`, classificado como **`unknown`**,
com nada gravado. O agente contornou **sem tocar no hook**, acrescentando
`&& echo All tests passed` ao script — *"que só executa se o runner sair com código 0"*.

E mesmo assim: *"o hook não foi invocado pelo harness nas minhas chamadas de Bash"*.

**Corrigiu os marcadores e continuou travado** — é a confirmação que faltava de que a causa
raiz é o hook não ser invocado, não a lista de padrões.

**A declaração de integridade é a mais rigorosa do lote:**

> *"O que NÃO foi feito: gravar 'pass' à mão no `state.json`, nem alimentar o hook com
> texto sintético para abrir o portão — houve uma invocação com texto sintético durante o
> diagnóstico, e ela foi substituída pela execução real antes do `advance_phase`."*

Declarou uma invocação sintética intermediária que ninguém teria notado. Terceiro contorno
declarado em dez projetos, todos por iniciativa do agente.

### AP3 acionado e recusado, com mitigações nomeadas

O operador escolheu continuar na mesma sessão. O registro assume: *"quem escreve os testes
é quem escreveu o código, com o viés de confirmação que isso carrega (AP5)"*, e adota duas
mitigações — testes escritos contra `specs/validation/acceptance-criteria.md` e contra os
ids `EDGE-1..EDGE-14`, *"não contra a implementação"*, mais o teste manual pelo operador.

Terceira vez no lote (T26, T29, T30) que a renovação é oferecida, recusada, e o risco fica
registrado dos dois lados.

### Procedência do teste manual

O operador executou o roteiro de **9 passos** e reportou via `AskUserQuestion` que tudo
funcionou. Cobriu os 8 casos de uso como usuário final, com verificação na caixa SMTP local
e no receptor de webhook.

Sexto dos dez projetos com human-AV pleno.
