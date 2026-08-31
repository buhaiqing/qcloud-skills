# Tool-Call Grounding — CloudBase Skill Integration

> **Scope**: `qcloud-cloudbase-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli tcb` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. CloudBase tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateEnv
register(ToolSchema(name="tcb_CreateEnv", description="创建 CloudBase 环境", params={
    "Region": ParamConstraint(type="string", required=True),
    "EnvName": ParamConstraint(type="string", required=True, max_length=64),
    "Channel": ParamConstraint(type="string", enum_values=["create_app", "create_qcloud"], default="create_app"),
    "Extensions": ParamConstraint(type="array",  required=False),
    }, returns={"EnvId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("tcb_DescribeEnvInfo", {"Region": "ap-guangzhou", "EnvId": ""})
# → (False, "Param EnvId is required", REQUIRED_PARAM_MISSING)
```

| Tool | Key params | Returns |
|---|---|---|
| `tcb_DescribeEnvInfo` | Region: string*; EnvId: string* | EnvId, EnvName, Status, Resources |
| `tcb_DeleteEnv` | Region: string*; EnvId: string* | RequestId |
| `tcb_CreateApiKey` | Region: string*; EnvId: string* | ApiKey, SecretId, RequestId |
| `tcb_CreateDatabaseACL` | Region: string*; EnvId: string*; CollectionName: string*; AclTag: string | RequestId |
| `tcb_DescribeCurveData` | Region: string*; EnvId: string*; ResourceTypes: array*; StartTime: string*; EndTime: string* | CurveData |

---

## 3. CloudBase State Dependencies

```
tcb_CreateEnv (EnvId)                   ← 基础：先创建环境
  ├── tcb_DescribeEnvInfo               ← 依赖 EnvId
  ├── tcb_CreateApiKey                  ← 依赖 EnvId
  ├── tcb_CreateDatabaseACL            ← 依赖 EnvId
  └── tcb_DeleteEnv                     ← 依赖 EnvId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TCB_SPECS: dict[str, ToolStateSpec] = {
    "tcb_CreateApiKey": ToolStateSpec(tool_name="tcb_CreateApiKey", provides=["ApiKey", "SecretId"],
        dependency=StateDependency(requires=[StateAtom("tcb_CreateEnv", "EnvId")])),
    "tcb_DescribeEnvInfo": ToolStateSpec(tool_name="tcb_DescribeEnvInfo", provides=[],
        dependency=StateDependency(requires=[StateAtom("tcb_CreateEnv", "EnvId")])),
}

tracker = StateTracker()
tracker.record("tcb_CreateEnv", {"EnvId": "env-abc123"})
can, why = tracker.can_call("tcb_CreateApiKey", TCB_SPECS)
# can=True, why=[]
```

---

## 4. CloudBase Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="tcb_CreateApiKey",
    params={"Region": "ap-guangzhou", "EnvId": "env-abc123"},
    reasoning="用户请求为环境 env-abc123 创建 API 密钥",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["EnvId 必须已创建"],
    result={"error_code": 0, "SecretId": "sid-xxx", "ApiKey": "***"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CloudBase Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, TCB_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("tcb_CreateKey", {"Region": "ap-guangzhou", "EnvId": "env-xxx"})
# → mode="tool_not_found", suggestion="tcb_CreateApiKey, tcb_CreateDatabaseACL, ..."

# Case 2: 必填参数缺失
reports = detector.detect("tcb_DescribeEnvInfo", {"Region": "ap-guangzhou"})
# → mode="param_out_of_range", detail="Param EnvId is required"

# Case 3: 状态未满足（环境未创建就创建 ApiKey）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, TCB_SPECS, tracker2)
reports = detector2.detect("tcb_CreateApiKey", {"Region": "ap-guangzhou", "EnvId": "env-xxx"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateApiKey

1. validate_call("tcb_CreateApiKey", params)  ← 参数 schema 校验
2. tracker.can_call("tcb_CreateApiKey", TCB_SPECS)  ← 状态依赖检查
3. Execute tccli tcb CreateApiKey ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
