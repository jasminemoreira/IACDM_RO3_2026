"""M-03 escrow — o unico ponto do sistema autorizado a NEGAR uma requisicao.

Metodo Escrow (P. E. O'Neil, "The Escrow Transactional Method", ACM TODS 11(4),
dez. 1986, DOI 10.1145/7239.7265 — ver specs/references/fundamentos-teoricos.md):
updates incrementais nao-bloqueantes sobre quantidade agregada sob contencao,
projetado para transacoes LONGAS. Por isso o contador e o par
(confirmado, reservado) e nao um escalar, e por isso a chamada ao provedor
acontece FORA da secao critica.

Contrato (V(3)):
  1. Atomico sobre os DOIS contadores (global e entidade), numa unica transacao.
     Reservar em um e falhar no outro deixaria saldo preso.
  2. Sem `await` de rede dentro da secao critica. Intencionalmente bloqueante e
     curta — e o que a torna atomica sem lock (decisao de V(2), achado A-01).
  3. `reconciliar` e idempotente por id_reserva.
  4. Sem TTL, sem relogio, sem expiracao: a vida da reserva e a vida da
     requisicao, garantida por bloco `finally` em gateway-http, e a queda de
     processo e tratada por persistencia.recuperar_no_arranque().
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from .janela import janela_de
from .persistencia import ENTIDADE, GLOBAL, Persistencia

log = logging.getLogger("t25.escrow")


class Motivo:
    """Codigo enumerado — o cliente precisa programar contra isto, nao contra
    texto livre (achado LIN-02)."""

    OK = "ok"
    TETO_GLOBAL = "teto_global_esgotado"
    TETO_ENTIDADE = "teto_entidade_esgotado"
    SEM_TETO = "teto_nao_configurado"
    MAX_TOKENS_ACIMA_DO_LIMITE = "max_tokens_acima_do_limite"
    RESERVAS_SIMULTANEAS = "reservas_simultaneas_excedidas"


@dataclass(frozen=True)
class Decisao:
    permitido: bool
    codigo_motivo: str
    id_reserva: str | None = None
    escopo_estourado: str | None = None
    reset_em: str | None = None
    saldo_nano: int | None = None


class Escrow:
    def __init__(self, persistencia: Persistencia) -> None:
        self._p = persistencia

    def reservar(
        self,
        entidade_id: str,
        valor_nano: int,
        instante: datetime,
        max_tokens_pedido: int,
        max_tokens_permitido: int,
        max_reservas: int,
    ) -> Decisao:
        janela = janela_de(instante).chave
        reset = janela_de(instante).fim.isoformat()

        # Defesa contra GAM-01: limita a reserva de pior caso de UMA requisicao.
        if max_tokens_pedido > max_tokens_permitido:
            return Decisao(False, Motivo.MAX_TOKENS_ACIMA_DO_LIMITE, reset_em=reset)

        with self._p.transacao() as c:  # BEGIN IMMEDIATE — secao critica
            # Defesa contra GAM-03: limita o AGREGADO de reservas em voo.
            n_abertas = c.execute(
                "SELECT COUNT(*) AS n FROM reserva WHERE entidade_id=? AND estado='aberta'",
                (entidade_id,),
            ).fetchone()["n"]
            if n_abertas >= max_reservas:
                return Decisao(False, Motivo.RESERVAS_SIMULTANEAS, reset_em=reset)

            escopos = ((GLOBAL, ""), (ENTIDADE, entidade_id))
            menor_saldo = None
            for escopo, ent in escopos:
                teto = self._p.ler_teto(c, escopo, ent)
                if teto is None:
                    return Decisao(
                        False, Motivo.SEM_TETO, escopo_estourado=escopo, reset_em=reset
                    )
                cont = self._p.ler_contador(c, escopo, ent, janela)
                saldo = teto - cont.comprometido_nano
                menor_saldo = saldo if menor_saldo is None else min(menor_saldo, saldo)
                if cont.comprometido_nano + valor_nano > teto:
                    # O mais restritivo vence (decisao b0ea0758).
                    codigo = (
                        Motivo.TETO_GLOBAL if escopo == GLOBAL else Motivo.TETO_ENTIDADE
                    )
                    return Decisao(
                        False,
                        codigo,
                        escopo_estourado=escopo,
                        reset_em=reset,
                        saldo_nano=saldo,
                    )

            id_reserva = uuid.uuid4().hex
            for escopo, ent in escopos:
                self._p.somar_reservado(c, escopo, ent, janela, +valor_nano)
            c.execute(
                "INSERT INTO reserva(id, entidade_id, janela_inicio, valor_nano, estado, criada_em)"
                " VALUES (?,?,?,?, 'aberta', ?)",
                (id_reserva, entidade_id, janela, valor_nano, instante.isoformat()),
            )
            return Decisao(
                True,
                Motivo.OK,
                id_reserva=id_reserva,
                reset_em=reset,
                saldo_nano=menor_saldo,
            )

    def reconciliar(self, id_reserva: str, custo_real_nano: int, evento: dict | None = None) -> bool:
        """Troca a reserva pelo custo real. Idempotente por id_reserva."""
        with self._p.transacao() as c:
            r = c.execute("SELECT * FROM reserva WHERE id=?", (id_reserva,)).fetchone()
            if r is None or r["estado"] != "aberta":
                return False  # ja aplicada
            # Invariante I3: o custo real nunca excede a reserva (pior caso).
            #
            # O clamp preserva o invariante do teto POR CONSTRUCAO. Mas se ele
            # chegar a atuar, a premissa A8 (tokens_entrada <= bytes_do_corpo) ou
            # o limite max_tokens foi violado pela realidade — e ai o clamp
            # converteria um estouro em SUBCONTAGEM SILENCIOSA. Por isso o caso
            # grita: e o unico sinal que denuncia A8 falsa em producao.
            custo = min(custo_real_nano, r["valor_nano"])
            if custo_real_nano > r["valor_nano"]:
                log.error(
                    "RESERVA INSUFICIENTE reserva=%s entidade=%s reservado_nano=%d"
                    " custo_real_nano=%d excedente_nano=%d — premissa A8 ou o limite"
                    " de max_tokens foi violado; o excedente NAO foi contabilizado",
                    id_reserva,
                    r["entidade_id"],
                    r["valor_nano"],
                    custo_real_nano,
                    custo_real_nano - r["valor_nano"],
                )
            for escopo, ent in ((GLOBAL, ""), (ENTIDADE, r["entidade_id"])):
                self._p.somar_reservado(c, escopo, ent, r["janela_inicio"], -r["valor_nano"])
                self._p.somar_confirmado(c, escopo, ent, r["janela_inicio"], +custo)
            c.execute("UPDATE reserva SET estado='reconciliada' WHERE id=?", (id_reserva,))
            if evento is not None:
                self._p.registrar_evento(c, **evento)
            return True

    def liberar(self, id_reserva: str) -> bool:
        """Devolve a reserva integralmente. Usada quando nao houve gasto algum
        (ex.: recusa antes de qualquer saida, erro de rede antes do envio)."""
        with self._p.transacao() as c:
            r = c.execute("SELECT * FROM reserva WHERE id=?", (id_reserva,)).fetchone()
            if r is None or r["estado"] != "aberta":
                return False
            for escopo, ent in ((GLOBAL, ""), (ENTIDADE, r["entidade_id"])):
                self._p.somar_reservado(c, escopo, ent, r["janela_inicio"], -r["valor_nano"])
            c.execute("UPDATE reserva SET estado='liberada' WHERE id=?", (id_reserva,))
            return True
