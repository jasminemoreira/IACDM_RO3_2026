# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Coordenador de implantação canário com rollback automático por métrica, convivendo com a versão estável

## A arquitetura

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

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo, e detecta uma classe de falha que as outras não detectam.

**Sete são universais** — rodam sempre e não estão em questão: Premissas, Arquitetura,
Implementabilidade, Rigor científico, Segurança, Desempenho, Conformidade regulatória.
**Não as inclua na resposta.**

**Doze são condicionais**, e são essas que você vai avaliar.

**A ativação é por SINAL DO PROJETO, e só.** Que outra lente pareça cobrir a mesma
classe de falha **não** é motivo para deixar uma de fora: não achar nada já é um
resultado válido, e decidir de antemão que duas lentes se sobrepõem é conclusão, não
premissa. Nunca marque `false` por redundância com outra lente — o motivo tem que ser
um sinal do projeto ("não há dependência externa", "não há superfície de usuário"),
nunca "já coberta pela lente X".


| lente | pergunta central | ativa quando |
|---|---|---|
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | External dependencies (APIs, DBs, queues, third-party services) |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | Replacing or modifying existing production system |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | Automated decisions about people (scoring, classification, moderation) |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | Multi-actor flows, state machines, or business processes |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | Production systems with operational requirements |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | State synchronization, runtime configuration affecting behavior, self-correcting or feedback-driven systems |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | Multiple independent actors, public API, external integrations, marketplace or platform design |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Inter-component communication, protocol definitions, message formats, interface contracts between independent teams |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | Module maintenance, system evolution, long-lived systems with technical debt accumulation |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T23-canario",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
