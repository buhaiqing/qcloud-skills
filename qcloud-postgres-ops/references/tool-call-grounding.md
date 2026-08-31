# Tool-Call Grounding — PostgreSQL Skill Integration

> **Scope**: `qcloud-postgres-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. PostgreSQL tccli Commands → ToolSchema Registration

在 agent 执行 `tccli postgres` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeDBInstances — 查询 PostgreSQL 实例列表
register(ToolSchema(
    name="postgres_DescribeDBInstances",
    description="查询 PostgreSQL 实例列表及状态",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "DBInstanceId": ParamConstraint(type="string", required=False),
        "Offset":      ParamConstraint(type="number", min_val=0, default=0),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "OrderByProject": ParamConstraint(type="number", default=0),
    },
    returns={"TotalCount": int, "DBInstanceSet": list},
    error_codes=list(ErrorCode),
))

# DescribeDBInstanceAttribute — 查询单个实例详情
register(ToolSchema(
    name="postgres_DescribeDBInstanceAttribute",
    description="查询 PostgreSQL 实例属性（规格、版本、存储）",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "DBInstanceId": ParamConstraint(type="string", required=True),
    },
    returns={"DBInstance": dict},
    error_codes=list(ErrorCode),
))

# DescribeSlowQueryList — 查询慢查询日志
register(ToolSchema(
    name="postgres_DescribeSlowQueryList",
    description="查询 PostgreSQL 慢查询语句列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "DBInstanceId": ParamConstraint(type="string", required=True),
        "StartTime":  ParamConstraint(type="string", required=True),
        "EndTime":    ParamConstraint(type="string", required=True),
        "Offset":      ParamConstraint(type="number", min_val=0, default=0),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "SlowQueryList": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("postgres_DescribeDBInstances", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. PostgreSQL State Dependencies

PostgreSQL 实例操作有依赖链（先查列表 → 再查详情 → 再查监控）：

```
postgres_create_instance (DBInstanceId)                 ← 前提：创建实例
  └── postgres_describe_db_instances (DBInstanceId)     ← 依赖 DBInstanceId
        └── postgres_describe_db_instance_attribute     ← 依赖 postgres_describe_db_instances.DBInstanceId
              └── postgres_describe_slow_query_list     ← 依赖 postgres_describe_db_instances.DBInstanceId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

PG_SPECS: dict[str, ToolStateSpec] = {
    "postgres_DescribeDBInstanceAttribute": ToolStateSpec(
        tool_name="postgres_DescribeDBInstanceAttribute",
        provides=["DBInstance"],
        dependency=StateDependency(requires=[
            StateAtom("postgres_DescribeDBInstances", "DBInstanceSet[].DBInstanceId"),
        ]),
    ),
    "postgres_DescribeSlowQueryList": ToolStateSpec(
        tool_name="postgres_DescribeSlowQueryList",
        provides=["SlowQueryList"],
        dependency=StateDependency(requires=[
            StateAtom("postgres_DescribeDBInstances", "DBInstanceSet[].DBInstanceId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("postgres_DescribeDBInstances", {"DBInstanceSet": [{"DBInstanceId": "postgres-abc123"}]})
can, why = tracker.can_call("postgres_DescribeDBInstanceAttribute", PG_SPECS)
# can=True, why=[]
```

---

## 4. PostgreSQL Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="postgres_DescribeSlowQueryList",
    params={"Region": "ap-guangzhou", "DBInstanceId": "postgres-abc123",
            "StartTime": "2026-01-01 00:00:00", "EndTime": "2026-01-07 00:00:00"},
    reasoning="用户查询 PostgreSQL 实例慢查询",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["StartTime < EndTime", "Limit ≤ 100"],
    result={"error_code": 0, "SlowQueryList": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. PostgreSQL Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, PG_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("postgres_DescibeDBInstances", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: postgres_DescribeDBInstances, ...")

# Case 2: 无效 DBInstanceId 格式
reports = detector.detect("postgres_DescribeDBInstanceAttribute",
    {"Region": "ap-guangzhou", "DBInstanceId": "pg-invalid-format!!!"})
# → HallucinationReport(mode="param_out_of_range", detail="DBInstanceId 格式无效")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, PG_SPECS, tracker2)
reports = detector2.detect("postgres_DescribeSlowQueryList",
    {"Region": "ap-guangzhou", "DBInstanceId": "postgres-unknown",
     "StartTime": "2026-01-01", "EndTime": "2026-01-07"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires postgres_DescribeDBInstances")
```

---

## 6. PostgreSQL Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe Instance Attribute

1. Validate schema  ← validate_call("postgres_DescribeDBInstanceAttribute", params)
2. Check state      ← tracker.can_call("postgres_DescribeDBInstanceAttribute", PG_SPECS)
3. Execute tccli    ← tccli postgres DescribeDBInstanceAttribute ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure       ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
