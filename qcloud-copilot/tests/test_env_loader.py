"""Tests for .env auto-load (CI mode LLM config)."""

from __future__ import annotations

import os
from pathlib import Path

from copilot.env_loader import load_project_dotenv
from copilot.llm_reasoner import load_llm_config_from_env
from copilot.mode_resolver import resolve_inspection_mode


def test_load_project_dotenv_copilot_prefixes(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "COPILOT_LLM_REASONING=1",
                "COPILOT_LLM_API_KEY=sk-from-dotenv",
                "COPILOT_LLM_BASE_URL=https://api.deepseek.com/v1",
                "COPILOT_LLM_MODEL=deepseek-chat",
                "COPILOT_INSPECTION_MODE=auto",
                "OTHER_SECRET=ignored",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "COPILOT_LLM_REASONING",
        "COPILOT_LLM_API_KEY",
        "COPILOT_LLM_BASE_URL",
        "COPILOT_LLM_MODEL",
        "OTHER_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)

    load_project_dotenv(env_path=env_file, force=True)

    assert os.environ.get("COPILOT_LLM_REASONING") == "1"
    assert os.environ.get("COPILOT_LLM_API_KEY") == "sk-from-dotenv"
    assert os.environ.get("COPILOT_LLM_BASE_URL") == "https://api.deepseek.com/v1"
    assert os.environ.get("OTHER_SECRET") is None

    cfg = load_llm_config_from_env()
    assert cfg is not None
    assert cfg.model == "deepseek-chat"


def test_shell_env_wins_over_dotenv(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("COPILOT_LLM_REASONING=1\n", encoding="utf-8")
    monkeypatch.setenv("COPILOT_LLM_REASONING", "0")
    load_project_dotenv(env_path=env_file, force=True)
    assert os.environ.get("COPILOT_LLM_REASONING") == "0"


def test_ci_mode_reads_dotenv_llm_gate(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "COPILOT_LLM_REASONING=1\nCOPILOT_LLM_API_KEY=sk-x\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("COPILOT_LLM_REASONING", raising=False)
    monkeypatch.delenv("COPILOT_LLM_API_KEY", raising=False)
    load_project_dotenv(env_path=env_file, force=True)

    result = resolve_inspection_mode("[CI模式] 朔州天源 无人值守巡检")
    assert result.effective == "ci"
    assert result.decision_maker == "llm_reasoner_v1"
