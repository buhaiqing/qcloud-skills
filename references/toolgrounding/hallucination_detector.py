"""幻觉检测器: 三类失效模式检测"""
import difflib
from dataclasses import dataclass

from state_dependency import StateTracker, ToolStateSpec
from tool_schema import REGISTRY, ToolSchema


@dataclass
class HallucinationReport:
    mode: str       # "tool_not_found" | "param_out_of_range" | "state_not_satisfied"
    detail: str
    suggestion: str
    severity: str   # "BLOCKER" | "WARN"


class GroundingDetector:
    def __init__(self, registry: dict[str, ToolSchema], specs: dict[str, ToolStateSpec], tracker: StateTracker):
        self.registry = registry
        self.specs = specs
        self.tracker = tracker

    def detect(self, tool_name: str, params: dict) -> list[HallucinationReport]:
        reports = []

        # 模式1: 工具不存在
        if tool_name not in self.registry:
            candidates = difflib.get_close_matches(tool_name, self.registry.keys(), n=3, cutoff=0.6)
            reports.append(HallucinationReport(
                mode="tool_not_found",
                detail=f"Tool {tool_name!r} not in registry",
                suggestion=f"Did you mean: {', '.join(candidates)}?" if candidates else "No similar tool found",
                severity="BLOCKER",
            ))
            return reports

        # 模式2: 参数越界
        schema = self.registry[tool_name]
        ok, msg, code = schema.validate_params(params)
        if not ok:
            reports.append(HallucinationReport(
                mode="param_out_of_range",
                detail=msg or str(code),
                suggestion=self._param_suggestion(schema),
                severity="BLOCKER",
            ))

        # 模式3: 状态未满足
        can, why = self.tracker.can_call(tool_name, self.specs)
        if not can:
            reports.append(HallucinationReport(
                mode="state_not_satisfied",
                detail="; ".join(why),
                suggestion=f"Call required tools first: {[self._extract_tool(m) for m in why]}",
                severity="BLOCKER",
            ))

        return reports

    @staticmethod
    def _param_suggestion(schema: ToolSchema) -> str:
        parts = []
        for pname, constraint in schema.params.items():
            if constraint.type == "enum" and constraint.enum_values:
                parts.append(f"{pname}: one of {constraint.enum_values}")
            elif constraint.type == "number":
                hint = "number"
                if constraint.min_val is not None:
                    hint += f" >= {constraint.min_val}"
                if constraint.max_val is not None:
                    hint += f" <= {constraint.max_val}"
                parts.append(f"{pname}: {hint}")
        return f"Valid params: {', '.join(parts)}"

    @staticmethod
    def _extract_tool(missing_msg: str) -> str:
        # "Requires cdb_create.InstanceId" → "cdb_create"
        parts = missing_msg.split()
        if len(parts) >= 2:
            return parts[1].split(".")[0]
        return missing_msg


if __name__ == "__main__":
    from state_dependency import SPECS, StateTracker
    from tool_schema import REGISTRY

    tracker = StateTracker()
    tracker.record("cdb_create", {"InstanceId": "cdb-789"})
    detector = GroundingDetector(REGISTRY, SPECS, tracker)

    # Case 1: 工具名拼错
    r = detector.detect("cvm_descrie_instances", {"Region": "ap-guangzhou"})
    print(f"[1] tool_not_found: {r[0].mode if r else 'none'}")

    # Case 2: 参数越界
    r = detector.detect("cvm_describe_instances", {"Region": "ap-moon", "Limit": 200})
    print(f"[2] param_out_of_range: {[x.mode for x in r]}")

    # Case 3: 状态未满足
    r = detector.detect("cdb_create_account", {})
    print(f"[3] state_not_satisfied: {[x.mode for x in r]}")
