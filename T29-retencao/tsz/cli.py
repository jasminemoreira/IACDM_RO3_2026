"""M-12 cli — adaptador de argparse. NENHUMA lógica de domínio.

Achado ARQ-01 de V(1): o `cli` dependia dos 11 outros módulos e detinha a execução do plano
de retenção. Em V(3) ele só faz parsing, formatação e tradução de erro para o operador.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import dataset_gen, retention, usecases
from .series import Point, SeriesError, TierSpec
from .store_port import OnReject

PROG = "tsz"


def _parse_tiers(text: str) -> list[TierSpec]:
    """`60:15d:average:0.5:0,300:90d:average:0.5:40h` — resolução:retenção:agg:xff:min_age."""
    out = []
    for part in text.split(","):
        fields = part.strip().split(":")
        if len(fields) < 2:
            raise SeriesError(
                f"tier {part!r} inválido; use resolução:retenção[:agregação[:xff[:min_age]]]"
            )
        out.append(
            TierSpec(
                seconds_per_point=_duration(fields[0]),
                retention_seconds=_duration(fields[1]),
                aggregation=fields[2] if len(fields) > 2 and fields[2] else "average",
                x_files_factor=float(fields[3]) if len(fields) > 3 and fields[3] else 0.5,
                min_age_seconds=_duration(fields[4]) if len(fields) > 4 and fields[4] else 0,
            )
        )
    return out


def _duration(text: str) -> int:
    """`60`, `5m`, `40h`, `15d`. Entrada malformada é erro de USUÁRIO, não traceback."""
    text = text.strip()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        if text and text[-1] in units:
            return int(float(text[:-1]) * units[text[-1]])
        return int(text)
    except ValueError:
        raise SeriesError(
            f"duração {text!r} inválida; use um número de segundos (60) ou um número "
            "com sufixo s/m/h/d (30s, 5m, 40h, 15d)"
        ) from None


def _read_points(path: str):
    """CSV de duas colunas `ts,valor`. `-` lê da entrada padrão.

    Entrada malformada produz erro de USUÁRIO com o número da linha — nunca um
    ValueError cru vindo de `int()`/`float()`.
    """
    if path == "-":
        stream = sys.stdin
    else:
        try:
            stream = open(path, "r", encoding="utf-8")
        except OSError as exc:
            raise SeriesError(f"não consegui ler {path!r}: {exc.strerror}") from None
    try:
        for lineno, raw in enumerate(stream, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.replace(";", ",").split(",")
            if len(parts) < 2:
                raise SeriesError(f"linha {lineno}: esperado 'ts,valor', li {raw!r}")
            try:
                ts, value = int(parts[0]), float(parts[1])
            except ValueError:
                raise SeriesError(
                    f"linha {lineno}: 'ts,valor' precisa ser um inteiro e um número, "
                    f"li {parts[0]!r} e {parts[1]!r}"
                ) from None
            yield Point(ts, value)
    finally:
        if stream is not sys.stdin:
            stream.close()


def _emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Compactador de séries temporais: codec Gorilla, retenção multi-tier por "
            "downsampling e migração entre formatos de armazenamento."
        ),
        epilog=(
            "NOTA: `retain` é um comando, não um processo. Nada envelhece sozinho — "
            "agende-o externamente (cron). Premissa declarada ASM-06."
        ),
    )
    p.add_argument("--base", default=".", help="diretório onde os acervos vivem")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="cria um acervo")
    c.add_argument("series")
    c.add_argument("--format", choices=["f1", "f2"], default="f2")
    c.add_argument(
        "--tiers",
        default=None,
        help="resolução:retenção[:agg[:xff[:min_age]]], separados por vírgula. "
        "Default: cru 60s/15d, 5m/90d (min_age 40h), 1h/730d (min_age 10d)",
    )

    i = sub.add_parser("ingest", help="UC-1: ingere e comprime")
    i.add_argument("series")
    i.add_argument("--input", default="-", help="CSV 'ts,valor' ou - para stdin")
    i.add_argument("--tier", type=int, default=0)
    i.add_argument(
        "--on-reject",
        choices=[OnReject.ABORT, OnReject.SKIP],
        default=OnReject.ABORT,
        help="abort (default): falha se algum ponto for rejeitado",
    )

    r = sub.add_parser("read", help="UC-2: lê um intervalo semiaberto [from, to)")
    r.add_argument("series")
    r.add_argument("--tier", type=int, default=0)
    r.add_argument("--from", dest="t_from", type=int, required=True)
    r.add_argument("--to", dest="t_to", type=int, required=True)

    t = sub.add_parser("retain", help="UC-3: aplica a política de retenção")
    t.add_argument("series")
    t.add_argument("--now", type=int, default=None, help="para reproduzir um plano previsto")
    t.add_argument("--dry-run", action="store_true", help="imprime o plano sem executar")

    m = sub.add_parser("migrate", help="UC-4: migra o acervo para outro formato")
    m.add_argument("series")
    m.add_argument("--to-format", choices=["f1", "f2"], required=True)
    m.add_argument(
        "--to",
        dest="to_path",
        default=None,
        help="caminho do acervo de destino; default: acervo-<serie>-<src>2<dst>",
    )
    m.add_argument("--allow-lossy", action="store_true", help="consente perda explicitamente")
    m.add_argument("--no-verify", action="store_true")
    m.add_argument("--dry-run", action="store_true")

    v = sub.add_parser("validate-config", help="UC-5: valida uma configuração de tiers")
    v.add_argument("--tiers", required=True)

    rep = sub.add_parser("report", help="UC-6: mede a razão de compressão por perfil")
    rep.add_argument("--profiles", default=None, help="lista separada por vírgula")
    rep.add_argument("--n", type=int, default=7200)
    rep.add_argument("--seed", type=int, default=7)

    n = sub.add_parser("info", help="estado do acervo: tiers, pontos, bytes por tier")
    n.add_argument("series")
    n.add_argument("--history", action="store_true", help="inclui a trilha do journal")

    g = sub.add_parser("gen-dataset", help="gera um perfil de ground truth")
    g.add_argument("profile", choices=list(dataset_gen.PROFILES))
    g.add_argument("--n", type=int, default=7200)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--step", type=int, default=60)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    base = Path(args.base)
    try:
        if args.cmd == "create":
            tiers = _parse_tiers(args.tiers) if args.tiers else retention.default_tiers()
            _emit(usecases.create(base, args.series, args.format, tiers))

        elif args.cmd == "ingest":
            root = _root(base, args.series)
            _emit(
                usecases.ingest(
                    root, _read_points(args.input), args.tier, args.on_reject
                )
            )

        elif args.cmd == "read":
            root = _root(base, args.series)
            for p in usecases.read(root, args.tier, args.t_from, args.t_to):
                print(f"{p.ts},{p.value!r}")

        elif args.cmd == "retain":
            root = _root(base, args.series)
            result = usecases.retain(root, args.now, args.dry_run)
            _emit(result)
            if args.dry_run:
                # UX-06: o preview diz QUAL `now` usou, para poder ser reproduzido.
                print(
                    f"\n# plano calculado com now={result['now_used']}; "
                    f"reproduza com: {PROG} retain {args.series} "
                    f"--now {result['now_used']}",
                    file=sys.stderr,
                )

        elif args.cmd == "migrate":
            root = _root(base, args.series)
            _emit(
                usecases.migrate(
                    root,
                    base,
                    args.to_format,
                    allow_lossy=args.allow_lossy,
                    verify=not args.no_verify,
                    dry_run=args.dry_run,
                    dst_root=Path(args.to_path) if args.to_path else None,
                )
            )

        elif args.cmd == "validate-config":
            _emit(usecases.validate_config(_parse_tiers(args.tiers)))

        elif args.cmd == "report":
            profiles = args.profiles.split(",") if args.profiles else None
            _emit(usecases.report(profiles, args.n, args.seed))

        elif args.cmd == "info":
            _emit(usecases.info(_root(base, args.series), args.history))

        elif args.cmd == "gen-dataset":
            for p in dataset_gen.generate(args.profile, args.n, args.seed, args.step):
                print(f"{p.ts},{p.value!r}")

    except SeriesError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    except OSError as exc:
        # Rede de segurança: um erro de sistema de arquivos é problema do operador
        # (permissão, disco cheio, caminho errado), não um defeito do programa. Um
        # traceback aqui diria 'quebrei' quando a verdade é 'não consegui'.
        print(f"{PROG}: erro de sistema de arquivos: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        # Rede de segurança contra entrada malformada que escape dos parsers acima.
        print(f"{PROG}: entrada inválida: {exc}", file=sys.stderr)
        return 2
    return 0


def _root(base: Path, series: str) -> Path:
    from .store_port import acervo_path

    return acervo_path(base, series)


if __name__ == "__main__":
    sys.exit(main())
