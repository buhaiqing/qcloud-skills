# Tool-Call Grounding — CI/CD Skill Integration

> **Scope**: `qcloud-cicd-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: sdk-only` — tccli 无 `codepipeline`/`coding` 子命令，全部通过 SDK/API 操作。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. CI/CD SDK Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribePipeline (list pipelines)
register(ToolSchema(name="cicd_DescribePipeline", description="查询 CI/CD 流水线列表", params={
    "Region": ParamConstraint(type="string", required=True),
    "Offset": ParamConstraint(type="number", min_val=0,        default=0),
    "Limit": ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    "ProjectId": ParamConstraint(type="string", required=False),
    }, returns={"TotalCount": int, "PipelineList": list}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("cicd_DescribePipeline", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `cicd_CreatePipeline` | Region: string*; ProjectId: string*; PipelineName: string*; Source: object*; Trigger: object | PipelineId, RequestId |
| `cicd_RunPipeline` | Region: string*; PipelineId: string*; Branch: string; CommitId: string | RequestId |
| `cicd_DescribePipelineRunDetail` | Region: string*; PipelineId: string*; RunId: string* | Status, Stages, Logs |
| `cicd_StopPipeline` | Region: string*; PipelineId: string*; RunId: string* | RequestId |

---

## 3. CI/CD State Dependencies

```
cicd_CreatePipeline (PipelineId)         ← 基础：先创建流水线
  ├── cicd_RunPipeline                   ← 依赖 PipelineId
  ├── cicd_DescribePipelineRunDetail    ← 依赖 PipelineId + RunId
  └── cicd_StopPipeline                 ← 依赖 PipelineId + RunId（运行中）
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CICD_SPECS: dict[str, ToolStateSpec] = {
    "cicd_RunPipeline": ToolStateSpec(tool_name="cicd_RunPipeline", provides=["RunId"],
        dependency=StateDependency(requires=[StateAtom("cicd_CreatePipeline", "PipelineId")])),
    "cicd_StopPipeline": ToolStateSpec(tool_name="cicd_StopPipeline", provides=[],
        dependency=StateDependency(requires=[StateAtom("cicd_RunPipeline", "RunId")])),
}

tracker = StateTracker()
tracker.record("cicd_CreatePipeline", {"PipelineId": "p-abc123"})
can, why = tracker.can_call("cicd_RunPipeline", CICD_SPECS)
# can=True, why=[]
```

---

## 4. CI/CD Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cicd_RunPipeline",
    params={"Region": "ap-guangzhou", "PipelineId": "p-abc123", "Branch": "main"},
    reasoning="用户请求触发流水线 p-abc123 在 main 分支执行",
    confidence=0.88,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["PipelineId 必须已创建"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CI/CD Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CICD_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cicd_ListPipeline", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="cicd_DescribePipeline, cicd_CreatePipeline, ..."

# Case 2: 参数越界
reports = detector.detect("cicd_DescribePipeline", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建流水线就触发）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, CICD_SPECS, tracker2)
reports = detector2.detect("cicd_RunPipeline", {"Region": "ap-guangzhou", "PipelineId": "p-xxx"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: RunPipeline

1. validate_call("cicd_RunPipeline", params)  ← 参数 schema 校验
2. tracker.can_call("cicd_RunPipeline", CICD_SPECS)  ← 状态依赖检查
3. Execute SDK call (CODING DevOps API)
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
