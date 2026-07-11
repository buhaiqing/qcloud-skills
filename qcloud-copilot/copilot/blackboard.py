from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_URL = "https://qcloud-skills/schema/blackboard/v1.json"
SCHEMA_VERSION = "1.2"

# Schema migration chain (additive, idempotent).  See AGENTS.md §14.6.
_SUPPORTED_SCHEMA_VERSIONS: tuple[str, ...] = ("1.0", "1.1", "1.2")
_MIGRATIONS: dict[str, str] = {
    "1.0": "migrate_to_1_1",
    "1.1": "migrate_to_1_2",
}


def migrate_to_1_1(board: dict[str, Any]) -> dict[str, Any]:
    """1.0 → 1.1: introduce shared_context.evidence_chain (additive)."""
    ctx = board.setdefault("shared_context", {})
    ctx.setdefault("evidence_chain", None)
    return board


def migrate_to_1_2(board: dict[str, Any]) -> dict[str, Any]:
    """1.1 → 1.2: schema bumps to allow pending_action.action='ask_user_response' + 5 ask_user fields.

    Pure version metadata bump; no field migration needed because all new fields
    on pending_action are optional and additively defined in schema.json.
    """
    return board


def migrate_board(board: dict[str, Any]) -> dict[str, Any]:
    """Run pending migrations in order; idempotent (no-op when already at HEAD)."""
    current = board.get("schema_version", "1.0")
    while current in _MIGRATIONS:
        next_step = _MIGRATIONS[current]
        if next_step == "migrate_to_1_1":
            board = migrate_to_1_1(board)
            board["schema_version"] = "1.1"
        elif next_step == "migrate_to_1_2":
            board = migrate_to_1_2(board)
            board["schema_version"] = "1.2"
        current = board["schema_version"]
    return board


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents until qcloud-skills repo root is found."""
    candidate = (start or Path.cwd()).resolve()
    for _ in range(10):
        if (candidate / "qcloud-copilot").is_dir() and (candidate / "AGENTS.md").is_file():
            return candidate
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return Path.cwd().resolve()


def default_board_dir() -> Path:
    return find_repo_root() / ".runtime" / "blackboard"


def schema_path(board_dir: Path | None = None) -> Path:
    asset = find_repo_root() / "qcloud-copilot" / "assets" / "blackboard.schema.json"
    if asset.is_file():
        return asset
    return (board_dir or default_board_dir()) / "schema.json"


def load_schema(board_dir: Path | None = None) -> dict[str, Any]:
    path = schema_path(board_dir)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_blackboard(data: dict[str, Any], board_dir: Path | None = None) -> None:
    schema = load_schema(board_dir)
    validator = jsonschema.Draft7Validator(
        schema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )
    validator.validate(data)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_board(session_id: str, user_request: str) -> dict[str, Any]:
    now = _now_iso()
    return {
        "$schema": SCHEMA_URL,
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "plan_id": None,
        "user_request": user_request,
        "created_at": now,
        "updated_at": now,
        "status": "active",
        "shared_context": {
            "contributions": {},
            "pending_actions": [],
        },
        "plan": None,
    }


def _merge_contribution(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Merge contributions for the same skill key (Phase 3 concurrent writes)."""
    if not existing:
        return deepcopy(incoming)
    merged = deepcopy(existing)
    for key, value in incoming.items():
        if key == "findings":
            seen = {f.get("id") for f in merged.get("findings", []) if isinstance(f, dict)}
            for finding in value:
                fid = finding.get("id") if isinstance(finding, dict) else None
                if fid not in seen:
                    merged.setdefault("findings", []).append(finding)
                    if fid:
                        seen.add(fid)
        elif key == "topology_hints":
            merged["topology_hints"] = sorted(
                set(merged.get("topology_hints", [])) | set(value or [])
            )
        elif key == "metadata" and isinstance(value, dict):
            merged.setdefault("metadata", {}).update(value)
        else:
            merged[key] = value
    return merged


