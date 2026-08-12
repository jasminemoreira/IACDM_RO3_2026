# Lições do ciclo 1 — T31 motor de regras de preço

Lições sobre **este projeto**, não sobre a metodologia. Insumo do ciclo 2.

---

## 1. As premissas que caem são sobre o AMBIENTE, não sobre o domínio

Quatro rodadas de crítica adversarial produziram 109 achados com 17 lentes
sobre 12 módulos. **Nenhuma delas pegou os seis defeitos reais do ciclo** — e
os seis são da mesma família:

| Premissa que caiu | O que ela assumia | O que a plataforma concede |
|---|---|---|
| `precificar → Decisao` | que o motor podia montar a decisão inteira | `Decisao` tem `registrada_em`, e A-04 proíbe o motor de ler o relógio |
| A-06 "sem trava" | um usuário = uma thread | o ASGI despacha handlers síncronos num threadpool |
| Trava de publicação em memória | que o processo vive o bastante | um restart apaga tudo que não foi persistido |
| Trava persistida | que o fato importado descreve o rascunho atual | divergem no primeiro clique de edição |

O padrão: a lente **Assumptions** examinou o que o *design* assume. Nenhuma das
dezessete examinou **o que a plataforma garante**, nem **por quanto tempo um
fato continua verdadeiro**. As duas perguntas que faltaram, e que valem para
qualquer projeto com runtime e persistência:

> *"Que propriedade do ambiente este desenho está assumindo sem verificar?"*
> *"Este dado descreve um fato de que instante — e por quanto tempo ele vale?"*

## 2. Toda restrição precisa do mesmo tempo de vida do dado que restringe

O defeito mais instrutivo do ciclo, e ele apareceu **duas vezes, em direções
opostas**:

- **Volátil demais:** a evidência que bloqueava a publicação vivia em memória.
  Restart → bloqueio some → versão publicável com preço base escolhido em
  silêncio. A dor #2 (erros silenciosos) voltava pela porta dos fundos.
- **Durável demais:** ao persistir a evidência, ela virou eterna. O analista
  excluía todas as regras do SKU em conflito — ação correta — e o bloqueio
  nunca cedia. **Onze tentativas sem saída possível.**

A regra que ficou: *uma restrição deve durar exatamente enquanto durar a razão
dela.* Nem menos (some no restart), nem mais (bloqueia para sempre). E os dois
testes de regressão prendem as duas pontas de propósito — consertar uma sem a
outra reintroduz o oposto.

## 3. O núcleo com spec normativa não deu problema; a fronteira sem spec deu

Distribuição dos 109 achados: os quatro módulos de **fronteira**
(`importador-csv`, `servico-aplicacao`, `repositorio-sqlite`, `ui-web`)
concentraram **60%**. O núcleo algorítmico (`dinheiro`,
`resolvedor-precedencia`, `motor-precificacao`, `explicador`) atraiu **7**.

Não é que o núcleo seja fácil — precedência com prioridade, especificidade e
vigência não é trivial. É que ele recebeu, na Fase 0, um **algoritmo normativo
escrito** (`glossario.md` §Resolução de conflito), invariantes numerados e
casos-armadilha com resultado esperado. As fronteiras receberam prosa.

**Para o ciclo 2:** o esforço de especificação deve ir para onde o dado *entra*
e *sai*, não para onde o algoritmo é difícil.

## 4. Mudança que subtrai converge; mudança que acumula gera achado

Medido ao longo das quatro rodadas:

| | It.1 | It.2 | It.3 | It.4 |
|---|---:|---:|---:|---:|
| Achados | 60 | 22 | 15 | 12 |
| Críticos | 10 | 2 | 0 | 0 |
| Mudança estrutural da resposta | 67% | 25% | 17% | 8% |
| Δ LOC | +19% | +2,5% | +1,7% | +0,2% |
| **Iatrogênicos** | — | 32% | 33% | **50%** |

O contraste decisivo veio da iteração 2: `motor-precificacao` foi alterado e
**zerou** achados — porque *perdeu* uma dependência. `importador-csv` *ganhou*
três responsabilidades e liderou os achados duas rodadas seguidas.

E a taxa iatrogênica subindo para 50% enquanto a severidade cai a zero é a
assinatura de um sistema onde iterar passa a produzir principalmente o eco das
próprias correções. **Foi o sinal de parada honesto.**

## 5. Armadilhas concretas do domínio e da stack

