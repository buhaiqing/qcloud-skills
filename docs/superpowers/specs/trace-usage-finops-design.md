# TRACE-1: Trace Usage & FinOps 成本归因设计

## 1. 背景与问题

当前仓库已具备 GCL trace、Copilot step audit、skill health、metrics JSONL 和 Prometheus 输出能力，但这些记录主要服务于质量审计与运行可观测性，尚不足以支撑 AIOps 成本分析。

现有 trace 的主要缺口：

1. 只有 Skill 名称，缺少 `SKILL.md`、引用文档、Prompt、Rubric、代码提交和运行时版本。
2. `trace_id`、`session_id`、`run_id`、`step_id` 的层级语义不完全统一，跨 Copilot、GCL、Skill、LLM、云 API 的链路不完整。
3. 没有标准化记录 Generator/Critic/总结器的 input/output/cached/reasoning token。
4. 没有按 Tencent Cloud `product/action/region/resource` 记录 CLI/SDK API 调用、重试、限流、请求量和数据读取量。
5. 没有价格版本、计费维度、成本状态和分摊键，无法区分真实成本、估算成本和未定价用量。
6. `output` 和命令文本承载了过多非结构化信息，不利于聚合和成本重算。

## 2. 目标

- 建立 `trace_schema_version=3.0` 的 Langfuse/OTel 对齐 `Trace`、`Observation`、`Score`、`UsageEvent`、`CostRecord`、`PricingSnapshot` 和可重建 `Summary` 契约。
- 可追踪一次用户请求/Incident 下的 Copilot、Skill、GCL、LLM、Cloud API 和验证步骤。
- 可回答 Skill 版本、产品 API 调用量、LLM Token、数据读取量和成本归因问题。
- 用事实用量与价格快照分离的方式支持后续重算和账单校准。
- 保持现有 GCL trace、Copilot audit、health JSONL 的向后兼容。
- 不记录 SecretId、SecretKey、原始凭证、未脱敏资源标识或敏感用户内容。

### 2.1 当前身份字段基线（代码事实）

当前实现没有真正定义或传播 `user_id`：

- `qcloud-copilot` 的主关联键是 `session_id`，用于 Blackboard、Session history、GCL join 和跨 Skill handoff。
- `Blackboard` 当前包含 `user_request`，但没有 `user_id`、`tenant_id`、`customer_id`、`operator_id` 或 `account_id` 字段。
- Proactive Inspection 的策略上下文存在 `customer`，它表示客户/巡检对象，不等同于终端用户。
- `session_id` 是会话/任务 ID，不得映射成 Langfuse `user_id`。

因此 TRACE-1 不做“兼容旧 user_id”的迁移，而是首次建立明确的身份上下文模型。

## 3. 非目标

- 本阶段不直接接入腾讯云账单生产 API。
- 本阶段不假设所有腾讯云 API 都存在按请求计费；未定价接口只记录用量并标记 `unpriced`。
- 本阶段不重写现有 GCL 评分逻辑、Copilot 编排逻辑或产品 Skill 业务逻辑。
- 本阶段不把 token 作为 Tencent Cloud 产品 API 的通用计费单位。

## 4. 架构

```text
Copilot / Skill / GCL / LLM / tccli / SDK / Verification
                         │
                         ▼
                 TraceContext + Observation/UsageEmitter
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Observation     UsageEvent     Audit/Redaction
          │              │              │
          └──────────────┼──────────────┘
                         ▼
             Trace Summary / FinOps Aggregator
                         │
                         ▼
       PricingSnapshot + CostAllocation + Dashboard
```

### 4.1 ID 层级

| ID | 语义 | 生命周期 |
|---|---|---|
| `trace_id` | 一次完整用户请求、巡检任务或 Incident 链路 | 全链路 |
| `span_id` | 一个 Copilot、Skill、GCL、LLM、Cloud API 或验证调用 | 单节点 |
| `parent_span_id` | 当前 span 的直接父调用 | 单节点关系 |
| `session_id` | Copilot 交互会话 | 会话级 |
| `incident_id` | 业务故障或事件 | Incident 生命周期 |
| `request_id` | 单次内部/外部请求 | 请求级 |
| `api_request_id` | Tencent Cloud API 返回的 `RequestId` | 云 API 请求级 |

## 5. 核心 Schema

### 5.0 分析域原则

`TraceRecord` 必须同时满足三类消费者：

1. **AIOps**：能够分析症状、时间线、证据、拓扑、根因、影响、变更、数据质量、处置和验证结果。
2. **FinOps**：能够分析 LLM、云 API、数据读取、计算、存储用量和成本，并按租户、业务、产品、Region、资源、Incident、Skill/版本归因。
3. **Langfuse/OTel**：能够映射 Trace/Observation/Generation/Score 和父子链路，不依赖私有 metadata 才能完成核心查询。

因此采用“**Trace 聚合根 + Observation 明细 + UsageEvent 事实账本 + 可重建 Summary**”模式：

- Trace 存放一次链路的稳定查询维度和摘要引用。
- Observation 存放 Skill、API、LLM、验证等节点明细。
- UsageEvent 存放不可变用量事实，价格和成本可以重算。
- AIOps/FinOps 必需字段禁止仅存在于自由格式 `output` 或 `metadata`。

### 5.1 TraceRecord v2

