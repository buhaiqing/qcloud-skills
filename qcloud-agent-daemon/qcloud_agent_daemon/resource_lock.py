# Copyright (c) 2026. All rights reserved.
"""ResourceLockManager — per-resource advisory locks via fcntl.flock.

Per ADR-0002 D5 + Spec §5. Lock key format: `{service}:{resource_id}`.
Lock files live under `lock_dir` (default `.runtime/locks/`).

Reuses fcntl idioms from `qcloud-copilot/copilot/blackboard.py` (`_session_lock`).

Critical invariant: the LockHandle MUST keep its file handle alive for the
lifetime of the lock. Returning without retaining the fd would let Python's
GC close the file, releasing the fcntl lock immediately. This is the
exact bug T2 caught (test_exclusive_blocks_shared).
"""
from __future__ import annotations

import fcntl
import time
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator

LockMode = Literal["READ", "WRITE"]


@dataclass
class LockHandle:
    """Opaque handle returned by try_acquire; pass to release().

    Holds an open file descriptor to keep the fcntl lock alive. Do not
    store this in a way that drops it prematurely.
    """

    resource_key: str
    mode: LockMode
    path: Path
    _fd: IO[str] | None = None  # file handle; keeping it open preserves the lock

    def release(self) -> None:
        """Release the lock by closing the underlying fd."""
        if self._fd is not None:
            with suppress(ValueError, OSError):
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            with suppress(ValueError, OSError):
                self._fd.close()
            self._fd = None


class ResourceLockManager:
    """Manages per-resource fcntl.flock advisory locks.

    Crash-safe: fcntl releases lock when process dies. The file handle
    is closed automatically by the OS.
    """

    def __init__(self, lock_dir: Path | str = ".runtime/locks") -> None:
        """Initialize with lock directory, creating it if needed."""
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, resource_key: str) -> Path:
        safe = resource_key.replace("/", "_").replace(":", "__")
        return self.lock_dir / f"{safe}.lock"

    def try_acquire(
        self,
        resource_key: str,
        mode: LockMode = "READ",
        timeout_s: float = 0.0,
    ) -> LockHandle | None:
        """Try to acquire lock; return handle or None.

        Non-blocking by default (timeout_s=0). For blocking, set timeout_s > 0;
        short sleeps between retries.
        """
        path = self._lock_path(resource_key)
        path.touch(exist_ok=True)
        fcntl_flag = fcntl.LOCK_EX if mode == "WRITE" else fcntl.LOCK_SH
        deadline = time.monotonic() + max(0.0, timeout_s)
        while True:
            fh = path.open("r+")
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_NB | fcntl_flag)
            except BlockingIOError:
                fh.close()
                if time.monotonic() >= deadline:
                    return None
                time.sleep(min(0.05, max(0.001, deadline - time.monotonic())))
                continue
            return LockHandle(resource_key=resource_key, mode=mode, path=path, _fd=fh)

    def release(self, handle: LockHandle | None) -> None:
        """Release a previously acquired lock. Idempotent (safe with None)."""
        if handle is None:
            return
        handle.release()

    @contextmanager
    def with_read(self, resource_key: str) -> Iterator[LockHandle | None]:
        """Context manager that acquires a read lock for the given resource."""
        handle = self.try_acquire(resource_key, mode="READ")
        try:
            yield handle
        finally:
            self.release(handle)

    @contextmanager
    def with_write(self, resource_key: str) -> Iterator[LockHandle | None]:
        """Context manager that acquires a write lock for the given resource."""
        handle = self.try_acquire(resource_key, mode="WRITE")
        try:
            yield handle
        finally:
            self.release(handle)


__all__ = ["LockHandle", "LockMode", "ResourceLockManager"]
