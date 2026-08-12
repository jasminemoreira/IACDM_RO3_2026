"""M-12 cli — a superficie que a PESSOA opera.

Exit codes (achado UX-04 — sem eles a CLI e inutilizavel em script):
  0  sucesso, nada pendente
  1  erro de execucao
  2  sucesso, mas ha conflito aberto aguardando decisao
  3  provedor indisponivel na retomada de ciclo aberto (achado ASS-08/PRO-06)

A saida distingue BLOQUEADA-POR-CONFLITO de SUSPENSA-POR-OSCILACAO (achado
UX-08) e explica os quatro estados do conflito (achado UX-07).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .canonical_event import UTC
from .conflict_queue import OPEN, RESOLVED, explain_states, transition_resolve
from .overlap_detector import find_overlaps
from .providers import ProviderAlpha, ProviderBeta
from .recurrence import ExpansionWindow, build_calendar, expand, now_utc
from .repository import Repository
from .sync_engine import SyncEngine

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFLICTS_OPEN = 2
EXIT_PROVIDER_UNAVAILABLE = 3


def _workspace(args) -> tuple[Repository, ProviderAlpha, ProviderBeta]:
    root = Path(args.workspace)
    repo = Repository(root / "sync.db")
    return repo, ProviderAlpha(root / "alpha"), ProviderBeta(root / "beta")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(vazio)"
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(str(c))) for w, c in zip(widths, row)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "  ".join("-" * w for w in widths)
    body = "\n".join("  ".join(str(c).ljust(w) for c, w in zip(row, widths)) for row in rows)
    return f"{line}\n{sep}\n{body}"


def cmd_sync(args) -> int:
    repo, alpha, beta = _workspace(args)
    engine = SyncEngine(repo, alpha, beta)
    try:
        report = engine.run_cycle(
            policy=args.policy, dry_run=args.dry_run, priority_side=args.priority_side
        )
    except ConnectionError as exc:  # provedor indisponivel na retomada
        print(f"provedor indisponivel na retomada: {exc}", file=sys.stderr)
        return EXIT_PROVIDER_UNAVAILABLE

    modo = "PLANO (dry-run, nada aplicado)" if report.dry_run else "CICLO APLICADO"
    print(f"{modo}  politica={args.policy}  duracao={report.duration_s:.2f}s")
    if report.recovered_cycle:
        print(f"ciclo {report.recovered_cycle} estava aberto e foi reconciliado automaticamente")
    if report.full_resync:
        print(f"full resync forcado por token invalidado: {', '.join(report.full_resync)}")
    print(f"puxados: {report.pulled}  |  sem mudanca (no-op): {report.skipped_noop}")
    print(f"escritas aplicadas: {len(report.applied)}")
    for item in report.applied:
        print(f"  - {item}")
    if report.conflicts_opened:
        print(f"conflitos abertos nesta rodada: {len(report.conflicts_opened)}")
    if report.conflicts_applied:
        print(f"decisoes aplicadas: {len(report.conflicts_applied)}")
    if report.conflicts_stale:
        print(f"decisoes que viraram STALE: {len(report.conflicts_stale)}")
    if report.blocked_keys:
        print(f"BLOQUEADAS POR CONFLITO ({len(report.blocked_keys)}): nada sincroniza nelas ate voce decidir")
        for key in report.blocked_keys:
            print(f"  - {key}")
    if report.suspended_oscillating:
        print(f"SUSPENSAS POR OSCILACAO ({len(report.suspended_oscillating)}): propagacao parada, veja `conflicts list`")
        for key in report.suspended_oscillating:
            print(f"  - {key}")
    if report.suspended_unobservable:
        print(f"fora do escopo observavel de um provedor: {len(report.suspended_unobservable)} (nao e delecao)")

    return EXIT_CONFLICTS_OPEN if repo.list_conflicts(OPEN) else EXIT_OK


def cmd_status(args) -> int:
    repo, alpha, beta = _workspace(args)
    tokens = repo.load_tokens()
    ancestors = repo.load_all_ancestors()
    open_conflicts = repo.list_conflicts(OPEN)
    resolved = repo.list_conflicts(RESOLVED)
    cycles = repo.recent_cycles(1)
    print(f"workspace: {args.workspace}")
    print(f"esquema: v{repo.meta('schema_version')}  |  fingerprint: v{repo.meta('fingerprint_algo')}")
    print(f"eventos com ancestral: {len(ancestors)}")
    print("tokens de estado: " + ", ".join(
        f"{name}={'presente' if token else 'ausente (proximo ciclo e full sync)'}"
        for name, token in (tokens or {alpha.name: None, beta.name: None}).items()
    ))
    print(f"ultimo ciclo: {cycles[0]['opened_at'] if cycles else 'nenhum'}")
    print(f"ciclos abertos (interrompidos): {repo.open_cycles() or 'nenhum'}")
    print(f"conflitos OPEN: {len(open_conflicts)}  |  RESOLVED aguardando sync: {len(resolved)}")
    if open_conflicts:
        print("\nchaves bloqueadas:")
        for conflict in open_conflicts:
            print(f"  - {conflict.key}  [{conflict.klass}]  {conflict.id}")
    return EXIT_CONFLICTS_OPEN if open_conflicts else EXIT_OK


def cmd_conflicts_list(args) -> int:
    repo, _, _ = _workspace(args)
    conflicts = repo.list_conflicts(args.state)
    rows = [
        [c.id, str(c.key), c.klass, c.state, ",".join(c.fields) or "-", c.resolution or "-"]
        for c in conflicts
    ]
    print(_table(["id", "chave", "classe", "estado", "campos", "decisao"], rows))
    print("\nestados:")
    for name, meaning in explain_states():
        print(f"  {name:<9} {meaning}")
    return EXIT_CONFLICTS_OPEN if repo.list_conflicts(OPEN) else EXIT_OK


def cmd_conflicts_show(args) -> int:
    """Achado UX-02: decidir sem ver os tres valores e decidir as cegas."""
    repo, _, _ = _workspace(args)
    conflict = repo.get_conflict(args.id)
    if conflict is None:
        print(f"conflito {args.id} nao encontrado", file=sys.stderr)
        return EXIT_ERROR
    print(f"conflito {conflict.id}  chave={conflict.key}  classe={conflict.klass}  estado={conflict.state}")
    print(f"detectado em {conflict.detected_at}  sob politica '{conflict.policy_at_detection}'")
    if conflict.reason:
        print(f"motivo: {conflict.reason}")
    print(f"escolhas validas: {', '.join(conflict.choices())}")
    fields = conflict.fields or tuple(
        sorted(set((conflict.value_a.scalar_fields() if conflict.value_a else {}).keys()))
    )
    rows = []
    for name in fields:
        rows.append([
            name,
            _fmt(getattr(conflict.value_ancestor_a, name, None)),
            _fmt(getattr(conflict.value_a, name, None)),
            _fmt(getattr(conflict.value_b, name, None)),
        ])
    print(_table(["campo", "ancestral", "lado A", "lado B"], rows))
    return EXIT_OK


def _fmt(value) -> str:
    if value is None:
        return "-"
    text = str(getattr(value, "instant_utc", value))
    return text if len(text) <= 40 else text[:37] + "..."


def cmd_conflicts_resolve(args) -> int:
    repo, _, _ = _workspace(args)
    conflict = repo.get_conflict(args.id)
    if conflict is None:
        print(f"conflito {args.id} nao encontrado", file=sys.stderr)
        return EXIT_ERROR
    try:
        updated = transition_resolve(conflict, args.take, datetime.now().astimezone())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR
    repo.begin()
    repo.save_conflict(updated)
    repo.commit()
    # PRO-03: o handoff e explicito. Resolver NAO aplica.
    print(f"conflito {updated.id} marcado RESOLVED com '{args.take}'.")
    print("Nada foi aplicado ainda — rode `t28 sync` para aplicar a decisao.")
    return EXIT_OK


def cmd_overlaps(args) -> int:
    repo, alpha, beta = _workspace(args)
    if bool(args.since) != bool(args.until):
        print("--since e --until precisam vir juntos", file=sys.stderr)
        return EXIT_ERROR
    window = ExpansionWindow.default(now_utc()) if not args.since else ExpansionWindow(
        datetime.fromisoformat(args.since).astimezone(UTC),
        datetime.fromisoformat(args.until).astimezone(UTC),
    )
    occurrences = []
    for provider in (alpha, beta):
        resources = list(provider.all_resources().values())
        if not resources:
            continue
        calendar = build_calendar(resources)
        occurrences += expand(calendar, window, provider.name, provider.scenario.calendar_tz)
    overlaps = find_overlaps(occurrences)
    print(f"janela de expansao: {window.start.date()} .. {window.end.date()}")
    print(f"ocorrencias expandidas: {len(occurrences)}  |  sobreposicoes: {len(overlaps)}")
    rows = [
        [
            o.left.start_utc.strftime("%Y-%m-%d %H:%M"),
            f"{o.left.summary} [{o.left.origin}]",
            f"{o.right.summary} [{o.right.origin}]",
            f"{o.minutes} min",
        ]
        for o in overlaps
    ]
    print(_table(["inicio (UTC)", "evento", "sobrepoe", "interseccao"], rows))
    return EXIT_OK


def cmd_journal(args) -> int:
    repo, _, _ = _workspace(args)
    rows = []
    discarded: list[tuple[str, str]] = []
    for cycle in repo.recent_cycles(args.limit):
        for entry in repo.journal_of(cycle["id"]):
            if args.key and args.key not in str(entry.key):
                continue
            rows.append([
                str(cycle["id"]), cycle["opened_at"][:19], str(entry.key),
                entry.direction, entry.kind, entry.state, entry.version or "-",
            ])
            if args.show_values:
                value = repo.discarded_value(entry.id)
                if value:
                    discarded.append((str(entry.key), value))
    print(_table(["ciclo", "aberto em", "chave", "direcao", "tipo", "estado", "versao"], rows))
    if args.show_values:
        # SEC-07: conteudo de calendario so sai do banco sob pedido explicito.
        for key, value in discarded:
            print(f"\n--- valor descartado em {key} ---\n{value}")
        if not discarded:
            print("\n(nenhum valor descartado registrado nestes ciclos)")
    else:
        print("\n(valores omitidos; use --show-values para exibir conteudo de calendario)")
    return EXIT_OK


def cmd_maintenance(args) -> int:
    repo, _, _ = _workspace(args)
    if args.action == "recompute-fingerprints":
        from .normalizer import fingerprint

        moment = datetime.now().astimezone()
        count = 0
        repo.begin()
        for key, ancestor in repo.load_all_ancestors().items():
            side_a = ancestor.side_a
            side_b = ancestor.side_b
            new_a = side_a if side_a.snapshot is None else type(side_a)(
                side_a.snapshot, fingerprint(side_a.snapshot), side_a.provider_version, side_a.sequence
            )
            new_b = side_b if side_b.snapshot is None else type(side_b)(
                side_b.snapshot, fingerprint(side_b.snapshot), side_b.provider_version, side_b.sequence
            )
            repo.save_ancestor(type(ancestor)(key, new_a, new_b, ancestor.suspended), moment)
            count += 1
        repo.commit()
        print(f"fingerprints recalculados para {count} ancestrais")
        return EXIT_OK
    if args.action == "prune":
        repo.begin()
        removed = repo.prune(datetime.now().astimezone())
        repo.commit()
        print(f"ciclos removidos do journal: {removed}")
        return EXIT_OK
    print(f"acao desconhecida: {args.action}", file=sys.stderr)
    return EXIT_ERROR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="t28", description="Sincronizador bidirecional de calendarios com deteccao de conflito"
    )
    parser.add_argument("--workspace", "-w", default="workspace", help="diretorio do workspace")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="executa UM ciclo completo de sincronizacao")
    p_sync.add_argument("--policy", default="pol4", choices=["pol1", "pol2", "pol3", "pol4", "manual"])
    p_sync.add_argument(
        "--priority-side", default="a", choices=["a", "b"],
        help="lado autoritativo quando a politica for pol3 (prioridade de fonte)",
    )
    p_sync.add_argument("--dry-run", action="store_true", help="mostra o plano sem aplicar")
    p_sync.set_defaults(func=cmd_sync)

    sub.add_parser("status", help="estado do sincronizador").set_defaults(func=cmd_status)

    p_conf = sub.add_parser("conflicts", help="fila de conflitos")
    conf_sub = p_conf.add_subparsers(dest="sub", required=True)
    p_list = conf_sub.add_parser("list")
    p_list.add_argument("--state", choices=["OPEN", "RESOLVED", "APPLIED", "STALE"])
    p_list.set_defaults(func=cmd_conflicts_list)
    p_show = conf_sub.add_parser("show")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_conflicts_show)
    p_res = conf_sub.add_parser("resolve")
    p_res.add_argument("id")
    p_res.add_argument(
        "--take", required=True, choices=["a", "b", "merge", "resume"],
        help="'resume' so vale para suspensao por oscilacao: retoma a propagacao da chave",
    )
    p_res.set_defaults(func=cmd_conflicts_resolve)

    p_ov = sub.add_parser("overlaps", help="conflitos de AGENDA (sobreposicao temporal)")
    p_ov.add_argument("--since")
    p_ov.add_argument("--until")
    p_ov.set_defaults(func=cmd_overlaps)

    p_j = sub.add_parser("journal", help="historico de ciclos")
    p_j.add_argument("--limit", type=int, default=10)
    p_j.add_argument("--key")
    p_j.add_argument("--show-values", action="store_true")
    p_j.set_defaults(func=cmd_journal)

    p_m = sub.add_parser("maintenance")
    p_m.add_argument("action", choices=["recompute-fingerprints", "prune"])
    p_m.set_defaults(func=cmd_maintenance)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # erro de execucao: nunca silencioso
        print(f"erro: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
