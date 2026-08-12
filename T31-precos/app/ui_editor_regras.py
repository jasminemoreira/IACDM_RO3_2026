"""M-12 `ui-editor-regras` — a grade de regras.

Separado de `ui-web` porque é onde mora toda a complexidade (IMP-01) e o
achado 🔴 UX-01: *se editar regra aqui for pior que editar célula na planilha,
o analista volta para a planilha e o motor vira leitura*. A contramedida é
edição em massa com colagem de TSV vinda do clipboard.

Spec completa: `specs/design/ui-editor-regras.md`.

MODO DEGRADADO — arbitragem do operador em resposta a PRO-06: o plano existe,
mas a Fase 5 NÃO pode acioná-lo sozinha. A grade completa foi implementada.

Y4/IMP-06: a grade edita uma LISTA SIMPLES. O `ConjuntoDeRegras` indexado só
nasce na fronteira de avaliação (validar/precificar), nunca por tecla digitada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .dominio.modelo_dominio import (
    ESCOPO_GERAL,
    DescontoPct,
    Faixa,
    PrecoUnitario,
    Regra,
    TipoEfeito,
    Vigencia,
    normalizar_sku,
)
from .dominio.dinheiro import Dinheiro, ErroFormato
from .servico_aplicacao import EntradaInvalida, ServicoAplicacao
from .ui_web import templates

router = APIRouter(tags=["ui"])
_servico: ServicoAplicacao | None = None


def configurar(servico: ServicoAplicacao) -> None:
    global _servico
    _servico = servico


def svc() -> ServicoAplicacao:
    if _servico is None:  # pragma: no cover
        raise RuntimeError("serviço não configurado")
    return _servico


def _linhas_do_rascunho() -> list[dict]:
    linhas = []
    for r in svc().rascunho_atual():
        valor = (
            r.efeito.valor.iso()
            if r.efeito.tipo is TipoEfeito.PRECO_UNITARIO
            else str(r.efeito.pct)
        )
        linhas.append(
            {
                "escopo": r.escopo,
                "de": r.faixa.minimo,
                "ate": r.faixa.maximo if r.faixa.maximo is not None else "",
                "tipo": r.efeito.tipo.value,
                "valor": valor,
                "prioridade": r.prioridade,
                "vig_de": r.vigencia.inicio.isoformat(),
                "vig_ate": r.vigencia.fim.isoformat() if r.vigencia.fim else "",
            }
        )
    return linhas


def _montar(linhas: list[dict]) -> tuple[list[Regra], dict[int, str]]:
    """Converte a grade em regras. Erro é POR CÉLULA, corrigível no lugar."""
    regras: list[Regra] = []
    erros: dict[int, str] = {}
    for i, ln in enumerate(linhas):
        escopo_bruto = (ln.get("escopo") or "").strip()
        if not escopo_bruto:
            continue
        escopo = ESCOPO_GERAL if escopo_bruto == ESCOPO_GERAL else normalizar_sku(escopo_bruto)
        try:
            minimo = int(str(ln.get("de", "")).strip())
        except ValueError:
            erros[i] = "quantidade inicial deve ser um inteiro"
            continue
        ate_txt = str(ln.get("ate", "")).strip()
        try:
            maximo = int(ate_txt) if ate_txt else None
        except ValueError:
            erros[i] = "quantidade final deve ser um inteiro ou vazio"
            continue
        try:
            faixa = Faixa(minimo, maximo)
        except ValueError as e:
            erros[i] = str(e)
            continue

        tipo = TipoEfeito(ln.get("tipo") or TipoEfeito.PRECO_UNITARIO.value)
        bruto = str(ln.get("valor", "")).strip()
        if tipo is TipoEfeito.DESCONTO_PCT:
            try:
                efeito = DescontoPct(Decimal(bruto.rstrip("%").replace(",", ".")))
            except (InvalidOperation, ValueError) as e:
                erros[i] = f"desconto inválido: {e}"
                continue
        else:
            v = Dinheiro.de_texto(bruto)
            if isinstance(v, ErroFormato):
                erros[i] = v.motivo
                continue
            efeito = PrecoUnitario(v)

        try:
            inicio = date.fromisoformat(str(ln.get("vig_de") or date.today().isoformat()))
            fim_txt = str(ln.get("vig_ate") or "").strip()
            fim = date.fromisoformat(fim_txt) if fim_txt else None
        except ValueError:
            erros[i] = "data de vigência inválida (use AAAA-MM-DD)"
            continue

        try:
            prioridade = int(str(ln.get("prioridade", "0")).strip() or 0)
        except ValueError:
            erros[i] = "prioridade deve ser um inteiro"
            continue

        regras.append(
            Regra(
                id=f"R-{escopo}-{minimo}-{maximo if maximo is not None else 'INF'}",
                escopo=escopo,
                faixa=faixa,
                efeito=efeito,
                prioridade=prioridade,
                vigencia=Vigencia(inicio, fim),
            )
        )
    return regras, erros


def _campos(f) -> list[dict]:
    n = len(f.getlist("escopo"))
    col = lambda nome: f.getlist(nome) + [""] * n
    return [
        {
            "escopo": col("escopo")[i],
            "de": col("de")[i],
            "ate": col("ate")[i],
            "tipo": col("tipo")[i],
            "valor": col("valor")[i],
            "prioridade": col("prioridade")[i],
            "vig_de": col("vig_de")[i],
            "vig_ate": col("vig_ate")[i],
        }
        for i in range(n)
    ]


@router.get("/regras", response_class=HTMLResponse)
def regras(request: Request):
    linhas = _linhas_do_rascunho()
    # A validação aparece já no GET: exigir que o analista descubra sozinho
    # que existe um botão "Validar" foi o que o deixou preso no teste manual.
    relatorio = svc().validar_rascunho() if linhas else None
    mensagem = None
    if relatorio is not None and not relatorio.bloqueia_publicacao:
        mensagem = (
            "aviso",
            f"{len(linhas)} regras em rascunho, ainda NÃO publicadas — "
            "o simulador e a API só respondem por versões publicadas. "
            "Informe autor e justificativa abaixo e clique em Publicar versão.",
        )
    return templates.TemplateResponse(
        request,
        "regras.html",
        {
            "linhas": linhas,
            "erros": {},
            "relatorio": relatorio,
            "mensagem": mensagem,
            "hoje": date.today().isoformat(),
        },
    )


@router.post("/regras", response_class=HTMLResponse)
async def salvar(request: Request):
    form = await request.form()
    acao = form.get("acao", "salvar")
    linhas = _campos(form)
    regras, erros = _montar(linhas)

    ctx = {
        "linhas": linhas,
        "erros": erros,
        "relatorio": None,
        "mensagem": None,
        "hoje": date.today().isoformat(),
    }

    if erros:
        ctx["mensagem"] = ("erro", "Corrija as células marcadas antes de continuar.")
        return templates.TemplateResponse(request, "regras.html", ctx)

    svc().salvar_rascunho(regras)
    ctx["linhas"] = _linhas_do_rascunho()

    if acao in ("validar", "publicar"):
        ctx["relatorio"] = svc().validar_rascunho()

    if acao == "publicar":
        autor = (form.get("autor") or "").strip()
        justificativa = (form.get("justificativa") or "").strip()
        reconheceu = bool(form.get("reconheco_avisos"))
        rel = ctx["relatorio"]
        if rel.avisos and not reconheceu:
            ctx["mensagem"] = (
                "aviso",
                "Há avisos de cobertura. Marque que você os viu para publicar "
                "— aviso sem reconhecimento é aviso ignorado.",
            )
            return templates.TemplateResponse(request, "regras.html", ctx)
        try:
            v = svc().publicar(autor, justificativa)
        except EntradaInvalida as e:
            ctx["mensagem"] = ("erro", str(e))
            return templates.TemplateResponse(request, "regras.html", ctx)
        ctx["linhas"] = _linhas_do_rascunho()
        ctx["relatorio"] = svc().validar_rascunho()
        ctx["mensagem"] = (
            "ok",
            f"Versão {v.numero} publicada por {v.autor}, vigente desde "
            f"{v.vigente_desde.strftime('%d/%m/%Y')}.",
        )
    elif acao == "validar":
        ctx["mensagem"] = ("ok", "Rascunho salvo e validado.")
    else:
        ctx["mensagem"] = ("ok", "Rascunho salvo.")

    return templates.TemplateResponse(request, "regras.html", ctx)
