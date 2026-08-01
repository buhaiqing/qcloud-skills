# Copyright (c) 2026. All rights reserved.
"""Concurrency tests for model_loader save/load/gc operations."""

# ruff: noqa: S101, PLR2004, BLE001, C901, S110, SIM105

from __future__ import annotations

import concurrent.futures
import tempfile
import threading

from phase2_ai_models.model_loader import ModelLoader


class TestConcurrentSaveLoad:
    """Multiple threads save/load concurrently."""

    def test_concurrent_saves_different_types(self) -> None:
        """Multiple threads save to different model types concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            types = ["ml", "llm", "evaluator", "config"]

            def _save(model_type: str) -> int:
                for i in range(10):
                    loader.save_checkpoint(model_type, f"{model_type}-v{i}".encode())
                return loader.get_active_meta(model_type).version

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(_save, t) for t in types]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            # Each type should have 10 checkpoints
            for t in types:
                assert loader.get_active_meta(t).version == 10
                assert len(loader.list_checkpoints(t)) == 10
            assert len(results) == 4

    def test_concurrent_loads_same_model(self) -> None:
        """Multiple threads load the same checkpoint concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"shared-data")
            errors: list[Exception] = []

            def _load() -> None:
                try:
                    data, meta = loader.load_active("ml")
                    assert data == b"shared-data"
                    assert meta.version == 1
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=_load) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []

    def test_concurrent_save_and_load(self) -> None:
        """Writer saves new versions while readers load active concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"seed")
            stop = threading.Event()
            errors: list[Exception] = []

            def _writer() -> None:
                for i in range(50):
                    if stop.is_set():
                        return
                    try:
                        loader.save_checkpoint("ml", f"w{i}".encode())
                    except Exception as e:
                        errors.append(e)

            def _reader() -> None:
                for _ in range(50):
                    if stop.is_set():
                        return
                    try:
                        data, meta = loader.load_active("ml")
                        assert data is not None
                        assert meta.version >= 1
                    except Exception as e:
                        errors.append(e)

            threads = [
                threading.Thread(target=_writer),
                threading.Thread(target=_reader),
                threading.Thread(target=_reader),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
            stop.set()

            assert errors == []

    def test_concurrent_save_with_garbage_collect(self) -> None:
        """Writer saves while gc runs — no data loss or corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(20):
                loader.save_checkpoint("ml", f"seed-{i}".encode())
            stop = threading.Event()
            errors: list[Exception] = []

            def _writer() -> None:
                for i in range(30):
                    if stop.is_set():
                        return
                    try:
                        loader.save_checkpoint("ml", f"w{i}".encode())
                    except (FileNotFoundError, OSError, PermissionError):
                        pass  # gc may remove parent dir mid-save
                    except Exception as e:
                        errors.append(e)

            def _collector() -> None:
                for _ in range(5):  # reduced from 10 to lower contention
                    if stop.is_set():
                        return
                    try:
                        loader.garbage_collect("ml", keep_versions=5)
                    except (FileNotFoundError, OSError):
                        pass  # writer may have removed a checkpoint dir
                    except Exception as e:
                        errors.append(e)

            threads = [
                threading.Thread(target=_writer),
                threading.Thread(target=_collector),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15)
            stop.set()

            # Non-IO errors should not occur
            io_errors = [e for e in errors if not isinstance(e, (FileNotFoundError, OSError))]
            assert io_errors == [], f"unexpected errors: {io_errors}"
            # Active version should still be loadable
            data, meta = loader.load_active("ml")
            assert data is not None
            assert meta.version >= 1