```json
{
  "trace_schema_version": "2.0",
  "trace_id": "trc-01J...",
  "parent_trace_id": null,
  "root_trace_id": "trc-01J...",
  "span_id": "spn-01J...",
  "parent_span_id": "spn-01J...",
  "trace_type": "copilot|skill|gcl|api|llm|verification",
  "status": "success|failure|partial|skipped|aborted",
  "started_at": "2026-07-25T10:00:00Z",
  "ended_at": "2026-07-25T10:00:03Z",
  "duration_ms": 3000,
  "request_context": {
    "session_id": "ses-xxx",
    "incident_id": "inc-xxx",
    "request_id": "req-xxx",
    "operation": "diagnose",
    "intent_class": "aiops_diagnosis",
    "safety_class": "read_only",
    "trigger_source": "alarm|schedule|user|finops|inspection"
  },
  "identity": {
    "user_id": null,
    "tenant_id": "tenant-xxx",
    "customer_id": "customer-xxx",
    "operator_id": "operator-xxx",
    "account_id_hash": "sha256:...",
    "identity_source": "request|session|config|handoff|unknown"
  },
  "tenant": {
    "tenant_id": "tenant-xxx",
    "customer_id": "customer-xxx",
    "business_unit": "ops",
    "environment": "production"
  },
  "runtime": {
    "agent_runtime": "codex|cursor|other",
    "runtime_version": "x.y.z",
    "python_version": "3.12.x",
    "tccli_version": "x.y.z",
    "sdk_name": "tencentcloud-sdk-python",
    "sdk_version": "x.y.z",
    "git_commit": "abcdef",
    "deployment_version": "release-xxx"
  },
  "skill": {
    "name": "qcloud-aiops-diagnosis",
    "version": "2.5.2",
    "source": "workspace|package|remote",
    "skill_file_sha256": "sha256:...",
    "skill_commit": "abcdef",
    "references": {
      "multi-source-rca": {"version": "1.4.0", "sha256": "sha256:..."},
      "anomaly-detection": {"version": "1.3.0", "sha256": "sha256:..."}
    },
    "prompt_version": "aiops-rca-v2",
    "rubric_version": "v1"
  },
  "plan": {
    "plan_id": "plan-xxx",
    "step_id": "diagnose-1",
    "step_index": 1,
    "total_steps": 3,
    "delegated_from": "qcloud-copilot",
    "delegated_to": "qcloud-aiops-diagnosis"
  },
  "scope": {
    "provider": "tencent_cloud",
    "region": "ap-guangzhou",
    "account_id_hash": "sha256:...",
    "products": ["monitor", "cvm", "tke"],
    "resource_types": ["instance", "cluster", "alarm_policy"],
    "resource_ids_hash": ["sha256:..."],
    "resource_count": 12
  },
  "aiops": {
    "incident": {
      "incident_id": "inc-xxx",
      "incident_class": "performance|availability|capacity|security|cost",
      "severity": "P0|P1|P2|P3",
      "lifecycle_state": "detected|correlated|diagnosed|mitigating|verifying|resolved|reviewed",
      "detected_at": "2026-07-25T09:55:00Z",
      "resolved_at": null,
      "slo_impact": {
        "slo_id": "slo-xxx",
        "violated": true,
        "error_budget_burn_rate": 8.2
      }
    },
    "signals": {
      "alarm_count": 12,
      "metric_anomaly_count": 4,
      "log_pattern_count": 3,
      "change_event_count": 1,
      "inspection_finding_count": 2,
      "signal_types": ["alarm", "metric", "log", "change"]
    },
    "evidence": {
      "evidence_count": 18,
      "sources": ["monitor", "cls", "cloudaudit", "topology"],
      "time_window_start": "2026-07-25T09:00:00Z",
      "time_window_end": "2026-07-25T10:00:00Z",
      "time_alignment": "complete|partial|misaligned",
      "data_quality": {
        "status": "complete|partial|stale|unavailable",
        "freshness_ms": 30000,
        "coverage_ratio": 0.93,
        "missing_sources": [],
        "degraded": false
      }
    },
    "topology": {
      "snapshot_id": "topo-xxx",
      "node_count": 35,
      "edge_count": 46,
      "snapshot_at": "2026-07-25T09:59:00Z",
      "completeness_ratio": 0.88
    },
    "rca": {
      "top_cause_id": "cause-xxx",
      "top_cause_category": "configuration_change",
      "confidence": "HIGH|MEDIUM|LOW",
      "confidence_score": 0.91,
      "hypothesis_count": 4,
      "supporting_evidence_count": 7,
      "contradicting_evidence_count": 1,
      "similar_incident_count": 2,
      "change_correlated": true
    },
    "impact": {
      "affected_service_count": 2,
      "affected_resource_count": 12,
      "affected_user_estimate": 430,
      "failed_request_count": 1800,
      "business_impact_level": "critical|high|medium|low|unknown"
    },
    "response": {
      "recommendation_count": 3,
      "action_count": 1,
      "human_approval_required": true,
      "rollback_available": true,
      "verification_status": "pending|passed|failed|inconclusive",
      "recovery_ratio": null,
      "mttr_ms": null
    },
    "quality": {
      "review_outcome": "confirmed|false_positive|false_negative|inconclusive|pending",
      "root_cause_rank": 1,
      "root_cause_confirmed": null,
      "alert_reduction_count": 9,
      "alert_compression_ratio": 0.75
    }
  },
  "finops": {
    "usage_summary": {
      "llm_request_count": 2,
      "llm_input_tokens": 12000,
      "llm_output_tokens": 3500,
      "llm_cached_input_tokens": 4000,
      "llm_reasoning_tokens": 800,
      "cloud_api_request_count": 8,
      "cloud_api_retry_count": 1,
      "metric_points_read": 1440,
      "log_bytes_read": 5242880,
      "event_records_read": 240,
      "compute_ms": 3100,
      "storage_bytes": 45000,
      "cache_hit_count": 2
    },
    "cost_summary": {
      "currency": "CNY",
      "llm_cost": 0.37,
      "cloud_api_cost": null,
      "data_scan_cost": null,
      "compute_cost": null,
      "storage_cost": null,
      "human_cost": null,
      "total_cost": 0.37,
      "cost_status": "partial",
      "priced_usage_ratio": 0.62,
      "pricing_versions": ["pricing-2026-07-25"]
    },
    "allocation": {
      "cost_center": "cc-ops",
      "project_id": "project-xxx",
      "service_name": "payment-api",
      "charge_type": "direct|shared|unallocated",
      "allocation_method": "resource|request|usage|equal_split",
      "allocation_ratio": 1.0
    },
    "value": {
      "incident_avoided": null,
      "downtime_avoided_ms": null,
      "estimated_loss_avoided": null,
      "manual_hours_saved": null,
      "currency": "CNY",
      "value_status": "unknown|estimated|actual"
    }
  },
  "usage_refs": ["use-01J...", "use-01J..."],
  "outcome": {
    "finding_count": 3,
    "incident_created": true,
    "root_cause_confidence": "HIGH",
    "verification_status": "pending",
    "review_outcome": "pending"
  },
  "security": {
    "masked_fields": ["request", "resource_ids"],
    "secret_scan": "passed",
    "data_classification": "internal"
  }
}
```

