---
name: qcloud-clb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CLB (Cloud Load Balancer, 负载均衡) — LoadBalancer instances, listeners,
  backend servers, and health checks. User mentions CLB, 负载均衡, Load Balancer,
  Tencent Cloud LB, or describes product-specific scenarios (e.g., traffic distribution,
  backend binding, listener configuration, health check failures, SSL certificates,
  cross-region binding, performance issues) even without naming the product directly.
  Not for billing, CAM, VPC-only operations, CVM instance management, or related
  products that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-clb),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.3.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/214"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli clb help` - CLI exposes CreateLoadBalancer, DescribeLoadBalancers,
    ModifyLoadBalancerAttributes, DeleteLoadBalancer, CreateListener, DescribeListeners,
    RegisterTargets, DeregisterTargets, DescribeTargetHealth, and 70+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CLB (Load Balancer) Operations Skill

## Overview

CLB (Cloud Load Balancer, 负载均衡) distributes access traffic across multiple backend servers, eliminating single points of failure. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (`tccli` CLI primary + Python SDK fallback), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** Follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: `tccli clb` is the **primary** path. You **MUST** ship `references/cli-usage.md` and document **both** CLI and SDK steps in each execution flow. SDK fallback covers edge-case operations CLI doesn't expose.

### Five Core Standards

See [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates).

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, health checks, backend redundancy, cross-region binding | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSL/HTTPS certificates, security groups, DDoS protection | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance type comparison, pay-as-you-go vs prepaid, idle LB detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Listener batch ops, target group management, automation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CLB" / "负载均衡" / "Load Balancer" / "LB" / "腾讯云负载均衡"
- CRUD or lifecycle ops on **LoadBalancer instances**, **Listeners** (TCP/UDP/HTTP/HTTPS), **Backend Servers/Targets**, **Target Groups**
- CLB access log analysis via CLS (see `references/clb-log-analysis.md`)
- Keywords: traffic distribution, listener, backend server, health check, SSL certificate, VIP, cross-region, Anycast
- Traffic issues (connection failures, backend health problems, SSL errors) without naming the product

### SHOULD NOT Use This Skill When

- Billing / account management → `qcloud-billing-ops` · CAM only → `qcloud-cam-ops` · VPC-only → `qcloud-vpc-ops`
- CVM instance management → `qcloud-cvm-ops` · SSL-only → `qcloud-ssl-ops` · Architecture review → `qcloud-well-architected-review`

### Delegation Rules

- CLB depends on VPC: verify VPC/Subnet via `qcloud-vpc-ops` before CreateLoadBalancer
- Backend servers are CVM: use `qcloud-cvm-ops` to verify instance existence/status before RegisterTargets
- HTTPS certificates: verify via SSL service or CAM
- Access log analysis: delegate to `qcloud-cls-ops`; reference `clb-log-analysis.md` for query templates
- Proactive inspection → `qcloud-proactive-inspection` (`references/proactive-inspection.md`); Well-Architected assessment → `qcloud-well-architected-review` (see Read-Only mode below)

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CLB**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** Create/Delete/Modify/Register/Deregister.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: clb`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` / `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime env | NEVER ask; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime env | Default `ap-guangzhou` if unset |
| `{{user.loadbalancer_id}}` / `{{user.loadbalancer_name}}` | User-supplied LB ID/name | Ask once; reuse |
| `{{user.listener_id}}` / `{{user.listener_protocol}}` / `{{user.listener_port}}` | Listener identity | Ask once; port default by protocol |
| `{{user.instance_id}}` / `{{user.target_port}}` / `{{user.target_weight}}` | Backend target | Ask once; weight default 10; verify instance via qcloud-cvm-ops |
| `{{output.loadbalancer_id}}` | From CreateLoadBalancer | Parse `$.Response.LoadBalancerIds[0]` |
| `{{output.listener_id}}` | From CreateListener | Parse `$.Response.ListenerIds[0]` |
| `{{output.request_id}}` | From any response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security (Credential Masking — MANDATORY):** NEVER log/print/expose `TENCENTCLOUD_SECRET_KEY`. Mask with `***` / `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions

