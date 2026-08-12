# T24 — catálogo de dados

Catálogo de dados com **donos declarados por domínio** e **linhagem entre eles**.
Responde uma pergunta e a responde bem:

> Se eu mudar este dataset, o que quebra a jusante e **quem eu preciso avisar**?

CLI sobre arquivos YAML versionados. Sem servidor, sem banco, sem autenticação — o
catálogo é um artefato revisável em pull request.

## Instalação

```bash
pip install -e .
```

Requer Python 3.11+, PyYAML 6.0+ e NetworkX 3.0+.

## Os dois atores

### Dono de domínio — declara

Um arquivo YAML por domínio, em `catalog/`. A fronteira do arquivo **é** a fronteira de
propriedade: cada dono edita apenas o seu, e conflito de merge entre domínios não existe.

```yaml
# catalog/financeiro.yaml
dominio: financeiro
dono:
  nome: Joao Souza
  contato: joao.souza@empresa.com

datasets:
  - nome: receita
    descricao: Receita reconhecida por competencia
    alimentado_por:
      - vendas.itens_pedido        # declarado pelo CONSUMIDOR

  - nome: previsao
    dono:                          # sobrescreve o dono do dominio
      nome: Carlos Lima
      contato: carlos.lima@empresa.com
    alimentado_por:
      - financeiro.receita
```

**`alimentado_por` é declarado por quem consome, apontando para quem produz.** Só o
consumidor sabe de fato o que consome — exigir que o produtor liste seus consumidores é
pedir justamente a informação que ele não tem, que é o problema original.

Formato completo em [`specs/models/formato-yaml.md`](specs/models/formato-yaml.md).

```bash
t24 validar
```

Reporta **todas** as violações de uma vez, cada uma nomeando o defeito: o ciclo com seus
datasets, a referência quebrada com sua identidade, o domínio sem dono com seu nome.

### Engenheiro de dados — consulta antes de mexer

```bash
t24 impacto vendas.pedidos
```

```
Mexer em 'vendas.pedidos' afeta 6 dataset(s) e exige avisar 4 responsavel(is):

  Ana Costa <ana.costa@empresa.com>
      - logistica.envios
      - logistica.rastreio
  Carlos Lima <carlos.lima@empresa.com>
      - financeiro.previsao
  Joao Souza <joao.souza@empresa.com>
      - financeiro.conciliacao
      - financeiro.receita
  Maria Silva <maria.silva@empresa.com>
      - vendas.itens_pedido

Escopo: o resultado cobre apenas dependencias DECLARADAS no catalogo. E um limite
inferior do conjunto real de afetados.
```

A saída é **agrupada por dono**, não por dataset: a pergunta é quem avisar.

```bash
t24 procedencia financeiro.conciliacao   # de onde vem este dado
t24 impacto vendas.pedidos --json        # saida estruturada
t24 --catalogo outro/dir validar         # outro diretorio
```

Códigos de saída: `0` sucesso · `1` catálogo inválido · `2` erro de uso.

## Regras que o catálogo impõe

| # | Invariante |
|---|---|
| INV-1 | Todo dataset pertence a exatamente um domínio |
| INV-2 | Todo domínio tem dono |
| INV-3 | Nenhum dataset é órfão de dono |
| INV-4 | O grafo é **acíclico** — ciclo é erro, e o erro nomeia o ciclo |
| INV-5 | Toda aresta referencia datasets declarados nos dois extremos |
| INV-6 | Dependência entre domínios nunca é declarada, apenas derivada |

INV-5 é deliberada e tem custo: **a adoção é big-bang**, porque um domínio não pode
declarar dependência de outro que ainda não existe. A alternativa seria devolver análise
de impacto silenciosamente incompleta, que é pior que erro explícito.

## O que este catálogo NÃO faz

Busca ou descoberta de datasets · relatórios de auditoria agregados · linhagem em nível
de coluna · scan automático de fontes · importação de OpenLineage/DataHub/DCAT · cache
entre execuções · notificação (a ferramenta diz quem avisar; avisar é com você).

Duas limitações que valem ser ditas em voz alta:

- **O catálogo é uma declaração, não um espelho verificado.** Nada detecta divergência
  entre o que está declarado e os pipelines reais. Detectar isso exigiria scan
  automático, que está fora de escopo por decisão de projeto.
- **O resultado é um limite inferior.** A completude do grafo depende da diligência de
  quem declara. Isso é propriedade social, não técnica — nenhuma arquitetura corrige
  incentivo, e por isso a ferramenta declara a limitação em vez de escondê-la.

## Arquitetura

9 módulos. Núcleo puro (`model`, `catalog`, `lineage_graph`, `validation`,
`query_service`) que não conhece arquivo, YAML nem terminal; bordas (`yaml_loader`,
`catalog_mapper`, `formatters`, `cli`) que fazem I/O. Dependência unidirecional:
borda → núcleo.

A garantia central: **`LoadedCatalog` recusa ser construído se houver qualquer
violação.** Consultar um catálogo inválido não é desaconselhado, é impossível.

Documento completo, com as três versões da arquitetura e as decisões que levaram a cada
uma: [`specs/technical/architecture.md`](specs/technical/architecture.md).

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest
```

`specs/datasets/ground-truth.md` é o oráculo do projeto — o catálogo de topologia
conhecida com os resultados esperados de toda consulta, escrito **antes** do código.
