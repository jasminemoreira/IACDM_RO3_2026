"""M-06 janela — funcao pura, sem estado e sem evento de virada.

Arquitetura V(3): a virada de janela NAO e um evento. Nenhum modulo e dono do
reset; a linha de contador e criada preguicosamente e `janela_inicio` faz parte
da chave. Este modulo apenas calcula limites a partir de um instante fornecido.

Decisao b7fbe77c: a janela mensal vira a meia-noite UTC do dia 1 — sem horario
de verao, sem instante inexistente ou duplicado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Janela:
    inicio: datetime
    fim: datetime  # exclusivo

    @property
    def chave(self) -> str:
        """Identificador estavel da janela, usado como parte da chave primaria."""
        return self.inicio.isoformat()


def _exigir_utc(instante: datetime) -> datetime:
    if instante.tzinfo is None:
        raise ValueError("instante sem fuso horario: a janela e definida em UTC")
    return instante.astimezone(timezone.utc)


def janela_de(instante: datetime) -> Janela:
    """Janela mensal de calendario, em UTC, que contem `instante`."""
    t = _exigir_utc(instante)
    inicio = datetime(t.year, t.month, 1, tzinfo=timezone.utc)
    if t.month == 12:
        fim = datetime(t.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fim = datetime(t.year, t.month + 1, 1, tzinfo=timezone.utc)
    return Janela(inicio=inicio, fim=fim)


def proximo_reset(instante: datetime) -> datetime:
    """Instante em que a janela vigente termina e o corte se reverte."""
    return janela_de(instante).fim


def agora() -> datetime:
    """Instante de referencia. Capturado UMA VEZ por requisicao (achado A-06)."""
    return datetime.now(timezone.utc)
