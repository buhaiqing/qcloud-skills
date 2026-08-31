# Tool-Call Grounding — CBS Skill Integration

> **Scope**: `qcloud-cbs-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. CBS tccli Commands → ToolSchema Registration

在 agent 执行 `tccli cbs` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeDisks — 查询云硬盘列表
register(ToolSchema(
    name="cbs_DescribeDisks",
    description="查询云硬盘列表及状态",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "DiskIds":     ParamConstraint(type="array",  required=False),
        "DiskType":    ParamConstraint(type="enum",   enum_values=["CLOUD_BASIC", "CLOUD_SSD", "CLOUD_PREMIUM", "CLOUD_BSSD"], required=False),
        "DiskState":   ParamConstraint(type="array",  required=False),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "Offset":      ParamConstraint(type="number", min_val=0, default=0),
        "ProjectId":   ParamConstraint(type="number", default=0),
    },
    returns={"TotalCount": int, "DiskSet": list},
    error_codes=list(ErrorCode),
))

# DescribeSnapshots — 查询快照列表
register(ToolSchema(
    name="cbs_DescribeSnapshots",
    description="查询云硬盘快照列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "SnapshotIds": ParamConstraint(type="array",  required=False),
        "DiskId":      ParamConstraint(type="string", required=False),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "Offset":      ParamConstraint(type="number", min_val=0, default=0),
    },
    returns={"TotalCount": int, "SnapshotSet": list},
    error_codes=list(ErrorCode),
))

# DescribeDiskConfigQuota — 查询可用区配额
register(ToolSchema(
    name="cbs_DescribeDiskConfigQuota",
    description="查询可用区云硬盘配置配额",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "Zone":       ParamConstraint(type="string", required=True),
        "DiskType":   ParamConstraint(type="string", required=False),
        "DiskChargeType": ParamConstraint(type="enum", enum_values=["PREPAID", "POSTPAID"], required=False),
    },
    returns={"DiskConfigSet": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("cbs_DescribeDisks", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. CBS State Dependencies

CBS 云硬盘操作有状态依赖链：

```
cbs_create_disk (DiskId)               ← 前提：先创建云硬盘
  └── cbs_attach_disk (DiskId, InstanceId) ← 依赖 cbs_create_disk.DiskId
        └── cbs_describe_disks              ← 依赖 cbs_create_disk.DiskId
              └── cbs_create_snapshot        ← 依赖 cbs_create_disk.DiskId（磁盘必须已挂载或可用）
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CBS_SPECS: dict[str, ToolStateSpec] = {
    "cbs_DescribeSnapshots": ToolStateSpec(
        tool_name="cbs_DescribeSnapshots",
        provides=["SnapshotSet"],
        dependency=StateDependency(requires=[
            StateAtom("cbs_DescribeDisks", "DiskSet[].DiskId"),
        ]),
    ),
    "cbs_AttachDisks": ToolStateSpec(
        tool_name="cbs_AttachDisks",
        provides=["DiskId", "InstanceId"],
        dependency=StateDependency(requires=[
            StateAtom("cbs_CreateDisks", "DiskId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("cbs_DescribeDisks", {"DiskSet": [{"DiskId": "disk-abc123", "DiskState": "UNATTACHED"}]})
can, why = tracker.can_call("cbs_DescribeSnapshots", CBS_SPECS)
# can=True, why=[]
```

---

## 4. CBS Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cbs_DescribeDisks",
    params={"Region": "ap-guangzhou", "Limit": 20, "DiskState": ["UNATTACHED"]},
    reasoning="用户查询广州地域未挂载的云硬盘",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区", "Limit ≤ 100"],
    result={"error_code": 0, "DiskSet": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CBS Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, CBS_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cbs_DescrieDisks", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: cbs_DescribeDisks, ...")

# Case 2: 无效 DiskType
reports = detector.detect("cbs_DescribeDisks",
    {"Region": "ap-guangzhou", "DiskType": "CLOUD_FAST"})
# → HallucinationReport(mode="param_out_of_range", detail="DiskType=CLOUD_FAST 不是有效枚举值")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CBS_SPECS, tracker2)
reports = detector2.detect("cbs_AttachDisks", {"DiskId": "disk-xyz", "InstanceId": "ins-abc"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires cbs_CreateDisks.DiskId")
```

---

## 6. CBS Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe Disks

1. Validate schema  ← validate_call("cbs_DescribeDisks", params)
2. Check state      ← tracker.can_call("cbs_DescribeDisks", CBS_SPECS)
3. Execute tccli    ← tccli cbs DescribeDisks ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure       ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
