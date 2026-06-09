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
  version: "1.1.0"
  last_updated: "2026-06-04"
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

CLB (Cloud Load Balancer, 负载均衡) provides security-focused traffic distribution services. Access traffic is automatically distributed across multiple backend servers, enhancing system capacity and eliminating single points of failure. Supports billion-level connections and ten-million concurrent requests. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CLB. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Use them as a design checklist:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (CLB, 负载均衡) and delegation rules (VPC → qcloud-vpc-ops, CVM → qcloud-cvm-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 CLB-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CLB), primary resource model (LoadBalancer); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, health checks, backend server redundancy, cross-region binding | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSL/HTTPS certificates, security group rules, DDoS protection | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance type comparison (shared vs dedicated), pay-as-you-go vs prepaid, idle LB detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Listener batch operations, target group management, automation via target groups | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CLB" OR "负载均衡" OR "Load Balancer" OR "LB" OR "腾讯云负载均衡"
- Task involves CRUD or lifecycle operations on **LoadBalancer instances** (CreateLoadBalancer, DescribeLoadBalancers, ModifyLoadBalancerAttributes, DeleteLoadBalancer)
- Task involves **Listeners** (TCP/UDP/HTTP/HTTPS) (CreateListener, DescribeListeners, ModifyListener, DeleteListener)
- Task involves **Backend Servers/Targets** (RegisterTargets, DeregisterTargets, DescribeTargetHealth, ModifyTargetWeight)
- Task involves **Target Groups** (CreateTargetGroup, DescribeTargetGroups, RegisterTargetGroupInstances)
- Task involves **CLB access log analysis via CLS** — bandwidth cost, error diagnosis, slow request analysis, traffic pattern, SSL security, client anomaly detection (see `references/clb-log-analysis.md`)
- Task keywords: traffic distribution, load balancing, listener, backend server, health check, SSL certificate, VIP, cross-region, Anycast
- User asks to deploy, configure, troubleshoot, or monitor CLB **via API, SDK, CLI, or automation**
- User describes traffic issues (connection failures, backend health problems, SSL errors) without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **CVM instance management** → delegate to: `qcloud-cvm-ops`
- Task is **SSL certificate management only** → delegate to: `qcloud-ssl-ops` (when present)
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- CLB depends on VPC: verify VPC/Subnet exist via `qcloud-vpc-ops` before CreateLoadBalancer
- CLB backend servers are CVM instances: use `qcloud-cvm-ops` to verify instance existence and status before RegisterTargets
- SSL certificates for HTTPS listeners: verify certificate exists via SSL service or CAM
- CLB access log analysis (FinOps/AiOps): delegate to `qcloud-cls-ops` for CLS log search and aggregation queries; reference `clb-log-analysis.md` for query templates
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

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
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.vip}}` | User-supplied VIP address | Ask once; reuse for operations |
| `{{user.loadbalancer_id}}` | User-supplied LB ID (lb-xxx) | Ask once; reuse for subsequent ops |
| `{{user.loadbalancer_name}}` | User-supplied LB name | Ask once; reuse |
| `{{user.listener_id}}` | User-supplied listener ID | Ask once; reuse |
| `{{user.listener_protocol}}` | Listener protocol | Ask once; options: TCP/UDP/HTTP/HTTPS |
| `{{user.listener_port}}` | Listener port | Ask once; default based on protocol |
| `{{user.instance_id}}` | Backend CVM instance ID | Ask once; delegate to qcloud-cvm-ops to verify |
| `{{user.target_port}}` | Backend server port | Ask once; reuse |
| `{{user.target_weight}}` | Backend server weight | Ask once; default 10 |
| `{{output.loadbalancer_id}}` | From CreateLoadBalancer response | Parse `$.Response.LoadBalancerIds[0]` |
| `{{output.listener_id}}` | From CreateListener response | Parse `$.Response.ListenerIds[0]` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions (Agent-Readable)

- **API spec is canonical**: https://cloud.tencent.com/document/api/214
- **Errors**: Tencent Cloud uses `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: ISO 8601 format (e.g., `2026-05-21T10:00:00+08:00`)
- **Idempotency**: Use unique names for LoadBalancer to avoid conflicts

