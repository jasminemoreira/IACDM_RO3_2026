# Critérios de aceitação

Escritos na Fase 4, antes do código. Alimentam o mapa de testes da Fase 6 e o inventário
de escopo da Fase 5.

Regra de ouro (Fase 6, passo 1.3): **teste verde não é o mesmo que spec atendida**. Um
teste só valida um critério se verificar o critério EXATO, não um substituto.

---

## CA-0 — Critério de acerto do projeto (o que torna o retrabalho mensurável)

| | |
|---|---|
| **Enunciado** | Sobre o catálogo de `specs/datasets/ground-truth.md`, `impacto vendas.pedidos` devolve EXATAMENTE os 6 datasets afetados e EXATAMENTE os 4 responsáveis esperados |
| **Verificação** | Igualdade de conjuntos, não continência. Falso negativo e falso positivo reprovam igualmente |
| **Obrigatório cobrir** | (a) `financeiro.conciliacao` aparece UMA vez, apesar de alcançável por dois caminhos; (b) `financeiro.previsao` responde Carlos Lima, não João Souza |
| **Onde é asserido** | Sobre `query-service.impact`, função pura — sem atravessar arquivo nem stdout |

---

## Critérios por caso de uso

| id | Caso de uso | Critério de aceitação | Verificável por |
|---|---|---|---|
| CA-1 | UC-1 declarar domínio | O catálogo de 4 arquivos do ground truth carrega sem violação e produz 4 domínios, 8 datasets e 7 arestas | Contagem exata contra `specs/datasets/ground-truth.md` |
| CA-2 | UC-2 impacto | Ver CA-0. Além dele: as demais 5 consultas de impacto da tabela de esperados batem exatamente | Igualdade de conjuntos |
| CA-3 | UC-3 ciclo | `ciclo.yaml` falha **nomeando os dois datasets do ciclo**. Mensagem contendo apenas "há um ciclo" NÃO atende | A mensagem contém `financeiro.receita` e `financeiro.previsao` |
| CA-4 | UC-4 aresta pendente | `aresta-pendente.yaml` falha nomeando `vendas.inexistente` | A mensagem contém a identidade quebrada |
| CA-5 | UC-5 dono sobrescrito | `effective_owner(financeiro.previsao)` é Carlos Lima; `effective_owner(financeiro.receita)` é João Souza | Comparação direta |
| CA-6 | UC-6 procedência | As 5 consultas de procedência da tabela de esperados batem exatamente | Igualdade de conjuntos |

## Critérios por invariante

| id | Invariante | Fixture | Critério |
|---|---|---|---|
| CA-7 | INV-2 domínio tem dono | `dominio-sem-dono.yaml` | Falha nomeando o domínio `financeiro` |
| CA-8 | INV-4 grafo acíclico | `ciclo.yaml` | Ver CA-3 |
| CA-9 | INV-5 aresta referencia declarados | `aresta-pendente.yaml` | Ver CA-4 |
| CA-10 | A10 nomes sem ponto | `nome-com-ponto.yaml` | Falha na construção do nome de domínio |
| CA-11 | GOV-04 contato ambíguo | `dono-ambiguo.yaml` | Falha exigindo desambiguação; NÃO colapsa as duas pessoas num dono |
| CA-12 | MEC-01 campo desconhecido | `campo-desconhecido.yaml` | Falha nomeando `alimentado_pro`; não ignora em silêncio |

## Critérios de borda

| id | Borda | Critério |
|---|---|---|
| CA-13 | Dataset folha | `impacto logistica.rastreio` imprime frase EXPLÍCITA de conjunto vazio. Saída silenciosa reprova (UX-03) |
| CA-14 | Dataset inexistente | `impacto vendas.inexistente` produz mensagem DISTINTA da de conjunto vazio (UX-02) |
| CA-15 | Diamante | Coberto por CA-0(a) |
| CA-16 | Donos deduplicados | `impacto vendas.pedidos` lista Ana Costa e João Souza uma vez cada, apesar de dois datasets cada (CA-0) |

## Critérios de contrato e garantia

| id | Garantia | Critério |
|---|---|---|
| CA-17 | Construtor auto-validante (IMPL-06) | Tentar construir `LoadedCatalog` com lista de violações não vazia levanta erro — **testado diretamente**, sem passar pelo fluxo normal |
| CA-18 | Violações agregadas (A9) | Um catálogo com 3 defeitos distintos reporta os 3 numa execução, não um por vez |
| CA-19 | Ordem determinística (IMPL-01, IMPL-08) | Duas execuções sobre a mesma entrada produzem a mesma ordem de violações; violações sem domínio vêm primeiro |
| CA-20 | Caracterização do NetworkX (SCI-02, ASM-06) | Testes que fixam o comportamento de `descendants` (exclui a origem), `ancestors` e `find_cycle`. **Requisito de saída da Fase 5** para `lineage-graph` |
| CA-21 | Saída dupla | `--json` produz JSON parseável com os mesmos conjuntos da saída texto; nenhum teste de conjunto depende de texto formatado |
| CA-22 | Ressalva de escopo (UX-06) | A ressalva de limite inferior aparece uma vez: rodapé no texto, campo `escopo: "declarado"` no JSON |
| CA-23 | `safe_load` (SEC-01) | O carregador não instancia objetos Python arbitrários a partir de YAML |

## Fora dos critérios (rastreabilidade do escopo negativo)

Não há critério de aceitação para: busca/descoberta, relatórios de auditoria agregados,
linhagem de coluna, scan automático, importação OpenLineage/DCAT, cache, carregamento
incremental, concorrência, rede, autenticação, modo watch, arquivo de configuração,
escrita de YAML pelo sistema, detecção de drift entre catálogo e realidade (CTRL-01,
aceito), e completude do grafo (GAME-01, aceito — a saída declara ser limite inferior).
