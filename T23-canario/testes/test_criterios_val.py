"""VAL-1 a VAL-12 de specs/validation/acceptance-criteria.md.

Cada teste verifica o critério EXATO, não um proxy. Um teste verde que mede
outra coisa é falsa cobertura — o risco explícito do protocolo da Fase 6.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from canario.alvo_de_implantacao import AlvoSimulado, InvarianteViolada, Papel
from canario.configuracao import Configuracao, ConfiguracaoInvalida
from canario.contadores import Contadores
from canario.coordenador import (
    Coordenador,
    Estado,
    JulgamentoConcluido,
    MudouEstado,
)
from canario.janela import Janela
from canario.julgamento import (
    LATENCIA_P99_SUCESSO,
    SATURACAO,
    TAXA_DE_ERRO,
    Veredito,
    julgar,
)
from canario.relogio import RelogioVirtual
from canario.score import aprova, pontuar
from canario.simulador_de_cenario import CENARIOS, SimuladorDeCenario

DATASETS = Path(__file__).resolve().parent.parent / "specs" / "datasets"


@pytest.fixture
def cfg() -> Configuracao:
    return Configuracao(guarda_taxa_erro=0.10, guarda_latencia_p99=400.0)


def carregar(chave: str) -> dict:
    return json.loads((DATASETS / f"{chave}.json").read_text(encoding="utf-8"))


# --- VAL-1 baseline pareado, nunca a estável de vida longa -------------------

def test_val1_julga_contra_baseline_nao_contra_estavel(cfg: Configuracao) -> None:
    """Contra o GROUND TRUTH depositado.

    A estável é de vida longa e está quente; canário e baseline nasceram
    juntos e estão frios. Um canário SADIO comparado contra a estável parece
    degradado — é exatamente o viés que R-05 descreve. Comparado contra o
    baseline pareado, ele passa.
    """
    d = carregar("uc1")["series"][LATENCIA_P99_SUCESSO.nome]

    contra_baseline = julgar(
        d["canario"], d["baseline"], LATENCIA_P99_SUCESSO, cfg.alfa, cfg.amostra_minima
    )
    contra_estavel = julgar(
        d["canario"], d["estavel"], LATENCIA_P99_SUCESSO, cfg.alfa, cfg.amostra_minima
    )

    assert contra_baseline is Veredito.PASS, (
        "canário sadio contra baseline pareado deve passar"
    )
    assert contra_estavel is Veredito.HIGH, (
        "se comparar contra a estável quente NÃO reprovasse um canário sadio, "
        "o simulador não estaria modelando idade de instância e a decisão "
        "BASELINE PAREADO seria indemonstrável (premissa A2)"
    )


# --- VAL-2 amostra mínima ----------------------------------------------------

def test_val2_abaixo_da_amostra_minima_e_nodata(cfg: Configuracao) -> None:
    """NEGATIVO — 49 pontos dão Nodata, não Pass."""
    d = carregar("uc1")["series"][TAXA_DE_ERRO.nome]
    n = cfg.amostra_minima - 1
    assert (
        julgar(d["canario"][:n], d["baseline"][:n], TAXA_DE_ERRO, cfg.alfa, cfg.amostra_minima)
        is Veredito.NODATA
    )


def test_val2_exatamente_a_amostra_minima_julga(cfg: Configuracao) -> None:
    d = carregar("uc1")["series"][TAXA_DE_ERRO.nome]
    n = cfg.amostra_minima
    assert (
        julgar(d["canario"][:n], d["baseline"][:n], TAXA_DE_ERRO, cfg.alfa, cfg.amostra_minima)
        is not Veredito.NODATA
    )


# --- VAL-3 Nodata fora do denominador ---------------------------------------

def test_val3_nodata_fora_do_denominador() -> None:
    score = pontuar(
        {
            LATENCIA_P99_SUCESSO: Veredito.PASS,
            TAXA_DE_ERRO: Veredito.HIGH,
            SATURACAO: Veredito.NODATA,
        }
    )
    # 1 Pass em 2 considerados = 50, e não 1 em 3 = 33,3
    assert score.valor == pytest.approx(50.0)


def test_val3_todos_nodata_e_indefinido() -> None:
    """NEGATIVO — denominador zero não é aprovação nem reprovação."""
    score = pontuar(dict.fromkeys(
        (LATENCIA_P99_SUCESSO, TAXA_DE_ERRO, SATURACAO), Veredito.NODATA
    ))
    assert score.indefinido
    assert not aprova(score, 100.0)


# --- VAL-4 comparação inclusiva ---------------------------------------------

def test_val4_score_igual_ao_limiar_aprova() -> None:
    """R-03: 'A score of exactly 95 with a pass threshold of 95 results in a pass.'"""
    score = pontuar(dict.fromkeys(
        (LATENCIA_P99_SUCESSO, TAXA_DE_ERRO, SATURACAO), Veredito.PASS
    ))
    assert score.valor == pytest.approx(100.0)
    assert aprova(score, 100.0), "comparação deve ser >= e não >"


def test_val4_um_veredito_high_reprova() -> None:
    score = pontuar(
        {
            LATENCIA_P99_SUCESSO: Veredito.PASS,
            TAXA_DE_ERRO: Veredito.PASS,
            SATURACAO: Veredito.HIGH,
        }
    )
    assert not aprova(score, 100.0)
    assert score.reprovadas == [SATURACAO.nome]


# --- VAL-5 falha vs. erro ----------------------------------------------------

def test_val5_erro_reseta_ao_recuperar(cfg: Configuracao) -> None:
    c = Contadores(cfg)
    for _ in range(3):
        c.registrar_erro("taxa_de_erro")
    assert c.erros_consecutivos("taxa_de_erro") == 3
    assert not c.estourou_erros()

    c.registrar_coleta_ok("taxa_de_erro")
    assert c.erros_consecutivos("taxa_de_erro") == 0, (
        "R-06: erros são efêmeros e recuperam sozinhos — o contador reseta"
    )


def test_val5_falha_nunca_reseta(cfg: Configuracao) -> None:
    """NEGATIVO — falha é total acumulado; sucesso não a apaga."""
    c = Contadores(cfg)
    c.registrar_falha()
    c.registrar_aprovacao()
    c.registrar_falha()
    assert c.falhas == 2, "aprovação não pode zerar o total de falhas"


def test_val5_erros_sao_por_metrica_nao_globais(cfg: Configuracao) -> None:
    """Achado RES-02: uma métrica quebrada não derruba as outras."""
    c = Contadores(cfg)
    for _ in range(cfg.limite_erros_consecutivos - 1):
        c.registrar_erro("taxa_de_erro")
        c.registrar_erro("saturacao")
    assert not c.estourou_erros()
    c.registrar_coleta_ok("saturacao")
    c.registrar_erro("taxa_de_erro")
    assert c.estourou_erros()
    assert c.metrica_estourada() == "taxa_de_erro"


# --- VAL-7 falha detém o avanço sem reverter ---------------------------------

def test_val7_falha_pausa_sem_reverter(cfg: Configuracao) -> None:
    """R-07: falhar DETÉM o avanço; só o acúmulo reverte."""
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc2"], relogio, alvo)
    coord = Coordenador(cfg, relogio, fonte, alvo)
    eventos: list = []
    coord.assinar(eventos.append)
    coord.executar()

    transicoes = [e for e in eventos if isinstance(e, MudouEstado)]
    pausou = [t for t in transicoes if t.para is Estado.PAUSADO]
    reverteu = [t for t in transicoes if t.para is Estado.REVERTIDO]

    assert pausou, "a primeira reprovação deveria ter pausado"
    assert reverteu, "o acúmulo deveria ter revertido"
    assert pausou[0].instante < reverteu[0].instante, (
        "pausou depois de reverter — a ordem prova que a pausa não é um estado real"
    )


# --- VAL-8 fórmulas de temporização de R-07 ----------------------------------

def test_val8_rollback_em_intervalo_vezes_limite_de_falhas(cfg: Configuracao) -> None:
    """R-07: `tempo até rollback = interval * threshold`. Igualdade EXATA."""
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc2"], relogio, alvo)
    desfecho = Coordenador(cfg, relogio, fonte, alvo).executar()

    esperado = cfg.intervalo * cfg.limite_falhas
    assert desfecho.revertido
    assert desfecho.instante_final == esperado, (
        f"rollback em {desfecho.instante_final}, R-07 prevê {esperado}"
    )


def test_val8_promocao_nao_antes_do_minimo(cfg: Configuracao) -> None:
    """`interval * n_passos` é piso: nenhuma promoção pode ser mais rápida."""
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc1"], relogio, alvo)
    desfecho = Coordenador(cfg, relogio, fonte, alvo).executar()

    minimo = cfg.intervalo * len(cfg.pesos)
    assert desfecho.promovido
    assert desfecho.instante_final >= minimo


# --- VAL-9 guarda absoluta sem aguardar a amostra mínima ---------------------

def test_val9_guarda_dispara_com_zero_julgamentos() -> None:
    """A razão de existir da guarda: não esperar significância estatística
    quando a degradação é grosseira."""
    cfg = Configuracao(guarda_taxa_erro=0.012, guarda_latencia_p99=400.0)
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc2"], relogio, alvo)
    desfecho = Coordenador(cfg, relogio, fonte, alvo).executar()

    assert desfecho.revertido
    assert desfecho.julgamentos == 0, (
        "a guarda deve curto-circuitar ANTES de qualquer julgamento estatístico"
    )
    assert "guarda absoluta" in desfecho.motivo


def test_val9_guarda_frouxa_nao_interfere(cfg: Configuracao) -> None:
    """NEGATIVO — com limiar alto, quem decide é a estatística, não a guarda."""
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc2"], relogio, alvo)
    desfecho = Coordenador(cfg, relogio, fonte, alvo).executar()
    assert "guarda absoluta" not in desfecho.motivo


# --- VAL-10 determinismo -----------------------------------------------------

@pytest.mark.parametrize("chave", ["uc1", "uc2", "uc3", "uc4"])
def test_val10_mesma_semente_mesma_trilha(cfg: Configuracao, chave: str) -> None:
    def trilha() -> list[str]:
        relogio = RelogioVirtual()
        alvo = AlvoSimulado(cfg)
        fonte = SimuladorDeCenario(CENARIOS[chave], relogio, alvo)
        coord = Coordenador(cfg, relogio, fonte, alvo)
        eventos: list = []
        coord.assinar(lambda e: eventos.append(repr(e)))
        coord.executar()
        return eventos

    assert trilha() == trilha()


# --- VAL-11 o operador entende POR QUE ---------------------------------------

def test_val11_motivo_nomeia_a_metrica_reprovada(cfg: Configuracao) -> None:
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc2"], relogio, alvo)
    desfecho = Coordenador(cfg, relogio, fonte, alvo).executar()

    assert any(
        m in desfecho.motivo
        for m in (LATENCIA_P99_SUCESSO.nome, TAXA_DE_ERRO.nome, SATURACAO.nome)
    ), f"o motivo não nomeia nenhuma métrica: {desfecho.motivo!r}"


# --- VAL-12 aborto manual ----------------------------------------------------

def test_val12_abortar_encerra_em_revertido(cfg: Configuracao) -> None:
    """A flag é verificada no início de cada iteração do laço monothread."""
    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(CENARIOS["uc1"], relogio, alvo)
    coord = Coordenador(cfg, relogio, fonte, alvo)

    # Aborta na primeira transição observada — meio da execução.
    coord.assinar(lambda e: coord.abortar() if isinstance(e, JulgamentoConcluido) else None)
    desfecho = coord.executar()

    assert desfecho.revertido
    assert "aborto" in desfecho.motivo.lower()
    assert alvo.distribuicao()[Papel.ESTAVEL] == 100


# --- Restrições técnicas de P1/P3 --------------------------------------------

def test_config_barra_teto_de_exposicao() -> None:
    """NEGATIVO — achado SUS-03: a estável nunca perde a maioria."""
    with pytest.raises(ConfiguracaoInvalida, match="teto de exposição"):
        Configuracao(guarda_taxa_erro=0.1, guarda_latencia_p99=400, pesos=(5, 20, 40))


def test_config_barra_julgamentos_dependentes() -> None:
    """NEGATIVO — achado CTL-03: janelas de julgamentos consecutivos devem ser
    disjuntas, senão o limite de falhas conta o mesmo julgamento N vezes."""
    with pytest.raises(ConfiguracaoInvalida, match="não independentes"):
        Configuracao(
            guarda_taxa_erro=0.1, guarda_latencia_p99=400,
            intervalo=5, taxa_de_amostragem=5,
        )


def test_config_exige_limiares_da_guarda() -> None:
    """NEGATIVO — achado SCI-01: sem fonte bibliográfica, sem valor padrão."""
    with pytest.raises(TypeError):
        Configuracao()  # type: ignore[call-arg]


def test_invariantes_de_peso(cfg: Configuracao) -> None:
    alvo = AlvoSimulado(cfg)
    for peso in cfg.pesos:
        alvo.aplicar(peso)
        d = alvo.distribuicao()
        assert sum(d.values()) == 100
        assert d[Papel.BASELINE] == d[Papel.CANARIO], "R-03: mesmo volume de tráfego"
        assert d[Papel.ESTAVEL] >= cfg.piso_estavel


def test_alvo_recusa_peso_acima_do_piso(cfg: Configuracao) -> None:
    """NEGATIVO — a invariante é estrutural, não convenção do chamador."""
    alvo = AlvoSimulado(cfg)
    with pytest.raises(InvarianteViolada):
        alvo.aplicar(40)  # 100 - 80 = 20 < piso 50


def test_promover_e_reverter_idempotentes(cfg: Configuracao) -> None:
    """Achado PRO-04."""
    alvo = AlvoSimulado(cfg)
    alvo.aplicar(cfg.pesos[0])
    alvo.promover()
    alvo.promover()
    alvo.reverter()  # fora de ordem, após terminal
    assert alvo.distribuicao()[Papel.ESTAVEL] == 100


def test_janela_e_deslizante_nao_cumulativa(cfg: Configuracao) -> None:
    """Achados ASM-03, PERF-01, CTL-02: tamanho fixo, descarta o mais antigo."""
    janela = Janela(cfg)
    for i in range(cfg.tamanho_janela * 3):
        janela.adicionar(Papel.CANARIO, TAXA_DE_ERRO.nome, float(i))
    serie = janela.series(Papel.CANARIO, TAXA_DE_ERRO.nome)
    assert len(serie) == cfg.tamanho_janela
    assert serie[0] == float(cfg.tamanho_janela * 2), "deveria ter descartado os antigos"
