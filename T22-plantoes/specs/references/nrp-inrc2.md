# Nurse Rostering Problem — fundamentação e benchmark INRC-II

> Depositado na Fase 0 (Nível 1 — Domínio). Todo parâmetro numérico usado no
> projeto deve rastrear até uma entrada deste arquivo ou de `clt-jornada.md`.

## 1. Classe do problema

O "distribuidor de plantões" é uma instância do **Nurse Rostering Problem (NRP)**
/ Nurse Scheduling Problem (NSP): atribuir pessoas a turnos satisfazendo um
conjunto de **restrições rígidas (hard)** — que toda solução válida deve cumprir —
e otimizando um conjunto de **restrições flexíveis (soft)**, cuja violação
penalizada define a qualidade da solução.

- Complexidade: NP-difícil no caso geral.
- Fonte: Wikipedia, *Nurse scheduling problem* — https://en.wikipedia.org/wiki/Nurse_scheduling_problem

Consequência de design (vale para a Fase 1): **hard ≠ soft é uma distinção
estrutural, não uma etiqueta**. Hard entra como restrição do modelo (poda o
espaço de busca); soft entra como termo penalizado na função objetivo. Um motor
que trate as duas do mesmo jeito ou não encontra solução (tudo hard) ou entrega
escala ilegal (tudo soft).

## 2. INRC-II — Second International Nurse Rostering Competition

Formulação de referência, com conjunto de restrições enxuto e pesos publicados.
Serve como **modelo canônico** a portar (S6 Tier 2), não como algoritmo a inventar.

- Fonte primária: Ceschia, Dang, De Causmaecker, Haspeslagh, Schaerf.
  *Second International Nurse Rostering Competition (INRC-II) — Problem
  Description and Rules*. arXiv:1501.04177 — https://arxiv.org/abs/1501.04177
  (HTML consultado: https://ar5iv.labs.arxiv.org/html/1501.04177)
- PDF oficial da competição: https://mobiz.vives.be/inrc2/wp-content/uploads/2014/10/INRC2.pdf

### 2.1 Restrições rígidas (hard) — todas verbatim

| id | Restrição | Enunciado |
|----|-----------|-----------|
| H1 | Single assignment per day | "A nurse can be assigned to at most one shift per day." |
| H2 | Under-staffing | "The number of nurses for each shift for each skill must be at least equal to the minimum requirement." |
| H3 | Shift type successions | "The shift type assignments of one nurse in two consecutive days must belong to the legal successions provided in the scenario." |
| H4 | Missing required skill | "A shift of a given skill must necessarily be fulfilled by a nurse having that skill." |

### 2.2 Restrições flexíveis (soft) — com peso de penalidade publicado

| id | Restrição | Peso | Observação |
|----|-----------|------|------------|
| S1 | Insufficient staffing for optimal coverage | 30 | por enfermeiro abaixo do requisito ótimo |
| S2 | Consecutive assignments | 15 / 30 | 15 para min/max consecutivos do mesmo tipo de turno; 30 para dias trabalhados consecutivos |
| S3 | Consecutive days off | 30 | violação de min/max de folgas consecutivas |
| S4 | Preferences | 10 | alocação em turno indesejado (pedido do profissional) |
| S5 | Complete week-end | 30 | trabalha só um dia do fim de semana quando o contrato exige ambos ou nenhum |
| S6 | Total assignments | 20 | avaliado no fim do horizonte: total de dias fora dos limites do contrato |
| S7 | Total working week-ends | 30 | avaliado no fim do horizonte: fins de semana trabalhados acima do máximo |

**Custo total** = Σ (violações soft × peso). Violação de restrição hard = solução
inviável (não é penalizada, é rejeitada).

Nota de calibração: o peso de `Preferences` (10) é o **menor** do conjunto — a
literatura de referência trata preferência individual como o item mais barato de
sacrificar. Se o produto quiser dar mais peso à preferência, isso é uma **decisão
de produto explícita**, não um default; deve ser registrada como tal.

### 2.3 Estrutura de dados de entrada (a reaproveitar no modelo de domínio)

- **Scenario** (global, vale para todo o horizonte): horizonte em semanas;
  skills; tipos de turno com limites de consecutividade e sucessões proibidas;
  contratos (limites de total de plantões, dias trabalhados/folgados consecutivos,
  máx. de fins de semana, exigência de fim de semana completo); pessoas com
  contrato e skills.
- **Week data** (por semana): cobertura exigida por turno × skill × dia
  (mínimo e ótimo); pedidos das pessoas (turnos indesejados / folga).
- **History** (transportado entre semanas): último turno trabalhado, nº de turnos
  consecutivos (do mesmo tipo e no total), folgas consecutivas; contadores
  acumulados (total de turnos, total de fins de semana trabalhados).

**Lição de arquitetura já visível aqui:** a formulação é *multi-estágio* — cada
semana é resolvida contra um `history` herdado da anterior. Qualquer geração que
trate um período isolado, sem estado de fronteira, viola H3/S2/S3 na emenda entre
períodos. Isso é um requisito de contrato entre módulos, não um detalhe.

## 3. Tecnologia de resolução (Tier 1 — biblioteca madura)

**Google OR-Tools / CP-SAT** é a ferramenta madura e documentada para NRP:
programação por restrições com satisfatibilidade, com exemplo oficial de
*nurse scheduling*. Cobre explicitamente períodos de descanso obrigatório,
casamento por skill e conformidade com legislação trabalhista.

- Wikipedia (definição hard/soft e panorama de abordagens): https://en.wikipedia.org/wiki/Nurse_scheduling_problem
- Aplicação CP-SAT em nurse scheduling (MDPI): https://www.mdpi.com/2673-4591/134/1/32
- Uso de OR-Tools no NSP (dissertação, U. Minho): https://repositorium.uminho.pt/bitstreams/cc5599d6-410d-499b-82f6-8c72b4cbc396/download
- Tutorial CP-SAT rostering: https://mbrenndoerfer.com/writing/cp-sat-rostering-constraint-programming-workforce-scheduling
- Discussão de desempenho SAT em NRP: https://groups.google.com/g/or-tools-discuss/c/3FC3eNDFyuk
- Abordagem alternativa (busca local dirigida por restrições), para contexto:
  arXiv:0910.1253 — https://arxiv.org/pdf/0910.1253

Decisão de Tier a ser confirmada na Fase 1: **Tier 1 para o solver** (usar
CP-SAT, não escrever busca própria) + **Tier 2 para o modelo** (portar a
formulação INRC-II, mesmos nomes e mesma estrutura de restrições).

## 4. Lacuna conhecida (a resolver antes da Fase 5)

O INRC-II **não modela troca de plantão entre pessoas nem aprovação** — é
geração pura. Toda a parte de *swap + approval* do enunciado não tem cobertura
nesta referência; a fonte para essa metade é a análise de concorrentes
(`specs/competitors/`), não a literatura de rostering.
