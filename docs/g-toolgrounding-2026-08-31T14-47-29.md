# LLM 工具调用 Grounding 严格化设计

> 日期: 2026-08-31
> 任务来源: g-toolgrounding

---

## 1. 工具 Schema 严格化方案

### 1.1 设计目标

- 函数签名（名称、参数类型、返回值结构）严格约束
- 参数边界校验（enum 范围、数值上下限、必填/可选）
- 调用结果的结构化错误码（而非自由文本）

### 1.2 核心组件

权威实现见 `references/toolgrounding/tool_schema.py`，包含 `ErrorCode` 枚举、`ParamConstraint`/`ToolSchema`/`ToolCallResult` dataclass 与 `validate_params()` 校验逻辑。

### 1.3 示例工具注册

注册入口、REGISTRY、validate_call 调用封装见 `references/toolgrounding/tool_schema.py`（`register()` / `REGISTRY` / `validate_call()`）。所有 `qcloud-*-ops` 工具在调用 `validate_call()` 前须先 `register(ToolSchema(...))`。


### 1.4 使用示例

```python
ok, msg, code = validate_call("cvm_describe_instances", {
    "Region": "ap-guangzhou",
    "Limit": 50
})
print(ok, msg, code)  # True None None

ok2, msg2, code2 = validate_call("cvm_describe_instances", {
    "Region": "ap-moon",
    "Limit": 200
})
print(ok2, msg2, code2)  # False Region=ap-moon not in [...] PARAM_OUT_OF_RANGE
```

---

## 2. 工具状态依赖显式化方案

### 2.1 设计目标

- 工具间的隐式状态依赖显式建模
- 依赖链完整性校验（调用前必须满足的前置状态）
- 状态依赖描述 YAML schema

### 2.2 状态依赖模型

权威实现见 `references/toolgrounding/state_dependency.py`，包含 `StateAtom` / `StateDependency` / `ToolStateSpec` dataclass 与 `StateTracker.record()` / `check()` / `can_call()` 校验逻辑。

### 2.4 YAML Schema 示例

```yaml
# tool_state_schema.yaml
state_dependency_version: "1.0"

# 全局状态定义
global_state:
  ccn_id:
    type: string
    description: "CCN 实例 ID，由 ccn_create 返回"
  vpc_id:
    type: string
    description: "VPC 实例 ID，由 vpc_create 或 vpc_describe 返回"
  cdb_instance_id:
    type: string
    description: "CDB 实例 ID，由 cdb_create 返回"

tools:
  cdb_create:
    provides:
      - InstanceId
      - VpcId
    dependency:
      requires: []

  cdb_configure_vpc:
    provides: []
    dependency:
      requires:
        - tool: cdb_create
          output: InstanceId
        - tool: vpc_describe
          output: VpcId

  cdb_create_account:
    provides:
      - AccountName
    dependency:
      requires:
        - tool: cdb_create
          output: InstanceId
          # VpcId must be set (no specific value required)

  cdb_set_cnf:
    provides: []
    dependency:
      requires:
        - tool: cdb_create
          output: InstanceId
        - tool: cdb_create_account
          output: AccountName
          value: "root"  # must be specifically "root" account

  cdb_import_data:
    provides: []
    dependency:
      requires:
        - tool: cdb_set_cnf
          # implicitly requires InstanceId from cdb_create
        - tool: cdb_create_account
          output: AccountName
```

### 2.5 校验示例

```python
tracker = StateTracker()

# 模拟调用链路
tracker.record("ccn_create", {"CcnId": "ccn-123"})
tracker.record("vpc_create", {"VpcId": "vpc-456"})
tracker.record("cdb_create", {"InstanceId": "cdb-789", "VpcId": "vpc-456"})

specs = {
    "cdb_create_account": ToolStateSpec(
        tool_name="cdb_create_account",
        provides=["AccountName"],
        dependency=StateDependency(requires=[
            StateAtom("cdb_create", "InstanceId"),
            StateAtom("vpc_create", "VpcId"),
        ])
    )
}

can, why = tracker.can_call("cdb_create_account", specs)
print(can, why)  # True [] — all deps satisfied

# 尝试跳过 cdb_create 直接调用
tracker2 = StateTracker()
tracker2.record("ccn_create", {"CcnId": "ccn-123"})
can2, why2 = tracker2.can_call("cdb_create_account", specs)
print(can2, why2)  # False ['Requires cdb_create.InstanceId', 'Requires vpc_create.VpcId']
```

---

## 3. 工具调用 Grounding Trace

### 3.1 设计目标

- 每次工具调用附带 grounding metadata（来源、置信度、约束条件）
- 结构化 trace 格式，便于事后回放和幻觉分析

