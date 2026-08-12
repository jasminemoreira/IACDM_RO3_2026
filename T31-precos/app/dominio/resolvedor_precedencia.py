"""M-04 `resolvedor-precedencia` — quem vence quando várias regras casam.

Algoritmo normativo de `specs/domain/glossario.md`:
  1. ordena por prioridade DECRESCENTE;
  2. empate no topo resolve por ESPECIFICIDADE (SKU vence `*`);
  3. empate que persiste é `EmpateInsoluvel` — I-6 diz que isso é defeito do
     validador, e o motor deve falhar ruidosamente em vez de escolher.

Equivale à hit policy PRIORITY do OMG DMN — inspiração declarada, não
conformidade verificada (SCI-03).
"""

from __future__ import annotations

from .modelo_dominio import EmpateInsoluvel, MotivoCodigo, Regra


def resolver(
    candidatas: list[Regra],
) -> tuple[Regra | None, list[tuple[Regra, MotivoCodigo]]]:
    """Devolve `(vencedora, derrotas)`.

    Sem candidatas, a vencedora é `None` — I-2: ausência de regra NÃO é erro,
    é o caminho do preço base. Cada derrota carrega o CÓDIGO do motivo, que é
    o que permite ao trace responder "por que NÃO ganhei o desconto X".
    """
    if not candidatas:
        return None, []

    maior = max(r.prioridade for r in candidatas)
    topo = [r for r in candidatas if r.prioridade == maior]
    derrotas: list[tuple[Regra, MotivoCodigo]] = [
        (r, MotivoCodigo.PERDEU_POR_PRIORIDADE)
        for r in candidatas
        if r.prioridade != maior
    ]

    if len(topo) == 1:
        return topo[0], derrotas

    especificas = [r for r in topo if r.e_especifica]
    if len(especificas) == 1:
        vencedora = especificas[0]
        derrotas += [
            (r, MotivoCodigo.PERDEU_POR_ESPECIFICIDADE) for r in topo if r is not vencedora
        ]
        return vencedora, derrotas

    empatadas = especificas or topo
    raise EmpateInsoluvel(
        "empate insolúvel entre as regras "
        + ", ".join(sorted(r.id for r in empatadas))
        + f" (prioridade {maior}, mesma especificidade) — "
        "deveria ter sido barrado na validação (I-6)"
    )
