# Critérios de aceitação e validação — T29

Fixado na Fase 0, Nível 5. **Este arquivo é a fonte de verdade da Fase 6** (o método manda
testar contra as specs, não contra a implementação).

Delivery Target: **produto completo** em ciclo único.

---

## Critério de acerto objetivo (CA)

Forma escolhida: **lossless verificado + razão de compressão reportada, sem limiar prometido.**
Justificativa da forma em `specs/datasets/perfis-de-serie.md` §C1 — a razão varia ~20× entre
perfis de série, logo qualquer limiar único seria arbitrário (se frouxo) ou inverificável
(se importado de R1, cujo dataset não é o nosso).

| id | Critério | Forma de verificação | Binário? |
|---|---|---|---|
| **CA-1** | `decode(encode(S)) == S` bit a bit, para todo S do dataset | comparar `struct.pack('>d', a) == struct.pack('>d', b)` — **nunca** `a == b` | **sim** |
| **CA-2** | Migração F1 → F2 → F1 preserva a série | equivalência ponto a ponto após ida e volta | **sim** |
| **CA-3** | Retenção respeita a divisibilidade (R6) e o `xFilesFactor` | config inválida é **rejeitada**; agregado com fração de definidos < `xff` é **indefinido** | **sim** |
| **CA-4** | Razão de compressão medida e reportada por perfil | relatório com B/ponto por perfil, comparado à sondagem da Fase 0 | não (é medição) |

**Não há critério de throughput/latência.** Decisão consciente: o projeto mede corretude e
razão de compressão. Registrado para que a Fase 2 (lente Performance) trate desempenho como
observação, não como requisito não cumprido.

## Casos-limite obrigatórios (CA-1 não passa sem eles)

| Caso | Por que é obrigatório | Armadilha |
|---|---|---|
| `0.0` e `-0.0` na mesma série | têm bits diferentes e aritmeticamente são iguais | um teste com `==` passa falsamente |
| `NaN` com payload `0x7ff8000000000001` | *lossless* exige preservar o payload | `float('nan')` genérico perde o payload; `nan != nan` |
| `+inf`, `-inf` | expoente todo 1, mantissa 0 | — |
| Subnormal `5e-324` | expoente todo 0 | — |
| `2⁵³ + 1` | limite de inteiro exato em double | — |
| Valor com bit 63 setado | `int` do Python não trunca em 64 bits (armadilha P1) | bug invisível: o número só cresce |
| `D = 64` (cabe em 7 bits) e `D = -64` (não cabe) | faixa assimétrica `[-63, 64]` de R1 §4.1.1 (armadilha P5) | 7 bits em complemento de dois dão `[-64, 63]` |

## Invariantes de domínio a verificar (I1–I7 de `specs/domain/glossario.md`)

| id | Invariante | Tipo de teste |
|---|---|---|
| I1 | codec é *lossless* | positivo, = CA-1 |
| I2 | timestamps estritamente crescentes dentro do bloco | **negativo** — série fora de ordem deve ser rejeitada |
| I3 | resolução do tier mais longo divisível pela do tier inferior | **negativo** — `180 → 600` deve ser rejeitado (600/180 = 3,33); `60 → 300` aceito |
| I4 | downsampling é irreversível (o cru é descartado) | comportamental |
| I5 | retenção efetiva ≥ nominal, por até uma duração de bloco | comportamental |
| I6 | agregado indefinido se fração de definidos < `xFilesFactor` | positivo + **negativo** |
| I7 | retenção de um nível < idade mínima do downsample seguinte ⇒ **perda silenciosa** | **negativo** — a config deve avisar/rejeitar, não perder calado |

Razão mínima exigida pelo método: **1 teste negativo por cada 2 positivos.** A tabela acima já
tem 4 invariantes com teste negativo obrigatório (I2, I3, I6, I7) — mais os limites de `D`.

## Parâmetros de retenção a validar

| Parâmetro | Valor | Fonte |
|---|---|---|
| Tiers | cru → **5 min** → **1 h** | R9 |
| Divisibilidade | 300/60 = 5; 3600/300 = 12 ✅ | R6 |
| Agregados preservados | **min, max, sum, count** | R9 |
| `xFilesFactor` de referência | **0.5** | R6, R7 |
| Idade de downsample (citável) | 5m aos **40 h**; 1h aos **10 dias** | R9 |

## Razão de compressão esperada por perfil (referência da sondagem da Fase 0)

Alvo: a implementação deve reproduzir estes números ±10%, senão divergiu de R1.
Contabilizado com N = 7.200, `seed = 7`, timestamps regulares de 1 s.

| Perfil | B/ponto esperado | Razão |
|---|---|---|
| Gauge inteiro estável | 0,33 | 48,6× |
| Contador monotônico | 2,67 | 6,0× |
| Temperatura, 1 decimal | 6,41 | 2,5× |
| Float de alta precisão | 6,63 | 2,4× |
| Timestamps regulares (isolado) | 1,00 bit/ponto | — |
| Timestamps com jitter ±1 s (isolado) | 6,84 bits/ponto | — |

