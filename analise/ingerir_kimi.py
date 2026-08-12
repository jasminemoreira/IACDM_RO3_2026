"""Ingere respostas do Kimi coladas em texto — um ou vários JSONs de uma vez.

    python3 ingerir_kimi.py <arquivo-com-as-respostas.txt>

Extrai cada objeto JSON de nível superior do texto (tolera cercas de código e prosa
em volta), valida contra as mesmas regras do caminho por API, e salva em
`cego/<taskId>-predicao-kimi-r<N>.json`.

Validação idêntica à do `rodar_predicao_kimi.py` de propósito: uma resposta colada à
mão não pode entrar sob critério mais frouxo do que uma vinda por API, ou o preditor
"Kimi" passa a significar duas coisas diferentes conforme o caminho.

Nada parcial é gravado: resposta inválida é reportada e descartada. Se o Kimi errou,
isso é dado sobre o preditor — não se corrige pedindo de novo.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from predicao_cega import LENTES  # noqa: E402
from preparar import PROJETOS  # noqa: E402
from rodar_predicao_kimi import _validar  # noqa: E402

SAIDA = Path(__file__).resolve().parent / "cego"
TASK_IDS = {t for t, _, _ in PROJETOS}
NOMES = [n for n, _, _ in LENTES]


def extrair(texto: str) -> list[dict]:
    """Objetos JSON de nível superior, por contagem de chaves fora de string."""
    achados, prof, ini, em_str, escape = [], 0, None, False, False
    for i, ch in enumerate(texto):
        if em_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                em_str = False
            continue
        if ch == '"':
            em_str = True
        elif ch == "{":
            if prof == 0:
                ini = i
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0 and ini is not None:
                try:
                    achados.append(json.loads(texto[ini:i + 1]))
                except json.JSONDecodeError:
                    pass
                ini = None
    return achados


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    texto = Path(argv[0]).read_text(encoding="utf-8")
    objetos = extrair(texto)
    if not objetos:
        print("Nenhum objeto JSON encontrado no texto.", file=sys.stderr)
        return 1

    SAIDA.mkdir(exist_ok=True)
    ok, ruins = [], []
    for obj in objetos:
        task_id = obj.get("projeto")
        if task_id not in TASK_IDS:
            ruins.append((task_id or "<sem campo projeto>", "não é um taskId do lote"))
            continue
        problemas = _validar(obj)
        if problemas:
            ruins.append((task_id, "; ".join(problemas)))
            continue
        # Uma resposta colada duas vezes NÃO é uma segunda rodada. Salvá-la como r2
        # faria o agregador contar dois julgamentos concordantes e reportar
        # estabilidade fabricada — a medida de oscilação vive exatamente disso.
        assinatura = hashlib.sha256(
            json.dumps([(l["lente"], l["ativa"], l["sinal"]) for l in obj["lentes"]],
                       ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        repetida = None
        for anterior in sorted(SAIDA.glob(f"{task_id}-predicao-kimi-r*.json")):
            velho = json.loads(anterior.read_text(encoding="utf-8"))
            outra = hashlib.sha256(
                json.dumps([(l["lente"], l["ativa"], l["sinal"]) for l in velho["lentes"]],
                           ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            if outra == assinatura:
                repetida = anterior.name
                break
        if repetida:
            ruins.append((task_id, f"idêntica a {repetida} — mesma resposta colada de novo, "
                                   f"não uma segunda rodada. Não gravada."))
            continue

        n = 1
        while (SAIDA / f"{task_id}-predicao-kimi-r{n}.json").exists():
            n += 1
        (SAIDA / f"{task_id}-predicao-kimi-r{n}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        ativas = sorted(l["lente"] for l in obj["lentes"] if l["ativa"])
        ok.append((task_id, n, len(ativas), obj["modulos_estimados"]))

    for task_id, n, n_ativas, mods in ok:
        print(f"  ok   {task_id:<18} r{n}  {n_ativas}/12 ativas, {mods} módulos")
    for task_id, motivo in ruins:
        print(f"  XXX  {task_id:<18} {motivo}")

    faltam = sorted(TASK_IDS - {p.name.split("-predicao")[0] for p in SAIDA.glob("*-predicao-kimi-r*.json")})
    print(f"\n{len(ok)} salvo(s), {len(ruins)} recusado(s).")
    print(f"faltam {len(faltam)}: {', '.join(faltam) if faltam else '—'}")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
