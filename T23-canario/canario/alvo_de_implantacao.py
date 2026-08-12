"""M-10 alvo-de-implantacao — PORTA de alocação de tráfego + adaptador.

DONO ÚNICO da distribuição de peso e das suas invariantes. As três participantes
não recebem pesos independentes: os três são DERIVADOS de um único número, o
peso do canário. Isso transforma duas invariantes em consequência estrutural em
vez de convenção que o chamador precisa respeitar (achados ASM-02, SEC-02).

    baseline == canario          (R-03: 'same type and amount of traffic')
    estavel  == 100 - 2*canario  (soma sempre 100)

O teto de exposição vive em `configuracao` e garante estavel >= piso (SUS-03).
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from .configuracao import Configuracao


class Papel(str, Enum):
    ESTAVEL = "estavel"
    BASELINE = "baseline"
    CANARIO = "canario"


class AlvoDeImplantacao(Protocol):
    def aplicar(self, peso_canario: int) -> None: ...

    def distribuicao(self) -> dict[Papel, int]: ...

    def promover(self) -> None: ...

    def reverter(self) -> None: ...


class InvarianteViolada(RuntimeError):
    pass


class AlvoSimulado:
    """Adaptador em memória. Mantém pesos e idade de instância por papel.

    `idade` é o instante de implantação. A estável nasce em tempo negativo
    (vida longa); baseline e canário nascem juntos em t=0. É essa diferença que
    o simulador converte em efeito de aquecimento — sem ela o baseline pareado
    seria indistinguível da estável (premissa A2, achado ASM-01).
    """

    IDADE_ESTAVEL = -10_000

    def __init__(self, cfg: Configuracao) -> None:
        self._cfg = cfg
        self._pesos: dict[Papel, int] = {
            Papel.ESTAVEL: 100,
            Papel.BASELINE: 0,
            Papel.CANARIO: 0,
        }
        self.idades: dict[Papel, int] = {
            Papel.ESTAVEL: self.IDADE_ESTAVEL,
            Papel.BASELINE: 0,
            Papel.CANARIO: 0,
        }
        self._terminal = False

    # --- Comandos ------------------------------------------------------------

    def aplicar(self, peso_canario: int) -> None:
        """Deriva os três pesos do peso do canário e verifica as invariantes."""
        if self._terminal:
            raise InvarianteViolada("alvo já em estado terminal")
        estavel = 100 - 2 * peso_canario
        if estavel < self._cfg.piso_estavel:
            raise InvarianteViolada(
                f"peso {peso_canario}% levaria a estável a {estavel}%, "
                f"abaixo do piso de {self._cfg.piso_estavel}%"
            )
        self._pesos = {
            Papel.ESTAVEL: estavel,
            Papel.BASELINE: peso_canario,
            Papel.CANARIO: peso_canario,
        }
        self._checar()

    def promover(self) -> None:
        """Troca de papéis: o canário vira a estável e serve 100%.

        Idempotente (achado PRO-04). O baseline desaparece — sua razão de existir
        era ser ponto de comparação, e não há mais o que comparar (achado ASM-08).
        """
        if self._terminal:
            return
        self._pesos = {Papel.ESTAVEL: 100, Papel.BASELINE: 0, Papel.CANARIO: 0}
        self.idades[Papel.ESTAVEL] = self.idades[Papel.CANARIO]
        self._terminal = True
        self._checar()

    def reverter(self) -> None:
        """Devolve 100% à estável. Idempotente (achado PRO-04).

        A estável nunca esteve abaixo do piso, logo suas instâncias continuam
        quentes — premissa A10, achado MIG-03.
        """
        if self._terminal:
            return
        self._pesos = {Papel.ESTAVEL: 100, Papel.BASELINE: 0, Papel.CANARIO: 0}
        self._terminal = True
        self._checar()

    # --- Consultas -----------------------------------------------------------

    def distribuicao(self) -> dict[Papel, int]:
        return dict(self._pesos)

    @property
    def terminal(self) -> bool:
        return self._terminal

    def _checar(self) -> None:
        total = sum(self._pesos.values())
        if total != 100:
            raise InvarianteViolada(f"a soma dos pesos é {total}, deveria ser 100")
        if self._pesos[Papel.BASELINE] != self._pesos[Papel.CANARIO]:
            raise InvarianteViolada(
                "baseline e canário devem ter o mesmo peso "
                f"({self._pesos[Papel.BASELINE]} != {self._pesos[Papel.CANARIO]})"
            )
