# Implementação de referência — CP-SAT (S6 Tier 2)

> Fase 1. Código de referência a PORTAR, não a inventar. Serve à regra S6:
> algoritmo com implementação de referência → portar literalmente (mesma
> estrutura, mesmos nomes), não reescrever por intuição.

## 1. Modelo mínimo VERIFICADO nesta máquina

Executado na Fase 0 para provar a viabilidade da plataforma. Rodou com
`ortools 9.15.6755` / Python 3.12.1 e devolveu `OPTIMAL`, escala `[2, 1, 2]`.
É o esqueleto do qual `solver-cpsat` (M-06) parte.

```python
from ortools.sat.python import cp_model

m = cp_model.CpModel()

# variável de decisão: x[pessoa, dia] — no sistema real, x[pessoa, plantao]
x = {(p, d): m.NewBoolVar(f'x{p}{d}') for p in range(3) for d in range(3)}

# H2 — cobertura: exatamente 1 pessoa por dia (no sistema: >= demanda_minima)
for d in range(3):
    m.AddExactlyOne(x[p, d] for p in range(3))

# H3 / L1 — sucessão proibida entre dias consecutivos
for p in range(3):
    for d in range(2):
        m.Add(x[p, d] + x[p, d + 1] <= 1)

s = cp_model.CpSolver()
s.parameters.max_time_in_seconds = 5
s.parameters.random_seed = 0          # SC-3: determinismo
s.parameters.num_search_workers = 1   # multi-thread quebra o determinismo
r = s.Solve(m)

s.StatusName(r)   # 'OPTIMAL'
```

## 2. Idiomas CP-SAT que o M-06 vai usar

| Necessidade | Idioma | Onde aparece |
|---|---|---|
| no máx. 1 plantão por pessoa por dia | `AddAtMostOne(...)` | H1 |
| cobertura mínima | `Add(sum(...) >= minimo)` | H2 |
| sucessão proibida | `Add(a + b <= 1)` | H3, L1 |
| déficit em relação à cobertura ótima | `AddMaxEquality(falta, [otimo - soma, 0])` | S1 (peso 30) |
| penalidade linear direta | termo `peso * var` no objetivo | S4 (peso 10) |
| ≥ 1 dia livre por janela de 7 dias | `Add(sum(janela) <= len(janela) - 1)` | L2 |
| função objetivo | `m.Minimize(sum(peso_i * viol_i))` | agregação de S1-S7 + internas |

## 3. Referências externas (consultadas na Fase 0)

- Exemplo oficial OR-Tools de *nurse scheduling* e panorama de abordagens:
  https://en.wikipedia.org/wiki/Nurse_scheduling_problem
- Aplicação de CP-SAT em nurse scheduling (MDPI, Eng. Proc. 134:32):
  https://www.mdpi.com/2673-4591/134/1/32
- Uso de OR-Tools no NSP (dissertação, Universidade do Minho):
  https://repositorium.uminho.pt/bitstreams/cc5599d6-410d-499b-82f6-8c72b4cbc396/download
- Tutorial de rostering com CP-SAT (padrões de modelagem):
  https://mbrenndoerfer.com/writing/cp-sat-rostering-constraint-programming-workforce-scheduling
- Desempenho de solvers SAT em NRP (discussão técnica):
  https://groups.google.com/g/or-tools-discuss/c/3FC3eNDFyuk

## 4. O que NÃO copiar destes exemplos

Todos os exemplos públicos tratam a escala como problema **estático de uma
janela**: sem estado de fronteira, sem regime de contrato alterando a natureza
das restrições, e sem verificação da escala *depois* de pronta. As três coisas
são requisitos deste projeto (`specs/technical/modelo-cpsat.md` §1, §6 e
`specs/models/modelo-dominio.md` §6). Portar a mecânica CP-SAT: sim. Portar a
arquitetura dos exemplos: não.
