# Tool-Call Grounding — Redis Skill Integration

> **Scope**: `qcloud-redis-ops` SKILL.md 的工具调用 grounding 指引。  
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

## 2. Redis tccli Commands → ToolSchema Registration

在 agent 执行 `tccli redis` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateInstance
register(ToolSchema(
    name="redis_CreateInstance",
    description="创建 Redis 实例",
    params={
        "Region":       ParamConstraint(type="string", required=True),
        "Zone":         ParamConstraint(type="string", required=True),
        "Memory":       ParamConstraint(type="number", min_val=256,   required=True),
        "VpcId":        ParamConstraint(type="string", required=True),
        "SubnetId":     ParamConstraint(type="string", required=True),
        "InstanceName": ParamConstraint(type="string", required=False, max_length=60),
        "Password":     ParamConstraint(type="string", required=False, max_length=32),
        "ChargeType":   ParamConstraint(type="enum",  enum_values=["PREPAID","POSTPAID"], default="POSTPAID"),
        "Period":       ParamConstraint(type="number", min_val=1, max_val=36, default=1),
    },
    returns={"InstanceId": str},
    error_codes=list(ErrorCode),
))

# DescribeInstances (single)
register(ToolSchema(
    name="redis_DescribeInstances",
    description="查询单个 Redis 实例详情",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "InstanceId": ParamConstraint(type="string", required=True),
    },
    returns={"InstanceSet": list},
    error_codes=list(ErrorCode),
))

# DescribeInstanceList (paginated)
register(ToolSchema(
    name="redis_DescribeInstanceList",
    description="分页查询 Redis 实例列表",
    params={
        "Region": ParamConstraint(type="string", required=True),
        "Offset": ParamConstraint(type="number", min_val=0,  default=0),
        "Limit":  ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))

# UpgradeInstance
register(ToolSchema(
    name="redis_UpgradeInstance",
    description="升级 Redis 实例规格",
    params={
        "Region":       ParamConstraint(type="string", required=True),
        "InstanceId":   ParamConstraint(type="string", required=True),
        "Memory":       ParamConstraint(type="number", min_val=256, required=True),
        "UpgradeType":  ParamConstraint(type="string", enum_values=["1","2"], required=True),
    },
    returns={"TradeDealDetailId": str},
    error_codes=list(ErrorCode),
))

# IsolateInstance
register(ToolSchema(
    name="redis_IsolateInstance",
    description="隔离 Redis 实例（软删除）",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "InstanceId": ParamConstraint(type="string", required=True),
    },
    returns={"InstanceIds": list},
    error_codes=list(ErrorCode),
))

# CleanInstance
register(ToolSchema(
    name="redis_CleanInstance",
    description="销毁已隔离的 Redis 实例（硬删除）",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "InstanceId": ParamConstraint(type="string", required=True),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("redis_DescribeInstances",
    {"Region": "ap-guangzhou", "InstanceId": "crs-abc"})
# → (True, "", SUCCESS)
```

---

## 3. Redis State Dependencies

Redis 操作有严格的状态依赖：

```
redis_CreateInstance (InstanceId)           ← 基础：先创建实例
  ├── redis_DescribeInstances (polling)    ← 依赖 InstanceId 查 Status=2(running)
  ├── redis_UpgradeInstance                 ← 依赖 Status=2
  ├── redis_IsolateInstance                 ← 依赖 Status=2
  └── redis_CleanInstance                   ← 依赖 Status=3(isolated)
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

REDIS_SPECS: dict[str, ToolStateSpec] = {
    "redis_UpgradeInstance": ToolStateSpec(
        tool_name="redis_UpgradeInstance",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("redis_CreateInstance", "InstanceId"),
        ]),
    ),
    "redis_CleanInstance": ToolStateSpec(
        tool_name="redis_CleanInstance",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("redis_IsolateInstance", "InstanceIds"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("redis_CreateInstance", {"InstanceId": "crs-abc123"})
can, why = tracker.can_call("redis_UpgradeInstance", REDIS_SPECS)
# can=True, why=[]
```

---

## 4. Redis Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="redis_CreateInstance",
    params={"Region": "ap-guangzhou", "Zone": "100001",
             "Memory": 1024, "VpcId": "vpc-abc",
             "SubnetId": "subnet-xyz", "InstanceName": "my-redis"},
    reasoning="用户请求创建 1GB 内存的 Redis 实例",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Zone 必须是可用区 ID（如 100001）", "VpcId/SubnetId 须已存在"],
    result={"error_code": 0, "data": {"InstanceId": "crs-xyz"}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. Redis Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, REDIS_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("redis_DesribeInstances", {"Region": "ap-guangzhou", "InstanceId": "crs-xxx"})
# → mode="tool_not_found"

# Case 2: 参数越界（Memory 低于最小值）
reports = detector.detect("redis_CreateInstance",
    {"Region": "ap-guangzhou", "Zone": "100001",
     "Memory": 64, "VpcId": "vpc-abc", "SubnetId": "subnet-xyz"})
# → mode="param_out_of_range", detail="Param Memory=64 < min 256"

# Case 3: 状态未满足（实例未隔离就尝试 CleanInstance）
tracker2 = StateTracker()
tracker2.record("redis_CreateInstance", {"InstanceId": "crs-xxx"})
detector2 = GroundingDetector(REGISTRY, REDIS_SPECS, tracker2)
reports = detector2.detect("redis_CleanInstance",
    {"Region": "ap-guangzhou", "InstanceId": "crs-xxx"})
# → mode="state_not_satisfied", detail="Requires redis_IsolateInstance.InstanceIds"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateInstance

1. validate_call("redis_CreateInstance", params)  ← 参数 schema 校验
2. tracker.can_call("redis_CreateInstance", REDIS_SPECS)  ← 状态依赖检查
3. Execute tccli redis CreateInstance ...
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
