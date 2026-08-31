# Tool-Call Grounding — VPC Skill Integration

> **Scope**: `qcloud-vpc-ops` SKILL.md 的工具调用 grounding 指引。  
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

## 2. VPC tccli Commands → ToolSchema Registration

在 agent 执行 `tccli vpc` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateVpc
register(ToolSchema(
    name="vpc_CreateVpc",
    description="创建 VPC",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "VpcName":    ParamConstraint(type="string", required=True, max_length=60),
        "CidrBlock":  ParamConstraint(type="string", required=True,
                  pattern=r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"),
        "ClientToken":ParamConstraint(type="string", required=False),
    },
    returns={"Vpc": dict},
    error_codes=list(ErrorCode),
))

# DescribeVpcs
register(ToolSchema(
    name="vpc_DescribeVpcs",
    description="查询 VPC 列表",
    params={
        "Region":  ParamConstraint(type="string", required=True),
        "VpcIds":  ParamConstraint(type="array",  required=False),
        "Offset":  ParamConstraint(type="number", min_val=0, default=0),
        "Limit":   ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "VpcSet": list},
    error_codes=list(ErrorCode),
))

# DeleteVpc
register(ToolSchema(
    name="vpc_DeleteVpc",
    description="删除 VPC",
    params={
        "Region": ParamConstraint(type="string", required=True),
        "VpcId":  ParamConstraint(type="string", required=True),
    },
    returns={"RequestId": str},
    error_codes=list(ErrorCode),
))

# CreateSubnet
register(ToolSchema(
    name="vpc_CreateSubnet",
    description="在 VPC 内创建子网",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "VpcId":      ParamConstraint(type="string", required=True),
        "SubnetName": ParamConstraint(type="string", required=True, max_length=60),
        "CidrBlock":  ParamConstraint(type="string", required=True,
                  pattern=r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"),
        "Zone":       ParamConstraint(type="string", required=True),
    },
    returns={"Subnet": dict},
    error_codes=list(ErrorCode),
))

# DescribeSubnets
register(ToolSchema(
    name="vpc_DescribeSubnets",
    description="查询子网列表",
    params={
        "Region":   ParamConstraint(type="string", required=True),
        "VpcIds":   ParamConstraint(type="array",  required=False),
        "SubnetIds":ParamConstraint(type="array",   required=False),
        "Offset":   ParamConstraint(type="number", min_val=0, default=0),
        "Limit":    ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "SubnetSet": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("vpc_CreateSubnet",
    {"Region": "ap-guangzhou", "VpcId": "vpc-xxx",
     "SubnetName": "my-subnet", "CidrBlock": "10.0.1.0/24", "Zone": "ap-guangzhou-3"})
# → (True, "", SUCCESS)
```

---

## 3. VPC State Dependencies

VPC 有严格的资源层次依赖：

```
vpc_CreateVpc (VpcId)                   ← 基础：先创建 VPC
  ├── vpc_DescribeVpcs (polling)        ← 依赖 VpcId 确认状态 AVAILABLE
  ├── vpc_CreateSubnet                  ← 依赖 VpcId + VPC 状态 AVAILABLE
  │     └── vpc_DescribeSubnets
  ├── vpc_CreateRouteTable              ← 依赖 VpcId
  └── vpc_DeleteVpc                     ← 依赖子网/路由表已清空
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

VPC_SPECS: dict[str, ToolStateSpec] = {
    "vpc_CreateSubnet": ToolStateSpec(
        tool_name="vpc_CreateSubnet",
        provides=["SubnetId"],
        dependency=StateDependency(requires=[
            StateAtom("vpc_CreateVpc", "VpcId"),
        ]),
    ),
    "vpc_DeleteVpc": ToolStateSpec(
        tool_name="vpc_DeleteVpc",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("vpc_CreateVpc", "VpcId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("vpc_CreateVpc", {"VpcId": "vpc-abc", "CidrBlock": "10.0.0.0/16"})
can, why = tracker.can_call("vpc_CreateSubnet", VPC_SPECS)
# can=True, why=[]
```

---

## 4. VPC Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="vpc_CreateSubnet",
    params={"Region": "ap-guangzhou", "VpcId": "vpc-abc",
             "SubnetName": "my-subnet", "CidrBlock": "10.0.1.0/24", "Zone": "ap-guangzhou-3"},
    reasoning="用户请求在 VPC 内创建子网",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["CidrBlock 必须是 VPC CidrBlock 的子集",
                 "Zone 必须是 Region 下的可用区"],
    result={"error_code": 0, "data": {"Subnet": {"SubnetId": "subnet-xyz"}}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. VPC Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, VPC_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("vpc_DesribeVpcs", {"Region": "ap-guangzhou"})
# → mode="tool_not_found"

# Case 2: 参数越界（CIDR 格式错误）
reports = detector.detect("vpc_CreateVpc",
    {"Region": "ap-guangzhou", "VpcName": "my-vpc", "CidrBlock": "10.0.0.256/24"})
# → mode="param_out_of_range", detail="Param CidrBlock does not match pattern ..."

# Case 3: 状态未满足（未创建 VPC 就创建子网）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, VPC_SPECS, tracker2)
reports = detector2.detect("vpc_CreateSubnet",
    {"Region": "ap-guangzhou", "VpcId": "vpc-xxx",
     "SubnetName": "s", "CidrBlock": "10.0.1.0/24", "Zone": "ap-guangzhou-3"})
# → mode="state_not_satisfied", detail="Requires vpc_CreateVpc.VpcId"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateSubnet

1. validate_call("vpc_CreateSubnet", params)   ← 参数 schema 校验
2. tracker.can_call("vpc_CreateSubnet", VPC_SPECS)  ← 状态依赖检查
3. Execute tccli vpc CreateSubnet ...
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
