# ADR-0002: L3→L4 Migration via `qcloud-agent-daemon/` (Persistent Event-Driven Scheduler)

> **Status**: Accepted
> **Date**: 2026-07-28
> **Deciders**: Architecture review (orchestrator merging 3 perspectives: Architect / Domain / Quality)
> **Supersedes**: —
> **Related**: ADR-0001, ADR-0003, docs/superpowers/specs/qcloud-agent-daemon-design.md (forthcoming), docs/gcl-spec.md §4, qcloud-copilot/copilot/blackboard.py

## 1. Context

The repo is at Gartner Agentic AI **L3 advanced** — strong within-session quality (GCL loop, isolated Critic, Reflexion, 4-tier Safety Gate, Blackboard evidence chain, L4 metrics tracker). What it lacks is the **persistent, event-driven scheduler layer** that distinguishes L4: ability to react to *external* triggers (cron, alarm webhook, EventBus event) without a human invoking a skill, and to keep running across sessions.

Triggering the decision now: three concrete business needs that current architecture cannot serve:

| Need | Today's limitation | L4 requirement |
|---|---|---|
| **FinOps daily cruise** | `qcloud-proactive-inspection/scripts/01-perceive/cruise_sniff.py` requires a human to invoke | Cron-triggered nightly daemon run with auto-publish to Blackboard |
| **AIOps alarm storm** | `qcloud-aiops-diagnosis` reacts when a human pastes an alarm | Webhook-triggered daemon run on `monitor DescribeAlarmHistories` critical event |
| **Future SecurityOps** | No capability | EventBus subscription to CAM/credential changes |

Upstream pattern reference: `jdcloud-skills/docs/architecture/2026-07-28-l3-to-l4-agent-daemon-adr.md` (Phase 1-2 complete; Phase 3-5 in progress). We deliberately **scope to FinOps + AIOps + future SecurityOps** and **adapt** rather than port (see §3).

## 2. State of the Union (current vs target)

