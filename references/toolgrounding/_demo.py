"""完整演示: 工具调用 Grounding 严格化全链路"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tool_schema import REGISTRY, validate_call, ErrorCode, ToolSchema, ParamConstraint
from state_dependency import StateTracker, SPECS, StateAtom, StateDependency, ToolStateSpec
from grounding_trace import ToolCallTrace, ParamSource
from hallucination_detector import GroundingDetector


def main():
    print("=" * 60)
    print("LLM 工具调用 Grounding 严格化 — 全链路演示")
    print("=" * 60)

    # ── Step 1: 正常调用 ──
    print("\n[Step 1] 正常工具调用校验")
    ok, msg, code = validate_call("cvm_describe_instances", {"Region": "ap-guangzhou", "Limit": 50})
    print(f"  ok={ok}, msg={msg}, code={code}")

    # ── Step 2: 参数越界 ──
    print("\n[Step 2] 参数越界检测")
    ok2, msg2, code2 = validate_call("cvm_describe_instances", {"Region": "ap-moon", "Limit": 200})
    print(f"  ok={ok2}, msg={msg2}, code={code2}")

    # ── Step 3: 状态依赖 ──
    print("\n[Step 3] 状态依赖校验")
    tracker = StateTracker()
    tracker.record("vpc_create", {"VpcId": "vpc-456"})
    tracker.record("cdb_create", {"InstanceId": "cdb-789", "VpcId": "vpc-456"})

    can, why = tracker.can_call("cdb_create_account", SPECS)
    print(f"  can_call={can}, missing={why}")

    tracker2 = StateTracker()
    can2, why2 = tracker2.can_call("cdb_create_account", SPECS)
    print(f"  (no state) can_call={can2}, missing={why2}")

    # ── Step 4: Grounding Trace ──
    print("\n[Step 4] Grounding Trace 记录")
    trace = ToolCallTrace.new(
        tool_name="cdb_create",
        params={"Region": "ap-guangzhou", "Zone": "ap-guangzhou-3", "InstanceType": "mysql-5.7"},
        reasoning="用户请求在广州地域创建 MySQL 实例",
        confidence=0.95,
        source=ParamSource.USER_INSTRUCTION,
        constraints=["Region 必须是可用区前缀", "InstanceType 必须为 mysql-5.7"],
        result={"error_code": 0, "error_name": "SUCCESS", "data": {"InstanceId": "cdb-abc"}},
        state_snapshot=tracker.snapshot(),
    )
    print(f"  trace_id={trace.trace_id}")
    print(f"  timestamp={trace.timestamp}")

    # ── Step 5: 幻觉检测 ──
    print("\n[Step 5] 幻觉检测器 — 三类失效模式")
    detector = GroundingDetector(REGISTRY, SPECS, tracker)

    # 工具不存在
    r1 = detector.detect("cvm_descrie_instances", {"Region": "ap-guangzhou"})
    print(f"  [tool_not_found]     mode={r1[0].mode if r1 else 'none'}, suggestion={r1[0].suggestion if r1 else ''}")

    # 参数越界
    r2 = detector.detect("cvm_describe_instances", {"Region": "ap-moon", "Limit": 200})
    print(f"  [param_out_of_range] mode={r2[0].mode if r2 else 'none'}, detail={r2[0].detail if r2 else ''}")

    # 状态未满足（用空 tracker2 触发 state_not_satisfied；cdb_create_account 已注册但无状态）
    detector2 = GroundingDetector(REGISTRY, SPECS, tracker2)
    r3 = detector2.detect("cdb_create_account", {})
    print(f"  [state_not_satisfied] mode={r3[0].mode if r3 else 'none'}, detail={r3[0].detail if r3 else ''}")

    print("\n✓ 全链路演示完成")


if __name__ == "__main__":
    main()
