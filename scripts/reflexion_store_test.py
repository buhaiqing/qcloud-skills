#!/usr/bin/env python3
"""Unit tests for reflexion_store.py."""

from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from failure_pattern_extract import enforce_line_cap, merge, parse_existing
from reflexion_store import (
    MAX_LINES,
    normalize_reflexion_key,
    parse_existing_safe,
    store_failure_pattern,
)


class TestReflexionStore(unittest.TestCase):
    """Test cases for reflexion store operations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patterns_file = Path(self.temp_dir.name) / "failure-patterns.md"

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_store_new_pattern(self) -> None:
        """Test storing a new pattern creates an entry."""
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Use JSON array format",
            path=self.patterns_file,
        )

        self.assertTrue(result)
        self.assertTrue(self.patterns_file.exists())

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertIn(key, patterns)
        self.assertEqual(patterns[key]["count"], 1)
        self.assertEqual(patterns[key]["fix"], "Use JSON array format")

    def test_dedup_existing_pattern(self) -> None:
        """Test that duplicate patterns are deduplicated and count incremented."""
        # Store first pattern
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Use JSON array format",
            path=self.patterns_file,
        )

        # Store same pattern again
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Different resolution",
            path=self.patterns_file,
        )

        self.assertTrue(result)

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertIn(key, patterns)
        # Count should be incremented
        self.assertEqual(patterns[key]["count"], 2)
        # Fix should NOT change on upsert (preserves original)
        self.assertEqual(patterns[key]["fix"], "Use JSON array format")

    def test_different_patterns_not_deduped(self) -> None:
        """Test that different patterns are stored separately."""
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Fix 1",
            path=self.patterns_file,
        )

        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="RunInstances",
            error="InvalidParameter",
            resolution="Fix 2",
            path=self.patterns_file,
        )

        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 2)

        key1 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        key2 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key1, patterns)
        self.assertIn(key2, patterns)

    def test_line_limit_enforcement(self) -> None:
        """Test that patterns are pruned when exceeding line limit."""
        # Create many patterns to exceed the limit
        for i in range(50):
            store_failure_pattern(
                skill=f"qcloud-skill-{i}-ops",
                command=f"Command{i}",
                error=f"Error{i}",
                resolution=f"Fix{i}",
                path=self.patterns_file,
            )

        # Verify file exists and is under limit
        self.assertTrue(self.patterns_file.exists())
        lines = self.patterns_file.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), MAX_LINES)

    def test_prune_keeps_high_count_patterns(self) -> None:
        """Test that pruning keeps patterns with higher hit counts."""
        # Store pattern with high count (via multiple upserts)
        for _ in range(10):
            store_failure_pattern(
                skill="qcloud-popular-ops",
                command="PopularCommand",
                error="PopularError",
                resolution="PopularFix",
                path=self.patterns_file,
            )

        # Store many low-count patterns
        for i in range(60):
            store_failure_pattern(
                skill=f"qcloud-rare-{i}-ops",
                command=f"RareCommand{i}",
                error=f"RareError{i}",
                resolution=f"RareFix{i}",
                path=self.patterns_file,
            )

        patterns = parse_existing_safe(self.patterns_file)

        # High-count pattern should still exist
        high_count_key = normalize_reflexion_key("runtime", "qcloud-popular-ops", "PopularCommand", "PopularError")
        self.assertIn(high_count_key, patterns)
        self.assertEqual(patterns[high_count_key]["count"], 10)

    def test_category_defaults_to_runtime(self) -> None:
        """Test that new patterns default to 'runtime' category."""
        store_failure_pattern(
            skill="qcloud-test-ops",
            command="TestCommand",
            error="TestError",
            resolution="TestFix",
            path=self.patterns_file,
        )

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-test-ops", "TestCommand", "TestError")
        self.assertEqual(patterns[key]["category"], "runtime")

    def test_update_timestamp_on_upsert(self) -> None:
        """Test that upsert updates the timestamp."""
        import time

        # Store first pattern
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="Test",
            error="Error",
            resolution="Fix",
            path=self.patterns_file,
        )

        patterns1 = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "Test", "Error")
        first_seen = patterns1[key].get("first_seen")

        # Wait a moment and upsert
        time.sleep(0.01)
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="Test",
            error="Error",
            resolution="NewFix",
            path=self.patterns_file,
        )

        patterns2 = parse_existing_safe(self.patterns_file)
        # first_seen should remain unchanged (it's the creation time)
        self.assertEqual(patterns2[key]["first_seen"], first_seen)
        # But count should be updated
        self.assertEqual(patterns2[key]["count"], 2)

    def test_empty_skill_rejected(self) -> None:
        """Test that empty skill is rejected."""
        result = store_failure_pattern(
            skill="",
            command="Test",
            error="Error",
            resolution="Fix",
            path=self.patterns_file,
        )
        self.assertFalse(result)

    def test_empty_error_rejected(self) -> None:
        """Test that empty error is rejected."""
        result = store_failure_pattern(
            skill="qcloud-test-ops",
            command="Test",
            error="",
            resolution="Fix",
            path=self.patterns_file,
        )
        self.assertFalse(result)

    def test_file_created_if_not_exists(self) -> None:
        """Test that file is created if it doesn't exist."""
        non_existent = Path(self.temp_dir.name) / "non_existent" / "failure-patterns.md"

        result = store_failure_pattern(
            skill="qcloud-test-ops",
            command="Test",
            error="Error",
            resolution="Fix",
            path=non_existent,
        )

        self.assertTrue(result)
        self.assertTrue(non_existent.exists())

    def test_normalize_reflexion_key_shape(self) -> None:
        """normalize_reflexion_key emits the 4-tuple (cat, skill, cmd_norm, err)."""
        key = normalize_reflexion_key("Runtime", "Qcloud-CVM-Ops", "TerminateInstances i-abc", "MissingParameter X")
        self.assertEqual(
            key,
            ("runtime", "qcloud-cvm-ops", "terminateinstances", "missingparameter x"),
        )

    def test_key_matches_copilot_sink_shape(self) -> None:
        """Same failure from copilot and GCL must produce an identical key string.

        Fixes L5: the two sinks must dedup instead of double-writing.
        """
        cat, skill, cmd, err = "runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        gcl_key = normalize_reflexion_key(cat, skill, cmd, err)
        # copilot reflexion.py uses an identical normalize_reflexion_key impl
        copilot_key = normalize_reflexion_key(cat, skill, cmd, err)
        self.assertEqual(gcl_key, copilot_key)
        self.assertEqual(
            ":".join(gcl_key),
            "runtime:qcloud-cvm-ops:terminateinstances:missingparameter",
        )

    def test_dedup_across_category_separates(self) -> None:
        """Different categories yield different keys (no cross-category merge)."""
        k1 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "X", "Y")
        k2 = normalize_reflexion_key("cli_parameter", "qcloud-cvm-ops", "X", "Y")
        self.assertNotEqual(k1, k2)


