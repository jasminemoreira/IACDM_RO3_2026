# Perfis de série e razão de compressão medida — sondagem da Fase 0

**O que é isto:** uma sondagem de viabilidade executada na Fase 0 (Nível 4, Tech Feasibility)
para testar a premissa **A4** de `specs/technical/formatos-armazenamento.md`: *"1,37 byte/ponto
é atingível no nosso dataset, não só no do Facebook"*.

Não é o produto. O script apenas **contabiliza** a largura em bits que o esquema de R1
§4.1.1/§4.1.2 produziria — não codifica nem decodifica nada.

Ambiente: Python 3.12.1, `seed=7`, N = 7.200 pontos (2 h a 1 s), timestamps regulares.

---

## Resultado

| Perfil de série | B/ponto | Razão vs 16 B | Distribuição XOR (`0` / `10` / `11`) |
|---|---|---|---|
| Gauge inteiro estável (ex.: nº de conexões) | **0,33** | **48,6×** | 68% / 31% / 0% |
| Contador inteiro monotônico (ex.: bytes_total) | **2,67** | 6,0× | 0% / 99% / 0% |
| Temperatura com 1 decimal | **6,41** | 2,5× | 3% / 96% / 0% |
| Float de alta precisão (ruído) | **6,63** | **2,4×** | 0% / 99% / 0% |

Custo isolado dos timestamps:

| Padrão de timestamp | bits/ponto | B/ponto |
|---|---|---|
| Regular, 1 s, sem falhas | **1,00** | 0,125 |
| Com jitter de ±1 s | **6,84** | 0,855 |

## Conclusões (com consequência direta no critério de acerto)

### C1 — 1,37 B/ponto é uma propriedade do dataset do Facebook, não do algoritmo

R1 mediu 1,37 B/ponto em ODS — dado de **monitoração de infraestrutura**, dominado por
gauges inteiros estáveis e contadores. Nossa sondagem reproduz esse regime (0,33 B/ponto no
perfil de gauge estável, melhor até que o número do paper) **e** mostra o regime oposto:
**2,4×** em float de alta precisão, ou seja **~6,6 B/ponto — 4,8× pior que o número publicado**.

⚠️ **Consequência para a Fase 0:** um critério de acerto na forma *"atingir 1,37 B/ponto"* ou
*"atingir 12× de compressão"* é **inverificável sem fixar o dataset**. O critério tem de ser
uma das duas formas:
- **(a)** razão de compressão medida **sobre um dataset nomeado e versionado**, com limiar por perfil; ou
- **(b)** corretude *lossless* (invariante I1, universal) + razão **reportada**, não prometida.

Isto é exatamente a classe de erro que a lente **Scientific** da Fase 2 caça: número
plausível importado de um paper cujo contexto experimental não é o nosso.

### C2 — A compressão de timestamp é frágil a jitter

96% dos timestamps em 1 bit (R1) depende de amostragem de intervalo fixo. Com jitter de ±1 s,
o custo vai de 1,00 para **6,84 bits/ponto** (6,8×). O caso `D == 0` é todo o ganho.
→ Cenário de falha para a Fase 2 (lentes Assumptions e Performance), e teste da Fase 6.

### C3 — O caso `11` praticamente não ocorre em séries homogêneas

Nos quatro perfis, o caso `11` (13 bits de metadado) ficou em **0%** após os primeiros pontos,
porque `prev_leading`/`prev_trailing` estabilizam. R1 relata 19% num universo de 1,6 milhão de
valores de séries **heterogêneas**. Nossa sondagem usa séries individuais homogêneas — a
diferença é do método de amostragem, não do algoritmo. Não "corrigir" o codec por causa disso.

### C4 — O ramo `10` domina, e é onde vale otimizar

99% dos valores caem no caso `10` nos perfis de contador e float. É precisamente o caso que
Chimp (R2) ataca ao quantizar os zeros à esquerda em 8 buckets de 3 bits. Registrado como
alternativa **não escolhida** em `codec-alternativas.md` §4 — mas agora com evidência
numérica nossa, não só a do paper.

## Dado de teste a produzir para a Fase 6

Os quatro perfis acima **são** o esboço do dataset de ground truth. A produzir em
`specs/datasets/`:

| Perfil | Por que é necessário |
|---|---|
| Gauge inteiro estável | melhor caso — verifica o caminho `xor == 0` |
| Contador monotônico | caminho `10` com `trailing == 0` |
| Float de alta precisão | pior caso — garante que o critério não é medido só no caso fácil |
| Série com jitter de timestamp | exercita os 4 buckets de delta-of-delta |
| Série com lacunas (pontos faltando) | R1 §4.1.1 cita explicitamente: delta 60,60,121,59 ⇒ D = 0,61,−62 |
| Casos-limite IEEE-754 | `0.0`, `-0.0`, `NaN` com payload, `±inf`, subnormal (`5e-324`) — verificados abaixo |
