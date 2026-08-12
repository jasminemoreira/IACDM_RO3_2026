"""M-05 troca — máquina de estados e revalidação no aceite.

5 estados (V(3)). Regras que a máquina codifica, cada uma vinda de uma decisão
registrada:

- A revalidação usa a escala VIGENTE no momento do aceite, nunca a de quando a
  troca foi criada. Uma regra só cobre todas as corridas entre trocas
  concorrentes (SC-8) e torna desnecessário um estado ORFA (PRO-05/PRO-06):
  se a escala-base deixou de ser a vigente, a revalidação rejeita com motivo.
- Violação RÍGIDA rejeita, mesmo com o consentimento das duas partes. Violação
  FLEXÍVEL apenas reporta o delta de custo (SC-13): autonomia acima de
  otimalidade, com a consequência visível.
- Expira quando o plantão mais próximo já passou — sem prazo configurável, que
  seria o único número do sistema sem fonte (SC-12).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from .avaliador import avaliar
from .dominio import (
    Alocacao,
    Contexto,
    Escala,
    EstadoEscala,
    EstadoTroca,
    Evento,
    TipoEvento,
)


@dataclass(frozen=True)
class Troca:
    id: str
    escala_id: str
    solicitante_id: str
    destinatario_id: str
    plantao_do_solicitante_id: str
    plantao_do_destinatario_id: str
    estado_troca: EstadoTroca = EstadoTroca.PENDENTE
    criada_em: str = ""
    decidida_em: str = ""
    motivo: str = ""

    def envolve(self, plantao_id: str) -> bool:
        return plantao_id in (
            self.plantao_do_solicitante_id,
            self.plantao_do_destinatario_id,
        )


@dataclass(frozen=True)
class ResultadoTroca:
    troca: Troca
    evento: Evento | None
    aceita: bool
    motivo: str
    delta_custo: int = 0
    termos_piorados: dict | None = None


class TrocaInvalida(Exception):
    pass


def expirou(troca: Troca, ctx: Contexto, hoje: date) -> bool:
    """Expira com o plantão mais próximo envolvido — regra do domínio, sem
    parâmetro arbitrário."""
    datas = [
        ctx.instancia.plantao(troca.plantao_do_solicitante_id).data,
        ctx.instancia.plantao(troca.plantao_do_destinatario_id).data,
    ]
    return min(datas) < hoje


def solicitar(
    id_troca: str,
    escala: Escala,
    ctx: Contexto,
    solicitante_id: str,
    destinatario_id: str,
    quando: str,
) -> Troca:
    """Cria a troca PENDENTE. Valida o que é estrutural agora; o que depende do
    estado da escala é revalidado no aceite."""
    if escala.estado_escala is not EstadoEscala.PUBLICADA:
        raise TrocaInvalida(
            "só escala publicada aceita troca; publique com `publicar` antes"
        )
    if solicitante_id == destinatario_id:
        raise TrocaInvalida("solicitante e destinatário são a mesma pessoa")

    vigente = escala.vigente()
    meus = vigente.plantoes_de(solicitante_id)
    seus = vigente.plantoes_de(destinatario_id)
    if not meus:
        raise TrocaInvalida(f"'{solicitante_id}' não tem plantão nesta escala")
    if not seus:
        raise TrocaInvalida(f"'{destinatario_id}' não tem plantão nesta escala")

    return Troca(
        id=id_troca,
        escala_id=escala.id,
        solicitante_id=solicitante_id,
        destinatario_id=destinatario_id,
        plantao_do_solicitante_id=meus[0],
        plantao_do_destinatario_id=seus[0],
        criada_em=quando,
    )


def solicitar_plantoes(
    id_troca: str,
    escala: Escala,
    ctx: Contexto,
    solicitante_id: str,
    destinatario_id: str,
    plantao_meu: str,
    plantao_dele: str,
    quando: str,
) -> Troca:
    """Variante explícita: o solicitante escolhe quais plantões permutar."""
    base = solicitar(
        id_troca, escala, ctx, solicitante_id, destinatario_id, quando
    )
    vigente = escala.vigente()
    if plantao_meu not in vigente.plantoes_de(solicitante_id):
        raise TrocaInvalida(
            f"plantão '{plantao_meu}' não pertence a '{solicitante_id}'"
        )
    if plantao_dele not in vigente.plantoes_de(destinatario_id):
        raise TrocaInvalida(
            f"plantão '{plantao_dele}' não pertence a '{destinatario_id}'"
        )
    return replace(
        base,
        plantao_do_solicitante_id=plantao_meu,
        plantao_do_destinatario_id=plantao_dele,
    )


def _aplicar_permuta(escala: Escala, troca: Troca) -> Escala:
    alocacoes = list(escala.alocacoes)
    a = Alocacao(troca.solicitante_id, troca.plantao_do_solicitante_id)
    b = Alocacao(troca.destinatario_id, troca.plantao_do_destinatario_id)
    alocacoes.remove(a)
    alocacoes.remove(b)
    alocacoes.append(Alocacao(a.pessoa_id, b.plantao_id))
    alocacoes.append(Alocacao(b.pessoa_id, a.plantao_id))
    return replace(escala, alocacoes=tuple(alocacoes))


def responder(
    troca: Troca,
    aceite: bool,
    escala: Escala,
    ctx: Contexto,
    quem: str,
    quando: str,
    hoje: date,
) -> ResultadoTroca:
    """Aceita ou recusa. No aceite, revalida contra a escala VIGENTE agora."""
    if troca.estado_troca is not EstadoTroca.PENDENTE:
        raise TrocaInvalida(
            f"troca '{troca.id}' já está {troca.estado_troca.value}"
        )

    if expirou(troca, ctx, hoje):
        motivo = "o plantão mais próximo desta troca já passou"
        return ResultadoTroca(
            troca=replace(
                troca,
                estado_troca=EstadoTroca.EXPIRADA,
                decidida_em=quando,
                motivo=motivo,
            ),
            evento=Evento(
                tipo=TipoEvento.EXPIRACAO,
                quem=quem,
                quando=quando,
                dados={"troca": troca.id},
            ),
            aceita=False,
            motivo=motivo,
        )

    if not aceite:
        motivo = "recusada pelo destinatário"
        return ResultadoTroca(
            troca=replace(
                troca,
                estado_troca=EstadoTroca.RECUSADA,
                decidida_em=quando,
                motivo=motivo,
            ),
            evento=None,
            aceita=False,
            motivo=motivo,
        )

    vigente = escala.vigente()
    a = Alocacao(troca.solicitante_id, troca.plantao_do_solicitante_id)
    b = Alocacao(troca.destinatario_id, troca.plantao_do_destinatario_id)
    if a not in vigente.alocacoes or b not in vigente.alocacoes:
        # cobre a corrida entre trocas concorrentes E a escala-base substituída
        motivo = (
            "a escala mudou desde que esta troca foi criada: um dos plantões "
            "não pertence mais a quem pertencia"
        )
        return ResultadoTroca(
            troca=replace(
                troca,
                estado_troca=EstadoTroca.REJEITADA,
                decidida_em=quando,
                motivo=motivo,
            ),
            evento=None,
            aceita=False,
            motivo=motivo,
        )

    antes = avaliar(vigente, ctx)
    depois = avaliar(_aplicar_permuta(vigente, troca), ctx)

    novas_rigidas = [
        v for v in depois.rigidas if v not in antes.rigidas
    ]
    if novas_rigidas:
        motivo = "; ".join(str(v) for v in novas_rigidas[:3])
        return ResultadoTroca(
            troca=replace(
                troca,
                estado_troca=EstadoTroca.REJEITADA,
                decidida_em=quando,
                motivo=motivo,
            ),
            evento=None,
            aceita=False,
            motivo=motivo,
        )

    delta = depois.custo - antes.custo
    piorados = {
        k: depois.custo_por_restricao.get(k, 0) - antes.custo_por_restricao.get(k, 0)
        for k in set(antes.custo_por_restricao) | set(depois.custo_por_restricao)
        if depois.custo_por_restricao.get(k, 0) > antes.custo_por_restricao.get(k, 0)
    }
    evento = Evento(
        tipo=TipoEvento.TROCA_EFETIVADA,
        quem=quem,
        quando=quando,
        dados={
            "troca": troca.id,
            "pessoa_a": troca.solicitante_id,
            "plantao_a": troca.plantao_do_solicitante_id,
            "pessoa_b": troca.destinatario_id,
            "plantao_b": troca.plantao_do_destinatario_id,
        },
    )
    return ResultadoTroca(
        troca=replace(
            troca, estado_troca=EstadoTroca.EFETIVADA, decidida_em=quando
        ),
        evento=evento,
        aceita=True,
        motivo="efetivada",
        delta_custo=delta,
        termos_piorados=piorados,
    )


def cancelar(troca: Troca, quem: str, quando: str) -> Troca:
    """Cancelamento pelo solicitante. Termina em RECUSADA — a capacidade fica,
    o estado extra não (E2/PRO-06); quem encerrou vai no campo motivo."""
    if troca.estado_troca is not EstadoTroca.PENDENTE:
        raise TrocaInvalida(f"troca '{troca.id}' já está {troca.estado_troca.value}")
    if quem != troca.solicitante_id:
        raise TrocaInvalida("só o solicitante pode cancelar a própria troca")
    return replace(
        troca,
        estado_troca=EstadoTroca.RECUSADA,
        decidida_em=quando,
        motivo=f"cancelada pelo solicitante ({quem})",
    )


def de(trocas: list[Troca], pessoa_id: str) -> dict:
    """Recebidas E enviadas (UX-04): sem isso, para o solicitante o pedido
    some depois de enviado."""
    return {
        "recebidas": [
            t
            for t in trocas
            if t.destinatario_id == pessoa_id
            and t.estado_troca is EstadoTroca.PENDENTE
        ],
        "enviadas": [
            t
            for t in trocas
            if t.solicitante_id == pessoa_id
            and t.estado_troca is EstadoTroca.PENDENTE
        ],
    }
