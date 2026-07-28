# ADR-0003: FinOps / AIOps / (future) SecOps Event-Driven Architecture

> **Status**: Accepted
> **Date**: 2026-07-28
> **Deciders**: Architecture review (Domain perspective merged with ADR-0002 daemon decision)
> **Supersedes**: —
> **Related**: ADR-0002, qcloud-proactive-inspection, qcloud-aiops-diagnosis, qcloud-finops-ops, qcloud-monitor-ops, qcloud-cam-ops

## 1. Context

ADR-0002 introduces the **plumbing** (`qcloud-agent-daemon/`). This ADR specifies the **business events** that plumbing must serve, scoped to the three operational domains in scope: **FinOps**, **AIOps**, and **future SecurityOps** (SecOps). It is the bridge between "we will run a daemon" and "the daemon will run *these* scenarios".

The constraint from the orchestrator review: every event source → target skill mapping must be **concrete** (named Tencent Cloud APIs, named QCloud skills) and must respect **auto-mode safety boundaries** (no destructive ops in unattended mode without Phase 3 ApprovalQueue).

## 2. Decision

We define **three event domains**, each with explicit event sources, target skills, risk levels, and auto-mode boundaries.

### 2.1 FinOps event domain

| Trigger | Source | Target skill(s) | Risk | Auto allowed? |
|---|---|---|---|---|
| Daily 02:00 cron | `CronSource` (cron: `0 2 * * *`) | `qcloud-finops-ops` (idle scan) + `qcloud-proactive-inspection` (cost-related analyzers) | SAFE | ✅ |
| Hourly cron | `CronSource` (cron: `0 * * * *`) | `qcloud-finops-ops` (账单异常突增 detection) | SAFE | ✅ |
| Weekly Mon 09:00 | `CronSource` | `qcloud-finops-ops` (月度预算执行率 + 季度报告) | SAFE | ✅ |
| Bill anomaly event | `EventBusSource` (Blackboard `pending_action.action="finops_anomaly"`) | `qcloud-finops-ops` (deep dive) | CAUTION | ✅ (read-only) |
| **Budget overrun → propose budget raise** | n/a (proposal) | `qcloud-finops-ops` | DANGEROUS | ❌ → ApprovalQueue |

**Auto-mode SAFE actions in FinOps**: 账单查询、闲置识别（只读）、预算执行率（只读）、账单异常检测、报告生成。
**Deferred to Phase 3 (ApprovalQueue)**: 计费变更、预算调整、资源删除/缩容建议的自动执行。

### 2.2 AIOps event domain

| Trigger | Source | Target skill(s) | Risk | Auto allowed? |
|---|---|---|---|---|
| 5-min cron | `CronSource` (cron: `*/5 * * * *`) | `qcloud-monitor-ops` (active alarm query) → if CRITICAL → `qcloud-aiops-diagnosis` | CAUTION | ✅ |
| Webhook POST | `WebhookSource` (`POST /webhook/monitor`) from Tencent Cloud Monitor alarm callback | `qcloud-aiops-diagnosis` | CAUTION | ✅ |
| EventBus event | `EventBusSource` (Blackboard `event_type="alert.critical"`) | `qcloud-aiops-diagnosis` + relevant product ops | CAUTION | ✅ |
| Periodic health | `CronSource` (cron: `0 */6 * * *`) | `qcloud-proactive-inspection` (anomaly sweep) | SAFE | ✅ |
| **Auto-remediation** (restart, scale, failover) | n/a (proposal) | product ops (`qcloud-cvm-ops`, `qcloud-clb-ops`, etc.) | DANGEROUS | ❌ → ApprovalQueue |

**Auto-mode CAUTION actions in AIOps**: 诊断调用、根因定位、修复建议生成（写入 Blackboard `evidence_chain.findings`）、告警分流（dedup/cooldown via EventBus）。
**Deferred to Phase 3**: 任何状态变更类操作（重启、扩缩容、FailoverSwitch）。

### 2.3 SecurityOps event domain (future, sketch only)

| Trigger | Source | Target skill(s) | Risk | Auto allowed? |
|---|---|---|---|---|
| CAM policy change event | `EventBusSource` (Blackboard `event_type="cam.policy.changed"`) | `qcloud-cam-ops` (audit) | CAUTION | ✅ (read-only audit) |
| AccessKey rotation overdue | `CronSource` (daily) | `qcloud-cam-ops` (list overdue keys) | SAFE | ✅ |
| Anomalous API call pattern | `CronSource` (15-min) + log analysis | `qcloud-cam-ops` + `qcloud-cls-ops` | CAUTION | ✅ (read-only) |
| **Auto-rotate key / revoke permission** | n/a (proposal) | `qcloud-cam-ops` | DANGEROUS | ❌ → ApprovalQueue |

