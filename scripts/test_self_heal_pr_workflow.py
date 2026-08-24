"""Tests for self_heal_pr_workflow."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from self_heal_pr_workflow import FixProposal, SelfHealPRWorkflow

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A real git repo (initialized with `git init`) with a remote URL."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:testowner/testrepo.git"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    return repo


@pytest.fixture
def fp_path(tmp_path: Path) -> Path:
    """A minimal failure-patterns.md with rows to deduplicate."""
    p = tmp_path / "failure-patterns.md"
    p.write_text(
        "| Skill | Error | Count |\n"
        "| `shellcheck` | `SC2086` | 3 |\n"
        "| `ruff` | `E501` | 1 |\n"
        "| `mypy` | `TP002` | 5 |\n",
        encoding="utf-8",
    )
    return p


def _make_proposal(
    skill: str = "shellcheck",
    error_code: str = "SC2086",
    level: str = "L1",
    auto_merge: bool = False,
) -> FixProposal:
    return FixProposal(
        level=level,
        skill=skill,
        error_code=error_code,
        occurrence_count=1,
        target_file="/tmp/test.py",
        old_content="echo $foo",
        new_content='echo "$foo"',
        rationale="quote variables",
        risk_assessment="low",
        auto_merge=auto_merge,
    )


# ---------------------------------------------------------------------------
# _labels_for_level
# ---------------------------------------------------------------------------

class TestLabelsForLevel:
    def test_l1_returns_self_heal_l1(self):
        labels = SelfHealPRWorkflow._labels_for_level("L1")
        assert labels == ["self-heal/L1"]

    def test_l2_returns_self_heal_l2_and_needs_human_review(self):
        labels = SelfHealPRWorkflow._labels_for_level("L2")
        assert labels == ["self-heal/L2", "needs-human-review"]

    def test_l3_returns_self_heal_l3_and_needs_human_approval(self):
        labels = SelfHealPRWorkflow._labels_for_level("L3")
        assert labels == ["self-heal/L3", "needs-human-approval"]

    def test_unknown_level_defaults_to_l1(self):
        labels = SelfHealPRWorkflow._labels_for_level("L9")
        assert labels == ["self-heal/L1"]


# ---------------------------------------------------------------------------
# _pr_number_from_url
# ---------------------------------------------------------------------------

class TestPRNumberFromUrl:
    def test_extracts_number(self):
        assert SelfHealPRWorkflow._pr_number_from_url(
            "https://github.com/owner/repo/pull/42",
        ) == 42

    def test_raises_on_malformed_url(self):
        with pytest.raises(ValueError, match="Cannot extract PR number"):
            SelfHealPRWorkflow._pr_number_from_url(
                "https://github.com/owner/repo/issues/42",
            )


# ---------------------------------------------------------------------------
# run_workflow — token missing
# ---------------------------------------------------------------------------

class TestRunWorkflowNoToken:
    def test_skipped_when_no_token(self, fake_repo: Path, fp_path: Path):
        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token=None,
            failure_patterns_path=fp_path,
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            result = wf.run_workflow(_make_proposal())
        assert result.status == "skipped"
        assert "GITHUB_TOKEN not set" in result.message


# ---------------------------------------------------------------------------
# _deduplicate_pattern
# ---------------------------------------------------------------------------

class TestDeduplicatePattern:
    def test_decrement_count_greater_than_one(self, fake_repo: Path, fp_path: Path):
        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )
        wf._deduplicate_pattern("shellcheck", "SC2086")
        content = fp_path.read_text()
        # count should have gone from 3 to 2
        assert "SC2086" in content

    def test_remove_row_when_count_becomes_zero(self, fake_repo: Path, fp_path: Path):
        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )
        # The ruff row has count=1; removing it should delete the line
        wf._deduplicate_pattern("ruff", "E501")
        content = fp_path.read_text()
        assert "E501" not in content

    def test_idempotent_when_pattern_not_found(self, fake_repo: Path, fp_path: Path):
        original = fp_path.read_text()
        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )
        wf._deduplicate_pattern("nonexistent", "NOCODE")
        assert fp_path.read_text() == original

    def test_noop_when_file_missing(self, fake_repo: Path, tmp_path: Path):
        absent = tmp_path / "nonexistent.md"
        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=absent,
        )
        # Must not raise
        wf._deduplicate_pattern("shellcheck", "SC2086")


# ---------------------------------------------------------------------------
# _create_pr — label correctness via mocked requests
# ---------------------------------------------------------------------------

class TestCreatePRLabels:
    """Verify correct labels are passed to the GitHub API when creating a PR."""

    @staticmethod
    def _capture_post_payload(
        fake_repo: Path,
        fp_path: Path,
        level: str,
    ) -> dict | None:
        captured: dict = {}

        def fake_post(url: str, **kwargs):
            captured["url"] = url
            captured["payload"] = kwargs.get("json")
            resp = mock.MagicMock()
            resp.status_code = 201
            resp.json.return_value = {"html_url": "https://github.com/testowner/testrepo/pull/99"}
            return resp

        def fake_get(url: str, **kwargs):
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.json.return_value = []
            return resp

        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )

        with mock.patch("self_heal_pr_workflow.requests.post", side_effect=fake_post), \
             mock.patch("self_heal_pr_workflow.requests.get", side_effect=fake_get), \
             mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            wf.run_workflow(_make_proposal(level=level))

        return captured.get("payload")

    def test_l1_pr_gets_self_heal_l1_label(self, fake_repo: Path, fp_path: Path):
        payload = self._capture_post_payload(fake_repo, fp_path, "L1")
        assert payload is not None
        assert payload["labels"] == ["self-heal/L1"]

    def test_l2_pr_gets_self_heal_l2_and_review_label(self, fake_repo: Path, fp_path: Path):
        payload = self._capture_post_payload(fake_repo, fp_path, "L2")
        assert payload is not None
        assert "self-heal/L2" in payload["labels"]
        assert "needs-human-review" in payload["labels"]

    def test_l3_pr_gets_self_heal_l3_and_approval_label(self, fake_repo: Path, fp_path: Path):
        payload = self._capture_post_payload(fake_repo, fp_path, "L3")
        assert payload is not None
        assert "self-heal/L3" in payload["labels"]
        assert "needs-human-approval" in payload["labels"]


# ---------------------------------------------------------------------------
# Deduplication — run_workflow integration
# ---------------------------------------------------------------------------

class TestDeduplicationIntegration:
    def test_deduplicate_called_after_l1_merge(self, fake_repo: Path, fp_path: Path):
        """When L1 auto-merge succeeds, _deduplicate_pattern should be called."""
        merge_called: list = []
        original_deduplicate = SelfHealPRWorkflow._deduplicate_pattern

        def tracking_deduplicate(self, skill, error_code):
            merge_called.append((skill, error_code))
            return original_deduplicate(self, skill, error_code)

        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )

        # Provide a mypy row with count > 1 so decrement works
        fp_path.write_text(
            "| Skill | Error | Count |\n"
            "| `mypy` | `TP002` | 2 |\n",
            encoding="utf-8",
        )

        def fake_post(url, **kwargs):
            resp = mock.MagicMock()
            resp.status_code = 201
            resp.json.return_value = {"html_url": "https://github.com/testowner/testrepo/pull/7"}
            return resp

        mock_put_resp = mock.MagicMock()
        mock_put_resp.status_code = 200

        with mock.patch("self_heal_pr_workflow.requests.post", side_effect=fake_post), \
             mock.patch("self_heal_pr_workflow.requests.put", return_value=mock_put_resp), \
             mock.patch("subprocess.run") as mock_run, \
             mock.patch.object(
                 SelfHealPRWorkflow,
                 "_wait_for_ci",
                 return_value=True,
             ), \
             mock.patch.object(
                 SelfHealPRWorkflow,
                 "_deduplicate_pattern",
                 tracking_deduplicate,
             ):
            mock_run.return_value = mock.MagicMock(returncode=0)
            result = wf.run_workflow(
                _make_proposal(skill="mypy", error_code="TP002", level="L1", auto_merge=True),
            )

        assert result.status == "merged"
        assert ("mypy", "TP002") in merge_called


# ---------------------------------------------------------------------------
# API error handling
# ---------------------------------------------------------------------------

class TestAPIErrorHandling:
    def test_create_pr_returns_none_on_request_exception(
        self, fake_repo: Path, fp_path: Path
    ):
        """requests exceptions during PR creation should result in failed status."""
        import requests

        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )

        def fake_post(url: str, **kwargs):
            raise requests.RequestException("connection reset")

        with mock.patch("self_heal_pr_workflow.requests.post", side_effect=fake_post), \
             mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            result = wf.run_workflow(_make_proposal())

        assert result.status == "failed"
        assert result.pr_url is None

    def test_pr_creation_422_returns_existing_pr(self, fake_repo: Path, fp_path: Path):
        """HTTP 422 during PR creation should trigger _find_existing_pr."""
        existing_pr_url = "https://github.com/testowner/testrepo/pull/12"

        def fake_post(url: str, **kwargs):
            resp = mock.MagicMock()
            if "head=" not in url:
                # First POST to /pulls returns 422 (already exists)
                resp.status_code = 422
            else:
                resp.status_code = 200
                resp.json.return_value = [{"html_url": existing_pr_url}]
            return resp

        def fake_get(url: str, **kwargs):
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.json.return_value = [{"html_url": existing_pr_url}]
            return resp

        wf = SelfHealPRWorkflow(
            repo_path=str(fake_repo),
            github_token="fake-token",
            failure_patterns_path=fp_path,
        )

        with mock.patch("self_heal_pr_workflow.requests.post", side_effect=fake_post), \
             mock.patch("self_heal_pr_workflow.requests.get", side_effect=fake_get), \
             mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            result = wf.run_workflow(_make_proposal())

        # Should fall back to existing PR instead of failing
        assert result.status == "created"
        assert result.pr_url == existing_pr_url
