# Implementação de referência — derivação de prioridade (Tier 2)

Componente Tier 2: algoritmo documentado com referência (F1). **Portar
literalmente** — mesma estrutura, mesmos nomes, testado contra as mesmas
entradas do ground truth. Não reinventar.

## A tabela é o algoritmo

A matriz de `specs/technical/matriz-prioridade.md` é uma tabela de consulta
total de 9 células. Não há fórmula a descobrir, não há caso a inferir.

```ts
// M-03 prioridade — referência a portar
type Impacto  = 'ALTO' | 'MEDIO' | 'BAIXO'
type Urgencia = 'ALTA' | 'MEDIA' | 'BAIXA'

// A matriz vem de M-02 configuracao (é DADO, não código — F2, F4).
// Esta é a forma default, idêntica a specs/technical/matriz-prioridade.md.
const MATRIZ_DEFAULT: Record<Impacto, Record<Urgencia, Prioridade>> = {
  ALTO:  { ALTA: 'P1', MEDIA: 'P2', BAIXA: 'P3' },
  MEDIO: { ALTA: 'P2', MEDIA: 'P3', BAIXA: 'P4' },
  BAIXO: { ALTA: 'P3', MEDIA: 'P4', BAIXA: 'P5' },
}

function derivar(impacto: Impacto, urgencia: Urgencia): Prioridade {
  return matriz()[impacto][urgencia]   // consulta total: sem default, sem fallback
}
```

**Não implementar como `P = impacto + urgencia - 1`.** A identidade aritmética
existe e está documentada, mas usá-la acopla a prioridade a uma matriz
simétrica de 3×3 — e a matriz é configurável (F2, F4). Trocar uma célula na
configuração deve mudar o resultado; com a fórmula, não muda. A tabela é a
verdade; a fórmula é coincidência desta configuração.

## Como o tipo `Prioridade` protege o CA-negativo

```ts
// M-03 prioridade — a única origem possível de uma Prioridade no sistema
declare const marca: unique symbol
export type Prioridade = ('P1'|'P2'|'P3'|'P4'|'P5') & { readonly [marca]: true }

// exportar SOMENTE derivar(). Não exportar construtor, não exportar cast.
```

Nenhum outro módulo consegue fabricar uma `Prioridade`. Um endpoint que
recebesse `prioridade` no corpo da requisição não teria como transformá-la no
tipo — o compilador recusa. É assim que o CA-negativo deixa de depender de
disciplina e passa a depender do `tsc`.

## Prazos — referência (M-04 `sla`)

```ts
// metas em horas corridas — de specs/technical/matriz-prioridade.md
const METAS_DEFAULT = {
  P1: { reconhecer:  0.167, resolver:   4 },
  P2: { reconhecer:  0.25,  resolver:   8 },
  P3: { reconhecer:  1,     resolver:  48 },
  P4: { reconhecer:  4,     resolver: 120 },
  P5: { reconhecer: 24,     resolver: 240 },
}

function prazos(p: Prioridade, abertoEm: Instante): Prazos {
  const m = metas()[p]
  return {
    reconhecimento: somarHoras(abertoEm, m.reconhecer),
    resolucao:      somarHoras(abertoEm, m.resolver),
  }
}
```

A assinatura só aceita `abertoEm`. Não há parâmetro `agora`, logo não há como
implementar por engano "reiniciar na reclassificação" — a opção descartada na
Fase 0.

## Testes de porte (Tier 2 exige testar contra as mesmas entradas)

Da tabela GT-1 de `specs/datasets/ground-truth-matriz.md`, as 9 entradas. Mais
as três propriedades: totalidade (9 células), monotonicidade (agravar um eixo
nunca melhora a prioridade), simetria dos eixos (ALTO/BAIXA = BAIXO/ALTA = P3).
