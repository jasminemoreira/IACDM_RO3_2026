"""Composicao e arranque do gateway T25.

Ordem de arranque (V(3)):
  1. carregar rate card (recusa apenas modelos vencidos, nunca a inicializacao)
  2. recuperar reservas orfas de queda de processo
  3. aplicar retencao de eventos — NO ARRANQUE, nunca durante o trafego
  4. servir
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route

from t25.escrow import Escrow
from t25.gateway_http import GatewayHTTP
from t25.identidade import AutenticadorOperador, Identidade
from t25.janela import agora
from t25.painel_api import PainelAPI
from t25.persistencia import Persistencia
from t25.precificador import Precificador
from t25.rate_card import RateCard
from t25.upstream import UpstreamAnthropic, UpstreamSimulado

RAIZ = Path(__file__).parent

logging.basicConfig(
    level=os.environ.get("T25_LOG", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("t25")


def construir(
    banco: str | None = None,
    caminho_rate_card: str | None = None,
    upstream=None,
    senha_operador: str | None = None,
    retencao_dias: int | None = None,
) -> Starlette:
    banco = banco or os.environ.get("T25_BANCO", str(RAIZ / "t25.db"))
    caminho_rate_card = caminho_rate_card or os.environ.get(
        "T25_RATE_CARD", str(RAIZ / "rate_card.json")
    )
    senha = senha_operador or os.environ.get("T25_SENHA_OPERADOR", "operador")
    retencao = (
        retencao_dias
        if retencao_dias is not None
        else int(os.environ.get("T25_RETENCAO_DIAS", "90"))
    )

    rate_card = RateCard.carregar(caminho_rate_card)
    persistencia = Persistencia(banco)

    liberadas = persistencia.recuperar_no_arranque()
    if liberadas:
        log.warning("recuperacao de arranque: %d reserva(s) orfa(s) liberada(s)", liberadas)
    removidos = persistencia.aplicar_retencao(retencao, agora())
    if removidos:
        log.info("retencao: %d evento(s) de uso removido(s)", removidos)

    vencidos = rate_card.modelos_vencidos(agora())
    if vencidos:
        # MEC-03: recusa os modelos vencidos, NAO a inicializacao inteira.
        log.warning("modelos sem preco vigente (serao negados): %s", ", ".join(vencidos))

    if upstream is None:
        chave = os.environ.get("ANTHROPIC_API_KEY")
        upstream = UpstreamAnthropic(chave) if chave else UpstreamSimulado()
        if chave is None:
            log.warning("ANTHROPIC_API_KEY ausente — usando upstream SIMULADO")

    identidade = Identidade(persistencia)
    escrow = Escrow(persistencia)
    precificador = Precificador(rate_card)
    gateway = GatewayHTTP(identidade, escrow, precificador, upstream)
    painel = PainelAPI(persistencia, AutenticadorOperador(AutenticadorOperador.hash_de(senha)), rate_card)

    app = Starlette(
        routes=[
            Route("/v1/messages", gateway.messages, methods=["POST"]),
            Route("/api/login", painel.login, methods=["POST"]),
            Route("/api/consumo", painel.consumo, methods=["GET"]),
            Route("/api/tetos/{entidade_id}", painel.definir_teto, methods=["PUT"]),
            Route("/health", painel.health, methods=["GET"]),
            # Mapa estatico EXPLICITO — sem rota curinga (achado SEG-02).
            Route("/", painel.estatico, methods=["GET"]),
            Route("/painel.css", painel.estatico, methods=["GET"]),
            Route("/painel.js", painel.estatico, methods=["GET"]),
        ]
    )
    app.state.persistencia = persistencia
    app.state.identidade = identidade
    app.state.escrow = escrow
    app.state.precificador = precificador
    app.state.upstream = upstream
    return app


app = construir()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("T25_PORTA", "8025")))
