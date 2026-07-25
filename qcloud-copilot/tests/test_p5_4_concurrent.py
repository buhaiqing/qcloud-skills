"""P5.4 — concurrent writes / duplicate events / idempotency keys / partial
failure recovery.

  - IdempotencyKey singleton enforces single-emission per key:
    repeat-call emit_observation_with_key() with same key returns the same
    record id and does NOT append a duplicate JSONL line.

  - Concurrent emit from a ThreadPool of N writers onto ObservableSink
    does not corrupt the JSONL (one line per record, newline-terminated).

  - Partial-failure recovery: if some emissions raise, the sink keeps the
    successful ones (best-effort) and reports N successes / M failures.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


# ---------------------------------------------------------------------------
# Idempotency key
# ---------------------------------------------------------------------------


def _obs(name, trace_id="trc-p5-4"):
    from copilot.trace_records import ObservationRecord, ObservationType

    return ObservationRecord(
        id=f"obs-{name}",
        trace_id=trace_id,
        type=ObservationType.SPAN,
        name=name,
    )


def test_idempotency_key_returns_same_record_id_for_same_key():
    from copilot.idempotency import with_idempotency_key

    rec1, dup1 = with_idempotency_key(
        producer=lambda: _obs("a"),
        idempotency_key="trc-1:step-1",
    )
    rec2, dup2 = with_idempotency_key(
        producer=lambda: _obs("a"),
        idempotency_key="trc-1:step-1",
    )
    assert rec1.id == rec2.id
    assert dup1 is False
    assert dup2 is True


def test_idempotency_key_thread_safe_under_concurrent_call():
    from copilot.idempotency import with_idempotency_key

    seen = []
    lock = threading.Lock()

    def producer():
        rec, was_dup = with_idempotency_key(
            producer=lambda: _obs("a"),
            idempotency_key="trc-2:step-x",
        )
        with lock:
            seen.append(was_dup)
        return rec

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda _: producer(), range(20)))
    assert len(seen) == 20
    # Exactly one real emission; the rest duplicate.
    real = sum(1 for d in seen if not d)
    dup = sum(1 for d in seen if d)
    assert real == 1
    assert dup == 19


# ---------------------------------------------------------------------------
# Concurrent emission -> ObservableSink
# ---------------------------------------------------------------------------


def test_concurrent_emit_observations_writes_complete_jsonl(tmp_path: Path):
    from copilot.observ import ObservableSink

    sink = ObservableSink(runtime_root=tmp_path)
    N = 25

    def write(i):
        obs = _obs(f"obs-{i}", trace_id=f"trc-c{i % 5}")
        sink.emit_observation(obs)
        return obs.id

    with ThreadPoolExecutor(max_workers=8) as ex:
        ids = list(ex.map(write, range(N)))

    audit_files = list((tmp_path / "audit").rglob("observations.jsonl"))
    total_lines = 0
    all_ids = set()
    for f in audit_files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            total_lines += 1
            rec = json.loads(line)
            all_ids.add(rec["id"])
    # Every id ends up exactly once across the jsonl files.
    assert total_lines == N
    assert all_ids == set(ids)


# ---------------------------------------------------------------------------
# Partial failure recovery
# ---------------------------------------------------------------------------


def test_partial_failure_keeps_successful_emits():
    """If a producer raises, the sink must not lose the records already emitted."""
    # We test the wrapper:
    from copilot.sink_recovery import emit_with_recovery as _emit

    # Build a fake sink that raises on the 3rd emit.
    class FlakySink:
        def __init__(self):
            self.emits = []
            self.calls = 0

        def emit_observation(self, obs):
            self.calls += 1
            if self.calls == 3:
                raise OSError("simulated sink failure")
            self.emits.append(obs.id)

    sink = FlakySink()
    result = _emit(sink, [_obs("ok-1"), _obs("ok-2"), _obs("boom"), _obs("ok-4"), _obs("ok-5")])
    assert len(sink.emits) == 4  # 1, 2, 4, 5
    assert "boom" not in sink.emits
    assert result["success_count"] == 4
    assert result["failure_count"] == 1
    assert result["failures"][0]["index"] == 2
    assert result["failures"][0]["error_type"] == "OSError"


def tmp_path_for():
    from pathlib import Path as _P
    import tempfile as _t

    return _P(_t.mkdtemp())
