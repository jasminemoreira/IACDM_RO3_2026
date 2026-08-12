"""M-09 journal — trilha append-only por acervo.

JSON Lines. `op` vem de um CONJUNTO FECHADO (achado LIN-09): `op` como string livre
tornaria a trilha inagregável, que é o mesmo defeito que a matriz de cobertura evita com
nomes canônicos de lente.

`json.dumps` escapa quebras de linha, o que elimina de graça a injeção de linha falsa de
auditoria (achado SEC-06).

ESCOPO DECLARADO (achado GOV-04, aceito por declaração): este journal é evidência contra
ERRO OPERACIONAL. Não é à prova de alteração deliberada — é um arquivo editável no mesmo
diretório, sem encadeamento de hash. Tornar isso à prova de alteração exigiria hash chain,
que está fora dos três eixos do enunciado.

Uma linha por COMANDO invocado, não por operação interna (achados ASM-09/PRF-05). Rotação é
do operador, como em qualquer log; `info` reporta o tamanho.
"""

from __future__ import annotations

import json
from pathlib import Path

OPS = frozenset({"ingest", "retain", "migrate", "expire", "create"})

JOURNAL_NAME = "journal.jsonl"


class JournalError(Exception):
    pass


def path_of(acervo: Path) -> Path:
    return Path(acervo) / JOURNAL_NAME


def append(acervo: Path, op: str, at: int, report: dict) -> None:
    """Grava uma linha. Chamada DEPOIS do ponto de commit (achado RES-07).

    Se o journal falhar, a operação já aconteceu — logo nunca registramos algo que não
    ocorreu. O inverso (operação sem registro por disco cheio) é o risco aceito, e é o
    menos danoso dos dois.
    """
    if op not in OPS:
        raise JournalError(
            f"op {op!r} não está no conjunto fechado {sorted(OPS)}: "
            "vocabulário livre tornaria a trilha inagregável"
        )
    line = json.dumps(
        {"at": int(at), "op": op, "report": report},
        ensure_ascii=False,
        sort_keys=True,
    )
    p = path_of(acervo)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read(acervo: Path):
    """Itera as linhas. Uma linha ilegível é reportada, não silenciada."""
    p = path_of(acervo)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                yield {"at": 0, "op": "?", "error": f"linha {lineno} ilegível: {exc}"}


def size_bytes(acervo: Path) -> int:
    p = path_of(acervo)
    return p.stat().st_size if p.exists() else 0
