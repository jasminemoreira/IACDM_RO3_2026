"""M-11 simulador-de-cenario — adaptador de fonte-de-metricas.

Dono da configuração de CENÁRIO: qual cenário, semente, magnitude e persistência
do aquecimento. Essa separação em relação a `configuracao` (que guarda só a
configuração de DECISÃO) é o que torna o critério de acerto CA-0 verificável de
forma estrutural: mesma `Configuracao`, `Cenario` diferente (achado IMP-05).

CONTRATO OBRIGATÓRIO — modelar idade de instância. Em t=0 a série da estável
DEVE diferir mensuravelmente da do baseline, apesar de rodarem a MESMA versão.
Sem isso, baseline e estável seriam indistinguíveis e a decisão mais cara da
Fase 0 — comparar contra baseline pareado — viraria código morto não
demonstrável (premissa A2, achados ASM-01 e ASM-09).

O efeito modelado é o que R-05 descreve: 'cache warmup time, heap size,
load-balancing algorithms'. Instância nova é mais lenta que instância antiga,
e essa diferença NÃO é diferença de versão.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .alvo_de_implantacao import AlvoSimulado, Papel
from .fonte_de_metricas import Amostra, Indisponivel, Resultado
from .julgamento import LATENCIA_P99_SUCESSO, SATURACAO, TAXA_DE_ERRO
from .relogio import Relogio

# --- Linha de base do serviço simulado (valores nominais) --------------------
LATENCIA_BASE = 100.0  # ms
ERRO_BASE = 0.010      # fração de requisições
SATURACAO_BASE = 0.400 # fração de capacidade

# --- Aquecimento: magnitude e persistência, NOMEADAS (achado ASM-09) ---------
FATOR_FRIO = 1.35
"""Instância recém-implantada responde 35% mais devagar enquanto está fria."""

MEIA_VIDA_AQUECIMENTO = 120
"""Tiques até o efeito cair pela metade. Torna 'mensuravelmente' verificável:
em t=0 o fator é 1,35 e decai exponencialmente com esta meia-vida."""


@dataclass(frozen=True)
class Cenario:
    """Configuração de CENÁRIO. Não confundir com `Configuracao` (decisão)."""

    nome: str
    semente: int = 42
    # UC-2: quanto o canário é pior que o baseline (multiplicador).
    degradacao_canario: float = 1.0
    # UC-3: ruído comum, que atinge canário E baseline igualmente.
    ruido_comum_inicio: int | None = None
    ruido_comum_fim: int | None = None
    ruido_comum_fator: float = 1.0
    # UC-4: janela em que o coletor não responde.
    coletor_fora_inicio: int | None = None
    coletor_fora_fim: int | None = None


class SimuladorDeCenario:
    """Implementa a porta `FonteDeMetricas`. Uma chamada, uma amostra (A8)."""

    def __init__(self, cenario: Cenario, relogio: Relogio, alvo: AlvoSimulado) -> None:
        self._cenario = cenario
        self._relogio = relogio
        self._alvo = alvo
        self._rng = random.Random(cenario.semente)

    def coletar(self, papel: str, metrica: str) -> Resultado:
        agora = self._relogio.agora()
        c = self._cenario

        if c.coletor_fora_inicio is not None and c.coletor_fora_fim is not None:
            if c.coletor_fora_inicio <= agora < c.coletor_fora_fim:
                return Indisponivel()

        papel_enum = Papel(papel)
        fator = self._fator_aquecimento(papel_enum, agora)

        if papel_enum is Papel.CANARIO:
            fator *= c.degradacao_canario

        if c.ruido_comum_inicio is not None and c.ruido_comum_fim is not None:
            if c.ruido_comum_inicio <= agora < c.ruido_comum_fim:
                # Ruído de AMBIENTE: atinge as três versões igualmente. É por
                # isso que a comparação concorrente o cancela e um limiar
                # absoluto não cancelaria — o coração do critério CA-0.
                fator *= c.ruido_comum_fator

        return Amostra(valor=self._amostrar(metrica, fator), instante=agora)

    def _fator_aquecimento(self, papel: Papel, agora: int) -> float:
        """Instância nova é mais lenta. Decai exponencialmente com a idade."""
        idade = agora - self._alvo.idades[papel]
        if idade < 0:
            idade = 0
        decaimento = 0.5 ** (idade / MEIA_VIDA_AQUECIMENTO)
        return 1.0 + (FATOR_FRIO - 1.0) * decaimento

    def _amostrar(self, metrica: str, fator: float) -> float:
        if metrica == LATENCIA_P99_SUCESSO.nome:
            return max(1.0, self._rng.gauss(LATENCIA_BASE * fator, LATENCIA_BASE * 0.08))
        if metrica == TAXA_DE_ERRO.nome:
            return max(0.0, self._rng.gauss(ERRO_BASE * fator, ERRO_BASE * 0.25))
        if metrica == SATURACAO.nome:
            return max(0.0, self._rng.gauss(SATURACAO_BASE * fator, SATURACAO_BASE * 0.10))
        raise ValueError(f"métrica desconhecida: {metrica}")


# --- Os quatro cenários dos casos de uso da Fase 0 ---------------------------

UC1_SAUDAVEL = Cenario(
    nome="UC-1 canário saudável",
    degradacao_canario=1.0,
)

UC2_DEGRADADO = Cenario(
    nome="UC-2 canário degradado",
    degradacao_canario=1.40,
)

UC3_RUIDO_COMUM = Cenario(
    nome="UC-3 ruído comum às duas",
    degradacao_canario=1.0,
    ruido_comum_inicio=0,
    ruido_comum_fim=10_000,
    ruido_comum_fator=1.60,
)

UC4_COLETOR_FORA = Cenario(
    nome="UC-4 coletor indisponível",
    degradacao_canario=1.0,
    coletor_fora_inicio=30,
    coletor_fora_fim=60,
)

CENARIOS: dict[str, Cenario] = {
    "uc1": UC1_SAUDAVEL,
    "uc2": UC2_DEGRADADO,
    "uc3": UC3_RUIDO_COMUM,
    "uc4": UC4_COLETOR_FORA,
}
