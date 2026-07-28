# Spec: `qcloud-agent-daemon` Design

> **Status**: Accepted (design phase)
> **Date**: 2026-07-28
> **Implements**: [ADR-0002](../../architecture/ADR-0002-l3-to-l4-daemon-migration.md), [ADR-0003](../../architecture/ADR-0003-faiops-event-driven-architecture.md)
> **Companion**: [qcloud-agent-daemon-implementation.md](../plans/qcloud-agent-daemon-implementation.md)
> **Self-check**: §12 (assert invariants before marking Phase complete)

## 1. Scope

Design of `qcloud-agent-daemon/`, the persistent event-driven scheduler that elevates QCloud from L3 to L4. Zero-invasion: no existing `qcloud-*-ops/` skill is modified. All integration is via existing public APIs (`scripts/gcl_runner.py`, `qcloud-copilot/copilot/blackboard.py`, `scripts/harness_safety.py`).

**Python version**: 3.10+ (consistent with existing `qcloud-copilot/copilot/` use of `match` statements; `aiohttp` + `fcntl` confirmed available).

**SKILL.md role**: The `SKILL.md` in this package exists for **documentation and discoverability only**. AI agents do NOT invoke `qcloud-agent-daemon/` via the Skill interface; the daemon runs as a standalone CLI process (`python3 -m qcloud_agent_daemon`). The SKILL.md follows the standard format so the package is discoverable in skill registries.

## 2. Module layout

```
qcloud-agent-daemon/
├── __init__.py
├── __main__.py                # python3 -m qcloud_agent_daemon
├── daemon.py                  # asyncio main loop, signal handling
├── events.py                  # DaemonEvent + EventSource Protocol + RiskLevel
├── event_router.py            # classify_event_risk + route to skill
├── resource_lock.py           # ResourceLockManager (fcntl.flock)
├── transient_filter.py        # TransientStateFilter (TC state whitelist)
├── session_manager.py         # per-event SessionManager
├── execution_pipeline.py      # ResourceLock → GCL runner → TransientFilter → Blackboard
├── health_check.py            # /healthz endpoint, 60s interval self-check
├── configs/
│   └── patrols.yaml           # cron + cooldown + target skill mappings (single source of truth)
├── sources/
│   ├── __init__.py
│   ├── cron.py                # CronSource (croniter-driven)
│   ├── webhook.py             # WebhookSource (aiohttp + HMAC-SHA256)
│   └── eventbus.py            # EventBusSource (bridges Blackboard 1.2)
└── tests/                     # NOT in scripts/ — colocated per Quality-perspective invariant §11.4
    ├── test_daemon.py
    ├── test_events.py
    ├── test_resource_lock.py     # TDD-first; ships before resource_lock.py implementation
    ├── test_transient_filter.py  # TDD-first; ships before transient_filter.py implementation
    ├── test_event_router.py
    ├── test_execution_pipeline.py
    └── fixtures/
        └── transient-states/    # tccli Describe* responses for whitelist authoring
```

CLI: `python3 -m qcloud_agent_daemon --config configs/patrols.yaml --sources cron,webhook,eventbus`

## 3. Core contracts

### 3.1 `DaemonEvent` (`events.py`)

```python
@dataclass(frozen=True)
class DaemonEvent:
    event_id: str                  # "evt_" + uuid4().hex
    source: Literal["cron","webhook","eventbus"]
    event_type: str                # e.g. "patrol.finops.daily"
    payload: dict[str, Any]        # event-specific
    created_at: str                # ISO timestamp
    trigger_mode: Literal["manual","auto"]   # hardcoded by source (ADR-0002 D3)
    trigger_source: str            # specific source name (e.g. "CronSource.finops_daily")
    risk: Literal["safe","caution","dangerous","unknown"]
    auto_chain_allowed: bool       # default False; only EventBusSource CRITICAL → True (ADR-0003 §2.4)
    customer_tag: str | None       # for dedup key (ADR-0003 §3)
```

### 3.2 `EventSource` Protocol (`events.py`)

```python
class EventSource(Protocol):
    TRIGGER_MODE: Literal["manual","auto"]  # class attribute, hardcoded
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def poll(self) -> DaemonEvent | None: ...
    @property
    def name(self) -> str: ...
```

