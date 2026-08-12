# Referências externas — formatos, record linkage e conciliação

Pesquisa autorizada pelo operador na Fase 0 (decisão `PESQUISA AUTORIZADA`).
Regra vinculante: **nenhum parâmetro numérico entra no código sem constar aqui com fonte.**

---

## 1. OFX — Open Financial Exchange

### 1.1 Estrutura da transação (`<STMTTRN>`)

Campos obrigatórios em toda `<STMTTRN>`: `TRNTYPE`, `DTPOSTED`, `TRNAMT`, `FITID`.

| Campo | Semântica | Formato |
|---|---|---|
| `TRNTYPE` | Tipo da transação. Conjunto fechado: `CREDIT, DEBIT, DEP, INT, DIV, FEE, SRVCHG, ATM, POS, XFER, CHECK, PAYMENT, CASH, DIRECTDEP, DIRECTDEBIT, REPEATPMT, OTHER`. | enum |
| `DTPOSTED` | Data de postagem. | `YYYYMMDD`, opcionalmente `YYYYMMDDHHMMSS` (+ fuso) |
| `TRNAMT` | Valor, com sinal. Sem símbolo de moeda e sem separador de milhar. | decimal com sinal |
| `FITID` | Identificador da transação atribuído pela instituição. | string |
| `NAME` / `MEMO` | Contraparte / descrição livre. | string (opcional) |
| `CHECKNUM` / `REFNUM` | Número do cheque / referência. | string (opcional) |

