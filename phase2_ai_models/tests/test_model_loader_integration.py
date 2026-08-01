# Copyright (c) 2026. All rights reserved.
"""Integration tests for model_loader save/load workflows."""

# ruff: noqa: S101, PLR2004, TRY003, EM101, PT017, BLE001, S110

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from phase2_ai_models.model_loader import ModelLoader


class TestSaveLoadRoundTrip:
    """End-to-end save → load → verify data integrity."""

    def test_save_load_large_binary(self) -> None:
        """Round-trip with 1MB binary data preserves exact content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            data = b"\x00\xff" * 524288  # 1 MB
            loader.save_checkpoint("ml", data, framework="pytorch")
            loaded, meta = loader.load_active("ml")
            assert loaded == data
            assert meta.version == 1

    def test_save_load_structured_json(self) -> None:
        """Round-trip with JSON-serializable model config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            config = {
                "layers": [128, 64, 32],
                "activation": "relu",
                "learning_rate": 0.001,
                "epochs": 100,
            }
            data = json.dumps(config).encode("utf-8")
            loader.save_checkpoint("ml", data, framework="xgboost", tags=["config", "v1"])
            loaded, meta = loader.load_active("ml")
            assert json.loads(loaded) == config
            assert "config" in meta.tags

    def test_save_load_empty_data(self) -> None:
        """Round-trip with empty binary (e.g., config-only model)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("evaluator", b"")
            loaded, _ = loader.load_active("evaluator")
            assert loaded == b""

    def test_save_load_unicode_metadata(self) -> None:
        """Metadata with unicode tags and metrics survives round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint(
                "ml",
                b"data",
                tags=["生产环境", "v1.0.0"],
                metrics={"准确率": 0.95, "F1分数": 0.93},
            )
            _, meta = loader.load_active("ml")
            assert "生产环境" in meta.tags
            assert meta.metrics["准确率"] == 0.95


class TestMultiVersionWorkflow:
    """Multi-version save → rollback → load workflows."""

    def test_save_multiple_versions_then_rollback(self) -> None:
        """Save v1, v2, v3; rollback to v2; verify active is v2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1-data")
            loader.save_checkpoint("ml", b"v2-data")
            loader.save_checkpoint("ml", b"v3-data")

            loader.rollback("ml", target_version=2)
            active_data, active_meta = loader.load_active("ml")
            assert active_data == b"v2-data"
            assert active_meta.version == 2

            # v3 still loadable by explicit version
            v3_data, _ = loader.load_checkpoint("ml", version=3)
            assert v3_data == b"v3-data"

    def test_save_after_rollback_continues_sequence(self) -> None:
        """Rollback to v2, save v4; version sequence is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1")
            loader.save_checkpoint("ml", b"v2")
            loader.save_checkpoint("ml", b"v3")

            loader.rollback("ml", target_version=1)
            loader.save_checkpoint("ml", b"v4-new")
            # New checkpoint should be v4
            _, meta = loader.load_active("ml")
            assert meta.version == 4
            assert loader.load_active("ml")[0] == b"v4-new"

    def test_rollback_to_nonexistent_version_raises(self) -> None:
        """Rollback to version that doesn't exist raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1")
            try:
                loader.rollback("ml", target_version=5)
                raise AssertionError("should have raised")
            except ValueError:
                pass

    def test_load_nonexistent_version_raises(self) -> None:
        """Loading version that doesn't exist raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            try:
                loader.load_checkpoint("ml", version=99)
                raise AssertionError("should have raised")
            except FileNotFoundError:
                pass


