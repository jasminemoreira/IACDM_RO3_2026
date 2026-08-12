"""M-11 usecases — os Transaction Scripts dos casos de uso UC-1..UC-6.

Saíram do `cli` porque lógica de domínio não pertence a um adaptador (achados ARQ-01,
ARQ-02, IMP-05). Aqui vive a ORDEM OBRIGATÓRIA de operações do `retain`.

ARQ-07 (este módulo tem fan-in alto) foi ACEITO com justificativa: fan-in alto é a
definição de uma camada de Transaction Script. "Corrigir" isso inventando outra camada
seria o AP2 que a própria análise de concentração da rodada 2 flagrou.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import dataset_gen, downsampler, journal, retention
from .gorilla_codec import Chunk
from .series import (
    ArchiveMeta,
    Point,
    RetentionPlan,
    SeriesError,
    TierSpec,
    is_aligned,
)
from .store_f1 import StoreF1
from .store_f2 import StoreF2
from .store_port import (
    OnReject,
    acervo_path,
    check_compatibility,
    read_meta,
    write_meta,
)

WRITER_VERSION = "0.1.0"


def _now() -> int:
    return int(time.time())


def open_store(root: Path):
    meta = read_meta(Path(root))
    return _store_for(Path(root), meta)


def _store_for(root: Path, meta: ArchiveMeta):
    return StoreF1(root, meta) if meta.fmt == "f1" else StoreF2(root, meta)


# --- UC: criar acervo -------------------------------------------------------------------


def create(base: Path, series_name: str, fmt: str, tiers: list[TierSpec], now: int | None = None) -> dict:
    now = _now() if now is None else now
    retention.validate(tiers)
    root = acervo_path(base, series_name)
    if (root / "meta.json").exists():
        raise SeriesError(f"{root} já existe; recrie apagando o diretório")
    meta = ArchiveMeta(
        series_name=series_name,
        fmt=fmt,
        tiers=tiers,
        created_at=now,
        writer_version=WRITER_VERSION,
    )
    root.mkdir(parents=True, exist_ok=True)
    store = _store_for(root, meta)
    store.create()
    write_meta(root, meta)
    report = {"acervo": str(root), "format": fmt, "tiers": len(tiers)}
    journal.append(root, "create", now, report)
    return report


# --- UC-1: ingerir e comprimir ----------------------------------------------------------


def ingest(
    root: Path,
    points,
    tier: int = 0,
    on_reject: str = OnReject.ABORT,
    now: int | None = None,
) -> dict:
    now = _now() if now is None else now
    root = Path(root)
    store = open_store(root)
    spec = store.meta.tiers[tier]

    # ASM-10/PRC-05: ponto atrasado é rejeitado com motivo, nunca corrigido em silêncio.
    watermark = store.derived_through(tier)
    accepted: list[Point] = []
    late = 0
    for p in points:
        if watermark is not None and p.ts <= watermark:
            late += 1
            continue
        accepted.append(p)

    report = store.write(tier, accepted)
    if late:
        report.reject("late", late)

    if report.rejected and on_reject == OnReject.ABORT:
        # UX-07: o operador decide ANTES de metade estar dentro. O que já foi escrito
        # permanece — dizemos exatamente isso, em vez de fingir transação.
        raise SeriesError(
            f"{report.rejected} ponto(s) rejeitado(s) ({report.reasons}); "
            f"{report.written} já gravado(s). Use --on-reject=skip para prosseguir "
            f"ignorando os rejeitados"
        )

    out = report.as_dict() | {"tier": tier, "series": store.meta.series_name}
    journal.append(root, "ingest", now, out)
    return out


# --- UC-2: ler intervalo ----------------------------------------------------------------


def read(root: Path, tier: int, t_from: int, t_to: int):
    """SEMIABERTO [t_from, t_to). Não escreve nada, logo não vai para o journal."""
    return open_store(Path(root)).read(tier, t_from, t_to)


# --- UC-5: validar configuração ---------------------------------------------------------


def validate_config(tiers: list[TierSpec]) -> dict:
    """UX-03: caminho ÚNICO de validação — `retain` chama exatamente esta função."""
    retention.validate(tiers)
    return {
        "tiers": [t.as_dict() for t in tiers],
        "ok": True,
        "divisibility": [
            f"{tiers[i].seconds_per_point}s -> {tiers[i + 1].seconds_per_point}s "
            f"({tiers[i + 1].seconds_per_point // tiers[i].seconds_per_point}x)"
            for i in range(len(tiers) - 1)
        ],
    }


# --- UC-3: aplicar retenção -------------------------------------------------------------


def plan_for(root: Path, now: int | None = None) -> tuple[RetentionPlan, object]:
    now = _now() if now is None else now
    store = open_store(Path(root))
    watermarks = {i: store.derived_through(i) for i in range(len(store.meta.tiers))}
    return retention.plan(store.meta.tiers, watermarks, now), store


def retain(root: Path, now: int | None = None, dry_run: bool = False) -> dict:
    """ORDEM OBRIGATÓRIA (achados RES-05/PRC-02, e RES-06 resolvido por E3):

        derivar → gravar → VERIFICAR → expirar

    Expirar só depois de o agregado estar gravado E verificado. Não há marca d'água a
    avançar: ela é derivada do próprio dado gravado, logo não existe janela entre duas
    escritas onde o estado possa ficar inconsistente.
    """
    now = _now() if now is None else now
    root = Path(root)
    plan, store = plan_for(root, now)

    result: dict = {
        "now_used": plan.now_used,
        "dry_run": dry_run,
        "derive": [],
        "expire": [],
    }

    for src, dst, t_from, t_to in plan.derive:
        src_spec = store.meta.tiers[src]
        dst_spec = store.meta.tiers[dst]
        step = {
            "src": src,
            "dst": dst,
            "from": t_from,
            "to": t_to,
            "aggregation": dst_spec.aggregation,
        }
        if dry_run:
            result["derive"].append(step | {"written": None})
            continue

        derived = list(
            downsampler.aggregate(
                store.read(src, t_from, t_to),
                src_spec.seconds_per_point,
                dst_spec.seconds_per_point,
                dst_spec.aggregation,
                dst_spec.x_files_factor,
            )
        )
        if not derived:
            result["derive"].append(step | {"written": 0})
            continue

        report = store.write(dst, derived)

        # VERIFICAR (achado IMP-07: o passo era decorativo por não ter critério).
        # Relê pela porta e compara ponto a ponto — é o mesmo critério de CA-2.
        back = {p.ts: p for p in store.read(dst, t_from, t_to)}
        missing = [p.ts for p in derived if p.ts not in back]
        wrong = [
            p.ts
            for p in derived
            if p.ts in back and not p.same_value_bits(back[p.ts])
        ]
        if missing or wrong:
            raise SeriesError(
                f"verificação falhou ao derivar tier {src}->{dst}: "
                f"{len(missing)} ausente(s), {len(wrong)} divergente(s). "
                f"NADA foi expirado"
            )
        result["derive"].append(step | report.as_dict())

    for tier, before in plan.expire:
        if dry_run:
            result["expire"].append({"tier": tier, "before_ts": before, "removed": None})
            continue
        rep = store.expire(tier, before)
        result["expire"].append({"tier": tier, "before_ts": before} | rep.as_dict())

    if not dry_run:
        journal.append(root, "retain", now, result)
    return result


# --- UC-4: migrar formato ---------------------------------------------------------------


def migrate(
    src_root: Path,
    dst_base: Path,
    dst_fmt: str,
    allow_lossy: bool = False,
    verify: bool = True,
    dry_run: bool = False,
    now: int | None = None,
    dst_root: Path | None = None,
) -> dict:
    """A migração NUNCA remove a origem (achado MIG-01): o rollback é a origem continuar lá.

    E também não sobrescreve o DESTINO: se ele já for um acervo, recusa. Destruir o destino
    seria a mesma classe de dano de MIG-01, pelo outro lado.

    `precheck` compara capacidades CONTRA OS DADOS (achado MIG-02), não contra uma flag.
    """
    now = _now() if now is None else now
    src_root = Path(src_root)
    src = open_store(src_root)
    if src.meta.fmt == dst_fmt:
        raise SeriesError(f"origem e destino são ambos {dst_fmt}: nada a migrar")

    if dst_root is None:
        # Inclui os DOIS formatos para que uma cadeia de migrações seja distinguível.
        dst_root = acervo_path(
            dst_base, f"{src.meta.series_name}-{src.meta.fmt}2{dst_fmt}"
        )
    dst_root = Path(dst_root)
    if (dst_root / "meta.json").exists():
        raise SeriesError(
            f"o destino {dst_root} já é um acervo: migrar para dentro dele misturaria "
            f"dados de dois acervos. Apague-o ou escolha outro destino com --to"
        )
    dst_meta = ArchiveMeta(
        series_name=src.meta.series_name,
        fmt=dst_fmt,
        tiers=list(src.meta.tiers),
        block_seconds=src.meta.block_seconds,
        created_at=now,
        writer_version=WRITER_VERSION,
    )
    dst = _store_for(dst_root, dst_meta)

    # Precheck ciente dos dados: varre a origem medindo o que de fato existe.
    risks = []
    per_tier: list[dict] = []
    for tier, spec in enumerate(src.meta.tiers):
        pts = list(src.read(tier, -(2**62), 2**62))
        unaligned = sum(1 for p in pts if not is_aligned(p.ts, spec.seconds_per_point))
        per_tier.append(
            {
                "tier": tier,
                "points": len(pts),
                "min_ts": min((p.ts for p in pts), default=None),
                "max_ts": max((p.ts for p in pts), default=None),
                "unaligned": unaligned,
            }
        )
        risks.extend(
            check_compatibility(
                src.capabilities(),
                dst.capabilities(),
                src.meta.tiers,
                per_tier[-1]["min_ts"],
                per_tier[-1]["max_ts"],
                unaligned,
            )
        )

    result: dict = {
        "src": str(src_root),
        "dst": str(dst_root),
        "src_format": src.meta.fmt,
        "dst_format": dst_fmt,
        "tiers": per_tier,
        "risks": [r.__dict__ for r in risks],
        "dry_run": dry_run,
        "lossless": not risks,
    }

    if risks and not allow_lossy:
        detail = "; ".join(f"{r.kind}: {r.detail}" for r in risks)
        raise SeriesError(
            f"migração abortada ANTES de escrever qualquer byte — o destino não "
            f"representa todo o dado da origem: {detail}. "
            f"Use --allow-lossy para prosseguir com perda consentida"
        )
    if dry_run:
        return result

    dst_root.mkdir(parents=True, exist_ok=True)
    dst.create()
    write_meta(dst_root, dst_meta)

    total_written = 0
    total_rejected = 0
    for tier in range(len(src.meta.tiers)):
        rep = dst.write(tier, src.read(tier, -(2**62), 2**62))
        total_written += rep.written
        total_rejected += rep.rejected
    result["written"] = total_written
    result["rejected"] = total_rejected

    if verify:
        # REG-03: CA-2 exige comparação ponto a ponto, não de contagens.
        for tier, spec in enumerate(src.meta.tiers):
            a = list(src.read(tier, -(2**62), 2**62))
            b = {p.ts: p for p in dst.read(tier, -(2**62), 2**62)}
            lost = [p.ts for p in a if p.ts not in b]
            differ = [p.ts for p in a if p.ts in b and not p.same_value_bits(b[p.ts])]
            if (lost or differ) and not allow_lossy:
                raise SeriesError(
                    f"verificação falhou no tier {tier}: {len(lost)} ponto(s) "
                    f"perdido(s), {len(differ)} divergente(s). A ORIGEM ESTÁ INTACTA"
                )
            result.setdefault("verify", []).append(
                {"tier": tier, "lost": len(lost), "differ": len(differ)}
            )
        result["lossless"] = all(
            v["lost"] == 0 and v["differ"] == 0 for v in result["verify"]
        )

    # MIG-04: marca a origem como superada, para não haver dois acervos "vigentes".
    src.meta.superseded_by = str(dst_root)
    write_meta(src_root, src.meta)

    # GOV-05: registra nos DOIS journals — se registrasse só num, metade da história
    # desapareceria exatamente na operação que move o acervo.
    journal.append(src_root, "migrate", now, result)
    journal.append(dst_root, "migrate", now, result)
    return result


# --- UC-6: medir e reportar -------------------------------------------------------------


def report(profiles=None, n: int = 7200, seed: int = 7, block_seconds: int = 7200) -> dict:
    """CA-4: razão MEDIDA e reportada por perfil, sem limiar prometido."""
    profiles = list(profiles or dataset_gen.PROFILES)
    rows = []
    for profile in profiles:
        pts = list(dataset_gen.generate(profile, n, seed, step=1))
        base = Chunk.window_of(pts[0].ts, block_seconds)
        chunk = Chunk(base, block_seconds)
        used = 0
        for p in pts:
            if not chunk.contains(p.ts):
                break
            chunk.append(p.ts, p.value)
            used += 1
        _, nbits = chunk.payload()
        bpp = nbits / 8 / used
        rows.append(
            {
                "profile": profile,
                "points": used,
                "bytes_per_point": round(bpp, 3),
                "ratio_vs_16b": round(16 / bpp, 1),
                "description": dataset_gen.describe(profile),
            }
        )
    return {"n": n, "seed": seed, "rows": rows}


def info(root: Path, history: bool = False) -> dict:
    """OBS-02/SUS-01: o que tem neste acervo, e quanto cada tier custa."""
    root = Path(root)
    store = open_store(root)
    tiers = []
    for i, spec in enumerate(store.meta.tiers):
        pts = list(store.read(i, -(2**62), 2**62))
        tiers.append(
            {
                "tier": i,
                "seconds_per_point": spec.seconds_per_point,
                "retention_seconds": spec.retention_seconds,
                "aggregation": spec.aggregation,
                "points": len(pts),
                "first_ts": min((p.ts for p in pts), default=None),
                "last_ts": max((p.ts for p in pts), default=None),
                "derived_through": store.derived_through(i),
                "bytes": store.size_bytes(i),
                "bytes_per_point": (
                    round(store.size_bytes(i) / len(pts), 3) if pts else None
                ),
            }
        )
    out = {
        "acervo": str(root),
        "series": store.meta.series_name,
        "format": store.meta.fmt,
        "format_version": store.meta.format_version,
        "block_seconds": store.meta.block_seconds,
        "superseded_by": store.meta.superseded_by,
        "journal_bytes": journal.size_bytes(root),
        "tiers": tiers,
    }
    if isinstance(store, StoreF2):
        out["integrity"] = {
            f"tier-{i}": store.verify(i) or "ok" for i in range(len(store.meta.tiers))
        }
    if history:
        out["history"] = list(journal.read(root))
    return out
