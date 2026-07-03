# qcloud-ccn-ops GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-ccn-ops` |
| CLI | `tccli vpc` (CCN operations share the VPC namespace) |
| max_iterations | 2 |

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (Generator).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (Generator — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

---

## 5. Anti-patterns

> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Attaching VPC without checking CIDR overlap** — causes `InvalidParameter.CidrConflict`
- ❌ **Detaching without checking dependent static routes** — creates blackholes
- ❌ **Deleting CCN without enumerating all attachments** — API rejects or leaves orphan routes
- ❌ **Setting bandwidth limit without verifying current usage** — may throttle production traffic
- ❌ **Cross-account attach without acceptor approval** — attachment stays `PENDING` indefinitely
- ❌ **Static route with non-attached next hop** — route is created but traffic blackholed
- ❌ **Credential literals in examples** — Safety=0 → ABORT
- ❌ **Shared-context G+C** — Critic must not see user request

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-03 | Initial CCN GCL prompt templates following TE-6 spec |

---

## 7. See also

- [`rubric.md`](rubric.md) — 5 dimensions + 5 CCN-specific safety rules
- [governance-and-adversarial-review.md](../../qcloud-skill-generator/references/governance-and-adversarial-review.md)
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl)
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
