# Copyright (c) 2026. All rights reserved.
"""TDD-first tests for ResourceLockManager (Spec §5).

Six cases per Plan T2.1:
  1. acquire/release round-trip
  2. exclusive blocks shared
  3. shared allows multiple holders
  4. non-blocking returns None
  5. crash recovery (kill -9 mid-hold)
  6. cross-process via subprocess

Per AGENTS.md L1: bare def test_*() functions are NOT discovered by unittest;
we use TestCase subclass. Per L5: assert populated values, not just presence.
"""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from qcloud_agent_daemon.resource_lock import (
    ResourceLockManager,
)


class ResourceLockManagerTest(unittest.TestCase):
    """Six required cases per Plan T2.1."""

    def setUp(self) -> None:
        """Create temporary lock directory and manager instance."""
        self.tmpdir = tempfile.mkdtemp(prefix="rlm-test-")
        self.mgr = ResourceLockManager(lock_dir=self.tmpdir)

    def tearDown(self) -> None:
        """Clean up lock files and temporary directory."""
        for p in Path(self.tmpdir).glob("*.lock"):
            with contextlib.suppress(FileNotFoundError):
                p.unlink()
        Path(self.tmpdir).rmdir()

    # ------------------------------------------------------------------
    # Case 1: acquire/release round-trip
    # ------------------------------------------------------------------
    def test_acquire_release_roundtrip(self) -> None:
        """Verify try_acquire returns handle and release is idempotent."""
        h = self.mgr.try_acquire("vm:i-abc123", mode="READ")
        assert h is not None
        assert h.resource_key == "vm:i-abc123"
        assert h.mode == "READ"
        assert h.path.exists()
        self.mgr.release(h)
        self.mgr.release(h)  # idempotent
        self.mgr.release(None)

    # ------------------------------------------------------------------
    # Case 2: exclusive blocks shared (WRITE blocks READ)
    # ------------------------------------------------------------------
    def test_exclusive_blocks_shared(self) -> None:
        """Verify WRITE holder blocks subsequent READ attempts."""
        writer = self.mgr.try_acquire("cvm:i-write", mode="WRITE")
        try:
            assert writer is not None
            reader = self.mgr.try_acquire("cvm:i-write", mode="READ")
            try:
                assert reader is None, "READ should fail while WRITE is held"
            finally:
                self.mgr.release(reader)
        finally:
            self.mgr.release(writer)

    # ------------------------------------------------------------------
    # Case 3: shared allows multiple holders
    # ------------------------------------------------------------------
    def test_shared_allows_multiple_holders(self) -> None:
        """Verify multiple READ holders can coexist."""
        h1 = self.mgr.try_acquire("redis:crs-1", mode="READ")
        h2 = self.mgr.try_acquire("redis:crs-1", mode="READ")
        h3 = self.mgr.try_acquire("redis:crs-1", mode="READ")
        try:
            assert h1 is not None
            assert h2 is not None
            assert h3 is not None
        finally:
            for h in (h1, h2, h3):
                self.mgr.release(h)

    # ------------------------------------------------------------------
    # Case 4: non-blocking returns None immediately
    # ------------------------------------------------------------------
    def test_nonblocking_returns_none(self) -> None:
        """Verify try_acquire with timeout_s=0 returns None when locked."""
        holder = self.mgr.try_acquire("clb:lb-1", mode="WRITE")
        try:
            assert holder is not None
            start = time.monotonic()
            result = self.mgr.try_acquire("clb:lb-1", mode="WRITE", timeout_s=0.0)
            elapsed = time.monotonic() - start
            assert result is None
            assert elapsed < 1.0, f"non-blocking took {elapsed:.3f}s, expected < 1s"
        finally:
            self.mgr.release(holder)

    # ------------------------------------------------------------------
    # Case 5: crash recovery — kill -9 mid-hold releases the lock
    # ------------------------------------------------------------------
    def test_crash_recovery_releases_lock(self) -> None:
        """Verify a process killed with SIGKILL releases its fcntl lock."""
        # Path setup: child must be able to import qcloud_agent_daemon
        repo_root = str(Path(__file__).resolve().parent.parent)
        script = textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {repo_root!r})
            from qcloud_agent_daemon.resource_lock import ResourceLockManager
            mgr = ResourceLockManager({self.tmpdir!r})
            h = mgr.try_acquire("mongodb:cmgo-1", mode="WRITE")
            if h is None:
                sys.exit(1)
            print("LOCKED", flush=True)
            time.sleep(60)
        """)
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        assert line == "LOCKED", "child should have acquired lock"

        blocked = self.mgr.try_acquire("mongodb:cmgo-1", mode="WRITE", timeout_s=0.1)
        try:
            assert blocked is None, "should be blocked while child holds WRITE lock"
        finally:
            self.mgr.release(blocked)

        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        time.sleep(0.2)  # let kernel release fcntl

        recovered = self.mgr.try_acquire("mongodb:cmgo-1", mode="WRITE")
        try:
            assert recovered is not None, "lock should be released after child SIGKILL"
        finally:
            self.mgr.release(recovered)

    # ------------------------------------------------------------------
    # Case 6: cross-process via subprocess
    # ------------------------------------------------------------------
    def test_cross_process_locks(self) -> None:
        """Verify two different Python processes see the same lock state."""
        repo_root = str(Path(__file__).resolve().parent.parent)
        script = textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {repo_root!r})
            from qcloud_agent_daemon.resource_lock import ResourceLockManager
            mgr = ResourceLockManager({self.tmpdir!r})
            h = mgr.try_acquire("postgres:pg-1", mode="READ")
            if h is None:
                sys.exit(1)
            print("CHILD_READY", flush=True)
            time.sleep(2.0)
        """)
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        assert line == "CHILD_READY"

        result = self.mgr.try_acquire("postgres:pg-1", mode="WRITE", timeout_s=0.1)
        try:
            assert result is None, "WRITE should be blocked by child's READ"
        finally:
            self.mgr.release(result)
        proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
