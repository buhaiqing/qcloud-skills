#!/usr/bin/env python3
"""Unit tests for failure_pattern_extract.py — stdlib only."""

import json

# Import from the module under test
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import failure_pattern_extract as fpe


class TestParseExisting(unittest.TestCase):
    """Tests for parse_existing() — markdown table parsing."""

    def _make_file(self, content: str) -> Path:
        p = Path(tempfile.mktemp(suffix=".md"))
        p.write_text(content, encoding="utf-8")
        return p

    def test_empty_file(self):
        p = self._make_file("")
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_no_section_headers(self):
        p = self._make_file("# Random doc\nSome text without tables.")
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_parses_single_pattern(self):
        content = (
            "## 1. CLI Parameter Errors\n\n"
            "| Skill | Command | Error Pattern | Fix | Count |\n"
            "|---|---|---|---|---|\n"
            "| `qcloud-cvm-ops` | `RunInstances` | `InvalidParameter` | Fix args | 3 |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        self.assertEqual(len(result), 1)
        key = ("qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["category"], "cli_parameter")
        self.assertEqual(result[key]["count"], 3)

    def test_skips_non_category_sections(self):
        content = (
            "## Usage Guidelines\n\n"
            "Some guide text with | pipes | in it |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_deduplicates_by_skill_command_error(self):
        content = (
            "## 1. CLI Parameter Errors\n\n"
            "| Skill | Command | Error Pattern | Fix | Count |\n"
            "|---|---|---|---|---|\n"
            "| `qcloud-redis-ops` | `DestroyInstances` | `MissingParameter` | Add InstanceIds | 5 |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        key = ("qcloud-redis-ops", "DestroyInstances", "MissingParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["count"], 5)


class TestCollectTraces(unittest.TestCase):
    """Tests for collect_traces() — glob + time filter."""

    def test_glob_no_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-2026-01-01-000000.json").write_text("{}", encoding="utf-8")
            (audit / "gcl-trace-2026-01-02-000000.json").write_text("{}", encoding="utf-8")
            result = fpe.collect_traces(root, None, None)
            self.assertEqual(len(result), 2)

    def test_since_hours_filters_old_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            old = audit / "gcl-trace-2020-01-01-000000.json"
            old.write_text("{}", encoding="utf-8")
            # Manually age the file
            import os
            old_time = 1577836800  # 2020-01-01 UTC
            os.utime(old, (old_time, old_time))

            new = audit / "gcl-trace-2099-01-01-000000.json"
            new.write_text("{}", encoding="utf-8")

            result = fpe.collect_traces(root, None, 24)
            self.assertEqual(len(result), 1)
            self.assertIn("2099", result[0].name)


class TestExtractFailurePatterns(unittest.TestCase):
    """Tests for extract_failure_patterns() — JSON parsing."""

    def _make_trace(self, data: dict) -> Path:
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_top_level_failure_pattern(self):
        trace = {
            "skill": "qcloud-cvm-ops",
            "final": {"status": "PASS"},
            "failure_pattern": {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Add InstanceIds",
                "reusable": True,
            },
        }
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["command"], "TerminateInstances")

    def test_iteration_failure_pattern(self):
        trace = {
            "skill": "qcloud-redis-ops",
            "final": {"status": "MAX_ITER"},
            "iterations": [
                {
                    "critic": {"scores": {"correctness": 0.5}},
                    "failure_pattern": {
                        "category": "runtime",
                        "skill": "qcloud-redis-ops",
                        "command": "ClearInstance",
                        "error": "Permission denied",
                        "fix": "Check CAM policy",
                        "reusable": True,
                    },
                }
            ],
        }
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], "runtime")
        self.assertIn("#iter-1", result[0]["_source"])

    def test_skips_invalid_json(self):
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text("not valid json{", encoding="utf-8")
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(result, [])

    def test_skips_missing_failure_pattern(self):
        trace = {"skill": "qcloud-cdb-ops", "final": {"status": "PASS"}}
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(result, [])


class TestMerge(unittest.TestCase):
    """Tests for merge() — dedup and increment."""

    def test_new_pattern_appended(self):
        existing = {}
        new = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "reusable": True,
            }
        ]
        result = fpe.merge(existing, new)
        key = ("qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["count"], 1)

    def test_existing_pattern_incremented(self):
        existing = {
            ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Fix args",
                "count": 2,
                "reusable": True,
            }
        }
        new = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Fix args",
                "reusable": True,
            }
        ]
        result = fpe.merge(existing, new)
        key = ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertEqual(result[key]["count"], 3)

    def test_skips_missing_skill(self):
        existing = {}
        new = [{"category": "runtime", "skill": "", "command": "", "error": "err"}]
        result = fpe.merge(existing, new)
        self.assertEqual(len(result), 0)