⚠️ Esta tabela é **verificação de fidelidade ao paper**, não critério de acerto. Se a
implementação der números muito diferentes nos mesmos perfis com a mesma seed, o codec
divergiu de `specs/technical/codec-gorilla.md` — é o micro-check adversarial da Fase 5 (S7).

---

# RESULTADOS REAIS — preenchido na Fase 7

Suíte: **141 testes, 0 falhas** (`pytest`, ~10,6 s). 99 funções: 50 negativas / 49 positivas.

## Critérios de acerto — esperado × obtido

| id | Esperado | Obtido | |
|---|---|---|---|
| **CA-1** | round-trip bit a bit em 100% dos casos | 11/11 casos-limite IEEE-754, comparando bytes. `NaN` com payload `0x7ff8000000000001` preservado; `-0.0` distinto de `0.0`; subnormal `5e-324`; `2⁵³+1` | ✅ |
| **CA-2** | F1 → F2 → F1 preserva a série | 60/60 pontos idênticos bit a bit na direção exata | ✅ |
| **CA-3** | divisibilidade (R6) + `xFilesFactor` | `180→600` recusado (3,33); I7 recusado; `average` encadeado recusado; `xff` emite em 100%/60%/50% e **suprime** em 40% | ✅ |
| **CA-4** | razão medida e reportada por perfil | 7 perfis medidos; os 4 da sondagem reproduzidos com desvio de **0,0–0,1%** | ✅ |

## Razão de compressão — sondagem da Fase 0 × implementação

| Perfil | Previsto (Fase 0) | Medido (implementação) | Desvio |
|---|---|---|---|
| gauge inteiro estável | 0,33 | **0,33** | −0,1% |
| contador monotônico | 2,67 | **2,67** | 0,0% |
| temperatura, 1 decimal | 6,41 | **6,41** | +0,0% |
| float de alta precisão | 6,63 | **6,63** | −0,1% |
| pontos faltando | — | 0,40 | — |
| jitter de timestamp | — | 0,64 | — |

Reproduzir os quatro números com a mesma seed **é** o teste de fidelidade a R1: um parâmetro
errado no codec moveria a razão.

## Invariantes — todas verificadas por teste

`I1` lossless ✅ · `I2` crescentes ✅ (com a divergência F1/F2 documentada) · `I3` divisibilidade ✅
· `I4` irreversibilidade — **não automatizável** (é ausência de mecanismo) · `I5` retenção
efetiva ≥ nominal ✅ (`effective_before_ts`) · `I6` `xFilesFactor` ✅ · `I7` perda silenciosa ✅
(com teste no limite exato **e** um segundo abaixo dele).

## Propriedades medidas além dos critérios

| Propriedade | Resultado |
|---|---|
| Atomicidade sob `SIGKILL` | 13 chunks íntegros, **0 `.tmp` órfãos**, `info` funcionando, integridade ok |
| Memória de `write()` | **plana em 1,5 MB** de 10 mil a 500 mil pontos (era 151 B/ponto) |
| Custo por ponto, F1 × F2 | **360 B/ponto** × **1 B/ponto** no mesmo dado |
| Entradas inválidas | 12 casos, **nenhum traceback**, todos exit 2 com mensagem de usuário |

## Defeitos encontrados APÓS o design convergir

Sete, mais uma premissa refutada — nenhum previsto pelas duas rodadas de crítica:

| Onde | Defeito |
|---|---|
| micro-check S7 (F5) | comprimento significativo 64 não cabe nos 6 bits de R1 (`-inf ⊕ 5e-324`) |
| micro-check S7 (F5) | `migrate` podia escrever **dentro** de um acervo existente |
| micro-check S7 (F5) | perfil `jitter` gerava ts duplicado com `step=1` |
| suíte (F6) | `METADATA_SIZE` é 16 e não 20 — **erro de spec**, em 6 arquivos |
| suíte (F6) | `default_tiers()` produzia config que a própria `validate()` recusa |
| suíte (F6) | ordem das verificações dava mensagem confusa |
| casos de borda (F6) | 3 caminhos vazavam **traceback** (CSV malformado, arquivo inexistente, duração inválida) |
| casos de borda (F6) | **`P-A8` refutada**: `write()` bufferizava a entrada inteira |

## Não coberto, e por quê

`I4` (ausência de mecanismo, verificável por inspeção) · `P-A2` escritor único (exigiria
concorrência, fora de escopo) · **legibilidade das mensagens e acionabilidade dos relatórios —
julgamento humano, e o teste exploratório humano NÃO foi realizado neste ciclo.** Quatro
defeitos sobreviveram a um "parece tudo bem": é a evidência do próprio ciclo de que essa
lacuna importa.

---

## Teste manual obrigatório (Fase 6, executado pelo operador — AP5)

O operador terá de executar pela CLI, como usuário final:
1. Ingerir uma série, comprimir, ler de volta — conferir que os valores voltam.
2. Aplicar a política de retenção e observar o tier de 5 min aparecer.
3. Migrar o acervo de F1 para F2 e voltar.
4. Tentar uma configuração de tiers inválida (`180 → 600`) e ver a mensagem de erro.
5. Julgar se as mensagens são compreensíveis e os relatórios acionáveis.
