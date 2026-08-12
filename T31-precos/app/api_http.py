"""M-10 `api-http` — adapter de entrada REST.

  * SEC-01 — o bind em 127.0.0.1 é responsabilidade de `main.py` e não é
    configurável por variável de ambiente. Não há auth (A-08); expor este
    serviço na rede entrega a publicação de preços a qualquer um.
  * A-04 — `data` é OBRIGATÓRIA no contrato de máquina. Só a UI preenche
    "hoje", de forma visível e editável.
  * LIN-04/W10 — `preco_unitario` é decimal em string ISO e é NORMATIVO;
    `preco_unitario_br` é derivado e existe só para apresentação.
  * ASS-03 — "nenhuma versão publicada" tem código próprio (409), distinto de
    entrada inválida (400) e de "nenhuma regra casou" (que é 200, I-2).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .adaptadores.importador_csv import ErroDeImportacao
from .adaptadores.repositorio_sqlite import ErroDePersistencia
from .servico_aplicacao import (
    EntradaInvalida,
    RascunhoConflitante,
    SemVersaoPublicada,
    ServicoAplicacao,
)

router = APIRouter(prefix="/api", tags=["preco"])
_servico: ServicoAplicacao | None = None


def configurar(servico: ServicoAplicacao) -> None:
    global _servico
    _servico = servico


def svc() -> ServicoAplicacao:
    if _servico is None:  # pragma: no cover
        raise RuntimeError("serviço não configurado")
    return _servico


class PedidoPreco(BaseModel):
    sku: str
    quantidade: int = Field(ge=1)
    data: date  # obrigatória — A-04
    solicitante: str = "não informado"


def _decisao_em_dict(d, explicacao: str) -> dict:
    return {
        "decisao_id": d.id,
        "sku": d.sku,
        "quantidade": d.quantidade,
        "data_pedido": d.data_pedido.isoformat(),
        "versao_regras": d.versao_regras,
        "preco_unitario": d.preco_unitario.iso(),  # NORMATIVO
        "total": d.total.iso(),  # NORMATIVO
        "preco_unitario_br": str(d.preco_unitario),  # apresentação
        "total_br": str(d.total),  # apresentação
        "explicacao": explicacao,
        "trace": {
            "resultado": d.trace.resultado.value,
            "vencedora": d.trace.vencedora,
            "calculo": d.trace.calculo,
            "vereditos": [
                {"regra_id": v.regra_id, "codigo": v.codigo.value, "detalhe": v.detalhe}
                for v in d.trace.vereditos
            ],
        },
    }


@router.post("/preco")
def preco(p: PedidoPreco) -> dict:
    try:
        d, expl = svc().precificar(p.sku, p.quantidade, p.data, p.solicitante)
    except SemVersaoPublicada as e:
        raise HTTPException(409, str(e)) from e
    except EntradaInvalida as e:
        raise HTTPException(400, str(e)) from e
    except ErroDePersistencia as e:
        # A-15: sem registro, sem preço.
        raise HTTPException(503, str(e)) from e
    return _decisao_em_dict(d, expl)


@router.post("/importar")
def importar(
    arquivo: UploadFile = File(...), substituir: bool = Form(False)
) -> dict:
    try:
        res, rel, par = svc().importar(arquivo.file.read(), substituir=substituir)
    except RascunhoConflitante as e:
        raise HTTPException(409, str(e)) from e
    except ErroDeImportacao as e:
        raise HTTPException(400, str(e)) from e
    return {
        "importadas": res.importadas,
        "rejeitadas": [{"linha": r.linha, "motivo": r.motivo} for r in res.rejeitadas],
        "avisos": [{"linha": a.linha, "descricao": a.descricao} for a in res.avisos],
        "colunas_desconhecidas": res.colunas_desconhecidas,
        "paridade": {
            "conferem": par.conferem,
            "total": par.total,
            "divergencias": par.divergencias,
        },
        "validacao": _validacao_em_dict(rel),
    }


def _validacao_em_dict(rel) -> dict:
    return {
        "bloqueia_publicacao": rel.bloqueia_publicacao,
        "erros": [
            {"tipo": e.tipo, "descricao": e.descricao, "regra_ids": list(e.regra_ids)}
            for e in rel.erros
        ],
        "avisos": [{"tipo": a.tipo, "sku": a.sku, "descricao": a.descricao} for a in rel.avisos],
    }


@router.post("/rascunho/validar")
def validar_rascunho() -> dict:
    return _validacao_em_dict(svc().validar_rascunho())


class PedidoPublicacao(BaseModel):
    autor: str
    justificativa: str  # GOV-07/Y7: obrigatória em TODA publicação


@router.post("/publicar")
def publicar(p: PedidoPublicacao) -> dict:
    try:
        v = svc().publicar(p.autor, p.justificativa)
    except EntradaInvalida as e:
        raise HTTPException(422, str(e)) from e
    except ErroDePersistencia as e:
        raise HTTPException(503, str(e)) from e
    return {"versao": v.numero, "vigente_desde": v.vigente_desde.isoformat(), "autor": v.autor}


@router.post("/republicar/{numero}")
def republicar(numero: int, p: PedidoPublicacao) -> dict:
    try:
        v = svc().republicar(numero, p.autor, p.justificativa)
    except (EntradaInvalida, SemVersaoPublicada) as e:
        raise HTTPException(422, str(e)) from e
    return {"versao": v.numero, "revertida_de": numero, "autor": v.autor}


@router.get("/exportar")
def exportar() -> Response:
    return Response(
        svc().exportar(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="regras.csv"'},
    )


@router.get("/historico")
def historico(sku: str | None = Query(None), limite: int = Query(100, le=1000)) -> list[dict]:
    return [
        {
            "decisao_id": d.id,
            "sku": d.sku,
            "quantidade": d.quantidade,
            "data_pedido": d.data_pedido.isoformat(),
            "versao_regras": d.versao_regras,
            "preco_unitario": d.preco_unitario.iso(),
            "total": d.total.iso(),
            "solicitante": d.solicitante,
            "registrada_em": d.registrada_em.isoformat(),
        }
        for d in svc().historico(sku, limite)
    ]


@router.get("/decisao/{decisao_id}")
def decisao(decisao_id: str) -> dict:
    d = svc()._repo.obter(decisao_id)
    if d is None:
        raise HTTPException(404, f"decisão {decisao_id} não encontrada")
    return _decisao_em_dict(d, "")


@router.post("/decisao/{decisao_id}/recalcular")
def recalcular(decisao_id: str) -> dict:
    """I-7: registrado × recalculado, apresentados como coisas distintas."""
    try:
        d, p = svc().recalcular(decisao_id)
    except (EntradaInvalida, SemVersaoPublicada) as e:
        raise HTTPException(404, str(e)) from e
    return {
        "registrada": {
            "preco_unitario": d.preco_unitario.iso(),
            "versao_regras": d.versao_regras,
            "registrada_em": d.registrada_em.isoformat(),
        },
        "recalculada": {
            "preco_unitario": p.preco_unitario.iso(),
            "versao_regras": svc().versao_vigente_em(d.data_pedido).numero,
        },
        "divergem": d.preco_unitario != p.preco_unitario,
        "nota": (
            "A decisão registrada é a prova do que o motor respondeu. O recálculo "
            "mostra o que as regras vigentes hoje dizem sobre aquela data."
        ),
    }


@router.get("/saude")
def saude() -> dict:
    """OBS-03/OBS-05/OBS-06 — versão vigente, cache e TAXA DE ACERTO.

    A taxa é o critério de revisão do teto declarado em A-22: abaixo de 80%
    em uso real, o teto está errado para o padrão de uso.
    """
    return svc().saude()
