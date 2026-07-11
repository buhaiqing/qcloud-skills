"""Inspection strategy apply — Agent inband write-back to Blackboard."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from copilot.blackboard import BlackboardClient, default_board_dir, load_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strategy_validator(board_dir: Path | None = None) -> jsonschema.Draft7Validator:
    schema = load_schema(board_dir)
    subschema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **schema["definitions"]["inspection_strategy"],
        "definitions": {
            "skipped_analyzer": schema["definitions"]["skipped_analyzer"],
            "priority_chain_item": schema["definitions"]["priority_chain_item"],
        },
    }
    return jsonschema.Draft7Validator(
        subschema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


def load_strategy_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_file():
        msg = f"Strategy file not found: {file_path}"
        raise FileNotFoundError(msg)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Invalid strategy JSON: {file_path}"
        raise ValueError(msg) from exc


def validate_strategy(strategy: dict[str, Any], board_dir: Path | None = None) -> None:
    strategy_validator(board_dir).validate(strategy)


def strategy_file_path(session_id: str, board_dir: Path | None = None) -> Path:
    return (board_dir or default_board_dir()) / f"strategy-{session_id}.json"


def apply_strategy(
    session_id: str,
    strategy: dict[str, Any],
    *,
    decision_maker: str | None = None,
    blackboard: BlackboardClient | None = None,
) -> dict[str, Any]:
    """Persist agent strategy to disk + merge into Blackboard evidence_chain."""
    merged = deepcopy(strategy)
    if decision_maker:
        merged["decision_maker"] = decision_maker
    merged.setdefault("strategy_schema", "1.2")
    merged.setdefault("llm_native_target", True)
    dm = merged.get("decision_maker") or decision_maker
    if dm == "llm_reasoner_v1":
        merged.setdefault("execution_path", "llm_api_selective")
    elif dm == "topology_reasoner_v1":
        merged.setdefault("execution_path", "topology_first_then_analyzer")
    else:
        merged.setdefault("execution_path", "agent_inband_selective")

    client = blackboard or BlackboardClient()
    validate_strategy(merged, client.board_dir)

    user_request = str(merged.get("user_request") or "")
    client.get_or_create(session_id, user_request)

    out_path = strategy_file_path(session_id, client.board_dir)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    existing = client.read_evidence_chain(session_id) or {}
    evidence_chain = {
        "schema_version": existing.get("schema_version") or "1.1",
        "built_at": _now(),
        "strategy": merged,
        "plan": existing.get("plan") or {},
        "process": existing.get("process") or [],
        "results": existing.get("results")
        or {
            "overall_verdict": "PENDING",
            "contributions": {},
            "artifact_index": [],
        },
    }
    client.write_evidence_chain(session_id, evidence_chain)

    return {
        "session_id": session_id,
        "strategy_path": str(out_path),
        "decision_maker": merged.get("decision_maker"),
        "selected_analyzers": merged.get("selected_analyzers") or [],
        "skipped_analyzers": merged.get("skipped_analyzers") or [],
    }
