"""M-10 gerador-sintetico — instâncias reprodutíveis para teste.

Decidido na Fase 0 como fonte dos dados de teste: reprodutível por semente,
sem dependência externa, e capaz de fabricar DELIBERADAMENTE a instância
inviável — sem a qual não há como testar o diagnóstico (SC-4).

Porte de referência: 30 pessoas, ~3 plantões/dia, 30 dias.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

TURNOS = [
    {"id": "diurno", "nome": "Diurno 12h", "inicio": "07:00", "fim": "19:00", "vira_o_dia": False},
    {"id": "noturno", "nome": "Noturno 12h", "inicio": "19:00", "fim": "07:00", "vira_o_dia": True},
]


def gerar(
    n_pessoas: int = 30,
    n_dias: int = 30,
    semente: int = 0,
    inicio: date | None = None,
    plantoes_por_dia: int = 3,
    inviavel: bool = False,
    com_preferencias: bool = True,
) -> dict:
    """Devolve o dicionário da instância (formato de `carregador.carregar`).

    `inviavel=True` fabrica um conflito estrutural local: um plantão exige mais
    gente habilitada do que existe.
    """
    rnd = random.Random(semente)
    inicio = inicio or date(2026, 9, 1)
    fim = inicio + timedelta(days=n_dias - 1)

    habilitacoes = [
        {"id": "clinica", "nome": "Clínica Médica"},
        {"id": "cardio", "nome": "Cardiologia"},
    ]

    # Calibração: os limites do contrato têm de ser consistentes com as vagas
    # que existem. Com min_plantoes acima de (vagas ótimas / pessoas), o solver
    # superlota os plantões para cumprir o mínimo contratual — e o custo cai a
    # zero por artefato da instância, não por qualidade da escala.
    vagas_otimas = sum(
        2 if ("cardio" if k == 2 else "clinica") == "clinica" else 1
        for _ in range(n_dias)
        for k in range(plantoes_por_dia)
    )
    por_pessoa = max(1, vagas_otimas // max(1, n_pessoas))

    contratos = [
        {
            "id": "c12x36",
            "regime": "12x36",
            "min_plantoes": max(1, por_pessoa - 1),
            "max_plantoes": por_pessoa + 2,
            "max_dias_consecutivos": 1,
            "min_dias_consecutivos": 1,
            "min_folgas_consecutivas": 1,
            "max_fins_de_semana": 3,
            "exige_fim_de_semana_completo": False,
            "horizonte_meses": 1,
        }
    ]

    pessoas = []
    for i in range(n_pessoas):
        habs = ["clinica"]
        if i % 3 == 0:
            habs.append("cardio")
        pessoas.append(
            {
                "id": f"p{i:02d}",
                "nome": f"Pessoa {i:02d}",
                "contrato_id": "c12x36",
                "habilitacoes": habs,
            }
        )

    plantoes = []
    for dia in range(n_dias):
        d = (inicio + timedelta(days=dia)).isoformat()
        for k in range(plantoes_por_dia):
            turno = TURNOS[k % 2]["id"]
            hab = "cardio" if k == 2 else "clinica"
            plantoes.append(
                {
                    "id": f"s{dia:02d}{k}",
                    "data": d,
                    "tipo_de_turno_id": turno,
                    "habilitacao_id": hab,
                    "demanda_minima": 1,
                    "demanda_otima": 2 if hab == "clinica" else 1,
                }
            )

    if inviavel and plantoes:
        # exige mais cardiologistas do que existem no cadastro
        cardio = [p for p in plantoes if p["habilitacao_id"] == "cardio"]
        alvo = cardio[0] if cardio else plantoes[0]
        alvo["habilitacao_id"] = "cardio"
        alvo["demanda_minima"] = sum(
            1 for p in pessoas if "cardio" in p["habilitacoes"]
        ) + 1
        alvo["demanda_otima"] = alvo["demanda_minima"]

    preferencias = []
    if com_preferencias:
        for pessoa in pessoas:
            for _ in range(2):
                dia = rnd.randrange(n_dias)
                preferencias.append(
                    {
                        "pessoa_id": pessoa["id"],
                        "data": (inicio + timedelta(days=dia)).isoformat(),
                        "tipo": "indesejado",
                        "tipo_de_turno_id": "noturno",
                    }
                )

    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "habilitacoes": habilitacoes,
        "tipos_de_turno": TURNOS,
        "contratos": contratos,
        "pessoas": pessoas,
        "plantoes": plantoes,
        "preferencias": preferencias,
        "regras_internas": [
            {
                "id": "INT-01",
                "descricao": "máximo de noturnos por período",
                "natureza": "flexivel",
                "peso": 25,
                "parametros": {"tipo_de_turno_id": "noturno", "max": 8},
            }
        ],
    }