class TestPrune(unittest.TestCase):
    """Tests for prune_low_frequency()."""

    def test_prunes_below_threshold(self):
        patterns = {
            ("a", "b", "c"): {"count": 1},
            ("a", "b", "d"): {"count": 3},
            ("a", "b", "e"): {"count": 5},
        }
        fpe.prune_low_frequency(patterns, min_count=3)
        self.assertEqual(len(patterns), 2)
        self.assertNotIn(("a", "b", "c"), patterns)


class TestEnforceLineCap(unittest.TestCase):
    """Tests for enforce_line_cap()."""

    def test_produces_valid_markdown(self):
        patterns = {
            ("qcloud-cvm-ops", "RunInstances", "InvalidParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "count": 2,
                "reusable": True,
            }
        }
        lines = fpe.enforce_line_cap(patterns)
        self.assertTrue(lines[0].startswith("# Failure Patterns"))
        self.assertIn("## 1. CLI Parameter Errors", lines)
        self.assertIn("## Usage Guidelines", lines)

    def test_skips_empty_sections(self):
        patterns = {
            ("qcloud-cvm-ops", "RunInstances", "InvalidParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "count": 2,
                "reusable": True,
            }
        }
        lines = fpe.enforce_line_cap(patterns)
        # Runtime section should not appear if empty
        section_titles = [ln for ln in lines if ln.startswith("## ")]
        self.assertNotIn("## 4. Runtime Execution Patterns", section_titles)


# ---------------------------------------------------------------------------
# Cell escaping: one write/read cycle must be the identity
# ---------------------------------------------------------------------------

# Values a GCL trace can actually carry. `command` is the executed shell
# command and `error` is a raw exception string, so a pipeline, a quoted param,
# a Windows-ish path and an unpaired backtick are all ordinary inputs.
HOSTILE = [
    "plain",
    "a|b",
    "a\\b",
    "a`b",
    "trail`",          # escaped backtick at the cell edge (H-30)
    "`lead",
    "`",
    "``",
    "expected `",
    'q"x',
    "]",
    '["',
    '["a.json"]',
    "a b",
    " lead ",
    "\ttabbed\t",
    "|",
    "\\",
    "\\|",
    "a`|`b",
    "—",
    "C:\\new",          # backslash + letter that is also an escape letter
    "boom\n| forged | row |",   # newline: used to delete the whole row (H-31)
    "new\nline",
    "cr\rhere",
    "\n",
    "a\r\nb",
]


