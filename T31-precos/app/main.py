"""Composição da aplicação — o único lugar que amarra os adapters ao núcleo.

SEC-01 🔴: o bind é `127.0.0.1` e NÃO é configurável por variável de ambiente.
A-08 declara que não há autenticação; subir com `--host 0.0.0.0` entregaria a
publicação de preços a qualquer um na rede, com custo de ataque zero. Se um dia
este serviço precisar sair da máquina local, isso é mudança de escopo e volta
para a Fase 0 — não é opção de linha de comando.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from . import api_http, ui_editor_regras, ui_web
from .adaptadores.repositorio_sqlite import RepositorioSQLite
from .servico_aplicacao import ServicoAplicacao

HOST = "127.0.0.1"  # SEC-01: NÃO configurável, de propósito.
# A porta é configurável porque não é controle de segurança — o que protege é
# o host. Útil quando 8000 já está tomada por outro serviço da máquina.
PORTA = int(os.environ.get("T31_PORTA", "8000"))
BANCO = Path(os.environ.get("T31_DB", "t31.db"))


def criar_app(caminho_banco: Path | str = BANCO) -> FastAPI:
    app = FastAPI(
        title="T31 — motor de regras de preço",
        description=(
            "Faixas por quantidade, histórico versionado e explicação da decisão, "
            "substituindo uma planilha legada."
        ),
        version="1.0",
    )
    repo = RepositorioSQLite(caminho_banco)
    servico = ServicoAplicacao(repo)
    for modulo in (api_http, ui_web, ui_editor_regras):
        modulo.configurar(servico)
        app.include_router(modulo.router)
    app.state.servico = servico
    app.state.repo = repo
    return app


app = criar_app()


def main() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORTA)


if __name__ == "__main__":  # pragma: no cover
    main()
