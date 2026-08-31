# Tool-Call Grounding — TCOP Skill Integration

> **Scope**: `qcloud-tcop-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: sdk-only` — tccli 无 `tcop` 子命令，全部通过 SDK/API 操作。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. TCOP SDK Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeResourceOptimizationList (idle/right-size recommendations)
register(ToolSchema(name="tcop_DescribeResourceOptimizationList", description="查询资源优化建议列表", params={
    "Region": ParamConstraint(type="string", required=True),
    "Type": ParamConstraint(type="string", enum_values=["idle", "rightsizing", "lifecycle"], required=False),
    "Offset": ParamConstraint(type="number", min_val=0,        default=0),
    "Limit": ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    }, returns={"TotalCount": int, "Items": list}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("tcop_DescribeResourceOptimizationList",
    {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `tcop_DescribeCostOptimizationSummary` | Region: string*; StartMonth: string*; EndMonth: string* | TotalSaving, Items |
| `tcop_DescribeArchitectureReviewResult` | Region: string*; TaskId: string* | Score, Pillars, Findings |
| `tcop_DescribeReservedInstanceCoverage` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, CoverageSet |

---

## 3. TCOP State Dependencies

TCOP 主要是分析类读操作，状态依赖较弱：

```
tcop_DescribeResourceOptimizationList        ← 无前置依赖
  └── tcop_DescribeCostOptimizationSummary   ← 无前置依赖（但建议依赖资源数据）
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TCOP_SPECS: dict[str, ToolStateSpec] = {
    "tcop_DescribeResourceOptimizationList": ToolStateSpec(tool_name="tcop_DescribeResourceOptimizationList", provides=[],
        dependency=StateDependency(requires=[])),
}

tracker = StateTracker()
can, why = tracker.can_call("tcop_DescribeResourceOptimizationList", TCOP_SPECS)
# can=True, why=[]
```

---

## 4. TCOP Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="tcop_DescribeResourceOptimizationList",
    params={"Region": "ap-guangzhou", "Type": "idle", "Offset": 0, "Limit": 20},
    reasoning="用户请求查看广州地域的闲置资源列表",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Type 可选 idle/rightsizing/lifecycle"],
    result={"error_code": 0, "TotalCount": 5, "Items": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. TCOP Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, TCOP_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("tcop_ListOptimization", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="tcop_DescribeResourceOptimizationList, tcop_DescribeCostOptimizationSummary, ..."

# Case 2: 参数越界
reports = detector.detect("tcop_DescribeResourceOptimizationList", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 参数枚举值错误
reports = detector.detect("tcop_DescribeResourceOptimizationList", {"Region": "ap-guangzhou", "Type": "foobar"})
# → mode="param_out_of_range", detail="Param Type=foobar not in enum"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: DescribeResourceOptimizationList

1. validate_call("tcop_DescribeResourceOptimizationList", params)  ← 参数 schema 校验
2. tracker.can_call("tcop_DescribeResourceOptimizationList", TCOP_SPECS)  ← 状态检查
3. Execute SDK call (tencentcloud-sdk-python)
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
