"""Cola operacional: criar entidade, emitir chave virtual e definir teto.

Nao e um modulo novo da arquitetura — e a interface de linha de comando das
operacoes ja declaradas em M-02 identidade (`emitir`) e M-08 persistencia
(`criar_entidade`, `definir_teto`). Sem isto o sistema nao pode ser exercitado
por uma pessoa, e o gate ui_runnable da Fase 5 seria impossivel.

  python admin.py criar-entidade equipe-busca "Equipe de Busca" --teto 5.00
  python admin.py emitir-chave equipe-busca
  python admin.py definir-teto global 50.00
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from t25.identidade import Identidade
from t25.janela import agora
from t25.persistencia import ENTIDADE, GLOBAL, Persistencia

BANCO = os.environ.get("T25_BANCO", str(Path(__file__).parent / "t25.db"))

NANO_POR_USD = 1_000_000_000


def main() -> int:
    p = argparse.ArgumentParser(description="administracao do gateway T25")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("criar-entidade")
    c.add_argument("id")
    c.add_argument("nome")
    c.add_argument("--teto", type=float, default=None, help="teto da entidade em USD")
    c.add_argument("--max-tokens", type=int, default=8192,
                   help="teto de max_tokens por requisicao (defesa GAM-01)")
    c.add_argument("--max-reservas", type=int, default=16,
                   help="reservas simultaneas por entidade (defesa GAM-03)")

    e = sub.add_parser("emitir-chave")
    e.add_argument("entidade_id")

    t = sub.add_parser("definir-teto")
    t.add_argument("alvo", help="'global' ou o id de uma entidade")
    t.add_argument("usd", type=float)

    args = p.parse_args()
    persistencia = Persistencia(BANCO)
    instante = agora()

    if args.cmd == "criar-entidade":
        persistencia.criar_entidade(
            args.id, args.nome, args.max_tokens, args.max_reservas, instante
        )
        if args.teto is not None:
            persistencia.definir_teto(
                ENTIDADE, args.id, round(args.teto * NANO_POR_USD), "admin", instante
            )
        print(f"entidade '{args.id}' criada (max_tokens={args.max_tokens}, "
              f"max_reservas={args.max_reservas})")

    elif args.cmd == "emitir-chave":
        chave = Identidade(persistencia).emitir(args.entidade_id)
        print("chave virtual (mostrada UMA unica vez, guarde agora):")
        print(chave)

    elif args.cmd == "definir-teto":
        escopo = GLOBAL if args.alvo == "global" else ENTIDADE
        alvo = "" if escopo == GLOBAL else args.alvo
        persistencia.definir_teto(
            escopo, alvo, round(args.usd * NANO_POR_USD), "admin", instante
        )
        print(f"teto {escopo} {alvo or '(global)'} = USD {args.usd:.2f}")

    persistencia.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
