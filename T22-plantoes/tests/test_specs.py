"""Suíte spec-driven — Fase 6.

Os testes derivam de specs/validation/criterios-aceitacao.md e das decisões da
Fase 0, NÃO do código. Cada teste verifica o critério exato, não um proxy:
"< 60s" é medido em segundos; "cita o artigo" procura o texto do artigo;
"rejeita" verifica o estado E o motivo.

Quem escreveu os módulos escreveu estes testes na mesma sessão — mitigação
declarada, registrada na decisão de renovação de sessão da Fase 6.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from plantoes import carregador, diagnostico, gerador_sintetico, solver_cpsat
from plantoes import restricoes_legais as RL
from plantoes import troca as T
from plantoes.avaliador import avaliar, derivar_fronteira
from plantoes.dominio import (
    Contexto,
    EstadoEscala,
    EstadoTroca,
    Natureza,
    Origem,
    Preferencia,
    TipoPreferencia,
)
from plantoes.repositorio_json import Repositorio

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable


# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------


def instancia(n_pessoas=12, n_dias=14, semente=0, inicio=None, inviavel=False):
    d = gerador_sintetico.gerar(
        n_pessoas=n_pessoas,
        n_dias=n_dias,
        semente=semente,
        inicio=inicio or date(2026, 9, 1),
        inviavel=inviavel,
    )
    return carregador.carregar_dict(d)


def gerar(inst, escala_id="t", limite=30, ctx=None):
    ctx = ctx or Contexto.sem_historico(inst)
    return solver_cpsat.gerar(ctx, escala_id, limite_s=limite), ctx


def publicada(inst, escala_id="t"):
    r, ctx = gerar(inst, escala_id)
    return replace(r.escala, estado_escala=EstadoEscala.PUBLICADA), ctx


def cli(*args, cwd=None):
    return subprocess.run(
        [PY, "-m", "plantoes.cli", *args],
        cwd=str(cwd or RAIZ),
        capture_output=True,
        text=True,
    )


def par_trocavel(escala, inst):
    """Encontra um par cuja permuta é legalmente viável."""
    datas = {}
    for a in escala.alocacoes:
        datas.setdefault(a.pessoa_id, set()).add(inst.plantao(a.plantao_id).data)
    for a in escala.alocacoes:
        pa = inst.plantao(a.plantao_id)
        for b in escala.alocacoes:
            pb = inst.plantao(b.plantao_id)
            if b.pessoa_id == a.pessoa_id or pa.habilitacao_id != pb.habilitacao_id:
                continue
            da = (datas[a.pessoa_id] - {pa.data}) | {pb.data}
            db = (datas[b.pessoa_id] - {pb.data}) | {pa.data}
            if len(da) != len(datas[a.pessoa_id]) or len(db) != len(datas[b.pessoa_id]):
                continue
            if all(
                d + timedelta(days=1) not in s and d - timedelta(days=1) not in s
                for s in (da, db)
                for d in s
            ):
                return a, b
    return None, None


# --------------------------------------------------------------------------
# UC-1 — gerar
# --------------------------------------------------------------------------


def test_uc1_gera_escala_viavel():
    inst = instancia()
    r, ctx = gerar(inst)
    assert r.escala is not None, r.motivo
    assert avaliar(r.escala, ctx).rigidas == ()


def test_uc1_inviavel_nao_grava_e_diagnostica(tmp_path):
    d = gerador_sintetico.gerar(n_pessoas=8, n_dias=4, inviavel=True)
    caminho = tmp_path / "inv.json"
    caminho.write_text(json.dumps(d), encoding="utf-8")
    p = cli("--dados", str(tmp_path), "gerar", "--instancia", str(caminho), "--id", "x")
    assert p.returncode == 3
    assert not (tmp_path / "escala_x.json").exists()


# --------------------------------------------------------------------------
# UC-2 — consultar
# --------------------------------------------------------------------------


def test_uc2_filtra_por_pessoa(tmp_path):
    _preparar(tmp_path)
    p = cli("--dados", str(tmp_path), "consultar", "--id", "e1", "--pessoa", "p00")
    assert p.returncode == 0
    corpo = [l for l in p.stdout.splitlines() if l.startswith("2026-")]
    assert corpo and all(" p00 " in l for l in corpo)


def test_uc2_escala_inexistente(tmp_path):
    p = cli("--dados", str(tmp_path), "consultar", "--id", "nao-existe")
    assert p.returncode == 2
    assert "não encontrada" in p.stderr
    assert "Traceback" not in p.stderr  # RES-03: nunca stacktrace bruto


def _preparar(tmp_path, n_pessoas=12, n_dias=14):
    """Gera e publica uma escala em tmp_path via CLI."""
    d = gerador_sintetico.gerar(n_pessoas=n_pessoas, n_dias=n_dias)
    caminho = tmp_path / "inst.json"
    caminho.write_text(json.dumps(d), encoding="utf-8")
    p = cli("--dados", str(tmp_path), "gerar", "--instancia", str(caminho), "--id", "e1")
    assert p.returncode == 0, p.stderr
    p = cli("--dados", str(tmp_path), "publicar", "--id", "e1")
    assert p.returncode == 0, p.stderr
    return caminho


# --------------------------------------------------------------------------
# UC-3 — solicitar
# --------------------------------------------------------------------------


def test_uc3_cria_pendente():
    inst = instancia()
    escala, ctx = publicada(inst)
    t = T.solicitar("t1", escala, ctx, "p00", "p01", "agora")
    assert t.estado_troca is EstadoTroca.PENDENTE
    assert t.plantao_do_solicitante_id in escala.plantoes_de("p00")
    assert t.plantao_do_destinatario_id in escala.plantoes_de("p01")


def test_uc3_rascunho_recusa():
    inst = instancia()
    r, ctx = gerar(inst)
    with pytest.raises(T.TrocaInvalida, match="publicada"):
        T.solicitar("t1", r.escala, ctx, "p00", "p01", "agora")


def test_uc3_consigo_mesmo_recusa():
    inst = instancia()
    escala, ctx = publicada(inst)
    with pytest.raises(T.TrocaInvalida, match="mesma pessoa"):
        T.solicitar("t1", escala, ctx, "p00", "p00", "agora")


# --------------------------------------------------------------------------
# UC-4 — responder
# --------------------------------------------------------------------------


def test_uc4_aceite_valido_efetiva():
    inst = instancia()
    escala, ctx = publicada(inst)
    a, b = par_trocavel(escala, inst)
    assert a is not None, "instância sem par trocável — teste inconclusivo"
    t = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r = T.responder(t, True, escala, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
    assert r.aceita and r.troca.estado_troca is EstadoTroca.EFETIVADA
    vig = replace(escala, eventos=escala.eventos + (r.evento,)).vigente()
    assert b.pessoa_id in vig.pessoas_em(a.plantao_id)
    assert a.pessoa_id in vig.pessoas_em(b.plantao_id)


def test_uc4_recusa_humana_nao_altera_escala():
    inst = instancia()
    escala, ctx = publicada(inst)
    t = T.solicitar("t1", escala, ctx, "p00", "p01", "agora")
    r = T.responder(t, False, escala, ctx, "p01", "agora", date(2026, 8, 1))
    assert r.troca.estado_troca is EstadoTroca.RECUSADA
    assert r.evento is None
    assert escala.vigente().alocacoes == escala.alocacoes


# --------------------------------------------------------------------------
# UC-5 — conformidade
# --------------------------------------------------------------------------


def test_uc5_reporta_com_fonte():
    inst = instancia()
    escala, ctx = publicada(inst)
    a = avaliar(escala, ctx)
    assert all(v.fonte for v in a.violacoes)
    assert "resumo" in a.distribuicao and "por_pessoa" in a.distribuicao


# --------------------------------------------------------------------------
# Critérios de sucesso SC-1 .. SC-15
# --------------------------------------------------------------------------


def test_sc1_porte_referencia_sem_rigidas():
    inst = instancia(n_pessoas=30, n_dias=30)
    r, ctx = gerar(inst, limite=60)
    assert r.escala is not None, r.motivo
    assert avaliar(r.escala, ctx).rigidas == ()


def test_sc2_tempo_abaixo_do_limite():
    """Mede o tempo REAL contra 60 s — não verifica apenas 'retorna escala'."""
    inst = instancia(n_pessoas=30, n_dias=30)
    inicio = time.monotonic()
    r, _ = gerar(inst, limite=60)
    decorrido = time.monotonic() - inicio
    assert r.escala is not None
    assert decorrido < 60, f"levou {decorrido:.1f}s"


def test_sc3_determinismo():
    inst = instancia(n_pessoas=20, n_dias=20)
    saidas = [gerar(inst)[0].escala.alocacoes for _ in range(3)]
    assert saidas[0] == saidas[1] == saidas[2]


def test_sc4_diagnostico_localiza_conflito():
    inst = instancia(n_pessoas=8, n_dias=4, inviavel=True)
    conflitos = diagnostico.analisar(inst)
    assert conflitos
    c = conflitos[0]
    texto = str(c)
    assert c.data in texto and c.tipo_de_turno_id in texto
    assert c.habilitacao_id in texto
    assert str(c.exigidos) in texto and str(c.elegiveis) in texto
    assert c.elegiveis < c.exigidos


def test_sc5_subotimo_declarado():
    """Limite ínfimo força FEASIBLE ou falha; em nenhum caso pode afirmar ótimo."""
    inst = instancia(n_pessoas=30, n_dias=30)
    r, _ = gerar(inst, limite=0.01)
    if r.escala is not None and r.status == "FEASIBLE":
        assert r.otimalidade_provada is False
    else:
        assert r.status in ("UNKNOWN", "INFEASIBLE", "OPTIMAL")


def test_sc6_troca_valida_mantem_conformidade():
    inst = instancia()
    escala, ctx = publicada(inst)
    a, b = par_trocavel(escala, inst)
    assert a is not None
    t = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r = T.responder(t, True, escala, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
    assert r.aceita
    depois = replace(escala, eventos=escala.eventos + (r.evento,)).vigente()
    assert avaliar(depois, ctx).rigidas == ()


def test_sc7_troca_ilegal_rejeitada_com_artigo():
    """Rejeita E cita a norma: verificar só o estado seria cobertura falsa."""
    inst = instancia()
    escala, ctx = publicada(inst)
    achou = False
    for a in escala.alocacoes:
        for b in escala.alocacoes:
            if a.pessoa_id == b.pessoa_id:
                continue
            t = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
            r = T.responder(t, True, escala, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
            if r.troca.estado_troca is EstadoTroca.REJEITADA and "CLT art." in r.motivo:
                achou = True
                break
        if achou:
            break
    assert achou, "nenhuma troca foi rejeitada citando artigo da CLT"


def test_sc8_corrida_entre_trocas():
    inst = instancia()
    escala, ctx = publicada(inst)
    a, b = par_trocavel(escala, inst)
    assert a is not None
    t1 = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r1 = T.responder(t1, True, escala, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
    assert r1.aceita
    depois = replace(escala, eventos=escala.eventos + (r1.evento,))
    # segunda troca, criada antes, sobre o MESMO plantão
    t2 = T.Troca("t2", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r2 = T.responder(t2, True, depois, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
    assert not r2.aceita
    assert "escala mudou" in r2.motivo


def test_sc9_emenda_entre_meses():
    """Ninguém que fecha o mês trabalhando abre o seguinte no dia 1 (12x36)."""
    set_ = instancia(n_pessoas=20, n_dias=20, inicio=date(2026, 9, 1))
    r1, ctx1 = gerar(set_, "m1")
    out = instancia(n_pessoas=20, n_dias=20, inicio=date(2026, 9, 21))
    fr = derivar_fronteira([r1.escala], [ctx1], out)
    ctx2 = Contexto(out, fr)
    r2, _ = gerar(out, "m2", ctx=ctx2)
    assert r2.escala is not None, r2.motivo
    fecharam = {k for k, v in fr.items() if v.ultimo_tipo_de_turno_id}
    primeiro = {
        a.pessoa_id
        for a in r2.escala.alocacoes
        if out.plantao(a.plantao_id).data == out.inicio
    }
    assert not (fecharam & primeiro)
    assert avaliar(r2.escala, ctx2).rigidas == ()


def test_sc10_rastreabilidade_normativa():
    inst = instancia()
    escala, ctx = publicada(inst)
    ruim = replace(escala, alocacoes=escala.alocacoes[:3])  # força H2
    for v in avaliar(ruim, ctx).violacoes:
        assert v.fonte, f"violação {v.restricao_id} sem fonte"
        assert v.origem in (Origem.LEGAL, Origem.MODELO, Origem.INTERNA)


def test_sc11_inv2_origem_e_natureza():
    """INV-2: restrição legal é sempre rígida e nunca tem peso."""
    inst = instancia()
    escala, ctx = publicada(inst)
    ruim = replace(escala, alocacoes=escala.alocacoes[:3])
    for v in avaliar(ruim, ctx).violacoes:
        if v.origem is Origem.LEGAL:
            assert v.natureza is Natureza.RIGIDA
            assert v.peso == 0


def test_sc12_expira_com_o_plantao():
    inst = instancia()
    escala, ctx = publicada(inst)
    t = T.solicitar("t1", escala, ctx, "p00", "p01", "agora")
    r = T.responder(t, True, escala, ctx, "p01", "agora", date(2027, 1, 1))
    assert r.troca.estado_troca is EstadoTroca.EXPIRADA


def test_sc13_delta_de_custo_reportado():
    """Troca legal que piora custo: efetiva E informa quais termos pioraram."""
    inst = instancia()
    escala, ctx = publicada(inst)
    a, b = par_trocavel(escala, inst)
    assert a is not None
    pb = inst.plantao(b.plantao_id)
    inst2 = replace(
        inst,
        preferencias=inst.preferencias
        + (
            Preferencia(
                a.pessoa_id, pb.data, TipoPreferencia.INDESEJADO, pb.tipo_de_turno_id
            ),
        ),
    )
    ctx2 = Contexto.sem_historico(inst2)
    t = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r = T.responder(t, True, escala, ctx2, b.pessoa_id, "agora", date(2026, 8, 1))
    assert r.aceita
    assert r.delta_custo > 0
    assert "S4" in (r.termos_piorados or {})


def test_sc14_regeracao_protege_eventos(tmp_path):
    caminho = _preparar(tmp_path)
    p = cli("--dados", str(tmp_path), "gerar", "--instancia", str(caminho), "--id", "e1")
    assert p.returncode == 4
    assert "--force" in p.stderr


def test_sc15_12x36_nao_rejeitado_indevidamente():
    """Escala 12x36 válida não pode acusar violação: L1/L2/L4 não se aplicam
    cumulativamente sob o art. 59-A."""
    inst = instancia()
    assert all(c.regime.value == "12x36" for c in inst.contratos)
    escala, ctx = publicada(inst)
    rigidas = avaliar(escala, ctx).rigidas
    assert rigidas == (), [str(v) for v in rigidas]


# --------------------------------------------------------------------------
# Invariantes e restrições técnicas
# --------------------------------------------------------------------------


@pytest.mark.parametrize("semente", [0, 1, 2, 3, 4])
def test_inv1_gerar_e_verificar_concordam(semente):
    """INV-1 como teste de propriedade: é o que impede aplicar/verificar de
    divergirem em silêncio (ARQ-02, LIN-01)."""
    inst = instancia(n_pessoas=10, n_dias=10, semente=semente)
    r, ctx = gerar(inst, f"s{semente}")
    assert r.escala is not None, r.motivo
    rigidas = avaliar(r.escala, ctx).rigidas
    assert rigidas == (), [str(v) for v in rigidas]


def test_inv3_vigente_deterministica():
    inst = instancia()
    escala, ctx = publicada(inst)
    a, b = par_trocavel(escala, inst)
    t = T.Troca("t1", escala.id, a.pessoa_id, b.pessoa_id, a.plantao_id, b.plantao_id)
    r = T.responder(t, True, escala, ctx, b.pessoa_id, "agora", date(2026, 8, 1))
    com_evento = replace(escala, eventos=escala.eventos + (r.evento,))
    assert com_evento.vigente().alocacoes == com_evento.vigente().alocacoes
    assert set(com_evento.vigente().alocacoes) != set(escala.alocacoes)


def test_l4_configuracao_ilegal_falha_cedo():
    d = gerador_sintetico.gerar(n_pessoas=6, n_dias=4)
    d["contratos"][0]["regime"] = "comum"
    with pytest.raises(carregador.ErroDeValidacao) as e:
        carregador.carregar_dict(d)
    texto = "\n".join(e.value.erros)
    assert "art. 59" in texto
    assert "10h" in texto


def test_l4_nao_se_aplica_ao_regime_12x36():
    """A interação REALMENTE perigosa do art. 59-A.

    Contraparte de `test_l4_configuracao_ilegal_falha_cedo`: o MESMO turno de
    12h que é ilegal sob regime comum precisa carregar sem erro sob 12x36, que
    é exceção expressa ao art. 59. Um motor que aplicasse L4 cumulativamente
    recusaria toda escala de plantão hospitalar — e o sintoma pareceria
    'configuração inválida', não 'regra errada'.
    """
    d = gerador_sintetico.gerar(n_pessoas=6, n_dias=4)
    assert d["contratos"][0]["regime"] == "12x36"
    assert any(t["id"] == "diurno" for t in d["tipos_de_turno"])
    inst = carregador.carregar_dict(d)  # não pode levantar
    assert RL.validar_configuracao(inst) == []


def test_l1_compila_sucessoes_proibidas():
    inst = instancia()
    ctx = Contexto.sem_historico(inst)
    proibidos = RL.pares_proibidos(ctx)
    assert ("noturno", "diurno") in proibidos  # 0h de descanso
    assert ("noturno", "noturno") not in proibidos  # 12h de descanso


def test_regime_altera_natureza_das_regras():
    """Sob 12x36 valem L3; sob regime comum valem L1, L2 e L4 (art. 59-A é
    exceção expressa)."""
    from plantoes.dominio import Regime

    assert RL.se_aplica("L3", Regime.DOZE_TRINTA_SEIS)
    assert not RL.se_aplica("L1", Regime.DOZE_TRINTA_SEIS)
    assert not RL.se_aplica("L2", Regime.DOZE_TRINTA_SEIS)
    assert RL.se_aplica("L1", Regime.COMUM)
    assert RL.se_aplica("L2", Regime.COMUM)
    assert not RL.se_aplica("L3", Regime.COMUM)


def test_guarda_de_peso_de_regra_interna():
    """CIE-01: regra sem fonte não pode dominar as calibradas pelo INRC-II."""
    d = gerador_sintetico.gerar(n_pessoas=6, n_dias=4)
    d["regras_internas"][0]["peso"] = 999
    with pytest.raises(carregador.ErroDeValidacao) as e:
        carregador.carregar_dict(d)
    assert "30" in "\n".join(e.value.erros)


def test_contexto_incompleto_e_recusado():
    """ASS-01/E3: não existe caminho para verificar sem fronteira."""
    inst = instancia()
    with pytest.raises(ValueError, match="incompleto"):
        Contexto(inst, {})


def test_fronteira_invalida_nao_propaga_silenciosamente():
    """CTL-01: escala de origem com violação rígida não propaga estado."""
    from plantoes.avaliador import FronteiraInvalida

    inst = instancia()
    escala, ctx = publicada(inst)
    ruim = replace(escala, alocacoes=escala.alocacoes[:2])  # viola H2
    with pytest.raises(FronteiraInvalida):
        derivar_fronteira([ruim], [ctx], inst)
    fr = derivar_fronteira([ruim], [ctx], inst, aceitar_historico=True)
    assert set(fr) == {p.id for p in inst.pessoas}


# --------------------------------------------------------------------------
# Regressões do teste exploratório da Fase 6
# --------------------------------------------------------------------------


def test_d01_dados_corrompidos_nao_vazam_traceback(tmp_path):
    """D-01: o carregador já tratava a instância de ENTRADA; faltava tratar os
    arquivos que o próprio sistema GRAVA. RES-03 prometeu 'nunca stacktrace
    bruto' e essa metade estava descoberta."""
    (tmp_path / "escala_x.json").write_text("lixo{{{", encoding="utf-8")
    p = cli("--dados", str(tmp_path), "consultar", "--id", "x")
    assert p.returncode == 2
    assert "Traceback" not in p.stderr and "Traceback" not in p.stdout
    assert "corrompido" in p.stderr


