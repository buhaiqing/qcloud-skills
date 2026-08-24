"""Self-Heal PR Workflow — creates and manages fix PRs.

Listens for FixProposals from SelfHealEngine and drives them through the PR lifecycle:
- L1: auto-create → CI → auto-merge
- L2: create with needs-human-review label
- L3: create with needs-human-approval label
- After merge: deduplicate pattern from failure-patterns.md
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FixProposal:
    """A self-heal fix proposal produced by SelfHealEngine."""

    level: str  # "L1" | "L2" | "L3"
    skill: str
    error_code: str
    occurrence_count: int
    target_file: str  # absolute or repo-relative path
    old_content: str
    new_content: str
    rationale: str
    risk_assessment: str
    auto_merge: bool


@dataclass
class PRWorkflowResult:
    """Result of processing a FixProposal through the PR workflow."""

    pr_url: str | None
    status: str  # "created" | "merged" | "failed" | "skipped"
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]
_FAILURE_PATTERNS_PATH = _ROOT / "docs" / "failure-patterns.md"


def _repo_info(repo_path: str = ".") -> tuple[str, str]:
    """Return (owner, repo) from git remote -v."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    url = result.stdout.strip()
    # git@github.com:owner/repo.git  or  https://github.com/owner/repo.git
    m = re.search(r":([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        raise RuntimeError(f"Cannot parse owner/repo from git remote: {url}")
    return m.group(1), m.group(2)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class SelfHealPRWorkflow:
    """Manages the PR lifecycle for self-heal fixes."""

    def __init__(
        self,
        repo_path: str = ".",
        github_token: str | None = None,
        failure_patterns_path: Path | None = None,
    ):
        self.repo_path: str = repo_path
        self.token: str | None = github_token or os.environ.get("GITHUB_TOKEN")
        self.api_base: str = "https://api.github.com"
        self._owner, self._repo = _repo_info(repo_path)
        self.fp_path: Path = failure_patterns_path or _FAILURE_PATTERNS_PATH

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def run_workflow(self, proposal: FixProposal) -> PRWorkflowResult:
        """Process a FixProposal through the PR workflow.

        Steps:
        1. Create a feature branch: fix/<skill>-<error_code>
        2. Apply the fix (write new_content to target_file)
        3. Create PR with appropriate labels
        4. If L1 and CI passes → auto-merge
        5. Deduplicate the pattern from failure-patterns.md
        """
        if not self.token:
            return PRWorkflowResult(
                pr_url=None,
                status="skipped",
                message="GITHUB_TOKEN not set; skipping PR creation.",
            )

        branch_name = f"fix/{proposal.skill}-{proposal.error_code}"

        try:
            # 1. Create branch
            if not self._create_branch(branch_name):
                return PRWorkflowResult(
                    pr_url=None,
                    status="failed",
                    message=f"Failed to create branch {branch_name}",
                )

            # 2. Apply fix
            self._apply_fix(proposal)

            # 3. Commit and push
            commit_ok = self._commit_and_push(branch_name, proposal)
            if not commit_ok:
                self._cleanup_branch(branch_name)
                return PRWorkflowResult(
                    pr_url=None,
                    status="failed",
                    message="Failed to commit/push fix",
                )

            # 4. Create PR
            labels = self._labels_for_level(proposal.level)
            pr_url = self._create_pr(proposal, labels)
            if not pr_url:
                self._cleanup_branch(branch_name)
                return PRWorkflowResult(
                    pr_url=None, status="failed", message="Failed to create PR"
                )

            # 5. L1 auto-merge
            if proposal.auto_merge and proposal.level == "L1":
                pr_number = self._pr_number_from_url(pr_url)
                ci_ok = self._wait_for_ci(pr_number, timeout=300)
                if ci_ok:
                    merged = self._merge_pr(pr_number)
                    if merged:
                        self._deduplicate_pattern(proposal.skill, proposal.error_code)
                        return PRWorkflowResult(
                            pr_url=pr_url,
                            status="merged",
                            message="L1 fix auto-merged after CI passed",
                        )
                    return PRWorkflowResult(
                        pr_url=pr_url,
                        status="failed",
                        message="CI passed but merge failed",
                    )
                return PRWorkflowResult(
                    pr_url=pr_url,
                    status="failed",
                    message="CI did not pass within timeout",
                )

            return PRWorkflowResult(
                pr_url=pr_url,
                status="created",
                message=f"PR created with labels {labels}; awaiting review",
            )

        except (subprocess.CalledProcessError, OSError, RuntimeError, requests.RequestException):
            self._cleanup_branch(branch_name)
            return PRWorkflowResult(
                pr_url=None, status="failed", message="Workflow error"
            )

    # -------------------------------------------------------------------------
    # Branch / commit helpers
    # -------------------------------------------------------------------------

    def _create_branch(self, branch_name: str) -> bool:
        """git checkout -b <branch_name>. Returns True on success."""
        try:
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=self.repo_path,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "checkout", "-B", branch_name, "origin/main"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _apply_fix(self, proposal: FixProposal) -> None:
        """Apply proposal.new_content to proposal.target_file (staged)."""
        target = Path(proposal.target_file)
        if not target.is_absolute():
            target = Path(self.repo_path) / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(proposal.new_content, encoding="utf-8")

    def _commit_and_push(
        self, branch_name: str, proposal: FixProposal
    ) -> bool:
        """git add + commit + push. Returns True on success."""
        try:
            subprocess.run(
                ["git", "-C", self.repo_path, "add", "."],
                check=True,
            )
            commit_msg = (
                f"fix({proposal.skill}): {proposal.error_code}\n\n"
                f"Level: {proposal.level}\n"
                f"Rationale: {proposal.rationale}\n"
                f"Risk: {proposal.risk_assessment}"
            )
            subprocess.run(
                ["git", "-C", self.repo_path, "commit", "-m", commit_msg],
                check=True,
            )
            env = {**os.environ, "GITHUB_TOKEN": self.token or ""}
            subprocess.run(
                ["git", "-C", self.repo_path, "push", "-u", "origin", branch_name],
                env=env,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    # -------------------------------------------------------------------------
    # GitHub API helpers
    # -------------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _create_pr(self, proposal: FixProposal, labels: list[str]) -> str | None:
        """POST /repos/{owner}/{repo}/pulls. Returns PR URL or None."""
        title = f"[{proposal.level}] {proposal.skill}: auto-fix for {proposal.error_code}"
        body = (
            f"## Self-Heal Fix\n\n"
            f"**Skill**: {proposal.skill}\n"
            f"**Level**: {proposal.level}\n"
            f"**Error**: `{proposal.error_code}`\n"
            f"**Occurrences**: {proposal.occurrence_count}\n\n"
            f"### Rationale\n{proposal.rationale}\n\n"
            f"### Risk Assessment\n{proposal.risk_assessment}\n\n"
            f"### Changes\n"
            f"- File: `{proposal.target_file}`\n\n"
            f"<!-- self-heal: {proposal.skill}:{proposal.error_code} -->\n"
        )

        payload = {
            "title": title,
            "head": f"fix/{proposal.skill}-{proposal.error_code}",
            "base": "main",
            "body": body,
            "labels": labels,
        }

        url = f"{self.api_base}/repos/{self._owner}/{self._repo}/pulls"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        if resp.status_code == 201:
            return resp.json().get("html_url")
        # 422 = already a PR exists; treat as success
        if resp.status_code == 422:
            return self._find_existing_pr(proposal)
        return None

    def _find_existing_pr(self, proposal: FixProposal) -> str | None:
        """Check if a PR already exists for this fix branch."""
        url = (
            f"{self.api_base}/repos/{self._owner}/{self._repo}/pulls"
            f"?head={self._owner}:fix/{proposal.skill}-{proposal.error_code}"
            f"&state=open"
        )
        resp = requests.get(url, headers=self._headers(), timeout=15)
        if resp.status_code == 200 and resp.json():
            return resp.json()[0].get("html_url")
        return None

    def _wait_for_ci(self, pr_number: int, timeout: int = 300) -> bool:
        """Poll GitHub Actions status. Returns True when all checks succeed."""
        deadline = time.time() + timeout

        # Resolve head SHA for this PR
        sha_url = (
            f"{self.api_base}/repos/{self._owner}/{self._repo}"
            f"/pulls/{pr_number}"
        )
        sha_resp = requests.get(sha_url, headers=self._headers(), timeout=15)
        if sha_resp.status_code != 200:
            return False
        sha = sha_resp.json().get("head", {}).get("sha")
        if not sha:
            return False

        while time.time() < deadline:
            statuses_url = (
                f"{self.api_base}/repos/{self._owner}/{self._repo}"
                f"/commits/{sha}/statuses"
            )
            resp = requests.get(statuses_url, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                statuses = resp.json()
                if not statuses:
                    time.sleep(10)
                    continue
                # All statuses must be "success" (no "failure" or "error")
                states = {s["state"] for s in statuses}
                if states == {"success"}:
                    return True
                if "failure" in states or "error" in states:
                    return False
            time.sleep(15)

        return False

    def _merge_pr(self, pr_number: int) -> bool:
        """PUT /repos/{owner}/{repo}/pulls/{number}/merge."""
        url = (
            f"{self.api_base}/repos/{self._owner}/{self._repo}"
            f"/pulls/{pr_number}/merge"
        )
        resp = requests.put(
            url,
            headers=self._headers(),
            json={"merge_method": "squash", "commit_title": "auto-merge (self-heal)"},
            timeout=30,
        )
        return resp.status_code == 200

    # -------------------------------------------------------------------------
    # Deduplication
    # -------------------------------------------------------------------------

    def _deduplicate_pattern(self, skill: str, error_code: str) -> None:
        """Remove or decrement the pattern entry in failure-patterns.md.

        Pattern key: (skill, error_code) — we match the skill column in the
        relevant category section and either remove the row or decrement count.
        """
        if not self.fp_path.exists():
            return

        content = self.fp_path.read_text(encoding="utf-8")
        original = content
        lines = content.splitlines()
        new_lines: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if (
                re.match(r"\|\s*`?" + re.escape(skill) + r"`?\s*\|", line, re.IGNORECASE)
                and error_code
                and error_code.lower() in line.lower()
            ):
                cells = [c.strip() for c in line.split("|")]
                # cells[-1] is empty (trailing |), cells[-2] is last content
                try:
                    count = int(cells[-2])
                except (ValueError, IndexError):
                    count = 1
                if count <= 1:
                    # Remove the row
                    i += 1
                    continue
                cells[-2] = str(count - 1)
                new_lines.append("|" + "|".join(cells) + "|")
                i += 1
                continue
            new_lines.append(line)
            i += 1

        new_content = "\n".join(new_lines)
        if new_content != original:
            self.fp_path.write_text(new_content + "\n", encoding="utf-8")

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def _cleanup_branch(self, branch_name: str) -> None:
        """Delete the local and remote feature branch."""
        try:
            subprocess.run(
                ["git", "-C", self.repo_path, "checkout", "main"],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "-C", self.repo_path, "branch", "-D", branch_name],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "-C", self.repo_path, "push", "origin", "--delete", branch_name],
                capture_output=True,
                check=False,
            )
        except subprocess.CalledProcessError:
            pass

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _labels_for_level(level: str) -> list[str]:
        mapping = {
            "L1": ["self-heal/L1"],
            "L2": ["self-heal/L2", "needs-human-review"],
            "L3": ["self-heal/L3", "needs-human-approval"],
        }
        return mapping.get(level, ["self-heal/L1"])

    @staticmethod
    def _pr_number_from_url(url: str) -> int:
        m = re.search(r"/pull/(\d+)", url)
        if not m:
            raise ValueError(f"Cannot extract PR number from URL: {url}")
        return int(m.group(1))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Self-Heal PR Workflow")
    parser.add_argument(
        "--proposal",
        type=str,
        required=True,
        help="Path to a JSON file containing a FixProposal",
    )
    parser.add_argument(
        "--repo-path", type=str, default=".", help="Path to the repo (default: .)"
    )
    parser.add_argument(
        "--token", type=str, default=None, help="GitHub token (or set GITHUB_TOKEN)"
    )
    args = parser.parse_args()

    proposal_data = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    proposal = FixProposal(**proposal_data)

    workflow = SelfHealPRWorkflow(repo_path=args.repo_path, github_token=args.token)
    result = workflow.run_workflow(proposal)

    print(f"[PR Workflow] status={result.status} pr_url={result.pr_url}")
    print(result.message)

    if result.status in ("merged", "created"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
