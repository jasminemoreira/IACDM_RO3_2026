"""Suíte adversarial do formato de achado — roda ANTES do T01.

O piloto do §6 custa dois projetos; este teste custa zero. Ele existe para
descobrir fragilidade de formato sem gastar T01 e T05 nisso.

Um fixture bem-formado que passa não ensina nada. O que ensina é o conjunto de
casos malformados: cada um tem que FALHAR ALTO, com mensagem que nomeia o
problema. Se algum for engolido em silêncio, a análise da RO3 sairia parecendo
completa sobre dado que não é.

Uso:  python3 test_formato.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ro3_parser import ErroDeFormato, carregar  # noqa: E402
import ro3_analise  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def montar(tmp: Path, caso: str) -> Path:
    """Workspace temporário = base compartilhada + a coverage-matrix do caso."""
    ws = tmp / caso
    # casos multi-iteração precisam da base com duas declarações de lentes
    if caso in ("12-lente-de-outra-iteracao", "13-iteracao-sem-declaracao",
                "14-duas-iteracoes-validas"):
        base = "base-2it"                     # prosa, duas iterações (pré-v0.14)
    elif caso == "18-v14-sem-declaracao":
        base = "base-v14-sem-decl"            # stateVersion sem activatedLenses
    elif caso in ("16-lente-abreviada", "17-estruturado-valido"):
        base = "base-v14"                     # declaração estruturada
    else:
        base = "base"
    shutil.copytree(FIX / base, ws)
    destino = ws / "specs" / "design"
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIX / "casos" / f"{caso}.md", destino / "coverage-matrix.md")
    return ws


def main() -> int:
    # Cada caso: {"aceita": bool, "mensagem": trecho exigido na recusa}.
    # Verificar só ok/recusado deixa passar uma trava que dispara com a mensagem errada —
    # e mensagem errada manda a sessão corrigir a coisa errada. Foi o que aconteceu com a
    # trava de versão única, que estourava NameError em vez de explicar o problema.
    esperado = json.loads((FIX / "casos" / "esperado.json").read_text(encoding="utf-8"))
    falhas = []

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for caso in sorted(esperado):
            spec = esperado[caso]
            deve_passar, trecho = spec["aceita"], spec.get("mensagem")
            ws = montar(tmp, caso)
            try:
                proj = carregar(ws)
                ok, msg = deve_passar, f"aceito ({len(proj.achados)} achados)"
            except ErroDeFormato as e:
                texto = str(e)
                ok = not deve_passar
                msg = f"recusado — {texto.splitlines()[0]}"
                if ok and trecho and trecho not in texto:
                    ok = False
                    msg = f"recusado pelo MOTIVO ERRADO — esperava '{trecho}' na mensagem"
            except Exception as e:  # noqa: BLE001 — qualquer outra exceção é bug do parser
                ok, msg = False, f"EXCEÇÃO NÃO TRATADA ({type(e).__name__}: {e})"

            print(f"  {'ok  ' if ok else 'XXX '} {caso:<28} {msg}")
            if not ok:
                falhas.append(caso)

        # O caso válido também tem que atravessar a análise inteira sem estourar.
        print("\n  --- análise ponta a ponta sobre o caso válido ---")
        try:
            proj = carregar(tmp / "00-valido")
            texto = ro3_analise.relatorio([proj])
            grupos = ro3_analise.clusters(proj)
            n_dup = sum(1 for a in proj.achados if a.duplica)
            print(f"  ok   {len(proj.achados)} achados → {len(grupos)} defeitos distintos "
                  f"({n_dup} marcação(ões) `duplica`)")
            for exigido in ("Passo 1", "Passo 2", "Passo 3", "Passo 4", "Passo 5"):
                if exigido not in texto:
                    falhas.append(f"relatorio-sem-{exigido}")
                    print(f"  XXX  relatório não contém '{exigido}'")
            if "NENHUMA" not in texto and "dimensão faltante" not in texto:
                falhas.append("passo5-sem-canal-nenhuma")
                print("  XXX  Passo 5 não reportou o achado marcado NENHUMA")
        except Exception as e:  # noqa: BLE001
            falhas.append("analise-ponta-a-ponta")
            print(f"  XXX  análise estourou: {type(e).__name__}: {e}")

    print()
    if falhas:
        print(f"{len(falhas)} FALHA(S): {', '.join(falhas)}")
        return 1
    print(f"{len(esperado)} casos conforme o esperado — o formato falha alto em cada modo previsto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
