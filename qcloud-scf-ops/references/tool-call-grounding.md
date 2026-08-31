# Tool-Call Grounding — SCF Skill Integration

> **Scope**: `qcloud-scf-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli scf` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. SCF tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateFunction
register(ToolSchema(name="scf_CreateFunction", description="创建云函数", params={
    "Region": ParamConstraint(type="string", required=True),
    "FunctionName": ParamConstraint(type="string", required=True, max_length=64),
    "Runtime": ParamConstraint(type="string", enum_values=["Python3.9","Nodejs16.13","Go1.16","Java8","PHP7.2"], required=True),
    "Code": ParamConstraint(type="object",  required=True),
    "Handler": ParamConstraint(type="string", required=True),
    "MemorySize": ParamConstraint(type="number", min_val=128, max_val=3072, default=128),
    "Timeout": ParamConstraint(type="number", min_val=1, max_val=900, default=3),
    "Namespace": ParamConstraint(type="string", default="default"),
    "VpcId": ParamConstraint(type="string", required=False),
    "SubnetId": ParamConstraint(type="string", required=False),
    }, returns={"FunctionName": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("scf_ListFunctions", {"Region": "ap-guangzhou", "Limit": 9999})
# → (False, "Param Limit=9999 > max 1000", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `scf_ListFunctions` | Region: string*; Namespace: string; Offset: number (min=0, def 0); Limit: number (min=1, max=1000, def 20) | TotalCount, Functions |
| `scf_CreateTrigger` | Region: string*; FunctionName: string*; TriggerName: string*; Type: string*; TriggerDesc: string; Namespace: string | RequestId |
| `scf_DeleteFunction` | Region: string*; FunctionName: string*; Namespace: string | RequestId |
| `scf_GetFunctionLogs` | Region: string*; FunctionName: string*; Namespace: string; Offset: number (min=0, def 0); Limit: number (min=1, max=200, def 20); StartTime: number; EndTime: number | TotalCount, Logs |

---

## 3. SCF State Dependencies

```
scf_CreateFunction (FunctionName)       ← 基础：先创建函数
  ├── scf_CreateTrigger                  ← 依赖 FunctionName
  ├── scf_GetFunctionLogs                ← 依赖 FunctionName
  └── scf_DeleteFunction                 ← 依赖 FunctionName（需先删除触发器）
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

SCF_SPECS: dict[str, ToolStateSpec] = {
    "scf_CreateTrigger": ToolStateSpec(tool_name="scf_CreateTrigger", provides=["TriggerName"],
        dependency=StateDependency(requires=[StateAtom("scf_CreateFunction", "FunctionName")])),
    "scf_GetFunctionLogs": ToolStateSpec(tool_name="scf_GetFunctionLogs", provides=[],
        dependency=StateDependency(requires=[StateAtom("scf_CreateFunction", "FunctionName")])),
}

tracker = StateTracker()
tracker.record("scf_CreateFunction", {"FunctionName": "my-func"})
can, why = tracker.can_call("scf_CreateTrigger", SCF_SPECS)
# can=True, why=[]
```

---

## 4. SCF Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="scf_CreateTrigger",
    params={"Region": "ap-guangzhou", "FunctionName": "my-func",
             "TriggerName": "timer-trigger", "Type": "timer",
             "TriggerDesc": "0 0 * * * *", "Namespace": "default"},
    reasoning="用户请求为函数 my-func 创建定时触发器",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["FunctionName 必须已创建", "TriggerName 唯一"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. SCF Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, SCF_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("scf_ListFunction", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="scf_ListFunctions, scf_CreateFunction, ..."

# Case 2: 参数越界
reports = detector.detect("scf_ListFunctions", {"Region": "ap-guangzhou", "Limit": 9999})
# → mode="param_out_of_range", detail="Param Limit=9999 > max 1000"

# Case 3: 状态未满足（函数未创建就创建触发器）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, SCF_SPECS, tracker2)
reports = detector2.detect("scf_CreateTrigger", {"Region": "ap-guangzhou", "FunctionName": "my-func", "TriggerName": "t1", "Type": "timer"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateTrigger

1. validate_call("scf_CreateTrigger", params)  ← 参数 schema 校验
2. tracker.can_call("scf_CreateTrigger", SCF_SPECS)  ← 状态依赖检查
3. Execute tccli scf CreateTrigger ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
