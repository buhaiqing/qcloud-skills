# Tool-Call Grounding — Service Mesh (TCM) Skill Integration

> **Scope**: `qcloud-service-mesh-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli tcm` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. TCM tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateMesh
register(ToolSchema(name="tcm_CreateMesh", description="创建服务网格", params={
    "Region": ParamConstraint(type="string", required=True),
    "MeshName": ParamConstraint(type="string", required=True, max_length=60),
    "MeshVersion": ParamConstraint(type="string", default="1.14.5"),
    "ClusterIds": ParamConstraint(type="array",  required=True),
    "Type": ParamConstraint(type="string", enum_values=["HOSTED", "DIRECT"], default="HOSTED"),
    "Ingress": ParamConstraint(type="object", required=False),
    }, returns={"MeshId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("tcm_DescribeMeshList", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `tcm_DescribeMesh` | Region: string*; MeshId: string* | MeshId, MeshName, Status, Clusters |
| `tcm_DescribeMeshList` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, Meshes |
| `tcm_ModifyMesh` | Region: string*; MeshId: string*; Config: object* | RequestId |
| `tcm_LinkClusterList` | Region: string*; MeshId: string*; ClusterIds: array* | RequestId |

---

## 3. TCM State Dependencies

```
tcm_CreateMesh (MeshId)                  ← 基础：先创建网格
  ├── tcm_DescribeMesh                   ← 依赖 MeshId
  ├── tcm_ModifyMesh                     ← 依赖 MeshId
  └── tcm_LinkClusterList                ← 依赖 MeshId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TCM_SPECS: dict[str, ToolStateSpec] = {
    "tcm_DescribeMesh": ToolStateSpec(tool_name="tcm_DescribeMesh", provides=[],
        dependency=StateDependency(requires=[StateAtom("tcm_CreateMesh", "MeshId")])),
    "tcm_ModifyMesh": ToolStateSpec(tool_name="tcm_ModifyMesh", provides=[],
        dependency=StateDependency(requires=[StateAtom("tcm_CreateMesh", "MeshId")])),
    "tcm_LinkClusterList": ToolStateSpec(tool_name="tcm_LinkClusterList", provides=[],
        dependency=StateDependency(requires=[StateAtom("tcm_CreateMesh", "MeshId")])),
}

tracker = StateTracker()
tracker.record("tcm_CreateMesh", {"MeshId": "mesh-abc"})
can, why = tracker.can_call("tcm_ModifyMesh", TCM_SPECS)
# can=True, why=[]
```

---

## 4. TCM Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="tcm_ModifyMesh",
    params={"Region": "ap-guangzhou", "MeshId": "mesh-abc", "Config": {"Tracing": {"SamplingRate": 0.1}}},
    reasoning="用户请求修改网格 mesh-abc 的链路追踪采样率为 10%",
    confidence=0.88,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["MeshId 必须已创建"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. TCM Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, TCM_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("tcm_ListMesh", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="tcm_DescribeMeshList, tcm_CreateMesh, ..."

# Case 2: 参数越界
reports = detector.detect("tcm_DescribeMeshList", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（网格未创建就修改配置）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, TCM_SPECS, tracker2)
reports = detector2.detect("tcm_ModifyMesh", {"Region": "ap-guangzhou", "MeshId": "mesh-xxx", "Config": {}})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: ModifyMesh

1. validate_call("tcm_ModifyMesh", params)  ← 参数 schema 校验
2. tracker.can_call("tcm_ModifyMesh", TCM_SPECS)  ← 状态依赖检查
3. Execute tccli tcm ModifyMesh ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
