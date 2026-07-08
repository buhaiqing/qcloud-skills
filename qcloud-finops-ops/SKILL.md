---
name: qcloud-finops-ops
description: 腾讯云 FinOps 一站式 Skill。聚焦单账号（可扩展多账号）的账单/费用/成本/预算/优化全闭环。能力包括：账单汇总与明细、账户余额与代金券、订单/收支、成本分摊（Tag）、预算与告警、闲置识别与优化建议、月度/季度报告、异常账单自动巡检。与 27 个产品 skill 联动实现"为什么花 → 怎么省"闭环。
keywords: [账单, 费用, 计费, FinOps, 成本优化, 预算, 代金券, 订单, 收支明细, 成本分析, 异常账单]
compatibility: tccli >= 3.0 + tencentcloud-sdk-python >= 4.0
cli_applicability: dual-path
cli_support_evidence: tccli billing DescribeBillSummaryByPayMode --help
environment:
  TENCENTCLOUD_SECRET_ID: "{{env.TENCENTCLOUD_SECRET_ID}}"
  TENCENTCLOUD_SECRET_KEY: "{{env.TENCENTCLOUD_SECRET_KEY}}"
  TENCENTCLOUD_REGION: "{{env.TENCENTCLOUD_REGION}}"
  TENCENTCLOUD_FINOPS_CONFIG: "{{env.TENCENTCLOUD_FINOPS_CONFIG}}"
related_skills:
  - qcloud-monitor-ops
  - qcloud-aiops-diagnosis
  - qcloud-proactive-inspection
  - qcloud-well-architected-review
  - qcloud-cam-ops
  - 27 个产品 skill（CVM/CDB/CLB/COS/ES/Redis/VPC 等）
metadata:
  version: 1.0.0
  last_updated: "2026-07-08"
  license: MIT
  author: HDOP
  runtime: cli+sdk
  python_version_minimum: "3.8"
---

# qcloud-finops-ops · FinOps 一站式

> 把"知道花了多少钱 → 知道为什么花 → 知道怎么省"串成完整闭环。

## 定位与边界

### SHOULD Use

- 账单：「本月账单」「按产品/项目汇总」「资源级账单」「L0-L3 明细」
- 资金：「账户余额」「可用金」「代金券」「订单」「收支明细」
- 分摊：「按部门分摊」「Tag 标签」「资源包抵扣」
- 预算：「设预算」「费用告警」「预算执行率」
- 异常：「为什么费用涨了」「账单异常」「突增检测」
- 优化：「怎么省钱」「闲置资源」「资源包推荐」「计费模式转换」
- 报告：「月度账单」「季度 FinOps 复盘」

### SHOULD NOT Use

- 四支柱卓越架构评估 / 架构设计审查 → delegate to: `qcloud-well-architected-review`
- 多云账单（阿里云/AWS/华为云）→ 不支持
- 权限/账号/密钥 → `qcloud-cam-ops`
- 资源 CRUD → 对应产品 skill
- 实时监控指标 → `qcloud-monitor-ops`
- 实际计费规则计算（阶梯价/折扣）→ 引用腾讯云官方文档
- 企业财务对账（合同/发票/报销）→ 超出 FinOps 范围
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected 成本评估（只读）→ 由 `qcloud-well-architected-review` 编排调用；见 **Read-Only Assessment Mode**

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** **Cost pillar** billing/TCO data for Well-Architected orchestrator; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | typically `cost` |
| `{{user.scope}}` | `account-wide` |

