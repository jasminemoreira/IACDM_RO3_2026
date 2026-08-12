# Critérios de aceitação — T25

Insumo da Fase 6. Cada linha vira ao menos um teste no Test Map.

---

## RESULTADOS (preenchido na Fase 7 — esperado × obtido)

Suíte: **50 testes, 50 verdes** (`pytest tests`). 28 negativos / 22 positivos.

| Critério | Esperado | Obtido | |
|---|---|---|---|
| CA-1 | soma das aceitas ≤ teto; posteriores negadas | 20 concorrentes → ≤3 aceitas, `confirmado ≤ teto`, `reservado==0`, I2 íntegro | ✅ |
| CA-2 | custo exato ao nano | 16.000.000 nano contra ground truth calculado à mão (D-1) | ✅ |
| CA-3 | reset reverte o corte | negada em agosto, permitida em setembro com `confirmado=0` | ✅ |
| CA-4 | modelo sem preço → negado | 402 `modelo_sem_preco_vigente`; nada enviado ao provedor | ✅ |
| CA-5 | `refusal` sem saída não cobra | custo 0 e reserva devolvida | ✅ |
| CA-6 | nenhum caminho deixa reserva aberta | erro do provedor, idempotência e liberação: `reservado==0` | ✅ |
| CA-7 | crash → reservas liberadas no arranque | 1 órfã liberada, contador restaurado | ✅ |
| CA-8 | I2 observável | `/health` expõe `i2_ok: true` | ✅ |
| CA-9 | defesas contra abuso | `max_tokens` acima do limite e reservas simultâneas negados | ✅ |
| CA-10 | painel protegido e informativo | 401 sem token, 404 em travessia, 400 em corpo inválido, distinção sem-dados | ✅ |
| **CA-11** | `count_tokens ≤ bytes` numa amostra real | **NÃO VERIFICADO** — exige `ANTHROPIC_API_KEY`. O teste existente prova que o *clamp sinaliza*, não que a premissa é verdadeira | ❌ |

**Defeito encontrado pelo teste de navegador e corrigido:** formatação com 2 casas
decimais escondia teto, consumo e saldo. Nenhum dos 48 testes de API podia detectá-lo.

**Limitação de todo o ciclo:** suíte e teste manual rodaram contra o **upstream
simulado**. A validação contra a API real permanece por fazer.

---

## CA-1 — CRITÉRIO DE ACERTO (congelado na Fase 0, decisão 86e98611)

**Invariante do teto sob concorrência.** Dado um teto T e N requisições
simultâneas de uma mesma entidade contra saldo quase esgotado:

- (a) a soma dos custos reais das requisições **aceitas** não ultrapassa T;
- (b) toda requisição submetida após o esgotamento é **negada**.

Verificação: N ≥ 20 requisições concorrentes contra teto que comporta ~3.
Falha se `confirmado_nano > teto_nano` em qualquer escopo.

## CA-2 — Exatidão contábil contra ground truth

Dado `usage` conhecido e rate card conhecido, `custo_nano` calculado é **exato**
(aritmética inteira, sem arredondamento intermediário).

Casos obrigatórios: as quatro categorias de token separadamente · cache 5m vs 1h
(1,25× vs 2,0×) · preço promocional do Sonnet 5 dentro e fora da vigência.

## CA-3 — Reset reverte o corte

Uma entidade cortada na janela N é atendida na janela N+1 sem intervenção.
Verificação: injetar instantes de janelas distintas (a janela é função pura).

## CA-4 — Modelo sem preço vigente é negado

Requisição para modelo ausente do rate card, ou com preço fora de vigência,
retorna 402 `modelo_sem_preco_vigente`. **Nunca** custo zero ou estimado.

## CA-5 — Política de cobrança por `stop_reason`

`refusal` sem tokens de saída ⇒ custo 0 e reserva devolvida integralmente.
`end_turn` e `max_tokens` ⇒ cobrados pelo `usage` retornado.

## CA-6 — Nenhum caminho de saída deixa reserva aberta

Para cada caminho — sucesso, erro do provedor, exceção, desconexão do cliente no
meio do stream — ao final: `reservado_nano == 0` e a reserva não está `'aberta'`.

## CA-7 — Recuperação de queda de processo

Reservas `'aberta'` presentes no arranque são liberadas e os contadores voltam a
refletir apenas o confirmado.

## CA-8 — Invariante I2 observável

`soma(valor_nano das reservas 'aberta') == reservado_nano` por escopo, exposto em
`/health`.

## CA-9 — Defesas contra abuso de reserva

`max_tokens` acima do limite da entidade ⇒ negado (GAM-01).
Reservas simultâneas acima do limite ⇒ negado (GAM-03).

## CA-10 — Superfície do painel

Sem autenticação: `/api/consumo` e `PUT /api/tetos` retornam 401.
Rota inexistente sob a raiz retorna 404 (sem travessia de caminho).
O painel distingue "sem dados" de "consumo zero" e exibe o próximo reset em UTC.

## CA-11 — A8, a premissa que sustenta CA-1 (validação empírica obrigatória)

Para uma amostra de corpos de requisição reais: `count_tokens(corpo) ≤ len(corpo em bytes)`.

**Se falhar, CA-1 cai junto** — a reserva de entrada deixa de ser limite superior.
O sistema já sinaliza a violação em runtime (log `RESERVA INSUFICIENTE`), mas o
teste deve provar que o caso normal não a dispara.
