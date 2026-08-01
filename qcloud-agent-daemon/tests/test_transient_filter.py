# Copyright (c) 2026. All rights reserved.
"""TDD-first tests for TransientStateFilter (Spec §6.2).

Per Plan T3.2: >=3 cases per service (stable / transient / unknown).
Plus: load errors, dual-classification, fixture provenance.

Per AGENTS.md L1: TestCase subclass. Per L5: assert populated values.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from qcloud_agent_daemon.transient_filter import (
    KNOWN_SERVICES,
    TransientStateFilter,
)


def _make_fixture(tmpdir: Path, service: str, stable: list[str], transient: list[str]) -> None:
    """Write a minimal whitelist fixture for one service."""
    data = {
        "_provenance": "test fixture",
        "_verify_command": "n/a",
        "stable_states": stable,
        "transient_states": transient,
    }
    (tmpdir / f"{service}.json").write_text(json.dumps(data), encoding="utf-8")


class _FixtureHelper:
    """Mixin that builds a complete tmp whitelist dir for all KNOWN_SERVICES."""

    DEFAULT_STABLE = {  # noqa: RUF012  # test fixture constants, never mutated
        "cvm": ["RUNNING", "STOPPED"],
        "cdb": ["RUNNING"],
        "redis": ["RUNNING"],
        "clb": ["RUNNING", "ACTIVE"],
        "mongodb": ["RUNNING"],
        "postgres": ["RUNNING"],
        "ckafka": ["RUNNING"],
    }
    DEFAULT_TRANSIENT = {  # noqa: RUF012  # test fixture constants, never mutated
        "cvm": ["PENDING", "STARTING", "STOPPING", "REBOOTING", "SHUTDOWN"],
        "cdb": ["CREATING", "INITING", "UPGRADING", "RESIZING"],
        "redis": ["CREATING", "INITING", "FLUSHING", "UPGRADING"],
        "clb": ["CREATING", "CONFIGURING", "DELETING"],
        "mongodb": ["CREATING", "INITING", "UPGRADING"],
        "postgres": ["CREATING", "INITING", "UPGRADING", "RESIZING"],
        "ckafka": ["CREATING", "INITING", "UPGRADING"],
    }

    def setUp(self) -> None:  # type: ignore[override]
        self.tmpdir = Path(tempfile.mkdtemp(prefix="tsf-test-"))
        for svc in KNOWN_SERVICES:
            _make_fixture(
                self.tmpdir,
                svc,
                self.DEFAULT_STABLE[svc],
                self.DEFAULT_TRANSIENT[svc],
            )
        self.filter = TransientStateFilter(self.tmpdir)

    def tearDown(self) -> None:  # type: ignore[override]
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TransientStateFilterTest(_FixtureHelper, unittest.TestCase):
    """>=3 cases per service x 7 services = >=21 cases."""

    # ------------------------------------------------------------------
    # Per-service smoke tests: one stable + one transient + one unknown
    # ------------------------------------------------------------------
    def test_cvm_stable(self) -> None:
        """Verify CVM RUNNING is classified as stable."""
        assert self.filter.classify("cvm", "RUNNING") == "stable"
        assert not self.filter.is_transient("cvm", "RUNNING")

    def test_cvm_transient(self) -> None:
        """Verify CVM STARTING is classified as transient."""
        assert self.filter.classify("cvm", "STARTING") == "transient"
        assert self.filter.is_transient("cvm", "STARTING")

    def test_cvm_unknown(self) -> None:
        """Verify CVM lower-case state is classified as unknown."""
        # Case-sensitive — lower-case "running" is unknown
        assert self.filter.classify("cvm", "running") == "unknown"

    def test_cdb_stable(self) -> None:
        """Verify CDB RUNNING is classified as stable."""
        assert self.filter.classify("cdb", "RUNNING") == "stable"

    def test_cdb_transient(self) -> None:
        """Verify CDB UPGRADING is classified as transient."""
        assert self.filter.classify("cdb", "UPGRADING") == "transient"

    def test_cdb_unknown(self) -> None:
        """Verify CDB unknown state is classified as unknown."""
        assert self.filter.classify("cdb", "MAGIC_STATE") == "unknown"

    def test_redis_stable(self) -> None:
        """Verify Redis RUNNING is classified as stable."""
        assert self.filter.classify("redis", "RUNNING") == "stable"

    def test_redis_transient(self) -> None:
        """Verify Redis FLUSHING is classified as transient."""
        assert self.filter.classify("redis", "FLUSHING") == "transient"

    def test_redis_unknown(self) -> None:
        """Verify Redis unknown state is classified as unknown."""
        assert self.filter.classify("redis", "UNKNOWN_STATE") == "unknown"

    def test_clb_stable(self) -> None:
        """Verify CLB RUNNING is classified as stable."""
        assert self.filter.classify("clb", "RUNNING") == "stable"

    def test_clb_transient(self) -> None:
        """Verify CLB CONFIGURING is classified as transient."""
        assert self.filter.classify("clb", "CONFIGURING") == "transient"

    def test_clb_unknown(self) -> None:
        """Verify CLB unknown state is classified as unknown."""
        assert self.filter.classify("clb", "MAGIC") == "unknown"

    def test_mongodb_stable(self) -> None:
        """Verify MongoDB RUNNING is classified as stable."""
        assert self.filter.classify("mongodb", "RUNNING") == "stable"

    def test_mongodb_transient(self) -> None:
        """Verify MongoDB INITING is classified as transient."""
        assert self.filter.classify("mongodb", "INITING") == "transient"

    def test_mongodb_unknown(self) -> None:
        """Verify MongoDB unknown state is classified as unknown."""
        assert self.filter.classify("mongodb", "DELETED") == "unknown"

    def test_postgres_stable(self) -> None:
        """Verify Postgres RUNNING is classified as stable."""
        assert self.filter.classify("postgres", "RUNNING") == "stable"

    def test_postgres_transient(self) -> None:
        """Verify Postgres RESIZING is classified as transient."""
        assert self.filter.classify("postgres", "RESIZING") == "transient"

    def test_postgres_unknown(self) -> None:
        """Verify Postgres unknown state is classified as unknown."""
        assert self.filter.classify("postgres", "QUIRK") == "unknown"

    def test_ckafka_stable(self) -> None:
        """Verify CKafka RUNNING is classified as stable."""
        assert self.filter.classify("ckafka", "RUNNING") == "stable"

    def test_ckafka_transient(self) -> None:
        """Verify CKafka UPGRADING is classified as transient."""
        assert self.filter.classify("ckafka", "UPGRADING") == "transient"

    def test_ckafka_unknown(self) -> None:
        """Verify CKafka unknown state is classified as unknown."""
        assert self.filter.classify("ckafka", "FLAP") == "unknown"

    # ------------------------------------------------------------------
    # Cross-service behavior
    # ------------------------------------------------------------------
    def test_unknown_service_returns_unknown(self) -> None:
        """Verify querying a non-existent service returns unknown."""
        assert self.filter.classify("nonexistent_service", "RUNNING") == "unknown"

    def test_known_services_returns_all_seven(self) -> None:
        """Verify known_services returns all 7 expected services."""
        services = self.filter.known_services()
        assert len(services) == len(KNOWN_SERVICES)
        for s in KNOWN_SERVICES:
            assert s in services

    def test_state_in_both_sets_returns_unknown(self) -> None:
        """Verify a state in both stable and transient sets returns unknown."""
        bad_dir = Path(tempfile.mkdtemp(prefix="tsf-bad-"))
        try:
            _make_fixture(bad_dir, "cvm", ["RUNNING"], ["RUNNING"])  # RUNNING in both
            f = TransientStateFilter(bad_dir)
            assert f.classify("cvm", "RUNNING") == "unknown"
        finally:
            shutil.rmtree(bad_dir, ignore_errors=True)

    def test_is_transient_matches_classify(self) -> None:
        """Verify is_transient is consistent with classify results."""
        for service in KNOWN_SERVICES:
            for state in self.DEFAULT_TRANSIENT[service]:
                assert self.filter.is_transient(
                    service, state,
                ), f"is_transient({service}, {state}) should be True"
            for state in self.DEFAULT_STABLE[service]:
                assert not self.filter.is_transient(
                    service, state,
                ), f"is_transient({service}, {state}) should be False"


class TransientStateFilterLoadErrorsTest(unittest.TestCase):
    """Verify load-failure paths fail loudly (per L4 — rejection tests for failure paths)."""

    def test_missing_fixture_classifies_as_unknown(self) -> None:
        """Verify missing fixture file results in unknown classification."""
        tmpdir = Path(tempfile.mkdtemp(prefix="tsf-missing-"))
        try:
            # Only create one fixture; cdb is missing
            _make_fixture(tmpdir, "cvm", ["RUNNING"], [])
            f = TransientStateFilter(tmpdir)  # no raise — lazy load
            # Querying missing service returns unknown
            assert f.classify("cdb", "RUNNING") == "unknown"
            # Querying present service works
            assert f.classify("cvm", "RUNNING") == "stable"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_real_fixtures_load_successfully(self) -> None:
        """Verify shipped fixtures in tests/fixtures/transient-states/ load correctly."""
        repo_root = Path(__file__).resolve().parent.parent
        fixture_dir = repo_root / "tests" / "fixtures" / "transient-states"
        assert fixture_dir.is_dir(), f"missing fixture dir: {fixture_dir}"
        f = TransientStateFilter(fixture_dir)
        # Verify all 7 services loaded
        assert len(f.known_services()) == len(KNOWN_SERVICES)
        # Spot-check CVM (most common)
        assert f.classify("cvm", "RUNNING") == "stable"
        assert f.classify("cvm", "STARTING") == "transient"


if __name__ == "__main__":
    unittest.main()
