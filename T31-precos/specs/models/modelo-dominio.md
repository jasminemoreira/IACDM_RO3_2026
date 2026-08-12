# Modelo de domínio — entidades, objetos de valor e contratos

Corresponde a **M-02 `modelo-dominio`** de `specs/technical/architecture.md`.
Domain Model (Fowler) com DDD tático: os invariantes I-1..I-7 de
`specs/domain/glossario.md` vivem nestes tipos, não nos serviços.

## Objetos de valor

### `Dinheiro` (M-01)
```
Dinheiro
  centavos: int                  # representação interna exata — nunca float
  de_texto(s: str) -> Dinheiro | ErroFormato
      # aceita "2,50" | "R$ 165,00" | "R$ 1.189,50" | "1189.50"
      # rejeita "" | "-10%" | "a partir de 50" | negativo
  multiplicar(qtd: int) -> Dinheiro
  aplicar_pct(pct: Decimal) -> Dinheiro      # half-up, 2 casas, uma única vez
  __str__() -> "R$ 1.189,50"
```
**Invariante:** nunca negativo. **I-5:** nenhuma operação converte para `float`.

### `Faixa`
```
Faixa
  minimo: int                    # >= 1
  maximo: int | None             # None = aberto à direita (∞)
  contem(qtd: int) -> bool       # minimo <= qtd <= maximo  (FECHADO nos dois lados)
  sobrepoe(outra: Faixa) -> bool
```
**Invariante:** `maximo is None or maximo >= minimo` — construir `Faixa(100, 50)`
levanta erro (caso R-01). **A-11:** intervalo fechado; a borda 19/20 é o teste
que prova isso (P-02, P-03).

### `Vigencia`
```
Vigencia
  inicio: date
  fim: date | None               # None = vigente indefinidamente
  contem(d: date) -> bool        # inicio <= d <= fim
```
*Valid time* de uma única linha do tempo (Snodgrass). Sem eixo de conhecimento.

### `Efeito` — **Strategy**
```
Efeito (protocolo)
  aplicar(preco_base: Dinheiro) -> Dinheiro
  descrever() -> str

PrecoUnitario(valor: Dinheiro)      aplicar -> valor                    (ignora a base)
DescontoPct(pct: Decimal)           aplicar -> preco_base.aplicar_pct(100 - pct)
```
Único ponto do domínio com variação real de algoritmo. Um terceiro efeito futuro
não toca `motor-precificacao`.

## Entidades

### `Produto`
```
Produto
  sku: str                       # normalizado: trim + upper  (A-02)
  descricao: str
  preco_base: Dinheiro           # base do desconto E resultado quando nada casa (I-2)
```

### `Regra`
```
Regra
  id: str
  escopo: str                    # um SKU específico OU "*" (qualquer produto)
  faixa: Faixa
  efeito: Efeito
  prioridade: int                # maior vence; importadas nascem com 0 (A-03)
  vigencia: Vigencia
  e_especifica() -> bool         # escopo != "*"
  casa(sku, qtd, data) -> (bool, motivo: str | None)
```
`casa` devolve **o motivo da não-correspondência** — é o que alimenta o trace
exaustivo (I-3) e permite responder "por que NÃO ganhei o desconto X".

### `VersaoDeRegras`
```
VersaoDeRegras
  numero: int
  publicada_em: datetime
  regras: tuple[Regra, ...]      # IMUTÁVEL (I-4)
```
Publicar cria uma nova; nunca altera a anterior. `Snapshot` (Fowler).

## Trace e decisão

```
Veredito
  regra_id: str
  casou: bool
  motivo: str
  # motivos possíveis: "casou"
  #                    "faixa não contém a quantidade (10–49, pedido 5)"
  #                    "vigência não contém a data (desde 01/03/2026)"
  #                    "escopo é outro SKU"
  #                    "perdeu por prioridade (0 < 50)"
  #                    "perdeu por especificidade (regra geral vs regra de SKU)"

Trace
  vereditos: tuple[Veredito, ...]        # TODAS as regras avaliadas — nunca vazio (I-3)
  vencedora: str | None                  # None = nenhuma casou → preço base
  calculo: str                           # "50 un × R$ 21,90 = R$ 1.095,00"

Decisao
  id: str
  sku: str
  quantidade: int
  data_pedido: date
  versao_regras: int
  preco_unitario: Dinheiro
  total: Dinheiro                        # preco_unitario × quantidade  (modelo VOLUME, A-10)
  trace: Trace
  registrada_em: datetime
```

**I-7 — o log é a verdade do que foi cobrado.** `Decisao` é imutável e guarda
`versao_regras`: se as regras daquela data forem reeditadas depois, o recálculo
diverge da decisão registrada, e a UI deve apresentar os dois valores como
coisas distintas — o registrado (o que foi cobrado) e o recalculado (o que as
regras atuais dizem sobre aquela data).

## Relatórios (saídas dos adapters de dados)

```
Relatorio(validação)   erros: [{regra_ids, tipo, descricao}]      # bloqueiam a publicação
                       avisos: [{sku, intervalo_descoberto}]      # lacuna: reporta, não bloqueia (AMB-5)

Resultado(importação)  rascunho: [Regra]
                       rejeitadas: [{linha: int, motivo: str}]    # motivo NOMEADO por linha
                       produtos: [Produto]

Relatorio(paridade)    conferem: int
                       divergencias: [{linha, esperado, obtido, delta}]
```

## Esquema SQLite (M-07)

```
produto(sku PK, descricao, preco_base_centavos)
versao(numero PK, publicada_em)
regra(id PK, versao_numero FK, escopo, faixa_min, faixa_max,
      efeito_tipo, efeito_valor, prioridade, vigencia_inicio, vigencia_fim)
rascunho_regra(id PK, ...mesmas colunas, sem versao_numero)
decisao(id PK, sku, quantidade, data_pedido, versao_regras,
        preco_unitario_centavos, total_centavos, trace_json, registrada_em)
```
Dinheiro é persistido em **centavos inteiros** — nunca `REAL` (I-5). O trace vai
como JSON na decisão porque é imutável e só é lido inteiro.
`publicar()` roda numa única transação: insere `versao` + todas as `regra` ou
nada (I-4, A-07).