Fonte: [OFX File Format Explained — bankxlsx](https://bankxlsx.com/blog/ofx-file-format-explained-tags-structure) ·
[OFX Validator Guide — Data Conversion Center](https://www.dataconversioncenter.com/blog/guide-ofx-validator/) ·
[OpenExchange Message Set Specification (xml.coverpages.org)](https://xml.coverpages.org/OFEXFIN1.html)

### 1.2 FITID — escopo de unicidade (**decisivo para o dedup**)

> "Uma FI atribui um FITID para identificar unicamente uma transação. Seu propósito primário é
> permitir que o cliente detecte respostas duplicadas."

Escopo declarado pela especificação:

> "FITIDs devem ser únicos **dentro do escopo das transações requisitadas — isto é, dentro de uma
> conta** — mas não precisam ser sequenciais nem crescentes."

E, explicitamente:

> "FITIDs **não são únicos entre instituições**. O cliente precisa usar **FI + conta + FITID** como
> chave única em sua base."

**Consequência de projeto (vinculante):** a chave de identidade nativa é a **tripla
`(instituição, conta, FITID)`**, nunca o `FITID` isolado. Usar FITID sozinho é um defeito de
correção, não uma otimização.

**Contra-evidência conhecida (premissa a declarar na Fase 1):** na prática, instituições violam a
garantia — há casos documentados de FITIDs que **mudam** entre downloads da mesma transação, e de
bancos que emitem FITIDs colidentes ou não conformes. O dedup **não pode assumir** que o FITID é
estável ao longo do tempo; ele é evidência forte, não prova.

Fontes: [OpenExchange Message Set Specification](https://xml.coverpages.org/OFEXFIN1.html) ·
[OFX FITIDs: Not as permanent as you might think — D. Barrett](http://blog.quinthar.com/2008/12/ofx-fitids-not-as-permanent-as-you.html) ·
[LCL ne respecte pas la norme OFX — Akretion](https://akretion.com/fr/blog/lcl-ne-respecte-pas-la-norme-ofx) ·
[HomeBank bug #1942379 — OFX import identificando duplicatas incorretamente](https://bugs.launchpad.net/homebank/+bug/1942379)

### 1.3 Biblioteca de parsing (candidata Tier 1)

**`ofxtools`** — biblioteca Python para OFX.
- Consome e produz **OFXv1 (SGML)** e **OFXv2 (XML)**; também lê QFX (ignorando tags proprietárias da Intuit).
- **Requer Python ≥ 3.10 e depende apenas da stdlib** (zero dependências externas).
- Converte para tipos nativos: valores monetários viram `Decimal`, datas viram `datetime` — alinhado ao invariante **I1**.
- API: `OFXTree` → `ofx.statements[0].transactions` → atributos `trnamt`, `dtposted`, …
- Maturidade declarada: mais de 10 anos de dados OFX de várias instituições passados pelo parser com resultados verificados.

Alternativa: **`ofxparse`** (BankAccount / CreditAccount / InvestmentAccount).

Fontes: [ofxtools — PyPI](https://pypi.org/project/ofxtools/) ·
[ofxtools — documentação do parser](https://ofxtools.readthedocs.io/en/latest/parser.html) ·
[csingley/ofxtools — GitHub](https://github.com/csingley/ofxtools)

---

## 2. Record linkage — base formal da deduplicação cross-source

### 2.1 Modelo de Fellegi-Sunter (1969)

Cada par de registros `(a, b)` pertence a `M = {(a,b) | a = b}` (mesmo evento) ou
`U = {(a,b) | a ≠ b}` (eventos distintos). Para cada campo comparado `i`:

- `m_i = Pr(cenário de comparação | os registros CASAM)`
- `u_i = Pr(cenário de comparação | os registros NÃO casam)`
- Fator de Bayes: `K_i = m_i / u_i`
- Peso parcial: `ω_i = log₂(K_i)`

Combinação:

```
odds posteriores = odds a priori × K₁ × K₂ × … × Kₙ
peso final       = peso a priori + ω₁ + ω₂ + … + ωₙ
probabilidade    = odds / (1 + odds)

Pr(match | dados) = (λ·m₁m₂…mₙ) / (λ·m₁m₂…mₙ + (1−λ)·u₁u₂…uₙ)
```

onde `λ` é a probabilidade a priori de dois registros ao acaso serem o mesmo evento.

**Advertência do autor da referência:** as probabilidades numéricas produzidas pelo modelo são
frequentemente estimativas ruins da probabilidade real de match — **prefira operar sobre o peso
(match weight) do que sobre a probabilidade convertida.**

Fontes: [The mathematics of the Fellegi-Sunter model — R. Linacre](https://www.robinlinacre.com/maths_of_fellegi_sunter/) ·
[An Interactive Introduction to Record Linkage — R. Linacre](https://www.robinlinacre.com/intro_to_probabilistic_linkage/)

### 2.2 Blocking (indexação) — controle do custo quadrático

Comparar todos os pares é `O(n²)`: 50.000 transações ⇒ ~1,25 × 10⁹ pares. Inviável para o
requisito de < 60s.

> "Blocking é um tipo de indexação que particiona os vetores de comparação. Pares de registros são
> **descartados a menos que concordem na chave de bloco**." A união de múltiplos blocos é chamada
> *indexação por disjunção*.

**Consequência de projeto:** o dedup cross-source **precisa** de uma etapa de blocking antes da
comparação par-a-par. Chave de bloco natural neste domínio: `(valor absoluto exato, janela de data)` —
disjunção com `(valor arredondado, contraparte normalizada)` para tolerar divergência de centavos.

Fontes: [Probabilistic Record Linkage and Deduplication after Indexing, Blocking, and Filtering — arXiv:1603.07816](https://arxiv.org/abs/1603.07816) ·
[Journal of Privacy and Confidentiality](https://journalprivacyconfidentiality.org/index.php/jpc/article/view/643) ·
[blocking: An R Package for Blocking of Records — R Journal 2026](https://journal.r-project.org/articles/RJ-2026-029/)

---

## 3. Conciliação bancária — prática contábil estabelecida

### 3.1 Taxonomia de exceções (o que NÃO casa, e por quê)

Cinco tipos primários:

1. **Diferenças de tempo** — item registrado de um lado e ainda não do outro. **Responde por 40-60% dos não-casados** em execuções típicas de conciliação.
2. **Pagamentos duplicados** — entradas idênticas por erro de digitação ou falha de sistema.
3. **Itens bancários não registrados** — tarifas, juros, transferências lançadas pelo banco e ausentes do livro.
4. **Transferências entre entidades** — movimentação com postagem assíncrona nos dois lados.
5. **Pagamentos parciais / processamento em lote** — transações não simétricas (conversão de moeda, dedução de taxas) ⇒ relações 1:N e N:1.

Estados adicionais citados: itens obsoletos (*stale* — cheques além da janela normal de compensação),
sinais de fraude, erros do banco, transações de alta variabilidade.

**Consequência de projeto:** órfão **não é sinônimo de erro**. Como diferenças de tempo dominam os
não-casados, o relatório precisa distinguir "órfão esperado (dentro da janela de compensação)" de
"órfão anômalo" — caso contrário o analista afoga em ruído.

Fonte: [Bank Reconciliation Isn't Just Matching: How to Handle Exceptions — Entries](https://www.tryentries.com/blog/bank-reconciliation-exceptions-framework) ·
[Common Bank Reconciliation Problems — CCMonet](https://www.ccmonet.ai/blog/common-bank-reconciliation-problems-missing-duplicate-and-unmatched-transactions)

### 3.2 Faixas de confiança e roteamento (prática de mercado)

Prática documentada em ferramentas de conciliação:

| Faixa de similaridade | Ação |
|---|---|
| 95-100 | auto-concilia sem revisão humana |
| 85-94 | auto-casa, com amostragem periódica para revisão |
| 70-84 | roteia para revisor humano, com o score como apoio à decisão |
| < 70 | tratamento padrão de exceção (não casa) |

Limiar típico de "alta confiança": **85-90**.
Algoritmos de similaridade citados: **Levenshtein**, **Jaro-Winkler**, matching por tokens.
Técnica de custo citada: **blocking** por faixa de valor, janela de data ou primeiros caracteres
**antes** de aplicar o algoritmo difuso caro — converge com §2.2.

Exemplo de regra concreta citado na literatura de mercado (ilustrativo, não normativo):
**valor casa dentro de US$ 0,50 e data dentro de 3 dias**.

Fontes: [Fuzzy Matching Algorithms in Bank Reconciliation — Optimus](https://optimus.tech/blog/fuzzy-matching-algorithms-in-bank-reconciliation-when-exact-match-fails) ·
[Bank Reconciliation Exceptions Framework — Entries](https://www.tryentries.com/blog/bank-reconciliation-exceptions-framework) ·
[Bank Reconciliation Software Matching — Treasury Software](https://www.treasurysoftware.com/bank-reconciliation/bank-reconciliation-software-matching.aspx)

**Ressalva registrada:** as faixas 95/85/70 são prática de mercado publicada por fornecedores, **não
resultado peer-reviewed**. São aceitáveis como ponto de partida calibrável, e devem ser tratadas
como parâmetro configurável com valor default documentado — nunca como constante mágica no código.
