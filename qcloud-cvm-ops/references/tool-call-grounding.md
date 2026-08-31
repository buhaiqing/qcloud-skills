# Tool-Call Grounding — CVM Skill Integration

> **Scope**: `qcloud-cvm-ops` SKILL.md 的工具调用 grounding 指引。  
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

## 2. CVM tccli Commands → ToolSchema Registration

在 agent 执行 `tccli cvm` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeInstances
register(ToolSchema(
    name="cvm_DescribeInstances",
    description="查询 CVM 实例列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "InstanceIds": ParamConstraint(type="array",  required=False),
        "Offset":      ParamConstraint(type="number", min_val=0,        default=0),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "Status":      ParamConstraint(type="string", required=False),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))

# RunInstances
register(ToolSchema(
    name="cvm_RunInstances",
    description="创建 CVM 实例",
    params={
        "Region":            ParamConstraint(type="string",   required=True),
        "Zone":             ParamConstraint(type="string",   required=True),
        "InstanceType":      ParamConstraint(type="string",   required=True),
        "ImageId":          ParamConstraint(type="string",   required=True),
        "InstanceName":      ParamConstraint(type="string",   required=False, max_length=30),
        "InstanceChargeType":ParamConstraint(type="enum",    enum_values=["POSTPAID_BY_HOUR","PREPAID"], default="POSTPAID_BY_HOUR"),
        "SecurityGroupIds":  ParamConstraint(type="array",    required=False),
        "VpcId":            ParamConstraint(type="string",   required=False),
        "SubnetId":         ParamConstraint(type="string",   required=False),
        "ClientToken":      ParamConstraint(type="string",   required=False),
    },
    returns={"InstanceIdSet": list},
    error_codes=list(ErrorCode),
))

# StartInstances / StopInstances / RebootInstances
for op in ["Start","Stop","Reboot"]:
    register(ToolSchema(
        name=f"cvm_{op}Instances",
        description=f"{op} CVM 实例",
        params={
            "Region":      ParamConstraint(type="string", required=True),
            "InstanceIds": ParamConstraint(type="array",   required=True),
            "StopType":    ParamConstraint(type="string", enum_values=["SOFT","HARD"], required=False),
            "RebootType":  ParamConstraint(type="string", enum_values=["SOFT","HARD"], required=False),
        },
        returns={"RequestId": str},
        error_codes=list(ErrorCode),
    ))

# TerminateInstances
register(ToolSchema(
    name="cvm_TerminateInstances",
    description="删除 CVM 实例",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "InstanceIds": ParamConstraint(type="array",   required=True),
        "DryRun":      ParamConstraint(type="boolean", required=False),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("cvm_DescribeInstances", {"Region": "ap-guangzhou", "Limit": 200})
# → (False, "Param Limit=200 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. CVM State Dependencies

CVM 操作有显式的状态依赖链：

```
cvm_RunInstances (InstanceId)            ← 基础：先创建实例
  ├── cvm_DescribeInstances (polling)   ← 依赖 InstanceId 查询状态
  ├── cvm_StartInstances                 ← 依赖 RUNNING 前置状态
  ├── cvm_StopInstances                 ← 依赖 RUNNING 状态
  ├── cvm_RebootInstances               ← 依赖 RUNNING 状态
  ├── cvm_TerminateInstances            ← 依赖任意已存在实例
  └── cvm_CreateImage                   ← 依赖实例存在
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CVM_SPECS: dict[str, ToolStateSpec] = {
    "cvm_StartInstances": ToolStateSpec(
        tool_name="cvm_StartInstances",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("cvm_RunInstances", "InstanceIdSet"),
        ]),
    ),
    "cvm_StopInstances": ToolStateSpec(
        tool_name="cvm_StopInstances",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("cvm_RunInstances", "InstanceIdSet"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("cvm_RunInstances", {"InstanceIdSet": ["ins-abc123"], "Zone": "ap-guangzhou-3"})
can, why = tracker.can_call("cvm_StartInstances", CVM_SPECS)
# can=True, why=[]
```

---

## 4. CVM Grounding Trace

每次 tccli 调用后生成 trace，记录参数来源和置信度：

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cvm_RunInstances",
    params={"Region": "ap-guangzhou", "Zone": "ap-guangzhou-3",
             "InstanceType": "S5.SMALL1", "ImageId": "img-xxxx"},
    reasoning="用户请求在广州地域创建一台 S5.SMALL1 测试实例",
    confidence=0.88,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Zone 必须是 Region 下的可用区", "InstanceType 需在 DescribeZoneInstanceConfigInfos 范围内"],
    result={"error_code": 0, "data": {"InstanceIdSet": ["ins-xxx"]}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CVM Hallucination Detection

在 agent 执行 tccli 前，用 `GroundingDetector` 拦截三类幻觉：

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CVM_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cvm_DescrieInstances", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="cvm_DescribeInstances, ..."

# Case 2: 参数越界（Limit 超限）
reports = detector.detect("cvm_DescribeInstances",
    {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建实例就 Start）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CVM_SPECS, tracker2)
reports = detector2.detect("cvm_StartInstances",
    {"Region": "ap-guangzhou", "InstanceIds": ["ins-xxx"]})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

在 SKILL.md 的「Execute」步骤中嵌入 grounding：

```
## Execute: RunInstances

1. validate_call("cvm_RunInstances", params)  ← 参数 schema 校验
2. tracker.can_call("cvm_RunInstances", CVM_SPECS)  ← 状态依赖检查
3. Execute tccli cvm RunInstances ...
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
