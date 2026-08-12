"""M-02 identidade — chave virtual -> entidade.

Decisao d8780304 / Fase 1: a chave virtual e emitida pelo GATEWAY. O app
consumidor nao detem a chave real do provedor, e por isso nao consegue contornar
o gateway chamando a API diretamente. E o que torna o corte inescapavel em vez
de cooperativo.

Armazenamos apenas o HASH da chave (specs/models §2). Um vazamento do banco nao
entrega credenciais utilizaveis.

V(2)/V(3): a autenticacao de OPERADOR saiu deste modulo e foi para painel-api,
seu unico consumidor (achado ARQ-02).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime

from .persistencia import Persistencia

_PREFIXO = "t25-"


def _hash(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def impressao_digital(chave: str) -> str:
    """Identificador curto e nao reversivel, seguro para log (achado SEG-06).

    O log NUNCA registra a chave virtual — apenas o id da entidade e isto.
    """
    return _hash(chave)[:12]


@dataclass(frozen=True)
class Entidade:
    id: str
    nome: str
    max_tokens: int
    max_reservas: int


class Identidade:
    def __init__(self, persistencia: Persistencia) -> None:
        self._p = persistencia

    def emitir(self, entidade_id: str) -> str:
        """Gera uma chave nova. O valor em claro e devolvido UMA unica vez."""
        chave = _PREFIXO + secrets.token_urlsafe(32)
        with self._p.transacao() as c:
            c.execute(
                "INSERT INTO chave_virtual(hash, entidade_id) VALUES (?,?)",
                (_hash(chave), entidade_id),
            )
        return chave

    def revogar(self, chave: str, agora: datetime) -> bool:
        with self._p.transacao() as c:
            cur = c.execute(
                "UPDATE chave_virtual SET revogada_em=? WHERE hash=? AND revogada_em IS NULL",
                (agora.isoformat(), _hash(chave)),
            )
            return (cur.rowcount or 0) > 0

    def resolver(self, chave: str | None) -> Entidade | None:
        if not chave:
            return None
        r = self._p.conexao().execute(
            "SELECT e.id, e.nome, e.max_tokens, e.max_reservas"
            " FROM chave_virtual k JOIN entidade e ON e.id = k.entidade_id"
            " WHERE k.hash=? AND k.revogada_em IS NULL",
            (_hash(chave),),
        ).fetchone()
        if r is None:
            return None
        return Entidade(r["id"], r["nome"], r["max_tokens"], r["max_reservas"])


class AutenticadorOperador:
    """Senha unica de operador (decisao b67ddd5a).

    Achado SEG-01: comparacao em tempo constante e limite de tentativas.
    O limite e um contador, NUNCA uma espera bloqueante — bloquear aqui
    bloquearia o event loop e, com ele, todo o trafego ao LLM (achado SEG-05).
    """

    def __init__(self, senha_hash: str, max_tentativas: int = 10) -> None:
        self._hash = senha_hash
        self._max = max_tentativas
        self._tentativas: dict[str, int] = {}

    @staticmethod
    def hash_de(senha: str) -> str:
        return _hash(senha)

    def autenticar(self, origem: str, senha: str) -> bool:
        if self._tentativas.get(origem, 0) >= self._max:
            return False
        ok = hmac.compare_digest(_hash(senha), self._hash)
        if ok:
            self._tentativas.pop(origem, None)
        else:
            self._tentativas[origem] = self._tentativas.get(origem, 0) + 1
        return ok

    def bloqueado(self, origem: str) -> bool:
        return self._tentativas.get(origem, 0) >= self._max
