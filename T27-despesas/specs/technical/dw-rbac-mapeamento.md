# Mapeamento DW-RBAC → `autoridade.resolver()` (resolve SCI-02 / SCI-04)

Referência: **DW-RBAC — a formal security model of delegation and revocation in workflow
systems**, Wainer & Kumar, *Information Systems*.
PDF aberto: <https://www.ic.unicamp.br/~wainer/papers/is07.pdf>

O achado SCI-02 (iteração 1) e sua reincidência SCI-04 (iteração 2) dizem a mesma coisa: o
projeto cita o paper mas nunca disse **qual construção dele** cada função implementa. Sem
isso, o "porte Tier 2" da Fase 5 vira reimplementação de memória (AP7). Este é o mapa.

## Construções do paper e sua contraparte aqui

| DW-RBAC | Neste projeto | Onde |
|---|---|---|
| **Delegation assertion** — o delegante afirma a delegação; ela existe como fato declarado, com sujeito, objeto e janela temporal | entidade `Delegacao(delegante, delegado, inicio, fim, estado)` criada por `podeCriar` | `dominio-delegacao` |
| **Acceptance** — o delegado aceita antes de exercer | **não implementado, deliberadamente.** Aqui a delegação vale sem aceite: o delegado descobre o item na bandeja. Simplificação consciente do escopo, registrada como divergência do modelo formal | — |
| **Execution** — o exercício da autoridade delegada em um ato concreto, avaliado no instante do ato | `resolver(despesa, atuante, decisoesDaDespesa, delegacoesAtivas, instante)`: é exatamente a função "execution" — decide se **este** ator pode praticar **este** ato **agora** | `autoridade` (INV-6) |
| **Revocation** — encerramento da delegação; o paper cataloga dimensões (propagação, dominância, dependência, automática vs. por usuário) | `revogar(delegacao, instante)`; **dimensões escolhidas:** revogação por usuário (delegante) *e* administrativa (Admin); **sem propagação** porque a delegação não é transitiva (INV-3); **sem dependência** porque não há cadeia de delegações; expiração é **automática por tempo**, avaliada sob demanda | `dominio-delegacao` |
| **Multi-step delegation** (delegação em cadeia) | **proibida** por INV-3. O paper a suporta; a proibição é decisão do operador, não omissão | `dominio-delegacao` |
| **Partial delegation** (subconjunto de permissões) | **não usada**: a delegação é global (decisão N5 da Fase 0) | — |

## O que isso fixa na Fase 5

Ao implementar `autoridade.resolver()`, a estrutura a portar é a de *execution* do DW-RBAC:
a autoridade efetiva de um ator sobre um ato é a união da autoridade própria com a
autoridade delegada **vigente naquele instante**, e a verificação é feita no ato, não na
entrada na fila. É essa ordem — verificar no ato — que INV-6 codifica, e é a razão pela qual
uma decisão tomada dentro da vigência permanece válida depois dela.

**Divergências conscientes do modelo formal**, para que a Fase 6 não as trate como defeito:
sem aceite pelo delegado; sem delegação multi-passo; sem delegação parcial; sem propagação
de revogação.
