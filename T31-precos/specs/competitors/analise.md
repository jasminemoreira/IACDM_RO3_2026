# Análise competitiva — o que já existe e por que não resolve

Levantamento de conhecimento consolidado (pesquisa web não autorizada na Fase 0;
sem URLs). O objetivo não é escolher um produto, é **delimitar o gap** que
justifica construir, e colher o que cada categoria já resolveu bem.

## Categoria 1 — Motores de regras de propósito geral

| Solução | O que resolve | Por que não serve aqui |
|---|---|---|
| **Drools** (Java, RETE/PHREAK, com DMN) | Motor maduro, hit policies, versionamento de KJARs, workbench para autor de negócio | Peso desproporcional: JVM + DSL própria (DRL) para ~1k regras de faixa. A explicação nativa é de *agenda/ativação*, não do formato contrastivo "por que não ganhei o desconto X". Curva do DRL recai sobre o analista |
| **json-rules-engine / node-rules** (JS) | Regras declarativas em JSON, leves, embutíveis | Não têm versionamento com vigência, nem log de decisão, nem validação de coerência de faixas — que são 3 dos 4 critérios de sucesso |
| **Zen Engine / GoRules** (DMN, Rust/Node) | Implementação de DMN com decision tables e hit policy | Traz o modelo certo de precedência, mas o produto é o *runtime*: importação da planilha suja, prova de paridade e trace contrastivo continuam por conta do integrador |
| **Open Policy Agent (Rego)** | Política declarativa, avaliação rápida, decision logs | Desenhado para autorização, não para aritmética monetária; Rego é hostil ao analista de preços |

**O que aproveitar:** a **hit policy explícita** do DMN (adotada) e a ideia de
*decision log* do OPA (adotada). **Confirmação importante:** nenhum motor
genérico entrega, de fábrica, a explicação contrastiva nem a prova de paridade
contra o legado — que é exatamente o valor deste projeto.

## Categoria 2 — Plataformas de precificação (CPQ / price management)

| Solução | O que resolve | Por que não serve aqui |
|---|---|---|
| **Pricefx, PROS, Vendavo, Zilliant** | Suíte completa: faixas, matrizes, aprovação, simulação, histórico, analytics | Escala e preço de plataforma corporativa; implantação em meses. Resolve um problema uma ordem de grandeza maior que "substituir uma planilha" |
| **SAP/Oracle pricing (condition tables)** | Condições por escala de quantidade, sequência de acesso, validade por data | O mecanismo de *access sequence* é justamente uma resolução de conflito por especificidade — validação independente do desenho adotado. Mas exige o ERP inteiro |
| **Stripe/Chargebee tiered pricing** | Faixas por quantidade (`tiered`/`volume`/`graduated`), API limpa | Modelo de assinatura, não de catálogo B2B; sem versionamento auditável de regra nem explicação da decisão |

**O que aproveitar:** a distinção **`volume` vs. `graduated`** dos motores de
assinatura é uma armadilha de domínio real — em `volume`, *toda* a quantidade
usa o preço da faixa atingida; em `graduated`, cada faixa cobra sua parte.
**Este projeto adota `volume`** (a faixa atingida define o preço unitário de todas
as unidades), que é o comportamento de uma planilha de preço por quantidade.
Registrar isso é o que evita implementar o modelo errado silenciosamente.

## Categoria 3 — O incumbente real: a planilha

| Aspecto | Planilha | Motor proposto |
|---|---|---|
| Custo de edição | Zero, imediato, familiar | Precisa de UI que não seja pior que a planilha |
| Coerência | **Nenhuma validação** — faixa sobreposta, lacuna e célula errada passam | Validador barra a publicação (CS-3) |
| Explicação | O número, sem o raciocínio | Trace contrastivo + frase (CS-2) |
| Histórico | "salvar como cópia" | Versão imutável + log de decisões (CS-4) |
| Consumo por sistema | Copiar/colar, exportação manual | API |
| Exatidão | Float binário + arredondamento de exibição | Decimal exato (I-5) |

**A planilha ganha em uma coisa: velocidade de edição.** É o risco competitivo
do projeto — se a UI de regras for mais lenta ou mais confusa que editar
células, o analista volta para a planilha e o motor vira leitura. Registrado como
premissa a atacar na Fase 2 (lente UI/UX).

## Gap que justifica construir

Nenhuma solução existente entrega, junto, as quatro coisas exigidas:
**(a)** importação da planilha suja **com prova de paridade**, **(b)** explicação
**contrastiva** da decisão, **(c)** validação de coerência **antes** da
publicação, **(d)** recálculo por data — em um artefato local, single-user, sem
plataforma corporativa.
