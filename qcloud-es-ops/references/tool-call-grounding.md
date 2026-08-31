# Tool-Call Grounding — ES Skill Integration

> **Scope**: `qcloud-es-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli es` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. ES tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateInstance
register(ToolSchema(name="es_CreateInstance", description="创建 ES 集群实例", params={
    "Region": ParamConstraint(type="string", required=True),
    "Zone": ParamConstraint(type="string", required=True),
    "InstanceName": ParamConstraint(type="string", required=True, max_length=50),
    "NodeType": ParamConstraint(type="string", required=True),
    "NodeNum": ParamConstraint(type="number", min_val=2, max_val=50, default=2),
    "DiskSize": ParamConstraint(type="number", min_val=100, default=100),
    "EsVersion": ParamConstraint(type="string", default="7.10.1"),
    "VpcId": ParamConstraint(type="string", required=False),
    "SubnetId": ParamConstraint(type="string", required=False),
    "AdminPassword": ParamConstraint(type="string", required=True, max_length=16),
    }, returns={"InstanceId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("es_DescribeInstances", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `es_DescribeInstances` | Region: string*; InstanceIds: array; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, Instances |
| `es_UpdateInstance` | Region: string*; InstanceId: string*; NodeNum: number (min=2, max=50); DiskSize: number (min=100) | RequestId |
| `es_RestartInstance` | Region: string*; InstanceId: string*; ForceRestart: boolean | RequestId |
| `es_CreateIndex` | Region: string*; InstanceId: string*; IndexName: string*; Body: object | RequestId |
| `es_DeleteInstance` | Region: string*; InstanceId: string* | RequestId |

---

## 3. ES State Dependencies

```
es_CreateInstance (InstanceId)           ← 基础：先创建实例
  ├── es_DescribeInstances (polling)     ← 依赖 InstanceId 查询状态
  ├── es_UpdateInstance                  ← 依赖 InstanceId
  ├── es_RestartInstance                 ← 依赖 InstanceId
  └── es_CreateIndex                     ← 依赖 InstanceId（集群可用时）
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

ES_SPECS: dict[str, ToolStateSpec] = {
    "es_UpdateInstance": ToolStateSpec(tool_name="es_UpdateInstance", provides=[],
        dependency=StateDependency(requires=[StateAtom("es_CreateInstance", "InstanceId")])),
    "es_RestartInstance": ToolStateSpec(tool_name="es_RestartInstance", provides=[],
        dependency=StateDependency(requires=[StateAtom("es_CreateInstance", "InstanceId")])),
    "es_CreateIndex": ToolStateSpec(tool_name="es_CreateIndex", provides=[],
        dependency=StateDependency(requires=[StateAtom("es_CreateInstance", "InstanceId")])),
}

tracker = StateTracker()
tracker.record("es_CreateInstance", {"InstanceId": "es-abc123"})
can, why = tracker.can_call("es_UpdateInstance", ES_SPECS)
# can=True, why=[]
```

---

## 4. ES Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="es_UpdateInstance",
    params={"Region": "ap-guangzhou", "InstanceId": "es-abc123", "NodeNum": 4, "DiskSize": 200},
    reasoning="用户请求扩容 es-abc123 到 4 节点 200GB",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["InstanceId 必须已创建", "NodeNum >= 2", "DiskSize >= 100"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. ES Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, ES_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("es_ListInstance", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="es_CreateInstance, es_DescribeInstances, ..."

# Case 2: 参数越界
reports = detector.detect("es_DescribeInstances", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（实例未创建就更新配置）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, ES_SPECS, tracker2)
reports = detector2.detect("es_UpdateInstance", {"Region": "ap-guangzhou", "InstanceId": "es-xxx", "NodeNum": 4})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: UpdateInstance

1. validate_call("es_UpdateInstance", params)  ← 参数 schema 校验
2. tracker.can_call("es_UpdateInstance", ES_SPECS)  ← 状态依赖检查
3. Execute tccli es UpdateInstance ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