### 3.3 `RiskLevel` enum (`events.py`)

```python
class RiskLevel(str, Enum):
    SAFE = "safe"           # read-only or report generation
    CAUTION = "caution"     # diagnoses, analyses; no resource mutation
    DANGEROUS = "dangerous" # resource mutation; auto mode → ApprovalQueue (Phase 3)
    UNKNOWN = "unknown"     # default; trigger human review
```

## 4. Event sources

### 4.1 `CronSource` (`sources/cron.py`)
- Reads `configs/patrols.yaml` → list of `{name, cron, target_skill, risk, cooldown_s}`
- Uses `croniter` to compute next firing; `asyncio.sleep` until then
- `TRIGGER_MODE = "auto"` (class attribute)
- Fires `DaemonEvent(event_type="patrol.<name>", risk=patrol.risk, …)`

### 4.2 `WebhookSource` (`sources/webhook.py`)
- aiohttp HTTP server (default port `9101`)
- `POST /webhook/{source_name}` — HMAC-SHA256 signed; reject unsigned (ADR-0003 §3)
- Body schema: `{"event_type": str, "payload": dict, "risk"?: str}`
- `TRIGGER_MODE = "auto"`

### 4.3 `EventBusSource` (`sources/eventbus.py`)
- Polls Blackboard 1.2 `.runtime/blackboard/*.json` every 5s via `BlackboardClient.read_contributions(since=...)`
- Subscribes to `event_type` patterns defined in `configs/patrols.yaml` (default `["alert.critical", "cam.policy.changed", "finops_anomaly"]`)
- `TRIGGER_MODE = "auto"`

## 5. `ResourceLockManager` (`resource_lock.py`)

Per-resource advisory lock via `fcntl.flock`. Lock key: `{service}:{resource_id}`.

| API | Lock mode | Behaviour |
|---|---|---|
| `try_acquire(resource_key, mode="READ", timeout_s=0)` | `LOCK_SH` / `LOCK_EX` | Non-blocking; returns `LockHandle` or `None` |
| `release(handle)` | downgrade + close | Idempotent |
| `with_read(resource_key, fn)` | `LOCK_SH` | Context manager; auto-release |
| `with_write(resource_key, fn)` | `LOCK_EX` | Context manager; auto-release |

Lock files live at `.runtime/locks/{service}__{resource_id}.lock`. Crash-safe (`fcntl` releases on process death).

**TDD-first**: `tests/test_resource_lock.py` ships *before* implementation with 6 cases: (1) acquire/release round-trip, (2) exclusive blocks shared, (3) shared allows multiple holders, (4) non-blocking returns `None`, (5) crash recovery (kill -9 mid-hold), (6) cross-process via subprocess.

## 6. `TransientStateFilter` (`transient_filter.py`)

Filters out "normal transient" cloud states (Starting/Stopping/…) that would otherwise trigger false alarms in AIOps auto-mode.

### 6.1 Whitelist (DRAFT — verify via fixtures, do not port JDCloud values)

> **⚠️ VALUES NOT VALIDATED.** Each row in the table below is a placeholder. Every entry MUST be replaced from `tests/fixtures/transient-states/<product>.json` (Plan T3.1) before production use. Do NOT ship the placeholder values as-is.

| Service | Transient states | Source CLI |
|---|---|---|
| `cvm` | `RUNNING`, `STOPPED` (real); transient: STARTING/STOPPING/REBOOTING/SHUTTING_DOWN | `tccli cvm DescribeInstances` |
| `cdb` | `RUNNING` (real); transient: INITING/PAUSING/RESIZING/UPGRADING | `tccli cdb DescribeDBInstances` |
| `redis` | `RUNNING` (real); transient: INITING/FLUSHING/UPGRADING | `tccli redis DescribeInstances` |
| `clb` | `RUNNING` (real); transient: CREATING/CONFIGURING | `tccli clb DescribeLoadBalancers` |
| `mongodb` | `RUNNING` (real); transient: INITING/UPGRADING | `tccli mongodb DescribeDBInstances` |
| `postgres` | `RUNNING` (real); transient: INITING/UPGRADING/RESIZING | `tccli postgres DescribeDBInstances` |
| `ckafka` | `RUNNING` (real); transient: INITING/CREATING | `tccli ckafka DescribeInstances` |

