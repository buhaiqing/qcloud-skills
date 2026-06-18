---
name: qcloud-skill-generator
description: >-
  Use when the user needs to create or update a Tencent Cloud Agent Skill
  (`qcloud-*-ops`) in this repository — even if they don't explicitly ask for
  scaffolding or generation. Triggers include: user wants to "add a skill for
  product X", "regenerate from API spec", or "fix gaps found during review".
  Also use when an existing skill needs realignment after API doc changes or
  fails a governance/adversarial review. Not for executing live changes against
  cloud accounts or for one-off debugging with no intent to maintain.
license: MIT
compatibility: >-
  Access to Tencent Cloud official documentation, API spec for the product,
  `qcloud-skill-generator/references/qcloud-skill-template.md`,
  `references/evaluation-driven-workflow.md`,
  `references/governance-and-adversarial-review.md` (when present),
  `references/prompt-library.md` (structured prompt repository),
  `references/optimization-analysis.md` (three-dimensional optimization framework),
  `references/user-experience-spec.md` (mandatory UX requirements for generated skills),
  `references/execution-environment.md` (CLI + Python SDK setup details),
  `references/cli-behavior.md` (verified tccli CLI behavioral notes),
  and agentskills.io frontmatter conventions.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: meta-skill
  guidance_freedom_level: medium
  python_version_minimum: "3.8"
  sdk_package: "tencentcloud-sdk-python"
---

# Tencent Cloud Skill Generator (Meta-Skill)

## Quick Start

### What This Skill Does
Scaffolds new or updates existing `qcloud-[product]-ops` skills in this repository, based on official Tencent Cloud API specs. This is a **meta-skill** — it generates runbooks for agents, not operational execution against cloud accounts.

### Prerequisites
- [ ] Access to API spec for the target Tencent Cloud product
- [ ] Read access to this repository's template files
- [ ] Network access to Tencent Cloud documentation URLs

### Your First Generation
```
Input: "Generate qcloud-cvm-ops for CVM instances, CBS disks, and snapshots"
Output: qcloud-cvm-ops/ directory with SKILL.md and references/
```

