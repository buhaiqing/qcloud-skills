# P0-1: 统一 AIOps 事件模型（AIOpsEnvelope）设计

> 状态：Draft · 关联 Plan：`docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md` §P0-1
> 前置：P0-0 TRACE-1 Trace v3 已落地（`trace_records.py`）。本设计在其之上定义统一事件信封，不重写 v3 模型。

## 1. 背景与问题

当前仓库存在 4 种不同的 finding/incident 形状与 2 种 handoff schema，互不统一，跨产品事件无法用同一组 ID 串联：

| 现有形状 | 位置 | 关键字段 | 缺身份链路 |
|---|---|---|---|
| Blackboard 消息 | `copilot/blackboard.py` + `assets/blackboard.schema.json` | `session_id/plan_id/status/shared_context` | 无 `trace_id/incident_id/causation_id/tenant` |
| TraceRecord v3 | `copilot/trace_records.py` | `trace_id/session_id/user_id/...` | 无 `tenant/region/incident_id/causation_id` 一等字段 |
| Finding (aiops) | `qcloud-aiops-diagnosis/lib/finding_fingerprint.py` | `metric/resource_id/direction/window_minutes/hash` | 无 `schema_version/severity/confidence` |
| Finding (proactive) | `qcloud-proactive-inspection` | `severity/resource_id/metric_name` | 无 `trace_id` |
| Incident (MTTR) | `references/mttr-tracking.md` | `incident_id/detected_at/status/severity` | 仅 `incident_id` |
| handoff: inspection | `assets/inspection-handoff.schema.json` | `handoff_id/findings[]` | 无 `trace_id/incident_id/causation_id/tenant` |
| handoff: finops | `assets/finops-handoff.schema.json` | `anomaly/time_window/owner` | 无 `trace_id/incident_id/causation_id/tenant` |

**核心缺口**（已由代码核实）：
1. `causation_id` 在全代码库**完全缺失**。
2. `tenant/region` 分散在 `IdentityTree`/`AttributionTree`/`metadata`，未一等化到事件/握手。
3. `data_quality`、`decision`、`action_state` 无统一字段。
4. 无统一信封 schema、无 JSON Schema 校验、无破坏性变更检测、无契约测试。
5. 跨 Skill handoff 不携带 `trace_id/incident_id/causation_id`，无法串联告警→诊断→处置→复盘。

## 2. 目标

- 设计统一的 `AIOpsEnvelope`，覆盖租户、地域、trace、incident、资源、时间窗口、证据、数据质量、置信度、决策和动作状态。
- 定义 Event / RCA / Anomaly / Inspection / Blackboard payload 到信封的映射关系。
- 引入 `schema_version` + 兼容策略 + JSON Schema 校验。
- 为所有跨 Skill handoff 增加 `trace_id`、`incident_id`、`causation_id`。
- 增加 Schema fixture、破坏性变更检测和契约测试。
- 验收：任一跨产品事件可通过同一组 ID 串联告警、诊断、处置和复盘。

## 3. 非目标

- 不重写 P0-0 的 TraceRecord v3 模型；信封是它的**外层包装**（envelope 包裹 trace_id 引用，非替代）。
- 本阶段不实现 P0-3 Incident 状态机（信封只携带 `incident.status` 快照，状态转移逻辑归 P0-3）。
- 本阶段不实现 P0-4 修复后验证闭环（信封只携带 `action_state` 字段，验证逻辑归 P0-4）。
- 不改变现有 Blackboard / handoff schema 的既有必填字段；采用**渐进包裹**（先加信封层 + 身份字段，不删除旧字段）。

## 4. 架构

```
                    ┌─────────────────────────────────────────┐
                    │           AIOpsEnvelope (v0.1)          │
                    │  schema_version / event_id / event_type │
                    │  trace_id · incident_id · causation_id  │
                    │  tenant_id · region · resource          │
                    │  time_window · evidence · data_quality  │
                    │  confidence · decision · action_state   │
                    └───────────────┬─────────────────────────┘
                                    │ wraps
        ┌──────────┬────────────┬───┴───────┬────────────┬──────────┐
        ▼          ▼            ▼           ▼            ▼          ▼
   Blackboard  TraceRecord  Finding(aiops) Finding(pro) Incident  Handoff
```

