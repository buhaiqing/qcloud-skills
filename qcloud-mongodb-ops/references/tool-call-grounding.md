# Tool-Call Grounding — MongoDB Skill Integration

> **Scope**: `qcloud-mongodb-ops` SKILL.md 的工具调用 grounding 指引。
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + call validate |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. MongoDB tccli Commands → ToolSchema Registration

在 agent 执行 `tccli mongodb` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeDBInstances — 查询 MongoDB 实例列表
register(ToolSchema(
    name="mongodb_DescribeDBInstances",
    description="查询 MongoDB 实例列表及状态",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "InstanceId":  ParamConstraint(type="string", required=False),
        "Offset":      ParamConstraint(type="number", min_val=0, default=0),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))

# DescribeSpecInfo — 查询实例规格
register(ToolSchema(
    name="mongodb_DescribeSpecInfo",
    description="查询 MongoDB 可用实例规格（Zone/Region 维度）",
    params={
        "Region":  ParamConstraint(type="string", required=True),
        "Zone":    ParamConstraint(type="string", required=True),
    },
    returns={"SpecInfoSet": list},
    error_codes=list(ErrorCode),
))

# DescribeSlowLogs — 查询慢日志
register(ToolSchema(
    name="mongodb_DescribeSlowLogs",
    description="查询 MongoDB 慢查询日志",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "InstanceId": ParamConstraint(type="string", required=True),
        "StartTime":  ParamConstraint(type="number", required=True),
        "EndTime":    ParamConstraint(type="number", required=True),
        "Offset":     ParamConstraint(type="number", min_val=0, default=0),
        "Limit":      ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "SlowLogList": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("mongodb_DescribeDBInstances", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. MongoDB State Dependencies

MongoDB 实例操作有依赖链（先查规格 → 创建实例 → 查慢日志）：

```
mongodb_describe_spec_info (SpecInfoSet)               ← 前提：查询可用规格
  └── mongodb_create_db_instance (InstanceId)            ← 依赖可用规格
        └── mongodb_describe_db_instances (InstanceId)   ← 依赖 mongodb_create_db_instance.InstanceId
              └── mongodb_describe_slow_logs            ← 依赖 mongodb_describe_db_instances.InstanceId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

MONGODB_SPECS: dict[str, ToolStateSpec] = {
    "mongodb_DescribeDBInstances": ToolStateSpec(
        tool_name="mongodb_DescribeDBInstances",
        provides=["InstanceSet"],
        dependency=StateDependency(requires=[
            StateAtom("mongodb_DescribeSpecInfo", "SpecInfoSet"),
        ]),
    ),
    "mongodb_DescribeSlowLogs": ToolStateSpec(
        tool_name="mongodb_DescribeSlowLogs",
        provides=["SlowLogList"],
        dependency=StateDependency(requires=[
            StateAtom("mongodb_DescribeDBInstances", "InstanceSet[].InstanceId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("mongodb_DescribeDBInstances", {"InstanceSet": [{"InstanceId": "cmgo-abc123"}]})
can, why = tracker.can_call("mongodb_DescribeSlowLogs", MONGODB_SPECS)
# can=True, why=[]
```

---

## 4. MongoDB Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="mongodb_DescribeSlowLogs",
    params={"Region": "ap-guangzhou", "InstanceId": "cmgo-abc123",
            "StartTime": 1735689600, "EndTime": 1736294400},
    reasoning="用户查询 MongoDB 实例慢日志",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["StartTime < EndTime（Unix时间戳）", "Limit ≤ 100"],
    result={"error_code": 0, "SlowLogList": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. MongoDB Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, MONGODB_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("mongodb_DescibeDBInstances", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: mongodb_DescribeDBInstances, ...")

# Case 2: 越界 Limit
reports = detector.detect("mongodb_DescribeDBInstances",
    {"Region": "ap-guangzhou", "Limit": 500})
# → HallucinationReport(mode="param_out_of_range", detail="Param Limit=500 > max 100")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, MONGODB_SPECS, tracker2)
reports = detector2.detect("mongodb_DescribeSlowLogs",
    {"Region": "ap-guangzhou", "InstanceId": "cmgo-unknown",
     "StartTime": 1735689600, "EndTime": 1736294400})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires mongodb_DescribeDBInstances")
```

---

## 6. MongoDB Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe Slow Logs

1. Validate schema  ← validate_call("mongodb_DescribeSlowLogs", params)
2. Check state      ← tracker.can_call("mongodb_DescribeSlowLogs", MONGODB_SPECS)
3. Execute tccli    ← tccli mongodb DescribeSlowLogs ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure      ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
