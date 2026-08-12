# RETRABALHO — T27-despesas

Exigido pelo §3 do BATCH-PROTOCOL. Formato: `data | severidade | origem | descrição`.

**Definição aplicada** (EXPERIMENT-PROTOCOL): retrabalho é defeito detectado por uma
suíte de aceitação **executada após o marco de entrega**. Defeito encontrado durante o
processo não é retrabalho.

## Defeitos pós-entrega

| data | severidade | origem | descrição |
|---|---|---|---|
| — | — | — | **nenhum registrado até 2026-08-11** |

CA-1 a CA-11, congelados na Fase 0 antes de codar, verificados na Fase 6: **43 testes
verdes, 100 asserções**, `tsc --noEmit` limpo, `npm audit` com 0 vulnerabilidades. Os 13
primeiros por teste automatizado **com verificação anti-vacuidade por mutação**; CA-11 por
execução humana na UI real.

Veredito da Fase 7: *"Atende — os 14 critérios de aceite estão cumpridos"*.

Este arquivo permanece aberto: defeito encontrado em uso posterior entra aqui, com data,
e **antes de ser corrigido**.

---

## Achados pré-entrega, registrados para o corpus (não são retrabalho)

### Verificação anti-vacuidade adotada por iniciativa, terceiro projeto seguido

O registro da Fase 7 diz que os critérios foram verificados *"por 43 testes automatizados
verdes **com verificação anti-vacuidade por mutação**"*.

É a terceira ocorrência no lote — T22, T23 e agora T27 — de teste de mutação praticado
**sem estar na guidance**. Três de sete projetos adotaram por conta própria a contramedida
para a classe de defeito que `ACHADOS-METODO.md` §M4 e §M5 catalogam. Reforça a
recomendação pós-lote: se três agentes independentes chegam à mesma prática, ela pertence
ao método.

### Um cast de tipo apagando o erro que o mapeamento explícito pegaria

Toda criação de despesa falhava com *"Papel undefined não existe na matriz"*. Causa:
`usuarios.porId` fazia `st.usuarioPorId.get(id) as Usuario` — **cast sem mapeamento de
coluna**. A linha do SQLite traz `papel_id` (snake_case do schema) e o tipo de domínio tem
`papelId` (camelCase), então `solicitante.papelId` era `undefined`.

O registro nomeia o mecanismo: *"o cast silenciou o erro que o mapeamento explícito teria
evitado"*. É defeito de fronteira entre dois vocabulários — a classe que a lente LIN
cobre — e o `as` do TypeScript é exatamente o que impede o compilador de vê-lo.

### A delegação acrescentava sem remover

Com delegação `carla → bruno` ativa, o item aparecia na bandeja de **bruno E de carla**,
violando CA-3 (*"o item aparece na bandeja de B e NÃO na de A"*). Em `autoridade.resolver`,
o ramo de autoridade própria devolvia sucesso para o delegante sem considerar que ele havia
delegado.

O que torna este caso interessante: o refinamento de CA-3 foi **aprovado pelo operador na
Fase 3** (V(3)/S2), e a implementação da Fase 5 não o realizou. Mesma classe do §M6 do
T26 — **a Fase 5 não preserva o que a Fase 3 decidiu** —, agora em dois projetos e por
mecanismos diferentes: lá foi desempenho reintroduzido, aqui foi uma regra de negócio
refinada e não implementada.

### Escolha de ferramenta de UI decidida contra o precedente, com razão

O operador escolheu `fastify.inject()` e **recusou Playwright**, que tinha sido a escolha
certa no T25. O racional registrado é específico: a UI é server-rendered sem JavaScript de
cliente, toda interação é link ou POST, e `inject()` exercita rota, nonce anti-CSRF,
redirecionamento e o HTML renderizado — *"~200 MB de download de navegadores para exercitar
pouca coisa além do que inject cobre"*.

E o registro declara **o que `inject` não cobre**, em vez de apresentar a escolha como sem
custo. Vale para o corpus como contraponto ao T25: lá o navegador real pegou um defeito de
formatação invisível a testes HTTP; aqui a ausência de JS de cliente remove esse risco. A
mesma decisão tem sinais opostos em projetos diferentes.

### Substituição de dependência por bloqueio real, com alternativa avaliada e recusada

`better-sqlite3 ^9.6` não instala no ambiente — sem prebuild para Node 24.13.1, e o
`node-gyp` falha. Subida para `^13.0.3`, **verificada carregando o módulo e executando uma
query**, não presumida. A alternativa `node:sqlite`, embutida no Node 24, foi avaliada e
recusada com razão registrada.

A stack aprovada na Fase 1 foi mantida integralmente; só as versões mudaram. Divergência
declarada, não contornada.

### Procedência do teste manual

O operador executou o roteiro exploratório e reportou *"me parece tudo ok"*, com
confirmação **global sobre os sete cenários** entregues em chat. Quarto dos sete projetos
com human-AV pleno (T24, T23, T25, T27).
