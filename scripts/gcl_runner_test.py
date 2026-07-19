#!/usr/bin/env python3
"""Unit tests for scripts/gcl_runner.py (GCL Orchestrator).

Pure stdlib — no external dependencies. Run with:
    python3 -m unittest scripts.gcl_runner_test -v

Covers:
- mask_secrets / has_credential_leak
- run_command (success, failure, timeout, secret-masking)
- structural_critic (each rubric dimension + blocking flag)
- load_critic (file, stdin, none)
- validate_critic_payload (each failure mode)
- decide (PASS / RETRY / SAFETY_FAIL branches)
- persist_trace (file written, JSON parseable)
- cmd_run end-to-end (PASS, SAFETY_FAIL, MAX_ITER, --structural-critic-only)
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure scripts/ is on sys.path when invoked as `python3 scripts/gcl_runner_test.py`
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import gcl_runner  # noqa: E402


def quiet_cmd_run(ns) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return gcl_runner.cmd_run(ns)


class SecretMaskingTests(unittest.TestCase):
    def test_mask_secret_key(self) -> None:
        out = gcl_runner.mask_secrets("SecretKey=AKID1234567890abcdefghij")
        self.assertIn("SecretKey=<masked>", out)
        self.assertNotIn("AKID1234567890abcdefghij", out)

    def test_mask_tencentcloud_secret_key(self) -> None:
        out = gcl_runner.mask_secrets("TENCENTCLOUD_SECRET_KEY=supersecretvalue")
        self.assertIn("TENCENTCLOUD_SECRET_KEY=<masked>", out)

    def test_has_credential_leak_akid(self) -> None:
        self.assertTrue(gcl_runner.has_credential_leak("AKIDABCDEFGHIJKLMNOPQRSTUV"))
        self.assertFalse(gcl_runner.has_credential_leak("AKIDshort"))

    def test_no_leak_when_clean(self) -> None:
        self.assertFalse(gcl_runner.has_credential_leak('{"Response":{"RequestId":"abc"}}'))

    def test_no_leak_when_already_masked(self) -> None:
        self.assertFalse(gcl_runner.has_credential_leak("SecretKey=<masked>"))


class RunCommandTests(unittest.TestCase):
    def test_success(self) -> None:
        result = gcl_runner.run_command('echo "hello world"')
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello world", result["result_excerpt"])
        self.assertEqual(result["stdout_len"], len("hello world\n"))

    def test_failure_exit_code(self) -> None:
        result = gcl_runner.run_command("exit 7")
        self.assertEqual(result["exit_code"], 7)

    def test_stderr_captured(self) -> None:
        result = gcl_runner.run_command('echo "err" 1>&2')
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("err", result["result_excerpt"])

    def test_timeout(self) -> None:
        result = gcl_runner.run_command("sleep 5", timeout=1)
        self.assertEqual(result["exit_code"], -1)
        self.assertIn("TIMEOUT", result["result_excerpt"])

    def test_command_secret_masked(self) -> None:
        result = gcl_runner.run_command('echo "TENCENTCLOUD_SECRET_KEY=shouldnotappear"')
        self.assertIn("<masked>", result["command"])
        self.assertNotIn("shouldnotappear", result["command"])


class StructuralCriticTests(unittest.TestCase):
    def test_passes_clean_run(self) -> None:
        gen = {"exit_code": 0, "result_excerpt": '{"Response":{"RequestId":"x"}}', "command": "tccli foo bar"}
        c = gcl_runner.structural_critic(gen)
        self.assertEqual(c["scores"]["correctness"], 1.0)
        self.assertEqual(c["scores"]["safety"], 1.0)
        self.assertEqual(c["scores"]["spec_compliance"], 1.0)
        self.assertFalse(c["blocking"])
        self.assertEqual(c["_mode"], "structural-only")

    def test_fails_on_nonzero_exit(self) -> None:
        gen = {"exit_code": 1, "result_excerpt": "some error", "command": "tccli foo bar"}
        c = gcl_runner.structural_critic(gen)
        self.assertEqual(c["scores"]["correctness"], 0.0)
        self.assertTrue(c["blocking"])

    def test_fails_on_credential_leak(self) -> None:
        gen = {
            "exit_code": 0,
            "result_excerpt": "leaked AKIDABCDEFGHIJKLMNOPQRSTUV",
            "command": "tccli foo bar",
        }
        c = gcl_runner.structural_critic(gen)
        self.assertEqual(c["scores"]["safety"], 0.0)
        self.assertTrue(c["blocking"])

    def test_traceability_low_on_empty_output(self) -> None:
        gen = {"exit_code": 0, "result_excerpt": "", "command": "tccli foo"}
        c = gcl_runner.structural_critic(gen)
        self.assertEqual(c["scores"]["traceability"], 0.5)


class LoadCriticTests(unittest.TestCase):
    def test_load_from_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}, "suggestions": [], "blocking": False}, f)
            f.flush()
            path = Path(f.name)
        try:
            critic = gcl_runner.load_critic(path, stdin=False)
            self.assertEqual(critic["scores"]["correctness"], 1)
        finally:
            path.unlink()

    def test_load_none_when_no_input(self) -> None:
        self.assertIsNone(gcl_runner.load_critic(None, stdin=False))


class ValidateCriticPayloadTests(unittest.TestCase):
    def _ok(self) -> dict:
        return {
            "scores": {
                "correctness": 1, "safety": 1, "idempotency": 1,
                "traceability": 1, "spec_compliance": 1,
            },
            "suggestions": [],
            "blocking": False,
        }

    def test_valid_payload(self) -> None:
        self.assertEqual(gcl_runner.validate_critic_payload(self._ok()), [])

    def test_missing_scores(self) -> None:
        errs = gcl_runner.validate_critic_payload({"suggestions": [], "blocking": False})
        self.assertTrue(any("scores" in e for e in errs))

    def test_missing_dimension(self) -> None:
        p = self._ok()
        del p["scores"]["safety"]
        errs = gcl_runner.validate_critic_payload(p)
        self.assertTrue(any("safety" in e for e in errs))

    def test_invalid_score_value(self) -> None:
        p = self._ok()
        p["scores"]["correctness"] = 0.7
        errs = gcl_runner.validate_critic_payload(p)
        self.assertTrue(any("correctness" in e for e in errs))

    def test_missing_suggestions(self) -> None:
        p = self._ok()
        del p["suggestions"]
        errs = gcl_runner.validate_critic_payload(p)
        self.assertTrue(any("suggestions" in e for e in errs))

    def test_missing_blocking(self) -> None:
        p = self._ok()
        del p["blocking"]
        errs = gcl_runner.validate_critic_payload(p)
        self.assertTrue(any("blocking" in e for e in errs))


class DecideTests(unittest.TestCase):
    def test_pass_when_all_at_threshold(self) -> None:
        scores = {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}
        self.assertEqual(gcl_runner.decide(scores), "PASS")

    def test_retry_when_below_threshold(self) -> None:
        scores = {"correctness": 0.5, "safety": 1, "idempotency": 0, "traceability": 1, "spec_compliance": 1}
        self.assertEqual(gcl_runner.decide(scores), "RETRY")

    def test_safety_fail_overrides(self) -> None:
        scores = {"correctness": 1, "safety": 0, "idempotency": 1, "traceability": 1, "spec_compliance": 1}
        self.assertEqual(gcl_runner.decide(scores), "SAFETY_FAIL")


class PersistTraceTests(unittest.TestCase):
    def test_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace = {"skill": "test", "final": {"status": "PASS"}}
            path = gcl_runner.persist_trace(root, trace)
            self.assertTrue(path.exists())
            self.assertTrue(str(path).endswith(".json"))
            self.assertEqual(json.loads(path.read_text())["skill"], "test")


class FailurePatternTests(unittest.TestCase):
    def test_cli_parameter(self) -> None:
        gen = {"exit_code": 1, "result_excerpt": "InvalidParameter: bad zone", "command": "tccli cvm DescribeInstances"}
        critic = {"scores": {"correctness": 0, "safety": 1, "idempotency": 0.5, "traceability": 1, "spec_compliance": 0.5}, "suggestions": ["use --Zone ap-guangzhou-2"], "blocking": True}
        fp = gcl_runner.extract_failure_pattern("qcloud-cvm-ops", gen["command"], gen, critic)
        self.assertIsNotNone(fp)
        self.assertEqual(fp["category"], "cli_parameter")
        self.assertEqual(fp["skill"], "qcloud-cvm-ops")
        self.assertIn("InvalidParameter", fp["error"])

    def test_runtime_timeout(self) -> None:
        gen = {"exit_code": -1, "result_excerpt": "TIMEOUT after 120s", "command": "tccli cdb CreateDBInstance"}
        critic = {"scores": {"correctness": 0, "safety": 1, "idempotency": 0.5, "traceability": 0.5, "spec_compliance": 0.5}, "suggestions": ["increase timeout"], "blocking": True}
        fp = gcl_runner.extract_failure_pattern("qcloud-cdb-ops", gen["command"], gen, critic)
        self.assertIsNotNone(fp)
        self.assertEqual(fp["category"], "runtime")

    def test_no_pattern_when_clean(self) -> None:
        gen = {"exit_code": 0, "result_excerpt": "all good", "command": "tccli cvm DescribeInstances"}
        critic = {"scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}, "suggestions": [], "blocking": False}
        fp = gcl_runner.extract_failure_pattern("qcloud-cvm-ops", gen["command"], gen, critic)
        self.assertIsNone(fp)

    def test_failure_pattern_in_max_iter_trace(self) -> None:
        critic = {
            "scores": {"correctness": 1, "safety": 1, "idempotency": 0, "traceability": 1, "spec_compliance": 1},
            "suggestions": ["set ClientToken"],
            "blocking": True,
        }
        tmp = Path(tempfile.mkdtemp())
        critic_file = tmp / "critic.json"
        critic_file.write_text(json.dumps(critic))
        # Inject a recognizable error string via a command that returns it
        ns = gcl_runner.build_parser().parse_args([
            "run",
            "--root", str(tmp),
            "--skill", "qcloud-test-ops",
            "--request", "test",
            "--command", "echo 'InvalidParameter: bad token'",
            "--max-iter", "2",
            "--critic-json", str(critic_file),
        ])
        rc = quiet_cmd_run(ns)
        self.assertEqual(rc, 1)
        trace_files = list((tmp / "audit-results").glob("gcl-trace-*.json"))
        data = json.loads(trace_files[0].read_text())
        self.assertIn("failure_pattern", data["final"])
        fp = data["final"]["failure_pattern"]
        self.assertIsNotNone(fp)
        self.assertEqual(fp["category"], "cli_parameter")


class CmdRunEndToEndTests(unittest.TestCase):
    def _run(self, critic_payload: dict | None, structural: bool = False, max_iter: int = 2) -> tuple[int, Path]:
        """Helper to invoke cmd_run with a temp root."""
        tmp = Path(tempfile.mkdtemp())
        critic_file: Path | None = None
        args = [
            "run",
            "--root", str(tmp),
            "--skill", "qcloud-test-ops",
            "--request", "test",
            "--command", 'echo "ok"',
            "--max-iter", str(max_iter),
        ]
        if structural:
            args.append("--structural-critic-only")
        if critic_payload is not None:
            critic_file = tmp / "critic.json"
            critic_file.write_text(json.dumps(critic_payload))
            args.extend(["--critic-json", str(critic_file)])
        ns = gcl_runner.build_parser().parse_args(args)
        rc = quiet_cmd_run(ns)
        return rc, tmp

    def test_structural_pass(self) -> None:
        rc, root = self._run(critic_payload=None, structural=True, max_iter=1)
        self.assertEqual(rc, 0)
        trace_files = list((root / "audit-results").glob("gcl-trace-*.json"))
        self.assertEqual(len(trace_files), 1)
        data = json.loads(trace_files[0].read_text())
        self.assertEqual(data["final"]["status"], "PASS")

    def test_external_critic_pass(self) -> None:
        critic = {
            "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
            "suggestions": [],
            "blocking": False,
        }
        rc, root = self._run(critic_payload=critic)
        self.assertEqual(rc, 0)

    def test_external_critic_safety_fail(self) -> None:
        critic = {
            "scores": {"correctness": 1, "safety": 0, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
            "suggestions": ["fix"],
            "blocking": True,
        }
        rc, root = self._run(critic_payload=critic)
        self.assertEqual(rc, 3)  # SAFETY_FAIL exit code

    def test_external_critic_max_iter(self) -> None:
        # Critic keeps giving idempotency=0 → never passes → MAX_ITER
        critic = {
            "scores": {"correctness": 1, "safety": 1, "idempotency": 0, "traceability": 1, "spec_compliance": 1},
            "suggestions": ["set ClientToken"],
            "blocking": True,
        }
        rc, root = self._run(critic_payload=critic, max_iter=2)
        self.assertEqual(rc, 1)  # MAX_ITER exit code
        trace_files = list((root / "audit-results").glob("gcl-trace-*.json"))
        data = json.loads(trace_files[0].read_text())
        self.assertEqual(data["final"]["status"], "MAX_ITER")
        self.assertIn("idempotency", data["final"].get("unresolved", []))

    def test_invalid_critic_exits_2(self) -> None:
        # Critic missing blocking → validation fails
        critic = {
            "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
            "suggestions": [],
        }
        rc, root = self._run(critic_payload=critic)
        self.assertEqual(rc, 2)



class TCloudErrorHintsTests(unittest.TestCase):
    """Tests for load_tcloud_error_hints and load_error_code_map."""

    def test_load_error_code_map_returns_dict(self) -> None:
        result = gcl_runner.load_error_code_map()
        self.assertIsInstance(result, dict)

    def test_load_error_code_map_contains_expected_keys(self) -> None:
        result = gcl_runner.load_error_code_map()
        # Should contain the known error codes from tcloud_error_codes
        self.assertIn("AuthFailure", result)
        self.assertIn("InvalidParameter", result)
        self.assertIn("RequestLimitExceeded", result)

    def test_load_error_code_map_has_required_fields(self) -> None:
        result = gcl_runner.load_error_code_map()
        if result:  # only test if module loaded
            for code, info in result.items():
                self.assertIn("category", info)
                self.assertIn("fix", info)

    def test_load_tcloud_error_hints_returns_string(self) -> None:
        result = gcl_runner.load_tcloud_error_hints()
        self.assertIsInstance(result, str)

    def test_load_tcloud_error_hints_contains_header(self) -> None:
        result = gcl_runner.load_tcloud_error_hints()
        self.assertIn("Tencent Cloud Error Code Reference", result)

    def test_load_tcloud_error_hints_contains_authfailure(self) -> None:
        result = gcl_runner.load_tcloud_error_hints()
        self.assertIn("AuthFailure", result)

    def test_load_tcloud_error_hints_contains_markdown_format(self) -> None:
        result = gcl_runner.load_tcloud_error_hints()
        # Should be markdown-formatted with backtick code spans and category/fix
        self.assertIn("`", result)  # backtick code span is in the output


class StructuralCriticErrorCodeTests(unittest.TestCase):
    """Tests for structural_critic error-code awareness."""

    def test_nonzero_exit_with_known_error_code_suggests_specific_fix(self) -> None:
        # When the error code is present in the excerpt, structural_critic
        # should use the specific fix from _error_code_map
        gen = {
            "exit_code": 1,
            "result_excerpt": '{"Response":{"Error":{"Code":"AuthFailure","Message":"Invalid credential"}}}',
            "command": "tccli cvm DescribeInstances",
            "_error_code_map": {
                "AuthFailure": {"severity": "major", "category": "auth", "fix": "Check SecretId/Key and CAM policy"},
            },
        }
        c = gcl_runner.structural_critic(gen)
        self.assertEqual(c["scores"]["correctness"], 0.0)
        # Should contain specific AuthFailure guidance, not generic message
        suggestions_text = " ".join(c["suggestions"])
        self.assertIn("AuthFailure", suggestions_text)
        self.assertIn("auth", suggestions_text)

    def test_nonzero_exit_with_unknown_code_falls_back_to_generic(self) -> None:
        gen = {
            "exit_code": 1,
            "result_excerpt": "some completely unknown error",
            "command": "tccli cvm DescribeInstances",
            "_error_code_map": {
                "AuthFailure": {"severity": "major", "category": "auth", "fix": "Check SecretId/Key"},
            },
        }
        c = gcl_runner.structural_critic(gen)
        suggestions_text = " ".join(c["suggestions"])
        # Should fall back to generic message
        self.assertIn("fix command or credentials", suggestions_text)

    def test_nonzero_exit_code_in_cmd_matches_error_code(self) -> None:
        # Error code can appear in the command string too
        gen = {
            "exit_code": 1,
            "result_excerpt": "Operation failed",
            "command": "tccli cvm DescribeInstances  # RequestLimitExceeded triggered",
            "_error_code_map": {
                "RequestLimitExceeded": {"severity": "major", "category": "rate_limit", "fix": "Reduce request frequency"},
            },
        }
        c = gcl_runner.structural_critic(gen)
        suggestions_text = " ".join(c["suggestions"])
        self.assertIn("RequestLimitExceeded", suggestions_text)
        self.assertIn("rate_limit", suggestions_text)

    def test_generator_dict_gets_error_hints_in_cmd_run(self) -> None:
        # End-to-end: generator dict should carry error_code_hints and _error_code_map
        # after run_command in cmd_run
        ns = argparse.Namespace(
            skill="qcloud-cvm-ops",
            request="test",
            command="echo ok",
            root=Path(tempfile.gettempdir()),
            max_iter=1,
            timeout=10,
            critic_json=None,
            critic_stdin=False,
            structural_critic_only=True,
            trace_id=None,
            enable_post_process=False,
            no_post_process=True,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            gcl_runner.cmd_run(ns)
        # Read the trace and verify generator has error hints
        trace_files = list((ns.root / "audit-results").glob("gcl-trace-*.json"))
        self.assertTrue(len(trace_files) >= 1)
        trace_data = json.loads(trace_files[-1].read_text())
        gen = trace_data["iterations"][0]["generator"]
        self.assertIn("error_code_hints", gen)
        self.assertIsInstance(gen["error_code_hints"], str)
        self.assertIn("_error_code_map", gen)
        self.assertIsInstance(gen["_error_code_map"], dict)



if __name__ == "__main__":
    unittest.main()