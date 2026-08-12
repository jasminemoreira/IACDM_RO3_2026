# Modelo de domínio

Fase 1. Nomes idênticos aos de `specs/domain/glossary.md` e à tabela de módulos
de `specs/technical/architecture.md` — a chave estável entre fases é o **nome**.

---

## Entidades e objetos de valor, por módulo dono

### `alvo-de-implantacao` (M-10)

**Participante** — entidade.

| Atributo | Tipo | Regra |
|---|---|---|
| `papel` | `estavel` \| `baseline` \| `canario` | Exatamente três participantes, um de cada papel |
| `peso` | inteiro 0-100 | A soma dos três é **sempre 100** — invariante |
| `idade` | instante de implantação | `estavel` tem idade antiga; `baseline` e `canario` nascem no mesmo instante |

**Invariantes:**
- `soma(pesos) == 100` em todo momento observável.
- `peso(baseline) == peso(canario)` enquanto a implantação está em curso — é o
  que sustenta a comparação pareada (R-03: "same type and amount of traffic").
- Rollback ⇒ `peso(estavel) == 100`, os outros dois zerados.

### `julgamento` (M-02)

**Metrica** — objeto de valor.

| Atributo | Valor |
|---|---|
| `nome` | `latencia_p99_sucesso` \| `taxa_de_erro` \| `saturacao` |
| `direcao` | `menor_e_melhor` para as três nesta versão |

⚠️ `direcao` mora aqui e em nenhum outro lugar. É ela que decide se `High` ou
`Low` reprova. Espalhada como condicional, inverte o sinal silenciosamente ao se
acrescentar uma métrica `maior_e_melhor` (ex.: vazão).

**Veredito** — objeto de valor: `Pass` \| `High` \| `Low` \| `Nodata`.

| Veredito | Significado | Reprova? (direção `menor_e_melhor`) |
|---|---|---|
| `Pass` | Nenhuma diferença significativa a 98% | não |
| `High` | Canário significativamente **acima** do baseline | **sim** |
| `Low` | Canário significativamente **abaixo** do baseline | não |
| `Nodata` | Amostra insuficiente (< 50 pontos) | não conta — **excluído do denominador** |

### `janela` (M-01)

**Amostra** — objeto de valor: `(participante, metrica, valor: float, instante: int)`.

A janela indexa por `(participante, metrica)` e responde `suficiente()` quando a
série atinge **50 pontos** (R-03/R-05).

### `score` (M-03)

**Score** — objeto de valor: `float` em 0-100, mais os vereditos que o compõem.

```
score = (quantidade de Pass / quantidade de vereditos != Nodata) × 100
aprova = score >= LIMIAR_UNICO
```

⚠️ **Denominador zero:** se as três métricas derem `Nodata`, o score é
indefinido. Nenhuma fonte cobre este caso. Tratamento adotado: **não é aprovação
nem reprovação** — é ausência de julgamento, e o passo permanece pausado
aguardando amostra. Reprovar por falta de dado transformaria coletor lento em
rollback; aprovar por falta de dado promoveria canário não observado.

### `contadores` (M-05)

| Contador | Semântica | Limite | Reset |
|---|---|---|---|
| `falha` | Julgamento que reprova | acumulado no total | nunca |
| `erro` | Impossibilidade de **medir** | 4 **consecutivos** (R-06) | ao primeiro sucesso |

Fonte da distinção (R-06, comentário do código-fonte do Argo Rollouts): "unlike
failures, errors tend to happen ephemerally and may recover on its own".

### `coordenador` (M-07)

**Estados da máquina de promoção:**

| Estado | Entra quando | Sai para |
|---|---|---|
| `progredindo` | início, ou julgamento aprovou | `pausado`, `revertido`, `promovido` |
| `pausado` | um julgamento reprovou, mas o limite ainda não estourou | `progredindo` (recupera) ou `revertido` (estoura) |
| `revertido` | limite de falhas estourado, guarda absoluta disparou, ou aborto do operador | terminal |
| `promovido` | último passo concluído com aprovação | terminal |

⚠️ O estado `pausado` é o que distingue "detém o avanço" de "reverte" (R-07).
Sem ele, um único ponto ruim reverteria.

---

## Fluxo principal (um ciclo do laço)

```
relogio.avancar(intervalo)
  → simulador gera amostras (por participante, com efeito de idade de instância)
  → fonte-de-metricas.coletar()  ─── Indisponivel? → contadores.registrar_erro()
  → janela.adicionar(...)
  → guarda-absoluta.dispara(canario)?  ─── sim → revertido (curto-circuito)
  → janela.suficiente(metrica)?  ─── não → Nodata
  → julgamento.julgar(canario, baseline, metrica) por métrica
  → score.pontuar(vereditos) → aprova?
       sim → plano-de-passos.proximo() → alvo-de-implantacao.aplicar() → progredindo
       não → contadores.registrar_falha() → pausado ou revertido
  → coordenador emite evento → cli imprime
```

A guarda absoluta é consultada **antes** da checagem de amostra suficiente: é
exatamente a sua razão de existir — reverter degradação grosseira sem aguardar os
50 pontos.
