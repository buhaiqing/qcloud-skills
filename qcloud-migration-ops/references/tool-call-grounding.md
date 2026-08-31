# Tool-Call Grounding — Migration Skill Integration

> **Scope**: `qcloud-migration-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli msp` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. Migration tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# RegisterMigrationTask
register(ToolSchema(name="msp_RegisterMigrationTask", description="注册迁移任务", params={
    "Region": ParamConstraint(type="string", required=True),
    "TaskName": ParamConstraint(type="string", required=True, max_length=64),
    "TaskType": ParamConstraint(type="number", required=True),
    "SrcAccessKey": ParamConstraint(type="string", required=True),
    "SrcRegion": ParamConstraint(type="string", required=True),
    "DstAccessKey": ParamConstraint(type="string", required=True),
    "DstRegion": ParamConstraint(type="string", required=True),
    "DatabaseType": ParamConstraint(type="string", required=False),
    }, returns={"TaskId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("msp_ListMigrationTask", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `msp_DescribeMigrationTask` | Region: string*; TaskId: string* | Status, Progress, RequestId |
| `msp_ListMigrationTask` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20); Status: number | TotalCount, TaskSet |
| `msp_ModifyMigrationTaskStatus` | Region: string*; TaskId: string*; Status: number* | RequestId |
| `msp_DeregisterMigrationTask` | Region: string*; TaskId: string* | RequestId |

---

## 3. Migration State Dependencies

```
msp_RegisterMigrationTask (TaskId)        ← 基础：先注册任务
  ├── msp_DescribeMigrationTask          ← 依赖 TaskId
  ├── msp_ModifyMigrationTaskStatus       ← 依赖 TaskId
  └── msp_DeregisterMigrationTask          ← 依赖 TaskId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

MSP_SPECS: dict[str, ToolStateSpec] = {
    "msp_DescribeMigrationTask": ToolStateSpec(tool_name="msp_DescribeMigrationTask", provides=[],
        dependency=StateDependency(requires=[StateAtom("msp_RegisterMigrationTask", "TaskId")])),
    "msp_ModifyMigrationTaskStatus": ToolStateSpec(tool_name="msp_ModifyMigrationTaskStatus", provides=[],
        dependency=StateDependency(requires=[StateAtom("msp_RegisterMigrationTask", "TaskId")])),
}

tracker = StateTracker()
tracker.record("msp_RegisterMigrationTask", {"TaskId": "task-abc"})
can, why = tracker.can_call("msp_DescribeMigrationTask", MSP_SPECS)
# can=True, why=[]
```

---

## 4. Migration Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="msp_DescribeMigrationTask",
    params={"Region": "ap-guangzhou", "TaskId": "task-abc"},
    reasoning="用户请求查看迁移任务 task-abc 的状态",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["TaskId 必须已注册"],
    result={"error_code": 0, "Status": 2, "Progress": 45, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. Migration Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, MSP_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("msp_ListTasks", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="msp_ListMigrationTask, msp_RegisterMigrationTask, ..."

# Case 2: 参数越界
reports = detector.detect("msp_ListMigrationTask", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（任务未注册就查询状态）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, MSP_SPECS, tracker2)
reports = detector2.detect("msp_DescribeMigrationTask", {"Region": "ap-guangzhou", "TaskId": "task-xxx"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: DescribeMigrationTask

1. validate_call("msp_DescribeMigrationTask", params)  ← 参数 schema 校验
2. tracker.can_call("msp_DescribeMigrationTask", MSP_SPECS)  ← 状态依赖检查
3. Execute tccli msp DescribeMigrationTask ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
