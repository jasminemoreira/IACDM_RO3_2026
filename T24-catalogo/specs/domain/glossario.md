# Glossário de domínio — T24 catálogo

Vocabulário operacional fixado na Fase 0 (iteração 1). Cada termo do enunciado
congelado foi tornado operacional por decisão do operador — o enunciado original
("catálogo de dados com donos declarados por domínio e linhagem entre eles") deixava
os quatro termos centrais ambíguos.

---

| Termo | Definição operacional no T24 | O que NÃO é |
|---|---|---|
| **Dataset** | Unidade catalogada. Uma tabela, arquivo ou tópico. Tem identidade, pertence a exatamente um domínio, carrega um schema descritivo. | **Não** é a coluna. Colunas existem como descrição dentro do dataset, sem identidade própria, sem dono próprio e sem participação na linhagem. |
| **Domínio** | Domínio de **negócio** no sentido Data Mesh (Vendas, Logística, Financeiro). Unidade de propriedade e responsabilidade. | **Não** é schema, banco, namespace de infra nem nó do organograma. Independe de onde o dado fisicamente reside. |
| **Dono** | Responsável declarado por um domínio. Todo dataset do domínio **herda** esse dono; um dataset pode sobrescrevê-lo pontualmente. | **Não** é inferido de metadados nem de histórico de commits. Propriedade é ato humano deliberado — daí "donos **declarados**". |
| **Linhagem** | Grafo dirigido entre datasets, granularidade de tabela. Aresta = "dataset A alimenta dataset B". | **Não** é linhagem de coluna. **Não** é um segundo grafo entre domínios. |
| **Dependência entre domínios** | Relação **derivada**, nunca declarada: se A (domínio X) alimenta B (domínio Y), então existe X→Y. | **Não** tem estrutura própria nem declaração própria — é uma projeção do grafo de datasets. |
| **Análise de impacto** | A pergunta central do produto: dado um dataset X, quais datasets a jusante são afetados e **quem são os donos** desses datasets. | **Não** é rastreio de proveniência (a direção inversa), **não** é busca/descoberta, **não** é auditoria de governança. |
| **Identidade de dataset** | Namespace hierárquico `dominio.dataset` (ex.: `vendas.pedidos`). A chave carrega o domínio. | **Não** é URN de infraestrutura (`postgres://host/tabela`) — divergência consciente da convenção OpenLineage; ver `specs/references/data-catalog-standards.md` §2. |

---

## Invariantes derivadas do vocabulário

Consequências lógicas das definições acima. Não são requisitos adicionais — são
implicações que o sistema precisa preservar.

| # | Invariante | Origem |
|---|---|---|
| INV-1 | Todo dataset pertence a exatamente um domínio. | Identidade `dominio.dataset` |
| INV-2 | Todo domínio tem dono. | "donos declarados por domínio" |
| INV-3 | Nenhum dataset é órfão de dono. | INV-1 + INV-2 + herança |
| INV-4 | O grafo de linhagem é acíclico. Ciclo é **erro de declaração** — carregamento falha nomeando o ciclo. | Decisão DAG estrito, Fase 0 |
| INV-5 | Toda aresta referencia datasets declarados nos dois extremos. | Aresta pendente tornaria o impacto incompleto e o dono irresolúvel |
| INV-6 | A dependência entre domínios nunca é declarada, só derivada. | Um único grafo, duas leituras |

INV-5 ainda não foi validada pelo operador — consta como assunção no teach-back.

## Termos do domínio deliberadamente ausentes

O campo teórico (governança de dados) tem vocabulário muito mais amplo. Estes termos
existem na literatura e **não** foram incorporados ao T24:

- **Steward / custodian** — DAMA-DMBOK separa quem responde (owner), quem cuida da
  qualidade (steward) e quem opera a infra (custodian). O T24 colapsa os três num
  único "dono". Ver `specs/references/data-catalog-standards.md` §1.
- **Data product** — princípio 2 do Data Mesh. O T24 implementa apenas o princípio 1
  (domain ownership).
- **Classificação / PII / política de retenção** — governança de conteúdo. Fora do
  escopo.
- **Distribution / DataService** (DCAT) — formas de acesso ao dado. O T24 cataloga o
  dataset, não como acessá-lo.