### Next Steps
- [Generation Workflow](#evaluation-driven-generation-workflow) — Step-by-step generation process
- [Anti-Pattern Checklist](#anti-pattern-checklist) — Common mistakes to avoid
- [P0/P1 Checklist](#p0--must-pass) — Quality gates for generated skills

---

## Overview

This **meta-skill** defines **how** to author a new **product-scoped** operational skill (e.g. `qcloud-cvm-ops`) **inside this repo**. It does **not** perform maintenance against a user's cloud account. Live work uses the generated `qcloud-[product]-ops` skills (official `tccli` CLI with **Python SDK fallback**).

### Guidance Freedom Level: Medium (Provide Templates)

This meta-skill operates at **Medium** guidance level: it provides **templates and frameworks** ([qcloud-skill-template.md](references/qcloud-skill-template.md), prompt library, UX spec) while allowing the agent to adapt based on product-specific context. Low-level scripts (CLI installation, Python SDK setup) are detailed in [references/execution-environment.md](references/execution-environment.md).

### Core Principle

Generated skills are **agent-readable runbooks**: triggers, env vs user placeholders, pre-flight → execute → validate → recover, safety gates, and outputs **grounded in API spec and verified CLI behavior**, not guessed.

### Technology Stack
- **CLI:** `tccli` (Python CLI tool, pip installable) — primary execution path
- **SDK:** `tencentcloud-sdk-python` (official Python SDK) — fallback for CLI edge cases
- **Execution:** Python script execution for SDK fallback

### Repository Scope
All generated layout and policies apply **only** to the `qcloud-skills` monorepo unless explicitly stated elsewhere.

---

## Role Boundary (Agent-Readable)

| This meta-skill **does** | This meta-skill **does not** |
|--------------------------|------------------------------|
| Choose **extend** vs **new** `qcloud-[product]-ops` | Replace deep product knowledge already in an existing ops skill |
| Scaffold `SKILL.md`, `references/*`, `assets/*` from the template | Call Tencent Cloud APIs on behalf of the user |
| Enforce naming, frontmatter, P0/P1, delegation, and **governance** hooks | Invent request/response fields or CLI flags without official doc verification |
| Point authors to **adversarial review** before merge (when governance doc exists) | Store or echo real credentials |

If the user wants **operational execution** (e.g. "create a resource"), load the appropriate `qcloud-*-ops` skill for that product — not this generator.

---

## When to Use / Not Use

### Use When
- A new Tencent Cloud product needs a **first** ops skill in **this repo**
- An existing skill lacks P0 elements (triggers, placeholders, flows, recovery, destructive gates)
- API or official docs changed; the skill should be **realigned** (bump version/changelog)
- A contributor needs the **standard directory layout** for a new `qcloud-[product]-ops`

### Do NOT Use When
- One-off debugging with no intent to maintain a reusable skill
- Non–Tencent-Cloud application work
- You only need billing/CAM execution — use dedicated ops skills when they exist

---

## Input / Output Structure

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product.name` | string | Yes | English product name (e.g., CVM, CBS, MySQL) |
| `product.slug` | string | Yes | CLI product slug (e.g., cvm, cbs, mysql) — verify via `tccli help <slug>` |
| `product.chinese_name` | string | No | Chinese name for trigger matching (e.g., 云服务器) |
| `primary_resource` | string | Yes | Primary resource type (e.g., Instance, Disk, DBInstance) |
| `api_service_id` | string | Yes | API service identifier from API spec or SDK package |
| `api_url` | string | Recommended | API spec URL or path — required for API-accurate fields |
| `operation_list` | string[] | Yes | List of operations (create, describe, modify, delete, list, product-specific) |
| `doc_urls` | string[] | Recommended | Official documentation URLs |
| `cli_support_evidence` | string | Yes | Confirmation that `tccli` exposes this product (or SDK fallback needed) |

### Output

| Artifact | Description | Required When |
|----------|-------------|---------------|
| `qcloud-[product]-ops/SKILL.md` | Main skill runbook — triggers, flows, recovery, safety gates | Always |
| `references/core-concepts.md` | Architecture, limits, regions, quotas, dependency graph, SPOF analysis | Always |
| `references/api-sdk-usage.md` | Operation map, required fields, pagination, request/response snippets | Always |
| `references/cli-usage.md` | `tccli` CLI command map, coverage gap table, invocation patterns | `cli_applicability: cli-first` / `dual-path` / `cli-only` |
| `references/troubleshooting.md` | Error codes (≥ 10), ordered diagnostics, multi-round diagnosis | Always |
| `references/monitoring.md` | Metrics, dashboards, alerts, cost & performance metrics | Product has monitoring metrics |
| `references/integration.md` | SDK setup, env vars, cross-skill delegation matrix | Always |
| `references/well-architected-assessment.md` | Four-pillar assessment: Reliability, Security, Cost, Efficiency (Tencent Cloud framework) | Always |
| `references/enhanced-self-healing-framework.md` | Self-healing patterns for installation flows | Always (referenced) |
| `references/knowledge-base.md` | Fault pattern library for diagnostic skills | AIOps/diagnosis skills |
| `references/observability.md` | Metrics→Logs→Traces linkage | Monitoring/AIOps skills |
| `references/idempotency-checklist.md` | Idempotent behavior for retries/automation | Automation-heavy products |
| `references/rubric.md` | GCL runtime scoring rubric (5 dimensions + product-specific safety rules). Owner for GCL scoring. | GCL `required` / `recommended` per [AGENTS.md §10.8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `references/prompt-templates.md` | GCL Generator/Critic/Orchestrator prompt skeletons; isolated-context enforcement | GCL `required` / `recommended` per [AGENTS.md §10.8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `assets/example-config.yaml` | Example configuration with UX and optimization settings | Always |
| `assets/eval_queries.json` | Trigger accuracy evaluation queries for the generated skill | Always |

> **GCL artifacts (rubric.md, prompt-templates.md)** are **mandatory** when the
> skill is GCL `required` or `recommended` per [AGENTS.md §10.8](../../AGENTS.md#8-per-skill-defaults-qcloud).
> For products with destructive operations (e.g. `TerminateInstances`,
> `DeleteBucket`, `IsolateDBInstance`, `DropDB`), the default is `required` and
> `max_iter=2`. Mirror the existing pilot skills (`qcloud-cvm-ops/references/rubric.md`,
> `qcloud-cvm-ops/references/prompt-templates.md`) and instantiate the **C6**
> Charter check below.

---

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Reference them throughout the generation workflow.

### Standard 1: Clear Boundaries (边界明确)
- **SHOULD use** conditions: precise, with keywords and intent matching
- **SHOULD NOT use** conditions: explicit negative cases that prevent misfire
- **Delegation rules**: clear pointers to related skills

### Standard 2: Structured I/O (输入输出结构化)
- Input parameters defined with types and sources (`{{env.*}}`, `{{user.*}}`)
- Output fields defined with JSON paths from API response schemas
- Placeholder conventions: `{{env.*}}` (from runtime, NEVER ask user), `{{user.*}}` (interactive collect), `{{output.*}}` (from API response)

### Standard 3: Explicit Actionable Steps (步骤明确可执行)
- Every operation: Pre-flight → Execute → Validate → Recover
- Steps are numbered, imperative, specific — not descriptive summaries
- CLI and SDK paths documented separately when both apply

### Standard 4: Complete Failure Strategies (失败策略完备)
- Error taxonomy with product-specific error codes (≥ 10)
- Each error pattern: max retries, backoff strategy, agent action, UX feedback
- HALT vs retry distinction; credential, quota, and business errors clearly separated

### Standard 5: Absolute Single Responsibility (职责绝对单一)
- One skill = one product = one primary resource model
- Cross-product delegation: document in Trigger & Scope, do NOT duplicate full flows
- Naming: `qcloud-[product]-ops` (lowercase, hyphenated)

---

## Post-Generation Self-Check (生成后自检 — 宪章执行)

> **机制：生成完成后自动执行，不符合则循环修复直到通过。**
> **参考：** `references/governance-and-adversarial-review.md` §0 Charter

### Self-Check Flowchart

```
生成完成 → 执行宪章检查 (C1-C6)
  ↓
C1-C6 全通过？
  ↓ YES          ↓ NO
报告成功    → HALT + 报告违规项
  ↓              ↓
结束        → 自动修复（填充模板内容）
                 ↓
              → 重新执行宪章检查
                 ↓
              → 循环直到通过
```

### Charter Compliance Checklist (强制执行)

| # | Check | Command | Pass Criteria | Auto-Fix Template |
|---|-------|---------|--------------|-------------------|
| C1 | Frontmatter | `head -3 SKILL.md | grep "^---"` | Starts with `---`, has `name`, `description`, `license`, `compatibility`, `metadata` | Use `qcloud-skill-template.md` frontmatter |
| C2 | SHOULD/SHOULD NOT | `grep -c "SHOULD Use" SKILL.md` | ≥ 1 match for each | Add Trigger & Scope section from template |
| C3 | Five Core Standards | `grep -c "Five Core Standards" SKILL.md` | ≥ 1 match | Add Five Core Standards table from template |
| C4 | Well-Architected | `grep -c "Well-Architected Framework" SKILL.md` | ≥ 1 match | Add Well-Architected Framework table |
| C5 | Variables | `grep -c "^## Variables" SKILL.md` | ≥ 1 match | Add Variables section with `{{env.*}}`/`{{user.*}}`/`{{output.*}}` |
| C6 | Token Efficiency | `grep -c "TE-[1-7]" SKILL.md` | ≥ 1 TE rule applied | Apply Token Efficiency rules per [Token Efficiency Requirements](#token-efficiency-requirements-p0) |
| C7 | **GCL Quality Gate** (when skill is GCL `required`/`recommended`) | `[ -f references/rubric.md ] && [ -f references/prompt-templates.md ] && grep -q "## Quality Gate (GCL)" SKILL.md` | All three checks pass | Scaffold rubric + prompt-templates from `qcloud-cvm-ops/references/{rubric,prompt-templates}.md`; add `## Quality Gate (GCL)` section to SKILL.md per [AGENTS.md §10](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate) |

### Self-Remediation Template (自动修复模板)

当检测到违规时，使用以下模板内容自动填充：

```yaml
# C1: Frontmatter template (填充到文件开头)
---
name: qcloud-[product]-ops
description: >-
  Use when the user needs to [trigger description]...
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`), Python 3.8+ runtime...
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "YYYY-MM-DD"
  runtime: Harness AI Agent, Claude Code, Cursor...
  python_version_minimum: "3.8"
  go_version_minimum: "1.21"
  api_profile: "[API version — doc link]"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    [CLI operation evidence]
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---
```

```markdown
# C2-C5: Missing sections (填充到 Overview 之后)

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- [Product triggers — match template format]

### SHOULD NOT Use This Skill When
- [Negative cases → delegate to other skills]

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.*}}` | User | [interactive placeholders] | ... |
| `{{output.*}}` | API Response | [response capture] | ... |
```