### JSON Path Reference

Common paths used across operations:

| Path | Description | Example Value |
|------|-------------|---------------|
| `$.Response.LoadBalancerIds[0]` | LB instance ID (CreateLoadBalancer) | `lb-12345678` |
| `$.Response.ListenerIds[0]` | Listener ID (CreateListener) | `lbl-12345678` |
| `$.Response.LoadBalancerSet[0].LoadBalancerId` | LB instance ID (DescribeLoadBalancers) | `lb-12345678` |
| `$.Response.LoadBalancerSet[0].LoadBalancerName` | LB name | `prod-api-lb` |
| `$.Response.LoadBalancerSet[0].Status` | Status: 1=creating, 2=running | `2` |
| `$.Response.LoadBalancerSet[0].LoadBalancerType` | Type: OPEN/Internal | `OPEN` |
| `$.Response.ListenerSet[0].ListenerId` | Listener ID | `lbl-12345678` |
| `$.Response.ListenerSet[0].Protocol` | Protocol: TCP/UDP/HTTP/HTTPS | `HTTPS` |
| `$.Response.Targets[0].HealthStatus` | Health: alive/dead/unknown | `alive` |
| `$.Response.Targets[0].InstanceId` | Backend CVM ID | `ins-12345678` |
| `$.Response.Targets[0].Port` | Backend port | `8080` |
| `$.Response.RequestId` | Request tracking ID | `abc123def-456g-789h` |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateLoadBalancer | — | `Status=2` (running) | 5s | 300s |
| CreateListener | — | Listener active | 5s | 120s |
| RegisterTargets | — | Backend registered | 5s | 60s |
| DeleteLoadBalancer | any | absent (404/empty) | 5s | 300s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, troubleshoot, and monitor CLB (Load Balancer) resources on Tencent Cloud using the `tccli` CLI (primary) or `tencentcloud-sdk-python-clb` SDK (fallback).

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
# Check CLI and credentials
tccli clb DescribeLoadBalancers --Region ap-guangzhou
```

### Your First Command
```bash
# List load balancers
tccli clb DescribeLoadBalancers --Region {{env.TENCENTCLOUD_REGION}}
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand CLB architecture
- [Common Operations](#execution-flows) — Create, manage, and delete load balancers
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateLoadBalancer | Create a new load balancer instance | Medium | Low |
| DescribeLoadBalancers | View LB instance details | Low | None |
| ModifyLoadBalancerAttributes | Change LB configuration | Medium | Medium |
| DeleteLoadBalancer | Remove a load balancer | Low | **High** — irreversible |
| CreateListener | Create a listener (TCP/UDP/HTTP/HTTPS) | Medium | Low |
| RegisterTargets | Bind backend servers to listener | Medium | Medium |
| DescribeTargetHealth | Check backend server health | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial CLB skill with dual-path CLI/SDK support |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CLB-specific safety rules incl. listener-delete traffic cut, mass-deregister drain, Internet↔Internal flip guard), `references/prompt-templates.md` (Generator + Critic + Orchestrator, isolated-context enforcement). `max_iter=2` per AGENTS.md §8 |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**. Do not skip phases.

### Operation: Create LoadBalancer

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python-clb` | Version ≥ minimum | Document install |
| CLI | `tccli version` | Exit code 0 | Document CLI install |
| Credentials | Check env vars: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY` | Non-empty values | HALT; user configures env |
| Region | Valid region code | `{{env.TENCENTCLOUD_REGION}}` valid | Suggest valid region |
| VPC exists | `tccli vpc DescribeVpcs` | Target VPC exists | HALT; delegate to qcloud-vpc-ops |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# CLI call (JSON output by default)
tccli clb CreateLoadBalancer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerType "OPEN" \
  --VpcId "{{user.vpc_id}}" \
  --LoadBalancerName "{{user.loadbalancer_name}}"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""
