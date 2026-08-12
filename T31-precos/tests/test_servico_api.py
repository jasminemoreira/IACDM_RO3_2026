"""M-09/M-10 — casos de uso via Facade e API, CS-4, CS-5 e regressões.

Inclui os testes dos DEFEITOS ENCONTRADOS PELO OPERADOR no teste manual da
Fase 5 — que nenhuma das quatro rodadas de crítica havia capturado.
"""

from __future__ import annotations

import threading
import time
from datetime import date, datetime

import pytest

from app.adaptadores.repositorio_sqlite import RepositorioSQLite
from app.dominio.dinheiro import Dinheiro
from app.dominio.modelo_dominio import ResultadoTrace
from app.servico_aplicacao import (
    EntradaInvalida,
    RascunhoConflitante,
    SemVersaoPublicada,
    ServicoAplicacao,
)
from conftest import AGORA, HOJE, csv_corrigido


# --------------------------------------------------------------------------
# UC-1 / UC-6 — precificar pela API
# --------------------------------------------------------------------------


def test_uc1_preco_com_trace(cliente):
    cliente.post(
        "/api/importar",
        files={"arquivo": ("t.csv", csv_corrigido(), "text/csv")},
        data={"substituir": "true"},
    )
    cliente.post("/api/publicar", json={"autor": "T", "justificativa": "teste"})
    r = cliente.post(
        "/api/preco",
        json={"sku": "SKU-1003", "quantidade": 50, "data": "2026-08-12", "solicitante": "checkout"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["preco_unitario"] == "21.90"  # §E P-01
    assert j["total"] == "1095.00"
    assert j["preco_unitario_br"] == "R$ 21,90"  # LIN-04: derivado
    assert j["trace"]["vereditos"], "I-3: trace nunca vazio"
    assert j["explicacao"]


def test_uc1_sku_desconhecido_e_400(cliente):
    cliente.post(
        "/api/importar",
        files={"arquivo": ("t.csv", csv_corrigido(), "text/csv")},
        data={"substituir": "true"},
    )
    cliente.post("/api/publicar", json={"autor": "T", "justificativa": "teste"})
    r = cliente.post(
        "/api/preco", json={"sku": "SKU-0000", "quantidade": 5, "data": "2026-08-12"}
    )
    assert r.status_code == 400  # ASS-02: erro de fronteira, não 500


def test_uc1_sem_versao_publicada_e_409(cliente):
    """ASS-03: estado DISTINTO de 'nenhuma regra casou' (que é 200).

    O cenário é catálogo POPULADO e nenhuma versão publicada — exatamente o
    estado em que o operador ficou preso no teste manual da Fase 5. Com o
    banco vazio o teste mediria outra coisa (catálogo inexistente).
    """
    cliente.post(
        "/api/importar",
        files={"arquivo": ("t.csv", csv_corrigido(), "text/csv")},
        data={"substituir": "true"},
    )
    r = cliente.post(
        "/api/preco", json={"sku": "SKU-1003", "quantidade": 5, "data": "2026-08-12"}
    )
    assert r.status_code == 409


def test_catalogo_vazio_orienta_a_importar(cliente):
    """Sem nada cadastrado, a resposta aponta o caminho em vez de só negar."""
    r = cliente.post(
        "/api/preco", json={"sku": "SKU-1003", "quantidade": 5, "data": "2026-08-12"}
    )
    assert r.status_code == 409
    assert "importe a planilha" in r.json()["detail"]


def test_uc1_data_e_obrigatoria_na_api(cliente):
    """A-04: no contrato de máquina a data não tem default."""
    r = cliente.post("/api/preco", json={"sku": "SKU-1003", "quantidade": 5})
    assert r.status_code == 422


def test_uc6_lacuna_cai_no_preco_base(servico_publicado):
    """§E P-05 — e o trace declara."""
    d, expl = servico_publicado.precificar("SKU-1009", 15, HOJE, "teste")
    assert d.preco_unitario.iso() == "3.20"
    assert d.trace.resultado is ResultadoTrace.PRECO_BASE
    assert "Nenhuma regra" in expl


def test_qtd_zero_rejeitada(servico_publicado):
    """§E P-04: entrada inválida ≠ lacuna."""
    with pytest.raises(EntradaInvalida):
        servico_publicado.precificar("SKU-1003", 0, HOJE, "teste")


# --------------------------------------------------------------------------
# UC-3 — publicar
# --------------------------------------------------------------------------


def test_uc3_bloqueia_com_planilha_suja(servico):
    """V-01 e V-04 barram a publicação da planilha bruta."""
    from conftest import csv_bruto

    servico.importar(csv_bruto(), substituir=True)
    with pytest.raises(EntradaInvalida) as e:
        servico.publicar("T", "tentativa")
    assert "bloqueada" in str(e.value)


def test_uc3_publica_apos_corrigir(servico):
    servico.importar(csv_corrigido(), substituir=True)
    v = servico.publicar("Jasmine", "migração inicial")
    assert v.numero == 1
    assert v.autor == "Jasmine"
    assert v.vigente_desde == AGORA.date()  # A-21: atribuída pelo sistema


def test_uc3_exige_autor_e_justificativa(servico):
    servico.importar(csv_corrigido(), substituir=True)
    with pytest.raises(EntradaInvalida):
        servico.publicar("", "sem autor")  # A-14
    with pytest.raises(ValueError):
        servico.publicar("T", "")  # GOV-07/Y7


def test_pro01_rascunho_vira_copia_da_publicada(servico):
    """PRO-01: sem estado órfão depois de publicar."""
    servico.importar(csv_corrigido(), substituir=True)
    v = servico.publicar("T", "teste")
    chave = lambda r: (r.escopo, r.faixa.minimo)
    assert sorted(map(chave, servico.rascunho_atual())) == sorted(map(chave, v.regras))


def test_pro02_importar_sobre_rascunho_exige_confirmacao(servico):
    """PRO-02/MIG-03: não destrói trabalho em silêncio."""
    servico.importar(csv_corrigido(), substituir=True)
    with pytest.raises(RascunhoConflitante):
        servico.importar(csv_corrigido(), substituir=False)


def test_i4_versao_publicada_e_imutavel(servico_publicado):
    v1 = servico_publicado.versao_vigente_em(HOJE)
    servico_publicado.salvar_rascunho([])
    servico_publicado.publicar("T", "segunda versão vazia")
    assert servico_publicado._repo.versao(1).regras == v1.regras


def test_pro03_republicar_reverte_sem_violar_i4(servico_publicado):
    """PRO-03 + PRO-05/Y7: reverter cria NOVA versão e não toca o rascunho."""
    servico_publicado.salvar_rascunho([])
    rascunho_antes = servico_publicado.rascunho_atual()
    v = servico_publicado.republicar(1, "T", "reversão para a v1")
    assert v.numero == 2
    assert v.origem.revertida_de == 1
    assert servico_publicado.rascunho_atual() == rascunho_antes  # não tocou


# --------------------------------------------------------------------------
# CS-4 — reprodutibilidade temporal (UC-5)
# --------------------------------------------------------------------------


def test_cs4_recalculo_igual_ao_registrado(servico_publicado):
    d, _ = servico_publicado.precificar("SKU-1003", 50, HOJE, "checkout")
    registrada, recalculada = servico_publicado.recalcular(d.id)
    assert registrada.preco_unitario == recalculada.preco_unitario


def test_p11_registrado_diverge_do_recalculado(servico_publicado):
    """I-7: o log prova o que o motor RESPONDEU; o recálculo, o que as regras
    de hoje dizem sobre aquela data. Papéis distintos, e devem divergir quando
    as regras mudam."""
    d, _ = servico_publicado.precificar("SKU-1003", 50, HOJE, "checkout")
    novas = [r for r in servico_publicado.rascunho_atual() if not (r.escopo == "SKU-1003" and r.faixa.minimo == 20)]
    servico_publicado.salvar_rascunho(novas)
    servico_publicado.publicar("T", "removi a faixa 20-99")
    registrada, recalculada = servico_publicado.recalcular(d.id)
    assert registrada.preco_unitario.iso() == "21.90"
    assert recalculada.preco_unitario.iso() == "24.90"  # caiu no preço base


# --------------------------------------------------------------------------
# CS-5 — latência. MEDE, não usa proxy.
# --------------------------------------------------------------------------


def test_cs5_latencia_com_1000_regras(servico):
    """CS-5: < 100 ms por precificação unitária com ~1.000 regras ativas."""
    from app.dominio.modelo_dominio import Faixa, PrecoUnitario, Produto, Regra, Vigencia

    vig = Vigencia(date(2026, 1, 1))
    regras, produtos = [], []
    for i in range(1, 251):
        sku = f"SKU-{i:04d}"
        produtos.append(Produto(sku, f"Produto {i}", Dinheiro.de_texto("10,00")))
        for j, (lo, hi) in enumerate([(1, 9), (10, 49), (50, 199), (200, None)]):
            regras.append(
                Regra(f"R-{sku}-{j}", sku, Faixa(lo, hi),
                      PrecoUnitario(Dinheiro.de_texto("9,00")), 0, vig)
            )
    assert len(regras) == 1000
    servico._repo.salvar_produtos(produtos)
    servico.salvar_rascunho(regras)
    servico.publicar("T", "carga de latência")

    servico.precificar("SKU-0100", 50, HOJE, "aquecimento")
    inicio = time.perf_counter()
    for _ in range(20):
        servico.precificar("SKU-0100", 50, HOJE, "medição")
    media_ms = (time.perf_counter() - inicio) / 20 * 1000
    print(f"\nCS-5: {media_ms:.2f} ms/precificação com {len(regras)} regras")
    assert media_ms < 100, f"{media_ms:.2f} ms excede o limiar de 100 ms"


# --------------------------------------------------------------------------
# REGRESSÃO — defeitos encontrados pelo OPERADOR no teste manual da Fase 5
# --------------------------------------------------------------------------


def test_regressao_bloqueio_sobrevive_ao_restart(tmp_path):
    """DEFEITO 2 (grave): a trava de publicação vivia só em memória.

    Um restart apagava a evidência de preço base divergente e a versão ficaria
    publicável com um preço escolhido em silêncio — derrotando V-04 e
    reintroduzindo a dor #2. Aqui o serviço é DESCARTADO e reconstruído.
    """
    from conftest import csv_bruto

    caminho = tmp_path / "restart.db"
    s1 = ServicoAplicacao(RepositorioSQLite(caminho), agora=lambda: AGORA)
    s1.importar(csv_bruto(), substituir=True)
    assert any(e.tipo == "preco_base_inconsistente" for e in s1.validar_rascunho().erros)
    del s1  # o processo "morre"

    s2 = ServicoAplicacao(RepositorioSQLite(caminho), agora=lambda: AGORA)
    rel = s2.validar_rascunho()
    assert rel.bloqueia_publicacao, "a trava não sobreviveu ao restart"
    assert any(e.tipo == "preco_base_inconsistente" for e in rel.erros)
    with pytest.raises(EntradaInvalida):
        s2.publicar("T", "não deveria passar")


def test_regressao_orientacao_quando_nao_ha_versao(cliente):
    """DEFEITO 1: a mensagem dizia o que estava errado e não o que fazer.

    O operador repetiu a ação dez vezes. A tela precisa citar o rascunho e
    oferecer o caminho.
    """
    cliente.post(
        "/importar",
        files={"arquivo": ("t.csv", csv_corrigido(), "text/csv")},
        data={"substituir": "1"},
    )
    r = cliente.post(
        "/simular", data={"sku": "SKU-1003", "quantidade": "50", "data": "2026-08-12"}
    )
    assert r.status_code == 200
    html = r.text
    assert "O que fazer" in html
    assert "regras em rascunho" in html
    assert 'href="/regras"' in html


def test_a06_acesso_concorrente(servico_publicado):
    """DEFEITO DE RUNTIME: A-06 dizia 'single-threaded, sem trava' — falso.

    O servidor ASGI executa handlers síncronos em threadpool. Sem o lock, o
    SQLite falha com 'objects created in a thread can only be used in that
    same thread'. Este teste é a regressão disso.
    """
    erros: list[Exception] = []

    def precifica():
        try:
            for _ in range(10):
                servico_publicado.precificar("SKU-1003", 50, HOJE, "concorrente")
        except Exception as e:  # noqa: BLE001
            erros.append(e)

    threads = [threading.Thread(target=precifica) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not erros, erros
    assert len(servico_publicado.historico(limite=1000)) == 80


def test_a15_sem_registro_sem_preco(servico_publicado, monkeypatch):
    """A-15, arbitrada pelo operador: se o log falha, a operação falha."""
    from app.adaptadores.repositorio_sqlite import ErroDePersistencia

    def falha(_):
        raise ErroDePersistencia("disco cheio")

    monkeypatch.setattr(servico_publicado._repo, "registrar", falha)
    with pytest.raises(ErroDePersistencia):
        servico_publicado.precificar("SKU-1003", 50, HOJE, "checkout")


def test_saude_expoe_taxa_de_acerto(servico_publicado):
    """A-22/Y1: o teto de 8 é parâmetro OBSERVÁVEL, não constante de fé."""
    servico_publicado.precificar("SKU-1003", 50, HOJE, "t")
    s = servico_publicado.saude()
    assert s["cache"]["teto"] == 8
    assert "taxa_acerto" in s["cache"]
