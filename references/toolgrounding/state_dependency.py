"""工具状态依赖显式化: 状态机 + StateTracker"""
from dataclasses import dataclass, field


@dataclass
class StateAtom:
    tool_name: str
    output_key: str
    expected_value: str | None = None  # None = any non-null

    def __str__(self):
        val_hint = f"={self.expected_value}" if self.expected_value else ""
        return f"{self.tool_name}.{self.output_key}{val_hint}"


@dataclass
class StateDependency:
    requires: list[StateAtom] = field(default_factory=list)


@dataclass
class ToolStateSpec:
    tool_name: str
    provides: list[str]
    dependency: StateDependency


class StateTracker:
    def __init__(self):
        self._state: dict[str, dict] = {}

    def record(self, tool_name: str, result: dict):
        self._state[tool_name] = result

    def check(self, spec: ToolStateSpec) -> tuple[bool, list[str]]:
        missing = []
        for atom in spec.dependency.requires:
            tool_state = self._state.get(atom.tool_name, {})
            val = tool_state.get(atom.output_key)
            if val is None:
                missing.append(f"Requires {atom}")
            elif atom.expected_value is not None and val != atom.expected_value:
                missing.append(f"Requires {atom} (got {val!r})")
        return len(missing) == 0, missing

    def can_call(self, tool_name: str, specs: dict[str, ToolStateSpec]) -> tuple[bool, list[str]]:
        spec = specs.get(tool_name)
        if spec is None:
            return True, []
        return self.check(spec)

    def snapshot(self) -> dict:
        import copy
        return copy.deepcopy(self._state)


# --- Demo specs ---
SPECS: dict[str, ToolStateSpec] = {
    "cdb_create_account": ToolStateSpec(
        tool_name="cdb_create_account",
        provides=["AccountName"],
        dependency=StateDependency(requires=[
            StateAtom("cdb_create", "InstanceId"),
            StateAtom("vpc_create", "VpcId"),
        ]),
    ),
    "cdb_set_cnf": ToolStateSpec(
        tool_name="cdb_set_cnf",
        provides=[],
        dependency=StateDependency(requires=[
            StateAtom("cdb_create", "InstanceId"),
            StateAtom("cdb_create_account", "AccountName", expected_value="root"),
        ]),
    ),
}


if __name__ == "__main__":
    tracker = StateTracker()
    tracker.record("ccn_create", {"CcnId": "ccn-123"})
    tracker.record("vpc_create", {"VpcId": "vpc-456"})
    tracker.record("cdb_create", {"InstanceId": "cdb-789", "VpcId": "vpc-456"})

    can, why = tracker.can_call("cdb_create_account", SPECS)
    print(f"[1] cdb_create_account can_call={can}, missing={why}")

    tracker2 = StateTracker()
    tracker2.record("ccn_create", {"CcnId": "ccn-123"})
    can2, why2 = tracker2.can_call("cdb_create_account", SPECS)
    print(f"[2] cdb_create_account can_call={can2}, missing={why2}")