SDK fallback script for CLB CreateLoadBalancer
"""
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        
        req = models.CreateLoadBalancerRequest()
        req.LoadBalancerType = "OPEN"
        req.VpcId = "{{user.vpc_id}}"
        req.LoadBalancerName = "{{user.loadbalancer_name}}"
        
        resp = client.CreateLoadBalancer(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Read `{{output.loadbalancer_id}}` from `$.Response.LoadBalancerIds[0]`
2. Poll DescribeLoadBalancers until `Status=2`:

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"{{output.loadbalancer_id}}\"]" | jq -r '.Response.LoadBalancerSet[0].Status')
  [ "$STATUS" = "2" ] && break
  sleep 5
done
```

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `InvalidParameter.LBIdNotFound` | 0 | — | HALT | `[ERROR] LoadBalancer ID not found - verify ID and retry` |
| `ResourceInsufficient` | 0 | — | HALT | `[ERROR] Resource quota exceeded - contact administrator` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credentials invalid - check TENCENTCLOUD_SECRET_ID/KEY` |
| `RequestLimitExceeded` | 3 | exponential | Back off and retry | `⚠️ Rate limit reached - retrying with backoff...` |
| `InternalError` | 3 | 2s, 4s, 8s | Retry then HALT | `[ERROR] Internal server error - retrying...` |
| `FailedOperation.ResourceInOperating` | 3 | 30s | Wait and retry | `⚠️ Resource busy - waiting 30s before retry...` |

### Operation: Describe LoadBalancers

#### Execution

```bash
# CLI — JSON output (default)
tccli clb DescribeLoadBalancers --Region {{env.TENCENTCLOUD_REGION}} --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]"
```

#### Present to User

| Field | Notes |
|-------|-------|
| ID | See JSON Path Reference: `$.Response.LoadBalancerSet[0].LoadBalancerId` |
| Name | See JSON Path Reference: `$.Response.LoadBalancerSet[0].LoadBalancerName` |
| VIP | `$.Response.LoadBalancerSet[0].VipIps[0]` |
| Status | See JSON Path Reference: `$.Response.LoadBalancerSet[0].Status` |
| Type | See JSON Path Reference: `$.Response.LoadBalancerSet[0].LoadBalancerType` |

### Operation: Create Listener

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| LoadBalancer exists | DescribeLoadBalancers | LB in running state | HALT |
| Port not conflict | Check existing listeners | Port available | HALT; suggest different port |

#### Execution — CLI

```bash
tccli clb CreateListener \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Protocol "{{user.listener_protocol}}" \
  --Port "{{user.listener_port}}" \
  --ListenerName "{{user.listener_name}}"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateListenerRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"
        req.Protocol = "{{user.listener_protocol}}"
        req.Port = {{user.listener_port}}
        req.ListenerName = "{{user.listener_name}}"

        resp = client.CreateListener(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.listener_id}}` from `$.Response.ListenerIds[0]`
2. Verify listener via DescribeListeners

### Operation: Register Targets (Bind Backend Servers)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Listener exists | DescribeListeners | Listener active | HALT |
| CVM instance exists | Delegate to qcloud-cvm-ops | Instance RUNNING | HALT |
| CVM in same VPC | DescribeInstances | Same VPC as LB | HALT; VPC mismatch |

#### Execution — CLI

```bash
tccli clb RegisterTargets \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --ListenerId "{{user.listener_id}}" \
  --Targets "[\"InstanceId\":\"{{user.instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":{{user.target_weight}}}]"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.RegisterTargetsRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"
        req.ListenerId = "{{user.listener_id}}"

        target = models.Target()
        target.InstanceId = "{{user.instance_id}}"
        target.Port = {{user.target_port}}
        target.Weight = {{user.target_weight}}
        req.Targets = [target]

        resp = client.RegisterTargets(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Verify backend registered via DescribeTargets
2. Check health status via DescribeTargetHealth

### Operation: Describe Target Health

#### Execution — CLI

```bash
tccli clb DescribeTargetHealth \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.DescribeTargetHealthRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"

        resp = client.DescribeTargetHealth(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Present to User

| Field | Notes |
|-------|-------|
| InstanceId | See JSON Path Reference: `$.Response.Targets[0].InstanceId` |
| Port | See JSON Path Reference: `$.Response.Targets[0].Port` |
| HealthStatus | See JSON Path Reference: `$.Response.Targets[0].HealthStatus` |

### Operation: Delete LoadBalancer

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.loadbalancer_name}}` (`{{user.loadbalancer_id}}`)
- **MUST** warn about: all listeners and backend bindings will be removed
- **MUST NOT** proceed without clear user assent

#### Execution

```bash
# Delete with confirmation
tccli clb DeleteLoadBalancer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}"
```

#### Post-execution Validation

Poll DescribeLoadBalancers until LB returns empty or 404.

---

## Prerequisites

1. **Install `tccli` CLI** (primary execution path):

   ```bash
   pip install tccli
   ```

2. **Bootstrap Python runtime** (for SDK fallback):

   ```bash
   python3 --version  # Should be ≥ 3.8
   pip install tencentcloud-sdk-python-clb
   ```

3. **Configure Credentials**:

   ```bash
   export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
   export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
   export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
   ```

4. **Verify Configuration**:
   ```bash
   tccli clb DescribeLoadBalancers --Region ap-guangzhou
   ```

## Reference Directory

### Core Documentation
- [Core Concepts](references/core-concepts.md) — CLB architecture and components
- [API & SDK Usage](references/api-sdk-usage.md) — API operation map and Python SDK
- [CLI Usage](references/cli-usage.md) — `tccli clb` commands
- [Troubleshooting Guide](references/troubleshooting.md) — Common issues and solutions
- [Monitoring & Alerts](references/monitoring.md) — CLB metrics (QCE/LB_PUBLIC namespace)
- [Integration](references/integration.md) — Cross-skill integration and setup

### Framework Integration
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar framework (Reliability, Security, Cost, Efficiency)
- [AIOps Best Practices](references/aiops-best-practices.md) — Multi-metric correlation, diagnosis tree, proactive inspection
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — Billing models, idle detection, right-sizing
- [SecOps Security Operations](references/secops-security-operations.md) — CAM policies, SSL security, network isolation

### Assets
- [Example Configuration](assets/example-config.yaml) — Sample config with UX and optimization settings
- [Evaluation Queries](assets/eval_queries.json) — Trigger accuracy test queries

## Error Code Reference

### Parameter Validation Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.LBIdNotFound` | LoadBalancer ID invalid | Verify LB ID; suggest `DescribeLoadBalancers` |
| `InvalidParameter.ListenerIdNotFound` | Listener ID invalid | Verify listener ID |
| `InvalidParameter.LocationNotFound` | Forwarding rule not found | Verify rule location/URL |
| `InvalidParameter.PortCheckFailed` | Port conflict or invalid | Use different port |
| `InvalidParameter.ProtocolCheckFailed` | Protocol mismatch | Check protocol support per CLB type |
| `InvalidParameter.RegionNotFound` | Region invalid | Verify region is correct |
| `InvalidParameter.FormatError` | Parameter format error | Check parameter format per API spec |
| `InvalidParameter.InvalidFilter` | Query filter error | Fix filter parameter structure |
| `InvalidParameter.RewriteAlreadyExist` | Rewrite rule already exists | Use different source URL |
| `InvalidParameter.SomeRewriteNotFound` | Some rewrite rules not found | Verify rewrite rule IDs |
| `InvalidParameter.ClientTokenLimitExceeded` | ClientToken expired | Generate new ClientToken |
| `InvalidParameterValue.Duplicate` | Duplicate parameter value | Use unique values |
| `InvalidParameterValue.InvalidFilter` | Filter input error | Fix filter name/values |
| `InvalidParameterValue.Length` | Parameter length error | Shorten parameter value |
| `InvalidParameterValue.Range` | Parameter range error | Adjust value to valid range |

### CLB Status & Operation Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `FailedOperation.InvalidLBStatus` | LB status abnormal | Wait for LB to stabilize; check `DescribeLoadBalancers` |
| `FailedOperation.ResourceInOperating` | Resource being operated | Wait 30s; retry |
| `FailedOperation.ResourceInCloning` | Resource being cloned | Wait for clone to complete |
| `FailedOperation.NoListenerInLB` | No listener for operation | Create listener first |
| `FailedOperation.EipTrafficCheckRisk` | EIP bandwidth exceeds threshold | Disable anti-misoperation in EIP console |
| `FailedOperation.FrequencyCheckRisk` | Delete frequency too high | Slow down delete rate |
| `FailedOperation.TargetNumCheckRisk` | Rule count risk too high | Pass `ForceDelete=true` |
| `FailedOperation.TrafficCheckRisk` | Traffic check high risk | Confirm force delete with `ForceDelete=true` |

### Auth & Resource Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `AuthFailure` | CAM signature/auth error | Check CAM policies for CLB |
| `OperationDenied` | Operation denied | Check account permissions |
| `ResourcesSoldOut` | Resources sold out | Try different region or specification |
| `InternalError` | Internal server error | Transient — retry; escalate if persists |

## Safety Gates (Destructive Operations)

Every **Delete**, **Deregister**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Warning about dependent resources** (listeners, backend bindings)
3. **Post-delete verification** (poll until 404 or deleted state)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CLB execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-clb-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CLB-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteLoadBalancers`, `DeleteListeners`, `DeregisterTargets` (batch > 50%) | **yes** | Irreversible; live-traffic cut; needs scoring |
| Sensitive mutating: `ModifyLoadBalancerAttributes` (Internet↔Internal flip), `ModifyListener` (protocol/port), `ModifyRule` (production domain/URL) | **yes** | Configuration drift / security risk; needs scoring |
| Mutating: `CreateLoadBalancer`, `CreateListener`, `RegisterTargets`, `CreateRule`, `ModifyTargetPort`, `ModifyTargetWeight` | **yes** | Cost / state-change risk; needs scoring |
| Read-only: `DescribeLoadBalancers`, `DescribeListeners`, `DescribeTargets`, `DescribeTaskStatus` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR any rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Internet↔Internal flip without diff ⇒ ABORT. Mass deregister without drain ⇒ ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### CLB-specific safety rules (rubric §4)

1. `DeleteLoadBalancers` (any) — LB ID + Name echo; listener / target-binding / replication dependency check; `--DryRun` for batch; warn atomicity
2. `DeleteListeners` (single or batch) — listener ID + protocol + port echoed; "traffic on port X cut immediately"; HTTPS cert detachment warning; rules count
3. `DeregisterTargets` batch > 50% — DRAIN guard: require `ConnectionDrainTimeout ≥ 30s`; surface `CurrConnections`; recurse-confirm
4. `ModifyLoadBalancerAttributes` switching Internet↔Internal — BEFORE/AFTER diff (type / IP version / accessibility); warn public IP release/acquisition; recurse-confirm
5. `RegisterTargets` (any) — verify each target `InstanceState == RUNNING`; reject cross-VPC without peer; surface weight=0 as hidden config error

### Sibling — CVM / CDB / COS / CLB Quality Gates

| Skill | §4 Distinctive rules |
|---|---|
| `qcloud-cvm-ops` | instances, disks, re-image |
| `qcloud-cdb-ops` | accounts, privileges, SQL data-plane boundary |
| `qcloud-cos-ops` | versioning, public ACL, cold transition, batch delete |
| `qcloud-clb-ops` (this) | listener traffic-cut, mass drain, direction flip, non-running target reject |

See [`references/rubric.md`](references/rubric.md) §6 for worked examples.

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "LoadBalancerIds": ["lb-xxx"],
    // Product-specific fields
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter.LBIdNotFound",
      "Message": "LoadBalancer instance ID error"
    }
  }
}
```