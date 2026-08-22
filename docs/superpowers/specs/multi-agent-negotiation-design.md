# Multi-Agent Negotiation Design (P2-7)

## Background

Skills orchestrate `tccli` operations, sometimes with multiple agents acting on
shared Tencent Cloud resources (e.g. CVM instances). Concurrent mutating ops on
the same resource can clobber state. A lightweight in-memory negotiation layer
serializes conflicting intentions before execution.

## Conflict Model

- `ResourceOp { agent_id, resource_id, action, priority }` where `action` in
  `{READ, WRITE, DELETE, SCALE}` and `resource_id` is a cloud resource id
  (e.g. `ins-xxxxxxxx`).
- `conflicts_with(other)` is true iff:
  1. `resource_id` equal,
  2. actions not both `READ`,
  3. at least one action in `MUTATING = {WRITE, DELETE, SCALE}`.
- `READ+READ` never conflicts. Cross-resource ops never conflict.

## Resolution Rules

- `NegotiationHub` collects proposals via `propose(op) -> proposal_id`
  (`p1`, `p2`, ...).
- `detect_conflicts() -> list[tuple[id, id]]` enumerates conflicting pairs.
- `resolve() -> dict[id, GRANTED|DENIED]`:
  - Non-conflicting proposals: `GRANTED`.
  - Each conflicting resource group: highest `priority` wins (`GRANTED`),
    others `DENIED`. Ties broken deterministically by lexicographic proposal id.
  - In-memory only; no side effects beyond recorded state.
- `decisions()` returns last `resolve()` outcome.

## Verification

- `scripts/negotiation.py` implements `ResourceOp` and `NegotiationHub`.
- `scripts/negotiation_test.py` (unittest): WRITE vs READ conflict, READ vs READ
  no conflict, detect pairs, higher priority wins, tie-break by id
  deterministic, independent resources never conflict.
- Gates: `python3 -m ruff check scripts/negotiation.py scripts/negotiation_test.py`
  and `python3 -m pytest scripts/negotiation_test.py -q` must pass.

## Self-Check

- Spec covers all brief requirements: dataclass fields, action set,
  conflict predicate, hub API, resolution semantics, tie-break, file list.
