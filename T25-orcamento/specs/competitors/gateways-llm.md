# Estado da arte — gateways de LLM com controle de orçamento

**Pesquisado em:** 2026-08-10, via busca web. **Nível de confiança:** os fatos abaixo
vêm de páginas de comparação e do blog do próprio fornecedor; **não** foram verificados
contra a documentação oficial de cada produto nem contra o código-fonte. Antes de
copiar qualquer mecânica específica na Fase 1, confirmar na doc do produto.

## Produtos identificados

| Produto | Natureza | Mecânica de orçamento (conforme fontes) |
|---|---|---|
| **LiteLLM** | Gateway/proxy open-source | **Chaves virtuais**: cada time recebe uma chave virtual com orçamento mensal configurável. O gasto é rastreado contra o custo real do provedor. Existe um hook `model_max_budget_limiter` no proxy. |
| **Portkey** | Gateway comercial | **Budget manager** que monitora uso acumulado ao longo do tempo e dispara alertas conforme limiares são cruzados. |
| **Helicone** | Gateway com foco em observabilidade | Descrito como gateway rápido e de baixo overhead, forte em observabilidade. Mecânica de corte rígido **não confirmada** pelas fontes consultadas. |
| **OpenRouter** | Roteador multi-provedor hospedado | Citado como alternativa de build-vs-buy; mecânica de orçamento não detalhada nas fontes. |
| **Kong AI Gateway / Zuplo** | Gateways de API com extensão para IA | Citados em guias de comparação; mecânica não detalhada. |

## O que isso valida no desenho do T25

1. **O ponto de enforcement escolhido é o padrão de mercado.** Todas as soluções
   operam como "ponto único de estrangulamento" (single chokepoint) no caminho da
   requisição — a mesma decisão registrada em `get_decisions(phase=0)` para T25.
2. **Chave virtual = entidade consumidora.** A unidade de atribuição de custo do
   mercado é uma credencial emitida pelo gateway, não a credencial do provedor. Isso
   converge com o modelo plano de entidades de T25 e é uma resposta possível para
   "como o gateway sabe quem está chamando".
3. **Rastrear contra o custo real do provedor** (LiteLLM) confirma a necessidade do
   rate card como dado de primeira classe.

## Onde o T25 se diferencia (e onde não deve tentar competir)

- Portkey descreve **alertas em limiares**; T25 decidiu **bloqueio duro**. Alerta é o
  comportamento comum; corte rígido é a escolha deste projeto e é o que o critério de
  acerto vai medir.
- Estes produtos são multi-provedor, multi-região, com observabilidade completa. T25 é
  uma sessão de 2–4h e 8–12 módulos: **não** tentar paridade. O que se copia é a
  mecânica de orçamento e a noção de chave virtual, não o escopo do produto.

## Lacuna remanescente

Nenhuma fonte consultada explica **como esses produtos tratam concorrência** — o
problema central de T25 (A1: custo de saída desconhecido antes da chamada). Se o
gateway concorrente estima, reserva ou simplesmente aceita overshoot é a pergunta
técnica mais valiosa a fazer à documentação deles antes da Fase 1. O único precedente
com mecânica documentada em detalhe é o da própria Anthropic
(`../technical/rate-card-llm.md` §4), que aceita overshoot de até uma requisição por
thread — ou seja, **não** resolve o problema, delimita-o.
