# Tool-Call Grounding — COS Skill Integration

> **Scope**: `qcloud-cos-ops` SKILL.md 的工具调用 grounding 指引。
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

## 2. COS 执行路径 — SDK-Only（无 tccli cos）

**重要**：腾讯云无 `tccli cos` 服务，COS 操作全部走 Python SDK (`tencentcloud.cos`) 或 `coscmd` CLI。

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# list_buckets — 列出所有 Bucket（ListBuckets 无 Region 参数）
register(ToolSchema(
    name="cos_ListAllMyBuckets",
    description="列出当前账户下所有 COS Bucket（SDK: list_buckets）",
    params={
        "Region": ParamConstraint(type="string", required=False),
    },
    returns={"Buckets": list, "Owner": dict},
    error_codes=list(ErrorCode),
))

# head_bucket — 查询 Bucket 元信息
register(ToolSchema(
    name="cos_HeadBucket",
    description="查询 Bucket 存在性和访问权限（SDK: head_bucket）",
    params={
        "Bucket": ParamConstraint(type="string", required=True),
        "Region": ParamConstraint(type="string", required=True),
    },
    returns={"BucketExists": bool, "BucketRegion": str},
    error_codes=list(ErrorCode),
))

# list_objects — 列出 Bucket 内对象
register(ToolSchema(
    name="cos_ListObjects",
    description="列出 Bucket 内对象（SDK: list_objects）",
    params={
        "Bucket":    ParamConstraint(type="string", required=True),
        "Region":    ParamConstraint(type="string", required=True),
        "Prefix":    ParamConstraint(type="string", required=False, default=""),
        "MaxKeys":   ParamConstraint(type="number", min_val=1, max_val=1000, default=100),
        "Delimiter": ParamConstraint(type="string", required=False),
    },
    returns={"Contents": list, "Name": str, "Prefix": str},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("cos_ListObjects", {"Bucket": "mybucket-123456789", "Region": "ap-guangzhou", "MaxKeys": 5000})
# → (False, "Param MaxKeys=5000 > max 1000", PARAM_OUT_OF_RANGE)
```

---

## 3. COS State Dependencies

COS Bucket 操作有隐式依赖：

```
cos_ListAllMyBuckets (Buckets[])        ← 前提：先确认 Bucket 存在
  └── cos_HeadBucket (Bucket, Region)    ← 依赖 cos_ListAllMyBuckets 返回的 Bucket 名称
        └── cos_ListObjects              ← 依赖 cos_HeadBucket 确认 Bucket 可访问
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

COS_SPECS: dict[str, ToolStateSpec] = {
    "cos_HeadBucket": ToolStateSpec(
        tool_name="cos_HeadBucket",
        provides=["BucketExists", "BucketRegion"],
        dependency=StateDependency(requires=[
            StateAtom("cos_ListAllMyBuckets", "Buckets[].Name"),
        ]),
    ),
    "cos_ListObjects": ToolStateSpec(
        tool_name="cos_ListObjects",
        provides=["ObjectList"],
        dependency=StateDependency(requires=[
            StateAtom("cos_ListAllMyBuckets", "Buckets[].Name"),
        ]),
    ),
}

tracker = StateTracker()
tracker.record("cos_ListAllMyBuckets", {"Buckets": [{"Name": "mybucket-123456789"}]})
can, why = tracker.can_call("cos_ListObjects", COS_SPECS)
# can=True, why=[]
```

---

## 4. COS Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="cos_ListObjects",
    params={"Bucket": "mybucket-123456789", "Region": "ap-guangzhou", "MaxKeys": 100},
    reasoning="用户列出 COS Bucket 中的对象列表",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Bucket 名称格式: name-APPID", "Region 必须是支持的地域"],
    result={"error_code": 0, "Contents": []},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. COS Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, COS_SPECS, tracker)

# Case 1: 工具名拼错（agent 误以为有 tccli cos）
reports = detector.detect("cos_ListBuckets", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", detail="COS 无 tccli 服务，请使用 Python SDK")

# Case 2: Bucket 名称格式错误
reports = detector.detect("cos_ListObjects",
    {"Bucket": "mybucket", "Region": "ap-guangzhou", "MaxKeys": 100})
# → HallucinationReport(mode="param_out_of_range", detail="Bucket 必须包含 APPID")

# Case 3: 状态未满足
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, COS_SPECS, tracker2)
reports = detector2.detect("cos_HeadBucket", {"Bucket": "unknown-123", "Region": "ap-guangzhou"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires cos_ListAllMyBuckets")
```

---

## 6. COS Integration Pattern

在 SKILL.md 的「Execute」步骤中嵌入 grounding（SDK 调用场景）：

```
## Execute: List Objects

1. Validate schema   ← validate_call("cos_ListObjects", params)
2. Check state       ← tracker.can_call("cos_ListObjects", COS_SPECS)
3. Execute SDK       ← cos_client.list_objects(Bucket=..., MaxKeys=...)
4. Emit trace        ← ToolCallTrace.new(...) → audit log
5. On failure        ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
