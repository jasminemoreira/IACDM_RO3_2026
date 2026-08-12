"""UC-1 a UC-4 — os quatro casos de uso da Fase 0.

Cada um com pelo menos um teste positivo e um negativo, conforme o protocolo
da Fase 6.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from canario.alvo_de_implantacao import AlvoSimulado, Papel
from canario.configuracao import Configuracao
from canario.coordenador import Estado, Coordenador, JulgamentoConcluido, MudouEstado
from canario.relogio import RelogioVirtual
from canario.simulador_de_cenario import CENARIOS, Cenario, SimuladorDeCenario


def rodar(cfg: Configuracao, cenario: Cenario):
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(cenario, relogio, alvo)
    coord = Coordenador(cfg, relogio, fonte, alvo)
    eventos: list = []
    coord.assinar(eventos.append)
    desfecho = coord.executar()
    return desfecho, eventos, alvo


@pytest.fixture
def cfg() -> Configuracao:
    return Configuracao(guarda_taxa_erro=0.10, guarda_latencia_p99=400.0)


# --- UC-1 canário saudável ---------------------------------------------------

def test_uc1_promove(cfg: Configuracao) -> None:
    desfecho, _, alvo = rodar(cfg, CENARIOS["uc1"])
    assert desfecho.promovido, f"{desfecho.estado}: {desfecho.motivo}"
    assert alvo.distribuicao()[Papel.ESTAVEL] == 100, "o canário deve virar a estável"


def test_uc1_falso_positivo_isolado_nao_reverte(cfg: Configuracao) -> None:
    """NEGATIVO — o que NÃO deve acontecer.

    Achado MEC-01: com alfa 0,01 e 3 métricas por julgamento, falsos positivos
    isolados são esperados. A tolerância a falhas (R-07) mais a histerese
    (R-06) existem exatamente para que eles não derrubem um canário sadio.
    """
    desfecho, eventos, _ = rodar(cfg, CENARIOS["uc1"])
    reprovacoes = [
        e for e in eventos if isinstance(e, JulgamentoConcluido) and not e.aprovado
    ]
    pausas = [
        e for e in eventos
        if isinstance(e, MudouEstado) and e.para is Estado.PAUSADO
    ]
    assert reprovacoes, "cenário perdeu poder: sem nenhuma reprovação isolada, este teste não verifica nada"
    assert pausas, "uma reprovação isolada deveria ter causado PAUSA"
    assert desfecho.promovido, "reprovação isolada não pode derrubar um canário sadio"


# --- UC-2 canário degradado --------------------------------------------------

def test_uc2_reverte(cfg: Configuracao) -> None:
    desfecho, _, alvo = rodar(cfg, CENARIOS["uc2"])
    assert desfecho.revertido, f"{desfecho.estado}: {desfecho.motivo}"
    assert alvo.distribuicao()[Papel.ESTAVEL] == 100, "rollback devolve 100% à estável"
    assert alvo.distribuicao()[Papel.CANARIO] == 0


@pytest.mark.parametrize("semente", [1, 7, 42, 99, 2024])
def test_uc2_nunca_promove(cfg: Configuracao, semente: int) -> None:
    """NEGATIVO — nenhuma semente promove um canário 40% pior."""
    desfecho, _, _ = rodar(cfg, replace(CENARIOS["uc2"], semente=semente))
    assert not desfecho.promovido, f"semente {semente} promoveu um canário degradado"


# --- UC-3 ruído comum às duas ------------------------------------------------

@pytest.mark.parametrize("semente", [1, 7, 42, 99, 2024])
def test_uc3_nao_reverte(cfg: Configuracao, semente: int) -> None:
    desfecho, _, _ = rodar(cfg, replace(CENARIOS["uc3"], semente=semente))
    assert not desfecho.revertido, (
        f"semente {semente}: ruído comum às duas versões não pode causar rollback "
        f"— {desfecho.motivo}"
    )


# --- UC-4 coletor indisponível -----------------------------------------------

def test_uc4_erro_nao_conta_como_falha(cfg: Configuracao) -> None:
    """O coletor cai e recupera: erro em sucessão, nunca falha do canário."""
    desfecho, eventos, _ = rodar(cfg, CENARIOS["uc4"])
    from canario.coordenador import ErroDeColeta

    erros = [e for e in eventos if isinstance(e, ErroDeColeta)]
    assert erros, "cenário perdeu poder: o coletor não chegou a falhar"
    assert desfecho.promovido, (
        f"o coletor recuperou antes do limite de {cfg.limite_erros_consecutivos} "
        f"erros consecutivos; o canário é sadio e deveria ser promovido — "
        f"{desfecho.estado}: {desfecho.motivo}"
    )


def test_uc4_coletor_permanente_reverte_pelo_motivo_de_erro(cfg: Configuracao) -> None:
    """NEGATIVO — se o coletor NÃO recupera, reverte pelo motivo CERTO.

    Reverter é correto aqui (não se promove o que não se consegue observar),
    mas o motivo precisa ser erro de coleta, e não falha do canário. Confundir
    os dois é o defeito que UC-4 existe para pegar.
    """
    cenario = replace(
        CENARIOS["uc4"], coletor_fora_inicio=20, coletor_fora_fim=10_000
    )
    desfecho, _, _ = rodar(cfg, cenario)
    assert desfecho.revertido
    assert "coleta" in desfecho.motivo.lower(), (
        f"reverteu pelo motivo errado: {desfecho.motivo!r} — o canário não falhou, "
        "o coletor falhou"
    )
    assert desfecho.falhas < cfg.limite_falhas, (
        "erros de coleta não podem ter incrementado o contador de FALHAS"
    )


# --- REG-01: o achado mais perverso da Fase 2 --------------------------------

def test_reg01_canario_sem_trafego_nao_promove(cfg: Configuracao) -> None:
    """NEGATIVO — um canário que PAROU de responder não pode ser promovido.

    Achado REG-01: sem métrica de tráfego, um canário mudo apresenta latência
    e erro melhores e saturação menor — e seria promovido justamente por estar
    quebrado. A defesa é `janela.volumes_comparaveis`.
    """
    from canario.fonte_de_metricas import Amostra, Indisponivel
    from canario.janela import Janela

    class FonteCanarioMudo:
        """Estável e baseline respondem; o canário não produz nada."""

        def __init__(self, relogio):
            self._relogio = relogio

        def coletar(self, papel: str, metrica: str):
            if papel == Papel.CANARIO.value:
                return Indisponivel("canário parou de receber requisições")
            return Amostra(valor=100.0, instante=self._relogio.agora())

    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    coord = Coordenador(cfg, relogio, FonteCanarioMudo(relogio), alvo)
    desfecho = coord.executar()

    assert not desfecho.promovido, (
        "um canário sem tráfego foi PROMOVIDO — suas métricas parecem ótimas "
        "porque ele não está servindo ninguém"
    )
    assert alvo.distribuicao()[Papel.ESTAVEL] == 100


def test_reg01_volumes_divergentes_recusam_julgamento(cfg: Configuracao) -> None:
    """A defesa é do módulo `janela`, e é testável isoladamente."""
    from canario.janela import Janela
    from canario.julgamento import TAXA_DE_ERRO

    janela = Janela(cfg)
    for _ in range(cfg.amostra_minima):
        janela.adicionar(Papel.BASELINE, TAXA_DE_ERRO.nome, 0.01)
    for _ in range(cfg.amostra_minima // 2):  # metade do volume
        janela.adicionar(Papel.CANARIO, TAXA_DE_ERRO.nome, 0.001)  # e "melhor"

    assert not janela.volumes_comparaveis(TAXA_DE_ERRO.nome)
    assert not janela.pronta(TAXA_DE_ERRO.nome)


def test_reg01_volumes_e_a_unica_defesa_quando_janela_excede_a_amostra() -> None:
    """Este teste existe porque um teste de MUTAÇÃO mostrou que os outros dois
    não tinham poder sobre `volumes_comparaveis`.

    Com tamanho_janela == amostra_minima, `pronta()` já implica contagens
    iguais (o deque satura em maxlen) e a razão é sempre 1,0 — a defesa contra
    REG-01 estava sendo prestada por `pronta()`, e desligar
    `volumes_comparaveis` não quebrava nada de ponta a ponta.

    Com janela MAIOR que a amostra mínima — configuração que `Configuracao`
    permite — existe a faixa em que ambas as séries passam do mínimo mas com
    volumes muito diferentes. É aí, e só aí, que o mecanismo age: canário com
    60 amostras excelentes contra baseline com 120 é um canário que perdeu
    metade do tráfego, não um canário melhor.
    """
    from canario.janela import Janela
    from canario.julgamento import TAXA_DE_ERRO

    cfg = Configuracao(
        guarda_taxa_erro=0.10, guarda_latencia_p99=400.0,
        amostra_minima=50, tamanho_janela=120,
        intervalo=24, taxa_de_amostragem=5,
    )
    janela = Janela(cfg)
    for _ in range(120):
        janela.adicionar(Papel.BASELINE, TAXA_DE_ERRO.nome, 0.01)
    for _ in range(60):
        janela.adicionar(Papel.CANARIO, TAXA_DE_ERRO.nome, 0.001)

    assert janela.pronta(TAXA_DE_ERRO.nome), (
        "ambas passam da amostra mínima — `pronta()` sozinha deixaria julgar"
    )
    assert not janela.volumes_comparaveis(TAXA_DE_ERRO.nome), (
        "razão 60/120 = 0,5 está abaixo de 0,8: o canário perdeu metade do "
        "tráfego e suas métricas 'melhores' não podem ser lidas como saúde"
    )