class TestCount1Survival(unittest.TestCase):
    """Regression: count=1 patterns must survive their first write.

    Previously reflexion_auto_writer.write_trace() called prune_low_frequency(min_count=3)
    BEFORE enforce_line_cap, silently removing brand-new patterns before they were ever
    written. store_failure_pattern() correctly handles capacity via _prune_by_count
    (which only fires when patterns > ~150). The write_trace path now mirrors this.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.patterns_file = self.temp_path / "failure-patterns.md"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_count1_pattern_survives_first_write(self) -> None:
        """A new pattern with count=1 must persist after its first store_failure_pattern call."""
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="DescribeInstances",
            error="AuthFailure: SecretId not found",
            resolution="Verify TENCENTCLOUD_SECRET_ID is correct",
            path=self.patterns_file,
        )
        self.assertTrue(result)
        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 1, "count=1 pattern must survive first write")
        first_pattern = next(iter(patterns.values()))
        self.assertEqual(first_pattern["count"], 1)
        self.assertEqual(first_pattern["skill"], "qcloud-cvm-ops")

    def test_write_trace_preserves_count1(self) -> None:
        """write_trace must NOT strip count=1 patterns before writing."""
        import reflexion_auto_writer as raw
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-redis-ops",
                    "command": "DescribeInstances",
                    "error": "Resource not found",
                    "fix": "Check resource ID",
                    "count": 1,
                }
            }
        }
        ok = raw.write_trace(trace, patterns_path=self.patterns_file)
        self.assertTrue(ok)
        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 1, "count=1 pattern must survive write_trace")

    def test_write_trace_isolates_tmp_file(self) -> None:
        """patterns_path redirects output away from the production file."""
        import reflexion_auto_writer as raw
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-redis-ops",
                    "command": "DescribeInstances",
                    "error": "tmp isolation probe",
                    "fix": "redirect",
                    "count": 1,
                }
            }
        }
        self.assertTrue(raw.write_trace(trace, patterns_path=self.patterns_file))
        self.assertIn("tmp isolation probe", self.patterns_file.read_text(encoding="utf-8"))


class TestDemotionIntegration(unittest.TestCase):
    """P1-2: evicted patterns demote to warm/cold layers instead of being lost."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.hot = self.temp_path / "failure-patterns.md"
        self.warm = self.temp_path / "failure-patterns-warm.md"
        self.cold = self.temp_path / "failure-patterns-cold.md"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_evicted_patterns_demote_to_warm(self) -> None:
        """When hot exceeds limit, lowest-count patterns go to warm."""
        # Override the module-level paths so demotion finds our temp files
        import reflexion_store as rs
        orig_hot = rs._HOT_PATH
        orig_warm = rs._WARM_PATH
        orig_cold = rs._COLD_PATH
        rs._HOT_PATH = self.hot
        rs._WARM_PATH = self.warm
        rs._COLD_PATH = self.cold
        try:
            # Store many patterns to force eviction
            for i in range(160):
                store_failure_pattern(
                    skill="qcloud-popular-ops",
                    command=f"op{i}",
                    error=f"error{i}",
                    resolution=f"fix{i}",
                    path=self.hot,
                )
            # The lowest-count (count=1) patterns should have been demoted to warm
            hot_patterns = parse_existing_safe(self.hot)
            warm_patterns = parse_existing_safe(self.warm) if self.warm.exists() else {}
            self.assertLess(len(hot_patterns), 160, "hot should have been pruned")
            # Demoted patterns should be in warm
            self.assertGreater(len(warm_patterns), 0, "warm should have received demoted patterns")
        finally:
            rs._HOT_PATH = orig_hot
            rs._WARM_PATH = orig_warm
            rs._COLD_PATH = orig_cold