> **CRITICAL**: Each entry MUST be verified against real `tccli <product> DescribeInstances --help` output and saved in `tests/fixtures/transient-states/<product>.json` as part of Phase 1+2. **Do NOT port JDCloud's whitelist** (ADR-0002 D6). The placeholder above is illustrative; real values discovered via fixtures take precedence.

### 6.2 API

```python
class TransientStateFilter:
    def __init__(self, whitelist_path: Path): ...
    def is_transient(self, service: str, state: str) -> bool:
        """True = filter out (do not alarm); False = real state change."""
    def classify(self, service: str, state: str) -> Literal["stable","transient","unknown"]:
        """`unknown` triggers human review (ADR-0002 Architect risk)."""
```

**TDD-first**: `tests/test_transient_filter.py` ships before implementation with ≥3 cases per service (real state / transient / unknown).

## 7. `EventRouter` (`event_router.py`)

```
DaemonEvent → classify_event_risk() → RiskLevel
            → SkillRouter.route(payload) → target_skill
            → {"action": "execute"|"queue_approval"|"no_match", ...}
```

| Event risk | Auto-mode action |
|---|---|
| SAFE | execute |
| CAUTION | execute (read-only or analysis; no mutation) |
| DANGEROUS | **queue_approval** (Phase 3; until then, **refuse + write pending_action**) |
| UNKNOWN | refuse + write pending_action for human review |

`SkillRouter` is a thin wrapper over `scripts/harness_router.py` (`build_skill_registry` index).

## 8. `ExecutionPipeline` (`execution_pipeline.py`)

```
async def execute(event: DaemonEvent) -> PipelineResult:
    1. session = SessionManager.create(event)
    2. lock = ResourceLockManager.try_acquire(resource_key, "READ", timeout_s=0)
       if lock is None: return PipelineResult("skipped_locked", ...)
    3. try:
         result = await run_gcl(
             target_skill, event.payload,
             safety_confirm=(event.trigger_mode == "manual"),  # ADR-0002 D7
             session_id=session.id,
         )
       finally:
         ResourceLockManager.release(lock)
    4. TransientStateFilter.classify(result.service, result.state) → log + filter
    5. BlackboardClient.write_contribution(session.id, ...)
    6. return PipelineResult(...)
```

**Hard constraint**: ExecutionPipeline MUST call existing `scripts/gcl_runner.py` (in-process import by default; subprocess via `--isolated` flag). NO fork of GCL logic (ADR-0002 D7).

## 9. `SessionManager` (`session_manager.py`)

Per-event session with `trigger_mode` + `trigger_source` fields. Persisted to `.runtime/daemon/sessions/{event_id}.json` (NOT Blackboard — Blackboard is for *cross*-skill; daemon sessions are private to daemon).

## 10. `HealthCheck` (`health_check.py`)

- `/healthz` returns `{"status":"ok","last_event_ts":...,"uptime_s":...}`
- 60s self-check: EventSource connectivity, Blackboard write/read, lock file dir writable
- L4 metrics tracker consumes `/healthz` data → adds `auto_event_throughput` + `auto_event_p95_latency_ms` indicators (ADR-0003 §2.4)

## 11. Quality-perspective invariants (must hold across all modules)

### 11.1 Blackboard schema compatibility

**Concrete write target** (existing schema 1.2 field paths; do NOT introduce new top-level keys):

```json
{
  "shared_context": {
    "evidence_chain": {
      "process": [
        {
          "step_id": "evt_abc123",
          "actor": "qcloud-agent-daemon",
          "status": "executed",
          "duration_ms": 1234,
          "artifact": ".runtime/daemon/sessions/evt_abc123.json"
        }
      ]
    },
    "pending_action": {
      "action": "approval_required",
      "trigger_mode": "auto",
      "trigger_source": "CronSource.finops_daily",
      "risk": "dangerous",
      "blocked_reason": "DANGEROUS in auto-mode; queued for ApprovalQueue (Phase 3)"
    }
  }
}
```
- Daemon MUST use existing `shared_context.evidence_chain` and `pending_action` slots
- Daemon MUST NOT introduce new top-level Blackboard fields
- CI gate: existing `validate_evidence_schema.py` exits 0 after daemon integration test

