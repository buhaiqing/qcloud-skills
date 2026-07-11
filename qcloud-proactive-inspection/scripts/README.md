# qcloud-proactive-inspection — scripts

Two-phase pipeline that powers the SKILL's `Discovery → Collection → Detection → Diagnosis → Report` workflow. All scripts load `TENCENTCLOUD_*` / `COPILOT_*` from the repo-root `.env` via `scripts/lib/env_loader.py` (priority: shell env > file > default).

## Layout

```
scripts/
├── lib/
│   ├── env_loader.py        # load .env (shell env wins via setdefault)
│   ├── tccli_client.py      # Cloud Monitor + tccli wrapper (GetMonitorData)
│   ├── tags.py              # tag read helpers
│   └── normalize.py         # PascalCase → camelCase + tag flattening
├── 01-perceive/
│   └── cruise_sniff.py      # Phase 1: cross-product topology discovery
├── 02-reason/
│   ├── cruise_analyze.py    # Phase 2: orchestrator (selective deep pass)
│   └── analyzers/           # 11 product analyzers (read-only; delegate mutation)
│       ├── vm_analyzer.py
│       ├── clb_analyzer.py
│       ├── eip_analyzer.py
│       ├── redis_analyzer.py
│       ├── rds_mysql_analyzer.py
│       ├── rds_postgresql_analyzer.py
│       ├── mongodb_analyzer.py
│       ├── es_analyzer.py
│       ├── nat_analyzer.py
│       ├── k8s_analyzer.py
│       └── sg_analyzer.py
├── test_env_loader.py       # pytest: env precedence + prefix filter
└── test_selective_analyzers.py  # pytest: analyzer registry / selective flow
```

## Prerequisites

```bash
# 1. Credentials
cp ../../.env.example ../../.env
# edit TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY / TENCENTCLOUD_REGION

# 2. tccli
pip install tccli            # primary path; SDK fallback for batch metrics
```

`tccli` is **not** required when running with `--mock` (selective analyzers can be exercised offline with synthetic data).

## Phase 1 — Sniff (`01-perceive/cruise_sniff.py`)

Walk a region, list resources in each product, and filter by a customer tag. Output is a topology JSON written to `.runtime/proactive-inspection/`.

```bash
python3 scripts/01-perceive/cruise_sniff.py \
    --region ap-guangzhou \
    --customer 客户A \
    --tag-key 客户 \
    --output .runtime/proactive-inspection
```

| Flag | Default | Notes |
|------|---------|-------|
| `--region` | `ap-guangzhou` | single region per run; loop shell-side for multi-region |
| `--customer` | required | tag value to match |
| `--tag-key` | `客户` | tag key on resources |
| `--output` | `.runtime/proactive-inspection` | directory for the per-run snapshot |

Sniffed products (driven by tccli `Describe*`):

`cvm` · `clb` · `vpc` · `redis` (TencentDB for Redis) · `cdb` (MySQL) · `postgres` · `mongodb` · `es` (Elasticsearch Service) · `eip` · `nat`

Internal `ALL_REGIONS = ["ap-guangzhou", "ap-shanghai", "ap-beijing", "ap-nanjing", "ap-chengdu"]` is exported for batch loops.

## Phase 2 — Analyze (`02-reason/cruise_analyze.py`)

Read the snapshot from Phase 1, collect metrics via `TccliClient`, run the registered analyzers, emit findings. Analyzers run only for products present in the topology (selective):

```bash
python3 scripts/02-reason/cruise_analyze.py \
    --sniff-file .runtime/proactive-inspection/cruise-客户A-<ts>.json \
    --hours 6 \
    --json
```

| Flag | Default | Notes |
|------|---------|-------|
| `--sniff-file` | from `--customer`+`.runtime` | path returned by Phase 1 |
| `--hours` | `6` | metric window (Cloud Monitor `Period`) |
| `--analyzers` | auto-detect from topology | CSV of analyzer names |
| `--resource-ids` | all in topology | narrow a run to specific IDs |
| `--strategy-file` | none | LLM strategy JSON (drives `--analyzers` when present) |
| `--json` | off | machine-readable output |

### Selective Analyzers

`create_by_names(...)` reads the registered analyzer catalog and instantiates only those with matching resources. Each analyzer's `discover()`, `query_metrics()`, and `analyze()` are independent; every analyzer is **read-only** — mutations are routed via the `ops_skill` field on each finding (e.g. `qcloud-cvm-ops`).

Available analyzer names (use as `--analyzers vm,redis,...`):

`vm` · `clb` · `eip` · `redis` · `rds_mysql` · `rds_postgresql` · `mongodb` · `es` · `nat` · `k8s` · `sg`

## Tests

```bash
cd scripts
python3 -m pytest -q
```

Two suites:

- `test_env_loader.py` — repo-root `.env` loading + shell-env precedence + `TENCENTCLOUD_/COPILOT_` prefix filter
- `test_selective_analyzers.py` — analyzer registry + selective name resolution + fact extraction

Both run offline (no tccli / credentials required).

## Conventions

- **Read-only.** No analyzer mutates cloud state. If a finding implies a change, the `ops_skill` field routes the user to the responsible product ops skill.
- **Tenant tag.** `客户` is the canonical tenant tag (`DEFAULT_CUSTOMER_TAG_KEY`); override with `--tag-key`.
- **Region union.** Phase 1 outputs scoped topology per region; cross-region rollups are the orchestrator's job.
- **Credential priority.** `os.environ.setdefault` — shell env always wins, `.env` only fills unset keys.
