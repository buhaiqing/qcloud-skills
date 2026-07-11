"""Tests for proactive-inspection .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from lib.env_loader import load_project_dotenv


def test_load_project_dotenv_tencentcloud_prefixes(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "TENCENTCLOUD_SECRET_ID=AKID-from-dotenv",
                "TENCENTCLOUD_REGION=ap-shanghai",
                "COPILOT_CUSTOMER_TAG_KEY=customer",
                "UNRELATED=ignored",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "TENCENTCLOUD_SECRET_ID",
        "TENCENTCLOUD_REGION",
        "COPILOT_CUSTOMER_TAG_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    load_project_dotenv(env_path=env_file, force=True)

    assert os.environ.get("TENCENTCLOUD_SECRET_ID") == "AKID-from-dotenv"
    assert os.environ.get("TENCENTCLOUD_REGION") == "ap-shanghai"
    assert os.environ.get("COPILOT_CUSTOMER_TAG_KEY") == "customer"
    assert os.environ.get("UNRELATED") is None


def test_shell_env_wins_over_dotenv(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TENCENTCLOUD_REGION=ap-shanghai\n", encoding="utf-8")
    monkeypatch.setenv("TENCENTCLOUD_REGION", "ap-guangzhou")
    load_project_dotenv(env_path=env_file, force=True)
    assert os.environ.get("TENCENTCLOUD_REGION") == "ap-guangzhou"
