# Tool-Call Grounding — Monitor Skill Integration

> **Scope**: `qcloud-monitor-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. Monitor tccli Commands → ToolSchema Registration

Monitor 是**只读/无状态**为主的产品（AlarmPolicy 生命周期除外）。以下为核心命令 schema：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeAlarmPolicies
register(ToolSchema(
    name="monitor_DescribeAlarmPolicies",
    description="查询告警策略列表",
    params={
        "Region":    ParamConstraint(type="string", required=True),
        "Module":    ParamConstraint(type="string", default="monitor"),
        "Namespace": ParamConstraint(type="string", required=False),
        "Offset":    ParamConstraint(type="number", min_val=0,  default=0),
        "Limit":     ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"Policies": list, "TotalCount": int},
    error_codes=list(ErrorCode),
))

# CreateAlarmPolicy
register(ToolSchema(
    name="monitor_CreateAlarmPolicy",
    description="创建告警策略",
    params={
        "Region":         ParamConstraint(type="string", required=True),
        "Module":         ParamConstraint(type="string", default="monitor"),
        "PolicyName":     ParamConstraint(type="string", required=True, max_length=60),
        "Namespace":      ParamConstraint(type="string", required=True),
        "MetricName":     ParamConstraint(type="string", required=True),
        "Period":         ParamConstraint(type="number", default=300),
        "Threshold":      ParamConstraint(type="number", required=True),
        "Operator":       ParamConstraint(type="string", required=True),
        "ContinuePeriod": ParamConstraint(type="number", default=2),
    },
    returns={"PolicyId": str},
    error_codes=list(ErrorCode),
))

# DeleteAlarmPolicy
register(ToolSchema(
    name="monitor_DeleteAlarmPolicy",
    description="删除告警策略",
    params={
        "Region":   ParamConstraint(type="string", required=True),
        "Module":   ParamConstraint(type="string", default="monitor"),
        "PolicyIds":ParamConstraint(type="array",  required=True),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# GetMonitorData
register(ToolSchema(
    name="monitor_GetMonitorData",
    description="查询指定指标的监控数据",
    params={
        "Region":        ParamConstraint(type="string", required=True),
        "Namespace":     ParamConstraint(type="string", required=True),
        "MetricName":    ParamConstraint(type="string", required=True),
        "Period":        ParamConstraint(type="number", default=60),
        "StartTime":     ParamConstraint(type="number", required=True),  # Unix timestamp
        "EndTime":       ParamConstraint(type="number", required=True),
        "Instances":     ParamConstraint(type="array",  required=True),
    },
    returns={"MetricDataPoints": list},
    error_codes=list(ErrorCode),
))

# DescribeAllNamespaces
register(ToolSchema(
    name="monitor_DescribeAllNamespaces",
    description="查询所有监控命名空间",
    params={
        "Region":   ParamConstraint(type="string", required=True),
        "Module":   ParamConstraint(type="string", default="monitor"),
        "Offset":   ParamConstraint(type="number", min_val=0,  default=0),
        "Limit":    ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"Namespaces": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("monitor_GetMonitorData",
    {"Region": "ap-guangzhou", "Namespace": "QCE/CVM",
     "MetricName": "CPUUsage", "StartTime": 1699000000,
     "EndTime": 1699003600, "Instances": [{"Dimensions": {"InstanceId": "ins-xxx"}}]})
# → (True, "", SUCCESS)
```

---

## 3. Monitor State Dependencies

Monitor 操作**以只读为主**，状态依赖相对简单。AlarmPolicy 变更有前置依赖：

```
monitor_CreateAlarmPolicy (PolicyId)       ← 基础：先创建策略
  ├── monitor_DescribeAlarmPolicies        ← 依赖 PolicyId 确认创建成功
  └── monitor_DeleteAlarmPolicy            ← 依赖 PolicyId

# GetMonitorData / DescribeAllNamespaces — 无状态，可直接调用
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

MONITOR_SPECS: dict[str, ToolStateSpec] = {
    "monitor_DeleteAlarmPolicy": ToolStateSpec(
        tool_name="monitor_DeleteAlarmPolicy",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("monitor_CreateAlarmPolicy", "PolicyId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("monitor_CreateAlarmPolicy", {"PolicyId": "policy-12345"})
can, why = tracker.can_call("monitor_DeleteAlarmPolicy", MONITOR_SPECS)
# can=True, why=[]
```

> **Note**: 大部分 Monitor 命令（Describe*/GetMonitorData）是**无状态只读**，无需 StateTracker。StateTracker 主要用于 AlarmPolicy 的 CREATE→DELETE 链。

---

## 4. Monitor Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

# 只读查询的 trace
trace = ToolCallTrace.new(
    tool_name="monitor_GetMonitorData",
    params={"Region": "ap-guangzhou", "Namespace": "QCE/CVM",
            "MetricName": "CPUUsage", "Period": 60,
            "StartTime": 1699000000, "EndTime": 1699003600,
            "Instances": [{"Dimensions": {"InstanceId": "ins-xxx"}}]},
    reasoning="用户请求查看 CVM 实例 CPU 使用率",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["StartTime/EndTime 为 Unix 时间戳", "Namespace 必须是有效命名空间"],
    result={"error_code": 0, "data": {"MetricDataPoints": [...]}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. Monitor Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, MONITOR_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("monitor_DesribeAlarmPolicies", {"Region": "ap-guangzhou"})
# → mode="tool_not_found"

# Case 2: 参数越界（Limit 超限）
reports = detector.detect("monitor_DescribeAlarmPolicies",
    {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建策略就删除）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, MONITOR_SPECS, tracker2)
reports = detector2.detect("monitor_DeleteAlarmPolicy",
    {"Region": "ap-guangzhou", "PolicyIds": ["policy-xxx"]})
# → mode="state_not_satisfied", detail="Requires monitor_CreateAlarmPolicy.PolicyId"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateAlarmPolicy

1. validate_call("monitor_CreateAlarmPolicy", params)  ← 参数 schema 校验
2. tracker.can_call("monitor_CreateAlarmPolicy", MONITOR_SPECS)  ← 状态依赖检查
3. Execute tccli monitor CreateAlarmPolicy ...
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination

## Execute: GetMonitorData (无状态路径)

1. validate_call("monitor_GetMonitorData", params)    ← 参数校验
2. Execute tccli monitor GetMonitorData ...            ← 无需 StateTracker
3. ToolCallTrace.new(...) → audit log
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
