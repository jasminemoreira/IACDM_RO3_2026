"""M-09 painel-api — leitura, configuracao de tetos, autenticacao e estatico.

V(2)/V(3): absorveu a autenticacao de operador (que saiu de identidade) e o
servico da SPA (que saiu de gateway-http). A SPA e servida por um MAPA DE ROTAS
EXPLICITO — sem rota curinga e sem consulta ao sistema de arquivos, portanto sem
superficie de travessia de caminho (achado SEG-02).

Achado ARQ-05 (4 responsabilidades neste modulo) foi ACEITO com justificativa:
servir 3 arquivos por mapa fixo nao e responsabilidade que pague um modulo.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

from .janela import agora, janela_de, proximo_reset
from .persistencia import ENTIDADE, GLOBAL

_ESTATICOS = Path(__file__).parent / "static"
# Mapa EXPLICITO: nenhum caminho vindo do cliente e usado para abrir arquivo.
_ROTAS_ESTATICAS = {
    "/": ("painel.html", "text/html; charset=utf-8"),
    "/painel.css": ("painel.css", "text/css; charset=utf-8"),
    "/painel.js": ("painel.js", "application/javascript; charset=utf-8"),
}


class PainelAPI:
    def __init__(self, persistencia, autenticador, rate_card) -> None:
        self._p = persistencia
        self._auth = autenticador
        self._rc = rate_card
        self._sessoes: set[str] = set()

    # ---------- autenticacao ----------

    async def login(self, req: Request):
        origem = req.client.host if req.client else "desconhecida"
        if self._auth.bloqueado(origem):
            return JSONResponse({"erro": "tentativas_excedidas"}, status_code=429)
        try:
            corpo = await req.json()
        except Exception:
            # Corpo nao-JSON nao pode derrubar o endpoint com 500 (achado do
            # teste de execucao real da Fase 5).
            return JSONResponse({"erro": "corpo_invalido"}, status_code=400)
        if not isinstance(corpo, dict) or not self._auth.autenticar(origem, corpo.get("senha", "")):
            return JSONResponse({"erro": "senha_invalida"}, status_code=401)
        token = secrets.token_urlsafe(24)
        self._sessoes.add(token)
        return JSONResponse({"token": token})

    def _autorizado(self, req: Request) -> bool:
        return req.headers.get("x-t25-operador", "") in self._sessoes

    # ---------- leitura ----------

    async def consumo(self, req: Request):
        if not self._autorizado(req):
            return JSONResponse({"erro": "nao_autorizado"}, status_code=401)
        instante = agora()
        janela = janela_de(instante)
        entidades = self._p.consumo_por_entidade(janela.chave)
        preco_saida = self._rc.preco_saida_mais_caro(instante)
        for e in entidades:
            # Achado UX-04: distinguir "sem dados" de "consumo zero".
            e["sem_dados"] = e["confirmado_nano"] is None
            e["confirmado_nano"] = e["confirmado_nano"] or 0
            e["reservado_nano"] = e["reservado_nano"] or 0
            if e["teto_nano"] is not None:
                comprometido = e["confirmado_nano"] + e["reservado_nano"]
                e["saldo_nano"] = e["teto_nano"] - comprometido
                # Uma requisicao e negada quando a RESERVA de pior caso nao cabe
                # no saldo — nao quando o saldo chega a zero. Sem isto o painel
                # diria "ativa" enquanto o gateway ja responde 402 (divergencia
                # encontrada na execucao real da Fase 5).
                # LIMITE SUPERIOR: ignora o custo do prompt, que tambem entra na
                # reserva. Uma requisicao com este max_tokens pode ainda assim ser
                # negada se o corpo for grande. O rotulo na SPA diz isso.
                e["max_tokens_que_cabem"] = (
                    max(0, e["saldo_nano"]) // preco_saida if preco_saida else 0
                )
                e["cortada"] = e["max_tokens_que_cabem"] == 0
            else:
                e["saldo_nano"] = None
                e["max_tokens_que_cabem"] = 0
                e["cortada"] = True  # sem teto configurado = negada (Motivo.SEM_TETO)
        g = self._p.contador_global(janela.chave)
        if g["teto_nano"] is not None:
            g["saldo_nano"] = g["teto_nano"] - (g["confirmado_nano"] + g["reservado_nano"])
            g["cortado"] = g["saldo_nano"] <= 0
        else:
            g["saldo_nano"] = None
            g["cortado"] = True
        return JSONResponse(
            {
                "janela_inicio": janela.inicio.isoformat(),
                "proximo_reset_utc": proximo_reset(instante).isoformat(),
                "global": g,
                "entidades": entidades,
            }
        )

    # ---------- configuracao ----------

    async def definir_teto(self, req: Request):
        if not self._autorizado(req):
            return JSONResponse({"erro": "nao_autorizado"}, status_code=401)
        entidade_id = req.path_params["entidade_id"]
        try:
            corpo = await req.json()
            valor_nano = int(corpo["valor_nano"])
        except Exception:
            return JSONResponse({"erro": "valor_nano_invalido"}, status_code=400)
        if valor_nano < 0:
            return JSONResponse({"erro": "valor_nano_negativo"}, status_code=400)
        escopo = GLOBAL if entidade_id == "global" else ENTIDADE
        alvo = "" if escopo == GLOBAL else entidade_id
        # Trilha de auditoria (achados SEG-04 / GOV-01): a operacao que desliga o
        # corte e a que mais precisa ser atribuivel.
        self._p.definir_teto(escopo, alvo, valor_nano, ator="operador", agora=agora())
        return JSONResponse({"ok": True, "escopo": escopo, "entidade_id": alvo})

    # ---------- saude ----------

    async def health(self, req: Request):
        instante = agora()
        janela = janela_de(instante)
        inv = self._p.verificar_invariantes(janela.chave)
        vencidos = self._rc.modelos_vencidos(instante)
        ok = inv["i2_ok"] and not vencidos
        return JSONResponse(
            {
                "ok": ok,
                "invariantes": inv,
                "modelos_sem_preco_vigente": vencidos,
                "janela_inicio": janela.inicio.isoformat(),
                "proximo_reset_utc": proximo_reset(instante).isoformat(),
            },
            status_code=200 if ok else 503,
        )

    # ---------- estatico ----------

    async def estatico(self, req: Request):
        rota = req.scope["path"]
        alvo = _ROTAS_ESTATICAS.get(rota)
        if alvo is None:
            return PlainTextResponse("nao encontrado", status_code=404)
        nome, tipo = alvo
        conteudo = (_ESTATICOS / nome).read_text(encoding="utf-8")
        if tipo.startswith("text/html"):
            return HTMLResponse(conteudo)
        return PlainTextResponse(conteudo, media_type=tipo)
