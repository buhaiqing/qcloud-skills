"""CLI plan mode tests (P2-T2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from copilot.cli import app
from copilot.models import Report, ReportSection

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"
runner = CliRunner()


def test_plan_dry_run_lists_step_order():
    result = runner.invoke(
        app,
        [
            "plan",
            "--plan",
            str(FIXTURE),
            "--session",
            "ses-cli-dry",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "vpc-0" in result.stdout
    assert "cruise-1" in result.stdout
    assert "alert-2" in result.stdout
    assert "report-3" in result.stdout


def test_plan_execution_mocked():
    mock_report = Report(
        title="Mock Plan Report",
        summary="ok",
        sections=[ReportSection(title="OK", severity="info", findings=["done"])],
        report_path="/tmp/mock-report.md",
    )
    with patch("copilot.cli.CopilotEngine") as mock_engine:
        mock_engine.return_value.run_plan.return_value = mock_report
        result = runner.invoke(
            app,
            [
                "plan",
                "--plan",
                str(FIXTURE),
                "--session",
                "ses-cli-run",
            ],
        )
    assert result.exit_code == 0
    assert "Mock Plan Report" in result.stdout
    assert "Report saved:" in result.stdout