| Capability | QCloud today | JDCloud L4 Entry | QCloud target (this ADR) | Migration |
|---|---|---|---|---|
| Persistent scheduler | ❌ none | `jdcloud_agent_daemon/daemon.py` (asyncio) | `qcloud-agent-daemon/daemon.py` | Adapted |
| EventSource abstraction | ❌ none | `events.py` + Protocol | `daemon/events.py` + Protocol | Adapted |
| CronSource | ❌ none | `sources/cron_source.py` | `daemon/sources/cron.py` | Direct port (pattern only) |
| WebhookSource | ❌ none | `sources/webhook_source.py` (aiohttp + HMAC) | `daemon/sources/webhook.py` | Direct port |
| EventBusSource | ❌ none | bridges `mesh/eventbus/` | bridges **Blackboard schema 1.2** | Adapted (different bridge target) |
| DaemonEvent.trigger_mode | ❌ none | `events.py` field | `daemon/events.py` field | Direct |
| EventRouter + RiskLevel | partial (`mode_resolver.py` for LLM mode only) | full | **separate** `daemon/event_router.py` (RiskLevel ≠ inspection mode) | New |
| ResourceLockManager (fcntl.flock) | ❌ none | `resource_lock.py` | `daemon/resource_lock.py` | TDD-first (constraint from orchestrator review) |
| TransientStateFilter (7-resource whitelist) | ❌ none | `transient_filter.py` | `daemon/transient_filter.py` | **Re-build table for Tencent Cloud** (do NOT port JDCloud's) |
| SessionManager + dual-mode | partial (`session.py` for inspection sessions only) | full | **separate** `daemon/session_manager.py` | New (different lifecycle) |
| ExecutionPipeline | partial (`engine.py` for LLM plans) | full | `daemon/execution_pipeline.py` (wraps **existing** GCL runner with `safety_confirm`) | Adapted (reuse > rebuild) |
| ApprovalQueue | ❌ none | `approval_queue.py` (Phase 5) | `daemon/approval_queue.py` (Phase 3) | Deferred to Phase 3 |
| HealthCheck | partial (`skill_health` in JDCloud) | `health_check.py` | `daemon/health_check.py` | New |
| ADR mechanism | ❌ none | n/a | `docs/architecture/` | New (ADR-0001) |

## 3. Decision

We introduce `qcloud-agent-daemon/` as a new top-level package, executing Phase 1 (skeleton) and Phase 2 (concurrency safety) **in a single coordinated initiative** (per orchestrator review: splitting leaves a "half-built cron that nothing consumes").

### D1 — New top-level package `qcloud-agent-daemon/`
**Rationale**: SecurityOps future scope will not live under `qcloud-copilot/`; aligning with JDCloud reduces cross-repo learning cost. Reuses `qcloud-copilot/` only via its public APIs (`PlanDispatcher`, `BlackboardClient`, `Safety` gates), never via internal modules.

### D2 — Reuse Blackboard 1.2 as the durable bus; do NOT introduce a new MQ layer
**Rationale**: QCloud Blackboard (`qcloud-copilot/copilot/blackboard.py`) is already file-locked (`fcntl`), schema-versioned, and the cross-subsystem write target. Adding Kafka/RabbitMQ would double the operational surface for a single-process use case. **No new EventBus abstraction**; daemon subscribes to Blackboard events via a thin EventBusSource.

### D3 — Dual-mode (manual / auto) hardcoded at the EventSource level
**Rationale**: Matches JDCloud D3 — prevents AI-reasoned mode classification. Each EventSource declares `TRIGGER_MODE: Literal["manual","auto"]` as a class attribute. `CronSource`, `WebhookSource`, `EventBusSource` are all `auto`. Future `ManualApiSource` would be `manual`.

### D4 — No manual/auto skill split
**Rationale**: All existing `qcloud-*-ops/` skills stay single-responsibility. The daemon adapts *invocation* (via `safety_confirm=False` in auto mode), not *skill structure*.

### D5 — ResourceLockManager (fcntl.flock) + TransientStateFilter as Phase 1+2 paired deliverable
**Rationale (orchestrator constraint)**: Both are preconditions for ExecutionPipeline to safely run auto-mode. **TDD-first** — write `scripts/test_resource_lock.py` + `scripts/test_transient_filter.py` using stubbed Tencent Cloud API responses BEFORE implementing. Reuse `harness_safety.py`'s fcntl idioms rather than reinventing.

### D6 — TransientStateFilter table MUST be built from Tencent Cloud API evidence, not ported from JDCloud
**Rationale**: JDCloud's 7-resource whitelist was authored against JD Cloud instance state codes. Tencent's state codes differ (e.g. `RUNNING`/`STOPPED` shared, but `Isolated`/`Banning`/`Migrating` semantics vary). Build from `tccli <product> DescribeInstances` fixture data; document each entry with source CLI command.

### D7 — ExecutionPipeline wraps **existing** GCL runner, not a new GCL
**Rationale (orchestrator constraint)**: `scripts/gcl_runner.py` already supports `safety_confirm: bool` and pre/post hooks. Daemon calls it via subprocess or in-process import. Destructive ops get `safety_confirm=False` (auto) + queue to ApprovalQueue (Phase 3). **No fork of GCL logic.**

### D8 — Phase boundaries
| Phase | Scope | Status |
|---|---|---|
| **Phase 1+2 (this initiative)** | D1-D7 above + EventSource/Cron/Webhook/Router/ResourceLock/TransientFilter/ExecutionPipeline/HealthCheck | This ADR |
| Phase 3 | ApprovalQueue + Dashboard integration (deferred) | Future ADR |
| Phase 4+ | A2A / goal decomposition / multi-agent (deferred) | Likely NO — QCloud uses Blackboard + skill orchestration, not A2A |

**We explicitly do NOT adopt JDCloud D8 (A2A template bulk extension)** — see §4.

### D9 — Agent-Agnostic P0 binding preserved
**Rationale**: `qcloud-agent-daemon/` runs as a standalone `python3 -m qcloud_agent_daemon` process. CLI surface only; no MCP, no agent-runtime SDK imports. Compatible with any OpenSpec agent that can spawn a subprocess.

## 4. Alternatives Considered

### A. Direct port of `jdcloud_agent_daemon/` Python code
**Rejected**: QCloud's GCL/Safety/Blackboard are *different* implementations (`scripts/gcl_runner.py` vs `gcl_runner.py` in `jdcloud-agent-infra/`). Direct port would fork the GCL core, breaking all existing tests, rubrics, and traces.

### B. Adopt JDCloud's A2A template-based bulk extension (D8 upstream)
**Rejected**: QCloud's cross-skill collaboration is Blackboard-mediated + orchestrator-skill-mediated (`qcloud-copilot`, `qcloud-well-architected-review`). A2A has no place in the current design; adding it would double the cross-skill surface area.

### C. Build cron-style automation on GitHub Actions only (no daemon)
**Rejected for FinOps/AIOps/SecOps**: GH Actions are polling-heavy (1-min minimum), not persistent, and have no Blackboard integration. They are good for *batch* work (pattern-anomaly-cron already uses it), bad for *reactive* work (alarm webhook).

### D. Reuse `qcloud-copilot/copilot/engine.py` as the daemon
**Rejected**: `engine.py` is a per-request topological DAG executor, not a long-lived asyncio scheduler. Mixing concerns confuses the PlanDispatcher contract.

### E. Skip Phase 2 (concurrency safety) for Phase 1 only
**Rejected**: Phase 1 alone (skeleton without ResourceLock/TransientFilter/ExecutionPipeline) produces a daemon that *generates* events but cannot *consume* them safely. Per orchestrator constraint: half-built = unfinished.

## 5. Architect-Perspective Risks (folded in)

| Risk | Mitigation |
|---|---|
| fcntl.flock LOCK_EX↔LOCK_SH upgrade deadlock | TDD-first; reuse `harness_safety.py` lock idioms; add explicit `try_acquire(timeout=)` everywhere |
| TransientFilter false negatives (state outside whitelist looks like incident) | Build whitelist from real `tccli Describe*` fixture responses; mark `UNKNOWN` (not `SAFE`) when state unrecognised → triggers human review |
| CronSource drift after clock change | Use `croniter` (already a dependency in upstream) + log every firing |
| Blackboard schema 1.2 contamination (daemon writes a new top-level field) | Use existing `shared_context.evidence_chain` and `pending_action` slots; do NOT extend schema in daemon |
| GCL runner subprocess vs in-process call | Default in-process (faster trace correlation); subprocess only when isolation needed; document the trade-off in Spec |
| Daemon becomes a hidden SPOF | `health_check.py` + SIGTERM graceful shutdown + systemd unit template (out of scope; document in Plan) |

## 6. Consequences

**Positive**:
- FinOps/AIOps gain automatic, unattended execution paths.
- Cron/webhook reactivity unblocks "夜间自动巡检 + 告警实时诊断" product scenarios.
- Phase 1+2 in one shot avoids the half-built intermediate state.
- Blackboard stays the single source of truth — no new MQ, no schema bump.

**Negative**:
- New top-level package adds directory surface area.
- 7-resource TransientFilter whitelist is new maintenance burden (each Tencent API revision may require update).
- TDD-first for ResourceLock/TransientFilter front-loads ~2-3 days of test fixture work.

**Mitigations**:
- AGENTS.md adds ADR reference + CADL boundary (companion to ADR-0001).
- Quarterly review of TransientFilter table; new states logged to `docs/failure-patterns.md` per CADL.
- `scripts/test_resource_lock.py` and `scripts/test_transient_filter.py` ship with Phase 1+2 (rejection tests prove both fire and stay silent, per L6).

## 7. Related

- **ADR-0001** — ADR mechanism (this ADR uses it)
- **ADR-0003** — FinOps/AIOps/SecOps event-driven architecture (next sibling)
- **docs/superpowers/specs/qcloud-agent-daemon-design.md** — forthcoming design doc (modules, contracts, fixtures)
- **docs/superpowers/plans/qcloud-agent-daemon-implementation.md** — forthcoming Phase 1+2 plan
- **AGENTS.md §"Spec-Plan-Code Alignment Gate"** — Spec/Plan traceability
- **AGENTS.md §L4-L13 (Execution lessons)** — `L6` (gates must fire AND stay silent) applies to Phase 1+2 tests

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-28 | Initial ADR-0002 |
