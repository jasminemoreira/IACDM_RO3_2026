# Fundamentos teóricos — manter um teto sobre uma soma, sob concorrência

O problema central de T25 não é novo e não é folclore de engenharia: manter o
invariante `soma_dos_custos ≤ teto` enquanto múltiplas transações concorrentes
incrementam essa soma é um problema clássico de bancos de dados, com literatura
revisada por pares. Codificar isso "no feeling" é AP7 (implementar sem referência).

**Nível de verificação:** F9 e F10 foram confirmados por busca em 2026-08-10 (título,
veículo, ano e ideia central). F11 e F12 são referências canônicas que **não** foram
verificadas nesta sessão — checar antes de citar em qualquer artefato externo.

---

## F9 — O padrão de reserva tem nome: método Escrow (1986)

> P. E. O'Neil. **"The Escrow Transactional Method."**
> *ACM Transactions on Database Systems (TODS)*, v. 11, n. 4, dez. 1986.
> DOI: 10.1145/7239.7265 · https://dl.acm.org/doi/10.1145/7239.7265

**Ideia central (conforme fontes consultadas):** transações de alto volume que só
fazem **incremento e decremento de quantidades agregadas** ("hotspot data") podem
operar de forma **não-bloqueante**, sem serializar umas às outras, se o sistema
souber que o update é incremental. O método suporta transações **longas** —
que levam muito tempo para completar — sem impedir acesso simultâneo ao mesmo
registro por outros usuários.

**Por que isso é T25, exatamente:**

| Escrow (1986) | T25 (2026) |
|---|---|
| campo agregado sob alta contenção | consumo acumulado da entidade e o consumo global |
| incremento/decremento com limite inferior | custo acumulado com **limite superior** (o teto) |
| transação longa que não pode bloquear as outras | requisição ao LLM, que leva **segundos a minutos** e não pode segurar um lock durante a geração |
| reserva de quantidade em "escrow" até o commit | a **reserva** do pior caso, mantida até a reconciliação |

O terceiro item é o mais importante: a razão de o desenho de T25 precisar de
reserva-e-reconciliação em vez de "abre transação, chama o LLM, fecha transação" é
exatamente a razão que motivou O'Neil — **a transação é longa**. Segurar a seção
crítica durante a chamada ao provedor serializaria o gateway inteiro em uma
requisição por vez. Nomear isso como método Escrow converte uma escolha de
arquitetura em uma decisão com precedente de 40 anos.

**Consequência direta para a Fase 1:** a estrutura de dados dos contadores não é
"um número". É, no mínimo, `(consumido_confirmado, reservado_em_voo)` — a decisão de
admissão lê a soma dos dois, e a reconciliação move valor de um para o outro. Este é
o formato Escrow.

---

## F10 — Um teto exige coordenação: confluência de invariante (2014)

> P. Bailis, A. Fekete, M. J. Franklin, A. Ghodsi, J. M. Hellerstein, I. Stoica.
> **"Coordination Avoidance in Database Systems."**
> *Proceedings of the VLDB Endowment*, 2014. DOI: 10.14778/2735508.2735509
> Versão estendida: arXiv:1402.2237 · https://arxiv.org/abs/1402.2237

**Ideia central (conforme fontes consultadas):** o trabalho define **confluência de
invariante (I-confluence)**, um critério formal que é condição **necessária e
suficiente** para que uma aplicação possa executar de forma segura **sem
coordenação**, preservando seus invariantes de nível de aplicação. Muitos invariantes
comuns são I-confluentes e portanto dispensam coordenação.

**O que isso decide em T25:** a pergunta "posso rodar múltiplas instâncias do gateway
sem coordenação entre elas e ainda garantir o teto?" tem resposta formal, não
opinativa. Basta aplicar o critério ao invariante `soma ≤ teto`.

⚠️ **Afirmação a verificar antes de usar como fundamento:** minha expectativa é que um
invariante de limite superior sobre uma soma **não** seja I-confluente — porque duas
réplicas podem, cada uma independentemente, aprovar um gasto válido no seu estado
local, e o merge dos dois estados viola o teto. Se isso se confirmar no texto do
artigo, é a justificativa formal para a decisão já registrada de **instância única
com banco transacional** (decisão `3151c6c0`), e o item "múltiplas instâncias" sai do
fora-de-escopo por preguiça e passa a estar fora de escopo por **teorema**.
A busca realizada não trouxe o trecho específico. **Ler o artigo antes de afirmar isso
em qualquer artefato do projeto.**

---

## F11 e F12 — Referências canônicas, NÃO verificadas nesta sessão

Registradas para consulta; não citar como fundamento sem verificar.

- J. Gray, A. Reuter. *Transaction Processing: Concepts and Techniques.* Morgan
  Kaufmann, 1993. — Tratado de referência sobre ACID, isolamento e recuperação.
  Relevante para: por que a transação do banco embutido resolve a atomicidade dos
  **dois** contadores (global e da entidade) simultaneamente.
- H. Berenson, P. Bernstein, J. Gray, J. Melton, E. O'Neil, P. O'Neil.
  "A Critique of ANSI SQL Isolation Levels." *SIGMOD*, 1995. — Relevante para: o nível
  de isolamento importa. A anomalia **lost update** é literalmente o modo de falha de
  T25 sob concorrência: duas requisições leem o mesmo saldo, ambas decidem "cabe",
  ambas escrevem, e uma sobrescreve a outra. Se o teste do critério de acerto falhar,
  este é o primeiro lugar a olhar.

---

## Parâmetros com fonte, derivados desta seção

| Parâmetro de design | Valor / forma | Fonte |
|---|---|---|
| Estrutura do contador | par (confirmado, reservado), não escalar | F9 |
| Duração aceitável da seção crítica | apenas a decisão + escrita; **nunca** engloba a chamada ao provedor | F9 (motivação de transação longa) |
| Número de instâncias do gateway | 1, enquanto o teto for invariante de soma | F10 (a verificar) + decisão `3151c6c0` |
| Nível de isolamento exigido | suficiente para impedir lost update na leitura-decisão-escrita | F12 (a verificar) |