**Domínio:**
- `volume` vs `graduated` muda o preço final e não é óbvio: 100 un na faixa
  50-199 a R$2,10 dá **R$210,00** (volume) ou **R$221,60** (graduated). A
  planilha legada significa *volume*. Decidir isso por conta própria teria
  invalidado a paridade inteira.
- "SKU inexistente no catálogo" **não é decidível** quando o catálogo é
  derivado da própria planilha. Só existe ao reimportar sobre catálogo
  preexistente. O ground truth original errava nisso.
- Preço base divergente para o mesmo SKU **não é erro de linha**, é erro de
  produto — e por isso não se resolve rejeitando linha.

**Stack:**
- `pytest.ini` com `-q` em `addopts` + `-q` na linha de comando = `-qq`, que
  **suprime a linha de resumo**. O gancho de verificação leu isso como falha e
  travou o portão. Uma flag inocente produziu um falso negativo.
- Espaço não-quebrável escrito como literal **colapsa em espaço comum** ao
  gravar o arquivo. Só sobrevive como escape ` ` — e sem isso a tolerância
  existiria apenas no comentário.
- `check_same_thread=False` no SQLite não basta: sem lock cobrindo
  BEGIN..COMMIT, a atomicidade de I-4 é ilusória em runtime multi-thread.
- CSV injection tem um efeito colateral: prefixar `'` na exportação **quebra a
  idempotência** do round-trip, a menos que a importação remova o `'`
  *somente* quando ele precede caractere de fórmula.

## 6. O julgamento humano encontrou o que a automação não sabia procurar

O smoke test dava tudo verde enquanto o operador encontrava três defeitos —
um deles grave. E os dois vereditos que mais importam para o produto **não são
verificáveis por teste**:

- **UX-01** — *"é melhor pq o fluxo é integrado, mas faltam filtros"*. A
  automação prova que a colagem de TSV funciona; só um humano diz se a tela
  ganha da planilha. Ganhou em fluxo, perde em volume.
- **UX-03** — *"está claro"* sobre registrado × recalculado. O teste verifica
  que os dois valores aparecem. Só o humano verifica que a **diferença entre
  eles é entendida** — e era o ponto onde o achado previa confusão com
  consequência financeira.

## 7. Um erro meu que vale como lição de processo

Afirmei duas vezes, no registro permanente, que *"UC-3 nunca foi executado por
humano — zero POST /regras no log"*. Havia **12**. Eu li o log de um servidor
num instante anterior às tentativas e converti ausência de evidência em
evidência de ausência. O operador corrigiu.

O rigor que se exige de um achado — evidência concreta, não impressão — vale
igualmente para o que se escreve **sobre o próprio processo**. Um registro
errado é pior que um registro ausente, porque parece confiável.

## 8. Ferramenta de verificação: duas fragilidades demonstráveis

O portão P6→P7 exige que um gancho testemunhe a suíte verde. Ele bloqueou
apesar de **seis execuções verdes verificáveis**. Duas causas de projeto que
foram demonstradas — e uma que **não** foi, registrada como não determinada.

**A. Classificar por texto em vez de código de saída.** O gancho lê marcadores
no stdout (`N passed`). O `pytest.ini` deste projeto traz `-q` em `addopts`;
acrescentar `-q` na linha de comando dá `-qq`, que **suprime a linha de resumo
inteira**. Uma suíte 100% verde fica inclassificável, e o portão trava. O código
de saída do processo era `0` e inequívoco — e não foi usado.

**B. "Não observado" é indistinguível de "observado e reprovado".** A mensagem
de bloqueio diz apenas *"the engine did not witness a passing test run"*. Para
descobrir que o motor guardava um `fail` obsoleto foi preciso **ler
`.versus/state.json` diretamente**, contornando a interface MCP que a
metodologia oferece. Sem esse recurso, o operador fica preso sem diagnóstico.

**C. Não determinado.** Em experimento controlado — ler estado, rodar `pytest`
verde, reler estado — o valor ficou **idêntico**: o gancho não disparou. Mas a
declaração está bem-formada, ganchos irmãos funcionam (o `PreToolUse/Bash`
bloqueou um `rm` de verdade), e o gancho grava corretamente quando invocado à
mão. **Por que não dispara, não sei** — e por isso não chamo de defeito da
ferramenta. A lição 7 acabou de registrar o custo de afirmar fato negativo a
partir de observação parcial; repeti-lo na página seguinte seria o pior tipo de
lição.

*Sugestão para a ferramenta:* classificar por código de saída, e a mensagem de
bloqueio dizer **o que o motor viu por último e quando**.
