# Tool-Call Grounding — Test Skill Integration

> **Scope**: `qcloud-test-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: cli-only` — 本 skill 为 M3 acceptance stub，无实际 tccli 命令操作。Grounding 框架用于验证框架本身的可用性，不执行实际云 API 调用。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. Test Skill — Stub Schema Registration

本 skill 不调用任何云 API，仅验证 SkillRegistry 路由能力。注册占位 schema：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# Stub: 验证 SkillRegistry 路由
register(ToolSchema(
    name="test_RouteSkill",
    description="M3 acceptance stub — 验证 SkillRegistry 路由",
    params={
        "Instruction": ParamConstraint(type="string", required=True),
    },
    returns={"SkillName": str, "Confidence": float},
    error_codes=list(ErrorCode),
))
```

---

## 3. Test Skill State Dependencies

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TEST_SPECS: dict[str, ToolStateSpec] = {
    "test_RouteSkill": ToolStateSpec(
        tool_name="test_RouteSkill",
        provides=[],
        dependency=StateDependency(requires=[]),
    ),
}

tracker = StateTracker()
can, why = tracker.can_call("test_RouteSkill", TEST_SPECS)
# can=True, why=[]
```

---

## 4. Test Skill Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="test_RouteSkill",
    params={"Instruction": "test ops acceptance"},
    reasoning="M3 acceptance stub 路由验证",
    confidence=1.0,
    source=ParamSource.USER_INSTRUCTION,
    constraints=[],
    result={"SkillName": "qcloud-test-ops", "Confidence": 1.0},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. Test Skill Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, TEST_SPECS, tracker)

# Case 1: 工具名拼错（应触发 tool_not_found）
reports = detector.detect("test_FakeCommand", {"Instruction": "test"})
# → mode="tool_not_found"

# Case 2: 参数缺失
reports = detector.detect("test_RouteSkill", {})
# → mode="param_out_of_range", detail="Param Instruction is required"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: Route (Stub)

1. validate_call("test_RouteSkill", params)  ← 参数 schema 校验
2. tracker.can_call("test_RouteSkill", TEST_SPECS)  ← 状态检查
3. 验证 SkillRegistry 路由返回 qcloud-test-ops
4. 返回 delegate_to = [{"skill": "qcloud-monitor-ops", ...}]
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