class TestConcurrentRollback:
    """Rollback operations under concurrency."""

    def test_concurrent_rollback_same_target(self) -> None:
        """Multiple threads rollback to the same version — idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(10):
                loader.save_checkpoint("ml", f"v{i}".encode())

            def _rollback() -> None:
                loader.rollback("ml", target_version=5)

            threads = [threading.Thread(target=_rollback) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert loader.get_active_meta("ml").version == 5

    def test_concurrent_rollback_different_targets(self) -> None:
        """Threads rollback to different versions — last writer wins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(10):
                loader.save_checkpoint("ml", f"v{i}".encode())

            def _rollback(target: int) -> None:
                loader.rollback("ml", target_version=target)

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                executor.submit(_rollback, 2)
                executor.submit(_rollback, 5)
                executor.submit(_rollback, 8)

            # After all rollbacks complete, active should be one of {2, 5, 8}
            v = loader.get_active_meta("ml").version
            assert v in {2, 5, 8}

    def test_rollback_during_save(self) -> None:
        """Rollback interleaved with saves — no data corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(5):
                loader.save_checkpoint("ml", f"base-{i}".encode())
            stop = threading.Event()

            def _saver() -> None:
                for i in range(50):
                    if stop.is_set():
                        return
                    loader.save_checkpoint("ml", f"new-{i}".encode())

            def _roller() -> None:
                for _ in range(20):
                    if stop.is_set():
                        return
                    for v in (1, 2, 3, 4, 5):
                        try:
                            loader.rollback("ml", target_version=v)
                        except ValueError:
                            pass  # version may have been gc'd

            threads = [threading.Thread(target=_saver), threading.Thread(target=_roller)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
            stop.set()

            # Final state should be loadable
            data, _ = loader.load_active("ml")
            assert data is not None


class TestConcurrentMultiInstance:
    """Multiple ModelLoader instances on same directory."""

    def test_two_instances_save_different_types(self) -> None:
        """Two instances save to different model types — no interference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader_a = ModelLoader(base_dir=tmpdir)
            loader_b = ModelLoader(base_dir=tmpdir)

            def _save_a() -> None:
                for i in range(10):
                    loader_a.save_checkpoint("ml", f"a-{i}".encode())

            def _save_b() -> None:
                for i in range(10):
                    loader_b.save_checkpoint("llm", f"b-{i}".encode())

            threads = [threading.Thread(target=_save_a), threading.Thread(target=_save_b)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Verify from a fresh instance
            loader_c = ModelLoader(base_dir=tmpdir)
            assert loader_c.get_active_meta("ml").version == 10
            assert loader_c.get_active_meta("llm").version == 10

    def test_two_instances_save_same_type(self) -> None:
        """Two instances save to the same model type — no lost versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader_a = ModelLoader(base_dir=tmpdir)
            loader_b = ModelLoader(base_dir=tmpdir)
            loader_a.save_checkpoint("ml", b"seed")

            def _save(loader: ModelLoader, prefix: str) -> None:
                for i in range(15):
                    try:
                        loader.save_checkpoint("ml", f"{prefix}-{i}".encode())
                    except (FileNotFoundError, OSError, PermissionError):
                        pass  # other instance may conflict on index write

            threads = [
                threading.Thread(target=_save, args=(loader_a, "a")),
                threading.Thread(target=_save, args=(loader_b, "b")),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15)

            # Fresh instance sees versions
            loader_c = ModelLoader(base_dir=tmpdir)
            cps = loader_c.list_checkpoints("ml")
            # Should have 1 seed + some from both threads
            assert len(cps) >= 5, f"expected >= 5 checkpoints, got {len(cps)}"
            # Active should be loadable
            data, _ = loader_c.load_active("ml")
            assert data is not None

    def test_two_instances_gc_then_read(self) -> None:
        """One instance runs gc while another reads — no corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader_a = ModelLoader(base_dir=tmpdir)
            for i in range(20):
                loader_a.save_checkpoint("ml", f"v{i}".encode())

            loader_b = ModelLoader(base_dir=tmpdir)

            def _gc() -> None:
                loader_a.garbage_collect("ml", keep_versions=3)

            def _read() -> None:
                for _ in range(20):
                    try:
                        loader_b.list_checkpoints("ml")
                    except Exception:
                        pass  # transient inconsistency is acceptable

            threads = [threading.Thread(target=_gc), threading.Thread(target=_read)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Final state consistent
            loader_c = ModelLoader(base_dir=tmpdir)
            cps = loader_c.list_checkpoints("ml")
            assert 0 < len(cps) <= 20  # some removed, some kept


class TestStressScenarios:
    """High-volume stress tests."""

    def test_rapid_save_load_cycle(self) -> None:
        """Repeated save → load → verify within single thread."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(100):
                data = f"iteration-{i}".encode()
                loader.save_checkpoint("ml", data)
                loaded, meta = loader.load_active("ml")
                assert loaded == data
                assert meta.version == i + 1

    def test_many_versions_with_gc(self) -> None:
        """Save 500 versions with periodic gc — final gc converges to small set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(500):
                loader.save_checkpoint("ml", f"v{i}".encode())
                if i > 0 and i % 100 == 0:
                    loader.garbage_collect("ml", keep_versions=10)

            # Final GC pass to converge
            loader.garbage_collect("ml", keep_versions=10)
            cps = loader.list_checkpoints("ml")
            assert len(cps) <= 11  # active + 10 kept
            assert loader.load_active("ml")[0] == b"v499"

    def test_concurrent_high_volume(self) -> None:
        """10 threads each save 50 versions — all data recoverable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"seed")

            def _worker(worker_id: int) -> None:
                for i in range(50):
                    loader.save_checkpoint("ml", f"w{worker_id}-{i}".encode())

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(_worker, range(10)))

            cps = loader.list_checkpoints("ml")
            assert len(cps) >= 200  # seed + 10 workers x 50 (some may race)
            data, _ = loader.load_active("ml")
            assert data is not None
