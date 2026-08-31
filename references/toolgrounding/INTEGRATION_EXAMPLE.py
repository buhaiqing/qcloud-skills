"""CDB Skill Integration — toolgrounding library end-to-end demo.

Demonstrates tool_schema + state_dependency + grounding_trace + hallucination_detector
on a realistic CDB tccli command sequence (no real API calls needed — uses mocks).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from grounding_trace import ParamSource, ToolCallTrace
from hallucination_detector import GroundingDetector
from state_dependency import StateAtom, StateDependency, StateTracker, ToolStateSpec
from tool_schema import ErrorCode, ParamConstraint, ToolSchema, register, validate_call

# ── Step 1: Register CDB tccli commands ───────────────────────────────────────

register(ToolSchema(
    name="cdb_CreateDBInstance",
    description="创建 CDB MySQL 实例",
    params={
        "Region":       ParamConstraint(type="string", required=True),
        "Zone":         ParamConstraint(type="string", required=True),
        "InstanceType": ParamConstraint(type="string", required=True),
        "Port":         ParamConstraint(type="number", min_val=1024, max_val=65535, default=3306),
        "Password":     ParamConstraint(type="string", required=True, max_length=32),
        "ChargeType":   ParamConstraint(type="enum", enum_values=["PREPAID", "POSTPAID"], default="POSTPAID"),
        "Period":       ParamConstraint(type="number", min_val=1, max_val=36, default=1),
    },
    returns={"InstanceId": str},
    error_codes=list(ErrorCode),
))

register(ToolSchema(
    name="cdb_DescribeDBInstances",
    description="查询 CDB 实例列表",
    params={
        "Region":      ParamConstraint(type="string", required=True),
        "InstanceIds": ParamConstraint(type="array",  required=False),
        "Status":      ParamConstraint(type="array",   required=False),
        "Offset":      ParamConstraint(type="number",  min_val=0, default=0),
        "Limit":       ParamConstraint(type="number",  min_val=1, max_val=50, default=20),
    },
    returns={"TotalCount": int, "Items": list},
    error_codes=list(ErrorCode),
))

register(ToolSchema(
    name="cdb_CreateAccounts",
    description="在指定 CDB 实例上创建数据库账号",
    params={
        "InstanceId": ParamConstraint(type="string", required=True),
        "Accounts":   ParamConstraint(type="array",   required=True),
    },
    returns={"AccountName": str},
    error_codes=list(ErrorCode),
))


# ── Step 2: State dependencies ─────────────────────────────────────────────

CDB_SPECS: dict[str, ToolStateSpec] = {
    "cdb_CreateAccounts": ToolStateSpec(
        tool_name="cdb_CreateAccounts",
        provides=["AccountName"],
        dependency=StateDependency(requires=[
            StateAtom("cdb_CreateDBInstance", "InstanceId"),
        ]),
    ),
}

tracker = StateTracker()
print("[Step 1] StateTracker — CreateDBInstance creates InstanceId")
tracker.record("cdb_CreateDBInstance", {"InstanceId": "cdb-12345", "Zone": "ap-guangzhou-3"})
can, why = tracker.can_call("cdb_CreateAccounts", CDB_SPECS)
print(f"  can_call={can}  (expected True)")
assert can, f"Expected can_call=True, got {why}"

print("\n[Step 2] StateTracker — empty tracker blocks CreateAccounts")
tracker2 = StateTracker()
can2, why2 = tracker2.can_call("cdb_CreateAccounts", CDB_SPECS)
print(f"  can_call={can2}, why={why2}  (expected False)")
assert not can2, "Expected can_call=False for empty tracker"


# ── Step 3: ToolCallTrace ───────────────────────────────────────────────────

print("\n[Step 3] ToolCallTrace — trace a CreateDBInstance call")
trace = ToolCallTrace.new(
    tool_name="cdb_CreateDBInstance",
    params={"Region": "ap-guangzhou", "Zone": "ap-guangzhou-3",
            "InstanceType": "mysql-5.7", "Port": 3306, "Password": "MyP@ssw0rd!"},
    reasoning="用户请求在广州地域创建一个 MySQL 5.7 实例",
    confidence=0.92,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["Region 必须是腾讯云可用区前缀", "Zone 必须为 Region 下的可用区"],
    result={"error_code": 0, "error_name": "SUCCESS", "data": {"InstanceId": "cdb-67890"}},
    state_snapshot=tracker.snapshot(),
)
assert trace.trace_id, "trace_id must be non-empty"
assert trace.grounding.source == ParamSource.USER_INSTRUCTION
print(f"  trace_id={trace.trace_id}")
print(f"  source={trace.grounding.source.value}  confidence={trace.grounding.confidence}")


# ── Step 4: Hallucination Detection ────────────────────────────────────────

print("\n[Step 4] HallucinationDetector — three failure modes")
detector = GroundingDetector(__import__("tool_schema", fromlist=["REGISTRY"]).REGISTRY,
                              CDB_SPECS, tracker)

# Case A: tool name misspelled
reports = detector.detect("cdb_DescrieDBInstances", {"Region": "ap-guangzhou"})
assert len(reports) == 1 and reports[0].mode == "tool_not_found"
print(f"  [A] tool_not_found     → {reports[0].suggestion}")

# Case B: param out of range
reports = detector.detect("cdb_DescribeDBInstances",
                          {"Region": "ap-guangzhou", "Limit": 999})
assert len(reports) == 1 and reports[0].mode == "param_out_of_range"
print(f"  [B] param_out_of_range → {reports[0].detail}")

# Case C: state not satisfied — all required params present but prerequisite not called
detector2 = GroundingDetector(
    __import__("tool_schema", fromlist=["REGISTRY"]).REGISTRY,
    CDB_SPECS, tracker2)
# Pass all required params so param validation passes; state check fails
reports = detector2.detect("cdb_CreateAccounts",
    {"InstanceId": "cdb-xxx", "Accounts": [{"User": "appuser", "Host": "%"}]})
state_reports = [r for r in reports if r.mode == "state_not_satisfied"]
assert len(state_reports) == 1 and state_reports[0].mode == "state_not_satisfied"
print(f"  [C] state_not_satisfied → {state_reports[0].detail}")


# ── Step 5: Schema validate call ───────────────────────────────────────────

print("\n[Step 5] validate_call — valid vs invalid params")
ok, msg, code = validate_call("cdb_DescribeDBInstances",
                               {"Region": "ap-guangzhou", "Limit": 20})
print(f"  valid:   ok={ok}  (expected True)")
assert ok

ok2, msg2, code2 = validate_call("cdb_DescribeDBInstances",
                                  {"Region": "ap-guangzhou", "Limit": 999})
print(f"  invalid: ok={ok2}, msg={msg2}  (expected False)")
assert not ok2 and code2 == ErrorCode.PARAM_OUT_OF_RANGE

print("\n✓ INTEGRATION_EXAMPLE passed — all assertions OK")
