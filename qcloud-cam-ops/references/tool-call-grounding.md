# Tool-Call Grounding — CAM Skill Integration

> **Scope**: `qcloud-cam-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli cam` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. CAM tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreatePolicy
register(ToolSchema(name="cam_CreatePolicy", description="创建 CAM 策略", params={
    "Region": ParamConstraint(type="string", required=True),
    "PolicyName": ParamConstraint(type="string", required=True, max_length=128),
    "PolicyDocument": ParamConstraint(type="string", required=True),
    "Description": ParamConstraint(type="string", required=False, max_length=300),
    }, returns={"PolicyId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("cam_ListPolicies", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 200", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `cam_ListPolicies` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=200, def 20); Keyword: string | TotalCount, Policies |
| `cam_AddUser` | Region: string*; Name: string*; Remark: string; ConsoleLogin: boolean; Password: string; NeedResetPassword: boolean | Uin, Name, RequestId |
| `cam_CreateRole` | Region: string*; RoleName: string*; PolicyDocument: string*; Description: string; ConsoleLogin: boolean | RoleId, RequestId |
| `cam_AttachRolePolicy` | Region: string*; PolicyId: string*; RoleId: string* | RequestId |

---

## 3. CAM State Dependencies

CAM 状态依赖链相对扁平（策略/用户/角色可独立创建）：

```
cam_AddUser (Uin)                        ← 基础：先创建用户
  └── cam_AttachUserPolicy (可选)        ← 依赖 Uin

cam_CreateRole (RoleId)                  ← 基础：先创建角色
  └── cam_AttachRolePolicy              ← 依赖 RoleId + PolicyId

cam_CreatePolicy (PolicyId)              ← 基础：先创建策略
  └── cam_AttachRolePolicy              ← 依赖 PolicyId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CAM_SPECS: dict[str, ToolStateSpec] = {
    "cam_AttachRolePolicy": ToolStateSpec(tool_name="cam_AttachRolePolicy", provides=[],
        dependency=StateDependency(requires=[StateAtom("cam_CreateRole", "RoleId"), StateAtom("cam_CreatePolicy", "PolicyId")])),
}

tracker = StateTracker()
tracker.record("cam_CreatePolicy", {"PolicyId": "p-abc123"})
tracker.record("cam_CreateRole", {"RoleId": "r-xyz"})
can, why = tracker.can_call("cam_AttachRolePolicy", CAM_SPECS)
# can=True, why=[]
```

---

## 4. CAM Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cam_AttachRolePolicy",
    params={"Region": "ap-guangzhou", "PolicyId": "p-abc123", "RoleId": "r-xyz"},
    reasoning="用户请求将策略 p-abc123 绑定到角色 r-xyz",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["PolicyId 必须已创建", "RoleId 必须已创建"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CAM Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CAM_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cam_ListPoliies", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="cam_ListPolicies, cam_AttachRolePolicy, ..."

# Case 2: 参数越界
reports = detector.detect("cam_ListPolicies", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 200"

# Case 3: 状态未满足（策略未创建就绑定）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, CAM_SPECS, tracker2)
reports = detector2.detect("cam_AttachRolePolicy", {"Region": "ap-guangzhou", "PolicyId": "p-xxx", "RoleId": "r-xxx"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: AttachRolePolicy

1. validate_call("cam_AttachRolePolicy", params)  ← 参数 schema 校验
2. tracker.can_call("cam_AttachRolePolicy", CAM_SPECS)  ← 状态依赖检查
3. Execute tccli cam AttachRolePolicy ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