class BlackboardClient:
    """Session-scoped cross-skill context bus (.runtime/blackboard/{session_id}.json)."""

    def __init__(self, board_dir: Path | None = None) -> None:
        self.board_dir = board_dir or default_board_dir()
        self.board_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.board_dir / f"{session_id}.json"

    def _lock_path(self, session_id: str) -> Path:
        return self.board_dir / f"{session_id}.lock"

    @contextmanager
    def _session_lock(self, session_id: str) -> Iterator[None]:
        lock_path = self._lock_path(session_id)
        lock_path.touch(exist_ok=True)
        with lock_path.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def create(self, session_id: str, user_request: str) -> dict[str, Any]:
        with self._session_lock(session_id):
            path = self._path(session_id)
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
            board = empty_board(session_id, user_request)
            validate_blackboard(board, self.board_dir)
            self._save_unlocked(board)
            return board

    def load(self, session_id: str) -> dict[str, Any] | None:
        path = self._path(session_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_blackboard(data, self.board_dir)
        return self._maybe_migrate(data)

    def save(self, board: dict[str, Any]) -> None:
        session_id = board["session_id"]
        with self._session_lock(session_id):
            self._save_unlocked(deepcopy(board))

    def _save_unlocked(self, board: dict[str, Any]) -> None:
        board["updated_at"] = _now_iso()
        validate_blackboard(board, self.board_dir)
        session_id = board["session_id"]
        self._path(session_id).write_text(
            json.dumps(board, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_or_create(self, session_id: str, user_request: str = "") -> dict[str, Any]:
        existing = self.load(session_id)
        if existing is not None:
            return existing
        return self.create(session_id, user_request)

    def set_status(self, session_id: str, status: str) -> dict[str, Any]:
        with self._session_lock(session_id):
            board = self._load_unlocked(session_id)
            board["status"] = status
            self._save_unlocked(board)
            return board

    def write_contribution(
        self, session_id: str, skill: str, contribution: dict[str, Any]
    ) -> dict[str, Any]:
        with self._session_lock(session_id):
            board = self._load_unlocked(session_id)
            existing = board["shared_context"]["contributions"].get(skill)
            board["shared_context"]["contributions"][skill] = _merge_contribution(
                existing,
                contribution,
            )
            self._save_unlocked(board)
            return board

    def _load_unlocked(self, session_id: str) -> dict[str, Any]:
        path = self._path(session_id)
        if not path.is_file():
            msg = f"Blackboard not found for session: {session_id}"
            raise FileNotFoundError(msg)
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_blackboard(data, self.board_dir)
        return self._maybe_migrate(data)

    @staticmethod
    def _maybe_migrate(data: dict[str, Any]) -> dict[str, Any]:
        """Run pending schema migrations in-memory; only persist via mutation methods."""
        return migrate_board(data)

    def read_contributions(
        self,
        session_id: str,
        skills: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        board = self._require(session_id)
        contributions = board["shared_context"]["contributions"]
        if skills is None:
            return deepcopy(contributions)
        return {name: deepcopy(contributions[name]) for name in skills if name in contributions}

    def read_topology_hints(self, session_id: str) -> list[str]:
        board = self._require(session_id)
        hints: set[str] = set()
        for contribution in board["shared_context"]["contributions"].values():
            for hint in contribution.get("topology_hints", []):
                if hint:
                    hints.add(hint)
        return sorted(hints)

    def add_pending_action(self, session_id: str, action: dict[str, Any]) -> dict[str, Any]:
        with self._session_lock(session_id):
            board = self._load_unlocked(session_id)
            board["shared_context"]["pending_actions"].append(action)
            self._save_unlocked(board)
            return board

    def write_evidence_chain(
        self, session_id: str, evidence_chain: dict[str, Any]
    ) -> dict[str, Any]:
        with self._session_lock(session_id):
            board = self._load_unlocked(session_id)
            board["shared_context"]["evidence_chain"] = deepcopy(evidence_chain)
            self._save_unlocked(board)
            return board

    def read_evidence_chain(self, session_id: str) -> dict[str, Any] | None:
        board = self._require(session_id)
        chain = board.get("shared_context", {}).get("evidence_chain")
        return deepcopy(chain) if chain else None

    def write_plan_snapshot(self, session_id: str, plan: Any) -> dict[str, Any]:
        """Persist plan summary to blackboard.plan (schema-compatible)."""
        with self._session_lock(session_id):
            board = self._load_unlocked(session_id)
            plan_id = getattr(plan, "plan_id", None) or "inline-plan"
            steps = getattr(plan, "steps", [])
            board["plan_id"] = plan_id
            board["plan"] = {
                "plan_id": plan_id,
                "steps": [
                    {"id": step.id, "type": step.type, "skill": step.skill} for step in steps
                ],
                "current_step": 0,
                "step_results": {},
            }
            self._save_unlocked(board)
            return board

    def _require(self, session_id: str) -> dict[str, Any]:
        board = self.load(session_id)
        if board is None:
            msg = f"Blackboard not found for session: {session_id}"
            raise FileNotFoundError(msg)
        return board
