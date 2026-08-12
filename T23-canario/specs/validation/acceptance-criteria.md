# Critérios de aceitação e validação

Escritos na Fase 0, **antes de qualquer código** (§2 do ENUNCIADO). É contra este
documento que a Fase 6 monta o Test Map — não contra a implementação.

---

## CA-0 — Critério de acerto objetivo (predição selada)

> Com **uma única configuração de limiares**, o sistema reverte o canário
> degradado (UC-2) **e** não reverte sob ruído comum às duas versões (UC-3), de
> forma reproduzível.

**Por que este critério discrimina.** Um limiar absoluto ingênuo passa em UC-2 e
falha em UC-3: o pico de carga do UC-3 cruza o mesmo limiar que a degradação do
UC-2, e o sistema reverte um canário inocente. Só o **par**, sob a **mesma
configuração**, prova que a comparação concorrente canário-vs-baseline foi
implementada em vez de apenas declarada.

⚠️ **Armadilha de falso verde a evitar na Fase 6:** rodar UC-2 e UC-3 com
configurações de limiar diferentes. Isso faz os dois passarem sem que o mecanismo
exista. A configuração precisa ser literalmente a mesma.

---

## Casos de uso e desfechos esperados

| id | Cenário | Desfecho esperado | O que prova |
|---|---|---|---|
| **UC-1** | Canário estatisticamente indistinguível do baseline | Progride por todos os passos até 100% e é promovido a estável | O caso positivo. Sem ele, um sistema que sempre reverte pareceria correto |
| **UC-2** | Canário com latência/erro sistematicamente piores | Reprovado; peso devolvido a zero; 100% à estável; motivo reportado | O requisito central do enunciado |
| **UC-3** | Pico de carga degradando canário **e** baseline igualmente | **Nenhum rollback** | Que a comparação é concorrente e não absoluta. Metade do CA-0 |
| **UC-4** | Fonte de métricas para de responder | Contado como **erro** em sucessão (limite 4), não como falha; recuperação zera o contador | A distinção falha/erro. Sem ele, coletor caído derruba canário saudável |

---

## Critérios de validação por área

| id | Critério | Verificação | Fonte |
|---|---|---|---|
| VAL-1 | O julgamento compara canário contra **baseline pareado**, nunca contra a estável de vida longa | Um teste em que estável e baseline têm métricas distintas (por idade de instância) deve mostrar o julgamento seguindo o baseline | R-03, R-04, R-05 |
| VAL-2 | Amostra mínima de **50 pontos por métrica** antes de julgamento estatístico válido | Com menos de 50 pontos, o veredito é `Nodata`, não `Pass` nem `Fail` | R-03, R-05 |
| VAL-3 | Score de grupo = `(Pass / Total) × 100`, **excluindo `Nodata` do denominador** | Caso com 1 `Nodata` em 4 métricas deve pontuar sobre 3, não sobre 4 | R-02, R-04 |
| VAL-4 | Limiares comparados de forma **inclusiva (≥)** | Score exatamente 95 com `passThreshold` 95 → **Pass** | R-02, R-03 |
| VAL-5 | **Falha** conta no total acumulado; **erro** conta em sucessão e reseta ao recuperar | UC-4: 3 erros, recuperação, 3 erros → não atinge o limite de 4 consecutivos | R-06 |
| VAL-6 | Latência medida em **p99 de requisições bem-sucedidas**, separada das falhas | Um cenário com muitos erros rápidos não pode reduzir a latência julgada | R-01 |
| VAL-7 | Falha detém o avanço do peso; só o acúmulo dispara rollback | Um único julgamento ruim pausa a promoção sem reverter | R-07 |
| VAL-8 | Temporização: `promoção = interval × (maxWeight / stepWeight)` e `rollback = interval × threshold` | Medido no relógio virtual | R-07 |
| VAL-9 | Guarda absoluta reverte sob degradação grosseira **sem** aguardar os 50 pontos | Canário com 100% de erro reverte antes da amostra mínima | decisão do operador (sem fonte na literatura — ver nota) |
| VAL-10 | Execução **determinística**: mesma semente → mesmo desfecho, sem relógio de parede | Rodar cada UC duas vezes com a mesma semente e comparar a trilha completa | decisões `MODELO DE TEMPO`, `STACK` |
| VAL-11 | O operador consegue ler **por que** o sistema decidiu | A saída da CLI nomeia a métrica reprovada e o veredito que motivou a decisão | decisão `ATORES E AUTONOMIA` |
| VAL-12 | Abortar manual funciona a qualquer momento durante a execução | Aborto no meio de um passo devolve tráfego à estável e encerra | decisão `ATORES E AUTONOMIA` |

