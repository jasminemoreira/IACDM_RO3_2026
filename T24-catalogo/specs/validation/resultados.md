# Resultados — esperado vs. obtido

Fechamento da Fase 7. Confronto entre os critérios escritos na Fase 4 (antes do código) e
o que a suíte e o teste manual efetivamente produziram.

**Suíte:** 56 testes, 56 passando (`pytest`, testemunhado pelo motor).
**Teste manual:** executado pelo operador. Confirmação literal: *"Testei e está bom"*.

---

## CA-0 — critério de acerto do projeto

| | Esperado (oráculo, Fase 4) | Obtido |
|---|---|---|
| Afetados de `vendas.pedidos` | 6, conjunto exato | ✅ 6, igualdade de conjunto |
| Responsáveis | 4, deduplicados | ✅ 4 |
| Diamante `financeiro.conciliacao` | 1 ocorrência | ✅ 1, no conjunto e no agrupamento |
| Dono sobrescrito `financeiro.previsao` | Carlos Lima | ✅ Carlos Lima, não João Souza |
| Próprio `vendas.pedidos` | ausente (A6) | ✅ ausente |

**CA-0 atendido.** A asserção é feita sobre `query_service.impact`, função pura — não
atravessa arquivo nem stdout, o que foi a razão de projetar o núcleo puro.

## Demais critérios

| CA | Resultado | CA | Resultado |
|---|---|---|---|
| CA-1 | ✅ 4/8/7 exatos | CA-13 | ✅ frase explícita, não silêncio |
| CA-2 | ✅ 6/6 linhas do oráculo | CA-14 | ✅ mensagem e exit code distintos |
| CA-3 | ✅ nomeia os dois datasets do ciclo | CA-15 | ✅ (via CA-0) |
| CA-4 | ✅ nomeia `vendas.inexistente` | CA-16 | ✅ Ana e João uma vez cada |
| CA-5 | ✅ herança e sobrescrita | CA-17 | ✅ construtor testado diretamente |
| CA-6 | ✅ 5/5 linhas do oráculo | CA-18 | ⚠️ atendido **com precisão acrescentada** |
| CA-7 | ✅ nomeia o domínio | CA-19 | ✅ ordem estável entre execuções |
| CA-8 | ✅ (via CA-3) | CA-20 | ✅ 9/9 caracterização |
| CA-9 | ✅ (via CA-4) | CA-21 | ✅ nas duas posições da flag |
| CA-10 | ✅ pelos dois lados | CA-22 | ✅ uma vez no texto, campo no JSON |
| CA-11 | ✅ recusa a ambiguidade | CA-23 | ✅ `safe_load` recusa a tag |
| CA-12 | ✅ nomeia `alimentado_pro` | | |

### CA-18 — a única divergência entre o escrito e o obtido

Escrito na Fase 4: *"um catálogo com 3 defeitos distintos reporta os 3 numa execução"*.

Obtido: verdadeiro **dentro de cada estágio**, falso entre estágios. O estágio de FORMA
porteia o SEMÂNTICO, e isso é deliberado — validar semântica sobre catálogo parcial
geraria falso positivo de "aresta pendente" para todo dataset do arquivo rejeitado.

O critério não foi enfraquecido para caber no código: o código foi verificado primeiro, a
razão do gate foi confirmada como necessária, e A9 recebeu a precisão que lhe faltava em
`specs/technical/architecture.md`. O operador enfrenta no máximo **duas** rodadas de
correção, nunca N — que era o atrito que A9 existia para evitar.

## Não verificável automaticamente

Compreensibilidade das mensagens para um dono de domínio, utilidade prática do
agrupamento por dono, e adequação do vocabulário do formato. Coberto pelo teste manual do
operador (AP5: nenhuma asserção substitui julgamento humano aqui).

## Métricas finais

| | |
|---|---|
| Módulos | 9 (V(3)); V(1) tinha 11 |
| LOC de produção | 1.171 |
| Testes | 56 (33 positivos / 23 negativos) |
| Achados da crítica adversarial | 75 acumulados (53 + 22) |
| Críticos | 12, todos fechados — 9 por desenho, 3 aceitos por arbitragem |
| Fixtures de defeito | 8 |
| Falhas em execução, com causa nomeada | 2 |