class TestBulkUpdateFirstSeenSurvival(unittest.TestCase):
    """R2: the BULK CLI path (_bulk_update) must not filter first-seen patterns.

    Commit 4e8e77b fixed prune-before-first-write in write_trace() only. The
    identical call in _bulk_update() kept deleting count=1 patterns on the run
    that first observed them, so with --min-count 3 (the default) no pattern
    could ever reach count 3 and the store was permanently empty. Measured on
    the real corpus: 78 traces → "New patterns: 1 / Pruned: 1 / Total: 0".

    These tests drive _bulk_update() directly with PATTERNS_FILE/ROOT redirected
    into a tmp dir — the repo's real docs/failure-patterns.md is never touched.
    """

    def setUp(self) -> None:
        import reflexion_auto_writer as raw

        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp_dir.name)
        self.patterns_file = self.tmp / "failure-patterns.md"
        self.raw = raw
        self._orig_root = raw.ROOT
        self._orig_patterns_file = raw.PATTERNS_FILE
        # _bulk_update prints PATTERNS_FILE.relative_to(ROOT) → both must point
        # at the same tmp dir, or the summary raise ValueError.
        raw.ROOT = self.tmp
        raw.PATTERNS_FILE = self.patterns_file

    def tearDown(self) -> None:
        self.raw.ROOT = self._orig_root
        self.raw.PATTERNS_FILE = self._orig_patterns_file
        self.temp_dir.cleanup()

    # -- helpers ----------------------------------------------------------

    def _trace(self, name: str, skill: str, command: str, error: str) -> Path:
        """Write a GCL-shaped trace whose final block carries a failure_pattern."""
        path = self.tmp / name
        path.write_text(
            json.dumps({
                "final": {
                    "failure_pattern": {
                        "category": "runtime",
                        "skill": skill,
                        "command": command,
                        "error": error,
                        "fix": "fix it",
                        "reusable": True,
                    }
                }
            }),
            encoding="utf-8",
        )
        return path

    def _bulk(
        self, trace_paths: list[Path], min_count: int = 3, dry_run: bool = False
    ) -> tuple[int, str, str]:
        """Run the bulk path under stdout/stderr capture. Returns (rc, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.raw._bulk_update(trace_paths, dry_run=dry_run, min_count=min_count)
        return rc, out.getvalue(), err.getvalue()

    @staticmethod
    def _reported(out: str) -> dict[str, int]:
        """Parse the printed summary counters into real ints."""
        return {
            label: int(value)
            for label, value in re.findall(
                r"(New patterns|Total patterns|Total hits):\s+(\d+)", out
            )
        }

    # -- first-seen survival ----------------------------------------------

    def test_first_seen_pattern_survives_bulk_run(self) -> None:
        """A first-ever failure_pattern must be present with count == 1 after a bulk run."""
        trace = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        rc, _out, err = self._bulk([trace])
        self.assertEqual(rc, 0, f"clean bulk run must exit 0 (stderr: {err})")

        patterns = parse_existing(self.patterns_file)
        self.assertEqual(len(patterns), 1, "first-seen count=1 pattern must survive the bulk run")
        self.assertEqual(
            patterns[("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")]["count"],
            1,
        )

    def test_same_pattern_in_two_traces_counts_two(self) -> None:
        """Recurrence across two traces accumulates instead of being pruned."""
        traces = [
            self._trace("gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"),
            self._trace("gcl-trace-b.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"),
        ]
        rc, _out, _err = self._bulk(traces)
        self.assertEqual(rc, 0)

        patterns = parse_existing(self.patterns_file)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(
            patterns[("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")]["count"],
            2,
        )

    # -- the aging policy --min-count must keep ---------------------------

    def test_preexisting_count1_pattern_is_retired(self) -> None:
        """--min-count ages out only what stopped recurring — asserted differentially.

        An `assertNotIn` alone holds even when everything is deleted, so the same
        run must also show a recurring pattern surviving with its count intact.
        """
        stale = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        first_hit = self._trace(
            "gcl-trace-b.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"
        )
        second_hit = self._trace(
            "gcl-trace-c.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"
        )
        self.assertEqual(self._bulk([stale, first_hit])[0], 0)
        # Run 2 re-scans only the recurrence → the stale pattern is unobserved.
        rc, _out, _err = self._bulk([second_hit])
        self.assertEqual(rc, 0)

        patterns = parse_existing(self.patterns_file)
        self.assertNotIn(
            ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter"),
            patterns,
            "a stored count=1 pattern that did not recur must be retired",
        )
        key = ("qcloud-redis-ops", "DescribeInstances", "ResourceNotFound")
        self.assertIn(key, patterns, "a pattern the run still observes must survive")
        self.assertEqual(patterns[key]["count"], 2, "surviving count must not be reset")
        self.assertEqual(len(patterns), 1)

    def test_min_count_1_retires_nothing(self) -> None:
        """--min-count 1 disables aging entirely: nothing may be retired."""
        first = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        self.assertEqual(self._bulk([first])[0], 0)
        second = self._trace(
            "gcl-trace-b.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"
        )
        rc, out, _err = self._bulk([second], min_count=1)
        self.assertEqual(rc, 0)
        self.assertIn("Retired (count<1):  0", out)

        patterns = parse_existing(self.patterns_file)
        self.assertEqual(len(patterns), 2, "min-count=1 must retire nothing")
        self.assertEqual(
            patterns[("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")]["count"],
            1,
        )

    # -- reported numbers must equal the real file -------------------------

    def test_reported_counts_match_file_contents(self) -> None:
        """Summary counters must equal the counts actually written to the store."""
        traces = [
            self._trace("gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"),
            self._trace("gcl-trace-b.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"),
            self._trace("gcl-trace-c.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"),
        ]
        rc, out, _err = self._bulk(traces)
        self.assertEqual(rc, 0)

        patterns = parse_existing(self.patterns_file)
        reported = self._reported(out)
        self.assertEqual(reported["New patterns"], 2)
        self.assertEqual(reported["Total patterns"], 2)
        self.assertEqual(reported["Total hits"], 3)
        # populated values, not just key presence (AGENTS.md L5)
        self.assertEqual(reported["Total patterns"], len(patterns))
        self.assertEqual(reported["Total hits"], sum(p["count"] for p in patterns.values()))
        self.assertEqual(sorted(p["count"] for p in patterns.values()), [1, 2])

    # -- R3: the empty-store gate -----------------------------------------

    def test_empty_store_gate_fires(self) -> None:
        """Patterns found in traces but 0 stored must be loud and non-zero."""
        unmergeable = self.tmp / "gcl-trace-unmergeable.json"
        unmergeable.write_text(
            json.dumps({
                "final": {
                    "failure_pattern": {
                        "category": "runtime",
                        "skill": "",  # dropped by merge() → nothing can be stored
                        "command": "TerminateInstances",
                        "error": "MissingParameter",
                    }
                }
            }),
            encoding="utf-8",
        )
        rc, out, err = self._bulk([unmergeable])
        self.assertNotEqual(rc, 0, "empty store despite patterns found must not look like success")
        self.assertIn("REFLEXION STORE IS EMPTY", err)
        self.assertIn("Total patterns:        0", out)
        self.assertEqual(parse_existing(self.patterns_file), {})

    def test_empty_store_gate_silent_on_clean_run(self) -> None:
        """A run that does store a pattern stays silent and exits 0."""
        trace = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        rc, out, err = self._bulk([trace])
        self.assertEqual(rc, 0)
        self.assertNotIn("REFLEXION STORE IS EMPTY", err)
        self.assertEqual(self._reported(out)["Total patterns"], 1)

    def test_gate_silent_when_no_patterns_in_traces(self) -> None:
        """Genuinely-nothing-to-do: no failure_pattern anywhere → no empty-store alarm."""
        trace = self.tmp / "gcl-trace-clean.json"
        trace.write_text(json.dumps({"final": {"status": "ok"}}), encoding="utf-8")
        rc, _out, err = self._bulk([trace])
        self.assertEqual(rc, 1, "pre-existing contract: 1 = no patterns found")
        self.assertNotIn("REFLEXION STORE IS EMPTY", err)

    # -- counting is a function of the corpus, not of the run count --------

    def test_cross_run_accumulation_is_not_a_first_write_filter(self) -> None:
        """A failure recurring in a LATER run must raise the count, never reset it.

        R2's fix moved the prune before the merge, which stopped deleting the
        pattern before it was written — but still deleted it on the next run and
        re-created it at count 1, so --min-count stayed a first-write filter
        delayed by one run and the count could never reach it.
        """
        key = ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        first = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        second = self._trace(
            "gcl-trace-b.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        for expected, trace in enumerate((first, second), start=1):
            rc, _out, err = self._bulk([trace])
            self.assertEqual(rc, 0, err)
            self.assertEqual(
                parse_existing(self.patterns_file)[key]["count"],
                expected,
                "--min-count must not delete a pattern the run just observed",
            )

        before = hashlib.sha256(self.patterns_file.read_bytes()).hexdigest()
        rc, _out, err = self._bulk([second])
        self.assertEqual(rc, 0, err)
        self.assertEqual(
            hashlib.sha256(self.patterns_file.read_bytes()).hexdigest(),
            before,
            "re-processing the same corpus must be a byte-for-byte no-op "
            "(same day — the rendered header embeds today's date)",
        )

    def test_three_runs_over_one_corpus_are_idempotent(self) -> None:
        """Counts track the corpus; running the extractor again must add nothing."""
        traces = [
            self._trace(
                f"gcl-trace-{n}.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"
            )
            for n in ("a", "b", "c")
        ]
        digests, hits = set(), set()
        for _ in range(3):
            rc, out, err = self._bulk(traces)
            self.assertEqual(rc, 0, err)
            digests.add(hashlib.sha256(self.patterns_file.read_bytes()).hexdigest())
            hits.add(self._reported(out)["Total hits"])

        self.assertEqual(len(digests), 1, "the store must not change on a re-run")
        self.assertEqual(hits, {3}, "Total hits must be the corpus hit count, not runs x hits")

    def test_observed_patterns_evicted_by_the_cap_are_reported_not_fatal(self) -> None:
        """The R3 gate must run AFTER the line cap: the cap is the loss path.

        Computed first, `missing` was structurally empty — both sides call
        pattern_key() on the same new_patterns list — while the cap evicted
        observed keys and the run still exited 0, so a GCL run could not tell
        that its own corpus had been truncated.

        The report is what the gate owes: loud, after the cap, naming the keys.
        It is deliberately NOT fatal for a cap-evicted key — merge() accepts
        every key `observed` holds, so that loss is the designed 200-line budget
        doing its job, and returning 3 made `make reflexion-update` (part of
        `make all`) permanently red on a large corpus with no remedy an operator
        could apply. Loss the cap cannot explain still exits 3; see
        test_gate_names_an_observed_pattern_merge_dropped.
        """
        traces = [
            self._trace(f"gcl-trace-{i:03d}.json", "qcloud-bulk-ops", f"cmd{i}", f"err{i}")
            for i in range(200)
        ]
        rc, out, err = self._bulk(traces)

        dropped = int(re.search(r"Dropped \(cap \d+\):\s+(\d+)", out).group(1))
        self.assertGreater(dropped, 0, "the fixture must actually overflow the cap")
        self.assertEqual(rc, 0, f"a full store is not a failure (stderr: {err})")
        self.assertIn("REFLEXION GATE (non-fatal)", err)
        self.assertIn("qcloud-bulk-ops", err, "the dropped keys must be reported by name")

    def test_write_trace_requires_an_explicit_destination(self) -> None:
        """The store must be unreachable without naming it — a signature, not a convention.

        The doc claimed "a run against a temporary root cannot mutate the
        shipped file", but the code defaulted `patterns_path` to the module's
        PATTERNS_FILE: one call that omitted it rewrote the committed store
        (sha ea524363611f -> ae54c1283c2c). There is no default any more.
        """
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-sink-ops",
                    "command": "cmd",
                    "error": "err",
                    "fix": "fix",
                }
            }
        }
        with self.assertRaises(TypeError):
            self.raw.write_trace(trace)  # type: ignore[call-arg]

    def test_write_trace_names_the_pattern_the_cap_dropped(self) -> None:
        """`True` means the write happened, not that this pattern is in the store.

        `evicted` is computed from the pre-existing keys only, so the eviction
        report could not name the newcomer — the one row the caller was writing.
        """
        full = TestLineCapEnforcement._patterns(200)
        self.patterns_file.write_text(
            "\n".join(enforce_line_cap(full, max_lines=10**6)) + "\n", encoding="utf-8"
        )
        self.assertGreater(len(parse_existing(self.patterns_file)), 100)

        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-newcomer-ops",
                    "command": "cmd",
                    "error": "err",
                    "fix": "fix",
                    "count": 1,
                }
            }
        }
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            written = self.raw.write_trace(trace, patterns_path=self.patterns_file)

        self.assertTrue(written, "the write did happen")
        self.assertNotIn(
            ("qcloud-newcomer-ops", "cmd", "err"),
            parse_existing(self.patterns_file),
            "precondition: the cap must have dropped the newcomer for this to mean anything",
        )
        self.assertIn("qcloud-newcomer-ops:cmd:err", err.getvalue())
        self.assertIn("stored NOWHERE", err.getvalue())

    def test_pre_upgrade_counts_are_replaced_by_the_true_count(self) -> None:
        """Counts written before the sources column existed were run-multiplicity
        fiction; the first run over a real corpus replaces them with the truth."""
        self.patterns_file.write_text(
            "## 4. Runtime Execution Patterns\n\n"
            "| Skill | Operation | Error Pattern | Root Cause | Count | LastSeen | Severity |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| `qcloud-cvm-ops` | `TerminateInstances` | MissingParameter | fix | 9 | 2026-09 | major |\n",
            encoding="utf-8",
        )
        trace = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        rc, _out, err = self._bulk([trace])
        self.assertEqual(rc, 0, err)

        patterns = parse_existing(self.patterns_file)
        self.assertEqual(
            patterns[("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")]["count"],
            1,
            "one trace observed the pattern, so the count is 1 regardless of what was stored",
        )

    def test_write_trace_counts_each_trace_once(self) -> None:
        """The single-trace path must be idempotent per trace file too."""
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-redis-ops",
                    "command": "DescribeInstances",
                    "error": "Resource not found",
                    "fix": "Check resource ID",
                }
            }
        }
        source = self.tmp / "gcl-trace-a.json"
        source.write_text("{}", encoding="utf-8")
        for _ in range(3):
            self.assertTrue(
                self.raw.write_trace(trace, trace_path=source, patterns_path=self.patterns_file)
            )

        patterns = parse_existing(self.patterns_file)
        self.assertEqual(
            patterns[("qcloud-redis-ops", "DescribeInstances", "Resource not found")]["count"],
            1,
            "writing the same trace three times is one observation, not three",
        )

    # -- R3: the gate asserts the real invariant --------------------------

    def test_gate_names_an_observed_pattern_merge_dropped(self) -> None:
        """A PARTIAL loss must fail by name, not pass because others survived."""
        dropped = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        kept = self._trace(
            "gcl-trace-b.json", "qcloud-redis-ops", "DescribeInstances", "ResourceNotFound"
        )
        real_merge = self.raw.merge
        self.raw.merge = lambda existing, new: real_merge(
            existing, [p for p in new if p.get("skill") != "qcloud-cvm-ops"]
        )
        try:
            rc, out, err = self._bulk([dropped, kept])
        finally:
            self.raw.merge = real_merge

        self.assertEqual(rc, 3, "losing an observed pattern must not look like success")
        self.assertIn("qcloud-cvm-ops:TerminateInstances:MissingParameter", err)
        self.assertEqual(self._reported(out)["Total patterns"], 1)

    def test_dry_run_reports_instead_of_failing(self) -> None:
        """--dry-run writes nothing, so it must not return the gate code."""
        unmergeable = self.tmp / "gcl-trace-unmergeable.json"
        unmergeable.write_text(
            json.dumps({
                "final": {
                    "failure_pattern": {
                        "category": "runtime",
                        "skill": "",
                        "command": "TerminateInstances",
                        "error": "MissingParameter",
                    }
                }
            }),
            encoding="utf-8",
        )
        rc, out, err = self._bulk([unmergeable], dry_run=True)
        self.assertEqual(rc, 0, "a read-only preview must not fail")
        self.assertIn("[dry-run] Would update:", out)
        self.assertIn("would leave the store empty", err)
        self.assertFalse(self.patterns_file.exists(), "a dry run must not create the store")

    # -- CLI wiring --------------------------------------------------------

    def test_cli_min_count_flag_reaches_bulk_update(self) -> None:
        """main() must forward --min-count into the bulk path."""
        trace = self._trace(
            "gcl-trace-a.json", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        )
        original_argv = sys.argv
        sys.argv = ["reflexion_auto_writer.py", "--input", str(trace), "--min-count", "1"]
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = self.raw.main()
        finally:
            sys.argv = original_argv

        self.assertEqual(rc, 0)
        self.assertIn("Retired (count<1):  0", out.getvalue())
        self.assertEqual(len(parse_existing(self.patterns_file)), 1)


class TestLineCapEnforcement(unittest.TestCase):
    """AGENTS.md makes "≤200 lines" a P0 constraint: it must be applied, not warned."""

    @staticmethod
    def _patterns(n: int) -> dict[tuple[str, str, str], dict]:
        """n distinct patterns, count 1..n, all in one category."""
        return {
            (f"qcloud-skill-{i}-ops", f"cmd{i}", f"err{i}"): {
                "category": "runtime",
                "skill": f"qcloud-skill-{i}-ops",
                "command": f"cmd{i}",
                "error": f"err{i}",
                "fix": "fix it",
                "count": i + 1,
                "last_seen": "2026-09",
                "sources": {"gcl-trace-x.json"},
            }
            for i in range(n)
        }

    def test_cap_is_enforced_by_dropping_the_least_recurring_rows(self) -> None:
        patterns = self._patterns(200)
        lines = enforce_line_cap(patterns)

        self.assertLessEqual(len(lines), MAX_LINES, "the emitted store must fit the cap")
        self.assertGreater(len(lines), MAX_LINES - 10, "the cap must be filled, not emptied")
        kept = sorted(p["count"] for p in patterns.values())
        self.assertLess(len(kept), 200, "rows must actually have been dropped")
        self.assertEqual(
            kept,
            list(range(200 - len(kept) + 1, 201)),
            "the dropped rows must be the least recurring ones",
        )

    def test_small_store_is_untouched(self) -> None:
        patterns = self._patterns(3)
        lines = enforce_line_cap(patterns)
        self.assertEqual(len(patterns), 3, "nothing may be dropped below the cap")
        self.assertLessEqual(len(lines), MAX_LINES)

    def test_sources_column_round_trips(self) -> None:
        patterns = self._patterns(2)
        lines = enforce_line_cap(patterns)
        self.assertTrue(any("| Sources |" in ln for ln in lines), "the column must be emitted")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failure-patterns.md"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            reloaded = parse_existing(path)
        self.assertEqual(
            reloaded[("qcloud-skill-0-ops", "cmd0", "err0")]["sources"],
            {"gcl-trace-x.json"},
            "sources must survive a write/read round trip",
        )

    # -- the cells hold arbitrary trace text -------------------------------

    def test_sources_column_round_trips_hostile_values(self) -> None:
        """Pipes, unpaired backticks and spaces in trace text must survive.

        Cells are written verbatim from the trace, and `command` is the executed
        shell command, so a pipe is ordinary. Unescaped, one pipe made an 8-cell
        row for an 8-column header; the parser's leading/trailing trim then read
        Count from the wrong column and truncated `error`, so prune saw a stale
        key, deleted it, and merge re-added it — the same key reported as both
        "Retired: 1" and "New patterns: 1" on every run, count pinned.
        """
        key = ("qcloud-adv-ops", "tccli cvm Run | grep Id", "InvalidParameter: a | b")
        hostile = {
            key: {
                "category": "runtime",
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "fix": "quote it: `a|b` and a lone ` backtick",
                "count": 2,
                "last_seen": "2026-09",
                "sources": {"ev il trace.json", "a`b.json"},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hostile.md"
            path.write_text("\n".join(enforce_line_cap(hostile)) + "\n", encoding="utf-8")
            back = parse_existing(path)

        self.assertIn(key, back, f"the row key must survive the round trip, got {list(back)}")
        self.assertEqual(back[key]["count"], 2, "Count must still be read from the Count cell")
        self.assertEqual(back[key]["error"], "InvalidParameter: a | b")
        self.assertEqual(back[key]["fix"], "quote it: `a|b` and a lone ` backtick")
        self.assertEqual(back[key]["sources"], {"ev il trace.json", "a`b.json"})

    def test_rescanning_a_hostile_corpus_does_not_inflate_count(self) -> None:
        """Re-scanning an identical corpus must be a no-op, hostile names included.

        Sources are persisted as a JSON array precisely so a filename containing
        a space round-trips. Space-joined, one such filename became N tokens that
        could never match the original again, so each re-scan added +1 and
        --promote (count >= 10) was forgeable.
        """
        pattern = {
            "category": "runtime",
            "skill": "qcloud-adv-ops",
            "command": "tccli cvm Run",
            "error": "InvalidParameter",
            "fix": "quote it",
            "_source": "ev il trace.json",
        }
        key = ("qcloud-adv-ops", "tccli cvm Run", "InvalidParameter")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.md"
            existing: dict = {}
            for scan in range(4):
                # Round-trip through the file each time: the defect was in the
                # persisted form, not in memory.
                existing = merge(existing, [pattern])
                path.write_text("\n".join(enforce_line_cap(existing)) + "\n", encoding="utf-8")
                existing = parse_existing(path)
                self.assertEqual(
                    existing[key]["count"], 1,
                    f"scan {scan + 1} of the identical corpus inflated the count",
                )

    def test_unattributed_count_survives_a_merge(self) -> None:
        """A row whose count exceeds its sources keeps that remainder.

        reflexion_store.store_failure_pattern — the qcloud-copilot sink, the
        third writer of this file — records no sources, so deriving count from
        the source set alone reset its rows to 1: a count=10 row plus one new
        trace became count=1, destroying the recurrence signal --promote reads.
        """
        key = ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.md"
            path.write_text(
                "## 4. Runtime Execution Patterns\n\n"
                "| Skill | Operation | Error Pattern | Root Cause | Count | LastSeen | Severity | Sources |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                f"| `{key[0]}` | `{key[1]}` | {key[2]} | fix | 10 | 2026-09 | major | — |\n",
                encoding="utf-8",
            )
            observed = {
                "category": "runtime",
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "fix": "fix",
                "_source": "gcl-trace-new.json",
            }

            merged = merge(parse_existing(path), [observed])
            self.assertEqual(
                merged[key]["count"], 11,
                "10 unattributed hits + 1 observed trace must be 11, not 1",
            )
            # ...and the same trace again is still one observation.
            merged = merge(merged, [observed])
            self.assertEqual(merged[key]["count"], 11, "a re-scan must not add another hit")

    def test_layer_limit_is_not_recapped_to_the_hot_limit(self) -> None:
        """A layer's own limit must reach enforce_line_cap, not the 200-line hot cap.

        _append_to_layer passed max_lines for its capacity maths but called the
        global cap, so WARM_LIMIT=500 / COLD_LIMIT=2000 were unreachable ceilings
        and demotion destroyed memory instead of preserving it.
        """
        import reflexion_store as rs

        with tempfile.TemporaryDirectory() as tmp:
            warm = Path(tmp) / "failure-patterns-warm.md"
            fixture = self._patterns(250)
            warm.write_text(
                "\n".join(enforce_line_cap(fixture, max_lines=10**6)) + "\n", encoding="utf-8"
            )
            self.assertGreater(
                len(parse_existing(warm)), 200, "fixture must exceed the hot cap to be meaningful"
            )

            extra = {
                **next(iter(fixture.values())),
                "skill": "qcloud-skill-extra-ops",
                "command": "cmd-extra",
                "error": "err-extra",
            }
            self.assertTrue(rs._append_to_layer(extra, warm, rs._WARM_LIMIT))
            self.assertGreater(
                len(parse_existing(warm)), 200,
                "the warm layer's 500-line limit must not be re-capped to the hot 200",
            )

    def test_every_section_heading_is_preceded_by_a_blank_line(self) -> None:
        """A table's last row must not swallow the next "## " section heading."""
        patterns = self._patterns(1)
        patterns[("qcloud-skill-9-ops", "cmd9", "err9")] = {
            **next(iter(patterns.values())),
            "category": "cli_parameter",
            "skill": "qcloud-skill-9-ops",
            "command": "cmd9",
            "error": "err9",
        }
        lines = enforce_line_cap(patterns)
        for i, line in enumerate(lines):
            if line.startswith("## "):
                self.assertEqual(lines[i - 1], "", f"{line!r} is glued to the line above")


