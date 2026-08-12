# Lições deste projeto

Escritas no fechamento do ciclo v1.0. São lições sobre **este projeto** — domínio, stack,
padrões e assunções que se mostraram erradas — não sobre a metodologia.

---

## 1. Assunção que depende de disciplina do chamador não é assunção, é esperança

A8 foi registrada na Fase 1 como *"a validação roda sempre antes de qualquer consulta"*.
A Fase 2 derrubou (ARC-04): nada no desenho impedia a CLI de pular o repositório. A
V(2) tentou consertar declarando *"só `catalog-mapper` pode construir `LoadedCatalog`"* —
e a Fase 2 derrubou de novo (IMPL-06), porque **Python não tem construtor privado**: isso
era convenção com cara de garantia.

Só virou verdade quando mudou de natureza: `LoadedCatalog.__init__` **exige a lista de
violações e recusa construir se ela não estiver vazia**. Deixou de importar quem chama.

A lição operacional: quando escrever "sempre" ou "nunca" numa assunção, perguntar *o que
acontece se alguém não obedecer*. Se a resposta for "não deveria fazer isso", não é
garantia. Se for "não consegue", é.

## 2. Remover o módulo sobrecarregado não remove a sobrecarga — ela vai para o vizinho

`catalog-repository` recebeu 10 achados por 8 lentes distintas na primeira rodada: fazia
quatro coisas. A resposta da Fase 3 foi eliminá-lo, distribuindo o trabalho.

A segunda rodada adversarial encontrou ARC-06: a sobrecarga tinha **migrado inteira** para
`catalog-mapper`, que passou de 4 achados para 5 e virou o novo gargalo. A V(2) moveu a
concentração; não a eliminou.

O que funcionou na V(3) foi diferente: dissolver por **dono natural** — grafo para
`lineage-graph`, certificação para `validation`, mapeamento fica com o mapeador. Correção
que move responsabilidade precisa **nomear o novo dono de cada pedaço**; se não nomear,
tudo cai no vizinho mais próximo.

Corolário do mesmo padrão: fundir `errors` em `model` resolveu o contrato duplicado
(ARC-02) e **engordou** o módulo que já era o mais atacado (ARC-07). A V(3) resolveu
fazendo `model` encolher, mandando os tipos para quem os produz.

## 3. Corrigir um lado de uma ambiguidade cria o defeito espelhado do outro lado

GOV-03: `Owner` era `{nome, contato}` por valor, então a mesma pessoa grafada de dois
jeitos virava dois donos — e a deduplicação exigida pelo critério de acerto falhava.
Correção: identidade pelo **contato normalizado**.

Rodada seguinte, GOV-04: duas pessoas que dividem uma caixa (`dados@empresa.com`) passaram
a colapsar num único dono, com o nome escolhido arbitrariamente entre os dois.

A resposta certa não era escolher qual dos dois erros preferir. Foi **recusar a
ambiguidade**: dois nomes distintos com o mesmo contato geram violação exigindo
desambiguação. Quando as duas leituras de um dado são defensáveis, às vezes o desenho
certo é não aceitar o dado.

## 4. "Todas de uma vez" precisa dizer *de quê*

A9 dizia *"erros de carregamento são agregados: todas as violações de uma vez"*. Um teste
da Fase 6 falhou porque um catálogo com defeito de forma **e** defeitos semânticos
reportava só o primeiro.

Investigando antes de concluir: o código estava certo. Validar semântica sobre o catálogo
parcial — só os arquivos que passaram na forma — geraria **falso positivo** de "aresta
pendente" para todo dataset do arquivo rejeitado. Reportar defeito inexistente é pior que
pedir uma segunda rodada.

A agregação é **por estágio**, e o gate entre estágios é load-bearing. O que A9 realmente
garante: no máximo duas rodadas, nunca N. Foi o teste que forçou a precisão — e valeu a
pena resistir ao impulso de afrouxar o teste para caber no código antes de entender por
que o código fazia aquilo.

## 5. A identidade que carrega o domínio troca um problema por outro

`dominio.dataset` foi escolhido porque resolve o dono **sem lookup** e faz a dependência
entre domínios cair de graça da própria aresta. Funcionou exatamente como previsto.

O custo está documentado desde a Fase 0 e não foi pago neste ciclo apenas porque nada foi
reorganizado: **mover um dataset entre domínios muda sua identidade e invalida toda aresta
que o referencia.** A convenção de nomes da OpenLineage alerta explicitamente contra isso
(regra de estabilidade), e a OpenLineage ancora identidade na infraestrutura pela razão
oposta à nossa.

Para um v2: se reorganização de domínio virar evento real, esta é a primeira decisão a
revisitar — e o caminho provável é identidade estável separada do nome de exibição, não
inverter a escolha.

## 6. Atritos de stack que só aparecem executando

- **`argparse` não aceita flag do parser principal depois do subcomando.** `t24 --json
  impacto X` funcionava; `t24 impacto X --json` — a ordem que qualquer pessoa escreve —
  quebrava. Resolvido declarando `--json` também nos subparsers com
  `default=argparse.SUPPRESS`, para que a posição anterior não seja sobrescrita.
- **O console-script `pytest` não põe o diretório atual no `sys.path`; `python3 -m pytest`
  põe.** A suíte passava por um caminho e nem coletava pelo outro. A correção certa era
  `pip install -e .`, não `PYTHONPATH` — o próprio README já mandava fazer isso.
- **NetworkX não checa aciclicidade sozinho.** A documentação diz literalmente que as
  funções de DAG só têm garantia sobre DAGs e que checar é responsabilidade de quem chama.
  Isso originou A8 e é a razão de `validation` rodar antes de qualquer travessia.

## 7. O que mais rendeu: escrever o oráculo antes do código

`specs/datasets/ground-truth.md` e os critérios CA-0..CA-23 foram escritos na Fase 4,
**antes de existir uma linha de implementação**. Dois efeitos concretos:

1. Quando a Fase 6 chegou, os valores esperados não podiam ter sido moldados pelo que a
   implementação acabou fazendo — restava apenas o viés de escolher *quais* testes
   escrever, que é bem menor.
2. O teste do critério de acerto tem três linhas, porque o núcleo é puro e a asserção é
   feita direto sobre `query_service.impact`, sem atravessar arquivo nem stdout. A decisão
   arquitetural (núcleo puro) e a decisão de verificação (igualdade de conjuntos) foram
   tomadas pelo mesmo motivo, e uma tornou a outra barata.

Combinação a repetir: definir o critério de acerto como propriedade de uma **função pura**,
e escrever o oráculo antes.
