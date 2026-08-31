# Tool-Call Grounding — DC Skill Integration

> **Scope**: `qcloud-dc-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli dc` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. DC tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateDirectConnect
register(ToolSchema(name="dc_CreateDirectConnect", description="创建专线", params={
    "Region": ParamConstraint(type="string", required=True),
    "DirectConnectName": ParamConstraint(type="string", required=True, max_length=64),
    "AccessPoint": ParamConstraint(type="string", required=True),
    "Bandwidth": ParamConstraint(type="number", min_val=1, max_val=10000, required=True),
    "CircuitCode": ParamConstraint(type="string", required=False),
    "LocalGatewayIp": ParamConstraint(type="string", required=False),
    "Vlan": ParamConstraint(type="number", min_val=0, max_val=4000, required=False),
    }, returns={"DirectConnectId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("dc_DescribeDirectConnects", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `dc_DescribeDirectConnects` | Region: string*; DirectConnectIds: array; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, DirectConnectSet |
| `dc_CreateDirectConnectTunnel` | Region: string*; DirectConnectId: string*; DirectConnectTunnelName: string*; Vlan: number* (min=0, max=4000); TencentAddress: string*; CustomerAddress: string*; BgpPeer: object | DirectConnectTunnelId, RequestId |
| `dc_DescribeDirectConnectTunnels` | Region: string*; DirectConnectId: string; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, DirectConnectTunnelSet |
| `dc_CreateDirectConnectGateway` | Region: string*; DirectConnectGatewayName: string*; Mode: string | DirectConnectGatewayId, RequestId |

---

## 3. DC State Dependencies

```
dc_CreateDirectConnect (DirectConnectId) ← 基础：先创建专线
  └── dc_CreateDirectConnectTunnel        ← 依赖 DirectConnectId
        └── dc_CreateDirectConnectGateway ← 可选：关联专线网关
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

DC_SPECS: dict[str, ToolStateSpec] = {
    "dc_CreateDirectConnectTunnel": ToolStateSpec(tool_name="dc_CreateDirectConnectTunnel", provides=["DirectConnectTunnelId"],
        dependency=StateDependency(requires=[StateAtom("dc_CreateDirectConnect", "DirectConnectId")])),
}

tracker = StateTracker()
tracker.record("dc_CreateDirectConnect", {"DirectConnectId": "dc-abc"})
can, why = tracker.can_call("dc_CreateDirectConnectTunnel", DC_SPECS)
# can=True, why=[]
```

---

## 4. DC Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="dc_CreateDirectConnectTunnel",
    params={"Region": "ap-guangzhou", "DirectConnectId": "dc-abc",
            "DirectConnectTunnelName": "tunnel-1", "Vlan": 100,
            "TencentAddress": "10.0.0.1", "CustomerAddress": "10.0.0.2"},
    reasoning="用户请求为专线 dc-abc 创建通道",
    confidence=0.88,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["DirectConnectId 必须已创建", "Vlan 范围 0-4000"],
    result={"error_code": 0, "DirectConnectTunnelId": "dcx-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. DC Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, DC_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("dc_ListDirectConnect", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="dc_CreateDirectConnect, dc_DescribeDirectConnects, ..."

# Case 2: 参数越界
reports = detector.detect("dc_DescribeDirectConnects", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（专线未创建就创建通道）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, DC_SPECS, tracker2)
reports = detector2.detect("dc_CreateDirectConnectTunnel", {"Region": "ap-guangzhou", "DirectConnectId": "dc-xxx",
     "DirectConnectTunnelName": "t1", "Vlan": 100,
     "TencentAddress": "10.0.0.1", "CustomerAddress": "10.0.0.2"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateDirectConnectTunnel

1. validate_call("dc_CreateDirectConnectTunnel", params)  ← 参数 schema 校验
2. tracker.can_call("dc_CreateDirectConnectTunnel", DC_SPECS)  ← 状态依赖检查
3. Execute tccli dc CreateDirectConnectTunnel ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