**关键决策**：信封是**包装层（wrapper）**，不侵入既有 payload 结构。每个事件被打包为 `{"envelope": {...}, "payload": <原始形状>}`。这样：
- 旧消费者仍可读 `payload`，不受破坏。
- 新消费者优先读 `envelope` 实现统一身份串联。
- `schema_version` 在信封上，兼容策略基于信封版本演进。

## 5. Schema

### 5.1 `AIOpsEnvelope`（JSON Schema v0.1）

```jsonc
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AIOpsEnvelope",
  "type": "object",
  "required": [
    "schema_version", "event_id", "event_type",
    "trace_id", "timestamp"
  ],
  "properties": {
    "schema_version": { "const": "0.1" },
    "event_id":        { "type": "string", "pattern": "^evt-[A-Za-z0-9_-]{8,}$" },
    "event_type":      { "enum": ["alarm","rca","anomaly","inspection","incident","blackboard","action","evidence"] },
    "timestamp":       { "type": "string", "format": "date-time" },
    "tenant_id":       { "type": ["string","null"] },
    "region":          { "type": ["string","null"] },
    "trace_id":        { "type": "string" },
    "incident_id":     { "type": ["string","null"] },
    "causation_id":    { "type": ["string","null"] },
    "resource": {
      "type": ["object","null"],
      "properties": {
        "product": { "type": "string" },
        "resource_id": { "type": "string" },
        "service_code": { "type": ["string","null"] }
      },
      "required": ["product", "resource_id"]
    },
    "time_window": {
      "type": ["object","null"],
      "properties": {
        "start": { "type": "string", "format": "date-time" },
        "end":   { "type": "string", "format": "date-time" }
      }
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": { "type": "string" },
          "ref_id": { "type": "string" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "required": ["source"]
      }
    },
    "data_quality": {
      "type": ["object","null"],
      "properties": {
        "status":      { "enum": ["ok","degraded","missing"] },
        "freshness_ms":{ "type": ["integer","null"] },
        "coverage_ratio": { "type": ["number","null"], "minimum": 0, "maximum": 1 },
        "missing_sources": { "type": "array", "items": { "type": "string" } }
      },
      "required": ["status"]
    },
    "confidence": { "type": ["number","null"], "minimum": 0, "maximum": 1 },
    "decision": {
      "type": ["object","null"],
      "properties": {
        "maker": { "type": "string" },
        "severity": { "enum": ["P0","P1","P2","P3","INFO"] },
        "priority": { "type": ["integer","null"] }
      }
    },
    "action_state": {
      "type": ["string","null"],
      "enum": [null, "pending", "executing", "verifying", "resolved", "rolled_back", "needs_human"]
    },
    "payload": { "description": "原始事件形状（不破坏既有结构）" }
  },
  "additionalProperties": false
}
```

### 5.2 身份字段映射

| envelope 字段 | 来源（现有代码） |
|---|---|
| `trace_id` | `TraceRecord.id` / `cruise_logger` 的 `trace_id` |
| `tenant_id` | `IdentityTree.tenant_id` / `AttributionTree.tenant_id`（可空） |
| `region` | `UsageEvent.region` / `AttributionTree.region` / blackboard `inspection_strategy.region` |
| `incident_id` | `AIOpsSummary.incident_id` / MTTR `incident_id`（可空） |
| `causation_id` | **新字段**（本设计引入），由握手生产者生成 `caus-<hash>`，缺省 `null` |
| `resource` | finding `resource_id` / blackboard finding `resource_id` |

### 5.3 兼容策略

- **向后兼容**：信封只新增包装层，`payload` 保留原始形状；现有 schema 的必填字段不删除、不重命名。
- **渐进要求**：`trace_id` 在 v0.1 即必填；`tenant_id`/`incident_id`/`causation_id` 为可空（`null`），生产者尽力填充，不阻塞（对齐 P0-0 的 User ID 开放议题：本地/自动化运行无值用 `null`）。
- **版本演进**：`schema_version` 常量约束；新增字段 = minor（向后兼容），删除/重命名必填字段 = major（触发破坏性变更检测）。

### 5.4 破坏性变更检测

- 对 `*.schema.json` 比较相邻版本：删除必填字段、收紧 `enum`、`additionalProperties:false` 下新增被拒绝字段 → 判为破坏性变更。
- 工具：新增 `scripts/validate_aiops_envelope.py`（含 schema 校验 + 破坏性检测）。

