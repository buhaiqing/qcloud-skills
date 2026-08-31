# Tool-Call Grounding — CDB Skill Integration

> **Scope**: `qcloud-cdb-ops` SKILL.md 的工具调用 grounding 指引。  
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

## 2. CDB tccli Commands → ToolSchema Registration

在 agent 执行 cd `tccli cdb` 命令前，注册 schema 并校验参数：

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeDBInstances
register(ToolSchema(
    name="cdb_DescribeDBInstances",
    description="查询 CDB 实例列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "InstanceIds": ParamConstraint(type="array",  required=False),
        "Status":      ParamConstraint(type="array",   required=False),
        "Offset":      ParamConstraint(type="number",  min_val=0,        default=0),
        "Limit":       ParamConstraint(type="number",  min_val=1, max_val=50, default=20),
        "ProjectId":   ParamConstraint(type="number",  default=-1),
    },
    returns={"TotalCount": int, "Items": list},
    error_codes=list(ErrorCode),
))

# CreateDBInstance
register(ToolSchema(
    name="cdb_CreateDBInstance",
    description="创建 CDB MySQL 实例",
    params={
        "Region":         ParamConstraint(type="string", required=True),
        "Zone":           ParamConstraint(type="string", required=True),
        "InstanceType":   ParamConstraint(type="string", required=True),
        "Port":           ParamConstraint(type="number", min_val=1024, max_val=65535, default=3306),
        "Password":       ParamConstraint(type="string", required=True, max_length=32),
        "VpcId":          ParamConstraint(type="string", required=False),
        "SubnetId":       ParamConstraint(type="string", required=False),
        "ChargeType":     ParamConstraint(type="enum", enum_values=["PREPAID", "POSTPAID"], default="POSTPAID"),
        "Period":         ParamConstraint(type="number", min_val=1, max_val=36, default=1),
    },
    returns={"InstanceId": str},
    error_codes=list(ErrorCode),
))

# DeleteBackup
register(ToolSchema(
    name="cdb_DeleteBackup",
    description="删除 CDB 备份",
    params={
        "InstanceId": ParamConstraint(type="string", required=True),
        "BackupId":   ParamConstraint(type="number", required=True),
    },
    returns={"Error": int},
    error_codes=list(ErrorCode),
))

# Validate before execution
ok, msg, code = validate_call("cdb_DescribeDBInstances", {"Region": "ap-guangzhou", "Limit": 200})
# → (False, "Param Limit=200 > max 50", PARAM_OUT_OF_RANGE)
```

---

## 3. CDB State Dependencies

CDB 操作有显式的状态依赖链（见 `state_dependency.py` 的 `SPECS`）：

```
cdb_create (InstanceId)              ← 基础：先创建实例
  └── cdb_create_account (AccountName) ← 依赖 cdb_create.InstanceId
        └── cdb_set_cnf              ← 依赖 cdb_create.InstanceId + cdb_create_account.AccountName=root
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

CDB_SPECS: dict[str, ToolStateSpec] = {
    "cdb_CreateAccounts": ToolStateSpec(
        tool_name="cdb_CreateAccounts",
        provides=["AccountName"],
        dependency=StateDependency(requires=[
            StateAtom("cdb_CreateDBInstance", "InstanceId"),
        ]),
    ),
    "cdb_ModifyInstanceParam": ToolStateSpec(
        tool_name="cdb_ModifyInstanceParam",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("cdb_CreateDBInstance", "InstanceId"),
        ]),
    ),
}

# Agent 执行前检查
tracker = StateTracker()
tracker.record("cdb_CreateDBInstance", {"InstanceId": "cdb-abc"})
can, why = tracker.can_call("cdb_CreateAccounts", CDB_SPECS)
# can=True, why=[]
```

---

## 4. CDB Grounding Trace

每次 tccli 调用后生成 trace，记录参数来源和置信度：

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

# tccli cdb DescribeDBInstances 执行后
trace = ToolCallTrace.new(
    tool_name="cdb_DescribeDBInstances",
    params={"Region": "ap-guangzhou", "Limit": 20},
    reasoning="用户请求查看广州地域所有运行中的实例",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区前缀", "Limit ≤ 50"],
    result={"error_code": 0, "error_name": "SUCCESS", "data": {"Items": []}},
    state_snapshot=tracker.snapshot(),
)
# trace.trace_id / trace.to_json()
```

---

## 5. CDB Hallucination Detection

在 agent 执行 tccli 前，用 `GroundingDetector` 拦截三类幻觉：

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY
from references.toolgrounding.state_dependency import StateTracker, SPECS

detector = GroundingDetector(REGISTRY, CDB_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("cdb_DescrieDBInstance", {"Region": "ap-guangzhou"})
# → HallucinationReport(mode="tool_not_found", suggestion="Did you mean: cdb_DescribeDBInstances, ...")

# Case 2: 参数越界（Zone 不存在）
reports = detector.detect("cdb_CreateDBInstance",
    {"Region": "ap-guangzhou", "Zone": "ap-moon-1", "InstanceType": "mysql-5.7", "Password": "xxx"})
# → HallucinationReport(mode="param_out_of_range", detail="Param Zone=ap-moon-1 ...")

# Case 3: 状态未满足（未创建实例就改参数）
tracker2 = StateTracker()
detector2 = GroundingDetector(REGISTRY, CDB_SPECS, tracker2)
reports = detector2.detect("cdb_ModifyInstanceParam", {"InstanceId": "cdb-xxx"})
# → HallucinationReport(mode="state_not_satisfied", detail="Requires cdb_CreateDBInstance.InstanceId")
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

在 SKILL.md 的「Execute」步骤中嵌入 grounding：

```
## Execute: Describe Instance

1. Validate schema  ← validate_call("cdb_DescribeDBInstances", params)
2. Check state      ← tracker.can_call("cdb_DescribeDBInstances", CDB_SPECS)
3. Execute tccli    ← tccli cdb DescribeDBInstances ...
4. Emit trace       ← ToolCallTrace.new(...) → audit log
5. On failure       ← GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
