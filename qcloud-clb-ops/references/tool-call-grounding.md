# Tool-Call Grounding — CLB Skill Integration

> **Scope**: `qcloud-clb-ops` SKILL.md 的工具调用 grounding 指引。  
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

## 2. CLB tccli Commands → ToolSchema Registration

在 agent 执行 `tccli clb` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateLoadBalancer
register(ToolSchema(
    name="clb_CreateLoadBalancer",
    description="创建 CLB 实例",
    params={
        "Region":           ParamConstraint(type="string", required=True),
        "LoadBalancerType": ParamConstraint(type="enum", enum_values=["OPEN","INTERNAL"], required=True),
        "VpcId":           ParamConstraint(type="string", required=True),
        "SubnetId":        ParamConstraint(type="string", required=False),
        "LoadBalancerName":ParamConstraint(type="string", required=False, max_length=60),
        "ClientToken":     ParamConstraint(type="string", required=False),
    },
    returns={"LoadBalancerIds": list},
    error_codes=list(ErrorCode),
))

# DescribeLoadBalancers
register(ToolSchema(
    name="clb_DescribeLoadBalancers",
    description="查询 CLB 实例列表",
    params={
        "Region":         ParamConstraint(type="string", required=True),
        "LoadBalancerIds":ParamConstraint(type="array", required=False),
        "Offset":         ParamConstraint(type="number", min_val=0, default=0),
        "Limit":          ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "LoadBalancerSet": list},
    error_codes=list(ErrorCode),
))

# CreateListener
register(ToolSchema(
    name="clb_CreateListener",
    description="创建 CLB 监听器",
    params={
        "Region":           ParamConstraint(type="string",   required=True),
        "LoadBalancerId":   ParamConstraint(type="string",   required=True),
        "Protocol":         ParamConstraint(type="enum",     enum_values=["TCP","UDP","HTTP","HTTPS"], required=True),
        "ListenerPort":     ParamConstraint(type="number",   min_val=1, max_val=65535, required=True),
        "ListenerName":     ParamConstraint(type="string",   required=False, max_length=60),
        "HealthCheckSwitch":ParamConstraint(type="boolean",  default=True),
    },
    returns={"ListenerIds": list},
    error_codes=list(ErrorCode),
))

# RegisterTargets
register(ToolSchema(
    name="clb_RegisterTargets",
    description="绑定后端服务器到监听器",
    params={
        "Region":         ParamConstraint(type="string", required=True),
        "LoadBalancerId": ParamConstraint(type="string", required=True),
        "ListenerId":    ParamConstraint(type="string", required=True),
        "Targets":        ParamConstraint(type="array",  required=True),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# DeleteLoadBalancer
register(ToolSchema(
    name="clb_DeleteLoadBalancer",
    description="删除 CLB 实例",
    params={
        "Region":         ParamConstraint(type="string", required=True),
        "LoadBalancerId": ParamConstraint(type="string", required=True),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("clb_CreateListener",
    {"Region": "ap-guangzhou", "LoadBalancerId": "lb-xxx",
     "Protocol": "TCP", "ListenerPort": 80})
# → (True, "", SUCCESS)
```

---

## 3. CLB State Dependencies

CLB 有显式的资源创建顺序依赖：

```
clb_CreateLoadBalancer (LoadBalancerId)    ← 基础：先创建 LB
  ├── clb_DescribeLoadBalancers (polling)   ← 依赖 LoadBalancerId 查状态
  ├── clb_CreateListener                    ← 依赖 LoadBalancerId + LB 状态=2(running)
  │     └── clb_RegisterTargets             ← 依赖 ListenerId + 后端 CVM 已 RUNNING
  └── clb_DeleteLoadBalancer               ← 依赖 LoadBalancerId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CLB_SPECS: dict[str, ToolStateSpec] = {
    "clb_CreateListener": ToolStateSpec(
        tool_name="clb_CreateListener",
        provides=["ListenerId"],
        dependency=StateDependency(requires=[
            StateAtom("clb_CreateLoadBalancer", "LoadBalancerIds"),
        ]),
    ),
    "clb_RegisterTargets": ToolStateSpec(
        tool_name="clb_RegisterTargets",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("clb_CreateLoadBalancer", "LoadBalancerIds"),
            StateAtom("clb_CreateListener", "ListenerIds"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("clb_CreateLoadBalancer", {"LoadBalancerIds": ["lb-12345"]})
can, why = tracker.can_call("clb_CreateListener", CLB_SPECS)
# can=True, why=[]
```

---

## 4. CLB Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="clb_CreateLoadBalancer",
    params={"Region": "ap-guangzhou", "LoadBalancerType": "OPEN",
            "VpcId": "vpc-abc", "SubnetId": "subnet-xyz"},
    reasoning="用户请求在广州创建一台公网型 CLB",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["VpcId 必须是已存在的 VPC", "SubnetId 必须是 VPC 内的子网"],
    result={"error_code": 0, "data": {"LoadBalancerIds": ["lb-67890"]}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CLB Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CLB_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("clb_DesribeLoadBalancers", {"Region": "ap-guangzhou"})
# → mode="tool_not_found"

# Case 2: 参数越界（ListenerPort 超限）
reports = detector.detect("clb_CreateListener",
    {"Region": "ap-guangzhou", "LoadBalancerId": "lb-xxx",
     "Protocol": "TCP", "ListenerPort": 70000})
# → mode="param_out_of_range", detail="Param ListenerPort=70000 > max 65535"

# Case 3: 状态未满足（未创建 LB 就注册后端）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CLB_SPECS, tracker2)
reports = detector2.detect("clb_RegisterTargets",
    {"Region": "ap-guangzhou", "LoadBalancerId": "lb-xxx",
     "ListenerId": "lbl-xxx", "Targets": [{"InstanceId": "ins-yyy", "Port": 8080}]})
# → mode="state_not_satisfied", detail="Requires clb_CreateLoadBalancer.LoadBalancerIds"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateListener

1. validate_call("clb_CreateListener", params)   ← 参数 schema 校验
2. tracker.can_call("clb_CreateListener", CLB_SPECS)  ← 状态依赖检查
3. Execute tccli clb CreateListener ...
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
