# Tool-Call Grounding — VPN Skill Integration

> **Scope**: `qcloud-vpn-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. VPN tccli Commands → ToolSchema Registration

VPN 属于 `tccli vpc` 命名空间（与 CCN 同属 VPC 产品线）：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeVpnGateways — 查询 VPN 网关
register(ToolSchema(
    name="vpc_DescribeVpnGateways",
    description="查询 VPN 网关列表及状态",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "VpnGatewayId": ParamConstraint(type="string", required=False),
        "State":      ParamConstraint(type="array",  required=False),
        "Offset":     ParamConstraint(type="number", min_val=0, default=0),
        "Limit":      ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "VpnGatewaySet": list},
    error_codes=list(ErrorCode),
))

# DescribeVpnConnections — 查询 VPN 通道
register(ToolSchema(
    name="vpc_DescribeVpnConnections",
    description="查询 VPN 通道列表及状态",
    params={
        "Region":       ParamConstraint(type="string", required=True),
        "VpnConnectionId": ParamConstraint(type="string", required=False),
        "State":        ParamConstraint(type="array",  required=False),
        "Offset":       ParamConstraint(type="number", min_val=0, default=0),
        "Limit":        ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "VpnConnectionSet": list},
    error_codes=list(ErrorCode),
))

# DescribeCustomerGateways — 查询用户网关
register(ToolSchema(
    name="vpc_DescribeCustomerGateways",
    description="查询用户网关列表",
    params={
        "Region":           ParamConstraint(type="string", required=True),
        "CustomerGatewayIds": ParamConstraint(type="array", required=False),
        "Offset":           ParamConstraint(type="number", min_val=0, default=0),
        "Limit":            ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "CustomerGatewaySet": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("vpc_DescribeVpnGateways", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. VPN State Dependencies

VPN 操作有依赖链（网关 → 通道）：

```
vpc_create_vpn_gateway (VpnGatewayId)          ← 前提：创建 VPN 网关
  └── vpc_create_vpn_connection (VpnConnectionId) ← 依赖 VPN 网关 ID
        └── vpc_describe_vpn_connections          ← 依赖 VPN 网关 ID
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

VPN_SPECS: dict[str, ToolStateSpec] = {
    "vpc_DescribeVpnConnections": ToolStateSpec(
        tool_name="vpc_DescribeVpnConnections",
        provides=["VpnConnectionSet"],
        dependency=StateDependency(requires=[
            StateAtom("vpc_DescribeVpnGateways", "VpnGatewaySet[].VpnGatewayId"),
        ]),
    ),
    "vpc_CreateVpnConnection": ToolStateSpec(
        tool_name="vpc_CreateVpnConnection",
        provides=["VpnConnectionId"],
        dependency=StateDependency(requires=[
            StateAtom("vpc_DescribeVpnGateways", "VpnGatewaySet[].VpnGatewayId"),
            StateAtom("vpc_DescribeCustomerGateways", "CustomerGatewaySet[].CustomerGatewayId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("vpc_DescribeVpnGateways", {"VpnGatewaySet": [{"VpnGatewayId": "vpngw-abc"}]})
can, why = tracker.can_call("vpc_DescribeVpnConnections", VPN_SPECS)
# can=True, why=[]
```

---

## 4. VPN Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="vpc_DescribeVpnConnections",
    params={"Region": "ap-guangzhou", "Limit": 20},
    reasoning="用户查询广州地域 VPN 通道状态",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区", "Limit ≤ 100"],
    result={"error_code": 0, "VpnConnectionSet": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. VPN Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, VPN_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("vpc_DescibeVpnGateways", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: vpc_DescribeVpnGateways, ...")

# Case 2: 无效 VPN 状态
reports = detector.detect("vpc_DescribeVpnGateways",
    {"Region": "ap-guangzhou", "State": ["active", "unknown"]})
# → HallucinationReport(mode="param_out_of_range", detail="State 值无效")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, VPN_SPECS, tracker2)
reports = detector2.detect("vpc_CreateVpnConnection",
    {"Region": "ap-guangzhou", "VpnGatewayId": "vpngw-xyz"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires vpc_DescribeCustomerGateways")
```

---

## 6. VPN Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe VPN Connections

1. Validate schema  ← validate_call("vpc_DescribeVpnConnections", params)
2. Check state     ← tracker.can_call("vpc_DescribeVpnConnections", VPN_SPECS)
3. Execute tccli   ← tccli vpc DescribeVpnConnections ...
4. Emit trace      ← ToolCallTrace.new(...) → audit log
5. On failure      ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