> **原则：自解优先于人工介入。Agent 必须在报告问题前尝试自动修复。**

---

## Token Efficiency Requirements (P0 — 强制)

> **Token Efficiency 原则**：每条 Token 都是成本。LLM 上下文窗口有限，生成技能应尽量减少不必要的内容膨胀。
> **C6 检查**: 生成完成后自动检查 TE-1 至 TE-7 是否落实，不符合则自动修复后重新检查。

### TE-1: 用 API 查询替代硬编码静态数据

**规则**：引擎版本、端口列表、可用区枚举等静态数据，使用 `tccli` 查询而非硬编码表格。

```markdown
# ❌ 硬编码
| Engine | Version | Port |
|--------|---------|------|
| MySQL  | 5.7     | 3306 |
| MySQL  | 8.0     | 3306 |

# ✅ 动态查询
tccli sqlserver DescribeDBInstances --filters '[{"Name":"engine-version","Values":["*"]}]'
```

**预估节省**：~200–500 Token/文件

### TE-2: 省略不必要的 Python docstring

**规则**：生成的 `references/api-sdk-usage.md` 等文件中的 Python 代码示例，用 `#` 行内注释代替函数级 `"""docstring"""`。

```python
# ❌ 函数级 docstring（占用多行）
def describe_instances(region: str) -> dict:
    """查询云服务器实例列表
    Args:
        region: 地域
    Returns:
        实例列表
    """
    ...

# ✅ 函数签名 + 行内注释（紧凑）
def describe_instances(region: str) -> dict:
    # 查询云服务器实例列表
    ...

# 保存模块级别 docstring（描述用途），删除函数级别 docstring
"""CVM 实例操作 — 查询、创建、删除、修改"""
```

**预估节省**：~100–200 Token/函数

### TE-3: 错误表 → 紧凑格式

**规则**：错误码表最多 3 列（`Error Code | Description | Recovery`），去掉冗余的 `Category`、`Retry`、`UX Feedback` 列。

```markdown
# ✅ 紧凑格式（3列）
| Error Code | Description | Recovery |
|------------|-------------|----------|
| InvalidInstance | 实例不存在 | `tccli cvm DescribeInstances --InstanceIds '["ins-xxx"]'` |
| InsufficientBalance | 余额不足 | 充值后再操作 |
| OperationDenied | 操作被拒绝 | 检查 CAM 权限 |
```

**预估节省**：~300–500 Token/文件

### TE-4: JSON paths 集中声明

