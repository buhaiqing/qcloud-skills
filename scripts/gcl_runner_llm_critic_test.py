#!/usr/bin/env python3
"""Tests for llm_critic() — Phase 1 module 1.1.

TDD: written before llm_critic() implementation. Mock-based; no real API.
Run: cd scripts && python3 -m unittest gcl_runner_llm_critic_test -v
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

# Tests reference internal helpers; import will fail until llm_critic exists.
from gcl_runner import (
    _build_llm_config,
    _parse_llm_response,
    llm_critic,
)


def _ok_payload(scores: dict | None = None) -> dict:
    return {
        "scores": scores or {"correctness": 1, "safety": 1, "idempotency": 1,
                             "traceability": 1, "spec_compliance": 1},
        "suggestions": ["looks good"],
        "blocking": False,
    }


def _generator() -> dict:
    return {
        "command": "tccli cvm DescribeInstances --Region ap-guangzhou",
        "exit_code": 0,
        "result_excerpt": "{\"Response\": {\"InstanceSet\": []}}",
        "duration_ms": 234,
    }


class BuildLLMConfigTest(unittest.TestCase):
    """_build_llm_config reads from env vars with explicit error messages."""

    def test_returns_none_when_env_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = _build_llm_config()
        self.assertIsNone(cfg)

    def test_returns_config_when_env_present(self):
        env = {
            "GCL_LLM_API_KEY": "sk-test-xxx",
            "GCL_LLM_BASE_URL": "https://api.example.com/v1",
            "GCL_LLM_MODEL": "gpt-4o-mini",
            "GCL_LLM_TIMEOUT": "60",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = _build_llm_config()
        self.assertEqual(cfg["api_key"], "sk-test-xxx")
        self.assertEqual(cfg["base_url"], "https://api.example.com/v1")
        self.assertEqual(cfg["model"], "gpt-4o-mini")
        self.assertEqual(cfg["timeout"], 60)

    def test_default_model_when_env_missing_model(self):
        env = {
            "GCL_LLM_API_KEY": "sk-test",
            "GCL_LLM_BASE_URL": "https://api.example.com/v1",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = _build_llm_config()
        self.assertEqual(cfg["model"], "gpt-4o-mini")

    def test_invalid_timeout_falls_back_to_default(self):
        env = {
            "GCL_LLM_API_KEY": "sk-test",
            "GCL_LLM_BASE_URL": "https://api.example.com/v1",
            "GCL_LLM_TIMEOUT": "not-a-number",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = _build_llm_config()
        self.assertEqual(cfg["timeout"], 120)


class ParseLLMResponseTest(unittest.TestCase):
    """_parse_llm_response extracts JSON from model output."""

    def test_parse_clean_json(self):
        body = json.dumps(_ok_payload())
        parsed = _parse_llm_response(body)
        self.assertEqual(parsed["scores"]["correctness"], 1)
        self.assertEqual(parsed["_mode"], "llm-builtin")

    def test_parse_json_in_code_fence(self):
        body = "```json\n" + json.dumps(_ok_payload()) + "\n```"
        parsed = _parse_llm_response(body)
        self.assertEqual(parsed["scores"]["safety"], 1)

    def test_parse_json_with_prose_prefix(self):
        body = "Here is my critique:\n" + json.dumps(_ok_payload())
        parsed = _parse_llm_response(body)
        self.assertEqual(parsed["scores"]["correctness"], 1)

    def test_parse_malformed_raises(self):
        with self.assertRaises(ValueError):
            _parse_llm_response("not json at all")


class LLMCRITICTest(unittest.TestCase):
    """llm_critic() — main LLM-based scoring path."""

    def test_llm_critic_normal_response(self):
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        fake_body = json.dumps(_ok_payload())
        with mock.patch("gcl_runner._call_llm_chat", return_value=fake_body):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="rubric",
                                prompt_template="template",
                                llm_config=cfg)
        self.assertEqual(result["scores"]["correctness"], 1)
        self.assertEqual(result["_mode"], "llm-builtin")
        self.assertFalse(result["blocking"])

    def test_llm_critic_safety_zero_returns_blocking(self):
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        payload = _ok_payload({"correctness": 1, "safety": 0, "idempotency": 1,
                               "traceability": 1, "spec_compliance": 1})
        payload["blocking"] = True
        fake_body = json.dumps(payload)
        with mock.patch("gcl_runner._call_llm_chat", return_value=fake_body):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="rubric",
                                prompt_template="template",
                                llm_config=cfg)
        self.assertEqual(result["scores"]["safety"], 0)
        self.assertTrue(result["blocking"])

    def test_llm_critic_malformed_falls_back_to_structural(self):
        """When LLM returns malformed JSON, fall back to structural_critic."""
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        with mock.patch("gcl_runner._call_llm_chat", return_value="not valid json"):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="rubric",
                                prompt_template="template",
                                llm_config=cfg)
        self.assertEqual(result["_mode"], "structural-only-fallback")
        # structural fallback must still satisfy validate_critic_payload shape
        self.assertIn("scores", result)
        self.assertIn("suggestions", result)
        self.assertIn("blocking", result)

    def test_llm_critic_timeout_falls_back_to_structural(self):
        """When LLM call times out, fall back to structural_critic."""
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        with mock.patch("gcl_runner._call_llm_chat",
                        side_effect=TimeoutError("LLM request timed out")):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="rubric",
                                prompt_template="template",
                                llm_config=cfg)
        self.assertEqual(result["_mode"], "structural-only-fallback")

    def test_llm_critic_retries_once_then_falls_back(self):
        """On first failure, retry once; on second failure, fall back."""
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        call_count = {"n": 0}

        def flaky(_cfg, _system, _user):
            call_count["n"] += 1
            raise TimeoutError("flaky")

        with mock.patch("gcl_runner._call_llm_chat", side_effect=flaky):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="r",
                                prompt_template="t",
                                llm_config=cfg)
        self.assertEqual(result["_mode"], "structural-only-fallback")
        self.assertEqual(call_count["n"], 2, "should have retried exactly once")

    def test_llm_critic_prompt_includes_rubric_and_generator(self):
        cfg = {"api_key": "sk-x", "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        captured: dict = {}

        def capture(_cfg, system, user):
            captured["system"] = system
            captured["user"] = user
            return json.dumps(_ok_payload())

        with mock.patch("gcl_runner._call_llm_chat", side_effect=capture):
            llm_critic(_generator(), "qcloud-cvm-ops",
                       rubric_text="RUBRIC_TEXT_HERE",
                       prompt_template="TEMPLATE_TEXT_HERE",
                       llm_config=cfg)
        self.assertIn("RUBRIC_TEXT_HERE", captured["system"])
        self.assertIn("TEMPLATE_TEXT_HERE", captured["system"])
        # Generator command must appear in user message
        self.assertIn("tccli cvm DescribeInstances", captured["user"])

    def test_llm_critic_does_not_leak_api_key(self):
        """API key must NOT appear in any returned payload or log output."""
        cfg = {"api_key": "sk-secret-DO-NOT-LEAK",
               "base_url": "https://api.example.com/v1",
               "model": "gpt-4o-mini", "timeout": 30}
        fake_body = json.dumps(_ok_payload())
        with mock.patch("gcl_runner._call_llm_chat", return_value=fake_body):
            result = llm_critic(_generator(), "qcloud-cvm-ops",
                                rubric_text="r", prompt_template="t",
                                llm_config=cfg)
        self.assertNotIn("sk-secret-DO-NOT-LEAK", json.dumps(result))
        # Also check the suggested suggestions don't leak
        for s in result.get("suggestions", []):
            self.assertNotIn("sk-secret", s)


if __name__ == "__main__":
    unittest.main()