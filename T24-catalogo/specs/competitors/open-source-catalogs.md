# Concorrentes — catálogos de dados open source

Levantamento da Fase 0 (iteração 1). Objetivo: situar o T24 no estado da arte e
identificar o **gap** que ele ocupa.

**Fontes:**
- https://atlan.com/openmetadata-vs-datahub/
- https://atlan.com/amundsen-vs-datahub/
- https://atlan.com/apache-atlas-alternatives/
- https://atlan.com/open-source-data-catalog-tools/
- https://thedataguy.pro/writing/2025/08/open-source-data-governance-frameworks/

---

## Panorama

DataHub e OpenMetadata lideram o espaço open source de catálogo de dados, por
comunidades grandes e ciclos de release rápidos. Apache Atlas atende ambientes
centrados em Hadoop/Apache. Amundsen atende necessidades leves de descoberta.

| Produto | Linhagem | Propriedade | Arquitetura | Posicionamento |
|---|---|---|---|---|
| **DataHub** | ingestão em streaming, linhagem **nativa em nível de coluna** | modelo de ownership completo | multi-componente: banco relacional (documentos) + Elasticsearch (busca) + **banco de grafos** (JanusGraph/Neo4j) + Kafka | times grandes, arquitetura modular, exige infraestrutura pesada |
| **OpenMetadata** | linhagem abrangente | qualidade + colaboração | stack simplificada: MySQL/PostgreSQL + Elasticsearch, **evita deliberadamente banco de grafos** para manter simplicidade arquitetural | plataforma all-in-one, mais fácil de operar |
| **Apache Atlas** | linhagem no ecossistema Hadoop | governança Hadoop | acoplado ao ecossistema Apache | melhor dentro de Hadoop |
| **Amundsen** | **limitada** — desenvolvimento desacelerou; linhagem, governança e tags de PII são pontos fracos | limitada | leve, fácil de implantar | busca de metadados simples |

---

## Onde o T24 se posiciona

Todos os quatro são **plataformas de servidor**: exigem banco, índice de busca e, em
alguns casos, banco de grafos e Kafka. O T24 é deliberadamente outra coisa —
**CLI sobre arquivos versionados, sem servidor, sem banco, sem índice**.

O gap ocupado:

1. **Propriedade declarada, não inferida.** As plataformas acima extraem metadados por
   scan automático e tratam ownership como atributo editável na UI. O T24 trata a
   declaração de propriedade como o **artefato primário**, revisável em pull request.
2. **Custo de entrada.** DataHub exige infraestrutura pesada; o T24 exige um
   interpretador Python e um diretório de arquivos.
3. **Uma pergunta, bem respondida.** As plataformas são de propósito geral (descoberta,
   qualidade, PII, colaboração, governança). O T24 responde **uma** pergunta — análise
   de impacto com resolução de dono.

**Observação relevante para a Fase 1 (evidência de terceiro, não opinião):** a decisão
do OpenMetadata de **evitar deliberadamente banco de grafos** e ainda assim entregar
linhagem abrangente é evidência prática de que grafo de linhagem não exige
infraestrutura de grafo. Isso sustenta a opção de estrutura em memória para o T24.

**Observação de risco:** DataHub oferece linhagem **em nível de coluna** como recurso
nativo. O T24 decidiu nível de tabela na Fase 0. É uma limitação consciente em relação
ao estado da arte, e deve constar no escopo negativo — não ser descoberta na Fase 2
como surpresa.
