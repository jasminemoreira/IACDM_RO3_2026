# Contratos de exemplo — payloads literais

Referência para a Fase 5 (S6 Tier 2: implementar contra exemplo escrito, não
contra memória). Todos os exemplos usam o dataset de
`specs/datasets/casos-armadilha.md`.

## UC-1 — precificar (caso P-01)

`POST /preco` — **data é obrigatória** no contrato de máquina (A-04: o motor
nunca lê o relógio).

```json
{ "sku": "SKU-1003", "quantidade": 50, "data": "2026-08-12" }
```

```json
{
  "sku": "SKU-1003",
  "quantidade": 50,
  "data_pedido": "2026-08-12",
  "versao_regras": 3,
  "preco_unitario": "R$ 21,90",
  "total": "R$ 1.095,00",
  "explicacao": "Aplicada a regra de faixa 20–99 un do SKU-1003: R$ 21,90/un. As faixas 1–4 e 5–19 não cobrem 50 un; a faixa 100+ exige quantidade maior.",
  "trace": {
    "vencedora": "R-1003-C",
    "calculo": "50 un × R$ 21,90 = R$ 1.095,00",
    "vereditos": [
      { "regra_id": "R-1003-A", "casou": false, "motivo": "faixa não contém a quantidade (1–4, pedido 50)" },
      { "regra_id": "R-1003-B", "casou": false, "motivo": "faixa não contém a quantidade (5–19, pedido 50)" },
      { "regra_id": "R-1003-C", "casou": true,  "motivo": "casou" },
      { "regra_id": "R-1003-D", "casou": false, "motivo": "faixa não contém a quantidade (100–∞, pedido 50)" }
    ]
  }
}
```

**I-3:** `vereditos` nunca é vazio. Toda regra avaliada aparece, mesmo as que não
casaram — é o que responde "por que NÃO ganhei o desconto X".

## UC-4 — derrota por prioridade (caso P-07)

Entrada `SKU-1001, qtd 600`, com a regra transversal `*` `500–∞` `DESCONTO_PCT 10`
prioridade 50, contra a regra de SKU `200–∞` `R$ 1,85` prioridade 0.

```json
{
  "preco_unitario": "R$ 2,25",
  "total": "R$ 1.350,00",
  "explicacao": "Aplicada a regra geral 'acima de 500 un, 10% off': R$ 2,50 − 10% = R$ 2,25/un. A regra de faixa 200+ do SKU-1001 (R$ 1,85/un) casou, mas perdeu por prioridade (0 < 50).",
  "trace": {
    "vencedora": "R-GERAL-500",
    "calculo": "R$ 2,50 − 10% = R$ 2,25; 600 un × R$ 2,25 = R$ 1.350,00",
    "vereditos": [
      { "regra_id": "R-1001-D",   "casou": true, "motivo": "perdeu por prioridade (0 < 50)" },
      { "regra_id": "R-GERAL-500","casou": true, "motivo": "casou" }
    ]
  }
}
```

Note: a regra derrotada tem `casou: true` **e** um motivo de derrota. Casar e
vencer são coisas diferentes — confundi-las apaga metade da explicação.

## UC-6 — nenhuma regra casa (caso P-05)

```json
{
  "sku": "SKU-1009", "quantidade": 15,
  "preco_unitario": "R$ 3,20",
  "total": "R$ 48,00",
  "explicacao": "Nenhuma regra de preço cobre 15 un do SKU-1009 (há faixas para 1–9 e 20–99). Aplicado o preço base: R$ 3,20/un.",
  "trace": {
    "vencedora": null,
    "calculo": "preço base R$ 3,20; 15 un × R$ 3,20 = R$ 48,00",
    "vereditos": [
      { "regra_id": "R-1009-A", "casou": false, "motivo": "faixa não contém a quantidade (1–9, pedido 15)" },
      { "regra_id": "R-1009-B", "casou": false, "motivo": "faixa não contém a quantidade (20–99, pedido 15)" }
    ]
  }
}
```

## UC-2 — importação

`POST /importar` (multipart com o CSV) →

```json
{
  "importadas": 26,
  "rejeitadas": [
    { "linha": 9,  "motivo": "faixa invertida: De (100) > Ate (50)" },
    { "linha": 19, "motivo": "preço ausente" },
    { "linha": 20, "motivo": "preço negativo: -1,00" },
    { "linha": 24, "motivo": "valor não-monetário em campo de preço: '-10%'" },
    { "linha": 35, "motivo": "campo 'De' não numérico: 'a partir de 50'" },
    { "linha": 40, "motivo": "SKU inexistente no catálogo: SKU-9999" },
    { "linha": 30, "motivo": "linha duplicada (idêntica à linha 29)" }
  ],
  "paridade": {
    "conferem": 26,
    "divergencias": []
  },
  "validacao": {
    "erros": [
      { "tipo": "sobreposicao", "regra_ids": ["R-1003-B","R-1003-PROMO"], "descricao": "faixas 5–19 e 15–60 se sobrepõem em 15–19, ambas com prioridade 0 e mesma especificidade" },
      { "tipo": "preco_base_inconsistente", "sku": "SKU-1007", "descricao": "preço base aparece como R$ 29,90 (3 linhas) e R$ 31,00 (1 linha)" }
    ],
    "avisos": [
      { "sku": "SKU-1009", "descricao": "sem cobertura para 10–19 un e 100+ un — cairá no preço base" }
    ]
  }
}
```

**A publicação fica bloqueada** enquanto houver `erros`. Os `avisos` não bloqueiam
(AMB-5: lacuna reporta, não impede).

## UC-5 — log vs. recálculo (caso P-11)

`GET /decisao/{id}` devolve o que foi cobrado; `POST /decisao/{id}/recalcular`
devolve o que as regras atuais dizem sobre a mesma data. Os dois convivem:

```json
{
  "registrada": { "preco_unitario": "R$ 21,90", "versao_regras": 3, "registrada_em": "2026-02-10T14:22:01" },
  "recalculada": { "preco_unitario": "R$ 20,50", "versao_regras": 7 },
  "divergem": true,
  "nota": "A decisão registrada é a prova do que foi cobrado. O recálculo mostra o que as regras vigentes hoje dizem sobre 10/02/2026."
}
```