### 3.2 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ToolCallTrace",
  "type": "object",
  "required": ["trace_id", "timestamp", "call", "grounding", "result"],
  "properties": {
    "trace_id": {
      "type": "string",
      "description": "全局唯一追踪 ID"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "call": {
      "type": "object",
      "required": ["tool_name", "params", "reasoning"],
      "properties": {
        "tool_name": { "type": "string" },
        "params": { "type": "object" },
        "reasoning": { "type": "string" },
        "intent": { "type": "string" }
      }
    },
    "grounding": {
      "type": "object",
      "required": ["confidence", "source", "constraints"],
      "properties": {
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "工具/参数选择置信度"
        },
        "source": {
          "type": "string",
          "enum": ["user_instruction", "skill_schema", "previous_result", "inferior_model", "fallback"],
          "description": "参数来源"
        },
        "constraints": {
          "type": "array",
          "items": { "type": "string" },
          "description": "应用的约束条件描述"
        },
        "inferior_model_hint": {
          "type": "string",
          "description": "当 source=inferior_model 时，记录底层模型名称"
        }
      }
    },
    "result": {
      "type": "object",
      "required": ["error_code", "error_name"],
      "properties": {
        "error_code": { "type": "integer" },
        "error_name": { "type": "string" },
        "data": { "type": "object" },
        "message": { "type": "string" },
        "duration_ms": { "type": "number" }
      }
    },
    "state_snapshot": {
      "type": "object",
      "description": "调用前的状态快照"
    }
  }
}
```

### 3.3 Python Dataclass

权威实现见 `references/toolgrounding/grounding_trace.py`，包含 `ParamSource` 枚举、`GroundingMetadata` / `ToolCallTrace` dataclass 与 `to_dict()` / `to_json()` 序列化逻辑。

---

## 4. 幻觉检测边界

### 4.1 三类失效模式

| 模式 | 触发条件 | 检测点 | 处理策略 |
|------|---------|--------|---------|
| **工具不存在** | 调用 `validate_call` 返回 `TOOL_NOT_FOUND` | Schema 注册表 lookup | 返回错误 + 列出相似工具名 |
| **参数越界** | `validate_params` 返回 `PARAM_OUT_OF_RANGE` 或 `PARAM_TYPE_ERROR` | 参数校验层 | 附合法值范围，re-call |
| **状态未满足** | `StateTracker.can_call` 返回 `False` | 调用前拦截 | 返回缺失依赖 + 调用建议 |

### 4.2 检测器实现

权威实现见 `references/toolgrounding/hallucination_detector.py`，包含 `HallucinationReport` dataclass、`GroundingDetector.detect()` 三类失效检测与 stdlib `difflib.get_close_matches()` 模糊匹配（替代自实现 Levenshtein）。

### 4.3 使用示例

```python
detector = GroundingDetector(REGISTRY, specs, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cvm_descrie_instances", {"Region": "ap-guangzhou"})
assert len(reports) == 1
assert reports[0].mode == "tool_not_found"

# Case 2: 参数越界
reports = detector.detect("cvm_describe_instances", {"Region": "ap-moon", "Limit": 200})
assert any(r.mode == "param_out_of_range" for r in reports)

# Case 3: 状态未满足（SPECS 由 detector 构造时传入，不在 params 里）
reports = detector.detect("cdb_create_account", {})
assert any(r.mode == "state_not_satisfied" for r in reports)
```

### 4.4 三类失效模式对照表

```
┌─────────────────────┬──────────────────────────────────────────────┐
│ 失效模式             │ 触发条件                                      │
├─────────────────────┼──────────────────────────────────────────────┤
│ 工具不存在            │ tool_name not in REGISTRY                    │
│                     │ (可能是模型幻觉出工具名 / 拼写错误)              │
├─────────────────────┼──────────────────────────────────────────────┤
│ 参数越界              │ validate_params → PARAM_OUT_OF_RANGE/        │
│                     │ PARAM_TYPE_ERROR/MISSING                       │
│                     │ (可能是模型枚举值幻觉 / 数值范围幻觉)            │
├─────────────────────┼──────────────────────────────────────────────┤
│ 状态未满足            │ StateTracker.can_call → False                 │
│                     │ (隐式依赖未显式建模 / 模型忽略前置调用)          │
└─────────────────────┴──────────────────────────────────────────────┘
```

---

## 5. 文件清单

| 文件 | 用途 |
|------|------|
| `references/toolgrounding/tool_schema.py` | Schema 定义 + 校验器 + 错误码 |
| `references/toolgrounding/state_dependency.py` | 状态依赖模型 + StateTracker |
| `references/toolgrounding/grounding_trace.py` | Trace dataclass + JSON serializer |
| `references/toolgrounding/hallucination_detector.py` | 三类失效检测器 |
| `references/toolgrounding/tool_state_schema.yaml` | YAML 状态依赖 schema 示例 |
| `references/toolgrounding/trace_schema.json` | Trace JSON Schema |
| `references/toolgrounding/_demo.py` | 可运行的完整演示脚本 |

---

## 6. Self-check

```python
# 验证所有模块可导入
import tool_schema, state_dependency, grounding_trace, hallucination_detector
# 验证 detector 对三类模式均有报告
# 验证 trace 可序列化/反序列化
# 验证 state tracker 可正确追踪和校验
```

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
