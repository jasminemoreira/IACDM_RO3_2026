# Arquitetura — T23 coordenador canário

Fase 1, iteração 1. Aprovada pelo operador.

Padrões: **Hexagonal (Portas e Adaptadores)** · KISS+YAGNI · SOLID (SRP + DIP) ·
funções puras no núcleo de decisão · monothread determinístico ·
GoF State/Strategy/Observer · Fowler Domain Model · sem persistência.

Stack: **Python 3.12 + scipy**.

---

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | janela | Acumula amostras por participante×métrica; sabe se atingiu a amostra mínima (≥50, R-03/R-05) | `adicionar(participante, metrica, valor, instante)` · `series(participante, metrica) -> [float]` · `suficiente(metrica) -> bool` | — |
| M-02 | julgamento | Dono de `metrica` (nome + direção) e `veredito`. Função PURA: séries pareadas → veredito, via Mann-Whitney U a 98% de confiança | `julgar(serie_canario, serie_baseline, metrica) -> Veredito` | janela |
| M-03 | score | Função PURA: vereditos → score `(Pass/Total)×100` excluindo Nodata do denominador; aprova/reprova por limiar único | `pontuar([Veredito]) -> Score` · `aprova(score) -> bool` | julgamento |
| M-04 | guarda-absoluta | Função PURA: amostras recentes → rollback imediato, sem aguardar a amostra mínima | `dispara(series_canario) -> Motivo \| None` | janela |
| M-05 | contadores | Falha (total acumulado) vs. erro (sucessão, limite 4, reset ao recuperar) — R-06 | `registrar_falha()` · `registrar_erro()` · `registrar_ok()` · `estourou() -> bool` | — |
| M-06 | plano-de-passos | Sequência de pesos do canário; próximo passo; se é o último | `proximo(atual) -> int \| None` · `ultimo(peso) -> bool` | — |
| M-07 | coordenador | Máquina de estados (progredindo / pausado / revertido / promovido) e o laço de execução. Orquestra e emite eventos | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | janela, julgamento, score, guarda-absoluta, contadores, plano-de-passos, relogio, fonte-de-metricas, alvo-de-implantacao |
| M-08 | relogio | PORTA + adaptador virtual: avanço programático do tempo. Nenhum outro módulo lê o relógio do sistema | `agora() -> int` · `avancar(delta)` | — |
| M-09 | fonte-de-metricas | PORTA de coleta. Distingue amostra de indisponibilidade — não são o mesmo evento | `coletar(participante, metrica) -> Amostra \| Indisponivel` | — |
| M-10 | alvo-de-implantacao | PORTA + adaptador. Dono de `participante` e da distribuição de peso (soma 100). Rollback = 100% à estável | `aplicar(pesos)` · `distribuicao() -> {papel: peso}` | — |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas. Gera amostras por cenário (UC-1…UC-4), RNG semeável, modela idade de instância (aquecimento) | implementa `fonte-de-metricas` | fonte-de-metricas, relogio |
| M-12 | cli | Entrada do operador. OBSERVA eventos do coordenador; imprime progresso, motivo e decisão final. Único módulo que escreve no terminal | `main(argv) -> int` | coordenador, simulador-de-cenario, relogio, alvo-de-implantacao |

### Ausência deliberada de um módulo `modelo`

Os objetos de valor moram nos seus donos naturais — `metrica` e `veredito` em
`julgamento`, `participante` e peso em `alvo-de-implantacao`, `amostra` em
`janela`. Um módulo `modelo` compartilhado do qual todos dependem seria um *hub*
de acoplamento, e o primeiro achado legítimo da lente Arquitetural.

### Interfaces

Três **portas** isolam tudo que é exterior: `relogio`, `fonte-de-metricas`,
`alvo-de-implantacao`. Trocar o substrato simulado por um real é troca de
adaptador, sem tocar no núcleo.

O núcleo de decisão — **M-02, M-03, M-04** — é composto de funções puras: recebe
listas de números, devolve vereditos e score, sem tocar relógio, rede ou
terminal. É isso que torna VAL-3 e VAL-4 verificáveis por tabela de entrada/saída,
sem simulador. `coordenador` emite eventos e `cli` observa: o domínio nunca imprime.

---

## Premissas (assumptions)

