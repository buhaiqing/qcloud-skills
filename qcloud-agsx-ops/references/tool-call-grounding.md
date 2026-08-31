# Tool-Call Grounding — AGSX Skill Integration

> **Scope**: `qcloud-agsx-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: sdk-only` — tccli 无 `ags` 子命令，全部通过 `tencentcloud-sdk-python` (module `tencentcloud.ags.v20201023`) 操作。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. AGSX SDK Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateSandboxTool
register(ToolSchema(name="agsx_CreateSandboxTool", description="创建 AGSX 沙箱工具", params={
    "Region": ParamConstraint(type="string", required=True),
    "Name": ParamConstraint(type="string", required=True, max_length=64),
    "Description": ParamConstraint(type="string", required=False, max_length=256),
    "Runtime": ParamConstraint(type="enum", enum_values=["e2b", "browser"], default="e2b"),
    }, returns={"SandboxToolId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("agsx_DescribeSandboxToolList", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `agsx_DescribeSandboxToolList` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, Items |
| `agsx_StartSandboxInstance` | Region: string*; SandboxInstanceId: string*; SandboxToolId: string* | InstanceId, RequestId |
| `agsx_DescribeSandboxInstanceList` | Region: string*; Status: string; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, Items |
| `agsx_StopSandboxInstance` | Region: string*; SandboxInstanceId: string* | RequestId |

---

## 3. AGSX State Dependencies

```
agsx_CreateSandboxTool (SandboxToolId)       ← 基础：先创建工具
  ├── agsx_DescribeSandboxToolList (polling) ← 依赖工具存在
  ├── agsx_StartSandboxInstance              ← 依赖 SandboxToolId
  └── agsx_StopSandboxInstance               ← 依赖已启动的实例
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

AGSX_SPECS: dict[str, ToolStateSpec] = {
    "agsx_StartSandboxInstance": ToolStateSpec(tool_name="agsx_StartSandboxInstance", provides=["SandboxInstanceId"],
        dependency=StateDependency(requires=[StateAtom("agsx_CreateSandboxTool", "SandboxToolId")])),
    "agsx_StopSandboxInstance": ToolStateSpec(tool_name="agsx_StopSandboxInstance", provides=[],
        dependency=StateDependency(requires=[StateAtom("agsx_StartSandboxInstance", "SandboxInstanceId")])),
}

tracker = StateTracker()
tracker.record("agsx_CreateSandboxTool", {"SandboxToolId": "st-abc"})
can, why = tracker.can_call("agsx_StartSandboxInstance", AGSX_SPECS)
# can=True, why=[]
```

---

## 4. AGSX Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="agsx_StartSandboxInstance",
    params={"Region": "ap-guangzhou", "SandboxToolId": "st-abc", "SandboxInstanceId": "si-xxx"},
    reasoning="用户请求启动沙箱工具 st-abc 的实例",
    confidence=0.88,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是可用区前缀", "SandboxToolId 必须已创建"],
    result={"error_code": 0, "data": {"InstanceId": "si-xxx"}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. AGSX Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, AGSX_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("agsx_StartSandbox", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="agsx_StartSandboxInstance, ..."

# Case 2: 参数越界
reports = detector.detect("agsx_DescribeSandboxToolList", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建工具就启动实例）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, AGSX_SPECS, tracker2)
reports = detector2.detect("agsx_StartSandboxInstance", {"Region": "ap-guangzhou", "SandboxToolId": "st-xxx", "SandboxInstanceId": "si-xxx"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: StartSandboxInstance

1. validate_call("agsx_StartSandboxInstance", params)  ← 参数 schema 校验
2. tracker.can_call("agsx_StartSandboxInstance", AGSX_SPECS)  ← 状态依赖检查
3. Execute SDK call (tencentcloud.ags...)
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
