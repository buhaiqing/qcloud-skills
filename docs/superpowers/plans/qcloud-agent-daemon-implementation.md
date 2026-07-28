# Plan: `qcloud-agent-daemon` Implementation — Phase 1+2

> **Status**: Accepted
> **Date**: 2026-07-28
> **Implements**: [ADR-0002](../../architecture/ADR-0002-l3-to-l4-daemon-migration.md), [ADR-0003](../../architecture/ADR-0003-faiops-event-driven-architecture.md)
> **Spec**: [qcloud-agent-daemon-design.md](../specs/qcloud-agent-daemon-design.md)
> **Estimated effort**: 7-10 working days (single PR/commit or 2-3 small PRs)
> **Self-check**: §5 (assert Phase exit criteria before declaring done)

## 1. Phase 1+2 boundary

Phase 1+2 in ONE initiative (per orchestrator review: Phase 1 alone = half-built cron).

**In scope (this Plan)**:
- `qcloud-agent-daemon/` package skeleton (per Spec §2)
- All 8 modules in Spec §3-§10
- 3 EventSource implementations (Cron / Webhook / EventBus)
- ResourceLockManager + TransientStateFilter (TDD-first)
- Tests: ≥6 cases for resource lock, ≥3 per service for transient filter
- Synthetic CI fixtures firing ≥1 of each event type/day (per L11)
- L4 metrics: 2 new indicators (`auto_event_throughput`, `auto_event_p95_latency_ms`)
- SKILL.md with CADL hook line

**Out of scope (deferred to Phase 3, future ADR)**:
- ApprovalQueue
- Dashboard / WebSocket
- SecOps write flows (cam.rotate_key, etc.)

## 2. Task breakdown

Tasks are ordered to satisfy TDD-first (constraint from orchestrator review) and minimize cross-module rework.

### T1 — Bootstrap (Day 1)
- [ ] T1.1 `mkdir qcloud-agent-daemon/{sources,configs,tests/fixtures/transient-states}`
- [ ] T1.2 `__init__.py`, `__main__.py` with `argparse` CLI (`--config`, `--sources`)
- [ ] T1.3 Stub `daemon.py` main loop (asyncio, signal handling, source lifecycle)
- [ ] T1.4 Stub `events.py` with `DaemonEvent`, `EventSource`, `RiskLevel` (matches Spec §3)
- [ ] T1.5 Stub `tests/test_events.py` with dataclass round-trip + Protocol conformance
- [ ] **DoD**: `python3 -m qcloud_agent_daemon --help` exits 0; `pytest qcloud-agent-daemon/tests/test_events.py` green

### T2 — ResourceLockManager (TDD-first) (Day 2-3)
- [ ] T2.1 Write `tests/test_resource_lock.py` with 6 cases per Spec §5 (acquire/release, exclusive blocks shared, shared allows multi, non-blocking returns None, crash recovery, cross-process via subprocess)
- [ ] T2.2 Implement `resource_lock.py` to satisfy tests
- [ ] T2.3 Reuse `harness_safety.py` fcntl idioms (do NOT reinvent)
- [ ] T2.4 Lint: `ruff check qcloud-agent-daemon/resource_lock.py`
- [ ] **DoD**: All 6 cases pass; existing `harness_safety_test.py` still green (regression check)

### T3 — TransientStateFilter (TDD-first) (Day 3-4)
- [ ] T3.1 Generate `tests/fixtures/transient-states/{cvm,cdb,redis,clb,mongodb,postgres,ckafka}.json` from real `tccli <product> DescribeInstances` responses (verify each state code)
- [ ] T3.2 Write `tests/test_transient_filter.py` with ≥3 cases per service (real/transient/unknown) per Spec §6.2
- [ ] T3.3 Implement `transient_filter.py` to satisfy tests
- [ ] T3.4 Lint
- [ ] **DoD**: All fixture-based tests pass; whitelist sourced from fixtures (NOT JDCloud port)

### T4 — EventRouter + SkillRouter wrapper (Day 4)
- [ ] T4.1 Implement `event_router.py` per Spec §7 (risk classification + skill routing)
- [ ] T4.2 Wrap `scripts/harness_router.py` for skill lookup
- [ ] T4.3 `tests/test_event_router.py` covering: SAFE→execute, CAUTION→execute, DANGEROUS→queue_approval (refuse + pending_action in Phase 1+2 since ApprovalQueue not yet built), UNKNOWN→refuse + pending_action
- [ ] **DoD**: DANGEROUS in auto mode writes Blackboard `pending_action` and returns without executing (proves gate fires per L6)