| # | Premissa | Consequência se for falsa |
|---|---|---|
| A1 | O simulador é fiel o bastante para que a decisão testada nele signifique algo em produção | O sistema está correto contra um mundo que não existe |
| A2 | `simulador-de-cenario` modela idade de instância (aquecimento) | Baseline e estável ficam indistinguíveis; `alvo-de-implantacao` e a decisão BASELINE PAREADO viram código morto não demonstrável |
| A3 | Os limiares da `guarda-absoluta` são defensáveis | VAL-9 é arbitrário. É o único parâmetro do sistema sem fonte bibliográfica |
| A4 | 50 pontos por métrica bastam neste regime sintético, como bastam no real | A amostra mínima protege menos do que aparenta |
| A5 | `coordenador` depender de 9 módulos é aceitável por ser o orquestrador | É ponto de concentração — declarado de propósito como alvo da lente Arquitetural |
| A6 | Exigir score 100 para aprovar (3 de 3 `Pass`) não é rigoroso demais | Uma métrica ruidosa reprova canários sadios e UC-1 fica instável |
| A7 | O laço monothread representa adequadamente o abortar manual do operador | Uma corrida real entre aborto e julgamento não é modelada nem detectada |

## Escopo negativo

O sistema deliberadamente **não**:

- fala com Kubernetes, service mesh ou Prometheus reais;
- persiste nada entre execuções (sem banco, sem retomada, sem histórico);
- julga latência p99 de falha (limitação conhecida — timeout que degrada sem alterar a taxa de erro fica descoberto);
- pede aprovação humana por passo;
- implementa a faixa `Marginal` (inalcançável com 3 métricas — ver decisão FAIXA MARGINAL ELIMINADA);
- lê o relógio do sistema em nenhum módulo;
- imprime de dentro do domínio.

---

# V(2) — após a Fase 3 (iteração 1 do laço 2↔3)

V(1) acima é preservada de propósito: achados da iteração 1 nomeiam módulos que
V(2) alterou ou removeu, e sem a versão anterior essa rastreabilidade se perde.
**A seção corrente é esta.**

## Decomposição V(2)

Continuam **12 módulos** (teto do §2). `plano-de-passos` foi absorvido por
`configuracao`; `configuracao` entrou.

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | janela | Janela **DESLIZANTE** de tamanho fixo por participante×métrica. Descarta o mais antigo ao exceder. Também recusa julgamento quando os volumes de canário e baseline divergem além da razão tolerada | `adicionar(participante, metrica, valor, instante)` · `series(participante, metrica) -> [float]` · `pronta(metrica) -> bool` · `volumes_comparaveis(metrica) -> bool` | configuracao |
| M-02 | julgamento | Dono de `metrica` (nome + direção) e `veredito`. Função PURA. **Usa `alternative` unicaudal derivado da direção**; empate/indefinição → `Nodata` | `julgar(serie_canario, serie_baseline, metrica) -> Veredito` | janela, configuracao |
| M-03 | score | Função PURA: vereditos → score `(Pass/Total)×100` excluindo Nodata; **denominador zero → `Indefinido`, nem aprova nem reprova** | `pontuar([Veredito]) -> Score` · `aprova(score) -> bool` | configuracao |
| M-04 | guarda-absoluta | Função PURA: piso de segurança sem aguardar amostra. **Limiares são parâmetro OBRIGATÓRIO do operador, sem valor padrão** | `dispara(series_canario) -> Motivo \| None` | janela, configuracao |
| M-05 | contadores | Falha (total acumulado) vs. erro (sucessão) — **ambos POR MÉTRICA**, não globais. Sucesso consecutivo para sair de `pausado` | `registrar_falha(metrica)` · `registrar_erro(metrica)` · `registrar_ok(metrica)` · `estourou() -> bool` · `recuperou() -> bool` | configuracao |
| M-06 | configuracao | **NOVO.** Objeto congelado, validado na construção, dono de TODOS os parâmetros e da sequência de pesos. Folha do grafo: ninguém depende dele para comportamento, só para valores | `proximo_peso(atual) -> int \| None` · atributos somente-leitura | — |
| M-07 | coordenador | Máquina de **5 estados** (aquecendo / progredindo / pausado / revertido / promovido) com histerese. Verifica a flag de aborto a cada iteração. Respeita duração máxima. Emite eventos **tipados** | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | M-01…M-06, M-08…M-10 |
| M-08 | relogio | PORTA + adaptador virtual. **Dono único do avanço: apenas `coordenador` chama `avancar`** | `agora() -> int` · `avancar(delta)` | — |
| M-09 | fonte-de-metricas | PORTA de coleta. **Quatro desfechos**: Amostra, Indisponivel, Lenta, Invalida. **Uma chamada = uma amostra** (cardinalidade fixada) | `coletar(participante, metrica) -> Amostra \| Indisponivel \| Lenta \| Invalida` | — |
| M-10 | alvo-de-implantacao | PORTA + adaptador. Dono de `participante`, dos pesos e das duas invariantes. **Deriva os três pesos do peso do canário, espelhando baseline em canário.** Executa a troca de papéis ao promover | `aplicar(peso_canario)` · `distribuicao() -> {papel: peso}` · `promover()` · `reverter()` | configuracao |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas. **Contrato exige modelar idade de instância**: em t=0 a série da estável difere mensuravelmente da do baseline | implementa `fonte-de-metricas` | fonte-de-metricas, relogio, configuracao |
| M-12 | cli | Composition root: constrói `configuracao` a partir de um **perfil nomeado**, instala o tratador de sinal para o aborto, observa eventos e imprime. Único módulo que escreve no terminal | `main(argv) -> int` | coordenador, simulador-de-cenario, relogio, alvo-de-implantacao, configuracao |