class TestCellEscaping(unittest.TestCase):
    """`escape_cell`/`unescape_cell` must be exact inverses through a real row.

    The old parser stripped backticks off *still-escaped* text, so an escaped
    trailing backtick lost its backtick and kept its backslash: `expected \\``
    read back as `expected \\`. It silently rewrote `error`, which is part of
    the dedup key, so the same failure re-keyed as a new row on every scan.
    Whitespace is the one documented exception — the key is normalised, so
    `' lead '` and `'lead'` are one pattern.
    """

    def _round_trip(self, value: str, *, as_skill: bool) -> str:
        """Write `value` into one cell, read the store back, return what came out.

        The emitter produces two shapes: `skill`/`command` inside backticks and
        `error`/`fix` bare. This exercises the value through both.
        """
        key = (value.strip(), "cmd", "err") if as_skill else ("qcloud-skill-ops", "cmd", value.strip())
        patterns = {
            key: {
                "category": "runtime",
                "skill": key[0],
                "command": "cmd",
                "error": key[2],
                "fix": "fix",
                "count": 1,
                "last_seen": "2026-09",
                "severity": "minor",
                "sources": set(),
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failure-patterns.md"
            path.write_text("\n".join(fpe.enforce_line_cap(patterns)) + "\n", encoding="utf-8")
            parsed = fpe.parse_existing(path)

        self.assertEqual(len(parsed), 1, f"the row was lost for {value!r} (as_skill={as_skill})")
        entry = next(iter(parsed.values()))
        return entry["skill"] if as_skill else entry["error"]

    def test_hostile_values_round_trip_either_emitted_shape(self):
        mismatches = []
        for value in HOSTILE:
            # A whitespace-only skill has no row to read back — parse_existing
            # skips those — so only the bare shape applies to it.
            for as_skill in (False, True) if value.strip() else (False,):
                got = self._round_trip(value, as_skill=as_skill)
                # The emitter writes "—" for a cell that is empty; the only
                # lossy case, and not an escaping one.
                if got != (value.strip() or "—"):
                    mismatches.append((value, as_skill, got))
        self.assertEqual(mismatches, [], f"{len(mismatches)} value(s) did not survive one cycle")

    def test_newline_in_a_cell_does_not_delete_the_row(self):
        """`parse_existing` is line-oriented: a raw newline used to lose the row.

        A nonempty `\n` or `\r` in any cell split the physical line, so the
        pattern disappeared from the store while `write_trace` still returned
        True. The pipes were already escaped, so this was data loss, not
        injection.
        """
        key = ("qcloud-newline-ops", "tccli cvm Run", "boom\n| forged | row | x")
        patterns = {
            key: {
                "category": "runtime",
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "fix": "fix",
                "count": 3,
                "last_seen": "2026-09",
                "sources": {"gcl-trace-a.json"},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failure-patterns.md"
            path.write_text("\n".join(fpe.enforce_line_cap(patterns)) + "\n", encoding="utf-8")
            parsed = fpe.parse_existing(path)

        self.assertEqual(len(parsed), 1, "a newline in a cell must not delete the row")
        self.assertEqual(parsed[key]["count"], 3)
        self.assertEqual(parsed[key]["error"], "boom\n| forged | row | x")
        self.assertEqual(parsed[key]["sources"], {"gcl-trace-a.json"})

    def test_unparseable_severity_does_not_eat_the_sources_cell(self):
        """`severity` and `last_seen` were the only cells the emitter left raw.

        An odd backtick in `severity` flipped the parser's backtick state for
        the rest of the row: the trailing pipes stopped splitting and the
        `Sources` cell was consumed. Provenance destroyed, count untouched —
        which breaks `count = len(sources) + unattributed` permanently.
        """
        for severity in ("a`b", "nor`mal", "minor|x", "\\", "`"):
            with self.subTest(severity=severity):
                key = ("qcloud-sev-ops", "cmd", "err")
                patterns = {
                    key: {
                        "category": "runtime",
                        "skill": key[0],
                        "command": key[1],
                        "error": key[2],
                        "fix": "fix",
                        "count": 7,
                        "last_seen": "2026-09",
                        "severity": severity,
                        "sources": {"gcl-trace-a.json"},
                    }
                }
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "failure-patterns.md"
                    path.write_text(
                        "\n".join(fpe.enforce_line_cap(patterns)) + "\n", encoding="utf-8"
                    )
                    parsed = fpe.parse_existing(path)

                self.assertEqual(parsed[key]["sources"], {"gcl-trace-a.json"})
                self.assertEqual(parsed[key]["count"], 7)
                self.assertEqual(parsed[key]["severity"], severity)


class TestOneTableSchema(unittest.TestCase):
    """Both emitters must render the same 8 columns, `Sources` included.

    `--layered` renders through `emit_layer` and writes the same
    `docs/failure-patterns.md`. A Sources-less table there made
    `parse_existing` set `_sources_recorded=False`, so the next `merge()`
    computed `unattributed = 0` and replaced every stored count with
    `len(sources)` — the count collapse, one flag away.
    """

    @staticmethod
    def _patterns() -> dict[tuple[str, str, str], dict]:
        key = ("qcloud-layer-ops", "tccli cvm Run", "InvalidParameter: bad")
        return {
            key: {
                "category": "runtime",
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "fix": "fix",
                "count": 6,
                "last_seen": "2026-09",
                "severity": "major",
                "sources": {f"gcl-trace-{n}.json" for n in "abcdef"},
            }
        }

    def test_both_emitters_declare_the_same_columns(self):
        store = fpe._emit_store(self._patterns())
        layer = fpe.emit_layer(self._patterns(), "Hot Layer")
        self.assertEqual(
            [ln for ln in store if ln.startswith("| Skill")],
            [ln for ln in layer if ln.startswith("| Skill")],
        )
        self.assertTrue(any("| Sources |" in ln for ln in layer))

    def test_layered_write_leaves_the_count_intact_on_the_next_merge(self):
        patterns = self._patterns()
        key = next(iter(patterns))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failure-patterns.md"
            fpe.save_layer(path, patterns, "Hot Layer")
            reobserved = {**patterns[key], "_source": "gcl-trace-g.json"}
            merged = fpe.merge(fpe.parse_existing(path), [reobserved])

        self.assertEqual(
            merged[key]["count"], 7, "6 stored sources + 1 new observation, not len(sources)"
        )
        self.assertEqual(len(merged[key]["sources"]), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
