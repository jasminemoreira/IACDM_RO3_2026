# Adjudicação de ETI — resultado

**2026-08-13.** Fecho da última pendência aberta do lote. O resultado é o terceiro dos três
desfechos que o desenho previa: **não confirma nem refuta, e a razão disso é o achado.**

---

## A pergunta

A lente **Ética** ativou em **5 de 12** projetos pela Fase 2 e em **9 de 12** sob o gatilho
corrigido Y2, nos dois leitores externos. Nos quatro projetos disputados — Y2 liga, Fase 2
não ligou —, a classe de falha estava presente e foi capturada por lentes vizinhas, ou ETI
genuinamente não se aplicava?

Três tentativas de adjudicar caíram antes desta:

| via | por que caiu |
|---|---|
| contribuição exclusiva nos casos limpos | **pega emprestada a variável dependente** do estudo — só uso descritivo |
| concordância entre estimadores | mede reprodutibilidade da **ativação**, não correção |
| sonda lexical | **retratada** — media densidade de prosa sobre humanos e homônimos (`analise/sonda_eti_refutada.py`) |

O fecho pleno abandona proxies: **ler os achados**.

---

## O desenho

Fixado em `analise/CRITERIO-ADJUDICACAO-ETI.md`, **escrito e datado antes de extrair ou ler
qualquer achado** — a única defesa contra o erro que derrubou a sonda.

| | |
|---|---|
| **corpus** | todos os achados de **GOV** e **REG** dos sete projetos em que a Fase 2 não ativou ETI — **60 achados**, 40 disputados e 20 de controle |
| **critério** | (1) identifica parte **sujeita** ao sistema, não quem o opera; **e** (2) descreve dano/exclusão, ausência de recurso, ou ausência de transparência para essa parte |
| **cegamento** | sem projeto, sem lente, sem id original; ordem embaralhada por `sha256` |
| **juízes** | Claude e `gpt-5.4`, famílias diferentes, mesmo pacote e mesmo critério, independentes |
| **escala** | SIM · NÃO · DÚVIDA (nunca contada como SIM) |

Os três desfechos eram admissíveis por construção, incluindo "o julgamento não discrimina".

---

## O resultado

| juiz | disputados (n=40) | controle (n=20) | Fisher bicaudal |
|---|---|---|---|
| **Claude** | 6 (**15%**) | 3 (**15%**) | **p = 1,00** |
| **gpt-5.4** | 5 (12%) | 0 (0%) | p = 0,159 |
| consenso (ambos SIM) | 4 (10%) | 0 (0%) | p = 0,291 |

**Concordância entre juízes: 82% bruta · κ de Cohen = 0,341.**

**Nenhuma das três linhas separa os grupos.** A do Claude não discrimina de forma alguma —
15% exatos nos dois. A do GPT aponta na direção esperada e não alcança significância com
n=20 no controle.

---

## Onde os juízes divergem, e o que isso diz

Os três SIM que só o Claude deu no grupo de **controle** vêm todos do **T24-catalogo**, e
são substantivos:

| id | achado | leitura |
|---|---|---|
| **A-49** | identidade de `Owner` por contato normalizado **colapsa pessoas distintas** que compartilham caixa; o nome de uma é escolhido arbitrariamente | Claude: exclusão de uma pessoa · GPT: qualidade de dado |
| **A-33** | o produtor passa a figurar em análise de impacto de terceiros **sem consentir nem tomar ciência** | Claude: falta de transparência para parte afetada · GPT: governança |
| **A-09** | nome e e-mail corporativo são **dado pessoal sob LGPD**, sem base legal, finalidade nem retenção | Claude: direito do titular · GPT: conformidade |

E o único SIM que só o GPT deu, **A-60** — *"`Decisao` não guarda QUEM pediu o preço; «esse
desconto foi concedido a quem?» é impossível de responder"* —, o Claude leu como
rastreabilidade para auditoria.

**Nenhuma das duas leituras é obviamente errada.** É a fronteira entre "ética" e
"governança de dados", e o critério escrito antes não a fixou o bastante.

---

## O achado

> **A fronteira entre dano ético e governança não é reprodutível entre dois juízes
> competentes que receberam o mesmo critério, escrito antes, sobre achados cegados.**

κ = 0,341 sobre a pergunta *"isto é materialmente ético?"* reproduz, **no nível do
conteúdo**, exatamente o problema que a lente tem **no nível do gatilho**.

A dificuldade não está na redação do critério de ativação — está no conceito. Um gatilho
melhor não resolve uma fronteira que os leitores não compartilham.

Isto conversa diretamente com o resultado do §5.3 e com Regnell et al. (2000): até o
**julgamento sobre o julgamento** tem o problema de granularidade que o estudo inteiro
investiga.

---

## Consequência para a pendência

**A decisão sobre ETI em 9/12 permanece decisão de projeto**, e agora com evidência de por
quê: não falta dado, falta um conceito compartilhado de onde a ética termina e a governança
começa.

Registrar isso é mais informativo que qualquer dos dois desfechos binários que se
esperavam.

---

## Ressalvas

**Contaminação parcial do juiz Claude, declarada no critério antes de julgar.** Durante a
depuração da sonda, em 2026-08-12, ele leu amostras de contexto de seis achados que
continham `operador`, ao menos um de GOV. O achado em questão (**A-58**, *"o mesmo operador
que errou reverte a própria decisão"*) foi classificado como **NÃO**, seguindo a zona
cinzenta que o critério resolvia de antemão — logo a contaminação não explica a divergência
entre juízes.

**n=20 no controle.** Nem o resultado do GPT — 0 de 20 contra 5 de 40 — separa com
p = 0,16. Um corpus maior poderia decidir; este não decide.

**Dois juízes, ambos modelos.** Um terceiro juiz humano independente mudaria o peso do
resultado, e não foi feito.

---

## Material

| arquivo | conteúdo |
|---|---|
| `analise/CRITERIO-ADJUDICACAO-ETI.md` | o critério, datado antes da leitura |
| `analise/cego/ETI-adjudicacao-itens.txt` | os 60 achados cegados, como entregues aos juízes |
| `analise/cego/ETI-adjudicacao-mapa.json` | a tradução id cegado → projeto, lente, id original |
| `analise/cego/ETI-adjudicacao-claude.json` | vereditos do Claude |
| `analise/cego/ETI-adjudicacao-gpt.json` | vereditos do gpt-5.4 |
| `analise/sonda_eti_refutada.py` | a sonda lexical retratada, com a refutação no mesmo comando |