### T5 — EventSource implementations (Day 5-6)
- [ ] T5.1 `CronSource` (croniter-based) with `TRIGGER_MODE = "auto"` class attribute (Spec §4.1)
- [ ] T5.2 `WebhookSource` (aiohttp + HMAC-SHA256 verification; reject unsigned per ADR-0003 §3)
- [ ] T5.3 `EventBusSource` (Blackboard 1.2 polling via `BlackboardClient.read_contributions(since=...)`)
- [ ] T5.4 `configs/patrols.yaml` (single source of truth for cron + cooldown + target skill — per L5/L9)
- [ ] T5.5 Tests: cron firing, webhook HMAC positive/negative, EventBus dedup
- [ ] **DoD**: Each source can fire a `DaemonEvent` end-to-end in isolation; L4 metrics tracker `auto_event_throughput` > 0 in CI

### T6 — ExecutionPipeline + GCL runner integration (Day 6-7)
- [ ] T6.1 Implement `execution_pipeline.py` per Spec §8 (sequence: SessionManager → ResourceLock → run_gcl → TransientFilter → Blackboard write)
- [ ] T6.2 Import `scripts/gcl_runner.run_gcl` (in-process by default; `--isolated` flag → subprocess)
- [ ] T6.3 Wire `safety_confirm=False` for auto mode (per ADR-0002 D7)
- [ ] T6.4 Implement `SessionManager` per Spec §9 (`.runtime/daemon/sessions/`, NOT Blackboard)
- [ ] T6.5 `tests/test_execution_pipeline.py` covering: happy path, lock contention → skip, TransientFilter false-positive → log-only, destructive in auto → refused (per T4.3)
- [ ] **DoD**: Pipeline runs end-to-end with synthetic event; GCL trace persists; `safety_confirm=False` is honored (regression: `harness_safety_test.py` still green)

### T7 — HealthCheck + L4 metrics integration (Day 7-8)
- [ ] T7.1 Implement `health_check.py` (`/healthz`, 60s self-check per Spec §10)
- [ ] T7.2 Add 2 new indicators to `scripts/l4_metrics_tracker.py`: `auto_event_throughput`, `auto_event_p95_latency_ms`
- [ ] T7.3 CI fixture: synthetic daily event firing (per L11 — metrics not vacuous)
- [ ] **DoD**: `python3 scripts/l4_metrics_tracker.py` shows the 2 new indicators with `current > 0` (L11 verification); CI exits 0

### T8 — Daemon main loop wiring (Day 8)
- [ ] T8.1 Wire daemon.py to: start sources → poll loop → execute pipeline → write Blackboard
- [ ] T8.2 SIGTERM/SIGINT graceful shutdown
- [ ] T8.3 `tests/test_daemon.py` covering: start/stop lifecycle, signal handling, source failure isolation (one source down ≠ daemon crash)
- [ ] **DoD**: `python3 -m qcloud_agent_daemon --sources cron --config configs/patrols.yaml` runs ≥30s in CI, processes ≥1 synthetic event, exits cleanly on SIGTERM

### T9 — SKILL.md + docs + ADR-trace (Day 9)
- [ ] T9.1 Create `qcloud-agent-daemon/SKILL.md` with frontmatter + CADL hook line at file end (Spec §11.5)
- [ ] T9.2 Update `docs/architecture/README.md` if needed (likely no change)
- [ ] T9.3 Update root AGENTS.md: add ADR reference + CADL boundary rule (companion to ADR-0001)
- [ ] T9.4 `scripts/cadl_lint.py` exits 0 (hook line present per §11.5)
- [ ] **DoD**: All spec §11 invariants verified by CI

