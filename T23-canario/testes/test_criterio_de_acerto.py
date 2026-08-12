"""CA-0 — o critério de acerto objetivo da predição selada (§2).

    Com UMA ÚNICA configuração de limiares, o sistema reverte o canário
    degradado (UC-2) E não reverte sob ruído comum às duas versões (UC-3).

Por que este par e não UC-2 sozinho: um limiar absoluto ingênuo PASSA em UC-2
(o canário degradado cruza o limiar) e FALHA em UC-3 (o pico de carga também
cruza, e o sistema reverte um canário inocente). Só o par sob a MESMA
configuração prova que a comparação concorrente foi implementada, e não apenas
declarada nas decisões.

⚠️ Armadilha de falso verde documentada em specs/validation: rodar UC-2 e UC-3
com configurações diferentes faria os dois passarem sem que o mecanismo
existisse. Por isso aqui há UM objeto `Configuracao`, construído uma vez.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from canario.alvo_de_implantacao import AlvoSimulado
from canario.configuracao import Configuracao
from canario.coordenador import Coordenador
from canario.relogio import RelogioVirtual
from canario.simulador_de_cenario import CENARIOS, SimuladorDeCenario

DATASETS = Path(__file__).resolve().parent.parent / "specs" / "datasets"


def executar(cfg: Configuracao, chave: str, semente: int | None = None):
    from dataclasses import replace

    cenario = CENARIOS[chave]
    if semente is not None:
        cenario = replace(cenario, semente=semente)
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(cenario, relogio, alvo)
    coordenador = Coordenador(cfg, relogio, fonte, alvo)
    return coordenador, coordenador.executar()


@pytest.fixture
def cfg() -> Configuracao:
    """UMA configuração. É o ponto inteiro do CA-0."""
    return Configuracao(guarda_taxa_erro=0.10, guarda_latencia_p99=400.0)


def test_ca0_mesma_config_uc2_reverte_uc3_nao(cfg: Configuracao) -> None:
    _, uc2 = executar(cfg, "uc2")
    _, uc3 = executar(cfg, "uc3")

    assert uc2.revertido, f"UC-2 deveria reverter, terminou em {uc2.estado}"
    assert not uc3.revertido, (
        f"UC-3 não deveria reverter — o ruído atinge canário E baseline "
        f"igualmente e a comparação concorrente deve cancelá-lo. "
        f"Terminou em {uc3.estado}: {uc3.motivo}"
    )


def test_ca0_limiar_absoluto_reverteria_uc3() -> None:
    """Sem este teste o CA-0 é vazio.

    Se os dados do UC-3 NÃO cruzassem um limiar absoluto razoável, o cenário
    não distinguiria comparação concorrente de limiar fixo — e 'uc3 não
    reverte' passaria em qualquer implementação, inclusive numa errada.

    Aqui verificamos o contrafactual sobre o GROUND TRUTH depositado: os
    valores absolutos do canário em UC-3 estão inflados o bastante para que um
    limiar calibrado no regime normal (UC-1) dispare.
    """
    uc1 = json.loads((DATASETS / "uc1.json").read_text(encoding="utf-8"))
    uc3 = json.loads((DATASETS / "uc3.json").read_text(encoding="utf-8"))

    normais = uc1["series"]["latencia_p99_sucesso"]["canario"]
    ruidosas = uc3["series"]["latencia_p99_sucesso"]["canario"]

    # Limiar absoluto calibrado com folga de 20% sobre o regime normal.
    limiar = max(normais) * 1.20
    media_ruidosa = sum(ruidosas) / len(ruidosas)

    assert media_ruidosa > limiar, (
        "o cenário UC-3 não é discriminante: seus valores absolutos não cruzam "
        "um limiar calibrado no regime normal, então ele não distingue "
        "comparação concorrente de limiar fixo"
    )


def test_ca0_razoes_do_ground_truth_confirmam_o_mecanismo() -> None:
    """A razão canário/baseline é o que a comparação concorrente enxerga.

    UC-3 tem valores absolutos altos e razão ~1: é exatamente por isso que o
    baseline pareado cancela o ruído de ambiente.
    """
    def razao(chave: str, metrica: str) -> float:
        d = json.loads((DATASETS / f"{chave}.json").read_text(encoding="utf-8"))
        c = d["series"][metrica]["canario"]
        b = d["series"][metrica]["baseline"]
        return (sum(c) / len(c)) / (sum(b) / len(b))

    assert razao("uc1", "latencia_p99_sucesso") == pytest.approx(1.0, abs=0.10)
    assert razao("uc3", "latencia_p99_sucesso") == pytest.approx(1.0, abs=0.10)
    assert razao("uc2", "latencia_p99_sucesso") > 1.25