### 5.1.1 TraceRecord 必填层级

| 层级 | 必填条件 | 用途 |
|---|---|---|
| Identity/Time/Status | 始终必填 | 链路、延迟、成功率 |
| Tenant/Scope | 始终必填；未知值显式 `unknown` | 多租户和资源归因 |
| Runtime/Skill Version | Skill 调用必填 | 版本质量与成本对比 |
| `aiops.incident/signals/evidence/rca/impact/response/quality` | AIOps trace 必填，未知值不得省略 | RCA、MTTR、误报、业务影响分析 |
| `finops.usage_summary/cost_summary/allocation/value` | 有任何 UsageEvent 时必填 | 用量、成本、分摊、价值分析 |
| `usage_refs` | 有外部用量明细时必填 | 事实账本 join |
| Security | 始终必填 | 脱敏和合规审计 |

### 5.1.2 分析指标可推导性

TraceRecord 必须能直接或通过 `usage_refs` 推导：

| 分析指标 | 所需字段 |
|---|---|
| MTTD/MTTA/MTTR | incident 时间戳、response 状态时间 |
| RCA Top-1/Top-3 准确率 | hypothesis rank、review outcome、confirmed cause |
| 告警压缩率 | alarm count、alert reduction count |
| 数据质量 SLO | freshness、coverage、missing sources、degraded |
| 修复成功率 | action、verification status、recovery ratio |
| 单 Incident 成本 | trace/incident ID + cost summary + UsageEvent |
| 单 Skill/版本成本 | skill name/version/commit + cost summary |
| 产品 API 成本 | UsageEvent product/action/region + PricingSnapshot |
| 成本收益比 | total cost + avoided loss/downtime/manual hours |
| 高成本低收益诊断 | total cost + RCA quality + MTTR impact + review outcome |

### 5.2 LLM UsageEvent

每一次模型请求独立记录，不只在 trace 汇总：

```json
{
  "usage_event_id": "use-01J...",
  "trace_id": "trc-01J...",
  "span_id": "spn-01J...",
  "usage_type": "llm_tokens",
  "role": "generator|critic|summarizer|router",
  "provider": "provider-name",
  "model": "model-name",
  "model_version": "model-version",
  "prompt_template_version": "v2.1",
  "input_tokens": 5000,
  "output_tokens": 1200,
  "cached_input_tokens": 800,
  "reasoning_tokens": 200,
  "total_tokens": 6400,
  "request_count": 1,
  "retry_index": 0,
  "latency_ms": 900,
  "finish_reason": "stop",
  "pricing_version": "pricing-2026-07-25",
  "quantity": 6400,
  "unit": "token",
  "estimated_cost": 0.18,
  "currency": "CNY",
  "cost_status": "estimated"
}
```

### 5.3 Cloud API UsageEvent

Tencent Cloud 产品 API 不默认使用 token 计费，按 API 和数据量记录：

```json
{
  "usage_event_id": "use-01J...",
  "trace_id": "trc-01J...",
  "span_id": "spn-01J...",
  "usage_type": "cloud_api_request",
  "client_type": "tccli|sdk",
  "provider": "tencent_cloud",
  "product": "monitor",
  "service": "monitor.tencentcloudapi.com",
  "action": "GetMonitorData",
  "api_version": "2018-07-24",
  "region": "ap-guangzhou",
  "api_request_id": "request-id",
  "request_count": 4,
  "success_count": 4,
  "failure_count": 0,
  "retry_count": 0,
  "throttle_count": 0,
  "request_bytes": 1200,
  "response_bytes": 8400,
  "resource_count": 12,
  "metric_points_read": 1440,
  "log_bytes_read": 0,
  "query_window_start": "2026-07-25T09:00:00Z",
  "query_window_end": "2026-07-25T10:00:00Z",
  "cache_hit": false,
  "quantity": 4,
  "unit": "api_request",
  "pricing_version": "tencent-cloud-2026-07-25",
  "estimated_cost": null,
  "currency": "CNY",
  "cost_status": "unpriced"
}
```