## 6. 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/superpowers/specs/aiops-envelope-design.md` | 设计文档 | 本文档 |
| `qcloud-aiops-diagnosis/assets/aiops-envelope.schema.json` | JSON Schema | 统一信封 schema（§5.1） |
| `qcloud-aiops-diagnosis/assets/aiops-envelope.fixtures.json` | fixture | 正常/异常/缺失数据/权限失败/多故障场景样本 |
| `qcloud-copilot/copilot/aiops_envelope.py` | 实现 | `wrap(event_type, payload, *, trace_id, ...) -> dict` 包装函数 + 校验 |
| `scripts/validate_aiops_envelope.py` | 校验/契约 | schema 校验 + 破坏性变更检测 + fixture 回放 |
| `scripts/test_aiops_envelope.py` | 测试 | 包装正确性、schema 校验、身份串联、破坏性检测 |

## 7. 算法/函数签名

```python
# qcloud-copilot/copilot/aiops_envelope.py
def wrap(
    event_type: str,
    payload: dict,
    *,
    trace_id: str,
    timestamp: str | None = None,
    tenant_id: str | None = None,
    region: str | None = None,
    incident_id: str | None = None,
    causation_id: str | None = None,
    resource: dict | None = None,
    time_window: dict | None = None,
    evidence: list[dict] | None = None,
    data_quality: dict | None = None,
    confidence: float | None = None,
    decision: dict | None = None,
    action_state: str | None = None,
) -> dict:
    """将原始事件包装为 AIOpsEnvelope 字典。event_id 自动生成 evt-<uuid8>。
    返回的 dict 必须通过 aiops-envelope.schema.json 校验。"""

def validate(envelope: dict, schema: dict | None = None) -> list[str]:
    """校验 envelope 是否符合 schema，返回错误列表（空 = 合法）。"""

def new_causation_id(seed: str) -> str:
    """由触发事件生成 caus-<sha256(seed)[:12]>。"""
```

## 8. Self-check / 自验

- 契约：`wrap()` 对全部 8 种 `event_type` 产物均通过 `validate()`（空错误列表）。
- 串联：同一 incident 的 alarm/rca/action 信封共享 `trace_id`+`incident_id`；根因事件含 `causation_id`，其它引用它。
- 兼容：对旧 payload 包装后，`payload` 内容与输入逐字段一致（不改写）。
- 脱敏：信封不含 SecretId/SecretKey/原始凭证。
- 破坏性检测：人为构造「删除必填字段」的 schema 变更 → 工具判为 breaking；反向不报。
- 门禁：`ruff check` 零 error；`scripts/validate_aiops_envelope.py` 全绿；`python3 scripts/validate_local.py` 不回归。

## 9. Phase 清单（PLAN）

- [ ] **Phase 0**: 写本文档（SPEC）+ 冻结 envelope schema（§5.1）。
- [ ] **Phase 1**: 建 `qcloud-aiops-diagnosis/assets/aiops-envelope.schema.json` + `fixtures.json`。
- [ ] **Phase 2**: 写 `qcloud-copilot/copilot/aiops_envelope.py`（wrap/validate/new_causation_id）。
- [ ] **Phase 3**: 写 `scripts/validate_aiops_envelope.py`（校验 + 破坏性检测 + fixture 回放）。
- [ ] **Phase 4**: 写 `scripts/test_aiops_envelope.py`（包装、校验、串联、兼容、脱敏、破坏性）。
- [ ] **Phase 5**: 将 `trace_id/incident_id/causation_id` 接入 2 个 handoff schema 的**信封层**（inspection-handoff、finops-handoff）。
- [ ] **Phase 6**: ruff + 全量测试 + `validate_local.py` + 本 SPEC 逐条对照（✅/⚠️/❌）。

## 10. DoD / 验收标准

- [ ] `wrap()` + `validate()` 有测试覆盖，全绿。
- [ ] 任一跨产品事件可通过同一 `trace_id`/`incident_id` 串联；根因经 `causation_id` 关联。
- [ ] 2 个 handoff schema 的信封层携带 `trace_id/incident_id/causation_id`。
- [ ] 破坏性变更检测工具可判 breaking/非 breaking。
- [ ] 无凭证/敏感信息写入信封。
- [ ] `ruff check` 零 error、`validate_aiops_envelope.py` 全绿、`validate_local.py` 不回归。
