# Copyright (c) 2026. All rights reserved.
"""Tests for model_loader module."""

# ruff: noqa: S101, PLR2004

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from phase2_ai_models.model_loader import CheckpointIndex, CheckpointMeta, ModelLoader


class TestCheckpointMeta:
    """CheckpointMeta dataclass validation."""

    def test_defaults(self) -> None:
        """Verify default values for optional CheckpointMeta fields."""
        meta = CheckpointMeta(
            checkpoint_id="test-v1",
            model_type="ml",
            version=1,
            created_at="2026-01-01T00:00:00Z",
        )
        assert meta.framework is None
        assert meta.framework_version is None
        assert meta.sha256 is None
        assert meta.tags == []
        assert meta.metrics == {}

    def test_full_meta(self) -> None:
        """Verify that all CheckpointMeta fields are populated correctly."""
        meta = CheckpointMeta(
            checkpoint_id="ml-v3",
            model_type="ml",
            version=3,
            created_at="2026-06-01T12:00:00Z",
            framework="xgboost",
            framework_version="2.0.3",
            sha256="abc123def456",
            tags=["production", "v3"],
            metrics={"accuracy": 0.95, "f1": 0.93},
        )
        assert meta.framework == "xgboost"
        assert len(meta.tags) == 2
        assert meta.metrics["accuracy"] == 0.95


class TestCheckpointIndex:
    """CheckpointIndex defaults."""

    def test_defaults(self) -> None:
        """Verify default values for CheckpointIndex."""
        idx = CheckpointIndex(model_type="ml")
        assert idx.model_type == "ml"
        assert idx.checkpoints == []
        assert idx.active_version == -1
        assert idx.index_version == 1


class TestModelLoaderSaveLoad:
    """Save and load checkpoints."""

    def test_save_and_load(self) -> None:
        """Verify checkpoint save creates correct metadata and active load restores data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            data = b"model-weights-binary-data"
            meta = loader.save_checkpoint(
                model_type="ml",
                model_data=data,
                framework="xgboost",
                framework_version="2.0.3",
                tags=["v1"],
            )
            assert meta.version == 1
            assert meta.sha256 is not None

            loaded_data, loaded_meta = loader.load_active("ml")
            assert loaded_data == data
            assert loaded_meta.version == 1

    def test_load_specific_version(self) -> None:
        """Verify loading a checkpoint by its version number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1-data", tags=["v1"])
            loader.save_checkpoint("ml", b"v2-data", tags=["v2"])
            loader.save_checkpoint("ml", b"v3-data", tags=["v3"])

            data_v2, meta_v2 = loader.load_checkpoint("ml", version=2)
            assert data_v2 == b"v2-data"
            assert meta_v2.version == 2

    def test_load_missing_version_raises(self) -> None:
        """Verify loading a nonexistent version raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"data")
            with pytest.raises(FileNotFoundError):
                loader.load_checkpoint("ml", version=99)

    def test_integrity_check_detects_corruption(self) -> None:
        """Verify SHA256 mismatch is detected when model data is tampered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"original-data")

            # Corrupt the model file on disk
            checkpoint_dir = Path(tmpdir) / "ml" / "v1"
            (checkpoint_dir / "model.bin").write_bytes(b"tampered-data")

            with pytest.raises(ValueError, match="SHA256 mismatch"):
                loader.load_active("ml")


class TestModelLoaderManagement:
    """Checkpoint management operations."""

    def test_rollback(self) -> None:
        """Verify rollback changes active version without deleting newer versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1")
            loader.save_checkpoint("ml", b"v2")
            loader.save_checkpoint("ml", b"v3")

            assert loader.get_active_meta("ml").version == 3

            loader.rollback("ml", target_version=2)
            assert loader.get_active_meta("ml").version == 2

            # v3 still exists on disk
            data_v3, _ = loader.load_checkpoint("ml", version=3)
            assert data_v3 == b"v3"

    def test_list_checkpoints_newest_first(self) -> None:
        """Verify list_checkpoints returns versions in descending order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1")
            loader.save_checkpoint("ml", b"v2")
            loader.save_checkpoint("ml", b"v3")

            cps = loader.list_checkpoints("ml")
            assert [c.version for c in cps] == [3, 2, 1]

    def test_garbage_collect_keeps_recent(self) -> None:
        """Verify gc removes old versions and keeps keep_versions recent + active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(10):
                loader.save_checkpoint("ml", f"v{i}".encode())

            removed = loader.garbage_collect("ml", keep_versions=3)
            assert len(removed) == 6
            assert 1 in removed
            assert 6 in removed
            assert 7 not in removed

            cps = loader.list_checkpoints("ml")
            assert len(cps) == 4  # 3 kept + active

    def test_garbage_collect_active_preserved(self) -> None:
        """Verify garbage_collect preserves the active (rollback) version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            for i in range(6):
                loader.save_checkpoint("ml", f"v{i}".encode())

            # Rollback to v2, then gc with keep_versions=2
            loader.rollback("ml", target_version=2)
            removed = loader.garbage_collect("ml", keep_versions=2)
            # v2 (active) + v5, v6 preserved; v1, v3, v4 removed
            assert loader.get_active_meta("ml").version == 2
            assert 2 not in removed  # active preserved
            assert 1 in removed
            assert 3 in removed
            assert 4 in removed

    def test_get_active_meta_empty(self) -> None:
        """Verify get_active_meta returns None when no checkpoints exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            assert loader.get_active_meta("ml") is None

    def test_rollback_invalid_version(self) -> None:
        """Verify rollback raises ValueError for nonexistent version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"v1")
            try:
                loader.rollback("ml", target_version=99)
                msg = "should have raised"
                raise AssertionError(msg)
            except ValueError:
                pass


class TestModelLoaderMultiType:
    """Multiple model types coexist."""

    def test_separate_indexes(self) -> None:
        """Verify that different model types have independent checkpoints and indexes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml", b"ml-data")
            loader.save_checkpoint("llm", b"llm-config")

            ml_meta = loader.get_active_meta("ml")
            llm_meta = loader.get_active_meta("llm")
            assert ml_meta is not None
            assert llm_meta is not None
            assert ml_meta.model_type == "ml"
            assert llm_meta.model_type == "llm"

    def test_different_framework_extensions(self) -> None:
        """Verify that framework determines the model file extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ModelLoader(base_dir=tmpdir)
            loader.save_checkpoint("ml-xgb", b"xgb", framework="xgboost")
            loader.save_checkpoint("ml-skl", b"skl", framework="sklearn")
            loader.save_checkpoint("ml-unk", b"unk")

            # Verify files exist with correct extensions
            assert (Path(tmpdir) / "ml-xgb" / "v1" / "model.json").is_file()
            assert (Path(tmpdir) / "ml-skl" / "v1" / "model.pkl").is_file()
            assert (Path(tmpdir) / "ml-unk" / "v1" / "model.bin").is_file()