**规则**：API 响应的 JSON paths 在文件头部集中声明（如 `## Response Fields` 区块），后续操作通过名称引用，不内联重复书写完整路径。

```markdown
# ✅ 集中声明
## Response Fields
| Field | Path | Type | Description |
|-------|------|------|-------------|
| InstanceId | `$.Response.InstanceSet[*].InstanceId` | String | 实例ID |
| InstanceName | `$.Response.InstanceSet[*].InstanceName` | String | 实例名称 |
| CreatedTime | `$.Response.InstanceSet[*].CreatedTime` | String | 创建时间 |

# 后续操作中通过名称引用
> 从 `InstanceName` 字段获取实例名称
```

**预估节省**：~50–100 Token/文件

### TE-5: YAML anchors 消除重复字段

**规则**：`example-config.yaml` 等文件中共享字段使用 `&anchor` / `<<: *anchor` 语法。

```yaml
# ✅ 使用 anchors 消除冗余
x-default-thresholds: &default-thresholds
  high: 90
  medium: 70
  low: 50

thresholds:
  cpu_usage:
    <<: *default-thresholds
  mem_usage:
    high: 90
    medium: 75
    low: 60       # 差异字段覆盖
  disk_usage:
    <<: *default-thresholds
  network_usage:
    <<: *default-thresholds
```

**预估节省**：~200–400 Token/文件

### TE-6: 消除跨文件重复流程

**规则**：Pre-flight → Execute → Validate → Recover 流程仅在 `SKILL.md` 中完整定义，`references/` 和 `assets/` 中不重复相同流程。GCL 的 Generator/Critic/Orchestrator 共享骨架集中在 [`references/gcl-prompt-backbone.md`](references/gcl-prompt-backbone.md)；各 product skill 的 `references/prompt-templates.md` 仅保留 **§5 产品 anti-patterns**（§1–§3 链接 backbone，**§4 安全规则见 `references/rubric.md` §4**，不在 prompt-templates 重复 per-op 表）；维护脚本：`scripts/te6_gcl_compress.py`。

```markdown
# ❌ 重复：execution-environment.md 中再次出现完整流程
## Installation Flow
1. Pre-flight: check Python...
2. Execute: pip install...
3. Validate: tccli --version...
4. Recover: retry with...

# ✅ 单一真相来源：仅在 SKILL.md 定义，引用文件只存唯一内容
references/execution-environment.md → 仅含安装命令和环境变量表
assets/example-config.yaml → 仅含配置字段示例
```

**预估节省**：~200–400 Token/文件

### TE-7: 消除冗余表格描述列

**规则**：表格中的 `Description` 列如果只是重述字段名的含义，则应合并或删除；对字段含义不言自明的行去掉描述。

```markdown
# ❌ Description 列多余（每行都在复述字段名）
| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `region` | env | 地域 | `ap-guangzhou` |
| `zone` | env | 可用区 | `ap-guangzhou-3` |

# ✅ 去掉冗余 Description 列
| Variable | Source | Example |
|----------|--------|---------|
| `region` | env | `ap-guangzhou` |
| `zone` | env | `ap-guangzhou-3` |

# 仅在字段含义不明确时保留 Description
| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `instance_type` | user | 实例规格（需用户指定） | `S5.SMALL1` |
```

**预估节省**：~100–200 Token/文件

### TE 边界 — 不可压缩的内容

| 可压缩 | 不可压缩 |
|--------|----------|
| Docstring、静态表格、重复流程 | Agent 可执行命令本身（参数、JSON paths） |
| 长篇架构描述 | 错误恢复逻辑、安全门、Credential 规则 |
| 多个示例变体（保留 1-2 个核心） | 跨技能编排链、AIOps/Well-Architected 场景定义 |

---

## Anti-Pattern Checklist

Before and during generation, check against these common anti-patterns:

| # | Anti-Pattern | How It Manifests | Correction |
|---|-------------|-----------------|------------|
| 1 | **Skill = Prompt** | Writing conversational instructions instead of executable steps | Use imperative numbered steps; define I/O; separate triggers from execution |
| 2 | **Skill = Human Doc** | Explaining concepts instead of instructing the agent | Use model-parsable structured language; define behavior boundaries |
| 3 | **Feature Bundling** | One skill tries to do everything (create + monitor + backup + billing) | Split into single-responsibility skills; delegate to existing skills |
| 4 | **API Hallucination** | Inventing field names, JSON paths, or CLI flags not in official docs | Cross-reference every field against API spec or verified CLI output |
| 5 | **Credential Leaking** | Printing, logging, or echoing secret values in any execution path | Mask all credentials with `***` / `<masked>`; check existence only |
| 6 | **No Safety Gate** | Destructive operations (delete, stop, terminate) without explicit confirmation | Add confirmation step before every destructive path (CLI + SDK) |
| 7 | **Hardcoded Values** | Regions, timeouts, or limits baked into instructions | Use `{{env.*}}` / `{{user.*}}` placeholders; document defaults separately |
| 8 | **Missing Failure Path** | Only documenting the success path; no error handling | Add failure recovery table with error codes, retry logic, HALT conditions |
| 9 | **Over-Engineering** | Adding advanced features before core flow works | Follow evaluation-driven approach: start minimal, expand step by step |
| 10 | **Redundant Redundancy** | Repeating the same info across SKILL.md and references | SKILL.md is entry point; references provide depth — no duplication |

