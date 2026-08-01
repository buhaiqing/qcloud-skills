# Copyright (c) 2026. All rights reserved.
"""Model loading utilities with checkpoint management.

Provides a unified interface for loading and managing AI model dependencies
used across Phase 2 modules:
  - LLM backends (OpenAI-compatible) for goal_inference
  - Condition evaluators for orchestration pattern matching
  - Optional ML model loading with versioned checkpoints

Checkpoint management supports:
  - Versioned save/load with SHA256 integrity verification
  - Metadata tracking (model type, framework version, training date)
  - Rollback to previous checkpoint versions
  - Garbage collection of stale checkpoints
"""

from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class CheckpointMeta:
    """Metadata for a single checkpoint."""

    checkpoint_id: str
    model_type: str  # "llm" | "ml" | "evaluator"
    version: int
    created_at: str  # ISO 8601
    framework: str | None = None  # "openai" | "xgboost" | "sklearn"
    framework_version: str | None = None
    sha256: str | None = None
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class CheckpointIndex:
    """Persistent index of all checkpoints for a model type."""

    model_type: str
    checkpoints: list[CheckpointMeta] = field(default_factory=list)
    active_version: int = -1
    index_version: int = 1
    max_version: int = 0  # monotonic version counter; never decreases on GC


class ModelLoader:
    """Unified model loading with checkpoint management.

    Manages a checkpoint directory with versioned saves, rollback support,
    and integrity verification.

    Directory layout:
        {base_dir}/
            {model_type}/
                v{version}/
                    model.{ext}       # serialized model file
                    meta.json         # CheckpointMeta
                index.json            # CheckpointIndex
    """

    def __init__(self, base_dir: Path | str = ".runtime/models") -> None:
        """Initialize ModelLoader with a base directory for checkpoint storage.

        Args:
            base_dir: Root directory for all model checkpoint data.

        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._indexes: dict[str, CheckpointIndex] = {}
        # Serializes index mutations + checkpoint dir writes for same-instance concurrency.
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Checkpoint save
    # ------------------------------------------------------------------

    def save_checkpoint(  # noqa: PLR0913, PLR0917
        self,
        model_type: str,
        model_data: bytes,
        framework: str | None = None,
        framework_version: str | None = None,
        tags: list[str] | None = None,
        metrics: dict[str, float] | None = None,
    ) -> CheckpointMeta:
        """Save a new checkpoint version for a model type.

        Args:
            model_type: "llm", "ml", "evaluator", etc.
            model_data: Raw model bytes to persist.
            framework: Framework name (openai, xgboost, sklearn).
            framework_version: Framework version string.
            tags: Optional tags for search/filtering.
            metrics: Optional performance metrics.

        Returns:
            CheckpointMeta for the saved checkpoint.

        """
        with self._lock:
            index = self._load_index(model_type)
            version = index.max_version + 1
            index.max_version = version
            sha256 = hashlib.sha256(model_data).hexdigest()

            checkpoint_dir = self._checkpoint_dir(model_type, version)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

            # Write model file
            ext = self._file_extension(framework)
            model_path = checkpoint_dir / f"model{ext}"
            model_path.write_bytes(model_data)

            # Write metadata
            meta = CheckpointMeta(
                checkpoint_id=f"{model_type}-v{version}",
                model_type=model_type,
                version=version,
                created_at=datetime.now(UTC).isoformat(),
                framework=framework,
                framework_version=framework_version,
                sha256=sha256,
                tags=tags or [],
                metrics=metrics or {},
            )
            (checkpoint_dir / "meta.json").write_text(
                json.dumps(self._meta_to_dict(meta), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            index.checkpoints.append(meta)
            index.active_version = version
            self._save_index(model_type, index)
            return meta

    # ------------------------------------------------------------------
    # Checkpoint load
    # ------------------------------------------------------------------

    def load_checkpoint(
        self, model_type: str, version: int | None = None,
    ) -> tuple[bytes, CheckpointMeta]:
        """Load a checkpoint.

        Args:
            model_type: Model type to load.
            version: Specific version (None = active version).

        Returns:
            (model_data_bytes, CheckpointMeta).

        Raises:
            FileNotFoundError: If checkpoint does not exist.
            ValueError: If SHA256 integrity check fails.

        """
        with self._lock:
            index = self._load_index(model_type)
            v = version if version is not None else index.active_version
            meta = next((m for m in index.checkpoints if m.version == v), None)
            if meta is None:
                raise FileNotFoundError(f"No checkpoint v{v} for {model_type}")  # noqa: TRY003, EM102
            checkpoint_dir = self._checkpoint_dir(model_type, v)
            ext = self._file_extension(meta.framework)
            model_path = checkpoint_dir / f"model{ext}"
            if not model_path.is_file():
                raise FileNotFoundError(f"Model file missing: {model_path}")  # noqa: TRY003, EM102

            data = model_path.read_bytes()

            # Integrity check
            if meta.sha256:
                actual = hashlib.sha256(data).hexdigest()
                if actual != meta.sha256:
                    raise ValueError(  # noqa: TRY003
                        f"SHA256 mismatch for {model_type} v{v}: "  # noqa: EM102
                        f"expected {meta.sha256[:8]}..., got {actual[:8]}...",
                    )

            return data, meta

    def load_active(self, model_type: str) -> tuple[bytes, CheckpointMeta]:
        """Load the active (latest) checkpoint for a model type."""
        return self.load_checkpoint(model_type)

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def rollback(self, model_type: str, target_version: int) -> CheckpointMeta:
        """Rollback active version to a previous checkpoint.

        Does NOT delete newer versions; they remain available for re-activation.
        """
        with self._lock:
            index = self._load_index(model_type)
            if target_version < 1 or target_version > len(index.checkpoints):
                raise ValueError(  # noqa: TRY003
                    f"Invalid rollback target: v{target_version} (have v1-{len(index.checkpoints)})",  # noqa: EM102, E501
                )
            index.active_version = target_version
            self._save_index(model_type, index)
            return index.checkpoints[target_version - 1]

    def list_checkpoints(self, model_type: str) -> list[CheckpointMeta]:
        """List all checkpoints for a model type, newest first."""
        with self._lock:
            index = self._load_index(model_type)
            return list(reversed(index.checkpoints))

    def get_active_meta(self, model_type: str) -> CheckpointMeta | None:
        """Get metadata for the active checkpoint, or None."""
        with self._lock:
            index = self._load_index(model_type)
            if index.active_version <= 0:
                return None
            for meta in index.checkpoints:
                if meta.version == index.active_version:
                    return meta
            return None

    def garbage_collect(
        self,
        model_type: str,
        keep_versions: int = 5,
        older_than_days: int | None = None,
    ) -> list[int]:
        """Remove stale checkpoints beyond keep_versions.

        Args:
            model_type: Model type to clean up.
            keep_versions: Minimum number of recent versions to keep.
            older_than_days: Also remove checkpoints older than this many days.

        Returns:
            List of removed version numbers.

        """
        with self._lock:
            index = self._load_index(model_type)
            if len(index.checkpoints) <= keep_versions:
                return []

            removed: list[int] = []
            cutoff = time.time() - (older_than_days or 365) * 86400

            # Active version is always preserved
            active_version = index.active_version
            # Collect candidates for removal (oldest first, excluding active)
            candidates = [
                m for m in index.checkpoints
                if m.version != active_version
            ]
            # Keep the most recent keep_versions candidates, remove the rest
            if keep_versions == 0:
                to_remove = list(candidates)  # remove all non-active
            else:
                to_remove = candidates[:-keep_versions] if len(candidates) > keep_versions else []

            for meta in to_remove:
                created_ts = datetime.fromisoformat(meta.created_at).timestamp()
                if older_than_days is not None and created_ts >= cutoff:
                    continue  # too recent to remove
                checkpoint_dir = self._checkpoint_dir(model_type, meta.version)
                if checkpoint_dir.is_dir():
                    shutil.rmtree(checkpoint_dir)
                removed.append(meta.version)

            # Rebuild index (remove collected entries)
            index.checkpoints = [
                m for m in index.checkpoints if m.version not in removed
            ]
            if index.active_version in removed:
                index.active_version = index.checkpoints[-1].version if index.checkpoints else -1
            self._save_index(model_type, index)
            return removed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _checkpoint_dir(self, model_type: str, version: int) -> Path:
        """Path to a specific checkpoint version directory."""
        return self.base_dir / model_type / f"v{version}"

    @staticmethod
    def _file_extension(framework: str | None) -> str:
        """File extension for serialized model based on framework."""
        if framework == "xgboost":
            return ".json"
        if framework in ("sklearn", "pytorch"):
            return ".pkl"
        return ".bin"

    def _index_path(self, model_type: str) -> Path:
        """Path to the index file for a model type."""
        return self.base_dir / model_type / "index.json"

    def _load_index(self, model_type: str) -> CheckpointIndex:
        """Load or create the checkpoint index for a model type."""
        if model_type in self._indexes:
            return self._indexes[model_type]

        path = self._index_path(model_type)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            checkpoints = [CheckpointMeta(**m) for m in data.get("checkpoints", [])]
            max_version = data.get("max_version", 0) or max(
                (m.version for m in checkpoints), default=0,
            )
            index = CheckpointIndex(
                model_type=data["model_type"],
                checkpoints=checkpoints,
                active_version=data.get("active_version", -1),
                index_version=data.get("index_version", 1),
                max_version=max_version,
            )
        else:
            index = CheckpointIndex(model_type=model_type)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._save_index(model_type, index)

        self._indexes[model_type] = index
        return index

    def _save_index(self, model_type: str, index: CheckpointIndex) -> None:
        """Persist the checkpoint index to disk."""
        path = self._index_path(model_type)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "model_type": index.model_type,
                    "checkpoints": [self._meta_to_dict(m) for m in index.checkpoints],
                    "active_version": index.active_version,
                    "index_version": index.index_version,
                    "max_version": index.max_version,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _meta_to_dict(meta: CheckpointMeta) -> dict[str, Any]:
        """Convert CheckpointMeta to a JSON-serializable dict."""
        return {
            "checkpoint_id": meta.checkpoint_id,
            "model_type": meta.model_type,
            "version": meta.version,
            "created_at": meta.created_at,
            "framework": meta.framework,
            "framework_version": meta.framework_version,
            "sha256": meta.sha256,
            "tags": meta.tags,
            "metrics": meta.metrics,
        }


__all__ = ["CheckpointIndex", "CheckpointMeta", "ModelLoader"]
