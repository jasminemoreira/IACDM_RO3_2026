"""Ferramenta de TESTE: simula uma pessoa editando o evento direto no provedor.

Nao faz parte do produto — existe para que o teste manual da Fase 6 possa
produzir mudanca externa sem passar pelo sincronizador, que e exatamente o que o
sincronizador precisa detectar.

Uso:
    python tools/simulate_external_edit.py <workspace> <lado> <uid> <campo>=<valor> ...
Exemplo:
    python tools/simulate_external_edit.py workspace a compartilhado@t28 location="Sala 9"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from t28agenda.normalizer import to_canonical, to_ics  # noqa: E402
from t28agenda.providers import ProviderAlpha, ProviderBeta, WriteOp  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(__doc__)
        return 1
    workspace, side, uid = Path(argv[0]), argv[1].lower(), argv[2]
    changes = dict(pair.split("=", 1) for pair in argv[3:])

    provider = (
        ProviderAlpha(workspace / "alpha") if side == "a" else ProviderBeta(workspace / "beta")
    )
    for provider_id, ics in provider.all_resources().items():
        event = to_canonical(ics, provider.dialect)
        if event.uid != uid:
            continue
        updated = event.with_fields(sequence=event.sequence + 1, **changes)
        provider.write(WriteOp("update", ics=to_ics(updated, provider.dialect), provider_id=provider_id))
        print(f"lado {side}: {uid} alterado ({', '.join(changes)}) — mudanca EXTERNA ao sincronizador")
        return 0
    print(f"uid {uid} nao encontrado no lado {side}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