## As quatro mudanças estruturais e o que cada uma resolve

**1. Janela deslizante** (`janela`) — tamanho fixo igual à amostra mínima.
Resolve ASM-03 (não mistura mais regimes de carga), PERF-01 (custo constante por
julgamento, não superlinear), CTL-02 (a inércia deixa de crescer), SUS-02
(retenção limitada). Um conceito a menos, não um a mais.

**2. `configuracao` substitui `plano-de-passos`** — a sequência de pesos já *era*
um parâmetro, e `proximo(atual)` é uma busca trivial sobre ela. Resolve IMP-03
(o CA-0 passa a ser expressável: um perfil nomeado, um objeto congelado), IMP-02,
SEC-01 (validação na construção), GOV-02, RES-03 (duração máxima), e dá lugar de
origem aos parâmetros de histerese e tolerância.

**3. `alvo-de-implantacao` vira dono único da alocação de tráfego** —
`aplicar(peso_canario)` deriva os três pesos, com `baseline == canario` e
`estavel == 100 − 2×canario`. Resolve ASM-02 e ARQ-04 (a regra tem dono e é
estrutural, não convencional), SEC-02 e LIN-03 (invariantes verificadas dentro),
PRO-03 (`promover()` existe). **Consequência de escopo:** o canário não pode
passar de 50%, porque acima disso a estável ficaria negativa. A promoção final
deixa de ser um passo de peso e passa a ser troca de papéis — que é o modelo de
R-04 e mantém "same type and amount of traffic" durante toda a análise.

**4. Máquina de 5 estados com histerese** (`coordenador`) — entra `aquecendo`.
Resolve PRO-02 (a fase inicial existe na máquina), PRO-01 e CTL-01 (sair de
`pausado` exige K sucessos consecutivos, com fonte em `consecutiveSuccessLimit`
de R-06), OBS-02 (`aquecendo` e `progredindo` são visivelmente distintos).

## Premissas V(2)

| # | Premissa | Estado |
|---|---|---|
| A1 | O simulador é fiel o bastante | mantida |
| A2 | O simulador modela idade de instância | **agora é contrato de M-11**, não premissa tácita |
| A3 | Os limiares da guarda são defensáveis | **convertida em risco aceito explícito**: sem valor padrão, o operador informa e o valor é impresso |
| A4 | 50 pontos bastam no regime sintético | mantida |
| A5 | `coordenador` depender de 9 é aceitável | mantida, mas 4 responsabilidades órfãs saíram dele |
| A6 | Score 100 não é rigoroso demais | **RETIRADA** — MEC-01 demonstrou o contrário; a tolerância mora agora em `contadores` com fonte em R-07 |
| A7 | O laço monothread representa o aborto | **RETIRADA** — o aborto é tratador de sinal com flag verificada por iteração |
| A8 | Uma chamada a `coletar` devolve uma amostra | **NOVA**, explícita (era ambiguidade LIN-01) |
| A9 | Só `coordenador` avança o relógio | **NOVA**, explícita (era ambiguidade LIN-02) |

