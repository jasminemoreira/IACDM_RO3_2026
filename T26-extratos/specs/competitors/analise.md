# Análise de concorrentes / estado da arte

Objetivo: descobrir como ferramentas maduras resolvem dedup na importação de extratos, para não
reinventar (S6 Tier 1/2) e para identificar a lacuna que T26 preenche.

| Ferramenta | Estratégia de dedup | Conciliação contra livro? | O que aproveitamos |
|---|---|---|---|
| **ledger-autosync** ([GitHub](https://github.com/egh/ledger-autosync)) | Grava uma **metatag em cada posting emitido**: `ofxid` para imports OFX e `csvid` para CSV. Na importação seguinte, só cria transações ausentes do arquivo ledger. | Parcial — o ledger é o livro | **O padrão de referência:** persistir a identidade de origem *junto do registro importado*, com **chave distinta por tipo de fonte**. Valida diretamente as camadas L1/L2 de `technical/parametros-matching.md`. |
| **beancount-import** ([GitHub](https://github.com/jbms/beancount-import)) | Associa robustamente a transação importada ao dado de origem; postings marcados com metadado específico da fonte, ex. `ofx_fitid`. Importação **semi-automática** — humano no laço. | Sim, contra o livro Beancount | Confirma duas escolhas nossas: metadado de origem por fonte, e **revisão humana como parte do fluxo**, não como falha. |
| **rustledger** ([GitHub](https://github.com/rustledger/rustledger)) | Pipeline de import com parsing CSV/OFX, detecção de duplicatas, categorização e reconciliação de saldo. | Sim | Confirma o recorte de módulos (parser → dedup → conciliação → saldo) como decomposição usual do problema. |
| **ledger-importer** ([PyPI](https://pypi.org/project/ledger-importer/0.5.2/)) | Dedup **entre múltiplas contas** com regra customizável pelo usuário. | Não | Precedente para dedup cross-source com regra configurável em vez de heurística fixa. |
| **Ferramentas de conciliação de mercado** (Treasury Software, Optimus, Entries) | Matching por faixas de confiança (95/85/70), blocking por faixa de valor e janela de data antes do fuzzy, roteamento de exceções para fila humana. | Sim, é o produto | Origem dos parâmetros P3-P5 e P7. Também a taxonomia de exceções. |

## Convergências (o que a prática já resolveu — não reinventar)

1. **Identidade de origem persistida no registro importado**, com chave distinta por tipo de fonte (`ofxid` vs `csvid`). Duas ferramentas independentes chegaram nisso.
2. **Blocking antes do fuzzy.** Unânime entre as ferramentas de mercado.
3. **Humano no laço para o ambíguo.** beancount-import é explicitamente semi-automático; ferramentas de mercado roteiam a faixa 70-94 para revisor.
4. **Estados de exceção nomeados**, não um booleano "casou/não casou".

## Lacuna que T26 ocupa

As ferramentas plain-text (ledger-autosync, beancount-import) resolvem dedup **de reimportação** com
excelência, mas tratam pouco a **duplicata cross-source** — quando o mesmo evento chega por duas
fontes com identidades nativas incompatíveis. As ferramentas de mercado tratam isso, mas são
SaaS fechado com custo e com os dados saindo da máquina.

T26 = dedup **em duas classes** (determinística + probabilística) **com decisão humana persistida e
reaproveitada**, local, com critério de acerto mensurável.

## Risco de escopo detectado

Todas as ferramentas comparáveis embutem também **categorização/classificação de transações**
(sugerir a conta contábil). Isso está **fora do escopo** de T26 — registrar em `outOfScope` na
Fase 1 para não vazar como scope creep na Fase 3 (AP9).