**Allowed:** 只读账单 API（`DescribeBill*`, `DescribeCost*`, `DescribeAccountBalance` 等）— **禁止** 触发计费变更或资源删除。

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: finops`).

## 凭证与配置

**单账号（默认）**：

```bash
export TENCENTCLOUD_SECRET_ID=AKIDxxx
export TENCENTCLOUD_SECRET_KEY=xxx
export TENCENTCLOUD_REGION=ap-guangzhou
```

**配置文件**（推荐生产环境，`$TENCENTCLOUD_FINOPS_CONFIG` 指向 `assets/example-config.yaml`）：支持预算定义、告警通道、Tag 映射、异常阈值、**预留多账号扩展位**（当前不读取）。

→ 详见 `references/setup-and-permissions.md`（最小权限策略、凭证安全、轮换流程）

## 8 大核心模块

### 模块 1：账单数据获取（基础层）

| 能力 | API（tccli） |
|---|---|
| 月度汇总 | `billing DescribeBillSummaryByMonth` |
| 按产品/项目/区域/计费模式汇总 | `DescribeBillSummaryBy{Product,Project,Region,PayMode}` |
| 明细 L0-L3 | `billing DescribeBillList` |
| 资源级账单 | `billing DescribeBillResourceSummary` |
| 成本分析 | `billing DescribeCostSummary` / `DescribeCostDetail` |

> 双路径：主 `tccli`，CLI 字段不全时回退 `tencentcloud-sdk-python` 中 `billing.v20180709` 客户端。
> → 详细参数与错误码见 `references/billing-api-mapping.md` §1、`references/sdk-usage.md` §2

### 模块 2：账户与资金（财务基线）

| 能力 | API |
|---|---|
| 账户余额（现金/可用金/冻结）| `billing DescribeAccountBalance` |
| 收支明细 | `trade DescribePayDeals` |
| 订单管理（新购/续费/退订）| `trade DescribeOrders` |
| 代金券（可用/已用/已过期）| `voucher DescribeVoucherList` |
| 账单调整（退费/补偿）| `billing DescribeBillAdjust` |

→ 详见 `references/billing-api-mapping.md` §2-3、`references/sdk-usage.md` §3-4

### 模块 3：成本分摊与归因

```bash
tccli tag GetTagKeys
tccli tag GetTagValues --TagKey "业务部门"
tccli billing DescribeCostDetail --Month "2026-05" \
  --DimensionTagKey "业务部门" --DimensionPeriodType "MONTH"
```

**典型标签维度**：`business-line` / `dept` / `env`（dev/staging/prod）/ `project-code` / `cost-center`。

**资源包使用率**：`billing DescribeResourcePackageList` / `DescribeResourcePackageUsage`。

→ 详细查询模式见 `references/cost-analysis-queries.md` §1-3

### 模块 4：预算与告警（事前控制）

**预算建议公式**：

```
建议预算 = max(过去3月均值, 去年同期) × (1 + 业务增长率) × 1.1
```

**异常检测算法**（核心，ii + iii 双维度）：

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

**告警通道**：委托 `qcloud-monitor-ops` 创建策略；支持短信/电话/邮件 + 企业微信/钉钉/飞书 Webhook。

→ 算法推导与变体见 `references/finops-methodology.md` §2，预算公式与分级见 §5

### 模块 5：成本优化建议（事中优化）

> **黄金原则**：所有建议须人工审批，本 skill 只生成建议 + 风险评估，不自动改资源。

**核心 7 类优化**（完整 28 类 → `references/finops-methodology.md` §3）：

| 类型 | 触发条件 | 数据来源 | 动作 | 风险 |
|---|---|---|---|---|
| 闲置 CVM | CPU < 5% × 7 天 | monitor+cvm | 关机/降配/释放 | 中 |
| 闲置 CLB | 连接数 < 10 × 7 天 | monitor+clb | 删除/共享带宽包 | 中 |
| 存储分层 | COS 标准存储 30 天未访问 | cos | 转归档/低频 | 低 |
| 计费模式 | 短期资源 < 30 天 | cvm/cdb/redis | 按量↔包月 | 中 |
| 资源包推荐 | 用量稳定 > 阈值 | billing | CDN/直播/COS 包 | 低 |
| Spot 实例 | 非生产 + 可中断 | cvm/tke | 改 Spot（省 60-90%）| 高 |
| NAT 优化 | 多个 EIP 同 VPC | vpc | 共享 NAT 网关 | 中 |

**建议模板**：`资源ID | 规格/计费 | 当前成本 | 优化后成本 | 节省% | 风险 | 审批owner | 年化节省`。

→ ROI 计算公式见 `references/finops-methodology.md` §4

### 模块 6：（预留）多云账单一站式

**当前版本不实现**，仅在 `example-config.yaml` 预留 `multi_cloud` 字段。

### 模块 7：报告生成

| 报告 | 频率 | 模板 |
|---|---|---|
| 月度账单 | 每月 1 日 | `references/reports/monthly-bill-template.md` |
| 季度复盘 | 每季末 | `references/reports/quarterly-review-template.md` |
| 自定义 | 临时 | 按需 |

**报告核心结构**（双维度对比章节必备）：

```markdown
## 1. 本月总览（同比/环比）
## 2. [维度 ii] 滚动对比 — 本月 vs 近3月均值
## 3. [维度 iii] 预算对比 — 已使用 / 剩余
## 4. 综合判断（MEDIUM / HIGH 置信度）
## 5. Top 5 成本来源 + Top 5 优化建议
## 6. 资源包使用率
```

**输出格式**：Markdown（主，飞书/钉钉/邮件）/ CSV（BI 消费）/ JSON（Agent 复用）。

### 模块 8：与其他 Skill 联动

| 联动 | 目标 | 数据流 |
|---|---|---|
| **读取** | `qcloud-monitor-ops` + 23 个产品 skill | 单向：产品 → finops |
| **触发** | `qcloud-proactive-inspection` | 单向：finops → 巡检（异常自动派发） |
| **协同** | `qcloud-aiops-diagnosis` / `qcloud-well-architected-review` | 双向：互引 |

**核心场景**：异常账单 → 自动派发巡检工单 → 联动 `qcloud-aiops-diagnosis` 出根因报告 → 通知告警通道。

→ 完整异常根因报告示例见 `references/cost-analysis-queries.md` §6

### 模块 9：跨账号统一成本视图（多账号）

> **能力等级：** P1（扩展功能，需提前配置子账号 CAM 委托）
> **原理：** 通过 CAM 角色委托（Role）获取多个子账号的只读账单数据，合并为统一视图。

#### 前置条件

| 检查 | 方法 | 预期 | 失败处理 |
|------|------|------|----------|
| 主账号 CAM Role | `tccli cam ListRoles` | 存在 FinOps 只读角色 | HALT；创建角色 |
| 子账号列表 | `tccli organization DescribeOrganizationMembers` | 非空 | HALT；未加入组织 |
| 子账号委托 | 每个子账号已授予主账号角色 | 委托状态 `ACTIVE` | HALT；配置委托 |

#### 执行 — 汇总脚本

```bash
#!/bin/bash
# 遍历子账号，汇总月度账单
# 需要子账号 SecretId/SecretKey 或 CAM Role 委托
ACCOUNTS=("$@")
echo "# 跨账号成本报告"
echo "| 账号 | 产品 | 月度费用(元) | 环比 |"
echo "|------|------|------------|------|"
for ACCOUNT in "${ACCOUNTS[@]}"; do
  export TENCENTCLOUD_SECRET_ID="${ACCOUNT}_SECRET_ID"
  export TENCENTCLOUD_SECRET_KEY="${ACCOUNT}_SECRET_KEY"
  tccli billing DescribeBillSummaryByMonth \
    --Month "$(date +%Y-%m)" \
    --Region "{{env.TENCENTCLOUD_REGION}}"