---

# V(3) — após a Fase 3 (iteração 2 do laço 2↔3)

**Seção corrente.** V(1) e V(2) preservadas para rastreabilidade dos achados.

Continuam **12 módulos**. Nenhum entrou, nenhum saiu — as mudanças são de
calibração das correções de V(2), que era exatamente o diagnóstico da iteração 2.

## Decomposição V(3) — só as linhas que mudaram

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-06 | configuracao | Objeto congelado APENAS da configuração de **DECISÃO**: limiares, tamanho de janela, histerese, tolerância, intervalo, duração máxima, sequência de pesos. **Semente e cenário saíram daqui.** Valida na construção as quatro regras enumeradas abaixo | `proximo_peso(atual) -> int \| None` · atributos somente-leitura | — |
| M-11 | simulador-de-cenario | Adaptador de fonte-de-metricas e **dono da configuração de CENÁRIO**: qual cenário, semente, magnitude e persistência do efeito de aquecimento | implementa `fonte-de-metricas` · `Cenario(nome, semente, aquecimento)` | fonte-de-metricas, relogio |
| M-02 | julgamento | Como em V(2), porém com **alfa = 0,01 unicaudal** (preserva a taxa por cauda dos 98% bicaudais de R-02) e **sem o veredito `Low`**, que o teste unicaudal nunca produz | `julgar(...) -> Veredito` onde Veredito ∈ {Pass, High, Nodata} | janela, configuracao |
| M-07 | coordenador | Como em V(2). **Expiração por duração máxima mapeia para `revertido`**, com motivo `expirou` — continuam 5 estados | `executar() -> Desfecho` · `assinar(observador)` · `abortar()` | M-01…M-06, M-08…M-10 |

Os oito demais módulos permanecem como em V(2).

## As quatro correções de calibração

**1. Teto de exposição** (validação em `configuracao`) — resolve **SUS-03**.
`2 × max(sequência_de_pesos) ≤ 100 − piso_estável`, com o piso vindo de R-04:
"Production cluster: majority of incoming requests". A estável **nunca** deixa de
servir a maioria. A progressão por etapas é preservada; o que se elimina é a
rampa ilimitada que levava a estável a zero. Uma regra de validação no lugar de
um comportamento sem fronteira. Também resolve MIG-03 de carona: a estável nunca
esfria, porque nunca fica sem tráfego.

**2. Independência entre julgamentos** (validação em `configuracao`) — resolve
**CTL-03**. `intervalo × taxa_de_amostragem ≥ tamanho_da_janela`: julgamentos
consecutivos usam amostras disjuntas. Isso restaura o pressuposto de
independência sem o qual o `threshold` de R-07 não transfere — a correção de
MEC-01 volta a ser válida.

**3. Separação decisão × cenário** — resolve **IMP-05**. `configuracao` perde
semente e cenário, que passam a `simulador-de-cenario`, dono natural da
estratégia de cenário. O CA-0 volta a ser verificável e agora de forma
estrutural: **mesma `configuracao`, `Cenario` diferente**. `configuracao` fica
menor e verdadeiramente monopropósito, o que também alivia ARQ-05.

**4. Expiração é rollback** — resolve **PRO-05** e **SCI-09**. Encerrar por
duração máxima sem conclusão mapeia para `revertido` com motivo `expirou`, em vez
de criar um sexto estado. Um mecanismo de segurança que não conseguiu concluir
deve terminar no lado seguro. Sem estado novo.

## Validações enumeradas de `configuracao` — resolve MEC-03

1. `2 × max(pesos) ≤ 100 − piso_estável`
2. `intervalo × taxa_de_amostragem ≥ tamanho_da_janela`
3. sequência de pesos estritamente crescente e não vazia
4. `K` de histerese ≥ 1; tolerância de falhas ≥ 1; limiar da guarda informado

## Premissas V(3)

Mantidas A1, A4, A5, A8, A9. **A2 vira critério verificável** (o contrato de
`simulador-de-cenario` passa a exigir magnitude e persistência do aquecimento com
valores nomeados, resolvendo ASM-09). **A3 permanece risco aceito** — os limiares
da guarda continuam sem fonte, e não inventei uma.

**A10 (nova, explícita):** a estável nunca desce abaixo do piso, logo o rollback
sempre encontra instâncias quentes.