def test_d01_dados_com_estrutura_errada_nao_vazam_traceback(tmp_path):
    """JSON válido mas com a forma errada — mesmo modo de falha, mesmo
    tratamento."""
    (tmp_path / "escala_x.json").write_text('{"id":"x"}', encoding="utf-8")
    p = cli("--dados", str(tmp_path), "consultar", "--id", "x")
    assert p.returncode == 2
    assert "Traceback" not in p.stderr
    assert "estrutura inesperada" in p.stderr


def test_b01_force_preserva_escala_anterior(tmp_path):
    """B-01: --force sobrescrevia no mesmo id, quebrando a imutabilidade que
    resolvia GOV-01 e deixando trocas EFETIVADAS apontando para uma escala que
    não continha mais a permuta."""
    caminho = _preparar(tmp_path)
    repo = Repositorio(tmp_path)
    antes = repo.carregar_bruta("e1")

    p = cli("--dados", str(tmp_path), "gerar", "--instancia", str(caminho),
            "--id", "e1", "--force")
    assert p.returncode == 0, p.stderr
    assert "PRESERVADA" in p.stdout

    # a original continua lá, intacta e com o mesmo estado
    depois = repo.carregar_bruta("e1")
    assert depois.alocacoes == antes.alocacoes
    assert depois.estado_escala is antes.estado_escala
    assert depois.eventos == antes.eventos
    # e a nova existe sob outro id
    assert repo.existe("e1-r1")
    assert (tmp_path / "instancia_e1-r1.json").exists()


