# Tool-Call Grounding — TDMQ Skill Integration

> **Scope**: `qcloud-tdmq-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli tdmq` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. TDMQ tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# CreateRocketMQCluster
register(ToolSchema(name="tdmq_CreateRocketMQCluster", description="创建 RocketMQ 集群", params={
    "Region": ParamConstraint(type="string", required=True),
    "ClusterName": ParamConstraint(type="string", required=True, max_length=64),
    "RegionId": ParamConstraint(type="string", required=True),
    "Bandwidth": ParamConstraint(type="number", min_val=3, max_val=9999, default=3),
    "NodeCount": ParamConstraint(type="number", min_val=2, max_val=20, default=2),
    }, returns={"ClusterId": str, "RequestId": str}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("tdmq_CreateRocketMQTopic", {"Region": "ap-guangzhou", "ClusterId": "", "NamespaceId": "", "TopicName": ""})
# → (False, "Param ClusterId is required", REQUIRED_PARAM_MISSING)
```

| Tool | Key params | Returns |
|---|---|---|
| `tdmq_CreateRocketMQNamespace` | Region: string*; ClusterId: string*; NamespaceName: string*; Ttl: number (min=60000, def 86400000); RetentionTime: number (min=60000, def 86400000) | NamespaceId, RequestId |
| `tdmq_CreateRocketMQTopic` | Region: string*; ClusterId: string*; NamespaceId: string*; TopicName: string*; Partitions: number (min=1, def 8); QueueNum: number (min=1, def 8) | TopicId, RequestId |
| `tdmq_CreateRocketMQGroup` | Region: string*; ClusterId: string*; NamespaceId: string*; GroupName: string*; ReadEnable: boolean | GroupId, RequestId |
| `tdmq_SendRocketMQMessage` | Region: string*; ClusterId: string*; NamespaceId: string*; TopicName: string*; MessageBody: string*; Tags: string | MsgId, RequestId |

---

## 3. TDMQ State Dependencies

```
tdmq_CreateRocketMQCluster (ClusterId)      ← 基础：先创建集群
  └── tdmq_CreateRocketMQNamespace          ← 依赖 ClusterId
        └── tdmq_CreateRocketMQTopic        ← 依赖 ClusterId + NamespaceId
              └── tdmq_SendRocketMQMessage ← 依赖 Topic
        └── tdmq_CreateRocketMQGroup        ← 依赖 ClusterId + NamespaceId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

TDMQ_SPECS: dict[str, ToolStateSpec] = {
    "tdmq_CreateRocketMQNamespace": ToolStateSpec(tool_name="tdmq_CreateRocketMQNamespace", provides=["NamespaceId"],
        dependency=StateDependency(requires=[StateAtom("tdmq_CreateRocketMQCluster", "ClusterId")])),
    "tdmq_CreateRocketMQTopic": ToolStateSpec(tool_name="tdmq_CreateRocketMQTopic", provides=["TopicName"],
        dependency=StateDependency(requires=[StateAtom("tdmq_CreateRocketMQCluster", "ClusterId"), StateAtom("tdmq_CreateRocketMQNamespace", "NamespaceId")])),
    "tdmq_SendRocketMQMessage": ToolStateSpec(tool_name="tdmq_SendRocketMQMessage", provides=["MsgId"],
        dependency=StateDependency(requires=[StateAtom("tdmq_CreateRocketMQTopic", "TopicName")])),
}

tracker = StateTracker()
tracker.record("tdmq_CreateRocketMQCluster", {"ClusterId": "rocketmq-abc"})
tracker.record("tdmq_CreateRocketMQNamespace", {"NamespaceId": "ns-xyz", "ClusterId": "rocketmq-abc"})
can, why = tracker.can_call("tdmq_CreateRocketMQTopic", TDMQ_SPECS)
# can=True, why=[]
```

---

## 4. TDMQ Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="tdmq_SendRocketMQMessage",
    params={"Region": "ap-guangzhou", "ClusterId": "rocketmq-abc",
            "NamespaceId": "ns-xyz", "TopicName": "my-topic",
            "MessageBody": "Hello TDMQ"},
    reasoning="用户请求向 my-topic 发送消息",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["TopicName 必须已创建"],
    result={"error_code": 0, "MsgId": "msg-xxx", "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. TDMQ Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, TDMQ_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("tdmq_ListCluster", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="tdmq_CreateRocketMQCluster, tdmq_CreateRocketMQNamespace, ..."

# Case 2: 必填参数缺失
reports = detector.detect("tdmq_CreateRocketMQTopic", {"Region": "ap-guangzhou", "ClusterId": "rocketmq-abc"})
# → mode="param_out_of_range", detail="Param NamespaceId is required"

# Case 3: 状态未满足（Topic 未创建就发消息）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, TDMQ_SPECS, tracker2)
reports = detector2.detect("tdmq_SendRocketMQMessage", {"Region": "ap-guangzhou", "ClusterId": "r-abc", "NamespaceId": "ns-xyz",
     "TopicName": "t1", "MessageBody": "hello"})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: SendRocketMQMessage

1. validate_call("tdmq_SendRocketMQMessage", params)  ← 参数 schema 校验
2. tracker.can_call("tdmq_SendRocketMQMessage", TDMQ_SPECS)  ← 状态依赖检查
3. Execute tccli tdmq SendRocketMQMessage ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
