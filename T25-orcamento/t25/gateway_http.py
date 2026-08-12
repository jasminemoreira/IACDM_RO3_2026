"""M-01 gateway-http — proxy e DONO DO CICLO DE VIDA DA RESERVA.

V(3), simplificacao central: a vida da reserva e a vida da requisicao, nao um
relogio. A reconciliacao ou liberacao acontece num bloco `finally` executado em
TODOS os caminhos de saida — sucesso, erro, timeout, desconexao do cliente,
excecao. Nao existe caminho que deixe reserva aberta. O unico caso restante,
queda do processo, e tratado em persistencia.recuperar_no_arranque().

Fluxo (specs/technical/architecture.md V(3)):
    identidade.resolver -> precificador.pior_caso -> TRANSACAO{escrow.reservar}
    -> upstream.enviar (LONGO, fora da transacao) -> TRANSACAO{reconciliar}

Contrato de passagem (achado LIN-01): apenas POST /v1/messages; lista explicita
de cabecalhos repassados; corpo repassado sem alteracao.

Log (achado SEG-06): NUNCA registra a chave virtual — apenas o id da entidade e
uma impressao digital.
"""

from __future__ import annotations

import json
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from .escrow import Motivo
from .identidade import impressao_digital
from .janela import agora
from .precificador import nano_para_texto
from .rate_card import ModeloSemPreco
from .upstream import ColetorDeUso, UsageIncompleto

log = logging.getLogger("t25.gateway")

# Cabecalhos repassados ao provedor. Lista explicita: nada mais atravessa.
CABECALHOS_REPASSADOS = ("anthropic-version", "anthropic-beta", "content-type")

CODIGO_HTTP_NEGADO = 402  # Payment Required — distinto de 429 do provedor (UX-02)


def _chave_da_requisicao(req: Request) -> str | None:
    chave = req.headers.get("x-api-key")
    if chave:
        return chave
    auth = req.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return None


def _negado(codigo: str, escopo: str | None = None, reset_em: str | None = None, http: int = CODIGO_HTTP_NEGADO):
    return JSONResponse(
        {
            "type": "error",
            "error": {
                "type": codigo,
                "escopo_estourado": escopo,
                "reset_em": reset_em,
                "message": "requisicao negada pelo teto de orcamento do gateway T25",
            },
        },
        status_code=http,
    )


class GatewayHTTP:
    def __init__(self, identidade, escrow, precificador, upstream) -> None:
        self._identidade = identidade
        self._escrow = escrow
        self._precificador = precificador
        self._upstream = upstream

    async def messages(self, req: Request):
        instante = agora()  # capturado UMA VEZ e propagado (achado A-06)

        chave = _chave_da_requisicao(req)
        entidade = self._identidade.resolver(chave)
        if entidade is None:
            log.warning("chave_desconhecida fp=%s", impressao_digital(chave or ""))
            return _negado("chave_virtual_invalida", http=401)

        corpo_bruto = await req.body()
        try:
            payload = json.loads(corpo_bruto)
        except json.JSONDecodeError:
            return _negado("corpo_invalido", http=400)

        modelo = payload.get("model")
        max_tokens = payload.get("max_tokens")
        if not modelo or not isinstance(max_tokens, int) or max_tokens <= 0:
            # Achado A-04: max_tokens ausente nao tem comportamento definido em
            # V(1); aqui e negado, porque e dele que a reserva depende.
            return _negado("model_e_max_tokens_obrigatorios", http=400)

        try:
            pior_caso = self._precificador.pior_caso(
                modelo, len(corpo_bruto), max_tokens, instante
            )
        except ModeloSemPreco:
            # Decisao 52af7cb9: sem preco, nega. Nunca zero, nunca estimado.
            return _negado("modelo_sem_preco_vigente", http=CODIGO_HTTP_NEGADO)

        decisao = self._escrow.reservar(
            entidade_id=entidade.id,
            valor_nano=pior_caso,
            instante=instante,
            max_tokens_pedido=max_tokens,
            max_tokens_permitido=entidade.max_tokens,
            max_reservas=entidade.max_reservas,
        )
        log.info(
            "decisao entidade=%s fp=%s modelo=%s permitido=%s motivo=%s reserva_usd=%s",
            entidade.id,
            impressao_digital(chave or ""),
            modelo,
            decisao.permitido,
            decisao.codigo_motivo,
            nano_para_texto(pior_caso),
        )
        if not decisao.permitido:
            return _negado(decisao.codigo_motivo, decisao.escopo_estourado, decisao.reset_em)

        cabecalhos = {
            k: v for k, v in req.headers.items() if k.lower() in CABECALHOS_REPASSADOS
        }
        if payload.get("stream"):
            return await self._stream(entidade, payload, cabecalhos, decisao, modelo, instante)
        return await self._unico(entidade, payload, cabecalhos, decisao, modelo, instante)

    # ---------- caminhos de saida: ambos com `finally` ----------

    async def _unico(self, entidade, payload, cabecalhos, decisao, modelo, instante):
        resolvida = False
        try:
            resposta = await self._upstream.enviar(payload, cabecalhos)
            custo = self._custo_cobravel(resposta.uso, resposta.stop_reason, modelo, instante)
            self._escrow.reconciliar(
                decisao.id_reserva,
                custo,
                self._evento(entidade, modelo, resposta.uso, custo, resposta.stop_reason, instante),
            )
            resolvida = True
            return JSONResponse(resposta.conteudo, status_code=resposta.status)
        except (UsageIncompleto, ModeloSemPreco) as e:
            log.error("falha de contabilidade: %s", e)
            return _negado("falha_de_contabilidade", http=502)
        finally:
            if not resolvida:
                self._escrow.liberar(decisao.id_reserva)

    async def _stream(self, entidade, payload, cabecalhos, decisao, modelo, instante):
        coletor = ColetorDeUso()

        async def gerar():
            resolvida = False
            try:
                async for pedaco in self._upstream.enviar_stream(payload, cabecalhos, coletor):
                    yield pedaco
                if coletor.uso is not None:
                    custo = self._custo_cobravel(
                        coletor.uso, coletor.stop_reason, modelo, instante
                    )
                    self._escrow.reconciliar(
                        decisao.id_reserva,
                        custo,
                        self._evento(
                            entidade, modelo, coletor.uso, custo, coletor.stop_reason, instante
                        ),
                    )
                    resolvida = True
            finally:
                # Cobre desconexao do cliente, erro do provedor e stream parcial.
                if not resolvida:
                    self._escrow.liberar(decisao.id_reserva)

        return StreamingResponse(gerar(), media_type="text/event-stream")

    # ---------- politica de cobranca ----------

    def _custo_cobravel(self, uso, stop_reason, modelo, instante) -> int:
        """specs/examples §7: recusa ANTES de qualquer saida nao e cobrada."""
        if stop_reason == "refusal" and uso.tokens_saida == 0:
            return 0
        return self._precificador.custo(uso, modelo, instante)

    @staticmethod
    def _evento(entidade, modelo, uso, custo, stop_reason, instante) -> dict:
        import uuid

        return {
            "id": uuid.uuid4().hex,
            "entidade_id": entidade.id,
            "modelo": modelo,
            "tokens_entrada": uso.tokens_entrada,
            "tokens_cache_leitura": uso.tokens_cache_leitura,
            "tokens_cache_escrita": uso.tokens_cache_escrita,
            "tokens_saida": uso.tokens_saida,
            "custo_nano": custo,
            "stop_reason": stop_reason,
            "ocorrido_em": instante.isoformat(),
        }