---

## Evaluation-Driven Generation Workflow

This workflow follows the **"fail first, evaluate first"** principle: define what "good" looks like before generating. At each critical node, validate the output and loop back for corrections.

> **Copy the checklist below before starting, and mark each step as you complete it.**

### Workflow Checklist

```
[ ] Step 1: Define Evaluation Targets — What does success look like?
[ ] Step 2: Analyze Sources — Extract operations, fields, errors from API spec
    ↓ [Feedback Loop: Sources complete? If gaps found → research, then return]
[ ] Step 3: Scaffold Layout — Create directory from template
[ ] Step 4: Populate SKILL.md — Fill template with verified data
    ↓ [Feedback Loop: Five core standards satisfied? If not → fix and re-verify]
[ ] Step 5: Fill Reference Files — Complete all references/
    ↓ [Feedback Loop: All files populated? If gaps → fix]
[ ] Step 6: Verify & Review — P0/P1 checklist + adversarial review
    ↓ [Feedback Loop: Any failures? → return to Step 4 or 5; re-verify after fix]
[ ] Step 7: Final Anti-Pattern Check — Run anti-pattern checklist above
```

---

### Step 1: Define Evaluation Targets

Before generating anything, define **3-5 evaluation cases** for the target skill. Each case has a clear PASS/FAIL criterion.

**Template:**
```markdown
| ID | Scenario | Expected Behavior | PASS Condition |
|----|----------|-----------------|----------------|
| E1 | User asks to create a resource with minimal input | Skill prompts for required fields, uses smart defaults for optional | ≤ 2 prompts before execution |
| E2 | User asks to delete a resource | Skill asks for explicit confirmation with resource identifier | Confirmation step present |
| E3 | API returns ResourceInsufficient | Skill returns clear error message with remediation steps | Error follows `[ERROR] code → explanation → fix → next step` |
| E4 | User asks about a non-existent resource | Skill checks existence first, returns "not found" with list suggestion | Resource existence check in pre-flight |
| E5 | User asks for a related product operation (e.g., VPC when using CVM) | Skill delegates to the correct skill or documents the limitation | Delegation rule present in Trigger & Scope |
| E6 | Backup before destructive operation | Skill reminds user to backup or validates existing backup | Pre-backup reminder in Delete/Modify flows |
| E7 | Cost optimization suggestion | Skill detects idle resource pattern and recommends right-sizing | Cost assessment section present in skill |
| E8 | Well-Architected security check | Skill documents minimum CAM permissions for operations | CAM section in `well-architected-assessment.md` |
```

**Purpose:** These cases anchor the generation process. Every feature in the generated skill must trace back to at least one evaluation case.

---

### Step 2: Analyze Sources

Extract from API spec and official docs:

- **Operations**: API methods grouped by resource
- **Parameters**: Required vs optional, types, enums, defaults
- **Response schemas**: JSON paths, terminal states, pagination
- **Error codes**: Product-specific error taxonomy (≥ 10 codes)
- **Async behavior**: Polling intervals, terminal state names
- **CLI coverage**: Which operations `tccli` supports vs SDK-only
- **API version drift** (updating existing skills): Compare current API against `metadata.api_profile`; flag changed signatures, deprecations, new parameters

**Validation checkpoint:** Before proceeding, confirm:
- [ ] All API methods are real (not invented)
- [ ] JSON paths are from actual response schemas
- [ ] Error codes are documented in API spec or official docs
- [ ] `cli_applicability` is correctly determined (`cli-first` / `dual-path` / `sdk-only` / `cli-only` for read-only skills)
- [ ] API version drift report generated (if updating existing skill)

---

### Step 3: Scaffold Directory Layout

```text
qcloud-[product]-ops/
├── SKILL.md
├── references/
│   ├── core-concepts.md
│   ├── api-sdk-usage.md
│   ├── cli-usage.md              # Required when cli_applicability: cli-first or dual-path
│   ├── troubleshooting.md
│   ├── monitoring.md              # When monitoring in scope
│   ├── integration.md
│   ├── well-architected-assessment.md  # MANDATORY: four-pillar assessment (Tencent Cloud)
│   └── idempotency-checklist.md  # When retries/automation required
├── assets/
│   ├── example-config.yaml
│   └── eval_queries.json         # MANDATORY: trigger accuracy eval queries
```

Add `references/idempotency-checklist.md` when retries or automation require idempotent behavior.

---

### Step 4: Populate SKILL.md

Base: [qcloud-skill-template.md](references/qcloud-skill-template.md).

Replace all `[Placeholder]` with product-specific content derived from Step 2. Every field, JSON path, and CLI command MUST be traceable to API spec or verified CLI output.

**Frontmatter requirements:**
| Field | Rule |
|-------|------|
| `name` | `qcloud-[product]-ops` — lowercase, hyphens, ≤ 64 chars |
| `description` | Third person, triggers only (per OpenSpec) |
| `cli_applicability` | `cli-first` (CLI covers most APIs, SDK for edges), `dual-path` (both paths required per operation), `sdk-only` (Python SDK only), or `cli-only` (read-only/discovery skills) |
| `cli_support_evidence` | Cite confirmation via `tccli help <product>` or official docs |

