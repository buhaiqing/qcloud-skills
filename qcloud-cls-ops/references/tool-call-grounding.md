# Tool-Call Grounding — CLS Skill Integration

> **Scope**: `qcloud-cls-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli cls` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. CLS tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateLogset
register(ToolSchema(name="cls_CreateLogset", description="创建日志集", params={
    "Region": ParamConstraint(type="string", required=True),
    "LogsetName": ParamConstraint(type="string", required=True, max_length=64),
    "Period": ParamConstraint(type="number", min_val=1, max_val=365, default=30),
    "LogsetType": ParamConstraint(type="string", enum_values=["FULLTEXT", "json"], default="FULLTEXT"),
    }, returns={"LogsetId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("cls_SearchLog", {"Region": "ap-guangzhou", "TopicId": "", "Query": "*", "StartTime": 0, "EndTime": 0})
# → (False, "Param TopicId is required", REQUIRED_PARAM_MISSING)
```

| Tool | Key params | Returns |
|---|---|---|
| `cls_CreateTopic` | Region: string*; LogsetId: string*; TopicName: string*; PartitionCount: number (min=1, max=10, def 1); StorageType: string | TopicId, RequestId |
| `cls_CreateIndex` | Region: string*; TopicId: string*; Rule: object*; Status: string | RequestId |
| `cls_SearchLog` | Region: string*; TopicId: string*; Query: string*; StartTime: number*; EndTime: number*; Limit: number (min=1, max=1000, def 100) | TotalCount, Results |
| `cls_CreateMachineGroup` | Region: string*; GroupName: string*; GroupType: string; Values: array* | GroupId, RequestId |

---

## 3. CLS State Dependencies

```
cls_CreateLogset (LogsetId)             ← 基础：先创建日志集
  └── cls_CreateTopic (TopicId)         ← 依赖 LogsetId
        └── cls_CreateIndex             ← 依赖 TopicId
              └── cls_SearchLog         ← 依赖 TopicId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CLS_SPECS: dict[str, ToolStateSpec] = {
    "cls_CreateTopic": ToolStateSpec(tool_name="cls_CreateTopic", provides=["TopicId"],
        dependency=StateDependency(requires=[StateAtom("cls_CreateLogset", "LogsetId")])),
    "cls_CreateIndex": ToolStateSpec(tool_name="cls_CreateIndex", provides=[],
        dependency=StateDependency(requires=[StateAtom("cls_CreateLogset", "LogsetId"), StateAtom("cls_CreateTopic", "TopicId")])),
    "cls_SearchLog": ToolStateSpec(tool_name="cls_SearchLog", provides=[],
        dependency=StateDependency(requires=[StateAtom("cls_CreateTopic", "TopicId")])),
}

tracker = StateTracker()
tracker.record("cls_CreateLogset", {"LogsetId": "ls-abc"})
tracker.record("cls_CreateTopic", {"TopicId": "topic-xyz", "LogsetId": "ls-abc"})
can, why = tracker.can_call("cls_SearchLog", CLS_SPECS)
# can=True, why=[]
```

---

## 4. CLS Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cls_SearchLog",
    params={"Region": "ap-guangzhou", "TopicId": "topic-xyz", "Query": "level:ERROR", "StartTime": 1725000000, "EndTime": 1725003600},
    reasoning="用户请求搜索 topic-xyz 中 level=ERROR 的日志",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["TopicId 必须已创建", "StartTime < EndTime", "Query 长度 <= 4096"],
    result={"error_code": 0, "TotalCount": 15, "Results": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CLS Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CLS_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cls_QueryLog", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="cls_SearchLog, cls_CreateLogset, ..."

# Case 2: 参数越界
reports = detector.detect("cls_SearchLog", {"Region": "ap-guangzhou", "TopicId": "topic-xyz", "Query": "*",
     "StartTime": 1725003600, "EndTime": 1725000000})
# → mode="param_out_of_range", detail="Param StartTime must be < EndTime"

# Case 3: 状态未满足（Topic 未创建就搜索）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, CLS_SPECS, tracker2)
reports = detector2.detect("cls_SearchLog", {"Region": "ap-guangzhou", "TopicId": "topic-xxx", "Query": "*",
     "StartTime": 1725000000, "EndTime": 1725003600})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: SearchLog

1. validate_call("cls_SearchLog", params)  ← 参数 schema 校验
2. tracker.can_call("cls_SearchLog", CLS_SPECS)  ← 状态依赖检查
3. Execute tccli cls SearchLog ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
