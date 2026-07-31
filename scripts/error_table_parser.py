#!/usr/bin/env python3
"""Parse markdown error tables in SKILL.md into ``ErrorRule`` instances.

Two table formats are supported (auto-detected by column count + header):

* **6-column standard** (Phase 1.3 target shape)::

      | Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |

* **Legacy 2-5 column** (older SKILL.md)::

      | Error Code | Max Retries | Recovery |
      | Error pattern | Retry Strategy | Recovery |

  In legacy format the Action is *inferred* from the Recovery text using
  simple keyword heuristics (``HALT``, ``Delegate``, ``Retry``, ``Fix``).
  Backoff seconds are parsed from patterns like ``"3 (2s,4s,8s)"`` or
  ``"3, exp backoff"``.

Public API:

    parse_error_table(markdown_text) -> list[ErrorRule]

L5 lesson: assertions check actual populated values (action, retries,
backoff list, delegate_to), not just key presence.
"""

from __future__ import annotations

import re

from error_escalator import Action, ErrorRule

# ---------------------------------------------------------------------------
# Table extraction (pure markdown; no external deps)
# ---------------------------------------------------------------------------

_TABLE_SEP_RE = re.compile(r"^[-:\s]+$")
_DELIMITER_DELEGATE_RE = re.compile(r"(?:delegate to|Delegated to)\s+`?([a-z0-9\-]+)`?",
                                    re.IGNORECASE)
_BACKOFF_KV_RE = re.compile(r"(\d+)\s*s?", re.IGNORECASE)
_MAX_RETRIES_RE = re.compile(r"\b(\d+)\b")
_EXPLICIT_LIST_RE = re.compile(r"\d+\s*s?(?:\s*,\s*\d+\s*s?)+")
_NUM_LIST_RE = re.compile(r"\b\d+\s*s?\b")


def _is_separator_row(cells: list[str]) -> bool:
    return all(_TABLE_SEP_RE.match(c.strip()) for c in cells if c.strip())