**Validation checkpoint (Five Core Standards):**
- [ ] **Boundary**: SHOULD/SHOULD NOT use conditions complete?
- [ ] **I/O**: All placeholders (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) correctly typed?
- [ ] **Steps**: Every operation has Pre-flight → Execute → Validate → Recover?
- [ ] **Failure**: Error taxonomy ≥ 10 codes, each with recovery action?
- [ ] **Single Responsibility**: One product, one resource model, clear delegation?

**If any standard fails → FIX before proceeding to Step 5.**

---

### Step 5: Fill Reference Files

| File | Content | Source |
|------|---------|--------|
| `core-concepts.md` | Architecture, limits, regions, quotas, resource relationships | Official docs |
| `api-sdk-usage.md` | Operation map, required fields, pagination, request/response snippets | API spec |
| `cli-usage.md` | `tccli` command map, coverage gap table, JSON output paths | Verified CLI output |
| `troubleshooting.md` | Error code table, ordered diagnostic steps, product-specific patterns | API spec + experience |
| `monitoring.md` | Metrics, dashboards, alarms, anomaly patterns | Monitoring docs |
| `integration.md` | Python SDK setup, dependency config, environment setup | Execution environment |

**Validation checkpoint:** All reference files populated with real content (not template placeholders)?

---

### Step 6: Verify & Review

