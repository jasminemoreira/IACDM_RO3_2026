# RETRABALHO — T31-precos

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-12** |

CS-1 a CS-5, congelados na Fase 0 antes de codar, verificados na Fase 6: **86 testes
verdes** (79 pytest + 7 Playwright em Chromium real), suíte executada seis vezes com a
saída lida. CS-1 paridade **26/26** contra a coluna original da planilha, divergência zero;
CS-3 **13/13** armadilhas detectadas antes da publicação; CS-5 latência **medida** em
11,21 ms.

Veredito da Fase 7: *"ATENDE, COM AS PENDÊNCIAS JÁ MAPEADAS"*.

**Único projeto do lote liberado para ciclo 2.** O operador encerrou a sessão declarando
*"funcionou parcialmente, mas vou liberar para um ciclo 2"*, e o backlog foi consolidado
como insumo do `start_new_cycle()`. As pendências são **trabalho de Fase 6 não concluído**,
não features — e estão nomeadas, não diferidas em silêncio.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### Três defeitos achados pelo operador num sistema que o smoke test da IA dava como verde

O registro nomeia a classe: *"a classe de achado que AP5 diz que automação não captura"*. É
a evidência mais direta do lote a favor do human-AV, e vale detalhar as três, porque cada
uma falha de um jeito diferente.

**1 — o sistema estava certo e a interface, muda.** Sintoma relatado: *"consegui importar
mas não consegui simular"*. O log mostrava **10 POSTs consecutivos em `/simular`, todos
HTTP 200**, e o banco em `versao=0`. O sistema se comportou **exatamente como projetado** —
"nenhuma versão publicada" é estado válido — e mesmo assim o operador não conseguiu fazer
o que queria. Nenhum teste automatizado detectaria isto: não há falha para detectar.

**2 — evidência volátil.** Depois de reiniciar o servidor, `GET /regras` deixava de exibir
o erro `preco_base_inconsistente` de SKU-1007 que aparecia logo após a importação. Causa:
`servico-aplicacao` guardava `self._conflitos` **apenas em memória do processo**. Achado ao
verificar o conserto do primeiro defeito.

**3 — beco sem saída na publicação.** *"Tentei e falhou de novo"*. O log confirma dois
`GET /regras` e **nenhum `POST /regras`**: o operador olhou a tela e não conseguiu publicar.

### O veredito humano sobre um achado 🔴, que é o que a lente UX existe para produzir

UX-01 dizia: *"se editar regra na UI for pior que editar célula, o analista volta para a
planilha e o motor vira leitura"*. Depois de usar a grade, o operador respondeu:

> *"é melhor pq o fluxo é integrado, mas faltam filtros"*

A contramedida principal **funcionou** — a integração entre editar, validar e publicar na
mesma tela é o que a planilha não tem. E a lacuna que sobrou virou item nomeado do ciclo 2,
com origem rastreável até o achado da Fase 2. É o ciclo completo crítica → contramedida →
julgamento humano → backlog, e só o T31 o exibe inteiro.

### Uma premissa da arquitetura refutada — segunda do lote

**A-06** dizia *"processo single-user / single-thread"*. O Starlette/FastAPI executa
endpoints **síncronos** (`def`, não `async def`) num threadpool, e a conexão SQLite criada
na thread que monta a aplicação era usada por outra: `sqlite3.ProgrammingError`.

O registro é direto: *"A PREMISSA A-06 ESTAVA ERRADA POR SER FORTE DEMAIS"*. Detalhe em
`ACHADOS-METODO.md` §M8 — duas premissas refutadas em onze projetos, ambas por execução
real, nenhuma pela crítica da Fase 2.

### O agente corrigiu uma afirmação falsa que ele mesmo tinha persistido duas vezes

> *"CORREÇÃO DE AFIRMAÇÃO FALSA QUE EU PERSISTI: registrei duas vezes, em decisões da Fase
> 5 e da Fase 6, que 'UC-3 nunca foi executado por humano — zero POST /regras no log'.
> ISSO ESTÁ ERRADO."*

A verificação em **todos** os arquivos de log dos quatro servidores encontrou **12 POST
/regras**. Ele havia lido o log de um servidor só e generalizado.

É um fato negativo afirmado a partir de observação parcial — e o mesmo agente, na Fase 7,
**usou esse erro para se conter**: ao diagnosticar o hook, escreveu *"NÃO afirmo que seja
defeito do Versus (…) a lição 7 deste mesmo ciclo registra que eu afirmei um fato negativo
a partir de observação parcial e errei. Repetir o padrão na frase seguinte seria o pior
tipo de lição."*

Correção de padrão de comportamento **dentro do ciclo**. Não conheço equivalente nos outros
dez projetos.

### Quarta ocorrência do M1, com o diagnóstico definitivo

Detalhado em `ACHADOS-METODO.md` §M1. O que este projeto acrescenta: uma **terceira causa**
(o `-qq` do pytest suprimindo o resumo), um **experimento controlado** provando que o hook
não dispara enquanto os ganchos irmãos disparam, e a **fragilidade estrutural** de não
haver ferramenta MCP que exponha `lastTestOutcome` — o que obriga a ler o `state.json` por
fora, contornando a interface que a metodologia oferece.

E a formulação sobre integridade, que vale como definição:

> *"O que fiz foi **retransmitir um resultado verdadeiro por um canal que estava quebrado**.
> A fraude seria invocar o gancho SEM ter rodado a suíte, ou com uma saída fabricada — e é
> exatamente por isso que registro aqui o comando, a saída usada e o motivo, **para que a
> diferença entre as duas coisas seja auditável e não dependa da minha palavra**."*

### Procedência do teste manual

Executado pelo operador **em duas rodadas**: na saída da Fase 5, onde achou os três
defeitos acima, e na Fase 6, concluída com UC-2 e UC-3 confirmados no log HTTP e no banco —
*"VERSÃO 1 PUBLICADA por 'XPPP', justificativa 'ppp', vigente desde 11/08, com 26 regras"*.

Sétimo dos onze projetos com human-AV pleno, e o de maior rendimento.
