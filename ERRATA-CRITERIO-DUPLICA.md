# Errata — a cláusula final do critério de `duplica` (BATCH-PROTOCOL §3)

**2026-08-14.** Nota de esclarecimento. **O protocolo não é alterado** — está congelado e é
o pré-registro contra o qual o lote correu. Esta errata diz qual é a leitura correta, sem
tocar no documento.

---

## O texto

§3, última frase do critério de `duplica`:

> *"Na dúvida, **não** marque duplicata e registre a dúvida na descrição — subdeclarar
> duplicata enviesa a favor da ortogonalidade (a hipótese), então o erro conservador é o
> oposto do que favorece o método."*

E o §7, referindo-se à mesma regra:

> *"O §3 fixa critério explícito e **viés conservador (na dúvida, não duplicar)** para
> reduzir isso"*

---

## O que está certo

**A primeira metade é correta e importante.** Subdeclarar duplicata produz mais clusters;
mais clusters tornam mais provável que uma lente seja a única ocupante de um cluster; isso
**infla a contribuição exclusiva**, que é a variável dependente da RO3.

Direção do viés: **subdeclarar favorece a hipótese** de ortogonalidade.

## Onde está a confusão

A palavra **"conservador"** aparece em dois sentidos incompatíveis, e o `então` liga um ao
outro como se um decorresse do outro:

| sentido | o que significa | o que recomenda |
|---|---|---|
| **(1) conservador quanto à afirmação** | não asseverar o que não se pode estabelecer; marcar duas coisas como o mesmo defeito é uma afirmação positiva, não marcar é abster-se | **não marcar** na dúvida |
| **(2) conservador quanto à própria hipótese** | errar contra o resultado que se quer encontrar | **marcar** na dúvida |

A instrução — *"na dúvida, não marque"* — segue o sentido **(1)**. A justificativa
oferecida logo depois — *"o erro conservador é o oposto do que favorece o método"* — é
verdadeira no sentido **(2)**, e nesse sentido ela **contradiz a instrução** em vez de
apoiá-la.

O `então` sugere derivação onde há oposição. Daí a ambiguidade, que chegou a induzir uma
inversão de direção na redação do artigo (já corrigida antes da submissão).

## A leitura correta, em uma frase

> A regra operacional do §3 é conservadora **quanto ao ato de marcar**, e por isso mesmo é
> **anticonservadora quanto à hipótese**: ela enviesa a medida a favor da ortogonalidade.
> O viés é conhecido, tem direção conhecida, e **não** é neutralizado pela própria regra.

---

## O corretivo, que estava no desenho

A remarcação cega existe exatamente para limitar esse viés, e a **união** das clusterizações
é o corretivo desenhado para ele.

A união funde todo par que **qualquer** avaliador agrupou. É a leitura **maximamente
agressiva** — a que mais reduz contribuição exclusiva, portanto a mais hostil à hipótese.
Se a subdeclaração do gerador estivesse inflando o resultado, é aqui que apareceria.

| clusterização | clusters | leitura |
|---|---|---|
| gerador (a regra do §3) | **1.029** | a mais permissiva com a hipótese |
| qwen full | 960 | |
| gpt-5.4 | 788 | |
| **união dos quatro** | **668** | **a mais hostil à hipótese** |

**A subdeclaração era substancial** — 361 clusters de diferença entre a marcação do gerador
e a união, 35% do total. E **o resultado sobrevive**: nenhuma lente chega a contribuição
exclusiva zero sob nenhuma das quatro, com o mínimo em MIG com 3 sob a união.

É por isso que o resultado principal deve sempre ser reportado com a tabela das quatro
clusterizações, e não só com a do gerador. Não é rigor decorativo: é o que impede que o
viés do §3, cuja direção é conhecida, se converta em conclusão.

---

## Também errado no pipeline, e corrigido

O mesmo par de sentidos aparecia na docstring de `analise/ro3_analise.py`, que é o código
que computa a variável:

> *"O viés conservador do §3 (na dúvida, não marcar duplicata) empurra a favor da
> ortogonalidade… Subdeclarar duplicata INFLA a contribuição exclusiva; o erro conservador
> seria superdeclarar."*

Chamava a regra de conservadora e, três linhas depois, dizia que o erro conservador seria o
oposto dela. Reescrito na v1.3 do pacote para usar um vocabulário só. O texto do protocolo
permanece intocado; a docstring, não — ela não é pré-registro, é ferramenta, e ferramenta
que se contradiz é defeito.

---

## O que esta errata NÃO faz

Não muda nenhum número, nenhuma conclusão, e nenhuma linha do protocolo. Nenhuma medida
dependia da frase: a análise sempre usou a marcação como está registrada nas matrizes, e a
tabela das quatro clusterizações já estava no resultado desde o fechamento.

O que muda é a **descrição** do viés — e que ela agora usa uma palavra num sentido só.
