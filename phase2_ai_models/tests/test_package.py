# Copyright (c) 2026. All rights reserved.
"""Tests for package-level constants."""

from __future__ import annotations

from phase2_ai_models import __version__


class TestPackage:
    """Package metadata."""

    def test_version(self) -> None:
        """Verify package version is 0.1.0."""
        assert __version__ == "0.1.0"  # noqa: S101
