# Tool-Call Grounding — TKE Skill Integration

> **Scope**: `qcloud-tke-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. TKE tccli Commands → ToolSchema Registration

在 agent 执行 `tccli tke` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeClusters — 查询集群列表
register(ToolSchema(
    name="tke_DescribeClusters",
    description="查询 TKE 集群列表及基础信息",
    params={
        "Region":    ParamConstraint(type="string", required=True),
        "ClusterIds": ParamConstraint(type="array", required=False),
        "Offset":   ParamConstraint(type="number", min_val=0, default=0),
        "Limit":    ParamConstraint(type="number", min_val=1, max_val=50, default=20),
        "Filters":  ParamConstraint(type="array",  required=False),
    },
    returns={"TotalCount": int, "Clusters": list},
    error_codes=list(ErrorCode),
))

# DescribeClusterInstances — 查询集群内节点
register(ToolSchema(
    name="tke_DescribeClusterInstances",
    description="查询 TKE 集群内节点（Node）列表",
    params={
        "Region":     ParamConstraint(type="string", required=True),
        "ClusterId":  ParamConstraint(type="string", required=True),
        "Offset":    ParamConstraint(type="number", min_val=0, default=0),
        "Limit":     ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "InstanceIds": ParamConstraint(type="array", required=False),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))

# DescribeClusterNodePools — 查询节点池
register(ToolSchema(
    name="tke_DescribeClusterNodePools",
    description="查询 TKE 集群节点池列表",
    params={
        "Region":    ParamConstraint(type="string", required=True),
        "ClusterId": ParamConstraint(type="string", required=True),
        "NodePoolIds": ParamConstraint(type="array", required=False),
    },
    returns={"NodePoolSet": list},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("tke_DescribeClusters", {"Region": "ap-guangzhou", "Limit": 200})
# → (False, "Param Limit=200 > max 50", PARAM_OUT_OF_RANGE)
```

---

## 3. TKE State Dependencies

TKE 集群操作有依赖链（集群 → 节点/节点池）：

```
tke_create_cluster (ClusterId)                    ← 前提：创建集群
  └── tke_describe_cluster_instances (ClusterId)  ← 依赖 tke_create_cluster.ClusterId
        └── tke_describe_cluster_nodepools        ← 依赖 tke_create_cluster.ClusterId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TKE_SPECS: dict[str, ToolStateSpec] = {
    "tke_DescribeClusterInstances": ToolStateSpec(
        tool_name="tke_DescribeClusterInstances",
        provides=["InstanceSet"],
        dependency=StateDependency(requires=[
            StateAtom("tke_DescribeClusters", "Clusters[].ClusterId"),
        ]),
    ),
    "tke_DescribeClusterNodePools": ToolStateSpec(
        tool_name="tke_DescribeClusterNodePools",
        provides=["NodePoolSet"],
        dependency=StateDependency(requires=[
            StateAtom("tke_DescribeClusters", "Clusters[].ClusterId"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("tke_DescribeClusters", {"Clusters": [{"ClusterId": "cls-abc123"}]})
can, why = tracker.can_call("tke_DescribeClusterInstances", TKE_SPECS)
# can=True, why=[]
```

---

## 4. TKE Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="tke_DescribeClusterInstances",
    params={"Region": "ap-guangzhou", "ClusterId": "cls-abc123", "Limit": 20},
    reasoning="用户查询 TKE 集群内节点列表",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区", "Limit ≤ 100"],
    result={"error_code": 0, "InstanceSet": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. TKE Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, TKE_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("tke_DescibeClusters", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: tke_DescribeClusters, ...")

# Case 2: 越界 Limit
reports = detector.detect("tke_DescribeClusterInstances",
    {"Region": "ap-guangzhou", "ClusterId": "cls-abc", "Limit": 200})
# → HallucinationReport(mode="param_out_of_range", detail="Param Limit=200 > max 100")

# Case 3: 状态未满足（未查询集群就查节点）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, TKE_SPECS, tracker2)
reports = detector2.detect("tke_DescribeClusterInstances",
    {"Region": "ap-guangzhou", "ClusterId": "cls-unknown"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires tke_DescribeClusters")
```

---

## 6. TKE Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change）：

```
## Execute: Describe Cluster Nodes

1. Validate schema  ← validate_call("tke_DescribeClusterInstances", params)
2. Check state      ← tracker.can_call("tke_DescribeClusterInstances", TKE_SPECS)
3. Execute tccli    ← tccli tke DescribeClusterInstances ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure      ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
