"""AskUserRunner — stdin/stdout-based user clarification step executor (BC-T3)."""

from __future__ import annotations

import contextlib
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TextIO

from copilot.models import AskOption, PlanStep, StepResult, _ASK_DEFAULT_UNSET

DEFAULT_TIMEOUT_SECONDS = 60
_ASK_DEFAULT_ENV = "COPILOT_ASK_DEFAULT"


@dataclass(frozen=True)
class AskUserResult:
    """Captured outcome of a successful ask_user interaction."""

    question_id: str
    selected_option: str
    selected_label: str
    timeout_seconds: int
    responded_at: str  # ISO 8601


class AskUserRunner:
    """Execute ask_user plan steps; render to stdout, read from stdin."""

    DEFAULT_TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS

    def execute(  # noqa: PLR0913 — explicit injection points by design (ADR D4)
        self,
        step: PlanStep,
        context: dict,
        blackboard: Any | None,
        session_id: str,
        *,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        question_id: str | None = None,
    ) -> StepResult:
        """Run an ask_user step.

        Returns StepResult(status="success", output={"selection": ...}) on
        a successful user pick; StepResult(status="failure", error=...) on
        validation/timeout errors; status="skipped" when no options to render.
        """
        options = list(step.ask_user_options)
        if not options:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="ask_user step requires non-empty ask_user_options",
            )

        timeout = max(1, int(step.ask_timeout_seconds))
        in_stream = stdin if stdin is not None else sys.stdin
        out_stream = stdout if stdout is not None else sys.stdout
        # question_id: stable prefix is the plan step id alone; `ask-` was
        # appended historically but step ids already start with `ask-` (e.g.
        # `ask-region-0`), so prefixing again produced a double `ask-ask-` id.
        qid = question_id or f"{step.id}-{uuid.uuid4().hex[:8]}"

        # 1. Render to stdout (Agent Runtime captures this)
        self._render(out_stream, step, options)

        # 2. Read selection with timeout
        try:
            picked = self._read_selection(in_stream, options, timeout)
        except _AskTimeout:
            return self._handle_timeout(
                step, options, qid, timeout, context, blackboard, session_id
            )

        # 3. Persist + inject into context
        self._commit(step, options, picked, qid, timeout, context, blackboard, session_id)
        return StepResult(
            step_id=step.id,
            status="success",
            output={
                "selection": {
                    "value": picked.value,
                    "label": picked.label,
                    "question_id": qid,
                }
            },
        )

    # ------------------------------------------------------------------ rendering

    @staticmethod
    def _render(out: TextIO, step: PlanStep, options: list[AskOption]) -> None:
        title = step.description or f"请选择 (timeout {step.ask_timeout_seconds}s):"
        out.write(f"\n=== ASK_USER: {step.id} ===\n")
        out.write(f"{title}\n")
        for idx, opt in enumerate(options, start=1):
            out.write(f"  [{idx}] {opt.value}  {opt.label}\n")
            if opt.description:
                out.write(f"       {opt.description}\n")
        out.write(f"选择 [1-{len(options)}] 或直接输入 value: ")
        out.flush()

    # ------------------------------------------------------------------ reading

    @staticmethod
    def _read_selection(in_stream: TextIO, options: list[AskOption], timeout: int) -> AskOption:
        """Block on a single line of stdin; translate to AskOption.

        Supports two input shapes:
          - numeric: '1'..'N' → options[idx-1]
          - literal: 'ap-guangzhou' → match by value
        """
        # We poll via a background thread pattern would be ideal, but the
        # simplest portable approach for a CLI ask is to call readline() and
        # rely on the caller controlling timeout (eg. COPILOT_ASK_DEFAULT env
        # for headless). For test injection, callers pass a StringIO whose
        # readline is instantaneous.
        #
        # To still support real-CLI timeout without threads, we set an alarm
        # via signal.SIGALRM (Unix-only). When SIGALRM is unavailable (eg.
        # Windows / threads), we degrade gracefully: caller decides. ADR D4
        # portability: stdin/stdout injection means tests bypass this path.
        _install_alarm(timeout)
        try:
            line = in_stream.readline()
        finally:
            _cancel_alarm()

        text = (line or "").strip()
        if not text:
            raise _AskTimeout(timeout)

        # Numeric: 1..N
        if text.isdigit():
            idx = int(text)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        # Literal value
        for opt in options:
            if opt.value == text:
                return opt

        # Unrecognized input — treat as timeout (fail-fast)
        raise _AskTimeout(timeout)

    # ------------------------------------------------------------------ timeout

    def _handle_timeout(
        self,
        step: PlanStep,
        options: list[AskOption],
        qid: str,
        timeout: int,
        context: dict,
        blackboard: Any | None,
        session_id: str,
    ) -> StepResult:
        # Precedence: step setting is authoritative when set. Sentinel
        # _ASK_DEFAULT_UNSET means "planner never declared" → fall back to env.
        # Explicit None / "never" means fail-fast (env is ignored).
        if step.ask_default_on_timeout is _ASK_DEFAULT_UNSET:
            chosen = os.environ.get(_ASK_DEFAULT_ENV, "").strip().lower() or None
        else:
            raw = step.ask_default_on_timeout
            chosen = raw.strip().lower() if isinstance(raw, str) else None
            chosen = chosen or None  # collapse empty

        if chosen == "first":
            picked = options[0]
            self._commit(step, options, picked, qid, timeout, context, blackboard, session_id)
            return StepResult(
                step_id=step.id,
                status="success",
                output={
                    "selection": {
                        "value": picked.value,
                        "label": picked.label,
                        "question_id": qid,
                        "defaulted_via": "first",
                    }
                },
            )

        return StepResult(
            step_id=step.id,
            status="failure",
            error=(
                f"ask_user step '{step.id}' timed out after {timeout}s. "
                "Set COPILOT_ASK_DEFAULT=first or pass ask_default_on_timeout='first' "
                "to enable headless auto-selection."
            ),
        )

    # ------------------------------------------------------------------ commit

    @staticmethod
    def _commit(
        step: PlanStep,
        options: list[AskOption],
        picked: AskOption,
        question_id: str,
        timeout: int,
        context: dict,
        blackboard: Any | None,
        session_id: str,
    ) -> None:
        # Inject into context so subsequent steps see the choice
        key = step.ask_user_context_key or "region"
        context[key] = picked.value
        context.setdefault("ask_user_history", []).append(
            {
                "step_id": step.id,
                "question_id": question_id,
                "selected_value": picked.value,
                "selected_label": picked.label,
                "options_count": len(options),
            }
        )

        # Persist to blackboard pending_actions (schema 1.2 ask_user_response)
        if blackboard is not None and session_id:
            pending = {
                "action": "ask_user_response",
                "skill": "qcloud-copilot",
                "reason": step.description or f"ask_user step {step.id} resolved",
                "question_id": question_id,
                "selected_option": picked.value,
                "selected_label": picked.label,
                "timeout_seconds": timeout,
                "responded_at": datetime.now(timezone.utc).isoformat(),
            }
            blackboard.add_pending_action(session_id, pending)


