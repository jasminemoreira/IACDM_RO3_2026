"""M-06 solver-cpsat — adaptador do solver.

Tier 1: usa OR-Tools CP-SAT, não escreve busca própria.
Tier 2: porta a formulação do INRC-II via `restricoes_modelo`.

Contrato determinístico (SC-3): random_seed=0 e num_search_workers=1.
Multi-thread quebra o determinismo, e sem determinismo não há teste de
regressão na Fase 6. A ordem de iteração sobre pessoas e plantões é
explicitamente ordenada por id — o determinismo não pode depender da ordem de
leitura do arquivo.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from . import restricoes_legais, restricoes_modelo
from .dominio import (
    Alocacao,
    Contexto,
    Escala,
    EstadoEscala,
)

LIMITE_PADRAO_S = 60  # SC-2

# RES-01: cada status significa uma coisa distinta e exige ação distinta.
SIGNIFICADO = {
    cp_model.OPTIMAL: ("OPTIMAL", "ótimo comprovado"),
    cp_model.FEASIBLE: (
        "FEASIBLE",
        "escala viável encontrada, mas o limite de tempo foi atingido antes de "
        "provar que é a melhor possível",
    ),
    cp_model.INFEASIBLE: (
        "INFEASIBLE",
        "não existe escala que satisfaça todas as restrições rígidas",
    ),
    cp_model.MODEL_INVALID: (
        "MODEL_INVALID",
        "o modelo construído é inválido — isto é um defeito do programa, não da "
        "sua instância",
    ),
    cp_model.UNKNOWN: (
        "UNKNOWN",
        "o tempo esgotou sem encontrar nenhuma escala viável; aumente o limite "
        "de tempo ou verifique a viabilidade da instância",
    ),
}


@dataclass(frozen=True)
class ResultadoGeracao:
    escala: Escala | None
    status: str
    motivo: str
    otimalidade_provada: bool
    segundos: float


def gerar(
    ctx: Contexto,
    escala_id: str,
    limite_s: int = LIMITE_PADRAO_S,
) -> ResultadoGeracao:
    inst = ctx.instancia
    modelo = cp_model.CpModel()

    # Variáveis: podadas por elegibilidade (H4 + indisponibilidade rígida).
    # Ordem explícita por id — determinismo não pode depender do dicionário.
    x = {}
    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        for plantao in sorted(inst.plantoes, key=lambda p: p.id):
            if inst.elegivel(pessoa, plantao):
                x[(pessoa.id, plantao.id)] = modelo.NewBoolVar(
                    f"x_{pessoa.id}_{plantao.id}"
                )

    restricoes_legais.aplicar(modelo, x, ctx)
    termos = restricoes_modelo.aplicar(modelo, x, ctx)
    if termos:
        modelo.Minimize(sum(termos))

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = limite_s

    status = solver.Solve(modelo)
    nome, motivo = SIGNIFICADO.get(status, ("DESCONHECIDO", "status não mapeado"))

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ResultadoGeracao(
            escala=None,
            status=nome,
            motivo=motivo,
            otimalidade_provada=False,
            segundos=round(solver.WallTime(), 3),
        )

    alocacoes = tuple(
        Alocacao(pessoa_id, plantao_id)
        for (pessoa_id, plantao_id), var in sorted(x.items())
        if solver.Value(var)
    )
    escala = Escala(
        id=escala_id,
        inicio=inst.inicio,
        fim=inst.fim,
        estado_escala=EstadoEscala.RASCUNHO,
        alocacoes=alocacoes,
        status_solver=nome,
        otimalidade_provada=(status == cp_model.OPTIMAL),
    )
    return ResultadoGeracao(
        escala=escala,
        status=nome,
        motivo=motivo,
        otimalidade_provada=(status == cp_model.OPTIMAL),
        segundos=round(solver.WallTime(), 3),
    )