def test_c01_limite_nao_positivo_recusado_no_parsing(tmp_path):
    """C-01: chegava ao solver e voltava como MODEL_INVALID, cuja mensagem
    culpa o programa por um erro do argumento."""
    caminho = _preparar(tmp_path)
    for valor in ("-5", "0", "abc"):
        p = cli("--dados", str(tmp_path), "gerar", "--instancia", str(caminho),
                "--id", "z", "--limite", valor)
        assert p.returncode == 2, valor
        assert "MODEL_INVALID" not in p.stderr
        assert "defeito do programa" not in p.stderr


def test_a01_pessoa_inexistente_e_erro_explicito(tmp_path):
    """A-01: um erro de digitação no id ficava indistinguível de 'você não tem
    plantões'."""
    _preparar(tmp_path)
    p = cli("--dados", str(tmp_path), "consultar", "--id", "e1",
            "--pessoa", "NAO_EXISTE")
    assert p.returncode == 2
    assert "não existe" in p.stderr

    p = cli("--dados", str(tmp_path), "trocar", "--id", "e1",
            "--pessoa", "p00", "--com", "NAO_EXISTE")
    assert p.returncode == 2
    assert "não existe" in p.stderr

    # pessoa válida sem filtro problemático continua funcionando
    p = cli("--dados", str(tmp_path), "consultar", "--id", "e1", "--pessoa", "p00")
    assert p.returncode == 0


def test_id_com_path_traversal_e_recusado(tmp_path):
    """SEC-03."""
    from plantoes.repositorio_json import ErroDeRepositorio

    repo = Repositorio(tmp_path)
    with pytest.raises(ErroDeRepositorio, match="id inválido"):
        repo.carregar_escala("../../etc/passwd")