### 5.4 Data UsageEvent

```json
{
  "usage_event_id": "use-01J...",
  "trace_id": "trc-01J...",
  "span_id": "spn-01J...",
  "usage_type": "metric_points|log_bytes|events|topology_nodes|compute_ms|storage_bytes",
  "product": "monitor|cls|cloudaudit|topology|local",
  "quantity": 1440,
  "unit": "metric_point",
  "pricing_version": "tencent-cloud-2026-07-25",
  "estimated_cost": null,
  "cost_status": "unpriced"
}
```

### 5.5 CostAllocation

```json
{
  "cost_allocation": {
    "tenant_id": "tenant-xxx",
    "customer_id": "customer-xxx",
    "account_id_hash": "sha256:...",
    "project_id": "project-xxx",
    "business_unit": "ops",
    "service_name": "payment-api",
    "environment": "production",
    "region": "ap-guangzhou",
    "product": "monitor",
    "resource_id_hash": "sha256:...",
    "cost_center": "cc-ops",
    "charge_type": "shared|direct|unallocated",
    "allocation_method": "resource|request|usage|equal_split",
    "allocation_ratio": 1.0
  }
}
```

### 5.6 PricingSnapshot

价格独立于原始用量：

```json
{
  "pricing_version": "tencent-cloud-2026-07-25",
  "provider": "tencent_cloud",
  "currency": "CNY",
  "effective_at": "2026-07-25T00:00:00Z",
  "source": "official_catalog|internal_rate_card|manual",
  "items": [
    {
      "product": "monitor",
      "action": "GetMonitorData",
      "usage_type": "api_request",
      "unit": "request",
      "unit_price": null,
      "price_status": "not_applicable|priced|unknown"
    }
  ]
}
```

## 6. 成本状态

禁止把未知价格写成 0：

- `actual`：账单或官方实际费用。
- `estimated`：按价格快照估算。
- `partial`：仅覆盖部分用量。
- `unpriced`：有用量但暂无价格。
- `not_applicable`：该产品/接口不适用该计费维度。

## 7. 落盘与兼容

### 7.1 三层数据

1. `Trace Summary`：面向查询和报告，汇总总 token、API 请求、数据量、成本和归因键。
2. `SpanRecord`：面向链路，记录 Copilot、Skill、GCL、LLM、Cloud API、Verification 节点。
3. `UsageEvent`：面向 FinOps，记录不可变事实用量，价格后算。

### 7.2 建议路径

```text
.runtime/traces/{trace_id}/summary.json
.runtime/traces/{trace_id}/spans.jsonl
.runtime/usage/usage-events.jsonl
.runtime/pricing/pricing-snapshot-{pricing_version}.json
```

现有路径继续保留：

- `audit-results/gcl-trace-*.json`
- `.runtime/gcl/copilot/audit/{run_id}/step-*.json`
- `.runtime/metrics/metrics.jsonl`
- `.runtime/health/skill-metrics.jsonl`

新增数据通过 `trace_id` 和 `span_id` 关联，不能破坏旧读取器。

## 8. 安全与隐私

- 资源 ID、账号 ID 和项目 ID 默认哈希；报告中只保留必要脱敏值。
- 禁止记录 SecretId、SecretKey、Token、Authorization header 和原始凭证。
- Prompt/response 只保存摘要、哈希或受控引用，默认不落原文。
- 所有 Prometheus 标签使用低基数、脱敏值；禁止把资源 ID、request ID 作为标签。
- UsageEvent 必须经过 secret scan 和敏感字段校验。

## 9. FinOps 查询能力

最低支持以下查询：

- Skill/版本/提交的总成本、Token 和 API 用量。
- 产品、Action、Region、租户和业务线的 API 用量。
- 单次 Incident 的 LLM、Cloud API、数据读取和总成本。
- GCL 重试、Critic、Generator、Summarizer 的增量成本。
- 成本与 MTTR、RCA 准确率、告警压缩率的联合分析。
- 同一用量在不同价格快照下的重算结果。

## 10. Self-check / Self-verify

实现必须满足：

```python
assert trace_schema_version == "2.0"
assert trace_id and span_id
assert skill.name and skill.version
assert usage_event_id and usage_type and quantity >= 0
assert cost_status != "estimated" or pricing_version
assert cost_status != "actual" or pricing_source
assert no_secret_fields(record)
assert every_usage_event_is_joinable_to_trace_or_span()
assert unknown_price_is_not_serialized_as_zero()
assert legacy_gcl_and_copilot_readers_still_parse()
```

## 11. 文件清单

