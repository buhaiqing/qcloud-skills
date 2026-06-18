# VPC GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-vpc-ops` |
| CLI | `tccli vpc help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (VPC).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (VPC — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Logging secret content** — extending the AGENTS.md list with the VPC-specific
  ban on letting `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` appear
  unmasked anywhere in command, response, or trace.

VPC-specific anti-patterns (most common incidents per `rubric.md` §6 worked examples):

- ❌ **DeleteVpc without resource enumeration** — cascading deletion surprises.
  The Generator MUST call `DescribeVpcResourceDashboard` (or the equivalent sweep
  of `DescribeInstances` + `DescribeLoadBalancers` + `DescribeNatGateways` +
  `DescribeVpcPeeringConnections`) BEFORE committing the delete. The most common
  VPC incident: "I deleted a staging VPC but a production CLB had a cross-VPC
  peering to it, and the peering broke all traffic."
- ❌ **DeleteSubnet without checking running resources** — the API does NOT
  prevent deletion of a subnet with running CVMs, but the CVMs become
  unreachable (their ENI is detached). Always run
  `tccli cvm DescribeInstances --Filters Name=subnet-id` first.
- ❌ **ReleaseAddresses on a bound EIP without surfacing the binding** — the
  Generator MUST call `DescribeAddresses` and check the `InstanceId` /
  `NetworkInterfaceId` fields. A bound EIP release silently breaks DNS and SSL
  certificate validation for any domain pointing to the EIP.
- ❌ **DeleteRouteTable without listing routes** — `0.0.0.0/0` delete is the most
  critical VPC incident (full internet egress drop). The Generator MUST list
  ALL route entries and warn explicitly about the blackhole for any default-route
  deletion.
- ❌ **DeleteSecurityGroup shared between environments** — silent rule loss for
  instances bound across environments. Always call `DescribeSecurityGroupReferences`
  to enumerate ALL bound instances (cross-VPC bindings included).
- ❌ **CreateSubnet with non-subset CIDR** — the API will reject, but the rubric
  should catch it pre-flight. Always validate that the subnet CIDR is a strict
  subset of the parent VPC CIDR before submitting.
- ❌ **Cross-VPC AssociateNetworkInterface** — the API will fail, but the rubric
  should catch it pre-flight. Always verify the target CVM / Subnet / SG is in
  the same VPC as the ENI.
- ❌ **Direct Linux network administration** — this skill does NOT own the OS
  data plane. If a user asks to run `iptables -F` or `ip route add`, HALT and
  explain the OS execution boundary.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 VPC rollout: Generator + Critic + Orchestrator templates for VPC (5 rules, isolated-context enforcement, VPC cascade delete + subnet resource dependency + EIP bound-release + route blackhole + SG rule loss hygiene). 4-section stub covering §1 Generator delta + §4 per-operation variants + §5 VPC-specific anti-patterns + §6 changelog |
| 1.1.0 | 2026-06-19 | Flesh out to full Tier-A conformance (7 sections): §1 expanded to full Generator template with VPC-specific pre-flight (CIDR format / subset validation, zone-in-region check, cascade enumeration hooks, credential masking) and execute / validate / recover sections; §2 new Critic template with explicit "MUST NOT see raw user request" gate, 5-dimension scoring, 5-rule violation tracking, VPC-specific cascade trace audit (parent + child RequestId chain); §3 new Orchestrator template with VPC-specific ABORT triggers (cascade enumeration, running CVM enumeration, EIP binding surfacing, default-route blackhole warning, SG bound-instance enumeration); §4 expanded with 2 new rows (non-destructive rule 0 for create ops, rule 6 for ENI associate/disassociate); §5 expanded with AGENTS.md §9 generic anti-patterns + 7 VPC-specific anti-patterns (cross-VPC association, non-subnet CIDR, OS-level network administration); §6 retains v1.0.0 entry; §7 new See also. Sibling template backbone adapted from `qcloud-cos-ops/references/prompt-templates.md` v1.1.0 |

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — generic anti-patterns banned list
- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec (5 dimensions)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-vpc-ops` is `required`, `max_iter=2`
- [rubric.md](rubric.md) — the rubric instance these templates score against (Tier A: 8 sections, 5 VPC-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates, execution flows, and pre-flight tables
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage pilot)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database pilot)