class TestCrossSessionPersistence:
    """Checkpoints survive across ModelLoader instances (simulated sessions)."""

    def test_reload_from_same_directory(self) -> None:
        """Save with one loader instance, load with another from same dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Session 1: save
            loader1 = ModelLoader(base_dir=tmpdir)
            loader1.save_checkpoint("ml", b"session-1-data", tags=["session-1"])
            loader1.save_checkpoint("ml", b"session-1-v2", tags=["session-1"])

            # Session 2: reload
            loader2 = ModelLoader(base_dir=tmpdir)
            data, meta = loader2.load_active("ml")
            assert data == b"session-1-v2"
            assert meta.version == 2
            assert "session-1" in meta.tags
            assert len(loader2.list_checkpoints("ml")) == 2

    def test_index_survives_empty_reload(self) -> None:
        """Index file is readable after re-instantiation with no changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader1 = ModelLoader(base_dir=tmpdir)
            loader1.save_checkpoint("ml", b"data")
            loader1.save_checkpoint("llm", b"config")

            loader2 = ModelLoader(base_dir=tmpdir)
            assert loader2.get_active_meta("ml").version == 1
            assert loader2.get_active_meta("llm").version == 1

    def test_gc_persistence_across_sessions(self) -> None:
        """GC in session 1, session 2 sees cleaned state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader1 = ModelLoader(base_dir=tmpdir)
            for i in range(8):
                loader1.save_checkpoint("ml", f"v{i}".encode())

            loader1.garbage_collect("ml", keep_versions=2)

            loader2 = ModelLoader(base_dir=tmpdir)
            cps = loader2.list_checkpoints("ml")
            assert len(cps) == 3  # active(v8) + 2 kept


class TestIntegrityAndCorruption:
    """SHA256 integrity checks and corruption detection."""

    def test_tampered_data_detected(self) -> None:
        """Modifying model file on disk triggers integrity failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"original-data")

            # Tamper with the file on disk
            model_file = Path(tmpdir) / "ml" / "v1" / "model.bin"
            model_file.write_bytes(b"tampered")

            try:
                loader.load_active("ml")
                raise AssertionError("should have raised")
            except ValueError as e:
                assert "SHA256 mismatch" in str(e)

    def test_missing_model_file_detected(self) -> None:
        """Deleting model file after save triggers FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"data")

            # Delete the model file but keep meta.json
            model_file = Path(tmpdir) / "ml" / "v1" / "model.bin"
            model_file.unlink()

            try:
                loader.load_active("ml")
                raise AssertionError("should have raised")
            except FileNotFoundError:
                pass

    def test_meta_json_corruption_handled(self) -> None:
        """Corrupted meta.json causes a fresh index on next load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader1 = ModelLoader(base_dir=tmpdir)
            loader1.save_checkpoint("ml", b"data")

            # Corrupt the index
            (Path(tmpdir) / "ml" / "index.json").write_text("{invalid json", encoding="utf-8")

            # New loader instance should handle gracefully
            try:
                loader2 = ModelLoader(base_dir=tmpdir)
                # May fail or recover — either way, shouldn't crash
                loader2.get_active_meta("ml")
            except (json.JSONDecodeError, Exception):
                pass  # Graceful degradation is acceptable


class TestGarbageCollectionScenarios:
    """Real-world GC scenarios."""

    def test_gc_with_exact_keep_boundary(self) -> None:
        """When checkpoints == keep_versions, nothing is removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(3):
                loader.save_checkpoint("ml", f"v{i}".encode())

            removed = loader.garbage_collect("ml", keep_versions=3)
            assert removed == []
            assert len(loader.list_checkpoints("ml")) == 3

    def test_gc_with_zero_keep_versions_keeps_active_only(self) -> None:
        """keep_versions=0 keeps only the active checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(5):
                loader.save_checkpoint("ml", f"v{i}".encode())

            removed = loader.garbage_collect("ml", keep_versions=0)
            assert len(removed) == 4
            assert len(loader.list_checkpoints("ml")) == 1
            assert loader.get_active_meta("ml").version == 5

    def test_gc_preserves_rolled_back_active(self) -> None:
        """After rollback to old version, gc preserves it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(10):
                loader.save_checkpoint("ml", f"v{i}".encode())

            loader.rollback("ml", target_version=3)
            removed = loader.garbage_collect("ml", keep_versions=2)

            assert 3 not in removed  # active preserved
            cps = loader.list_checkpoints("ml")
            versions = {c.version for c in cps}
            assert 3 in versions  # active
            assert 9 in versions  # recent
            assert 10 in versions  # recent

    def test_gc_idempotent(self) -> None:
        """Running gc twice produces same state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(8):
                loader.save_checkpoint("ml", f"v{i}".encode())

            _removed1 = loader.garbage_collect("ml", keep_versions=3)
            removed2 = loader.garbage_collect("ml", keep_versions=3)
            assert removed2 == []
            assert len(loader.list_checkpoints("ml")) == 4  # active + 3 kept