# ---------------------------------------------------------------------------
# The documented writer list must match the code
# ---------------------------------------------------------------------------

_STORE_FILE = "failure-patterns.md"


def _store_writers() -> set[str]:
    """Functions in scripts/*.py that write docs/failure-patterns.md.

    "Writes the store" is read off the source: the function mentions the store
    filename, or a module-level name whose value mentions it (PATTERNS_FILE,
    HOT_PATH, DEFAULT_STORE_PATH, _FAILURE_PATTERNS_PATH), AND it writes. Doc
    references count, which is how the shared sink is found.
    """
    scripts = Path(__file__).resolve().parent
    writers: set[str] = set()
    for path in sorted(scripts.glob("*.py")):
        if path.name.endswith("_test.py") or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        store_names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and _STORE_FILE in ast.unparse(node.value)
        }
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            source = ast.unparse(node)
            mentions = _STORE_FILE in source or any(n in source for n in store_names)
            writes = "write_text" in source or ".write(" in source
            if mentions and writes:
                writers.add(f"{path.stem}.{node.name}")
    return writers


def _documented_writers() -> set[str]:
    """The fenced list in docs/reflexion-memory.md §10."""
    doc = (
        Path(__file__).resolve().parents[1] / "docs" / "reflexion-memory.md"
    ).read_text(encoding="utf-8")
    after = doc.split("<!-- store-writers:", 1)[1]
    return {
        line.strip()
        for line in after.split("```")[1].splitlines()
        if line.strip()
    }


