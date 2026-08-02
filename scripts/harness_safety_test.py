#!/usr/bin/env python3
"""Tests for harness_safety — Phase 3 destructive detection + token binding."""
import json
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[1])
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import harness_safety


class HarnessSafetyTest(unittest.TestCase):
    def test_destructive_detected(self) -> None:
        code = (
            "import sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import is_destructive; "
            "assert is_destructive('Delete the CVM instance ins-1'); "
            "assert not is_destructive('List the CVM instances'); "
            "print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_token_binding_ok(self) -> None:
        code = (
            "import hashlib, sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import bind_token; "
            "plan='delete ins-1'; h=hashlib.sha256(plan.encode()).hexdigest()[:16]; "
            "tok=bind_token(plan, h); assert tok==h; print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_token_mismatch_refuses(self) -> None:
        code = (
            "import sys\n"
            "sys.path.insert(0, 'scripts')\n"
            "from harness_safety import bind_token\n"
            "try:\n"
            "    bind_token('delete ins-1', 'deadbeef')\n"
            "except PermissionError:\n"
            "    print('ok')\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", res.stdout)

    def test_inflected_verbs_still_destructive(self) -> None:
        # Regression guard for the inflection gap: "deleted" / "removes" must be
        # caught (a bare substring/split match would let them bypass the token gate).
        code = (
            "import sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import is_destructive; "
            "assert is_destructive('the instance will be deleted'); "
            "assert is_destructive('this removes the disk'); "
            "assert is_destructive('stopping the cluster'); "
            "print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", res.stdout)


class HarnessSafetyFalsePositiveTest(unittest.TestCase):
    """Benign read-only plans must NOT trip the destructive gate.

    Every false positive forces a human to issue a confirmation token for a
    harmless plan, which trains operators to rubber-stamp the gate.
    """

    def test_benign_plans_are_not_destructive(self) -> None:
        for plan in (
            # Words that merely *start with* a destructive verb but are not
            # inflections of it — the old prefix match flagged all of these.
            "list resettable configs",
            "rmap the topology",
            "review the formatter output",
            "collect killswitch metrics",
            "describe instances",
            "list all buckets",
            "get metrics for the cluster",
        ):
            with self.subTest(plan=plan):
                self.assertFalse(harness_safety.is_destructive(plan))

    def test_inflected_verbs_are_still_destructive(self) -> None:
        # Inflection tolerance (L13) must survive the false-positive fix.
        for plan in (
            "the instances were stopped",
            "killing the runaway process",
            "formatting the attached volume",
            "deleting the snapshot",
            "terminated the cluster",
            "removes the disk",
        ):
            with self.subTest(plan=plan):
                self.assertTrue(harness_safety.is_destructive(plan))

    def test_new_verbs_still_destructive(self) -> None:
        for plan in (
            "isolate the compromised instance",
            "release the elastic IP",
            "shutdown the cluster",
            "expire the stale cache keys",
            "kill the runaway process",
            "unbind the security group",
            "rollback the deployment",
            "overwrite the bucket object",
            "format the attached volume",
        ):
            with self.subTest(plan=plan):
                self.assertTrue(harness_safety.is_destructive(plan))

    def test_short_verbs_require_exact_match(self) -> None:
        # A hypothetical 2-char verb must not prefix-match benign vocabulary.
        self.assertTrue(harness_safety._matches("rm", "rm"))
        self.assertFalse(harness_safety._matches("rmap", "rm"))
        # 3+ char verbs keep inflection tolerance.
        self.assertTrue(harness_safety._matches("deleted", "delete"))


class HarnessSafetyVerbsSourceTest(unittest.TestCase):
    """VERBS must come from assets/shared/destructive_verbs.json (single source)."""

    def test_verbs_load_from_shared_json(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(["alpha", "beta", "reset"], fh)
            fh.flush()
            path = Path(fh.name)
        try:
            loaded = harness_safety._load_verbs(path)
            self.assertEqual(loaded, {"alpha", "beta", "reset"})
        finally:
            path.unlink()

    def test_verbs_fallback_on_missing_json_with_warning(self) -> None:
        missing = Path("/nonexistent/destructive_verbs.json")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            loaded = harness_safety._load_verbs(missing)
        self.assertEqual(loaded, harness_safety._FALLBACK_VERBS)
        self.assertTrue(any("falling back" in str(w.message) for w in caught))

    def test_effective_verbs_are_strict_superset_of_legacy(self) -> None:
        self.assertIn("reset", harness_safety.VERBS)
        self.assertTrue(harness_safety._FALLBACK_VERBS <= harness_safety.VERBS)


if __name__ == "__main__":
    unittest.main()
