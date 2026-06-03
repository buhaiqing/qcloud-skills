---
name: qcloud-well-architected-review
description: >-
  Use when the user needs to review, audit, or assess Tencent Cloud architecture
  against the Well-Architected Framework — reliability assessment (backup/recovery,
  DR runbook, multi-AZ), security audit (CAM permissions, credential management,
  network isolation), cost optimization (idle resource detection, right-sizing),
  or efficiency improvement (batch operations, automation). Also triggers on
  architecture review requests, compliance checks, or performance/cost analysis
  for any Tencent Cloud product including CVM, CDB, Redis, ES, TKE, CLB, VPC, COS, CDN.
  Not for live API execution against cloud resources unless paired with a
  product-specific ops skill.
license: MIT
type: cross-cutting-assessment
compatibility:
  - tccli >= 3.0
  - python >= 3.8
  - tencentcloud-api-credentials
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  tags:
    - tencent-cloud
    - well-architected
    - assessment
    - architecture-review
  requirements:
    - tccli
    - jq
  python_version_minimum: "3.8"
  api_profile: "Tencent Cloud Well-Architected Framework (multi-product)"
  cli_applicability: "cli-only"
  cli_support_evidence: >-
    Assessment uses Describe* operations across all Tencent Cloud products
    via `tccli` for resource enumeration, configuration review, and
    compliance verification. No write operations performed.
  related_skills:
    - qcloud-finops-ops   # 反向：架构评估的成本优化维度可与 finops 协同（well-architected 提供 TCO 视角，finops 提供实时账单）
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud Well-Architected Review Skill

## Overview

This skill provides a **four-pillar architecture assessment framework** for Tencent Cloud resources, adapted from Tencent Cloud's Well-Architected Framework. It operates independently for ad-hoc architecture reviews, or as a **delegated target** from product-specific ops skills (qcloud-cvm-ops, qcloud-redis-ops, qcloud-tke-ops, etc.) for cross-cutting architectural concerns.

**Four Pillars:**
1. **可靠性 (Reliability)** — Backup/recovery, DR, multi-AZ, health checks, safety gates
2. **安全性 (Security)** — CAM permissions, credential management, network isolation, encryption
3. **成本 (Cost)** — Billing models, idle resource detection, right-sizing, optimization
4. **效率 (Efficiency)** — Batch operations, automation, resource scheduling, API optimization

### Core Principle

Every assessment follows the **Discover → Evaluate → Report → Recommend** loop:
1. Discover resources and their current configuration
2. Evaluate against four-pillar checklists
3. Generate structured assessment report
4. Provide actionable, prioritized recommendations

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User asks "帮我看看当前架构是否有问题" or "do an architecture review"
- User requests security audit: "检查下权限配置是否安全"
- User wants cost analysis: "帮我分析下云资源成本浪费"
- User asks for reliability assessment: "有没有单点故障风险"
- User requests optimization: "帮我优化资源配置"
- Product-specific skill delegates to this skill for architecture review
- Compliance audit or pre-production review is needed

### SHOULD NOT Use This Skill When
- User needs live resource CRUD operations → delegate to product-specific ops skill
- User asks about billing/账单查询/费用明细/成本分摊 → delegate to `qcloud-finops-ops`
- 协同场景：`qcloud-finops-ops` 提供实时账单数据，本 skill 的成本优化评估可结合该数据生成 TCO 指标；本 skill 架构评估发现的高成本架构模式可反馈给 finops 持续监控
- User needs VPC/CLB/CAM configuration changes → delegate to qcloud-vpc-ops, qcloud-clb-ops, qcloud-cam-ops

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.product}}` | User | Product to assess (CVM, Redis, TKE, etc.) | `cvm` |
| `{{user.scope}}` | User | Assessment scope (single-resource, account-wide) | `account-wide` |
| `{{user.pillars}}` | User | Which pillars to assess (all, reliability, security, cost, efficiency) | `all` |
| `{{output.resource_list}}` | API Response | Discovered resources for assessment | JSON array |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers, delegation rules to product skills |
| 2 | **Structured I/O** | `{{env.*}}`/`{{user.*}}`/`{{output.*}}` conventions, type and source documented |
| 3 | **Explicit Actionable Steps** | Each pillar: Discover → Evaluate → Score → Recommend |
| 4 | **Complete Failure Strategies** | API rate limit handling, credential validation, region fallback |
| 5 | **Absolute Single Responsibility** | One skill = architecture assessment only; no resource mutations |

## Assessment Workflow

### Step 1: Discover Resources

```bash
# Discover all CVM instances in region
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100

