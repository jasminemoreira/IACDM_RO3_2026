# Modelos de dado — V(3)

Os tipos que atravessam interfaces, no formato em que a Fase 5 vai codificá-los. Fonte:
`specs/technical/architecture.md` §V(3). Só três tipos de domínio — `TierState` foi deletado em
V(3) porque a marca d'água é derivada do dado.

---

## Tipos de domínio (módulo `series`)

```python
@dataclass(frozen=True)
class Point:
    ts: int        # segundos Unix; estritamente crescente na série (I2)
    value: float   # IEEE-754 binary64; -0.0, NaN com payload e subnormais são PRESERVADOS

@dataclass(frozen=True)
class TierSpec:
    seconds_per_point: int    # resolução. 60 no cru por default
    retention_seconds: int    # janela; contada de floor(now)
    aggregation: str          # um de AGGREGATIONS (R6): average|sum|last|max|min
    x_files_factor: float     # [0.0, 1.0]; 0.5 default (R6/R7)
    min_age_seconds: int      # idade mínima para derivar. R9 cita 40h (5m) e 10d (1h)

@dataclass(frozen=True)
class ArchiveMeta:
    format_version: int       # recusar leitura se > a versão do escritor
    format: str               # "f1" | "f2"
    block_seconds: int        # 7200; validado <= 14400 NA CARGA (MEC-06)
    created_at: int
    writer_version: str
    series_name: str          # ^[A-Za-z0-9._-]+$ (SEC-01)
    tiers: list[TierSpec]
    superseded_by: str | None # preenchido por migrate na ORIGEM (MIG-04)
```

**Não existe `TierState`.** `derived_through_ts(tier)` é calculado:

| Formato | Cálculo |
|---|---|
| F2 | `max(base_ts dos arquivos de chunk do tier) + block_seconds` |
| F1 | timestamp do slot válido mais recente (validade = ts gravado == ts esperado da posição) |

## Relatórios (módulo `store-port`)

```python
@dataclass(frozen=True)
class Capabilities:
    mutable_slots: bool
    min_ts: int                    # F1: 0        | F2: -2**63
    max_ts: int                    # F1: 2**32-1  | F2: 2**63-1
    aligned_writes_required: bool   # F1: True     | F2: False

@dataclass(frozen=True)
class WriteReport:
    written: int
    rejected: int
    reasons: dict[str, int]   # motivo -> contagem: "unaligned"|"duplicate"|"out_of_range"|"late"
    bytes_written: int        # necessário para CA-4 (REG-02)

@dataclass(frozen=True)
class ExpireReport:
    points_removed: int
    blocks_removed: int
    effective_before_ts: int  # É a invariante I5: a fronteira REAL do descarte

@dataclass(frozen=True)
class LossRisk:
    kind: str                 # "ts_out_of_range" | "alignment_required" | "slot_collision"
    detail: str
    affected: int             # contado contra OS DADOS, não contra a flag (MIG-02)
```

## Plano de retenção (módulo `retention`)

```python
@dataclass(frozen=True)
class RetentionPlan:
    derive: list[tuple[int, int, int, int]]  # (tier_src, tier_dst, t_from, t_to) semiaberto
    expire: list[tuple[int, int]]            # (tier, before_ts)
    now_used: int                            # impresso pelo --dry-run (UX-06)
```

## Layout do acervo em disco (E1/E2 de V(3))

```
acervo-<serie>/
├── meta.json                    # ArchiveMeta, uma escrita atômica = o commit
├── journal.jsonl                # uma linha por comando; op de conjunto fechado
├── tier-0/                      # F2: um arquivo por bloco, nome = base_ts
│   ├── 1786464000.chunk
│   └── 1786471200.chunk
└── tier-1/
    └── 1786464000.chunk
```

Em F1, `tier-N/` contém **um** arquivo de slots fixos, byte-exato a R6.

## Linha do journal (módulo `journal`)

JSON Lines. `op` **de conjunto fechado** — `ingest | retain | migrate | expire` (LIN-09).
`json.dumps` escapa quebras de linha, o que elimina injeção de linha falsa (SEC-06).

```json
{"at": 1786470000, "op": "retain", "series": "cpu.load", "writer": "0.1.0",
 "report": {"derived": 12, "expired": 3, "now_used": 1786470000}}
```

## Invariantes por tipo (rastreabilidade para a Fase 6)

| Invariante | Onde é imposta |
|---|---|
| I1 lossless | `gorilla-codec` (round-trip bit a bit) |
| I2 timestamps crescentes | `series.validate_stream`, chamado pelo caminho de escrita de `store-port` |
| I3 divisibilidade entre tiers | `retention.validate` |
| I4 downsampling irreversível | `usecases` (documentado; recomputar exige apagar o chunk) |
| I5 retenção efetiva ≥ nominal | `ExpireReport.effective_before_ts` |
| I6 `xFilesFactor` | `downsampler` (contra a contagem nominal do tier de origem imediato) |
| I7 retenção vs idade de downsample | `retention.validate`, por par adjacente |
