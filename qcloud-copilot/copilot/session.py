from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from copilot.blackboard import BlackboardClient
from copilot.models import SessionState, ExecutionPlan


_MEMOR_DIR = Path.home() / ".omo" / "memor" / "copilot" / "sessions"


class SessionManager:
    def __init__(self, blackboard: BlackboardClient | None = None) -> None:
        self._blackboard = blackboard or BlackboardClient()

    def init_blackboard(self, session_id: str, user_request: str) -> dict:
        """Create or load Level 3 blackboard for this session."""
        return self._blackboard.get_or_create(session_id, user_request)

    def blackboard_client(self) -> BlackboardClient:
        return self._blackboard

    def create_session(self) -> SessionState:
        session_id = f"ses-{uuid.uuid4().hex[:8]}"
        state = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            history=[],
            current_plan=None,
            context={},
        )
        self._save(state)
        return state

    def save_plan(self, session_id: str, plan: ExecutionPlan) -> None:
        state = self.load_session(session_id)
        if state is None:
            return
        state.current_plan = plan
        self._save(state)

    def append_history(self, session_id: str, entry: dict) -> None:
        state = self.load_session(session_id)
        if state is None:
            return
        state.history.append(entry)
        self._save(state)

    def get_or_create(self, session_id: str) -> SessionState:
        state = self.load_session(session_id)
        if state is not None:
            return state
        new_state = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            history=[],
            current_plan=None,
            context={},
        )
        self._save(new_state)
        return new_state

    def update_context(self, session_id: str, updates: dict) -> None:
        state = self.load_session(session_id)
        if state is None:
            return
        state.context.update(updates)
        self._save(state)

    def delete_session(self, session_id: str) -> None:
        path = _MEMOR_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()

    def load_session(self, session_id: str) -> SessionState | None:
        path = _MEMOR_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        import json

        data = json.loads(path.read_text())
        from copilot.models import SessionState as SM

        return SM(**data)

    def list_sessions(self) -> list[str]:
        if not _MEMOR_DIR.exists():
            return []
        return [p.stem for p in _MEMOR_DIR.glob("ses-*.json")]

    def _save(self, state: SessionState) -> None:
        _MEMOR_DIR.mkdir(parents=True, exist_ok=True)
        import json

        path = _MEMOR_DIR / f"{state.session_id}.json"
        path.write_text(json.dumps(state.__dict__, default=str, ensure_ascii=False))
