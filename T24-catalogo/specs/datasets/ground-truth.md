# Ground truth — catálogo de exemplo com topologia conhecida

Este arquivo é o ORÁCULO do projeto. Foi escrito na Fase 4, ANTES de qualquer linha de
código, justamente para que os resultados esperados não sejam moldados pelo que a
implementação vier a fazer.

O critério de acerto do projeto é medido aqui:

> Sobre um catálogo de topologia CONHECIDA, `impacto` devolve EXATAMENTE o conjunto de
> datasets afetados e EXATAMENTE o conjunto de donos — incluindo o caso diamante (sem
> duplicata) e o caso de dono sobrescrito.

"Exatamente" = igualdade de conjuntos. Nem falso negativo (afetado omitido) nem falso
positivo (não-afetado incluído).

---

## O catálogo

### `catalog/vendas.yaml`
```yaml
dominio: vendas
dono:
  nome: Maria Silva
  contato: maria.silva@empresa.com
datasets:
  - nome: pedidos
    descricao: Pedidos brutos capturados no checkout
  - nome: itens_pedido
    descricao: Linhas de item explodidas por pedido
    alimentado_por:
      - vendas.pedidos
```

### `catalog/logistica.yaml`
```yaml
dominio: logistica
dono:
  nome: Ana Costa
  contato: ana.costa@empresa.com
datasets:
  - nome: envios
    descricao: Envios despachados por pedido
    alimentado_por:
      - vendas.pedidos
  - nome: rastreio
    descricao: Eventos de rastreio por envio
    alimentado_por:
      - logistica.envios
```

### `catalog/financeiro.yaml`
```yaml
dominio: financeiro
dono:
  nome: João Souza
  contato: joao.souza@empresa.com
datasets:
  - nome: receita
    descricao: Receita reconhecida por competência
    alimentado_por:
      - vendas.itens_pedido
  - nome: conciliacao
    descricao: Conciliação entre receita reconhecida e custo de envio
    alimentado_por:
      - financeiro.receita
      - logistica.envios
  - nome: previsao
    descricao: Projeção de receita para o trimestre
    dono:
      nome: Carlos Lima
      contato: carlos.lima@empresa.com
    alimentado_por:
      - financeiro.receita
```

### `catalog/marketing.yaml`
```yaml
dominio: marketing
dono:
  nome: Bia Rocha
  contato: bia.rocha@empresa.com
datasets:
  - nome: campanhas
    descricao: Campanhas ativas por período
```

---

## Grafo resultante (direção do FLUXO, já invertida em relação à declaração)

```
vendas.pedidos ──┬─→ vendas.itens_pedido ──→ financeiro.receita ──┬─→ financeiro.conciliacao
                 │                                                 │        ▲
                 │                                                 └─→ financeiro.previsao
                 │                                                          
                 └─→ logistica.envios ──┬─→ logistica.rastreio
                                        │
                                        └─→ financeiro.conciliacao

marketing.campanhas   (isolado, sem arestas)
```

7 arestas. Acíclico. **`financeiro.conciliacao` é o DIAMANTE**: alcançável a partir de
`vendas.pedidos` por dois caminhos independentes (via `itens_pedido → receita` e via
`envios`). Precisa aparecer UMA vez.

**`financeiro.previsao` é o DONO SOBRESCRITO**: pertence ao domínio `financeiro` (dono
João Souza) mas declara dono próprio, Carlos Lima.

---

## Resultados esperados — `impacto`

### `impacto vendas.pedidos` — CASO PRINCIPAL DO CRITÉRIO DE ACERTO

Afetados (6, conjunto exato):

| dataset | dono efetivo | por quê |
|---|---|---|
| `vendas.itens_pedido` | Maria Silva | domínio afeta a si mesmo |
| `logistica.envios` | Ana Costa | |
| `logistica.rastreio` | Ana Costa | transitivo, 2 saltos |
| `financeiro.receita` | João Souza | transitivo, 2 saltos |
| `financeiro.conciliacao` | João Souza | **DIAMANTE — uma única vez** |
| `financeiro.previsao` | Carlos Lima | **DONO SOBRESCRITO — não é João Souza** |

Responsáveis (4, conjunto exato após deduplicação):
`Maria Silva` · `Ana Costa` (aparece por 2 datasets) · `João Souza` (aparece por 2
datasets) · `Carlos Lima`

O próprio `vendas.pedidos` **NÃO** está no conjunto (assunção A6).

### Demais consultas de impacto