### T10 — Phase exit verification (Day 9-10)
- [ ] T10.1 Run `python3 scripts/validate_local.py` → exit 0
- [ ] T10.2 Run `python3 scripts/validate_skills_frontmatter.py` → exit 0 (new SKILL.md included)
- [ ] T10.3 Run `python3 scripts/check_gcl_conformance.py` → 33+1/33+1 conform
- [ ] T10.4 Run `python3 scripts/cadl_lint.py` → exit 0
- [ ] T10.5 Run `ruff check qcloud-agent-daemon/` → 0 errors
- [ ] T10.6 Run `python3 -m unittest discover qcloud-agent-daemon/tests/` → all green
- [ ] T10.7 Verify Spec §12 self-check table: all 13 items ✅
- [ ] T10.8 Update `docs/failure-patterns.md` if any new failure modes discovered during T1-T9 (per CADL)
- [ ] **DoD**: All 8 checks exit 0; Spec §12 self-check fully ✅; Phase 1+2 declared done

## 3. Verify checkpoints (between phases)

| After task | Verify |
|---|---|
| T1 | CLI loads; test_events.py green |
| T2 | resource_lock tests green; harness_safety regression OK |
| T3 | transient_filter tests green; fixtures sourced from real CLI |
| T4 | event_router gate-fires (DANGEROUS in auto refuses); L6 verification |
| T5 | Each source fires a DaemonEvent; L4 metric auto_event_throughput > 0 |
| T6 | Pipeline end-to-end; GCL trace persists; safety_confirm honored |
| T7 | L4 metrics tracker shows 2 new indicators non-vacuous; L11 verification |
| T8 | Daemon lifecycle + signal handling green |
| T9 | SKILL.md valid; cadl_lint green |
| T10 | All CI gates green; Spec §12 self-check ✅ |

## 4. Risks + mitigations

| Risk | Mitigation |
|---|---|
| TDD-first front-loads 2-3 days of fixture/test work | Acceptable: per L7, drift between plan and reality causes rework; tests as spec is cheaper |
| TransientFilter whitelist incomplete for some Tencent state codes | `unknown` classification in §6.2 → human review path (no false alarms) |
| Blackboard 1.2 schema contamination | Spec §11.1 + T9.3 spec/plan traceability; CI gate `validate_evidence_schema.py` |
| GCL runner subprocess vs in-process semantics differ | Default in-process; `--isolated` flag explicit; documented in Spec §8 |
| Daemon becomes hidden SPOF | HealthCheck + signal handling + T8.3 isolation test |
| L4 metrics vacuous | T7.3 synthetic CI fixtures per L11 |

## 5. Self-check (before declaring Phase 1+2 done)

| # | Item | Source | Status |
|---|---|---|---|
| 1 | All 10 task groups (T1-T10) marked done with verifiable artifacts | §2 | ⬜ |
| 2 | All 9 verify checkpoints pass | §3 | ⬜ |
| 3 | All 6 risks mitigated per evidence (not just stated) | §4 | ⬜ |
| 4 | `validate_local.py`, `validate_skills_frontmatter.py`, `check_gcl_conformance.py`, `cadl_lint.py`, `ruff`, `unittest` all exit 0 | T10.1-10.6 | ⬜ |
| 5 | Spec §12 self-check (all 13 items ✅) re-verified | T10.7 | ⬜ |
| 6 | AGENTS.md updated with ADR + CADL boundary rule | T9.3 | ⬜ |
| 7 | `docs/failure-patterns.md` updated if any new failure modes found | T10.8 | ⬜ |
| 8 | 2 new L4 indicators (`auto_event_throughput`, `auto_event_p95_latency_ms`) non-vacuous | T7.2-7.3 | ⬜ |

## 6. Out of scope (Phase 3+)

- **Phase 3** (future ADR): ApprovalQueue, Dashboard / WebSocket
- **Phase 4+**: SecOps write flows (CAM key rotation, etc.); deferred until Phase 3 unblocks

## 7. Related

- [ADR-0002](../../architecture/ADR-0002-l3-to-l4-daemon-migration.md) — D1-D9 + risks
- [ADR-0003](../../architecture/ADR-0003-faiops-event-driven-architecture.md) — FinOps/AIOps/SecOps event tables
- [qcloud-agent-daemon-design.md](../specs/qcloud-agent-daemon-design.md) — design spec §1-§14
- [AGENTS.md §L1-L13](../../AGENTS.md) — execution lessons (L6, L7, L11 apply)
- AGENTS.md §"复利资产沉淀机制 (CADL)" — T10.8 closure requirement
