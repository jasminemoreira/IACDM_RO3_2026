# Padrões e referências — catálogo de dados, propriedade e linhagem

Material coletado na Fase 0 (iteração 1). Toda afirmação abaixo tem fonte citada.
Regra Versus: nenhum parâmetro numérico ou algoritmo entra no código sem referência
verificável (lente Científica, Fase 2).

---

## 1. DCAT 3 — W3C Data Catalog Vocabulary

**Fonte:** https://www.w3.org/TR/vocab-dcat-3/ (W3C Recommendation)

Vocabulário RDF padrão para descrever catálogos de dados na web. Relevante aqui como
**referência de modelagem**, não como formato de serialização (o projeto usa arquivos
declarativos próprios, não RDF).

### Classes centrais
| Classe | Definição (verbatim da spec) |
|---|---|
| `dcat:Catalog` | "A curated collection of metadata about resources" |
| `dcat:Dataset` | Coleção de dados publicada por um único agente |
| `dcat:Distribution` | "An accessible form of a dataset such as a downloadable file" |
| `dcat:DataService` | "A collection of operations accessible through an interface" |
| `dcat:CatalogRecord` | Registro de metadados descrevendo o cadastro do recurso |

### Identificação de dataset
- `dcterms:identifier` — "A unique identifier of the resource being described"
- `dcterms:title` — "A name given to the resource"

### Propriedade / responsabilidade
- `dcterms:publisher` — "The entity responsible for making the resource available"
- `dcterms:creator` — "The entity responsible for producing the resource"
- `dcat:contactPoint` — "Relevant contact information for the cataloged resource"
- `prov:qualifiedAttribution` — liga o recurso a agentes com responsabilidade sobre ele

**Leitura para T24:** DCAT distingue *publisher* (quem disponibiliza) de *creator*
(quem produz) e de *contactPoint* (com quem falar). O T24 colapsou os três num único
conceito de **dono do domínio** (decisão de Fase 0). Isso é uma simplificação
deliberada e deve constar como assunção — DCAT documenta que a prática real separa
esses papéis.

### Proveniência / linhagem
- `dcat:qualifiedRelation` — "Link to a description of a relationship with another resource"
- `dcat:previousVersion` — "The previous version of a resource in a lineage"
- `prov:wasRevisionOf` — super-propriedade de relação de revisão
- `dcterms:isReferencedBy` — recursos que citam/apontam para o dataset

**Leitura para T24:** DCAT modela linhagem principalmente como **versionamento**, não
como fluxo de transformação entre datasets distintos. Para "A alimenta B" o padrão
adequado é OpenLineage (seção 2), não DCAT.

---

## 2. OpenLineage — convenção de nomes de dataset

**Fonte:** https://openlineage.io/docs/spec/naming/

Spec aberta para eventos de linhagem. Relevante aqui pela **convenção de identidade**.

### Estrutura
Dataset é identificado pela combinação **namespace + name**. O namespace deriva do
tipo de datasource; o name identifica o dataset dentro daquele datasource.

### Formato de namespace por tipo de fonte
| Tipo | Formato |
|---|---|
| Bancos/warehouse (Postgres, MySQL) | `postgres://{host}:{port}` |
| Snowflake | `snowflake://{organization}-{account}` |
| Object storage (S3, GCS) | `s3://{bucket}`, `gs://{bucket}` |
| Filas (Kafka, PubSub) | `kafka://{bootstrap server host}:{port}` |
| Serviços específicos | `bigquery`, `spanner://{projectId}:{instanceId}` |

### Regras (verbatim / parafraseado da spec)
- **Unicidade:** o `name` deve ser único dentro do seu namespace.
- **Estabilidade:** nomes devem permanecer estáveis ao longo do tempo — a spec
  destaca o caso do Snowflake, onde escolher o formato errado **quebra a conexão de
  linhagem**.
- Justificativa da spec: *"employing a unique naming strategy per resource ensures
  that the spec is followed uniformly regardless of metadata producer"*.

**Leitura para T24 — divergência consciente e ASSUNÇÃO DE RISCO:**
OpenLineage ancora a identidade na **infraestrutura** (`postgres://host:port`). O T24
decidiu ancorar em **domínio de negócio** (`vendas.pedidos`). O trade-off é explícito:

| | OpenLineage (infra) | T24 (domínio) |
|---|---|---|
| Resolver o dono do dataset | exige lookup | imediato, sai da própria chave |
| Mover dataset entre domínios | identidade estável | **identidade muda, arestas quebram** |
| Mover dataset entre servidores | **identidade muda** | identidade estável |

A regra de **estabilidade** da OpenLineage é o alerta direto contra a escolha do T24:
reorganização de domínios (evento comum em Data Mesh) invalida identidades. Isso é
material para a Fase 2 — lentes Assunções e Migração/Coexistência.

---

## 3. Data Mesh — princípio de propriedade por domínio

**Fontes:**
- https://www.starburst.io/blog/data-mesh-book-bulletin-principle-of-domain-ownership/
- https://www.oreilly.com/library/view/data-mesh/9781492092384/ (Dehghani, Z., *Data Mesh*, O'Reilly)
- https://www.getdbt.com/blog/the-four-principles-of-data-mesh

Conceito criado por **Zhamak Dehghani** (ThoughtWorks, 2019). Definição de data mesh
pela autora: *"a sociotechnical approach to share, access and manage analytical data in
complex and large-scale environments — within or across organizations"*.

### Os quatro princípios
1. **Domain ownership** — propriedade orientada a domínio
2. Data as a product
3. Self-service data platform
4. Federated computational governance

### Princípio 1 (o que o T24 implementa)
Times de domínio assumem responsabilidade pelos seus dados. O núcleo é a
**descentralização e distribuição da responsabilidade sobre o dado para quem está mais
próximo dele** — quem entende aquela parte do negócio está melhor posicionado para
gerir o dado e garantir sua corretude. Especialistas de domínio tornam-se **data
product owners**, apoiados por data product developers.

**Leitura para T24:** este é o fundamento teórico da decisão "domínio tem dono; dataset
herda". O T24 implementa o princípio 1 e **não** implementa os princípios 2, 3 e 4 —
delimitação relevante para o escopo negativo da Fase 1.