# Discover all Redis instances
tccli redis DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100

# Discover all TKE clusters
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --Limit 100

# Discover all CDB instances
tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100
```

### Step 2: Evaluate Per Pillar

For each discovered resource, apply the pillar-specific checklist from the corresponding reference file.

### Step 3: Score & Report

Generate structured assessment report with:
- Overall score per pillar (0-100)
- Per-resource findings (pass/fail/warning)
- Prioritized recommendations

### Step 4: Recommend

Map findings to actionable items with:
- Severity (Critical/High/Medium/Low)
- Effort estimate (quick fix / medium / major change)
- Documentation links

## Overall Architecture Score

Calculate the weighted overall architecture score from four pillar scores:

```
overall_score = (reliability * 0.30) + (security * 0.30) + (cost * 0.20) + (efficiency * 0.20)
```

| Pillar | Weight | Why |
|--------|--------|-----|
| Reliability | 30% | Foundation of any architecture |
| Security | 30% | Critical for compliance and trust |
| Cost | 20% | Important but secondary to stability |
| Efficiency | 20% | Optimization after fundamentals |

### Score Interpretation

| Overall Score | Rating | Action |
|---------------|--------|--------|
| 90-100 | Excellent | Architecture is well-optimized |
| 80-89 | Good | Minor improvements recommended |
| 70-79 | Fair | Significant issues to address |
| 60-69 | Poor | Major architectural changes needed |
| < 60 | Critical | Immediate remediation required |

### Priority When Pillars Conflict

When recommendations from different pillars conflict:
1. **Security > Reliability > Cost > Efficiency**
2. Security issues are always prioritized
3. Reliability issues take precedence over cost optimization

## Delegation Matrix

| Source Skill | Delegates To | Trigger |
|-------------|-------------|---------|
| qcloud-cvm-ops | qcloud-well-architected-review | Architecture review requested |
| qcloud-redis-ops | qcloud-well-architected-review | Security/cost assessment |
| qcloud-tke-ops | qcloud-well-architected-review | Reliability/efficiency review |
| qcloud-cdb-ops | qcloud-well-architected-review | Full architecture audit |
| qcloud-clb-ops | qcloud-well-architected-review | Multi-product review |
| qcloud-vpc-ops | qcloud-well-architected-review | Network security audit |
| qcloud-cos-ops | qcloud-well-architected-review | Storage optimization review |
| qcloud-monitor-ops | qcloud-well-architected-review | Monitoring coverage review |

## Anti-Patterns

| Anti-Pattern | How It Manifests | Correction |
|-------------|-----------------|------------|
| Review without discovery | Making assumptions about resources | Always run Describe* first |
| Vague scores | Saying "looks good" without metrics | Use structured scoring per pillar |
| Missing recommendations | Listing problems without solutions | Every finding must have actionable fix |
| Over-assessing | Reviewing everything when user only asked for cost | Honor user scope preference |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — 4-pillar assessment (Reliability, Security, Cost, Efficiency), delegation matrix |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 rules: scope clarity, read-only collection, confidence disclosure, cross-pillar consistency, delegation matrix respect), `references/prompt-templates.md`. `max_iter=5` per AGENTS.md §8 |

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **5** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 rules (advisory skill) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Safety rules (rubric §4)

1. **Scope clarity** — surface assessment scope; mark skipped pillars as "NOT ASSESSED"
2. **Read-only collection** — no mutations; confirm read-only delegation
3. **No false certainty** — surface confidence; caveat for incomplete data
4. **Cross-pillar consistency** — surface conflicting recommendations; flag trade-offs
5. **Delegation matrix respect** — reject out-of-matrix skills; recommend re-run after addition

**Advisory/read-only skill.** No hard ABORT on Safety=0 (no destructive ops).

---

For pillar-specific detailed checklists, see:
- [Reliability Pillar](references/reliability-pillar.md) — Backup/recovery, DR, multi-AZ
- [Security Pillar](references/security-pillar.md) — CAM, credentials, encryption
- [Cost Pillar](references/cost-pillar.md) — Billing, idle detection, right-sizing
- [Efficiency Pillar](references/efficiency-pillar.md) — Batch ops, automation, scheduling