# ---------------------------------------------------------------------------
# SIGALRM-based timeout (Unix). Imported lazily so non-Unix platforms don't
# error on module import. Tests inject stdin/stdout and never reach this path.
# ---------------------------------------------------------------------------


class _AskTimeout(Exception):
    def __init__(self, seconds: int) -> None:
        super().__init__(f"timed out after {seconds}s")
        self.seconds = seconds


def _install_alarm(seconds: int) -> None:
    if signal_module is None or not hasattr(signal_module, "SIGALRM"):
        return
    # SIGALRM only works on the main thread of the main interpreter. When the
    # dispatcher wraps our execute() in a ThreadPoolExecutor worker (default
    # STEP_TIMEOUT path), calling signal.signal() raises ValueError. We catch
    # it and degrade: caller relies on stdin injection (or a small timeout in
    # another layer). Real CLI usage in process main is unaffected.
    with contextlib.suppress(ValueError):
        signal_module.signal(signal_module.SIGALRM, _on_alarm)
        signal_module.alarm(seconds)


def _cancel_alarm() -> None:
    if signal_module is None or not hasattr(signal_module, "SIGALRM"):
        return
    with contextlib.suppress(ValueError):
        signal_module.alarm(0)


def _on_alarm(signum: int, frame: Any) -> None:
    raise _AskTimeout(seconds=0)


# Lazy signal module reference (signal.signal exists on Unix; on Windows it's
# missing). Importing at top-level would break Windows tests.
try:
    import signal as signal_module  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — Windows fallback
    signal_module = None  # type: ignore[assignment]
