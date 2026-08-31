# Tool-Call Grounding — API Gateway Skill Integration

> **Scope**: `qcloud-apigw-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli apigateway` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. API Gateway tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateService
register(ToolSchema(name="apigw_CreateService", description="创建 API Gateway 服务", params={
    "Region": ParamConstraint(type="string", required=True),
    "ServiceName": ParamConstraint(type="string", required=True, max_length=60),
    "Protocol": ParamConstraint(type="enum", enum_values=["HTTP", "HTTPS", "WEBSOCKET"], default="HTTP"),
    "ServiceDesc": ParamConstraint(type="string", required=False, max_length=400),
    "ExclusiveSetName": ParamConstraint(type="string", required=False),
    "NetTypes": ParamConstraint(type="array",  required=False),
    }, returns={"ServiceId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("apigw_DescribeServices", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `apigw_CreateApi` | Region: string*; ServiceId: string*; ApiName: string*; ApiMethod: string; ApiPath: string*; AuthType: string; RequestConfig: object | ApiId, RequestId |
| `apigw_ReleaseService` | Region: string*; ServiceId: string*; Environment: string*; VersionName: string | RequestId |
| `apigw_DescribeServices` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20); SearchId: string | TotalCount, ServiceSet |
| `apigw_DescribeApis` | Region: string*; ServiceId: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, ApiSet |
| `apigw_DeleteService` | Region: string*; ServiceId: string* | RequestId |

---

## 3. API Gateway State Dependencies

```
apigw_CreateService (ServiceId)           ← 基础：先创建服务
  └── apigw_CreateApi (ApiId)            ← 依赖 ServiceId
        └── apigw_ReleaseService         ← 依赖 ServiceId + ApiId 已创建
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

APIGW_SPECS: dict[str, ToolStateSpec] = {
    "apigw_CreateApi": ToolStateSpec(tool_name="apigw_CreateApi", provides=["ApiId"],
        dependency=StateDependency(requires=[StateAtom("apigw_CreateService", "ServiceId")])),
    "apigw_ReleaseService": ToolStateSpec(tool_name="apigw_ReleaseService", provides=[],
        dependency=StateDependency(requires=[StateAtom("apigw_CreateService", "ServiceId")])),
}

tracker = StateTracker()
tracker.record("apigw_CreateService", {"ServiceId": "service-abc"})
can, why = tracker.can_call("apigw_CreateApi", APIGW_SPECS)
# can=True, why=[]
```

---

## 4. API Gateway Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="apigw_ReleaseService",
    params={"Region": "ap-guangzhou", "ServiceId": "service-abc", "Environment": "release"},
    reasoning="用户请求发布服务到 release 环境",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Environment 必须是 test/prepub/release 之一", "ServiceId 必须已创建"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. API Gateway Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, APIGW_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("apigw_Create", {"Region": "ap-guangzhou", "ServiceId": "svc-xxx"})
# → mode="tool_not_found", suggestion="apigw_CreateService, apigw_CreateApi, ..."

# Case 2: 参数越界
reports = detector.detect("apigw_DescribeServices", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建服务就发布）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, APIGW_SPECS, tracker2)
reports = detector2.detect("apigw_ReleaseService", {"Region": "ap-guangzhou", "ServiceId": "svc-xxx", "Environment": "release"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateApi

1. validate_call("apigw_CreateApi", params)  ← 参数 schema 校验
2. tracker.can_call("apigw_CreateApi", APIGW_SPECS)  ← 状态依赖检查
3. Execute tccli apigateway CreateApi ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
