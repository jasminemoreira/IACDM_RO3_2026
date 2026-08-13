# Critério de adjudicação de ETI — fixado ANTES da leitura

**Escrito em 2026-08-13, antes de extrair ou ler qualquer achado.** Esta ordem é a única
defesa contra o erro que derrubou a sonda lexical: lá eu acreditei numa separação sem
testar o que a produzia. O análogo aqui seria ajustar o critério ao que se vai lendo.

## A pergunta que está sendo adjudicada

ETI ativou em **5 de 12** projetos pela Fase 2 e em **9 de 12** sob o gatilho Y2, nos dois
leitores externos. Nos quatro projetos disputados — Y2 liga, Fase 2 não ligou —, a classe
de falha ética estava presente e foi capturada por lentes vizinhas, ou ETI genuinamente não
se aplicava?

| resultado | leitura |
|---|---|
| substância ética presente nos disputados e ausente no controle | **9 é correção** — a Fase 2 sub-ativava |
| substância igual nos dois grupos | **o julgamento não discrimina** — nada se conclui |
| substância ausente nos disputados | **9 é erosão** — o gatilho alargou demais |

Os três desfechos são admissíveis. O segundo e o terceiro precisam poder acontecer.

## O critério

Um achado é **materialmente ético** quando satisfaz as duas condições:

**(1) Identifica uma parte SUJEITA ao sistema** — alguém sobre quem o sistema decide, ou
que sofre efeito da decisão —, e não apenas quem **opera** o sistema ou o método.

> Exclui explicitamente o *operador da metodologia* (quem conduz as fases IACDM) e o
> operador técnico agindo como tal. Inclui a mesma pessoa quando ela aparece como alvo de
> uma decisão do sistema.

**(2) Descreve ao menos um destes**, em relação a essa parte:

| | |
|---|---|
| **a. dano ou exclusão** | a parte perde algo, é bloqueada, penalizada, cobrada indevidamente, ou fica de fora de um benefício |
| **b. ausência de recurso** | não há como contestar, corrigir ou reverter uma decisão que a afeta |
| **c. ausência de transparência** | a parte não consegue saber que a decisão ocorreu, por quê, ou com base em quê |

Isto é a substância da pergunta central de ETI: *"quem pode ser prejudicado? há auditoria,
correção e transparência?"*

## O que NÃO conta

| não conta | por quê |
|---|---|
| rastreabilidade para auditoria interna — "quem fez o quê" | atribuição sem parte afetada nomeada é governança |
| conformidade com norma como tal — "não atende ao art. X" | é regulatório; só conta se descrever o dano que a norma previne |
| propriedade/curadoria de dado sem parte afetada | governança |
| controle de acesso como propriedade de segurança | segurança |
| segregação de funções focada em **quem decide** | governança — a menos que nomeie o efeito sobre o decidido |

A fronteira decisiva: **quem aparece no achado é o decisor ou o decidido?** Se só o
decisor, não conta.

## Zona cinzenta, resolvida de antemão

Achado que descreve **falta de segunda instância** ("o mesmo ator reverte a própria
decisão") conta **apenas se** o texto mencionar a parte afetada pela decisão revertida.
Sem essa menção, é segregação de funções → governança.

Achado sobre **explicabilidade de uma decisão** conta como (c) **apenas se** o destinatário
da explicação for a parte afetada, não o auditor ou o operador.

## Escala de julgamento

Três valores, sem meio-termo:

- **SIM** — satisfaz (1) e (2).
- **NÃO** — não satisfaz.
- **DÚVIDA** — o texto de uma linha não permite decidir.

`DÚVIDA` é reportada à parte e **não** contada como SIM em nenhuma agregação.

## Desenho

**Corpus.** Todos os achados das lentes **GOV** e **REG** dos sete projetos em que a Fase 2
**não** ativou ETI. Quatro disputados (Y2 liga) e três de controle (Y2 não liga).

**Cegamento.** Os achados vão ao juiz sem projeto, sem lente, sem id original, em ordem
embaralhada por `sha256`. O juiz não sabe de qual grupo cada achado vem, nem quantos há em
cada grupo.

**Juízes.** Dois, independentes: Claude (este analista) e `gpt-5.4`, de família diferente.
Cada um recebe o mesmo pacote e o mesmo critério. Concordância reportada.

**Agregação.** Taxa de SIM por grupo, com o denominador sendo o total de achados GOV+REG
daquele grupo. Comparação entre grupos disputado × controle.

## Ameaça declarada

**Contaminação parcial do juiz Claude.** Durante a depuração da sonda lexical, em
2026-08-12, eu li amostras de contexto de seis achados que continham o termo `operador`, e
ao menos um era de GOV — *"não declara papel nem segunda instância: o mesmo operador que
errou reverte a própria decisão"*. Não sei de qual projeto veio.

Isto é contaminação pequena mas real, e é a razão de o segundo juiz existir. Se os dois
divergirem, a leitura do GPT é a não contaminada.

## O que este fecho NÃO resolve

Não diz se o **texto do gatilho Y2** é bom. Diz se a **classe de falha** estava presente nos
projetos disputados. Um gatilho pode acertar a ativação pelo motivo errado.
