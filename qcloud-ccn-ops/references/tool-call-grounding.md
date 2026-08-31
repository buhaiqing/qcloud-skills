# Tool-Call Grounding — CCN Skill Integration

> **Scope**: `qcloud-ccn-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. CCN tccli Commands → ToolSchema Registration

CCN 属于 `tccli vpc` 命名空间（与 VPN 同属 VPC 产品线）：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeCcns — 查询云联网实例
register(ToolSchema(
    name="vpc_DescribeCcns",
    description="查询云联网（CCN）实例列表",
    params={
        "Region":    ParamConstraint(type="string", required=True),
        "CcnId":     ParamConstraint(type="string", required=False),
        "State":     ParamConstraint(type="array",  required=False),
        "Offset":    ParamConstraint(type="number", min_val=0, default=0),
        "Limit":     ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "CcnSet": list},
    error_codes=list(ErrorCode),
))

# DescribeCcnAttachedInstances — 查询云联网已挂载实例
register(ToolSchema(
    name="vpc_DescribeCcnAttachedInstances",
    description="查询挂载到 CCN 的网络实例（VPC/BM/子网）",
    params={
        "Region":    ParamConstraint(type="string", required=True),
        "CcnId":     ParamConstraint(type="string", required=True),
        "Offset":    ParamConstraint(type="number", min_val=0, default=0),
        "Limit":     ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))

# DescribeCcnRegionBandwidthLimits — 查询跨地域带宽上限
register(ToolSchema(
    name="vpc_DescribeCcnRegionBandwidthLimits",
    description="查询云联网跨地域带宽限制",
    params={
        "Region":  ParamConstraint(type="string", required=True),
        "CcnId":   ParamConstraint(type="string", required=True),
    },
    returns={"CcnRegionBandwidthLimitSet": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("vpc_DescribeCcns", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. CCN State Dependencies

CCN 操作有依赖链（云联网 → 挂载实例 → 带宽限制）：

```
vpc_create_ccn (CcnId)                              ← 前提：创建 CCN
  └── vpc_attach_cen_instances (CcnId, InstanceId) ← 依赖 CcnId
        └── vpc_describe_ccn_attached_instances      ← 依赖 CcnId
              └── vpc_describe_ccn_region_bandwidth  ← 依赖 CcnId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CCN_SPECS: dict[str, ToolStateSpec] = {
    "vpc_DescribeCcnAttachedInstances": ToolStateSpec(
        tool_name="vpc_DescribeCcnAttachedInstances",
        provides=["InstanceSet"],
        dependency=StateDependency(requires=[
            StateAtom("vpc_DescribeCcns", "CcnSet[].CcnId"),
        ]),
    ),
    "vpc_DescribeCcnRegionBandwidthLimits": ToolStateSpec(
        tool_name="vpc_DescribeCcnRegionBandwidthLimits",
        provides=["CcnRegionBandwidthLimitSet"],
        dependency=StateDependency(requires=[
            StateAtom("vpc_DescribeCcns", "CcnSet[].CcnId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("vpc_DescribeCcns", {"CcnSet": [{"CcnId": "ccn-abc123"}]})
can, why = tracker.can_call("vpc_DescribeCcnAttachedInstances", CCN_SPECS)
# can=True, why=[]
```

---

## 4. CCN Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="vpc_DescribeCcnAttachedInstances",
    params={"Region": "ap-guangzhou", "CcnId": "ccn-abc123", "Limit": 20},
    reasoning="用户查询云联网挂载的网络实例",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区", "Limit ≤ 100"],
    result={"error_code": 0, "InstanceSet": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CCN Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, CCN_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("vpc_DescibeCcns", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: vpc_DescribeCcns, ...")

# Case 2: 无效 CcnId 格式
reports = detector.detect("vpc_DescribeCcnAttachedInstances",
    {"Region": "ap-guangzhou", "CcnId": "not-a-valid-ccn-id"})
# → HallucinationReport(mode="param_out_of_range", detail="CcnId 格式无效")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CCN_SPECS, tracker2)
reports = detector2.detect("vpc_DescribeCcnRegionBandwidthLimits",
    {"Region": "ap-guangzhou", "CcnId": "ccn-unknown"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires vpc_DescribeCcns")
```

---

## 6. CCN Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe CCN Attached Instances

1. Validate schema  ← validate_call("vpc_DescribeCcnAttachedInstances", params)
2. Check state      ← tracker.can_call("vpc_DescribeCcnAttachedInstances", CCN_SPECS)
3. Execute tccli    ← tccli vpc DescribeCcnAttachedInstances ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure       ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
