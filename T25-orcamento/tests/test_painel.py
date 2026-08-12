"""CA-10 superficie do painel · CA-8 invariante observavel · UC-5 operador."""

from __future__ import annotations

from starlette.testclient import TestClient


def _logado(app):
    c = TestClient(app)
    tok = c.post("/api/login", json={"senha": "segredo"}).json()["token"]
    return c, {"x-t25-operador": tok}


# ---------- CA-10: autenticacao ----------

def test_consumo_sem_token_e_recusado(montar):
    app, *_ = montar()
    assert TestClient(app).get("/api/consumo").status_code == 401


def test_definir_teto_sem_token_e_recusado(montar):
    """A operacao que DESLIGA o corte e a que mais precisa de protecao."""
    app, *_ = montar()
    r = TestClient(app).put("/api/tetos/eb", json={"valor_nano": 999_000_000_000})
    assert r.status_code == 401


def test_login_com_senha_errada_e_recusado(montar):
    app, *_ = montar()
    assert TestClient(app).post("/api/login", json={"senha": "errada"}).status_code == 401


def test_login_com_corpo_nao_json_devolve_400_e_nao_500(montar):
    """Defeito encontrado na execucao real da Fase 5."""
    app, *_ = montar()
    r = TestClient(app).post(
        "/api/login", content=b"isto nao e json", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400


def test_travessia_de_caminho_nao_alcanca_arquivos(montar):
    """SEG-02: a SPA e servida por mapa de rotas explicito, sem consultar o FS."""
    app, *_ = montar()
    c = TestClient(app)
    assert c.get("/").status_code == 200
    for alvo in ("/../app.py", "/etc/passwd", "/painel.html", "/t25.db"):
        assert c.get(alvo).status_code == 404, alvo


# ---------- CA-10: conteudo ----------

def test_consumo_expoe_reset_em_utc_e_estado_de_corte(montar):
    app, *_ = montar(teto_entidade=1.0)
    c, h = _logado(app)
    d = c.get("/api/consumo", headers=h).json()
    assert d["proximo_reset_utc"].endswith("+00:00")
    e = d["entidades"][0]
    assert {"teto_nano", "confirmado_nano", "reservado_nano", "saldo_nano",
            "cortada", "sem_dados", "max_tokens_que_cabem"} <= set(e)


def test_consumo_distingue_sem_dados_de_consumo_zero(montar, corpo_requisicao):
    """UX-04: janela sem requisicao alguma nao tem linha de contador."""
    app, _, chave, _ = montar()
    c, h = _logado(app)
    assert c.get("/api/consumo", headers=h).json()["entidades"][0]["sem_dados"] is True
    TestClient(app).post("/v1/messages", json=corpo_requisicao, headers={"x-api-key": chave})
    assert c.get("/api/consumo", headers=h).json()["entidades"][0]["sem_dados"] is False


def test_entidade_sem_saldo_aparece_como_cortada(montar, corpo_requisicao):
    app, _, chave, _ = montar(teto_entidade=0.0000001)
    c, h = _logado(app)
    assert c.get("/api/consumo", headers=h).json()["entidades"][0]["cortada"] is True


# ---------- UC-5: operador ajusta teto ----------

def test_operador_define_teto_e_a_auditoria_registra_o_ator(montar):
    app, p, _, _ = montar(teto_entidade=1.0)
    c, h = _logado(app)
    assert c.put("/api/tetos/eb", json={"valor_nano": 5_000_000_000}, headers=h).status_code == 200
    d = c.get("/api/consumo", headers=h).json()
    assert d["entidades"][0]["teto_nano"] == 5_000_000_000
    linhas = p.conexao().execute(
        "SELECT ator, para_nano FROM auditoria_teto ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert linhas["ator"] == "operador" and linhas["para_nano"] == 5_000_000_000


def test_valor_de_teto_invalido_e_recusado(montar):
    app, *_ = montar()
    c, h = _logado(app)
    assert c.put("/api/tetos/eb", json={"valor_nano": -1}, headers=h).status_code == 400
    assert c.put("/api/tetos/eb", json={"nada": 1}, headers=h).status_code == 400


# ---------- CA-8: invariante observavel ----------

def test_health_expoe_o_invariante_i2(montar):
    app, *_ = montar()
    d = TestClient(app).get("/health").json()
    assert d["ok"] is True
    assert d["invariantes"]["i2_ok"] is True
    assert d["modelos_sem_preco_vigente"] == []
    assert d["proximo_reset_utc"].endswith("+00:00")
