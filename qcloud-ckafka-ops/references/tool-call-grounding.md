# Tool-Call Grounding — CKafka Skill Integration

> **Scope**: `qcloud-ckafka-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli ckafka` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. CKafka tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateInstance
register(ToolSchema(name="ckafka_CreateInstance", description="创建 CKafka 实例", params={
    "Region": ParamConstraint(type="string", required=True),
    "InstanceName": ParamConstraint(type="string", required=True, max_length=64),
    "ZoneId": ParamConstraint(type="string", required=True),
    "InstanceType": ParamConstraint(type="string", required=True),
    "VpcId": ParamConstraint(type="string", required=False),
    "SubnetId": ParamConstraint(type="string", required=False),
    "BandwidthWidth": ParamConstraint(type="number", min_val=1, default=10),
    "DiskSize": ParamConstraint(type="number", min_val=100, default=500),
    "MsgRetentionTime": ParamConstraint(type="number", min_val=1, max_val=30, default=7),
    }, returns={"InstanceId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("ckafka_DescribeInstances", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `ckafka_DescribeInstances` | Region: string*; InstanceIds: array; Offset: number (min=0, def 0); Limit: number (min=1, max=100, def 20) | TotalCount, InstanceList |
| `ckafka_CreateTopic` | Region: string*; InstanceId: string*; TopicName: string*; Partition: number (min=1, def 3); ReplicaNum: number (min=1, max=3, def 3); RetentionMs: number (min=60000, def 3600000) | TopicId, RequestId |
| `ckafka_DescribeConsumerGroup` | Region: string*; InstanceId: string*; TopicName: string | TotalCount, ConsumerGroups |
| `ckafka_DescribeACL` | Region: string*; InstanceId: string* | ACLList |
| `ckafka_DeleteInstance` | Region: string*; InstanceId: string* | RequestId |

---

## 3. CKafka State Dependencies

```
ckafka_CreateInstance (InstanceId)        ← 基础：先创建实例
  ├── ckafka_CreateTopic                 ← 依赖 InstanceId
  ├── ckafka_DescribeConsumerGroup       ← 依赖 InstanceId
  └── ckafka_DescribeACL                ← 依赖 InstanceId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CKAFKA_SPECS: dict[str, ToolStateSpec] = {
    "ckafka_CreateTopic": ToolStateSpec(tool_name="ckafka_CreateTopic", provides=["TopicName"],
        dependency=StateDependency(requires=[StateAtom("ckafka_CreateInstance", "InstanceId")])),
    "ckafka_DescribeConsumerGroup": ToolStateSpec(tool_name="ckafka_DescribeConsumerGroup", provides=[],
        dependency=StateDependency(requires=[StateAtom("ckafka_CreateInstance", "InstanceId")])),
}

tracker = StateTracker()
tracker.record("ckafka_CreateInstance", {"InstanceId": "ckafka-abc"})
can, why = tracker.can_call("ckafka_CreateTopic", CKAFKA_SPECS)
# can=True, why=[]
```

---

## 4. CKafka Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="ckafka_CreateTopic",
    params={"Region": "ap-guangzhou", "InstanceId": "ckafka-abc",
            "TopicName": "my-topic", "Partition": 6, "ReplicaNum": 3},
    reasoning="用户请求在实例 ckafka-abc 创建主题 my-topic",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["InstanceId 必须已创建", "Partition >= 1", "ReplicaNum 1-3"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. CKafka Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, CKAFKA_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("ckafka_ListInstance", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="ckafka_CreateInstance, ckafka_DescribeInstances, ..."

# Case 2: 参数越界
reports = detector.detect("ckafka_DescribeInstances", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（未创建实例就创建 Topic）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, CKAFKA_SPECS, tracker2)
reports = detector2.detect("ckafka_CreateTopic", {"Region": "ap-guangzhou", "InstanceId": "ckafka-xxx", "TopicName": "t1", "Partition": 3})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: CreateTopic

1. validate_call("ckafka_CreateTopic", params)  ← 参数 schema 校验
2. tracker.can_call("ckafka_CreateTopic", CKAFKA_SPECS)  ← 状态依赖检查
3. Execute tccli ckafka CreateTopic ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
