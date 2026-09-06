"""Tool Schema 严格化: 函数签名校验 + 结构化错误码"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(Enum):
    SUCCESS = 0
    TOOL_NOT_FOUND = 1001
    PARAM_MISSING = 1002
    PARAM_TYPE_ERROR = 1003
    PARAM_OUT_OF_RANGE = 1004
    STATE_NOT_SATISFIED = 1005
    EXECUTION_ERROR = 1999


@dataclass
class ParamConstraint:
    type: str  # "string" | "number" | "boolean" | "object" | "array" | "enum"
    enum_values: list | None = None
    min_val: float | None = None
    max_val: float | None = None
    max_length: int | None = None
    pattern: str | None = None
    required: bool = False
    default: Any = None


@dataclass
class ToolSchema:
    name: str
    description: str
    params: dict[str, ParamConstraint]
    returns: dict[str, Any]  # expected return keys + types
    error_codes: list[ErrorCode]

    def validate_params(self, params: dict) -> tuple[bool, str | None, ErrorCode | None]:
        for pname, constraint in self.params.items():
            val = params.get(pname)
            if val is None:
                if constraint.required:
                    return False, f"Missing required param: {pname}", ErrorCode.PARAM_MISSING
                continue
            if constraint.type == "enum":
                if val not in constraint.enum_values:
                    return False, f"Param {pname}={val!r} not in {constraint.enum_values}", ErrorCode.PARAM_OUT_OF_RANGE
            elif constraint.type == "number":
                if not isinstance(val, (int, float)):
                    return False, f"Param {pname} type must be number", ErrorCode.PARAM_TYPE_ERROR
                if constraint.min_val is not None and val < constraint.min_val:
                    return False, f"Param {pname}={val} < min {constraint.min_val}", ErrorCode.PARAM_OUT_OF_RANGE
                if constraint.max_val is not None and val > constraint.max_val:
                    return False, f"Param {pname}={val} > max {constraint.max_val}", ErrorCode.PARAM_OUT_OF_RANGE
            elif constraint.type == "string":
                if not isinstance(val, str):
                    return False, f"Param {pname} type must be string", ErrorCode.PARAM_TYPE_ERROR
                if constraint.max_length and len(val) > constraint.max_length:
                    return False, f"Param {pname} length {len(val)} > max {constraint.max_length}", ErrorCode.PARAM_OUT_OF_RANGE
                if constraint.pattern and not re.fullmatch(constraint.pattern, val):
                    return False, f"Param {pname} pattern mismatch", ErrorCode.PARAM_OUT_OF_RANGE
        return True, None, None


@dataclass
class ToolCallResult:
    error_code: ErrorCode
    data: Any | None = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "data": self.data,
            "message": self.message,
        }


# --- Registry ---
REGISTRY: dict[str, ToolSchema] = {}


def register(schema: ToolSchema):
    REGISTRY[schema.name] = schema


def validate_call(tool_name: str, params: dict) -> tuple[bool, str | None, ErrorCode | None]:
    schema = REGISTRY.get(tool_name)
    if schema is None:
        return False, f"Tool {tool_name!r} not found", ErrorCode.TOOL_NOT_FOUND
    return schema.validate_params(params)


# --- Register example tool ---
register(ToolSchema(
    name="cdb_create_account",
    description="Create CDB account (InstanceId optional for demo; state dependency is checked by tracker)",
    params={"InstanceId": ParamConstraint(type="string", required=False)},
    returns={"AccountName": str},
    error_codes=list(ErrorCode),
))

register(ToolSchema(
    name="cvm_describe_instances",
    description="Query CVM instances",
    params={
        "Region": ParamConstraint(type="enum", enum_values=["ap-guangzhou", "ap-shanghai", "ap-beijing"], required=True),
        "Limit": ParamConstraint(type="number", min_val=1, max_val=100, default=20),
        "Offset": ParamConstraint(type="number", min_val=0, default=0),
        "InstanceIds": ParamConstraint(type="array", default=[]),
    },
    returns={"TotalCount": int, "InstanceSet": list},
    error_codes=list(ErrorCode),
))


if __name__ == "__main__":
    # Demo
    ok, msg, code = validate_call("cvm_describe_instances", {"Region": "ap-guangzhou", "Limit": 50})
    print(f"[1] ok={ok}, msg={msg}, code={code}")

    ok2, msg2, code2 = validate_call("cvm_describe_instances", {"Region": "ap-moon", "Limit": 200})
    print(f"[2] ok={ok2}, msg={msg2}, code={code2}")

    ok3, msg3, code3 = validate_call("cvm_describe_instances", {"Region": "ap-guangzhou"})
    print(f"[3] ok={ok3}, msg={msg3}, code={code3}")