done
```

#### 输出

| 字段 | 路径 |
|------|------|
| 账号维度汇总 | `$.Response.SummaryTotal[*].RealTotalCost` |
| 按产品汇总 | `$.Response.SummaryByProduct[*]` |
| 环比变化 | `$.Response.SummaryTotal[*].RealTotalCostRate` |

#### 失败恢复

| 错误码 | 处理 |
|--------|------|
| `UnauthorizedOperation` | HALT；检查 CAM 委托配置 |
| `OrganizationNotExists` | HALT；账号未加入组织 |
| `ResourceNotFound.Role` | HALT；创建 FinOps 只读角色 |

## 核心工作流（Pre-check → Execute → Verify → Recover）

```
1. Pre-check  校验凭证/权限/限流，加载 TENCENTCLOUD_FINOPS_CONFIG
2. Route      按用户 query 匹配 8 大模块入口
3. Fetch      并行调用账单/余额/订单/代金券 API；必要时 delegate 产品 skill
4. Transform  内存聚合（产品/项目/区域/标签）+ 同比环比 + 异常检测（ii+iii）
5. Cross-Ref  delegate monitor 拉监控；delegate 产品 skill 拿元数据；计算优化空间
6. Output     表格 + TopN + 优化建议 + 置信度标注
7. Verify     金额合计对账（容差<¥0.01）+ 跨产品一致性 + 异常复核
8. Recover    CLI 字段不全→SDK / 权限不足→提示追加策略 / 限流→分页+退避
```

## 5 个质量门

| # | 门 | 标准 |
|---|---|---|
| 1 | Pre-flight | 凭证/权限/限流三件套通过 |
| 2 | 数据完整性 | 金额合计 = 子项之和（容差 < ¥0.01） |
| 3 | 异常可解释 | 每个异常标注 ii/iii 维度 + 数值 |
| 4 | 建议可执行 | 含资源ID/风险/预期节省/审批 owner |
| 5 | 报告可审计 | 数据可追溯到 API 调用 + 时间戳 |

## 双路径实现示例

**主路径（tccli）**：

```bash
tccli billing DescribeBillSummaryByMonth --Month "2026-05" --PayType "prePayAndPostPay"
tccli billing DescribeAccountBalance
tccli voucher DescribeVoucherList --Status "unused" --Limit 100
```

**兜底路径（Python SDK）**：CLI 字段不全、复杂 JSON 参数、批量操作时使用。

→ 完整 SDK 模板见 `references/sdk-usage.md`

## 故障排查速查

| 现象 | 原因 | 解决 |
|---|---|---|
| `AuthFailure` | SecretID/Key 错或过期 | 检查环境变量 + CAM 密钥 |
| `InvalidParameter.Month` | 月份格式错 | 用 `YYYY-MM` |
| 账单数据缺失 | 子账号未授权 | 追加 `QcloudBillingReadOnlyAccess` |
| API 限流 | QPS 超限 | 降低并发 + 分页 + 退避重试 |
| 对账偏差 | 实时 vs 结算账单时差 | 引用腾讯云官方计费说明 |

→ 详细排查（凭证、参数、性能、联动、紧急情况）见 `references/troubleshooting.md`

## 局限与免责声明

- **API 准确性**：本文件基于训练数据中腾讯云文档记忆编写，**实际参数/字段以 `https://cloud.tencent.com/document/api/555` 为准**。
- **计费规则**：实际计费（阶梯价/预留实例/促销折扣）由腾讯云计费系统决定，本 skill **不内置**计算。
- **数据延迟**：账单数据通常 1-2 天延迟，实时性低于控制台。
- **跨账号**：当前**仅支持单账号**；多账号扩展位已预留。
- **多云**：当前**不支持**阿里云/AWS/华为云。

