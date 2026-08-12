"""M-07 upstream — Strategy (real | simulado) + Adapter do `usage`.

Strategy: o upstream simulado NAO e utilitario de teste, e modulo do sistema
(decisao f21733c9). Ele permite forjar `refusal`, timeout, stream parcial e
`usage` arbitrario — casos de borda impossiveis de provocar sob demanda contra a
API real, e sem os quais o criterio de acerto nao seria testavel.

Adapter: traduz o `usage` da API para o modelo interno (as QUATRO categorias).
Achado MEC-02: verifica que as categorias conhecidas cobrem o total reportado e
falha alto se nao cobrirem — uma categoria nova de token entraria como nao
contabilizada, em silencio.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol

from .precificador import Uso


class UsageIncompleto(Exception):
    """As categorias conhecidas nao cobrem o total reportado pela API."""


@dataclass
class Resposta:
    conteudo: dict
    uso: Uso
    stop_reason: str | None
    status: int = 200


@dataclass
class ColetorDeUso:
    """Preenchido ao fim do stream: o `usage` chega no evento message_delta."""

    uso: Uso | None = None
    stop_reason: str | None = None
    partes: list[bytes] = field(default_factory=list)


def ttl_de_cache_1h(payload: dict) -> bool:
    """O `usage` NAO informa o TTL do cache; quem informa e a requisicao.

    Divergencia encontrada no micro-check S7: sem isto, escrita de cache com
    ttl='1h' (2,0x) seria cobrada como 5m (1,25x) — subcontabilizacao de 1,6x.
    Varre `system` e `messages` procurando cache_control.ttl == '1h'.
    """

    def varrer(no) -> bool:
        if isinstance(no, dict):
            cc = no.get("cache_control")
            if isinstance(cc, dict) and cc.get("ttl") == "1h":
                return True
            return any(varrer(v) for v in no.values())
        if isinstance(no, list):
            return any(varrer(v) for v in no)
        return False

    return varrer(payload.get("system")) or varrer(payload.get("messages"))


def adaptar_usage(bruto: dict, cache_1h: bool = False) -> Uso:
    entrada = int(bruto.get("input_tokens") or 0)
    leitura = int(bruto.get("cache_read_input_tokens") or 0)
    escrita = int(bruto.get("cache_creation_input_tokens") or 0)
    saida = int(bruto.get("output_tokens") or 0)

    # MEC-02: se a API reportar um total de entrada maior que a soma das
    # categorias conhecidas, ha categoria nova nao contabilizada.
    total_reportado = bruto.get("total_input_tokens")
    if total_reportado is not None and int(total_reportado) > entrada + leitura + escrita:
        raise UsageIncompleto(
            f"total_input_tokens={total_reportado} excede a soma das categorias conhecidas"
            f" ({entrada}+{leitura}+{escrita}). Rate card e adapter precisam de atualizacao."
        )
    return Uso(entrada, leitura, escrita, saida, cache_escrita_1h=cache_1h)


class Upstream(Protocol):
    async def enviar(self, payload: dict, cabecalhos: dict) -> Resposta: ...

    def enviar_stream(
        self, payload: dict, cabecalhos: dict, coletor: ColetorDeUso
    ) -> AsyncIterator[bytes]: ...


class UpstreamAnthropic:
    """Cliente real. A chave do provedor vive AQUI e nunca sai do gateway."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        from anthropic import AsyncAnthropic  # import tardio: dependencia opcional

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._c = AsyncAnthropic(**kwargs)

    async def enviar(self, payload: dict, cabecalhos: dict) -> Resposta:
        msg = await self._c.messages.create(**payload)
        d = msg.model_dump()
        return Resposta(
            conteudo=d,
            uso=adaptar_usage(d.get("usage") or {}, ttl_de_cache_1h(payload)),
            stop_reason=d.get("stop_reason"),
        )

    async def enviar_stream(
        self, payload: dict, cabecalhos: dict, coletor: ColetorDeUso
    ) -> AsyncIterator[bytes]:
        corpo = dict(payload)
        corpo.pop("stream", None)
        async with self._c.messages.stream(**corpo) as stream:
            async for texto in stream.text_stream:
                yield _sse("content_block_delta", {"delta": {"type": "text_delta", "text": texto}})
            final = await stream.get_final_message()
            d = final.model_dump()
            coletor.uso = adaptar_usage(d.get("usage") or {}, ttl_de_cache_1h(payload))
            coletor.stop_reason = d.get("stop_reason")
            yield _sse("message_stop", {"type": "message_stop"})


def _sse(evento: str, dados: dict) -> bytes:
    return f"event: {evento}\ndata: {json.dumps(dados)}\n\n".encode("utf-8")


class UpstreamSimulado:
    """Upstream controlavel. `roteiro` permite forjar cada caso de borda."""

    def __init__(self, roteiro: dict | None = None) -> None:
        # roteiro: {'uso': {...}, 'stop_reason': ..., 'atraso_s': ..., 'erro': ...}
        self.roteiro = roteiro or {}
        self.chamadas: list[dict] = []

    def _resposta(self, payload: dict | None = None) -> Resposta:
        uso_bruto = self.roteiro.get(
            "uso", {"input_tokens": 100, "output_tokens": 50}
        )
        cache_1h = ttl_de_cache_1h(payload or {})
        return Resposta(
            conteudo={
                "id": "msg_simulado",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "resposta simulada"}],
                "usage": uso_bruto,
                "stop_reason": self.roteiro.get("stop_reason", "end_turn"),
            },
            uso=adaptar_usage(uso_bruto, cache_1h),
            stop_reason=self.roteiro.get("stop_reason", "end_turn"),
        )

    async def enviar(self, payload: dict, cabecalhos: dict) -> Resposta:
        self.chamadas.append(payload)
        if self.roteiro.get("atraso_s"):
            await asyncio.sleep(self.roteiro["atraso_s"])
        if self.roteiro.get("erro"):
            raise RuntimeError(self.roteiro["erro"])
        return self._resposta(payload)

    async def enviar_stream(
        self, payload: dict, cabecalhos: dict, coletor: ColetorDeUso
    ) -> AsyncIterator[bytes]:
        self.chamadas.append(payload)
        yield _sse("content_block_delta", {"delta": {"type": "text_delta", "text": "simulado"}})
        if self.roteiro.get("atraso_s"):
            await asyncio.sleep(self.roteiro["atraso_s"])
        if self.roteiro.get("erro"):
            raise RuntimeError(self.roteiro["erro"])
        r = self._resposta(payload)
        coletor.uso = r.uso
        coletor.stop_reason = r.stop_reason
        yield _sse("message_stop", {"type": "message_stop"})