- **API spec is canonical**: https://cloud.tencent.com/document/api/214
- **Errors**: `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: ISO 8601 (e.g., `2026-05-21T10:00:00+08:00`)
- **Idempotency**: Use unique LB names; see [Idempotency Guidance](#idempotency-guidance)

### JSON Path Reference (common)

| Path | Description | Example |
|------|-------------|---------|
| `$.Response.LoadBalancerIds[0]` | LB ID (CreateLoadBalancer) | `lb-12345678` |
| `$.Response.ListenerIds[0]` | Listener ID (CreateListener) | `lbl-12345678` |
| `$.Response.LoadBalancerSet[0].LoadBalancerId` | LB ID (Describe) | `lb-12345678` |
| `$.Response.LoadBalancerSet[0].Status` | 1=creating, 2=running | `2` |
| `$.Response.LoadBalancerSet[0].LoadBalancerType` | OPEN / Internal | `OPEN` |
| `$.Response.ListenerSet[0].Protocol` | TCP/UDP/HTTP/HTTPS | `HTTPS` |
| `$.Response.Targets[0].HealthStatus` | alive / dead / unknown | `alive` |
| `$.Response.Targets[0].InstanceId` | Backend CVM ID | `ins-12345678` |
| `$.Response.Targets[0].Port` | Backend port | `8080` |

### Expected State Transitions

| Operation | Initial → Target | Poll | Max Wait |
|-----------|------------------|------|----------|
| CreateLoadBalancer | — → `Status=2` | 5s | 300s |
| CreateListener | — → active | 5s | 120s |
| RegisterTargets | — → registered | 5s | 60s |
| DeleteLoadBalancer | any → absent | 5s | 300s |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI + SDK) → Validate → Recover**. Do not skip phases. Detailed CLI/SDK commands live in [references/execution-flows.md](references/execution-flows.md).

> **Anchor note:** Links below use `#N-<slug>` anchors that map to `## N. <Title>` headings in `references/execution-flows.md` (e.g. `#create-loadbalancer`). If you rename a heading there, update the matching anchor here to avoid a silent broken link.

### Quick Triage (diagnostic entry points)

- SLB 5xx / backend health failure / connection failure → [SLB 5xx Fast Diagnosis](references/slb-5xx-diagnosis-optimized.md) (MTTR < 30 min)
- Access log analysis (bandwidth, slow requests, SSL security, client anomaly) → [CLB Log Analysis](references/clb-log-analysis.md)
- Generic troubleshooting → [Troubleshooting Guide](references/troubleshooting.md)

### Capabilities at a Glance

| Operation | Description | Complexity | Risk |
|-----------|-------------|------------|------|
| CreateLoadBalancer | Create LB instance | Medium | Low |
| DescribeLoadBalancers | View LB details | Low | None |
| ModifyLoadBalancerAttributes | Change LB config | Medium | Medium |
| DeleteLoadBalancer | Remove LB | Low | **High — irreversible** |
| CreateListener | Create listener | Medium | Low |
| RegisterTargets | Bind backends | Medium | Medium |
| DescribeTargetHealth | Check backend health | Low | None |

### Create LoadBalancer