def _split_row(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells (drops leading/trailing |)."""
    line = line.strip()
    line = line.removeprefix("|")
    line = line.removesuffix("|")
    return [c.strip() for c in line.split("|")]


def _extract_tables(text: str) -> list[list[list[str]]]:
    """Return every markdown table in the text as list-of-rows-of-cells."""
    tables: list[list[list[str]]] = []
    rows: list[list[str]] = []
    in_table = False

    def flush() -> None:
        nonlocal rows
        if len(rows) >= 2:
            # Drop trailing separator rows
            cleaned = [r for r in rows if not _is_separator_row(r)]
            if len(cleaned) >= 2:
                tables.append(cleaned)
        rows = []

    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            rows.append(_split_row(stripped))
            in_table = True
        else:
            if in_table:
                flush()
                in_table = False
    if in_table:
        flush()
    return tables


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

_ERROR_HEADER_NAMES = (
    "error code",
    "error pattern",
    "code",
    "错误码",
    "错误模式",
)


def _detect_format(header: list[str]) -> str | None:
    """Return ``"standard"`` for 6-col tables with an Action column,
    ``"legacy"`` for 2-5 col tables whose first column is an error code,
    ``None`` for unrelated tables (e.g. ``Pre-flight check`` tables)."""
    normalized = [h.lower().strip() for h in header]
    first = normalized[0] if normalized else ""
    if first not in _ERROR_HEADER_NAMES:
        return None
    if len(normalized) >= 6 and "action" in normalized:
        return "standard"
    return "legacy"


# ---------------------------------------------------------------------------
# Standard 6-column parser
# ---------------------------------------------------------------------------

def _parse_action(raw: str) -> Action:
    raw = raw.strip().upper()
    if raw in {a.value for a in Action}:
        return Action(raw)
    # Heuristic fallback
    if "FIX" in raw:
        return Action.FIX
    if "DELEGATE" in raw:
        return Action.DELEGATE
    if "RETRY" in raw:
        return Action.RETRY
    return Action.HALT


def _parse_int(raw: str, default: int = 0) -> int:
    m = _MAX_RETRIES_RE.search(raw)
    return int(m.group(1)) if m else default


def _parse_backoff_strategy(raw: str) -> tuple[list[int], str]:
    """Parse the Backoff column. Returns ``(seconds_list, strategy)``.

    Recognised patterns:

    * ``"—"`` / ``"-"`` / ``""``        → ``([], "fixed")``
    * ``"exponential"``                  → ``([], "exponential")``
    * ``"3, exp backoff"``               → ``([], "exponential")``
    * ``"2s,4s,8s"``                     → ``([2, 4, 8], "fixed")``
    * ``"3 (2s,4s,8s)"``                 → ``([2, 4, 8], "fixed")``
    """
    raw = raw.strip()
    if not raw or raw in {"—", "-", "n/a"}:
        return ([], "fixed")
    if "exp" in raw.lower():
        return ([], "exponential")
    # Try explicit list "2s,4s,8s" or "2, 4, 8"
    nums = [int(m.group(1)) for m in _BACKOFF_KV_RE.finditer(raw)]
    if len(nums) >= 2:
        return (nums, "fixed")
    return ([], "fixed")


def _parse_delegate(raw: str) -> str | None:
    raw = raw.strip()
    if not raw or raw in {"—", "-", ""}:
        return None
    # Strip backticks
    if raw.startswith("`") and raw.endswith("`"):
        raw = raw[1:-1]
    return raw


def _strip_code(raw: str) -> str:
    """Drop backticks from error code cells (anywhere in the cell).

    Compound codes like `` `InvalidVpcId` / `InvalidSubnetId` `` end up
    with stray trailing backticks after the original ``.strip("`")``
    implementation. We strip *all* backticks here; the renderer in
    ``migrate_error_tables`` re-wraps the code in a single pair.
    """
    return raw.strip().replace("`", "").strip()


def _parse_standard_row(row: list[str]) -> ErrorRule:
    code = _strip_code(row[0])
    action = _parse_action(row[1])
    max_retries = _parse_int(row[2])
    backoff_seconds, backoff_strategy = _parse_backoff_strategy(row[3])
    delegate_to = _parse_delegate(row[4])
    recovery_hint = row[5].strip().strip("`").strip() if len(row) > 5 else ""
    return ErrorRule(
        code=code,
        action=action,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        backoff_strategy=backoff_strategy,
        delegate_to=delegate_to,
        recovery_hint=recovery_hint,
    )


# ---------------------------------------------------------------------------
# Legacy 2-5 column parser
# ---------------------------------------------------------------------------

# Legacy 3-col: Error Code | Retry/Strategy | Recovery
# Legacy 4-col: Error Code | Max Retries | Recovery | <ignored>
# Legacy 5-col: Error Code | Retry Strategy | Recovery | <ignored> | <ignored>


def _parse_legacy_action(recovery_text: str) -> tuple[Action, str | None]:
    """Infer Action + delegate_to from free-text recovery column.

    The recovery text often contains multiple clauses separated by ``;`` or
    ``.`` — e.g. ``"Retry; HALT if persists"`` or ``"HALT. Delegate to X"``.
    The *primary* action is the verb in the first clause; trailing clauses
    are conditional or hints.

    Priority (first-clause wins):

    * starts with ``"Retry"`` / ``"back off"`` → ``(RETRY, None)``
    * starts with ``"Halt"``                  → ``(HALT, delegate_to?)``
    * starts with ``"Fix"``                   → ``(FIX, None)``
    * contains ``"Delegate to <skill>"`` (no HALT/Retry in first clause)
      → ``(DELEGATE, skill)``
    * default                                   → ``(HALT, None)`` (safe)
    """
    text = recovery_text.strip()
    if not text:
        return (Action.HALT, None)
    # Split into clauses (preserve order; first clause is primary).
    clauses = [c.strip() for c in re.split(r"[;.]", text) if c.strip()]
    primary = clauses[0].lower() if clauses else ""
    delegate_match = _DELIMITER_DELEGATE_RE.search(text)
    # Check the first clause for the primary verb.
    if "retry" in primary or "back off" in primary or "backoff" in primary:
        return (Action.RETRY, None)
    if "halt" in primary:
        return (Action.HALT, delegate_match.group(1) if delegate_match else None)
    if "fix" in primary:
        return (Action.FIX, None)
    # No primary verb in first clause; fall back to body-level hints.
    if delegate_match and "delegate" in text.lower():
        return (Action.DELEGATE, delegate_match.group(1))
    return (Action.HALT, None)


def _refine_action_by_retry(
    action: Action,
    *,
    max_retries: int,
    backoff_seconds: list[int],
    backoff_strategy: str,
) -> Action:
    """Upgrade HALT → RETRY when an explicit retry schedule exists.

    Legacy tables often encode retries/backoff in the *Retry* column while
    leaving the *Recovery* column as plain prose (e.g. ``"Add delay between
    queries"``). Without this post-process the dispatcher would HALT even
    though the operator clearly intended ``RequestLimitExceeded`` to retry
    3 times with exponential backoff. The rule: if ``max_retries > 0`` AND
    a backoff schedule is specified (either explicit seconds list or
    ``exponential`` strategy), treat as RETRY.
    """
    if action != Action.HALT:
        return action
    if max_retries <= 0:
        return action
    has_schedule = bool(backoff_seconds) or backoff_strategy == "exponential"
    return Action.RETRY if has_schedule else action


def _parse_legacy_retry(retry_text: str) -> tuple[int, list[int], str]:
    """Parse the Retry column. Returns (max_retries, backoff_seconds, strategy)."""
    raw = retry_text.strip()
    if "exp" in raw.lower():
        return (_parse_int(raw, 3), [], "exponential")
    # Match "3 (2s,4s,8s)" pattern
    m_list = _EXPLICIT_LIST_RE.search(raw)
    if m_list:
        nums = [int(n.group(0).rstrip("sS")) for n in _BACKOFF_KV_RE.finditer(m_list.group(0))]
        return (_parse_int(raw, 3), nums, "fixed")
    # Plain integer or just "0"
    return (_parse_int(raw, 0), [], "fixed")


def _parse_legacy_row(row: list[str], header: list[str] | None = None) -> ErrorRule | None:
    """Parse one legacy-format row.

    Column shape detection (per the docstring intent — Code | Retry | Recovery
    followed by ignored columns):

    * 2 cells: ``Code | <single combined>`` (the trailing cell encodes
      both retry strategy and recovery prose, e.g. ``"Retry (3x, exp backoff)"``).
    * 3 cells: ``Code | Retry | Recovery``
    * 4 cells: ``Code | Retry | Recovery | <ignored>``
    * 5 cells: ``Code | Retry | Recovery | <ignored> | <ignored>``

    A handful of skills (notably ``qcloud-tcop-ops``) use a *5-column layout*
    where the columns are actually ``Code | MaxRetries | Backoff | AgentAction
    | UXFeedback`` — the rightmost pair carries meaningful Action verbs, not
    extra metadata to ignore. We detect this layout by header keyword match
    (``"backoff"`` + ``"action"``) and switch to column-aware parsing.

    NB: Phase 1.3.3 changed this from reading ``row[-2]/row[-1]`` (which
    silently swapped Retry↔Recovery for the rightmost-pair layout) to honour
    the documented ``Code | Retry | Recovery | …`` layout for the common case,
    with header-aware fallback for the special 5-col shape.
    """
    if len(row) < 2:
        return None
    code = _strip_code(row[0])
    if not code:
        return None

    # Special case: 5-col tables whose header has "Backoff" + "Agent Action".
    detected_5col = (
        len(row) == 5
        and header is not None
        and len(header) == 5
        and "backoff" in header[2].lower()
        and any(k in header[3].lower() for k in ("action", "agent"))
        and any(k in header[4].lower() for k in ("hint", "feedback", "ux", "recovery"))
    )
    if detected_5col:
        # row[1] = retries, row[2] = backoff, row[3] = agent action, row[4] = hint
        max_retries, backoff_seconds, backoff_strategy = _parse_legacy_retry(row[1])
        # Backoff: also try to pull an explicit list from the dedicated column.
        _, extra_seconds, extra_strategy = _parse_legacy_retry(row[2])
        if not backoff_seconds and extra_seconds:
            backoff_seconds = extra_seconds
        if backoff_strategy == "fixed" and extra_strategy == "exponential":
            backoff_strategy = "exponential"
        action, delegate_to = _parse_legacy_action(row[3])
        action = _refine_action_by_retry(
            action,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            backoff_strategy=backoff_strategy,
        )
        # Recovery hint: prefer the Agent Action prose + UXFeedback appended;
        # the dispatcher only reads this as user-facing guidance.
        recovery_hint = (
            f"{row[3].strip()}; {row[4].strip()}"
            if row[4].strip() not in {"", "—", "-"}
            else row[3].strip()
        )
        return ErrorRule(
            code=code,
            action=action,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            backoff_strategy=backoff_strategy,
            delegate_to=delegate_to,
            recovery_hint=recovery_hint,
        )

    # Standard legacy layout (2-4 cells): row[1]=Retry, row[2]=Recovery.
    if len(row) == 2:
        retry_text = row[1]
        recovery_text = row[1]
    else:
        retry_text = row[1]
        recovery_text = row[2]
    max_retries, backoff_seconds, backoff_strategy = _parse_legacy_retry(retry_text)
    action, delegate_to = _parse_legacy_action(recovery_text)
    # If the operator specified a retry schedule (retries > 0 + backoff),
    # promote HALT → RETRY so the dispatcher actually honours the schedule.
    action = _refine_action_by_retry(
        action,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        backoff_strategy=backoff_strategy,
    )
    recovery_hint = recovery_text.strip()
    return ErrorRule(
        code=code,
        action=action,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        backoff_strategy=backoff_strategy,
        delegate_to=delegate_to,
        recovery_hint=recovery_hint,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_error_table(markdown_text: str) -> list[ErrorRule]:
    """Parse every markdown error table in ``markdown_text`` into ErrorRules.

    Returns an empty list when no tables are present.
    """
    rules: list[ErrorRule] = []
    for table in _extract_tables(markdown_text):
        if not table:
            continue
        header = table[0]
        fmt = _detect_format(header)
        if fmt is None:
            continue
        for row in table[1:]:
            if not row or not row[0].strip():
                continue
            if fmt == "standard":
                rules.append(_parse_standard_row(row))
            else:
                r = _parse_legacy_row(row, header=header)
                if r is not None:
                    rules.append(r)
    return rules


__all__ = ["parse_error_table"]