| 文件 | 动作 |
|---|---|
| `qcloud-copilot/copilot/trace_context.py` | 新增统一上下文和 ID 层级 |
| `qcloud-copilot/copilot/trace_records.py` | 新增 Trace/Observation/Score/UsageEvent/CostRecord/Summary 数据模型 |
| `qcloud-copilot/copilot/usage.py` | 新增 LLM/API/数据用量采集器 |
| `qcloud-copilot/copilot/cost.py` | 新增价格快照与成本状态处理 |
| `qcloud-copilot/copilot/quality/audit.py` | 增加版本、关联键并保持兼容 |
| `qcloud-copilot/copilot/integration/gcl.py` | 传递 trace/span 上下文及 GCL 版本信息 |
| `qcloud-copilot/copilot/observ.py` | 复用 OBS-1 sink，增加 span/usage 写入 |
| `qcloud-copilot/assets/trace-record.schema.json` | 新增 TraceRecord Schema |
| `qcloud-copilot/assets/usage-event.schema.json` | 新增 UsageEvent Schema |
| `qcloud-copilot/tests/test_trace_records.py` | 数据模型与安全测试 |
| `qcloud-copilot/tests/test_usage_cost.py` | 用量、价格和成本状态测试 |
| `scripts/trace_cost_aggregate.py` | 新增 FinOps 聚合查询脚本 |
| `scripts/trace_cost_aggregate_test.py` | 聚合和重算测试 |
| `docs/superpowers/specs/trace-usage-finops-design.md` | 本设计文档 |
| `docs/superpowers/plans/trace-usage-finops-plan.md` | 实施计划 |

## 12. Langfuse 兼容设计

### 12.1 对齐原则

TRACE-1 采用 Langfuse 的核心语义，不直接复制其内部数据库字段：

- 一个 `TraceRecord` 对应 Langfuse 的 Trace。
- 一个 `SpanRecord` 对应 Langfuse 的 Observation/Span。
- LLM 调用对应 `Generation` observation。
- tccli/SDK/本地脚本调用对应 `Span` 或 `Tool` observation。
- 人工确认、GCL Critic、验证和评估结果作为子 observation 或 Score。
- 腾讯云产品、Skill 版本、FinOps 用量和成本作为标准字段之外的受控 `metadata` 或独立 `UsageEvent`。

不能把所有信息塞进 `metadata`：`user_id`、`session_id`、`name`、`version`、`input`、`output`、`usage`、`status` 等需要保持一等字段，便于 Langfuse 查询和 UI 展示。

### 12.2 Langfuse 风格对象映射

| TRACE-1 | Langfuse 语义 | 说明 |
|---|---|---|
| `trace_id` | Trace `id` | 一次完整请求/任务/Incident 链路 |
| `request_context.session_id` | `session_id` | 会话级关联，不能放入 metadata 替代 |
| `tenant.customer_id` | `user_id` 或受控 metadata | 仅在语义确实是终端用户时使用 `user_id` |
| `trace.started_at/ended_at` | Trace timestamps | 保持 ISO-8601 UTC |
| `span_id` | Observation `id` | 所有子节点唯一 |
| `parent_span_id` | Observation parent | 构建父子树 |
| `trace_type=skill` | Span | Skill 执行节点 |
| `trace_type=llm` | Generation | 记录 model、provider、token usage、cost |
| `trace_type=api` | Span/Tool | 记录产品、Action、RequestId 和请求结果 |
| `trace_type=verification` | Span/Event | 修复后验证和回滚判断 |
| `skill.name` | Observation `name` | 建议使用稳定低基数名称 |
| `skill.version` | Observation `version` | 记录执行版本 |
| `skill.skill_commit` | metadata `skill_commit` | 代码可复现信息 |
| `plan/operation` | metadata/input | 计划和操作上下文 |
| `input` | Observation input | 默认摘要/引用，敏感内容脱敏 |
| `output` | Observation output | 默认结构化摘要/引用 |
| `llm_usage` | Generation usage | 标准 token 字段优先 |
| `estimated_cost` | Generation cost | 记录金额、币种、价格版本和状态 |
| `outcome.review_outcome` | Score | 人工/自动结果反馈 |
| `tags` | Trace/Observation tags | 低基数、可筛选标签 |
| `metadata` | Trace/Observation metadata | 仅放扩展属性，不承载核心字段 |

本仓库的身份映射规则：`session_id` 只映射 Langfuse `session_id`；真实终端用户才映射 `user_id`；`tenant_id`、`customer_id`、`operator_id` 和 `account_id_hash` 保持独立一等字段或受控扩展字段，禁止静默互换。

### 12.3 推荐的 Langfuse-aligned TraceRecord

```json
{
  "id": "trc-01J...",
  "name": "qcloud-aiops-diagnosis",
  "timestamp": "2026-07-25T10:00:00Z",
  "input": {"type": "diagnose", "summary": "sanitized"},
  "output": {"status": "success", "finding_count": 3},
  "user_id": null,
  "session_id": "ses-xxx",
  "release": "release-xxx",
  "version": "2.5.2",
  "environment": "production",
  "tags": ["aiops", "diagnosis", "tencent-cloud"],
  "metadata": {
    "trace_schema_version": "2.0",
    "incident_id": "inc-xxx",
    "tenant_id": "tenant-xxx",
    "customer_id": "customer-xxx",
    "operator_id": "operator-xxx",
    "account_id_hash": "sha256:...",
    "business_unit": "ops",
    "region": "ap-guangzhou",
    "products": ["monitor", "cvm"],
    "skill_commit": "abcdef",
    "references_sha256": "sha256:...",
    "prompt_version": "aiops-rca-v2",
    "rubric_version": "v1"
  },
  "status": "success",
  "latency_ms": 3000,
  "observations": ["obs-01J...", "obs-01J..."],
  "scores": ["score-01J..."]
}
```