⚠️ **VAL-9 não tem fonte bibliográfica.** Os limiares da guarda absoluta são
decisão de projeto do operador, não parâmetro de literatura. Está declarado assim
de propósito, e é alvo nomeado da lente Científica na Fase 2 — que vai cobrar
exatamente isto.

---

## Fora de escopo (não testar, não implementar)

| Item | Razão |
|---|---|
| Kubernetes / service mesh / Prometheus reais | Substrato simulado; incluir tornaria o CA-0 não-verificável na janela de 2-4h |
| Persistência entre execuções | Execução da CLI é autocontida; exigiria persistência + máquina de estados durável sem valor para os 4 UCs |
| Latência p99 de falha | Métrica não selecionada. **Limitação conhecida:** timeout que degrada sem alterar taxa de erro fica descoberto |
| Aprovação manual por passo | Contradiz o "rollback automático" do enunciado |

---

# RESULTADOS — preenchido na Fase 7

Suíte: **62 testes, todos verdes** (`python3 -m pytest testes/`).

## Esperado × obtido

| Critério | Esperado | Obtido | |
|---|---|---|---|
| **CA-0** | mesma config: UC-2 reverte, UC-3 não | confirmado por teste E por execução manual do operador | ✅ |
| UC-1 | PROMOVIDO | PROMOVIDO em t=60 | ✅ |
| UC-2 | REVERTIDO | REVERTIDO em t=30 | ✅ |
| UC-3 | não reverte | PROMOVIDO em t=60, em 5 sementes | ✅ |
| UC-4 | erro, não falha | PROMOVIDO em t=90 após recuperação do coletor | ✅ |
| VAL-1 | julga contra baseline | contra a estável, o mesmo canário sadio dá `High` — o viés existe e é medido | ✅ |
| VAL-2 | 49 pontos → `Nodata` | confirmado; 50 julga | ✅ |
| VAL-3 | `Nodata` fora do denominador | 1 `Pass` em 2 considerados = 50, não 33,3 | ✅ |
| VAL-4 | comparação inclusiva | score 100 com limiar 100 aprova | ✅ |
| VAL-5 | erro reseta, falha não | confirmado, e contadores são por métrica | ✅ |
| VAL-6 | p99 de sucesso separada da de falha | **cumprido apenas no nome** — o substrato não modela requisições individuais | ⚠️ |
| VAL-7 | pausa antes de reverter | `pausado` precede `revertido` na trilha | ✅ |
| VAL-8 | `intervalo × limite_falhas` | rollback em t=30, previsto 30 — **igualdade exata** | ✅ |
| VAL-9 | guarda sem aguardar amostra | reverteu com **0 julgamentos** | ✅ |
| VAL-10 | determinismo | trilha idêntica nos 4 cenários e saída byte a byte igual | ✅ |
| VAL-11 | operador entende o porquê | confirmado por julgamento humano | ✅ |
| VAL-12 | aborto manual | Ctrl+C → REVERTIDO, confirmado pelo operador | ✅ |

## Poder da suíte, medido por mutação

| Mutação | Testes derrubados |
|---|---|
| Inverter a cauda do Mann-Whitney (`greater` → `less`) | 14 |
| Desligar `volumes_comparaveis` | 2 (era **1** antes de corrigir a falsa cobertura) |

## Razões canário/baseline no ground truth depositado

| cenário | latência | erro | saturação |
|---|---|---|---|
| UC-1 saudável | 1,00 | 1,00 | 0,98 |
| UC-2 degradado | 1,39 | 1,40 | 1,38 |
| **UC-3 ruído comum** | **1,00** | **1,00** | **0,99** |

UC-3 é a evidência numérica do mecanismo: valores absolutos inflados em 60%, razão 1,00. Um limiar absoluto veria degradação; a comparação concorrente vê paridade.
