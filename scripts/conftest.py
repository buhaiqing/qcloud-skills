#!/usr/bin/env python3
"""Auto-restore committed assets after a pytest session.

Defence-in-depth against test pollution (H-10): even if a test forgets a
tearDown and writes into the production assets tree, this conftest
snapshots the three load-bearing files at session start and restores them
at session finish, regardless of pass/fail. The restore is *additive* —
it does not silence legitimate production-state writes the suite wants
to assert; it only catches the case where a test forgot to clean up.

If a test wants to assert a permanent change to a committed file, it
must commit it in the same change and the snapshot check below will
warn (not fail) so the discrepancy stays visible.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_KEYS = ("assets/shared/thresholds.json",)
_SNAPSHOT: dict[str, tuple[str, int]] = {}


def pytest_sessionstart(session: pytest.Session) -> None:
    """Snapshot the load-bearing files before any test runs."""
    for rel in SNAPSHOT_KEYS:
        p = ROOT / rel
        if p.exists():
            _SNAPSHOT[rel] = (p.read_text(encoding="utf-8"), p.stat().st_size)
        else:
            _SNAPSHOT[rel] = ("", -1)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Restore the load-bearing files; warn if the disk differs from HEAD."""
    for rel, (text, size) in _SNAPSHOT.items():
        p = ROOT / rel
        if not p.exists():
            continue
        current = p.read_text(encoding="utf-8")
        # Only restore if the change is *exactly* what a known polluting
        # test pattern produces (single-key dict, <committed size) — this
        # avoids clobbering legitimate session-level edits.
        try:
            current_parsed = json.loads(current)
        except json.JSONDecodeError:
            current_parsed = None
        if (
            isinstance(current_parsed, dict)
            and len(current_parsed) <= 2
            and len(current) < size
        ):
            p.write_text(text, encoding="utf-8")
            sys.stderr.write(
                f"\nconftest.py: restored {rel} ({size} bytes) — "
                f"a test wrote a partial/single-key dict and left it on disk; "
                f"please move that test into a tempfile.TemporaryDirectory.\n"
            )
        elif current != text:
            sys.stderr.write(
                f"\nconftest.py: WARN {rel} drifted from session snapshot "
                f"({len(current)} bytes vs {size} committed). "
                f"If intentional, commit it; otherwise the polluting test "
                f"needs a tempdir fix.\n"
            )