| consulta | afetados esperados | responsáveis esperados |
|---|---|---|
| `impacto financeiro.receita` | `financeiro.conciliacao`, `financeiro.previsao` | João Souza, Carlos Lima |
| `impacto logistica.envios` | `logistica.rastreio`, `financeiro.conciliacao` | Ana Costa, João Souza |
| `impacto logistica.rastreio` | ∅ (folha) | ∅ |
| `impacto financeiro.conciliacao` | ∅ (folha) | ∅ |
| `impacto marketing.campanhas` | ∅ (isolado) | ∅ |
| `impacto vendas.inexistente` | erro `DatasetNotFound` | — |

As três linhas com ∅ e a linha de erro são situações DISTINTAS e devem produzir mensagens
distintas (achado UX-02).

---

## Resultados esperados — `procedencia`

| consulta | a montante esperados | domínios atravessados |
|---|---|---|
| `procedencia financeiro.conciliacao` | `financeiro.receita`, `vendas.itens_pedido`, `vendas.pedidos`, `logistica.envios` | financeiro, vendas, logistica |
| `procedencia financeiro.previsao` | `financeiro.receita`, `vendas.itens_pedido`, `vendas.pedidos` | financeiro, vendas |
| `procedencia logistica.rastreio` | `logistica.envios`, `vendas.pedidos` | logistica, vendas |
| `procedencia vendas.pedidos` | ∅ (origem) | ∅ |
| `procedencia marketing.campanhas` | ∅ (isolado) | ∅ |

---

## Fixtures de defeito

Cada fixture planta UM defeito e é rastreável a uma invariante ou a um achado da Fase 2.

### 1. `ciclo.yaml` — viola INV-4
```yaml
dominio: financeiro
dono: {nome: João Souza, contato: joao.souza@empresa.com}
datasets:
  - nome: receita
    alimentado_por: [financeiro.previsao]
  - nome: previsao
    alimentado_por: [financeiro.receita]
```
Esperado: erro **nomeando os dois datasets do ciclo** — `financeiro.receita` e
`financeiro.previsao`. Não basta dizer "há um ciclo".

### 2. `aresta-pendente.yaml` — viola INV-5
```yaml
dominio: financeiro
dono: {nome: João Souza, contato: joao.souza@empresa.com}
datasets:
  - nome: receita
    alimentado_por: [vendas.inexistente]
```
Esperado: erro nomeando a referência quebrada `vendas.inexistente`.

### 3. `dominio-sem-dono.yaml` — viola INV-2
```yaml
dominio: financeiro
datasets:
  - nome: receita
```
Esperado: erro nomeando o domínio `financeiro`.

### 4. `dono-ambiguo.yaml` — achado GOV-04
Dois domínios, nomes de pessoa diferentes, MESMO contato:
```yaml
# a.yaml
dominio: alfa
dono: {nome: Maria Silva, contato: dados@empresa.com}
datasets: [{nome: x}]
# b.yaml
dominio: beta
dono: {nome: Ana Costa, contato: dados@empresa.com}
datasets: [{nome: y}]
```
Esperado: erro exigindo desambiguação. Colapsar as duas pessoas num dono só, em
silêncio, é o defeito que GOV-04 identificou.

### 5. `nome-com-ponto.yaml` — achado ASM-01
```yaml
dominio: vendas.br
dono: {nome: Maria Silva, contato: maria.silva@empresa.com}
datasets: [{nome: pedidos}]
```
Esperado: erro na construção do nome de domínio. Sem isso, a identidade
`vendas.br.pedidos` é lida como domínio `vendas` + dataset `br.pedidos` e resolve o dono
ERRADO em silêncio.

### 6. `campo-desconhecido.yaml` — achado MEC-01
```yaml
dominio: vendas
dono: {nome: Maria Silva, contato: maria.silva@empresa.com}
datasets:
  - nome: pedidos
    alimentado_pro: [vendas.outro]     # erro de digitação
```
Esperado: erro nomeando o campo desconhecido. Ignorar em silêncio faria a aresta
desaparecer sem aviso.

---

## Contagens de referência

| Métrica | Valor |
|---|---|
| Domínios | 4 |
| Datasets | 8 |
| Arestas de linhagem | 7 |
| Donos distintos | 5 (Maria, Ana, João, Carlos, Bia) |
| Datasets com dono sobrescrito | 1 (`financeiro.previsao`) |
| Nós alcançáveis por 2 caminhos | 1 (`financeiro.conciliacao`) |
| Datasets isolados | 1 (`marketing.campanhas`) |
| Fixtures de defeito | 6 |
