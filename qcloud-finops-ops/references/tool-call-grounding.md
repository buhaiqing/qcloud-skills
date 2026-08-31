# Tool-Call Grounding — FinOps Skill Integration

> **Scope**: `qcloud-finops-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli billing` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. FinOps tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeBillSummaryByPayMode
register(ToolSchema(name="billing_DescribeBillSummaryByPayMode", description="按计费模式汇总账单", params={
    "Region": ParamConstraint(type="string", required=True),
    "BeginTime": ParamConstraint(type="string", required=True),
    "EndTime": ParamConstraint(type="string", required=True),
    "PeriodType": ParamConstraint(type="string", enum_values=["byPayMode", "byProduct", "byRegion", "byInstance"], default="byPayMode"),
    }, returns={"SummaryTotal": dict, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("billing_DescribeBillDetail", {"Region": "ap-guangzhou", "BeginTime": "", "EndTime": ""})
# → (False, "Param BeginTime is required", REQUIRED_PARAM_MISSING)
```

| Tool | Key params | Returns |
|---|---|---|
| `billing_DescribeBillDetail` | Region: string*; BeginTime: string*; EndTime: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20); ProductCode: string | TotalCount, ItemSet |
| `billing_DescribeAccountBalance` | Region: string* | Balance, Uin, RequestId |
| `billing_DescribeCostSummaryByProduct` | Region: string*; BeginTime: string*; EndTime: string*; Limit: number (min=1, max=1000, def 10) | TotalCost, ItemSet |
| `billing_DescribeVoucherInfo` | Region: string*; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20); Status: string | TotalCount, VoucherSet |

---

## 3. FinOps State Dependencies

FinOps 主要为读操作（账单/余额查询），状态依赖较弱：

```
billing_DescribeAccountBalance              ← 无前置依赖
  └── billing_DescribeBillSummaryByPayMode ← 无前置依赖（但依赖账户有效）

billing_DescribeVoucherInfo                ← 无前置依赖
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

FINOPS_SPECS: dict[str, ToolStateSpec] = {
    "billing_DescribeBillSummaryByPayMode": ToolStateSpec(tool_name="billing_DescribeBillSummaryByPayMode", provides=[],
        dependency=StateDependency(requires=[])),
}

tracker = StateTracker()
can, why = tracker.can_call("billing_DescribeBillSummaryByPayMode", FINOPS_SPECS)
# can=True, why=[]
```

---

## 4. FinOps Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="billing_DescribeBillSummaryByPayMode",
    params={"Region": "ap-guangzhou", "BeginTime": "2024-08-01", "EndTime": "2024-08-31"},
    reasoning="用户请求查看 2024 年 8 月按计费模式汇总的账单",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["BeginTime <= EndTime", "时间范围不超过 12 个月"],
    result={"error_code": 0, "SummaryTotal": {"PayMode": "POSTPAID", "TotalCost": 12345.67}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. FinOps Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, FINOPS_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("billing_GetBillSummary", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="billing_DescribeBillSummaryByPayMode, billing_DescribeBillDetail, ..."

# Case 2: 必填参数缺失
reports = detector.detect("billing_DescribeBillDetail", {"Region": "ap-guangzhou"})
# → mode="param_out_of_range", detail="Param BeginTime is required"

# Case 3: 参数越界（时间范围过大）
reports = detector.detect("billing_DescribeBillSummaryByPayMode", {"Region": "ap-guangzhou", "BeginTime": "2020-01-01", "EndTime": "2024-12-31"})
# → mode="param_out_of_range", detail="时间范围超过 12 个月限制"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: DescribeBillSummaryByPayMode

1. validate_call("billing_DescribeBillSummaryByPayMode", params)  ← 参数 schema 校验
2. tracker.can_call("billing_DescribeBillSummaryByPayMode", FINOPS_SPECS)  ← 状态检查
3. Execute tccli billing DescribeBillSummaryByPayMode ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