Run the [P0/P1 Checklist](#p0--must-pass) below against the generated skill. Run the [Adversarial Review](references/governance-and-adversarial-review.md) scenarios (when present).

**For any failure:**
1. Identify the gap
2. Return to Step 4 (SKILL.md) or Step 5 (references)
3. Fix the gap
4. Re-verify the full checklist

**Re-verify after fixes — do not skip re-runs.**

---

### Step 7: Final Anti-Pattern Check

Run the [Anti-Pattern Checklist](#anti-pattern-checklist) above against the generated skill. Every item must pass.

**If an anti-pattern is detected:**
- Document the instance
- Fix according to the "Correction" column
- Re-run the P0/P1 checklist

---

## Description Optimization (Trigger Accuracy)

The `description` field in frontmatter is the sole trigger mechanism for skill activation. An under-specified description means the skill won't load when it should; an over-broad one means it loads when it shouldn't. Optimize it systematically:

### Write an Effective Description

Follow these principles from the [agentskills.io specification](https://agentskills.io/skill-creation/optimizing-descriptions):

| Principle | Guideline | Example |
|-----------|-----------|---------|
| **Imperative phrasing** | Frame as instruction to agent: "Use when..." | `Use when the user needs to...` |
| **Focus on user intent** | Describe what user is trying to achieve, not skill mechanics | Focus on problems user solves, not CLI/SDK internals |
| **Err on the side of pushy** | Include implicit trigger scenarios explicitly | `even when the user doesn't explicitly mention [product]` |
| **Negative boundaries** | State what the skill is NOT for | `Not for billing, CAM, or related products` |
| **Keep concise** | Under 1024 character hard limit | Aim for 300–700 characters |

### Create Eval Queries

Create an `assets/eval_queries.json` file with ~20 queries (10 should-trigger, 10 should-not-trigger):

```json
[
  { "query": "I need to create a [product] instance", "should_trigger": true },
  { "query": "Check my account bill", "should_trigger": false }
]
```

**Query design tips:**
- **Should-trigger**: Vary phrasing (formal/casual/typos), explicitness (names product vs describes need), detail level (terse vs context-heavy)
- **Should-not-trigger**: Focus on **near-misses** — queries sharing keywords but needing different skills
- **Realism**: Include file paths, personal context, casual language, abbreviations

### Optimization Loop

1. **Evaluate**: Run each query through the agent with the skill installed; compute trigger rate
2. **Identify failures**: Which should-trigger queries didn't trigger? Which should-not-trigger did?
3. **Revise**: If too narrow — broaden scope or add trigger context. If too broad — add specificity or negative boundaries
4. **Repeat**: 5 iterations max. Use a 60/40 train/validation split to avoid overfitting

### Apply the Result

- Update `description` in SKILL.md frontmatter
- Verify under 1024 characters
- Test with 5–10 fresh queries as sanity check
- See `assets/eval_queries.json` for the meta-skill's own eval queries

---

## Before You Generate: Decisions

### Extend vs New Directory
- **Extend** same product and resource model (new operation section, paths, troubleshooting rows)
- **New** `qcloud-[product]-ops` when the **service/API surface** or **primary resource** is distinct

### Naming
- Pattern: `qcloud-[product]-ops` (lowercase, hyphenated)
- Search the repo for collisions before creating

### Dependencies
- Cross-product chains: document **delegation** in Trigger & Scope
- Avoid duplicating another product's full flows

### Sources of Truth
- **API spec + official docs** beat forums and chat logs
- Pin an API/SDK profile in skill `metadata` or `references/integration.md`

### Secrets
- Only `{{env.*}}` **names** and documentation; never real keys or customer data
- Credential masking is MANDATORY — see [references/execution-environment.md](references/execution-environment.md#credential-security)

### CLI-First with Python SDK Fallback
- Primary path: `tccli` CLI (Python CLI tool, covers most APIs)
- Fallback path: `tencentcloud-sdk-python` (official Python SDK)
- Execution environment details: [references/execution-environment.md](references/execution-environment.md)

---

## Governance (Expert Recommendation)

**Minimal adversarial review** gives high return for low cost: it catches destructive-action shortcuts, credential leaks in instructions, and API hallucination **before** merge. Treat [governance-and-adversarial-review.md](references/governance-and-adversarial-review.md) (when present) as the **reviewer companion** to this meta-skill.

Optional later improvements: PR template checkbox linking to that doc; periodic check that CLI-documented skills stay aligned with API spec when APIs change.

---

## Agent-Ready Quality Checklist

### P0 — MUST PASS

- [ ] **Trigger & Scope** with SHOULD-use / SHOULD-NOT-use and delegation rules
- [ ] **Variables:** `{{env.*}}` vs `{{user.*}}`; no secret literals; `{{env.*}}` never collected from user
- [ ] **Flows:** Pre-flight → Execute → Validate → Recover for **each** critical operation
- [ ] **Each flow** documents the correct primary path per `cli_applicability` (`cli-first`/`dual-path` → `tccli` primary + SDK fallback; `sdk-only` → SDK only; `cli-only` → CLI read-only)
- [ ] **Failure recovery:** HALT vs retry; throttling with exponential backoff; non-retryable business errors (ResourceInsufficient, InvalidParameter)
- [ ] **API fidelity:** Fields and paths traceable to API spec/SDK for the stated version
- [ ] **CLI fidelity:** Default output is JSON; commands match official CLI docs; JSON paths verified with a real CLI run or official docs
- [ ] **Safety gates** for destructive operations (before **each** documented path: `tccli` **and** SDK fallback)
- [ ] **Timeouts** for polling and long-running operations (default: 5s interval, 300s max wait)
- [ ] **Self-Healing Framework:** All installation flows follow [enhanced-self-healing-framework.md](references/enhanced-self-healing-framework.md) with pre-flight checks, error classification, multi-path recovery, health verification, and graceful degradation
- [ ] **Self-Healing Coverage:** CLI install, Python runtime setup, dependency download all have ≥ 3 self-healing paths per error type
- [ ] **Self-Healing Metrics:** Health score ≥ 8/10, self-healing duration < 30s, user intervention rate < 20% documented as success criteria
- [ ] **UX Onboarding:** Quick Start section present; first-time user can execute first command within 60 seconds per [user-experience-spec.md](references/user-experience-spec.md) Section 2.1
- [ ] **UX Interaction:** Common operations require ≤ 3 prompts; smart defaults documented; destructive operations have explicit confirmation per [user-experience-spec.md](references/user-experience-spec.md) Section 3
- [ ] **UX Feedback:** Success/failure messages follow standardized format; progress shown for operations > 5s per [user-experience-spec.md](references/user-experience-spec.md) Section 4
- [ ] **UX Error Handling:** Error messages follow `[ERROR] code: summary → explanation → fix → next step` format per [user-experience-spec.md](references/user-experience-spec.md) Section 5
- [ ] **Prompt Library Alignment:** Generation process uses structured prompts from [prompt-library.md](references/prompt-library.md) with effectiveness tracking where applicable
- [ ] **Description Optimization:** Generated skill's `description` field follows agentskills.io optimization principles — imperative phrasing, user-intent focused, implicit trigger scenarios, negative boundaries, under 1024 chars
- [ ] **Eval Queries:** `assets/eval_queries.json` created or updated with should-trigger/should-not-trigger queries for the generated skill
- [ ] **Optimization Awareness:** Skill design considers Fault Diagnosis, Root Cause Localization, and Rapid Resolution dimensions per [optimization-analysis.md](references/optimization-analysis.md)
- [ ] **AIOps Compliance (when skill involves monitoring/alarm/diagnosis):** Skill implements multi-metric correlation, cross-skill diagnosis decision tree, delegation matrix, proactive inspection, and alarm storm handling per [aiops-best-practices.md](references/aiops-best-practices.md)
- [ ] **Well-Architected — Reliability Pillar:** Backup/recovery operations documented with RTO/RPO; DR runbook included; explicit confirmation on all destructive operations per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected — Security Pillar:** Minimum CAM permissions documented; credential masking enforced; VPC endpoint recommendation present per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected — Cost Pillar:** Billing model comparison table present; idle resource detection pattern documented per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected — Efficiency Pillar:** Batch operation pattern documented; automation recommendations present per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected Reference:** SKILL.md links to `well-architected-assessment.md` for pillar-specific assessment patterns
- [ ] **Token Efficiency applied:** TE-1 to TE-7 rules applied per [Token Efficiency Requirements](#token-efficiency-requirements-p0)

### P1 — SHOULD PASS

- [ ] **Chaining:** Stable output fields for downstream skills (via `{{output.*}}` placeholders)
- [ ] **Naming:** `qcloud-[product]-ops` consistent with repo conventions
- [ ] **Pinned** SDK/API baseline where drift matters (in metadata or integration.md)
- [ ] **Idempotency** or duplicate-resource behavior documented when automation or retries apply
- [ ] **Adversarial scenarios** considered using the governance doc (when present)
- [ ] **Path preference:** SKILL.md states when to prefer `tccli` vs SDK fallback if non-obvious
- [ ] **Metadata:** Ops skill frontmatter includes `cli_applicability`, `cli_support_evidence`, `python_version_minimum`, `environment` vars
- [ ] **Well-Architected — Multi-AZ:** Cross-AZ/region deployment recommendation present per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected — Right-Sizing:** Resource utilization → recommendation mapping documented per [well-architected-assessment.md](references/well-architected-assessment.md)
- [ ] **Well-Architected — Batch:** Batch operation pattern documented for ≥ 3 resources per [well-architected-assessment.md](references/well-architected-assessment.md)

---

## Example Request

> Add a Tencent Cloud skill for CVM in this repo: instances, CBS disks, and snapshots. Docs: `https://cloud.tencent.com/document/product/213`. API spec: `https://cloud.tencent.com/document/api/213`. Python SDK (fallback).

**Expected output:** `qcloud-cvm-ops` tree with **real** API methods, Python SDK types, response paths, **and** matching `tccli` commands (primary path), plus Python SDK fallback documentation.

---

## Quality Gate (GCL)

This meta-skill participates in the **Generator-Critic-Loop (GCL)** at the **generation-time**
layer. The loop audits the **generated artifact** (a `qcloud-*-ops/SKILL.md` + `references/`
tree), not cloud resources.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 generator-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Why this skill is `optional` (not `required`)

The meta-skill **does not mutate cloud resources**. Its output is a skill
checked into git. Safety is enforced by the **build-time** Charter C1-C7
self-check + 2-round self-review (already mandatory above) and by the
**Charter C7 enforcement** that requires generated skills to ship with their
own Tier A rubric.md + prompt-templates.md + Quality Gate chapter. The GCL
loop on this meta-skill is therefore a **double-check**: it verifies that
the Charter was followed during generation.

### Decision flow

1. **Safety = 0** (e.g., credential literal emitted) ⇒ **ABORT** — emit
   recovery: replace literal with `{{env.*}}` placeholder
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved
   Charter violations in `final.unresolved`
3. **All Charter C1-C7 checks pass** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's `charter_violations` injected

### Meta-skill-specific safety rules (rubric §4)

1. Generated `references/rubric.md` MUST have `safety = 1.0` threshold for destructive ops
2. Generated `references/prompt-templates.md` §2 Critic MUST be isolated-context
3. Generated `SKILL.md` MUST include `## Quality Gate (GCL)` chapter (Charter C7)
4. Frontmatter `metadata.cli_applicability` MUST be set with `cli_support_evidence`
5. Real-time API doc changes MUST surface breaking changes in trace + bump version

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — generating a hypothetical `qcloud-foo-ops`

| Dimension | Score |
|---|---|
| Correctness | 1 (frontmatter has all 5 keys) |
| **Safety** | **0** (rule 1 violated: rubric.md missing `safety = 1.0` for `DeleteFoo`) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 0.5 (Charter C7 partial — rubric.md present, prompt-templates.md missing) |

`decision: ABORT`. Recovery suggestion: "Add `safety = 1.0` to rubric.md §2 dimensions and scaffold prompt-templates.md from cos-ops reference".

See [`references/rubric.md`](references/rubric.md) §6 for two more examples.

---

## Reference Directory

| File | Purpose |
|------|---------|
| [qcloud-skill-template.md](references/qcloud-skill-template.md) | Base template for generated SKILL.md |
| [execution-environment.md](references/execution-environment.md) | CLI install, Python SDK setup, credential config, verification **(progressive disclosure)** |
| [cli-behavior.md](references/cli-behavior.md) | Verified `tccli` CLI behavioral notes (output format, env vars, patterns) **(progressive disclosure)** |
| [enhanced-self-healing-framework.md](references/enhanced-self-healing-framework.md) | **MANDATORY** self-healing patterns for installation flows |
| [governance-and-adversarial-review.md](references/governance-and-adversarial-review.md) | (when present) Adversarial review scenarios and governance checklist |
| [prompt-library.md](references/prompt-library.md) | Structured prompts for the generation lifecycle |
| [gcl-prompt-backbone.md](references/gcl-prompt-backbone.md) | **TE-6** shared GCL Generator/Critic/Orchestrator skeletons (product skills link, do not duplicate) |
| [optimization-analysis.md](references/optimization-analysis.md) | Three-dimensional optimization framework |
| [user-experience-spec.md](references/user-experience-spec.md) | Mandatory UX requirements for all generated skills |
| [aiops-best-practices.md](references/aiops-best-practices.md) | Mandatory AIOps patterns for monitoring/diagnosis skills |
| [well-architected-assessment.md](references/well-architected-assessment.md) | **NEW** Tencent Cloud Well-Architected Framework four-pillar assessment integration |
| [assets/eval_queries.json](assets/eval_queries.json) | Eval queries for testing the meta-skill's description trigger accuracy |

### External References

- [Tencent Cloud CLI (tccli)](https://cloud.tencent.com/document/product/440)
- [Tencent Cloud SDK for Python (tencentcloud-sdk-python)](https://cloud.tencent.com/document/sdk/Python)
- [Agent Skills Open Specification](https://agentskills.io/specification)