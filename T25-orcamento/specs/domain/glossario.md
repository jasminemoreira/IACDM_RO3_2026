# Glossário do domínio — T25 (FinOps de IA / governança de custo de inferência)

Vocabulário canônico do projeto. Um termo, um significado. Sinônimos listados são
**proibidos** no código, nos specs e nos testes — a Fase 2 (lente Linguística) e a
Fase 5 vão cobrar consistência.

| Termo canônico | Definição | Evitar (sinônimo proibido) |
|---|---|---|
| **entidade consumidora** | **identidade técnica** rastreável que consome: projeto, serviço ou chave. Modelo plano, sem hierarquia. **Nunca corresponde a uma pessoa** — decisão do operador na Fase 3, em resposta a REG-01/ETI-02: assim `evento_uso` não é dado pessoal e o painel não é ferramenta de monitoramento individual. | "cliente", "tenant", "conta", "usuário" |
| **evento de uso** (usage record) | registro imutável de um consumo já ocorrido: entidade, modelo, tokens por categoria, custo calculado, instante. | "log", "transação" |
| **token de entrada** | token do prompt enviado ao modelo. Subdivide-se em não-cacheado, escrita de cache e leitura de cache — categorias com **preços diferentes**. | "prompt token", "token de input" |
| **token de saída** | token gerado pelo modelo. Custa tipicamente 5× o de entrada. | "completion token" |
| **rate card** (tabela de preços) | preço por 1M tokens, por (provedor, modelo, categoria de token), com data de vigência. | "tarifa", "preço" solto |
| **custo** | valor monetário derivado de tokens × rate card. Sempre em moeda, nunca em tokens. | "gasto", "despesa" |
| **teto** (budget) | valor máximo de custo acumulado permitido numa janela, para um escopo (global e/ou entidade). | "limite" solto, "quota" |
| **janela de orçamento** | intervalo recorrente sobre o qual o consumo acumula; o início de uma nova janela reseta o acumulado. | "período", "ciclo" |
| **reset** | virada de janela que zera o consumo acumulado e, por consequência, reverte o corte. | "renovação" |
| **saldo** | teto − custo acumulado na janela vigente. Pode ser negativo por overshoot residual. | "crédito", "budget restante" |
| **reserva** (hold) | débito provisório feito ANTES da chamada, no valor do pior caso (entrada exata + `max_tokens` × preço de saída). | "pré-autorização" |
| **reconciliação** | substituição da reserva pelo custo real, após a resposta trazer o `usage`. | "ajuste", "acerto" |
| **decisão** (permitir/negar) | resultado do portão de admissão para uma requisição, função do saldo vigente. | "autorização", "validação" |
| **corte** | estado em que novas requisições de uma entidade são negadas até reset ou intervenção. | "bloqueio" solto, "ban" |
| **portão de admissão** | ponto do gateway que decide antes de gastar. | "middleware", "interceptor" |
| **overshoot** | custo registrado acima do teto. Política do projeto: tolerância zero por decisão; o valor residual possível é consequência de concorrência e de requisições em voo, não de política. | "estouro" solto |
| **limite de taxa** (rate limit) | restrição temporal do provedor (RPM/ITPM/OTPM), sinalizada por HTTP 429 + `retry-after`. **Não** é teto de orçamento. | usar "limite" para os dois |

## Termos vagos do enunciado, já resolvidos (Fase 0, iteração 1)

| Enunciado | Resolvido como |
|---|---|
| "consumo" | custo de uso de API de LLM, derivado de tokens × rate card |
| "teto de orçamento" | valor em moeda, por janela recorrente com reset automático |
| "corte automático" | bloqueio duro (hard stop) de novo consumo, decisão síncrona |
| "painel" | superfície operada por pessoa (definição de forma pendente no Nível 5) |
