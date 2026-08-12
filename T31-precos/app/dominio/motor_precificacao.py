"""M-03 `motor-precificacao` — o cálculo e o trace exaustivo.

Recebe um `ConjuntoDeRegras` (indexado na construção) e um `Produto` JÁ
RESOLVIDO — nunca um `sku` cru nem uma versão persistida. Consequências:

  * ASS-02: SKU desconhecido é erro de fronteira e não chega aqui;
  * A-04: o motor NUNCA lê o relógio — a data vem do chamador;
  * V(2)/U6: funciona sobre rascunho, o que desfez a circularidade ARQ-01;
  * PERF-06: o índice não é reconstruído por chamada.

I-3: o trace nunca sai vazio. Toda regra avaliada aparece, com código de
motivo — inclusive as que casaram e perderam, que é o que responde
"por que NÃO ganhei o desconto X".
"""

from __future__ import annotations

from datetime import date

from .modelo_dominio import (
    ConjuntoDeRegras,
    MotivoCodigo,
    Precificacao,
    Produto,
    Regra,
    ResultadoTrace,
    Trace,
    Veredito,
)
from .resolvedor_precedencia import resolver


def precificar(
    conjunto: ConjuntoDeRegras,
    produto: Produto,
    quantidade: int,
    quando: date,
) -> Precificacao:
    """Pré-condições (validadas em `servico-aplicacao`, ASS-01/U1):
    `quantidade >= 1` e `produto` existente no catálogo.
    """
    avaliadas: list[tuple[Regra, MotivoCodigo]] = [
        (r, r.avaliar(produto.sku, quantidade, quando))
        for r in conjunto.regras_de(produto.sku)
    ]
    candidatas = [r for r, m in avaliadas if m is MotivoCodigo.CANDIDATA]
    vencedora, derrotas = resolver(candidatas)

    motivo_final: dict[str, MotivoCodigo] = {r.id: m for r, m in avaliadas}
    for regra, codigo in derrotas:
        motivo_final[regra.id] = codigo
    if vencedora is not None:
        motivo_final[vencedora.id] = MotivoCodigo.VENCEU

    vereditos = tuple(
        Veredito(
            regra_id=regra.id,
            codigo=motivo_final[regra.id],
            detalhe=_detalhe(regra, motivo_final[regra.id], quantidade, quando),
        )
        for regra, _ in avaliadas
    )

    if vencedora is None:
        unitario = produto.preco_base
        total = unitario.multiplicar(quantidade)
        trace = Trace(
            resultado=ResultadoTrace.PRECO_BASE,
            vereditos=vereditos,
            calculo=(
                f"nenhuma regra casou → preço base {unitario}; "
                f"{quantidade} un × {unitario} = {total}"
            ),
            vencedora=None,
        )
        return Precificacao(unitario, total, trace)

    unitario = vencedora.efeito.aplicar(produto.preco_base)
    total = unitario.multiplicar(quantidade)
    trace = Trace(
        resultado=ResultadoTrace.APLICOU_REGRA,
        vereditos=vereditos,
        calculo=_calculo(vencedora, produto, unitario, quantidade, total),
        vencedora=vencedora.id,
    )
    return Precificacao(unitario, total, trace)


def _detalhe(
    regra: Regra, codigo: MotivoCodigo, quantidade: int, quando: date
) -> dict:
    """Dados estruturados do veredito. A prosa é derivada por `explicador`."""
    base = {"escopo": regra.escopo, "faixa": str(regra.faixa), "prioridade": regra.prioridade}
    match codigo:
        case MotivoCodigo.FORA_DA_FAIXA:
            base["quantidade_pedida"] = quantidade
        case MotivoCodigo.FORA_DA_VIGENCIA:
            base["data_pedido"] = quando.isoformat()
            base["vigencia_inicio"] = regra.vigencia.inicio.isoformat()
            base["vigencia_fim"] = (
                regra.vigencia.fim.isoformat() if regra.vigencia.fim else None
            )
        case _:
            pass
    return base


def _calculo(regra, produto, unitario, quantidade, total) -> str:
    from .modelo_dominio import TipoEfeito

    if regra.efeito.tipo is TipoEfeito.DESCONTO_PCT:
        return (
            f"{produto.preco_base} − {regra.efeito.descrever()} = {unitario}; "
            f"{quantidade} un × {unitario} = {total}"
        )
    return f"{quantidade} un × {unitario} = {total}"
