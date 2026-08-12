# Datasets de teste — verdade fundamental da Fase 6

Todos gerados por `plantoes.cli gerar-dados` com **semente fixa**: são
reprodutíveis byte a byte, e é isso que permite usá-los como teste de regressão
(SC-3 exige que a mesma entrada produza sempre a mesma escala).

| Arquivo | Porte | Papel |
|---|---|---|
| `instancia-referencia-30x30.json` | 30 pessoas, 30 dias, 90 plantões, 150 vagas ótimas | porte de referência de SC-1 e SC-2 |
| `instancia-pequena-12x14.json` | 12 pessoas, 14 dias | instância rápida para os testes de fluxo |
| `instancia-inviavel.json` | 8 pessoas, 4 dias | **inviável de propósito**: um plantão exige mais cardiologistas do que existem no cadastro. Sem ela não há como testar SC-4 (diagnóstico localizado) |

Resultados medidos no porte de referência (Fase 5/6):

- 150 alocações para 150 vagas ótimas, **custo 0**, **0 violações rígidas**
- **0,3 s** contra o limite de 60 s de SC-2
- 3 execuções idênticas (SC-3)