→ API 校对清单与错误码见 `references/api-cross-check.md`

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-04 | Phase 1 GCL rollout |
| 1.1.0 | 2026-06-09 | Added `references/well-architected-assessment.md` (Cost worker + schema-aligned output) |
| 1.2.0 | 2026-07-03 | Added module 9: cross-account unified cost view (multi-account via CAM role delegation) |

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each FinOps execution against an explicit rubric,
in addition to the build-time **Safety Gates** above and the build-time **2-round
self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

> **Read-only / advisory skill.** This skill MUST NOT auto-execute billing changes or
> resource mutations. GCL Safety dimension uses threshold **0.5** (not 1.0) for advisory
> violations; destructive delegation to product skills requires Safety = 1.0.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-finops-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 FinOps-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Advisory with delegation risk: idle-resource recommendations that could trigger product-skill deletes | **yes** | Must enforce handoff-only, no auto-execute |
| Billing report generation: cost breakdown, tag attribution, budget alerts | optional | Privacy masking still scored |
| Read-only: `DescribeBillDetail`, `DescribeCostSummary`, CLS idle queries | optional (max_iter=1, no hard abort) | No side effects |

### Decision flow (first match wins)

1. **Safety = 0** on destructive delegation (rule 2 or 5 violated) ⇒ **ABORT** — advisory privacy violations score 0.5, RETRY not ABORT
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### FinOps-specific rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | Bill download / cost report generation (any read op) | Warn that the report contains sensitive billing data — do NOT output the raw report contents in t... |
| 2 | Cost anomaly detection / budget alert configuration (recommendation flow) | For any cost anomaly that triggers a budget alert: warn that the system will NOT auto-execute any... |
| 3 | Tag-based cost allocation modification (`CreateCostAllocationTag` / `DeleteCostAllocationTag` / `ModifyCostAllocationTag`) | Warn that changing cost allocation tags changes how costs are attributed in future reports; exist... |
| 4 | `DeleteBillSummary` / `DeleteBillExport` (historical billing data purge) | Warn that historical billing data will be permanently purged (this is NOT soft-delete); require p... |
| 5 | Resource type report / cross-skill delegation (recommendation flow) | For resource-type recommendations (e.g., "consider terminating idle CVM"): delegate to the specif... |

Auto-execute / credential leak ⇒ **Safety = 0**; see rubric §2 for advisory thresholds.

### Worked example — idle CVM recommendation with auto-terminate attempt

| Dimension | Score |
|---|---|
| Correctness | 0.5 (idle list correct, but action attempted) |
| **Safety** | **0** (rule 5 violated — auto-executed terminate instead of handoff) |
| Idempotency | 1 |
| Traceability | 0.5 (billing data masked correctly) |
| Spec Compliance | 0 |

`decision: ABORT`. Recovery suggestion: "Revert any unintended termination via product skill; re-run as read-only report with handoff to `qcloud-cvm-ops`."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on cost report and RETRY on unmasked invoice URL).

---

## 相关 Skill 索引

| Skill | 关系 |
|---|---|
| `qcloud-monitor-ops` | 监控指标 + 告警通道 |
| `qcloud-aiops-diagnosis` | 多指标诊断（含成本维度）|
| `qcloud-proactive-inspection` | 异常账单自动派发 |
| `qcloud-finops-ops` | 架构评估（含 TCO）| [`references/well-architected-assessment.md`](references/well-architected-assessment.md) |
| `qcloud-cam-ops` | 权限/账号/密钥 |
| 23 个产品 skill | 资源元数据归因（只读）|