### 12.4 推荐的 ObservationRecord

```json
{
  "id": "obs-01J...",
  "trace_id": "trc-01J...",
  "parent_observation_id": "obs-parent",
  "type": "SPAN|GENERATION|EVENT",
  "name": "GetMonitorData",
  "start_time": "2026-07-25T10:00:00Z",
  "end_time": "2026-07-25T10:00:01Z",
  "input": {"action": "GetMonitorData", "parameters_hash": "sha256:..."},
  "output": {"request_id": "masked", "status": "success"},
  "metadata": {
    "skill_name": "qcloud-aiops-diagnosis",
    "skill_version": "2.5.2",
    "provider": "tencent_cloud",
    "product": "monitor",
    "action": "GetMonitorData",
    "region": "ap-guangzhou",
    "client_type": "tccli"
  },
  "status_message": null,
  "level": "DEFAULT",
  "version": "2.5.2",
  "usage": null,
  "cost": null
}
```

### 12.5 GenerationRecord

LLM 记录应尽量采用 Langfuse Generation 语义：

```json
{
  "id": "gen-01J...",
  "trace_id": "trc-01J...",
  "parent_observation_id": "obs-copilot",
  "type": "GENERATION",
  "name": "aiops-generator",
  "model": "model-name",
  "model_parameters": {"temperature": 0.2},
  "input": {"prompt_ref": "sha256:..."},
  "output": {"summary": "sanitized"},
  "usage": {
    "input": 5000,
    "output": 1200,
    "total": 6200,
    "unit": "TOKENS",
    "input_cached": 800,
    "reasoning": 200
  },
  "cost": {
    "input": 0.10,
    "output": 0.07,
    "total": 0.17,
    "currency": "CNY",
    "pricing_version": "pricing-2026-07-25",
    "status": "estimated"
  },
  "metadata": {
    "provider": "provider-name",
    "role": "generator",
    "prompt_template_version": "v2.1",
    "retry_index": 0
  }
}
```

### 12.6 Scores 与反馈

对齐 Langfuse Score 概念，统一反馈结构：

```json
{
  "id": "score-01J...",
  "trace_id": "trc-01J...",
  "observation_id": "obs-01J...",
  "name": "root_cause_accuracy",
  "value": 1.0,
  "data_type": "NUMERIC",
  "source": "human|rule|llm_judge|incident_review",
  "comment": "confirmed",
  "timestamp": "2026-07-25T12:00:00Z"
}
```

GCL rubric、RCA 置信度、修复验证结果和 FinOps 价值评估不应混在同一个字段中，应使用不同的 Score 名称。

### 12.7 OpenTelemetry 兼容边界

Langfuse 的 Trace/Observation 树可映射到 OpenTelemetry：

- `trace_id`、`span_id`、`parent_span_id` 采用 W3C Trace Context 可转换格式。
- Skill、API、Verification 使用 span。
- LLM Generation 保留 `model`、`usage`、`cost` 等 Langfuse 扩展属性。
- 不把高基数的资源 ID、RequestId、原始 Prompt 作为 OTel metrics 标签。
- 本地 JSONL 是事实审计源；Langfuse/OTel 是可选导出目标，不作为本地落盘的前置依赖。

### 12.8 Langfuse 导出适配器

新增导出层，而不是让核心采集器依赖 Langfuse SDK：

```text
TraceRecord/ObservationRecord/UsageEvent
                 │
                 ▼
       LangfuseExporter (optional)
                 │
                 ├── Trace
                 ├── Span / Generation / Event
                 └── Score
```

适配器要求：

- 使用 `trace_id`、`session_id`、`user_id` 的一等字段映射。
- 父子 observation 顺序稳定，支持迟到事件和重试幂等。
- 将 `input/output` 按敏感级别降采样或只发送摘要引用。
- 将 `UsageEvent` 的 token usage 映射到 Generation usage；腾讯云 API 用量保留在 metadata/外部 UsageEvent。
- 将本地成本状态映射到 observation cost，同时保留 `pricing_version` 和 `cost_status`。
- 导出失败不阻塞云操作和本地审计。
- 支持批量、重试、退避和 dead-letter 记录。

## 13. Langfuse 对齐自验证

```python
assert trace.id == trace_id
assert trace.session_id == session_id
assert observation.parent_observation_id in known_observation_ids
assert generation.type == "GENERATION"
assert generation.usage.total == generation.usage.input + generation.usage.output
assert generation.cost.status != "estimated" or generation.cost.pricing_version
assert core_fields_are_first_class_fields_not_metadata_only()
assert export_is_idempotent_by_trace_and_observation_id()
assert exporter_failure_does_not_block_local_audit()
assert sensitive_input_output_is_redacted_before_export()
```

## 14. 架构重构决策

### 14.1 决策

现有“TraceRecord 同时包含 `span_id`、`parent_span_id`、`trace_type`，再由同一记录扩展 AIOps/FinOps 汇总”的结构不作为最终实现结构。改为三类明确对象：

