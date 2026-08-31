# Tool-Call Grounding — CDN Skill Integration

> **Scope**: `qcloud-cdn-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. CDN tccli Commands → ToolSchema Registration

在 agent 执行 `tccli cdn` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeDomains — 查询加速域名列表
register(ToolSchema(
    name="cdn_DescribeDomains",
    description="查询 CDN 加速域名列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "Domain":      ParamConstraint(type="string", required=False),
        "Status":      ParamConstraint(type="array",  required=False),
        "Offset":      ParamConstraint(type="number", min_val=0,        default=0),
        "Limit":       ParamConstraint(type="number", min_val=1, max_val=100, default=100),
        "ProjectId":   ParamConstraint(type="number", default=0),
    },
    returns={"TotalCount": int, "Domains": list},
    error_codes=list(ErrorCode),
))

# DescribeDomainsConfig — 查询域名配置
register(ToolSchema(
    name="cdn_DescribeDomainsConfig",
    description="查询 CDN 域名配置（查询类，非修改）",
    params={
        "Region":   ParamConstraint(type="string", required=True),
        "Domain":   ParamConstraint(type="string", required=True),
        "Key":      ParamConstraint(type="array",  required=False),
        "Offset":   ParamConstraint(type="number", min_val=0, default=0),
        "Limit":    ParamConstraint(type="number", min_val=1, max_val=100, default=100),
    },
    returns={"TotalCount": int, "DomainList": list},
    error_codes=list(ErrorCode),
))

# DescribeCdnData — CDN 流量/带宽查询
register(ToolSchema(
    name="cdn_DescribeCdnData",
    description="查询 CDN 流量、带宽、请求数明细",
    params={
        "Region":       ParamConstraint(type="string", required=True),
        "Domain":       ParamConstraint(type="string", required=False),
        "StartTime":   ParamConstraint(type="string", required=True),
        "EndTime":     ParamConstraint(type="string", required=True),
        "Metric":      ParamConstraint(type="enum", enum_values=["flux", "bandwidth", "requests"], default="flux"),
        "Interval":    ParamConstraint(type="enum", enum_values=["5min", "hour", "day"], default="day"),
    },
    returns={"DataPoints": list, "TotalCount": int},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("cdn_DescribeDomains", {"Region": "ap-guangzhou", "Limit": 500})
# → (False, "Param Limit=500 > max 100", PARAM_OUT_OF_RANGE)
```

---

## 3. CDN State Dependencies

CDN 域名操作有隐式依赖（域名必须先存在）：

```
cdn_create_domain (Domain)           ← 前提：域名已接入 CDN
  └── cdn_describe_domain_config      ← 依赖 cdn_create_domain.Domain
        └── cdn_modify_config         ← 依赖 cdn_create_domain.Domain + 配置版本
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CDN_SPECS: dict[str, ToolStateSpec] = {
    "cdn_DescribeDomainsConfig": ToolStateSpec(
        tool_name="cdn_DescribeDomainsConfig",
        provides=["Domain", "DomainConfigVersion"],
        dependency=StateDependency(requires=[
            StateAtom("cdn_DescribeDomains", "Domains[].Domain"),
        ]),
    ),
    "cdn_DescribeCdnData": ToolStateSpec(
        tool_name="cdn_DescribeCdnData",
        provides=["CdnDataPoints"],
        dependency=StateDependency(requires=[
            StateAtom("cdn_DescribeDomains", "Domains[].Domain"),
        ]),
    ),
}

# Agent 执行前检查
tracker = StateTracker()
tracker.record("cdn_DescribeDomains", {"Domains": [{"Domain": "example.com"}]})
can, why = tracker.can_call("cdn_DescribeDomainsConfig", CDN_SPECS)
# can=True, why=[]
```

---

## 4. CDN Grounding Trace

每次 tccli 调用后生成 trace：

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

# tccli cdn DescribeDomains 执行后
trace = ToolCallTrace.new(
    tool_name="cdn_DescribeDomains",
    params={"Region": "ap-guangzhou", "Limit": 20},
    reasoning="用户查询广州地域 CDN 域名列表",
    confidence=0.95,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区", "Limit ≤ 100"],
    result={"error_code": 0, "error_name": "SUCCESS", "data": {"Domains": []}},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CDN Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, CDN_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cdn_DescibeDomains", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: cdn_DescribeDomains, ...")

# Case 2: 参数越界（无效 Domain 格式）
reports = detector.detect("cdn_DescribeDomainsConfig",
    {"Region": "ap-guangzhou", "Domain": "not-a-valid-domain!!!"})
# → HallucinationReport(mode="param_out_of_range", detail="Domain 格式无效")

# Case 3: 状态未满足（未查域名就查配置）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CDN_SPECS, tracker2)
reports = detector2.detect("cdn_DescribeCdnData", {"Region": "ap-guangzhou", "Domain": "unknown.com",
    "StartTime": "2026-01-01 00:00:00", "EndTime": "2026-01-02 00:00:00"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires cdn_DescribeDomains")
```

---

## 6. CDN Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（minimal change，不改主体）：

```
## Execute: Describe Domain Config

1. Validate schema  ← validate_call("cdn_DescribeDomainsConfig", params)
2. Check state      ← tracker.can_call("cdn_DescribeDomainsConfig", CDN_SPECS)
3. Execute tccli    ← tccli cdn DescribeDomainsConfig ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure       ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
