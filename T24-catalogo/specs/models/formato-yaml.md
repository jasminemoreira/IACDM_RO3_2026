# Formato de declaração — um arquivo YAML por domínio

Modelo de dados da camada de declaração. É o contrato que o **dono de domínio** opera
(UC-1) e a entrada de `yaml-loader` (M-07) / `catalog-mapper` (M-08).

## Localização

Um arquivo por domínio, em um diretório passado por argumento à CLI:

```
catalog/
  vendas.yaml
  logistica.yaml
  financeiro.yaml
```

A fronteira do arquivo É a fronteira de propriedade: cada dono edita apenas o seu
arquivo. Conflito de merge entre domínios distintos não existe por construção.

## Estrutura

```yaml
# catalog/financeiro.yaml
dominio: financeiro
dono:
  nome: João Souza
  contato: joao@empresa.com

datasets:
  - nome: receita
    descricao: Receita reconhecida por competência    # opcional, texto livre
    alimentado_por:                                   # opcional
      - vendas.pedidos

  - nome: previsao
    descricao: Projeção de receita para o trimestre
    dono:                                             # opcional — SOBRESCREVE o dono do domínio
      nome: Carlos Lima
      contato: carlos@empresa.com
    alimentado_por:
      - financeiro.receita
```

## Campos

| Campo | Nível | Obrigatório | Regra |
|---|---|---|---|
| `dominio` | raiz | sim | Nome do domínio. **Não pode conter ponto** (A10). Deve ser único entre arquivos |
| `dono` | raiz | sim | Objeto `{nome, contato}`. Garante INV-2 |
| `dono.nome` | — | sim | Texto livre |
| `dono.contato` | — | sim | Texto livre (e-mail, canal, o que torne a notificação acionável) |
| `datasets` | raiz | sim | Lista. Pode ser vazia — um domínio sem datasets é válido |
| `datasets[].nome` | dataset | sim | **Não pode conter ponto** (A10). Único dentro do domínio |
| `datasets[].descricao` | dataset | não | Texto livre. Documenta o dataset para humano; não é schema estruturado |
| `datasets[].dono` | dataset | não | Mesma forma de `dono`. Quando presente, **sobrescreve** o dono herdado do domínio |
| `datasets[].alimentado_por` | dataset | não | Lista de identidades completas `dominio.dataset`. Ausente ou vazia = dataset de origem |

## Identidade

A identidade de um dataset é `<dominio>.<nome>`, composta pelo `dominio` do arquivo
mais o `nome` do dataset. Ela nunca é escrita explicitamente na própria declaração —
apenas em `alimentado_por`, ao referenciar dataset de outro domínio (ou do mesmo).

## Direção da aresta — atenção

`alimentado_por` é declarado pelo **consumidor** e aponta para o **produtor**. A aresta
do grafo vai na direção **oposta** à da declaração:

```
declaração:  financeiro.receita  alimentado_por  vendas.pedidos
aresta:      vendas.pedidos  ->  financeiro.receita
```

Razão da escolha (Fase 0): só o consumidor sabe de fato o que consome. Exigir que o
produtor liste seus consumidores é pedir exatamente a informação que ele não tem — que
é o problema original que este projeto existe para resolver.

A inversão é responsabilidade **exclusiva** de `catalog-mapper` (M-08). Nenhum outro
módulo enxerga a direção declarada; do `lineage-graph` (M-04) para dentro, só existe a
direção do fluxo do dado.

## Erros de declaração e a invariante que cada um viola

| Situação | Invariante | Comportamento |
|---|---|---|
| `alimentado_por` referencia dataset não declarado | INV-5 | Erro de carregamento, nomeando a referência quebrada |
| Ciclo entre datasets | INV-4 | Erro de carregamento, **nomeando os datasets do ciclo** |
| `dono` ausente no domínio | INV-2 | Erro de carregamento, nomeando o domínio |
| Nome de domínio duplicado entre arquivos | INV-1 | Erro de carregamento, nomeando os arquivos em conflito |
| Nome de dataset duplicado no mesmo domínio | INV-1 | Erro de carregamento |
| Ponto no nome de domínio ou de dataset | A10 | Erro de carregamento |

Todas as violações são reportadas **de uma vez** (A9), não uma por execução.