```text
Trace (聚合根，Langfuse Trace 对齐)
  ├── Observation[] (执行树，Langfuse Span/Generation/Event 对齐)
  ├── Score[]       (质量与结果反馈，Langfuse Score 对齐)
  ├── UsageEvent[]  (不可变用量账本，FinOps 事实源)
  └── Summary       (AIOps/FinOps 查询摘要，可重建)
```

### 14.2 为什么要改变当前结构

- `TraceRecord` 不应既代表整条链路又代表某个 span；否则父子关系和聚合边界不清晰。
- Langfuse 的 Trace 是聚合根，Span/Generation/Event 才是执行节点；采用同样语义可以降低导出适配成本。
- FinOps 用量不是一次调用的属性，而是不可变事实事件；单独账本才能支持价格变更、账单校准和重算。
- AIOps 统计字段（告警数、证据数、RCA 置信度、MTTR）是摘要，不应成为唯一事实来源；必须由 Observation/Score/外部事件引用重建。
- Trace Summary 可以被重新聚合，避免运行中不断修改历史执行记录。

### 14.3 新对象职责边界

| 对象 | 负责 | 不负责 |
|---|---|---|
| `Trace` | id、name、session/user、时间、版本、租户、顶层状态、摘要引用 | 单个 API/LLM 调用细节 |
| `Observation` | Skill、GCL、LLM、Cloud API、验证、人工审批执行节点 | 全局成本结算 |
| `Score` | RCA 正确性、数据质量、验证结果、GCL 评分、业务价值反馈 | 原始执行事实 |
| `UsageEvent` | token、API request、日志/指标读取、计算/存储等用量 | 业务结论和质量评分 |
| `CostRecord` | 基于 UsageEvent + PricingSnapshot 的成本结果 | 覆盖原始用量 |
| `Summary` | AIOps/FinOps 查询加速和报表字段 | 作为唯一事实来源 |

### 14.4 推荐 Trace 对象

```json
{
  "id": "trc-01J...",
  "name": "qcloud-aiops-diagnosis",
  "timestamp": "2026-07-25T10:00:00Z",
  "started_at": "2026-07-25T10:00:00Z",
  "ended_at": "2026-07-25T10:00:03Z",
  "status": "success",
  "input": {"type": "diagnose", "summary": "sanitized"},
  "output": {"status": "success", "finding_count": 3},
  "user_id": "customer-xxx",
  "session_id": "ses-xxx",
  "release": "release-xxx",
  "version": "2.5.2",
  "environment": "production",
  "tags": ["aiops", "diagnosis", "tencent-cloud"],
  "metadata": {
    "trace_schema_version": "3.0",
    "tenant_id": "tenant-xxx",
    "incident_id": "inc-xxx",
    "business_unit": "ops",
    "region": "ap-guangzhou",
    "products": ["monitor", "cvm"],
    "skill_commit": "abcdef",
    "prompt_version": "aiops-rca-v2",
    "rubric_version": "v1"
  },
  "aiops_summary": {
    "incident_id": "inc-xxx",
    "incident_class": "performance",
    "severity": "P1",
    "lifecycle_state": "diagnosed",
    "root_cause_confidence": "HIGH",
    "evidence_count": 18,
    "data_quality_status": "complete",
    "affected_resource_count": 12,
    "business_impact_level": "high",
    "verification_status": "pending"
  },
  "finops_summary": {
    "usage_event_count": 10,
    "total_cost": 0.37,
    "currency": "CNY",
    "cost_status": "partial",
    "priced_usage_ratio": 0.62
  },
  "observation_refs": ["obs-01J..."],
  "usage_refs": ["use-01J..."],
  "score_refs": ["score-01J..."],
  "summary_version": "1.0"
}
```

`Trace` 不再包含 `span_id`、`parent_span_id` 或 `trace_type`；这些字段属于 Observation。`user_id` 仅在存在真实终端用户时填写；客户、租户、操作者和云账号使用独立字段。

### 14.5 推荐 Observation 对象

```json
{
  "id": "obs-01J...",
  "trace_id": "trc-01J...",
  "parent_observation_id": "obs-parent",
  "type": "SPAN|GENERATION|EVENT",
  "name": "GetMonitorData",
  "start_time": "2026-07-25T10:00:00Z",
  "end_time": "2026-07-25T10:00:01Z",
  "status": "success|error|partial|skipped",
  "input": {"action": "GetMonitorData", "parameters_hash": "sha256:..."},
  "output": {"request_id_hash": "sha256:...", "resource_count": 12},
  "version": "2.5.2",
  "metadata": {
    "skill_name": "qcloud-aiops-diagnosis",
    "skill_version": "2.5.2",
    "provider": "tencent_cloud",
    "product": "monitor",
    "action": "GetMonitorData",
    "region": "ap-guangzhou",
    "client_type": "tccli",
    "operation_type": "read",
    "retry_index": 0
  },
  "usage_refs": ["use-01J..."],
  "score_refs": [],
  "error": null
}
```

### 14.6 Summary 重建规则

Summary 不是手工维护的第二事实源，必须由以下对象按规则重建：

- `aiops_summary.incident`：Incident/Event 生命周期数据。
- `aiops_summary.evidence`：Evidence observation 的去重计数和 DataQuality Score。
- `aiops_summary.rca`：RCA observation 的 hypothesis 输出和 review Score。
- `aiops_summary.response`：Action/Verification observation。
- `finops_summary.usage`：UsageEvent 按 `trace_id` 聚合。
- `finops_summary.cost`：CostRecord 按 `pricing_version` 聚合。

