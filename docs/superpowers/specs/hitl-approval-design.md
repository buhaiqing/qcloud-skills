# P1-3 HITL Approval Chain — Design

> Status: Draft · Scope: `scripts/hitl_approval.py` + tests

## 1. Background

Ops skills execute live cloud mutations via `tccli`. The harness already detects destructive
intent (`harness_safety.is_destructive`) and binds a human-issued token to `plan_hash`
(`bind_token`/`plan_hash`). There is no tiered gate that maps severity to approval mode,
no degraded timeout, and no auditable chain. This spec defines that gate.

## 2. Tier Model

| Tier | Condition | Gate |
|------|-----------|------|
| `AUTO` | non-destructive plan | `APPROVED` by `system`, no human |
| `TOKEN_BOUND` | destructive + `severity ∈ {info, warning}` | human-issued token must equal `plan_hash(plan_text)` |
| `HUMAN_REVIEW` | destructive + `severity ∈ {critical, high}` (unknown → review) | non-empty `human_approver` sign-off |

`classify_action(plan_text, severity)` implements this mapping; severity is case-insensitive.

## 3. Decision State Machine

```
          ┌─ token valid / approver present ─► APPROVED
request ──┤─ missing/invalid + not timed out ─► DENIED
          └─ missing/invalid + now ≥ timeout_s ─► TIMEOUT_DEGRADED
```

- `AUTO` always `APPROVED` (approver `system`).
- `TOKEN_BOUND`: `bind_token` success → `APPROVED` (`approver=human-token`, `token_hash=plan_hash`);
  else if `now ≥ timeout_s` → `TIMEOUT_DEGRADED` (safe degraded path), else `DENIED`.
- `HUMAN_REVIEW`: `human_approver.strip() != ""` → `APPROVED`; else timeout → `TIMEOUT_DEGRADED`, else `DENIED`.

`Decision ∈ {APPROVED, DENIED, TIMEOUT_DEGRADED}`; degraded is terminal but auditable, never silent.

Injectable clock: `now` may be `float | Callable[[], float] | None` (defaults to `time.monotonic`);
tests use fixed floats / lambdas for determinism.

## 4. Audit Trail

Every `request_approval` appends one record to `trace["approval_chain"]` (creating the list if absent):

```python
{"tier": tier.value, "decision": decision.value, "timestamp": ts,
 "approver": approver, "token_hash": token_hash, "reason": reason}
```

`ApprovalDecision` mirrors this plus `incident_id` (= `plan_hash(plan_text)` by default),
`plan_text`, and `timestamp`. Credential-free: only `token_hash`, never raw token.

## 5. Verification

- `python3 -m ruff check scripts/hitl_approval.py scripts/hitl_approval_test.py` → 0 errors.
- `python3 -m pytest scripts/hitl_approval_test.py -q` → all pass (classify tiers, AUTO approved+logged,
  TOKEN_BOUND valid/invalid/timeout, HUMAN_REVIEW with/without approver+timeout, chain growth).
- `plan_hash`/`bind_token`/`is_destructive` reused from `harness_safety`; no reimplementation.