**Why "future"**: SecOps scope is sketched but not committed. Current `qcloud-cam-ops` has read-only audit flows; write flows (rotate, revoke) are gated by L2 confirmation. The daemon will subscribe to SecOps events **only after** Phase 3 ApprovalQueue is in place, because every SecOps remediation is DANGEROUS.

### 2.4 Cross-cutting rules (hard)

1. **No DANGEROUS op in auto mode without ApprovalQueue** (Phase 3 prerequisite; until then, daemon refuses the event and writes a `pending_action` to Blackboard for human review).
2. **All auto-mode runs MUST write to Blackboard** with `trigger_mode="auto"`, `trigger_source="<CronSource|WebhookSource|EventBusSource>"`, and a `evidence_chain` block. This satisfies Reflexion's "every GCL trace must persist" rule and the audit requirement.
3. **All auto-mode runs feed Reflexion** the same way manual runs do — no separate pipeline.
4. **Rate limiting**: each (event_source, target_skill) pair has a configurable cooldown (default 60s) via the EventBus dedup mechanism already in place.
5. **Daemon health is observable**: `/healthz` endpoint returns last-event-processed timestamp; L4 metrics tracker adds 2 new indicators: `auto_event_throughput` and `auto_event_p95_latency_ms`.

## 3. Domain-Perspective Risks (folded in)

| Risk | Mitigation |
|---|---|
| CronSource storm (multiple cron events fire near same time on same resource) | EventBus cooldown + ResourceLock per `{service}:{resource_id}` |
| Webhook replay attack | HMAC-SHA256 signature verification (port from JDCloud D5 reference); reject unsigned |
| FinOps daily cron overlap with manual proactive-inspection run | Blackboard dedup key includes `(customer_tag, day)` |
| AIOps diagnosis recursion (daemon event triggers another alarm → triggers daemon again) | `auto_chain_allowed: bool` field on `DaemonEvent`; default `False`; only `EventBusSource` CRITICAL events can set `True` and only to 1 level deep |
| SecOps false positives flagging legitimate CAM changes | Auto-mode is **read-only audit only** in SecOps; remediation requires human |
| L4 metrics `auto_event_*` become vacuous (always 0) if no events run | Phase 1+2 ships with synthetic fixtures that fire at least one of each event type per day in dev/CI; see Plan §3 |

## 4. Alternatives Considered

### A. One mega-event "any anomaly → all skills"
**Rejected**: LLM reasoning cannot scale to "trigger everything"; also destroys dedup/cooldown. Per-domain event tables give explicit, auditable contracts.

### B. Polling-only (no Webhook/EventBus sources)
**Rejected for AIOps**: Tencent Cloud Monitor supports alarm callbacks; not using them means we miss events between polls. Polling is the *fallback* (5-min cron), not the primary path.

### C. SecOps in this ADR (commit to it now)
**Rejected**: Current `qcloud-cam-ops` lacks ApprovalQueue integration; committing SecOps would force Phase 3 into Phase 1+2 scope, blowing up the budget. Sketched here for context; future ADR will commit.

## 5. Consequences

**Positive**:
- Concrete, auditable event → skill mapping; no LLM guessing in production.
- Auto-mode boundaries explicit; safety review is mechanical (grep for DANGEROUS in auto-mode event tables).
- SecOps future scope sketched cleanly; future ADR can promote it without rewriting this one.

**Negative**:
- 3+ event sources × multiple target skills = operational surface area. Each new event needs an entry in the table + cron in `daemon/configs/patrols.yaml` + cooldown config.
- "DANGEROUS → ApprovalQueue" means several FinOps/AIOps remediation scenarios are **not** auto-executable until Phase 3.

**Mitigations**:
- Patrols config (`daemon/configs/patrols.yaml`) is YAML; per L5/L9 (TE), one source of truth, no hardcoded cron in code.
- Phase 3 is the next planned ADR after this initiative; estimate ≤2 weeks.

## 6. Related

- **ADR-0002** — daemon plumbing
- **docs/superpowers/specs/qcloud-agent-daemon-design.md** — `daemon/configs/patrols.yaml` schema defined there
- **docs/superpowers/plans/qcloud-agent-daemon-implementation.md** — Phase 1+2 rollout
- **qcloud-monitor-ops** — alarm source for AIOps Webhook
- **qcloud-cam-ops** — read-only SecOps anchor
- **AGENTS.md §L11** (KPI gate is only as real as the data it ingests) — applies to L4 metrics `auto_event_*`

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-28 | Initial ADR-0003 |