**Pre-flight:** SDK present (`pip show tencentcloud-sdk-python-clb`); CLI present (`tccli version`); credentials set; region valid; **VPC exists** (`tccli vpc DescribeVpcs`) else HALT → `qcloud-vpc-ops`.
**Execute:** [execution-flows.md §1](references/execution-flows.md#create-loadbalancer).
**Validate:** read `{{output.loadbalancer_id}}` from `$.Response.LoadBalancerIds[0]`; poll `DescribeLoadBalancers` until `Status=2`.

### Create Listener

**Pre-flight:** LB running (DescribeLoadBalancers); port not conflicting.
**Execute:** [execution-flows.md §3](references/execution-flows.md#create-listener).
**Validate:** capture `{{output.listener_id}}`; verify via `DescribeListeners`.

### Register Targets (Bind Backend Servers)

**Pre-flight:** Listener active; **CVM exists & RUNNING** (delegate `qcloud-cvm-ops`); CVM in same VPC as LB.
**Execute:** [execution-flows.md §4](references/execution-flows.md#register-targets-bind-backend-servers).
**Validate:** `DescribeTargets` + `DescribeTargetHealth`.

### Describe LoadBalancers / Describe Target Health

**Execute:** [execution-flows.md §2](references/execution-flows.md#describe-loadbalancers) / [§5](references/execution-flows.md#describe-target-health).
**Present:** ID/Name/VIP/Status/Type (LB) and InstanceId/Port/HealthStatus (targets) — see JSON Path Reference.

### Delete LoadBalancer (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.loadbalancer_name}}` (`{{user.loadbalancer_id}}`)
- **MUST** warn: all listeners and backend bindings will be removed
- **MUST NOT** proceed without clear user assent
- **Execute:** [execution-flows.md §6](references/execution-flows.md#delete-loadbalancer). **Validate:** poll until empty/404.

### Idempotency Guidance

- **CreateLoadBalancer:** pass a stable `ClientToken` (UUID). On timeout, re-run with same token — returns existing instance instead of duplicating.
- **RegisterTargets:** partial success possible — always `DescribeTargetHealth` and diff against requested set; flag non-`RUNNING` targets.
- **DeregisterTargets:** idempotent — re-deregistering a removed target succeeds; no pre-check needed for retries.

## Failure Recovery

| Error pattern | Max retries | Agent Action |
|--------------|-------------|--------------|
| `InvalidParameter.LBIdNotFound` / `ListenerIdNotFound` | 0 | HALT — verify ID |
| `ResourceInsufficient` | 0 | HALT — contact administrator |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | HALT — check credentials |
| `RequestLimitExceeded` | 3 | Exponential backoff, retry |
| `InternalError` | 3 | Retry (2s/4s/8s), then HALT |
| `FailedOperation.ResourceInOperating` | 3 | Wait 30s, retry |

> Full CLB error taxonomy (parameter / status / auth / resource codes) in [references/error-reference.md](references/error-reference.md).

## Safety Gates (Destructive Operations)

Every **Delete**, **Deregister**, or **irreversible** operation MUST have: (1) explicit user confirmation with resource ID shown, (2) warning about dependent resources (listeners, backend bindings), (3) post-op verification (poll until 404/deleted). See also GCL rules below for `DeleteListeners` / batch `DeregisterTargets` / Internet↔Internal flip.

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate is a **runtime** scoring layer auditing each CLB execution against a rubric, in addition to the build-time Safety Gates and 2-round self-review in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (AGENTS.md §8 default) |
| Rubric | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CLB-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop? | Why |
|---|---|---|
| Destructive: `DeleteLoadBalancers`, `DeleteListeners`, batch `DeregisterTargets` (>50%) | **yes** | Irreversible; live-traffic cut |
| Sensitive mutating: `ModifyLoadBalancerAttributes` (Internet↔Internal), `ModifyListener`, `ModifyRule` | **yes** | Config drift / security risk |
| Mutating: `CreateLoadBalancer`, `CreateListener`, `RegisterTargets`, `CreateRule`, `ModifyTargetPort/Weight` | **yes** | Cost / state-change risk |
| Read-only: `Describe*` / `DescribeTaskStatus` | optional (max_iter=1) | Polling tail of parent op |

### Decision flow (first match wins)

1. **Safety = 0** or rule violation in `{1..5}` ⇒ **ABORT**. Internet↔Internal flip w/o diff ⇒ ABORT. Mass deregister w/o drain ⇒ ABORT.
2. `current_iter >= max_iterations` ⇒ return best-so-far + unresolved items.
3. All thresholds met ⇒ **PASS**.
4. Otherwise ⇒ **RETRY** with Critic suggestions.

### CLB-specific safety rules (rubric §4)

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteLoadBalancers` | LB ID + Name echo + confirmation + listener/target dependency check |
| 2 | `DeleteListeners` | Listener ID + protocol + port echoed; "traffic on port X will be cut" warning |
| 3 | `DeregisterTargets` (batch > 50%) | DRAIN guard: `ConnectionDrainTimeout` ≥ 30s required |
| 4 | `ModifyLoadBalancerAttributes` (Internet↔Internal) | Show BEFORE/AFTER type/IP/InternetAccessible; warn public↔private flip |
| 5 | `RegisterTargets` | Reject `InstanceState ≠ RUNNING`; reject targets in different VPC |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**. Full rules: [`references/rubric.md`](references/rubric.md) §4; worked examples §6.

## Reference Directory

- **Core:** [Core Concepts](references/core-concepts.md) · [API & SDK Usage](references/api-sdk-usage.md) · [CLI Usage](references/cli-usage.md) · [Troubleshooting](references/troubleshooting.md) · [SLB 5xx Fast Diagnosis](references/slb-5xx-diagnosis-optimized.md) · [Monitoring & Alerts](references/monitoring.md) · [Integration](references/integration.md)
- **Framework:** [Well-Architected Assessment](references/well-architected-assessment.md) · [AIOps Best Practices](references/aiops-best-practices.md) · [FinOps Cost Optimization](references/finops-cost-optimization.md) · [SecOps Security Operations](references/secops-security-operations.md)
- **Execution detail:** [Execution Flows](references/execution-flows.md) · [Error Reference](references/error-reference.md)
- **Assets:** [Example Config](assets/example-config.yaml) · [Eval Queries](assets/eval_queries.json)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial CLB skill with dual-path CLI/SDK support |
| 1.1.0 | 2026-06-04 | GCL rollout: `## Quality Gate (GCL)`, `references/rubric.md`, `references/prompt-templates.md` |
| 1.2.0 | 2026-07-04 | SLB 5xx fast diagnosis: `references/slb-5xx-diagnosis-optimized.md`, quick 5xx triage, Quick Diagnosis Scenarios table |
| 1.2.1 | 2026-07-06 | AIOps fixes: duplicate `--Region` flags, hardcoded pricing, retry guidance, idempotency note |
| 1.3.0 | 2026-07-09 | SKILL.md consolidation: removed duplicate Quick Start / Prerequisites / Output Schema / error-code tables (moved to new `references/error-reference.md`); merged Capabilities into Execution Flows; added Quick Triage entry points; reduced 549 → 276 lines while preserving all operational info |

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
