"""工具调用 Grounding Trace: 结构化 trace + dataclass"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import uuid
import json
from typing import Any, Optional


class ParamSource(Enum):
    USER_INSTRUCTION = "user_instruction"
    SKILL_SCHEMA = "skill_schema"
    PREVIOUS_RESULT = "previous_result"
    INFERIOR_MODEL = "inferior_model"
    FALLBACK = "fallback"


@dataclass
class GroundingMetadata:
    confidence: float
    source: ParamSource
    constraints: list[str] = field(default_factory=list)
    inferior_model_hint: Optional[str] = None


@dataclass
class ToolCallTrace:
    trace_id: str
    timestamp: str
    call: dict
    grounding: GroundingMetadata
    result: dict
    state_snapshot: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["grounding"]["source"] = self.grounding.source.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def new(
        tool_name: str,
        params: dict,
        reasoning: str,
        confidence: float,
        source: ParamSource,
        constraints: list[str],
        result: dict,
        state_snapshot: Optional[dict] = None,
    ) -> "ToolCallTrace":
        return ToolCallTrace(
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            call={"tool_name": tool_name, "params": params, "reasoning": reasoning},
            grounding=GroundingMetadata(confidence=confidence, source=source, constraints=constraints),
            result=result,
            state_snapshot=state_snapshot,
        )


if __name__ == "__main__":
    trace = ToolCallTrace.new(
        tool_name="cdb_create",
        params={"Region": "ap-guangzhou", "Zone": "ap-guangzhou-3", "InstanceType": "mysql-5.7"},
        reasoning="用户请求在广州地域创建 MySQL 实例",
        confidence=0.95,
        source=ParamSource.USER_INSTRUCTION,
        constraints=["Region 必须是可用区前缀", "InstanceType 必须为 mysql-5.7"],
        result={"error_code": 0, "error_name": "SUCCESS", "data": {"InstanceId": "cdb-abc"}},
        state_snapshot={"existing_instances": 3},
    )
    print(trace.to_json())