### 11.2 GCL runner contract
- Daemon calls `scripts/gcl_runner.run_gcl(..., safety_confirm=...)` with `safety_confirm=False` in auto mode
- Daemon MUST NOT bypass `harness_safety.py` destructive-verb detection (ADR-0002 D7)
- CI gate: existing `gcl_runner_test.py` + `harness_safety_test.py` still pass

### 11.3 Reflexion continuity
- Auto-mode runs feed `docs/failure-patterns.md` via the **same** extraction path as manual runs (no daemon-specific extractor)
- CI gate: `reflexion_retrieve.py` returns non-empty for both manual and auto traces within 7 days

### 11.4 L4 metrics continuity
- `l4_metrics_tracker.py` continues to update 5 existing indicators
- 2 new indicators (`auto_event_throughput`, `auto_event_p95_latency_ms`) added; both go green within Phase 1+2
- Per L11 (AGENTS.md): metrics computed from REAL data; Phase 1+2 ships synthetic fixtures that fire ≥1 of each event type/day in CI

### 11.5 CADL hook compatibility
- Every new `.py` under `qcloud-agent-daemon/` is discoverable by `scripts/cadl_lint.py` (i.e. falls under the existing scan rules)
- Phase 1+2 adds a `qcloud-agent-daemon/SKILL.md` with the canonical hook line at file end (per AGENTS.md CADL requirement)

### 11.6 Agent-Agnostic P0 binding
- `qcloud-agent-daemon/` imports ONLY stdlib + existing repo modules (`scripts/`, `qcloud-copilot/copilot/`)
- No MCP, no agent-runtime SDK, no Cursor/OpenCode/Claude-Code-specific imports
- CLI surface only: `python3 -m qcloud_agent_daemon`
- CI gate: a `grep -rE "(mcp|opencode|claude_code|cursor).*import" qcloud-agent-daemon/` returns empty

## 12. Self-check (before declaring Phase 1+2 done)

Per AGENTS.md Spec-Plan-Code Alignment Gate: each item MUST be ✅.

| # | Item | Status |
|---|---|---|
| 1 | All modules in §2 exist or have explicit "deferred to Phase N" markers | ⬜ |
| 2 | DaemonEvent contract matches §3.1 | ⬜ |
| 3 | EventSource Protocol matches §3.2 | ⬜ |
| 4 | CronSource / WebhookSource / EventBusSource match §4 | ⬜ |
| 5 | ResourceLockManager has 6 TDD test cases (§5) — proving both fire AND stay silent per L6 | ⬜ |
| 6 | TransientStateFilter whitelist sourced from fixtures/transient-states/*.json (§6.1) | ⬜ |
| 7 | EventRouter refuses DANGEROUS in auto mode (§7) | ⬜ |
| 8 | ExecutionPipeline calls `scripts/gcl_runner.run_gcl(..., safety_confirm=...)` (§8) — no fork | ⬜ |
| 9 | SessionManager persists to `.runtime/daemon/sessions/` (§9), NOT Blackboard | ⬜ |
| 10 | HealthCheck `/healthz` returns expected JSON shape (§10) | ⬜ |
| 11 | Invariants §11.1-11.6 verified by CI | ⬜ |
| 12 | SKILL.md exists with CADL hook line (§11.5) | ⬜ |
| 13 | AGENTS.md updated with ADR reference (§11 CADL boundary) | ⬜ |

## 13. Out of scope (deferred)

- ApprovalQueue (Phase 3)
- Dashboard / WebSocket (Phase 3)
- A2A-style multi-agent dispatch (intentionally NOT — QCloud uses Blackboard + skill orchestration)
- Goal decomposition (intentionally NOT — QCloud's PlanDispatcher handles multi-step within a request; cross-request scheduling is daemon's job)

## 14. Related

- [ADR-0002](../../architecture/ADR-0002-l3-to-l4-daemon-migration.md)
- [ADR-0003](../../architecture/ADR-0003-faiops-event-driven-architecture.md)
- [qcloud-agent-daemon-implementation.md](../plans/qcloud-agent-daemon-implementation.md) — Phase 1+2 tasks
- [gcl-spec.md](../../gcl-spec.md) — runner contract
- [harness_safety.py](../../../scripts/harness_safety.py) — destructive-verb detection reused
