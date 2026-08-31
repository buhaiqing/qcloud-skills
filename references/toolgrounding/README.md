# Tool Grounding Library

> 为 qcloud-*-ops skill 提供工具调用严格化的基础能力。

## Modules

| File | Responsibility |
|------|---------------|
| `tool_schema.py` | ToolSchema + ParamConstraint：参数类型/范围/枚举校验，ErrorCode 枚举，validate_call 全局入口 |
| `state_dependency.py` | StateAtom + StateDependency + StateTracker：工具间状态依赖显式化，can_call 前置检查 |
| `grounding_trace.py` | ToolCallTrace + ParamSource：每次调用的结构化 trace，含参数来源、置信度、约束、状态快照 |
| `hallucination_detector.py` | GroundingDetector：三模式检测（tool_not_found / param_out_of_range / state_not_satisfied），返回修复建议 |
| `_demo.py` | 全链路演示（4 模块串接） |

## Relationship with qcloud-*-ops

本库为 qcloud-*-ops skill 提供**工具调用 grounding 基础能力**，不直接调用 tccli。消费方式：

1. **Schema 注册**：在 skill 执行 tccli 前，注册该 skill 的命令 schema（见 `INTEGRATION_EXAMPLE.py`）
2. **状态依赖**：声明工具链的前置状态（例：cdb_CreateAccounts 依赖 cdb_CreateDBInstance.InstanceId）
3. **Trace 记录**：每次 tccli 调用后生成 ToolCallTrace，写入审计日志
4. **幻觉拦截**：Agent 执行前用 GroundingDetector 检测参数/状态/工具名幻觉

## Consumption

### Schema registration + validation

```python
from tool_schema import register, validate_call, ToolSchema, ParamConstraint

register(ToolSchema(name="cdb_DescribeDBInstances", ...))
ok, msg, code = validate_call("cdb_DescribeDBInstances", {"Region": "ap-guangzhou"})
```

### State tracking

```python
from state_dependency import StateTracker, ToolStateSpec, StateAtom, StateDependency

specs = {"cdb_CreateAccounts": ToolStateSpec(...)}
tracker = StateTracker()
tracker.record("cdb_CreateDBInstance", {"InstanceId": "cdb-123"})
can, why = tracker.can_call("cdb_CreateAccounts", specs)
```

### Grounding trace

```python
from grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(tool_name="cdb_CreateDBInstance", ...,
                          source=ParamSource.USER_INSTRUCTION, confidence=0.9, ...)
```

### Hallucination detection

```python
from hallucination_detector import GroundingDetector

detector = GroundingDetector(REGISTRY, specs, tracker)
reports = detector.detect("cdb_DescrieDBInstance", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: ...")
```

## Referenced Skills

| Skill | File |
|-------|------|
| `qcloud-cdb-ops` | `qcloud-cdb-ops/references/tool-call-grounding.md` |

## Self-Check

```bash
# Demo — existing library demo
python3 references/toolgrounding/_demo.py

# Integration example — CDB skill integration
python3 references/toolgrounding/INTEGRATION_EXAMPLE.py

# Lint
ruff check references/toolgrounding/INTEGRATION_EXAMPLE.py
```
