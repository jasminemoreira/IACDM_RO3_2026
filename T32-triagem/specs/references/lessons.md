# Lições do ciclo v1.0 — T32-triagem

Lições sobre ESTE projeto e o que ele revelou. Escritas na Fase 7, para
alimentar um eventual v2 ou uma autópsia. Não são lições sobre a metodologia
em abstrato — são o que aprendemos fazendo este sistema.

## 1. A descoberta central veio da documentação de um concorrente, não do enunciado

O enunciado dizia "triagem com prioridade automática, reclassificação e recurso
do solicitante". Quatro substantivos soltos. O que os organizou foi uma linha
da documentação do GLPI (fonte F4): **a urgência é declarada pelo solicitante,
o impacto é atribuído pelo agente**.

Dessa assimetria de autoridade decorre tudo o mais: reclassificação e recurso
são *o mesmo mecanismo visto dos dois lados* — cada parte contesta o eixo que a
outra declarou. Ninguém contesta a prioridade, porque ela é derivada.

**Lição de domínio:** num sistema com dois eixos e dois atores, procure quem
declara cada eixo antes de desenhar qualquer fluxo. A estrutura política do
sistema estava escondida numa nota de rodapé sobre configuração de produto.

## 2. A literatura desaconselhava exatamente o que o enunciado exigia

A fonte F5 (Advisera / ISO 20000) diz que mudar prioridade no meio do ciclo de
vida deve ser evitado, porque as ferramentas ITSM têm problemas para recalcular
prazos de escalonamento. O enunciado exigia reclassificação *e* recurso — isto
é, exigia justamente a operação desaconselhada.

Isso não invalidou o projeto: promoveu **o comportamento do relógio de SLA sob
mudança de prioridade** de detalhe a requisito de primeira classe, decidido na
Fase 0 e não descoberto na Fase 5.

**Lição:** quando a literatura desaconselha o que o requisito pede, o
desaconselhado é o núcleo do projeto, não um obstáculo a contornar.

## 3. Uma regra na assinatura vale mais que a mesma regra num comentário

`sla.prazos(p, abertoEm)` não aceita `agora`. A decisão "recontar prazos desde
a abertura" — descartando "reiniciar na reclassificação" — deixou de ser algo a
lembrar e passou a ser algo impossível de errar: a função não recebe o dado que
a implementação errada exigiria.

O mesmo com `Prioridade`, tipo com marca cuja única origem é `derivar`, e com
`repositorio.salvar({entidade, eventos})`, que não tem versão que grave só o
estado.

**Lição de stack:** em TypeScript, marcar tipos e omitir parâmetros são as duas
formas mais baratas de transformar decisão de projeto em erro de compilação. A
mutação confirmou: quebrar a regra dos prazos derrubou 14 testes.

## 4. Uma guarda que existe e não guarda é pior que guarda nenhuma

`additionalProperties: false` no esquema de cada endpoint parecia proteger a
separação de autoridade dos eixos — a descoberta central do projeto. Não
protegia: o Fastify configura o AJV com `removeAdditional: true` por padrão, e
o campo alheio era **apagado em silêncio** em vez de recusado. O teste passava
porque o efeito era o mesmo; a guarda não existia.

Só apareceu porque uma requisição real foi feita e o código de status foi lido.

**Lição de stack (Fastify):** verifique o default de `removeAdditional`. E, em
geral: uma guarda cujo sucesso é indistinguível do silêncio precisa de um teste
que observe a RECUSA, não só a ausência do efeito.

## 5. As lentes olharam para "quem pode", nunca para "quando se decide quem"

Duas rodadas de crítica adversarial, 18 lentes, 78 achados. Nenhum tocou na
janela entre **renderizar** o formulário e **enviá-lo**.

Governança perguntou se toda ação é atribuível. Segurança perguntou como um
atacante exploraria. Processo perguntou se as transições estão completas. As
três examinaram *quem pode fazer o quê* — nenhuma perguntou *em que instante a
autoria é decidida*. O resultado: com duas abas e uma troca de usuário no meio,
a trilha registrava Carla como autora de um chamado que Ana escreveu. O sistema
cuja tese é atribuição auditável **mentia sobre autoria**, e os 68 testes
concordavam com a mentira.

Encontrou-se com um humano, um navegador e duas abas.