每个摘要字段应保留 `source_refs` 或能够通过稳定 ID 反查来源；摘要失效时可重建，不能覆盖原始 Observation/UsageEvent。

### 14.7 版本迁移

- 当前 GCL `trace_schema_version=v1` 保留为 legacy reader 输入。
- 新实现使用 `trace_schema_version=3.0`，避免把未兼容的结构称为 v2。
- 提供 `legacy_gcl_to_observation()` 和 `legacy_audit_to_observation()` 适配器。
- 旧文件不原地修改；迁移结果写入新路径并保留 `legacy_source_ref`。
- `TraceRecord v2` 设计文档中的旧单对象结构降级为过渡 DTO，不作为持久化主模型。

## 15. 重构验收标准

```python
assert trace_is_aggregate_root_without_span_fields()
assert every_observation_has_trace_id_and_valid_parent()
assert every_generation_has_langfuse_usage_shape()
assert every_usage_event_is_immutable_and_joinable()
assert summary_can_be_rebuilt_from_observations_scores_and_usage()
assert cost_can_be_recomputed_from_usage_and_pricing_snapshot()
assert legacy_gcl_and_audit_files_are_readable_via_adapters()
assert langfuse_export_uses_trace_observation_generation_score_mapping()
assert aiops_queries_need_no_raw_prompt_or_secret()
assert finops_queries_need_no_unstructured_output_parsing()
assert session_id_is_never_used_as_user_id()
assert customer_id_is_not_silently_mapped_to_user_id()
assert unknown_identity_source_is_explicit()
assert missing_identity_values_serialize_as_json_null()
assert identity_tree_shape_is_stable_across_cli_and_automation()
```

## 16. 开放决策备案：User ID 定义不阻塞主线

**决策状态：Open / Deferred，备案日期：2026-07-25**

### 16.1 决策结论

当前主要运行方式是本地 CLI 和 Agent 定时自动执行，暂时缺少稳定、可信、统一的终端用户身份来源。因此：

- 暂不强行定义或生成统一 `user_id`。
- `user_id` 保留为可选一等字段，没有可靠来源时写 JSON `null`。
- 不使用 `session_id`、本地用户名、机器名、Git 用户名、SecretId 或 Agent 名称冒充 `user_id`。
- `session_id`、`incident_id`、`tenant_id`、`customer_id`、`operator_id`、`service_account_id`、`job_id`、`schedule_id` 和 `agent_id` 继续作为独立归因维度。
- 当前议题不阻塞 Trace v3、AIOps、FinOps、Langfuse 或 OpenTelemetry 优化主线。

### 16.2 当前固定身份树

```json
{
  "identity": {
    "user_id": null,
    "tenant_id": null,
    "customer_id": null,
    "operator_id": null,
    "service_account_id": null,
    "account_id_hash": null,
    "actor_type": null,
    "initiator_type": "cli|schedule|webhook|chat|api|unknown",
    "identity_source": "request|oidc|iam|session|config|automation|local_fallback|unknown",
    "identity_confidence": "verified|declared|inferred|unknown"
  },
  "automation": {
    "job_id": null,
    "schedule_id": null,
    "run_id": null,
    "agent_id": null
  }
}
```

所有字段固定保留；没有可靠值时使用 `null`，不使用空字符串或字符串 `"unknown"` 代替 ID。`identity_source`、`identity_confidence`、`initiator_type` 可以使用枚举值说明缺失原因和入口。

### 16.3 分阶段处理

- **现在**：先实现固定身份树、`null` 缺省、session/incident/automation/tenant/customer 等非用户归因维度。
- **后续**：如果接入 OIDC、SSO、IAM 或统一 Agent Gateway，再使用认证主体的稳定 `sub` 映射为 `user_id`。
- **复审触发**：出现统一认证方案、跨租户用户分析需求、合规审计要求或 Langfuse User 维度成为正式业务指标时，重新评审本决策。

### 16.4 未决问题

- 是否接入统一 OIDC/SSO/IAM 身份中心。
- Agent Gateway 是否生成统一 `operator_id` 或 `service_account_id`。
- 本地 profile 是否允许绑定 tenant/customer，但不伪造 user。
- 自动化任务的 job/schedule/agent 标识是否纳入统一注册中心。
- Langfuse exporter 是否在目标环境允许 `null user_id`，以及是否需要省略该字段。

## 17. 实施前置门禁

本设计在进入任何业务代码修改前必须满足：

1. **SPEC/PLAN Gate**：本 SPEC 和对应 PLAN 完成评审，包含数据结构、架构边界、迁移策略、文件清单、Phase、DoD 和自验证。
2. **GCL Gate**：由 Generator 实施、至少两个隔离 Critic 审查，Critic 不执行云 API 或修改资源；安全评分为 0 时立即停止。
3. **TDD Gate**：每个 Phase 按“失败测试 → 最小实现 → 重构 → 回归验证”执行。
4. **Subagent Orchestrator Gate**：子代理任务必须有明确 owner、互不冲突的写入边界、并发上限和回收策略。
5. **Workspace Gate**：现有未提交修改不得被覆盖、回滚或混入 TRACE-1 无关变更。

在这些门禁完成前，TRACE-1 只允许修改 SPEC/PLAN，不允许修改生产实现代码。
