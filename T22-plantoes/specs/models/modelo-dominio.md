# Modelo de domínio — entidades, estados e formatos

> Fase 1, Passo 0. Vocabulário conforme `specs/domain/glossario.md`.

## 1. Entidades

```
Habilitacao        id, nome

TipoDeTurno        id, nome, inicio (HH:MM), fim (HH:MM), duracao_horas,
                   noturno: bool            # derivado: intersecta 22h–5h (art. 73 §2)

Contrato           id, regime ∈ {comum, 12x36},
                   min_plantoes, max_plantoes,              # S6
                   max_dias_consecutivos, min_dias_consecutivos,   # S2
                   min_folgas_consecutivas, max_folgas_consecutivas, # S3
                   max_fins_de_semana,                       # S7
                   exige_fim_de_semana_completo: bool        # S5

Pessoa             id, nome, contrato_id, habilitacoes[]

Plantao            id, data, tipo_de_turno_id, habilitacao_id,
                   demanda_minima,   # H2, rígida
                   demanda_otima     # S1, peso 30

Preferencia        pessoa_id, plantao_id | data, tipo ∈ {indesejado, indisponivel}
                   # indesejado  → S4, peso 10, violável
                   # indisponivel → RÍGIDA, variável não criada

RegraInterna       id, descricao, natureza ∈ {rigida, flexivel}, peso?, parametros
                   # origem = 'interna'; nunca se confunde com as legais

Alocacao           pessoa_id, plantao_id

Escala             id, periodo (inicio, fim), estado ∈ {rascunho, publicada},
                   alocacoes[], custo, status_solver, otimalidade_provada: bool

Troca              id, solicitante_id, destinatario_id,
                   plantao_do_solicitante_id, plantao_do_destinatario_id,
                   estado, criada_em, decidida_em?, motivo_rejeicao?

Violacao           restricao_id, origem, fonte, pessoa_id?, plantao_id?, descricao
```

## 2. Máquina de estados da Troca

```
                   solicitar (UC-3)
                        │
                        ▼
                  ┌───────────┐
                  │ PENDENTE  │
                  └─────┬─────┘
                        │
        ┌───────────────┼────────────────┬──────────────────┐
        │ recusar       │ aceitar (UC-4) │ plantão já passou│
        ▼               ▼                ▼                  │
   ┌──────────┐   revalidação        ┌──────────┐           │
   │ RECUSADA │   contra a escala    │ EXPIRADA │◄──────────┘
   └──────────┘   ATUAL              └──────────┘
                        │
              ┌─────────┴─────────┐
              │ viola rígida?     │
        sim   │                   │  não
              ▼                   ▼
       ┌──────────────┐    ┌────────────┐
       │  REJEITADA   │    │  EFETIVADA │
       │ (+ motivo e  │    │ (+ delta   │
       │  fonte legal)│    │  de custo) │
       └──────────────┘    └────────────┘
```

**Estados finais:** RECUSADA (decisão humana), REJEITADA (veredito da máquina),
EFETIVADA, EXPIRADA. Nenhum permite transição posterior.

Regras que a máquina codifica — cada uma vinda de uma decisão da Fase 0:

| Regra | Origem |
|---|---|
| A revalidação usa a escala **atual no momento do aceite**, nunca a de quando a troca foi criada | resolve corrida entre trocas com uma regra só (SC-8) |
| Violação **rígida** rejeita; violação **flexível** apenas reporta o delta de custo | autonomia acima de otimalidade, com consequência visível (SC-13) |
| EXPIRADA é derivada da data do plantão mais próximo, não de um prazo configurável | evita o único parâmetro numérico do sistema sem fonte (SC-12) |
| Só escala **publicada** aceita troca | rascunho é volátil por definição |

**REJEITADA ≠ RECUSADA.** Uma é a máquina dizendo "isto é ilegal"; a outra é uma
pessoa dizendo "não quero". Colapsar as duas apagaria a distinção que o produto
existe para manter.

## 3. Ciclo de vida da Escala

```
UC-1 gerar ──► RASCUNHO ──publicar──► PUBLICADA ──┐
                   ▲                        │      │ aceita trocas
                   └── re-gerar (--force) ◄──┘      │ (mutação in loco das alocações)
                       avisa quantas trocas
                       efetivadas serão descartadas
```

## 4. Formato de entrada (JSON)

Um arquivo de instância por unidade/período. Chaves em português, alinhadas ao
glossário — o vocabulário do domínio é o do operador, não o da biblioteca.

```json
{
  "periodo": {"inicio": "2026-09-01", "fim": "2026-09-30"},
  "habilitacoes": [{"id": "clinica", "nome": "Clínica Médica"}],
  "tipos_de_turno": [
    {"id": "diurno", "nome": "Diurno 12h", "inicio": "07:00", "fim": "19:00"},
    {"id": "noturno", "nome": "Noturno 12h", "inicio": "19:00", "fim": "07:00"}
  ],
  "contratos": [
    {"id": "c12x36", "regime": "12x36", "min_plantoes": 12, "max_plantoes": 16,
     "max_dias_consecutivos": 2, "min_folgas_consecutivas": 1,
     "max_fins_de_semana": 2, "exige_fim_de_semana_completo": false}
  ],
  "pessoas": [
    {"id": "p01", "nome": "Ana", "contrato_id": "c12x36", "habilitacoes": ["clinica"]}
  ],
  "plantoes": [
    {"id": "s001", "data": "2026-09-01", "tipo_de_turno_id": "noturno",
     "habilitacao_id": "clinica", "demanda_minima": 2, "demanda_otima": 3}
  ],
  "preferencias": [
    {"pessoa_id": "p01", "data": "2026-09-07", "tipo": "indisponivel"}
  ],
  "regras_internas": [
    {"id": "INT-01", "descricao": "máx. 8 noturnos por mês",
     "natureza": "flexivel", "peso": 25,
     "parametros": {"tipo_de_turno_id": "noturno", "max": 8}}
  ]
}
```

## 5. Formato de saída (JSON) — escala

```json
{
  "id": "2026-09-unidade-a",
  "periodo": {"inicio": "2026-09-01", "fim": "2026-09-30"},
  "estado": "rascunho",
  "status_solver": "OPTIMAL",
  "otimalidade_provada": true,
  "custo": 240,
  "custo_por_restricao": {"S1": 60, "S4": 30, "INT-01": 150},
  "alocacoes": [{"pessoa_id": "p01", "plantao_id": "s001"}]
}
```

`custo_por_restricao` não é enfeite: é o que permite ao UC-4 reportar **quais**
termos pioraram numa troca, e não apenas que o total subiu.

## 6. Fronteira derivada (não é entrada do usuário)

Ao gerar o mês `M`, o sistema procura a escala **publicada** de `M-1` no disco e
deriva:

```
FronteiraPorPessoa:
    ultimo_tipo_de_turno         # H3 e L1 na virada
    dias_trabalhados_consecutivos  # S2
    folgas_consecutivas            # S3
    total_plantoes_acumulado       # S6, se o horizonte contratual > 1 mês
    fins_de_semana_trabalhados      # S7
```

Se não houver escala anterior, a fronteira é vazia — comportamento correto para
o primeiro mês, e não deve ser confundido com erro.

**PR-4 (aberta):** assume-se que esses contadores são deriváveis sem ambiguidade
da escala anterior. O caso duvidoso é um mês anterior **parcialmente** coberto
(escala de 15 dias): os contadores de S6/S7 ficam sub-representados. Sinalizar
em vez de adivinhar.