**Lição — e a mais importante deste ciclo:** análise estática de permissões não
alcança confusão temporal de identidade. Para a próxima vez, uma pergunta a
acrescentar a Governança ou Segurança: *"entre o instante em que esta ação é
composta e o instante em que é gravada, o que pode mudar?"*

## 6. A correção da rodada anterior é a fonte de defeito da rodada seguinte

Na iteração 2 da crítica, 3 dos 7 críticos eram **regressões introduzidas pela
correção da iteração 1**: MOV-2 duplicou o recálculo de prazos que V(1)
protegia por assinatura única; MOV-2 anunciou uma garantia ("impossível violar
a trilha") que não entregava — impossível era *não produzir* o evento, não *não
gravá-lo*; MOV-5 removeu a estatística de recursos e, com ela, a visibilidade
de que a política anti-abuso da Fase 0 dependia explicitamente.

V(2) era predominantemente **aditiva**. V(3) foi predominantemente
**subtrativa** — e seis dos sete movimentos removeram mecanismo.

**Lição:** correção aditiva cria superfície nova e merece nova crítica;
correção subtrativa, muito menos. A natureza da mudança prediz melhor o risco
residual do que a quantidade de módulos tocados.

## 7. A Fase 0 pode se contradizer, e a contradição só aparece na Fase 3

A Fase 0 decidiu "transparência + prescrição, **sem** penalidade" justificando
que *"o abuso fica visível"*. A mesma Fase 0 pôs **relatórios e dashboards no
escopo negativo**. As duas decisões não podem valer juntas: a visibilidade
agregada de que a política anti-abuso depende é exatamente o relatório
proibido.

Ninguém percebeu na Fase 0. Apareceu quando a Fase 3 removeu a estatística por
respeito ao escopo negativo e a lente Ética apontou que nada mais continha abuso.

**Lição:** decisões de escopo negativo e decisões de política podem se anular
mutuamente sem que nenhuma delas pareça errada isoladamente. Vale um passo de
verificação cruzada no fim da Fase 0: *cada justificativa registrada continua
verdadeira à luz de todo o escopo negativo?*

## 8. Premissas que ninguém declarou porque pareciam simétricas

A Fase 1 declarou A7 — *o solicitante age de boa-fé*. Ninguém declarou a boa-fé
do **agente**, embora o desenho dependesse dela igualmente: o agente atribui o
impacto e é medido pela violação de SLA que esse mesmo impacto produz, o que dá
incentivo direto a subestimar. A lente Teoria dos Jogos encontrou (JOG-01) e a
premissa A11 nasceu na Fase 3.

**Lição:** ao declarar uma premissa sobre a boa-fé de um ator, percorra os
outros atores e pergunte se a mesma premissa se aplica. A assimetria de
declaração revela a assimetria de atenção.

## 9. Três parâmetros, três lastros diferentes — e vale distinguir

A matriz 3×3 é convergência de mercado (Tier B, quatro produtos concordam). As
metas de SLA em minutos são exemplo de fornecedor (Tier C). O `prazoTriagem` não
tem lastro nenhum — nenhum dos quatro produtos pesquisados tem prazo de triagem
(Tier D, originado neste projeto).

Declarar isso no próprio `politica.json` custou três linhas e evitou que o
sistema afirmasse "ITIL manda 4 horas para P1", que seria falso.

**Lição:** classifique o lastro por parâmetro, não por documento. Um mesmo
artigo pode sustentar a estrutura e não sustentar os números.

## 10. Premissas que se mostraram erradas

- **"A ordenação da fila é um problema de desempenho."** Não era. Ordenar por
  prazo crescente já põe os violados no topo (violado ≡ prazo < agora), e o
  achado PER-01 evaporou sem mecanismo algum. Mas a "solução elegante"
  introduziu PER-04: prazo de triagem e prazo de resolução são grandezas
  diferentes, e num só eixo de ordenação um não triado de 60 min passava na
  frente de um P1 de 240 min. A resposta certa eram duas seções.
- **"Escapar HTML à mão é aceitável porque o problema é pequeno."** Continua
  verdade, mas quase deu errado por outro motivo: fragmentos aninhados eram
  escapados duas vezes. A solução foi tornar o escape *idempotente por
  marcação de tipo*, não confiar em não aninhar.
- **"Prioridade e prazos precisam ser colunas do banco."** Não precisavam. São
  derivados dos eixos na leitura, e isso eliminou por construção a divergência
  entre valor gravado e valor recalculável (CTL-01) — sem nenhum mecanismo de
  reconciliação.