class TestTheWriterListIsComplete(unittest.TestCase):
    """`docs/reflexion-memory.md` §10 must name every writer of the store.

    The count was wrong three rounds running ("Three paths write ..." against
    four, then five) because nothing connected the prose to the code. This test
    is that connection: add a writer, and the suite fails until the doc names it.
    """

    def test_documented_writers_match_the_code(self) -> None:
        self.assertEqual(
            _documented_writers(),
            _store_writers(),
            "docs/reflexion-memory.md §10 and the code disagree about who writes "
            "docs/failure-patterns.md",
        )

    def test_every_documented_writer_exists(self) -> None:
        scripts = Path(__file__).resolve().parent
        for name in sorted(_documented_writers()):
            module_name, _, function = name.partition(".")
            tree = ast.parse((scripts / f"{module_name}.py").read_text(encoding="utf-8"))
            defined = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            self.assertIn(function, defined, f"{name} is documented but does not exist")


# ---------------------------------------------------------------------------
# The suite must not be a producer of the artefacts the KPI gate grades
# ---------------------------------------------------------------------------

def _shipped_artefact_snapshot() -> tuple[str, dict[str, int]]:
    """(sha256 of the reflexion store, {evidence stream: line count})."""
    repo = Path(__file__).resolve().parents[1]
    store = repo / "docs" / "failure-patterns.md"
    digest = hashlib.sha256(store.read_bytes()).hexdigest() if store.is_file() else ""
    streams = {
        p.name: len(p.read_text(encoding="utf-8").splitlines())
        for p in (repo / "audit-results").glob("evidence-*.jsonl")
    }
    return digest, streams


# Captured at import, before any test in the run has executed: `unittest
# discover` imports every module first and only then runs them, so this is the
# pristine state even though other modules run before this one.
_AT_IMPORT = _shipped_artefact_snapshot()


class TestShippedArtefactsAreNotATestWorkspace(unittest.TestCase):
    """docs/failure-patterns.md and audit-results/evidence-*.jsonl are committed.

    They are agent-facing inputs to the KPI gate, which grades the evidence
    stream as a real run. The suite used to be their producer: `unittest
    discover` minted schema-valid, leak_checked, run_id="local" records and
    rewrote the store, so the gate read the test suite back as production
    evidence — the floor of 10 records did not stop it, because it counted 17.
    """

    def test_full_suite_did_not_mutate_the_shipped_artefacts(self) -> None:
        after = _shipped_artefact_snapshot()
        self.assertEqual(
            after,
            _AT_IMPORT,
            "the test suite wrote a committed, agent-facing artefact: "
            f"{_AT_IMPORT} -> {after}",
        )


if __name__ == "__main__":
    unittest.main()
