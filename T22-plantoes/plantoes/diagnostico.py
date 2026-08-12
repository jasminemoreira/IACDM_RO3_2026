"""M-07 diagnostico — inviabilidade estrutural, localizada.

CP-SAT devolve INFEASIBLE sem dizer por quê. Este módulo existe para transformar
isso em algo acionável: "dia 14, noturno, cardiologia: exige 2, apenas 1
elegível".

Só a verificação estrutural pré-solve. A relaxação por camadas descrita em V(1)
foi REMOVIDA em V(3) por KISS (IMP-03): era ideia sem especificação, e a
verificação de elegibilidade cobre o caso real — falta de gente habilitada e
disponível para a demanda mínima.
"""

from __future__ import annotations

from dataclasses import dataclass

from .dominio import Instancia


@dataclass(frozen=True)
class Conflito:
    plantao_id: str
    data: str
    tipo_de_turno_id: str
    habilitacao_id: str
    exigidos: int
    elegiveis: int

    def __str__(self) -> str:
        return (
            f"{self.data}, turno '{self.tipo_de_turno_id}', habilitação "
            f"'{self.habilitacao_id}': exige {self.exigidos}, apenas "
            f"{self.elegiveis} pessoa(s) elegível(is)"
        )


def analisar(inst: Instancia) -> list[Conflito]:
    """Conflitos locais que tornam a instância inviável por construção."""
    conflitos = []
    for plantao in sorted(inst.plantoes, key=lambda p: (p.data, p.id)):
        elegiveis = sum(1 for pessoa in inst.pessoas if inst.elegivel(pessoa, plantao))
        if elegiveis < plantao.demanda_minima:
            conflitos.append(
                Conflito(
                    plantao_id=plantao.id,
                    data=plantao.data.isoformat(),
                    tipo_de_turno_id=plantao.tipo_de_turno_id,
                    habilitacao_id=plantao.habilitacao_id,
                    exigidos=plantao.demanda_minima,
                    elegiveis=elegiveis,
                )
            )
    return conflitos
