# Patches para `versus-claude`

> **Inventário consolidado: [`MELHORIAS-POS-LOTE.md`](MELHORIAS-POS-LOTE.md).**
> Lista única e acionável do que aplicar depois dos doze, com evidência por item.
> Os pedidos avulsos abaixo continuam válidos como detalhe técnico; o inventário
> os ordena e, no caso do `PEDIDO-M1`, **inverte a prioridade** depois da segunda
> ocorrência no T28.

Contra a **0.12.4** (commit `0cc74cb`). Três tamanhos; **o mínimo é o recomendado
antes do lote.**

| arquivo | o que faz | tamanho | testes |
|---|---|---|---|
| `nivel1-minimo-arquitetura-por-versao.patch` | **recomendado** — `architecture.md` deixa de ser sobrescrito a cada iteração | 1 arquivo, +8 | 56 ✓ / 0 ✗ |
| `nivel1-idioma-e-arquitetura.patch` | o acima + hook detectando a decisão de lentes em português | 2 arquivos, +16 −1 | 56 ✓ / 0 ✗ |
| `lentes-estruturadas.patch` | o acima + ferramenta MCP `record_activated_lenses`, enum das 12 lentes, campo em `state.json`, gate de evidência | 9 arquivos, +329 −7 | 65 ✓ / 0 ✗ |

## Como aplicar

O fonte fica em `versus-claude/src`, não na raiz do repositório — daí o `--directory`.

```bash
cd /home/jasmine/INDT/Versus_Claude
git apply --check -p1 --directory=versus-claude /home/jasmine/INDT/RO3/patches/<patch>   # ensaio
git apply -p1 --directory=versus-claude /home/jasmine/INDT/RO3/patches/<patch>
cd versus-claude && npm run build && npm test
```

Equivalente, de dentro de `versus-claude/`: `git apply -p1 <patch>`, sem `--directory`.

Nenhum deles toca `package.json`, `CHANGELOG.md` ou o `version` de `src/mcp/server.ts` —
bump e commit ficam com você.

---

## O mínimo: `architecture.md` por versão

Só guidance. Nenhuma linha de código, nenhum teste afetado, nenhum comportamento de
gate alterado.

A Fase 3 passa a **acrescentar** uma seção `## V(N+1)` com sua própria tabela de
módulos, em vez de substituir a anterior. O laço Fase 2↔3 critica uma arquitetura
diferente a cada rodada; sobrescrevendo, só a última sobrevive.

No piloto T01 isso aconteceu de verdade: `quota-limiter` existia na V(1), foi
eliminado na V(2), e os achados da iteração 1 passaram a apontar para um módulo que
nenhum artefato legível por máquina registrava. É perda de informação, e é a única
das correções encontradas no piloto que perde algo.

## O que ficou de fora, e por quê

**O aviso falso do hook.** Em sessão conduzida em português o modelo grava
`LENTES ATIVADAS`, e o hook — que procura o literal inglês `ACTIVATED LENSES`
([inject-context.ts:66](../../Versus_Claude/versus-claude/src/hooks/inject-context.ts)) —
exibe `⚠ P2 STEP 1 MISSING` durante toda a Fase 2, apesar do registro estar correto.

Não foi corrigido antes do lote porque **é aviso, não portão**: injeta texto no
contexto e não bloqueia nada. O T01 rodou as 8 fases com ele aparecendo o tempo todo
e entregou uma matriz bem-formada com 73 achados. O custo é ruído; o custo de mexer
no instrumento às vésperas da coleta é risco de regressão, que esta série de versões
já mostrou ser real. Fica declarado como limitação conhecida.

Consertar de verdade não é ensinar mais idiomas ao `grep` — é parar de ler prosa
livre. Isso é o `lentes-estruturadas.patch`, para depois do lote.

## Sobre `lentes-estruturadas.patch`

Guardado, não recomendado agora. Substitui a prosa por
`record_activated_lenses(conditional, notActivated)`, com `enum` das 12 condicionais,
exigência de que todas as 12 estejam contabilizadas, motivo obrigatório para cada
não-ativada, e `state.activatedLenses` como campo estruturado. O critério
`activated_lenses_recorded` deixa de ser booleano carimbável.

Uma bateria adversarial contra essa ferramenta achou **quatro bugs** na primeira
rodada — lente presente nas duas listas, lente duplicada, e lente universal aceita
como condicional (esta corrompe a contagem de condicionais, que é variável medida da
RO3). Os quatro estão corrigidos e cobertos por testes de regressão. Mas é superfície
nova, e o histórico desta série — três regressões na 0.12.0, a colisão do `M-` na
0.12.2, estes quatro — diz que cada mudança custa uma rodada de bugs. Não às vésperas
do lote.
