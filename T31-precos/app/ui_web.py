"""M-11 `ui-web` — três telas: simulador, importação e histórico.

É dono da base visual (template base + CSS), importada em uma direção só por
`ui-editor-regras` (ARQ-06).

  * SEC-03 — autoescape do Jinja2 LIGADO explicitamente. `descricao` e os
    motivos vêm do CSV, que é dado não confiável.
  * A-04 — o campo de data vem preenchido com "hoje" de forma VISÍVEL e
    editável; o motor nunca lê o relógio.
  * UX-03 — registrado × recalculado aparecem lado a lado e rotulados, não
    como nota de rodapé.
  * UX-08/Y8 — o corte do trace entra por "casou primeiro", nunca por
    prioridade: a regra de prioridade baixa é justamente a que o analista foi
    procurar.
  * Sem CDN — nenhuma dependência de rede em runtime.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .dominio.explicador import motivo_em_texto
from .dominio.modelo_dominio import MotivoCodigo
from .servico_aplicacao import (
    EntradaInvalida,
    RascunhoConflitante,
    SemVersaoPublicada,
    ServicoAplicacao,
)

TETO_VEREDITOS = 10  # Y8: número declarado, com "ver todas" sempre disponível

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.autoescape = True  # SEC-03
templates.env.globals["motivo_em_texto"] = motivo_em_texto

_servico: ServicoAplicacao | None = None


def configurar(servico: ServicoAplicacao) -> None:
    global _servico
    _servico = servico


def svc() -> ServicoAplicacao:
    if _servico is None:  # pragma: no cover
        raise RuntimeError("serviço não configurado")
    return _servico


def resumir_trace(vereditos, quantidade: int, teto: int = TETO_VEREDITOS):
    """Y8/UX-08 — ordem de entrada DESCORRELACIONADA da prioridade.

    1º todas as que casaram (venceu, ou perdeu tendo casado);
    2º as adjacentes por faixa (a imediatamente abaixo e acima da quantidade);
    3º as demais.
    Devolve `(mostrados, total)` para a tela poder dizer "mostrando X de Y".
    """
    casou = {
        MotivoCodigo.VENCEU,
        MotivoCodigo.CANDIDATA,
        MotivoCodigo.PERDEU_POR_PRIORIDADE,
        MotivoCodigo.PERDEU_POR_ESPECIFICIDADE,
    }

    def distancia(v) -> int:
        faixa = v.detalhe.get("faixa", "")
        try:
            minimo = int(str(faixa).split("–")[0])
        except (ValueError, IndexError):
            return 10**9
        return abs(minimo - quantidade)

    prioritarios = [v for v in vereditos if v.codigo in casou]
    resto = sorted((v for v in vereditos if v.codigo not in casou), key=distancia)
    return [*prioritarios, *resto][:teto], len(vereditos)


templates.env.globals["resumir_trace"] = resumir_trace


@router.get("/", response_class=HTMLResponse)
def raiz():
    return RedirectResponse("/simular", status_code=302)


@router.get("/simular", response_class=HTMLResponse)
def simular_form(request: Request):
    return templates.TemplateResponse(
        request,
        "simular.html",
        {"hoje": date.today().isoformat(), "resultado": None, "erro": None},
    )


@router.post("/simular", response_class=HTMLResponse)
def simular(
    request: Request,
    sku: str = Form(...),
    quantidade: str = Form(...),
    data: str = Form(...),
    ver_todas: str = Form(""),
):
    ctx = {"hoje": data, "sku": sku, "quantidade": quantidade, "resultado": None, "erro": None}
    try:
        qtd = int(quantidade)
    except ValueError:
        ctx["erro"] = f"quantidade deve ser um número inteiro, recebido '{quantidade}'"
        return templates.TemplateResponse(request, "simular.html", ctx)
    try:
        d, expl = svc().precificar(sku, qtd, date.fromisoformat(data), "UI do analista")
    except SemVersaoPublicada as e:
        # Defeito encontrado no teste manual do operador: dizer só "não há
        # versão publicada" deixa o analista preso — ele repetiu a ação dez
        # vezes. O estado do rascunho é a informação que faltava.
        ctx["erro"] = str(e)
        ctx["sem_versao"] = {"regras_no_rascunho": len(svc().rascunho_atual())}
        return templates.TemplateResponse(request, "simular.html", ctx)
    except (EntradaInvalida, ValueError) as e:
        ctx["erro"] = str(e)
        return templates.TemplateResponse(request, "simular.html", ctx)
    ctx["resultado"] = {"decisao": d, "explicacao": expl, "ver_todas": bool(ver_todas)}
    return templates.TemplateResponse(request, "simular.html", ctx)


@router.get("/importar", response_class=HTMLResponse)
def importar_form(request: Request):
    return templates.TemplateResponse(request, "importar.html", {"r": None, "erro": None})


@router.post("/importar", response_class=HTMLResponse)
def importar(
    request: Request,
    arquivo: UploadFile = File(...),
    substituir: str = Form(""),
):
    try:
        res, rel, par = svc().importar(arquivo.file.read(), substituir=bool(substituir))
    except RascunhoConflitante as e:
        return templates.TemplateResponse(
            request, "importar.html", {"r": None, "erro": str(e), "confirmar": True}
        )
    except Exception as e:  # ErroDeImportacao e afins
        return templates.TemplateResponse(
            request, "importar.html", {"r": None, "erro": str(e)}
        )
    return templates.TemplateResponse(
        request,
        "importar.html",
        {"r": {"res": res, "val": rel, "par": par}, "erro": None},
    )


@router.get("/historico", response_class=HTMLResponse)
def historico(request: Request, sku: str = "", decisao: str = ""):
    comparacao = None
    if decisao:
        try:
            d, p = svc().recalcular(decisao)
            comparacao = {
                "registrada": d,
                "recalculada": p,
                "divergem": d.preco_unitario != p.preco_unitario,
            }
        except (EntradaInvalida, SemVersaoPublicada):
            comparacao = None
    return templates.TemplateResponse(
        request,
        "historico.html",
        {
            "decisoes": svc().historico(sku or None, 100),
            "sku": sku,
            "comparacao": comparacao,
        },
    )
