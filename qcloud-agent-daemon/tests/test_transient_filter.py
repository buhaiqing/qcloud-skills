"""TDD-first tests for TransientStateFilter (Spec §6.2).

Per Plan T3.2: ≥3 cases per service (stable / transient / unknown).
Plus: load errors, dual-classification, fixture provenance.

Per AGENTS.md L1: TestCase subclass. Per L5: assert populated values.
"""
from __future__ import annotations

import json
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

    DEFAULT_STABLE = {
        "cvm": ["RUNNING", "STOPPED"],
        "cdb": ["RUNNING"],
        "redis": ["RUNNING"],
        "clb": ["RUNNING", "ACTIVE"],
        "mongodb": ["RUNNING"],
        "postgres": ["RUNNING"],
        "ckafka": ["RUNNING"],
    }
    DEFAULT_TRANSIENT = {
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
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TransientStateFilterTest(_FixtureHelper, unittest.TestCase):
    """≥3 cases per service × 7 services = ≥21 cases."""

    # ------------------------------------------------------------------
    # Per-service smoke tests: one stable + one transient + one unknown
    # ------------------------------------------------------------------
    def test_cvm_stable(self) -> None:
        self.assertEqual(self.filter.classify("cvm", "RUNNING"), "stable")
        self.assertFalse(self.filter.is_transient("cvm", "RUNNING"))

    def test_cvm_transient(self) -> None:
        self.assertEqual(self.filter.classify("cvm", "STARTING"), "transient")
        self.assertTrue(self.filter.is_transient("cvm", "STARTING"))

    def test_cvm_unknown(self) -> None:
        # Case-sensitive — lower-case "running" is unknown
        self.assertEqual(self.filter.classify("cvm", "running"), "unknown")

    def test_cdb_stable(self) -> None:
        self.assertEqual(self.filter.classify("cdb", "RUNNING"), "stable")

    def test_cdb_transient(self) -> None:
        self.assertEqual(self.filter.classify("cdb", "UPGRADING"), "transient")

    def test_cdb_unknown(self) -> None:
        self.assertEqual(self.filter.classify("cdb", "MAGIC_STATE"), "unknown")

    def test_redis_stable(self) -> None:
        self.assertEqual(self.filter.classify("redis", "RUNNING"), "stable")

    def test_redis_transient(self) -> None:
        self.assertEqual(self.filter.classify("redis", "FLUSHING"), "transient")

    def test_redis_unknown(self) -> None:
        self.assertEqual(self.filter.classify("redis", "UNKNOWN_STATE"), "unknown")

    def test_clb_stable(self) -> None:
        self.assertEqual(self.filter.classify("clb", "RUNNING"), "stable")

    def test_clb_transient(self) -> None:
        self.assertEqual(self.filter.classify("clb", "CONFIGURING"), "transient")

    def test_clb_unknown(self) -> None:
        self.assertEqual(self.filter.classify("clb", "MAGIC"), "unknown")

    def test_mongodb_stable(self) -> None:
        self.assertEqual(self.filter.classify("mongodb", "RUNNING"), "stable")

    def test_mongodb_transient(self) -> None:
        self.assertEqual(self.filter.classify("mongodb", "INITING"), "transient")

    def test_mongodb_unknown(self) -> None:
        self.assertEqual(self.filter.classify("mongodb", "DELETED"), "unknown")

    def test_postgres_stable(self) -> None:
        self.assertEqual(self.filter.classify("postgres", "RUNNING"), "stable")

    def test_postgres_transient(self) -> None:
        self.assertEqual(self.filter.classify("postgres", "RESIZING"), "transient")

    def test_postgres_unknown(self) -> None:
        self.assertEqual(self.filter.classify("postgres", "QUIRK"), "unknown")

    def test_ckafka_stable(self) -> None:
        self.assertEqual(self.filter.classify("ckafka", "RUNNING"), "stable")

    def test_ckafka_transient(self) -> None:
        self.assertEqual(self.filter.classify("ckafka", "UPGRADING"), "transient")

    def test_ckafka_unknown(self) -> None:
        self.assertEqual(self.filter.classify("ckafka", "FLAP"), "unknown")

    # ------------------------------------------------------------------
    # Cross-service behavior
    # ------------------------------------------------------------------
    def test_unknown_service_returns_unknown(self) -> None:
        self.assertEqual(self.filter.classify("nonexistent_service", "RUNNING"), "unknown")

    def test_known_services_returns_all_seven(self) -> None:
        services = self.filter.known_services()
        self.assertEqual(len(services), 7)
        for s in KNOWN_SERVICES:
            self.assertIn(s, services)

    def test_state_in_both_sets_returns_unknown(self) -> None:
        """Config error: a state in BOTH stable and transient → unknown (route to human)."""
        bad_dir = Path(tempfile.mkdtemp(prefix="tsf-bad-"))
        try:
            _make_fixture(bad_dir, "cvm", ["RUNNING"], ["RUNNING"])  # RUNNING in both
            f = TransientStateFilter(bad_dir)
            self.assertEqual(f.classify("cvm", "RUNNING"), "unknown")
        finally:
            import shutil
            shutil.rmtree(bad_dir, ignore_errors=True)

    def test_is_transient_matches_classify(self) -> None:
        """is_transient is a thin wrapper over classify (per Spec §6.2)."""
        for service in KNOWN_SERVICES:
            for state in self.DEFAULT_TRANSIENT[service]:
                self.assertTrue(
                    self.filter.is_transient(service, state),
                    f"is_transient({service}, {state}) should be True",
                )
            for state in self.DEFAULT_STABLE[service]:
                self.assertFalse(
                    self.filter.is_transient(service, state),
                    f"is_transient({service}, {state}) should be False",
                )


class TransientStateFilterLoadErrorsTest(unittest.TestCase):
    """Verify load-failure paths fail loudly (per L4 — rejection tests for failure paths)."""

    def test_missing_fixture_classifies_as_unknown(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="tsf-missing-"))
        try:
            # Only create one fixture; cdb is missing
            _make_fixture(tmpdir, "cvm", ["RUNNING"], [])
            f = TransientStateFilter(tmpdir)  # no raise — lazy load
            # Querying missing service returns unknown
            self.assertEqual(f.classify("cdb", "RUNNING"), "unknown")
            # Querying present service works
            self.assertEqual(f.classify("cvm", "RUNNING"), "stable")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_real_fixtures_load_successfully(self) -> None:
        """The shipped fixtures in tests/fixtures/transient-states/ must load."""
        repo_root = Path(__file__).resolve().parent.parent
        fixture_dir = repo_root / "tests" / "fixtures" / "transient-states"
        self.assertTrue(fixture_dir.is_dir(), f"missing fixture dir: {fixture_dir}")
        f = TransientStateFilter(fixture_dir)
        # Verify all 7 services loaded
        self.assertEqual(len(f.known_services()), 7)
        # Spot-check CVM (most common)
        self.assertEqual(f.classify("cvm", "RUNNING"), "stable")
        self.assertEqual(f.classify("cvm", "STARTING"), "transient")


if __name__ == "__main__":
    unittest.main()
