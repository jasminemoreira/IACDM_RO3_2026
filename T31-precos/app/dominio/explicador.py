"""M-06 `explicador` — traduz CÓDIGOS em frase pt-BR.

V(2)/U2 e ARQ-04: este módulo NÃO reinterpreta semântica de faixa ou vigência.
Ele traduz `MotivoCodigo` + `detalhe` estruturado em texto. A interpretação
vive em um só lugar (o motor), e é isso que apaga a lógica duplicada.

Miller (2019): explicações humanas são CONTRASTIVAS e SELETIVAS. O trace
guarda tudo (I-3); a frase mostra a vencedora e a razão da derrota da rival
mais próxima.
"""

from __future__ import annotations

from .modelo_dominio import MotivoCodigo, Precificacao, ResultadoTrace, Veredito

_PROSA = {
    MotivoCodigo.FORA_DA_FAIXA: "a faixa {faixa} un não cobre a quantidade pedida",
    MotivoCodigo.FORA_DA_VIGENCIA: "a regra não estava vigente na data do pedido",
    MotivoCodigo.ESCOPO_DIVERGENTE: "a regra é de outro produto",
    MotivoCodigo.PERDEU_POR_PRIORIDADE: "casou, mas perdeu por prioridade",
    MotivoCodigo.PERDEU_POR_ESPECIFICIDADE: (
        "casou, mas perdeu por especificidade (regra geral vs. regra de SKU)"
    ),
    MotivoCodigo.CANDIDATA: "casou",
    MotivoCodigo.VENCEU: "aplicada",
}


def motivo_em_texto(v: Veredito) -> str:
    modelo = _PROSA.get(v.codigo, v.codigo.value)
    return modelo.format(**{**{"faixa": "—"}, **v.detalhe})


def explicar(p: Precificacao, sku: str) -> str:
    t = p.trace
    if t.resultado is ResultadoTrace.PRECO_BASE:
        faixas = [
            v.detalhe.get("faixa")
            for v in t.vereditos
            if v.codigo is MotivoCodigo.FORA_DA_FAIXA
        ]
        existentes = (
            f" (há faixas para {', '.join(f for f in faixas if f)})" if faixas else ""
        )
        return (
            f"Nenhuma regra de preço cobre esta quantidade de {sku}{existentes}. "
            f"Aplicado o preço base: {p.preco_unitario}/un."
        )

    vencedora = next(v for v in t.vereditos if v.codigo is MotivoCodigo.VENCEU)
    alvo = "qualquer produto" if vencedora.detalhe.get("escopo") == "*" else sku
    frase = (
        f"Aplicada a regra de faixa {vencedora.detalhe.get('faixa')} un de {alvo}: "
        f"{p.preco_unitario}/un."
    )

    rival = _rival_mais_proxima(t.vereditos)
    if rival is not None:
        frase += (
            f" A regra {rival.regra_id} (faixa {rival.detalhe.get('faixa')} un) "
            f"{motivo_em_texto(rival)}."
        )
    return frase


def _rival_mais_proxima(vereditos: tuple[Veredito, ...]) -> Veredito | None:
    """A derrotada que MAIS perto chegou — a base contrastiva de Miller.

    Perder por prioridade ou especificidade significa ter casado; é essa a
    rival que responde "por que NÃO ganhei o desconto X".
    """
    derrotadas = [
        v
        for v in vereditos
        if v.codigo
        in (
            MotivoCodigo.PERDEU_POR_PRIORIDADE,
            MotivoCodigo.PERDEU_POR_ESPECIFICIDADE,
        )
    ]
    if not derrotadas:
        return None
    return max(derrotadas, key=lambda v: v.detalhe.get("prioridade", 0))
