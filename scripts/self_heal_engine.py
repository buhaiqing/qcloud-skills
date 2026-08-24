#!/usr/bin/env python3
"""Self-Heal Engine — automatically generate and apply fixes for recurring failures.

Trigger: same (skill, error_code) appears N times (default 5) in 30 days.

Fix levels:
  L1 — template-based: add error table row to SKILL.md (auto-merge)
  L2 — LLM: adjust default parameters (needs human review)
  L3 — LLM: restructure command template (needs human approval)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
FAILURE_PATTERNS_PATH = ROOT / "docs" / "failure-patterns.md"
TRACES_DIR = ROOT / ".runtime" / "traces"


@dataclass
class FixProposal:
    """A proposed fix for a recurring failure pattern."""

    level: str  # "L1" | "L2" | "L3"
    skill: str  # "qcloud-cvm-ops"
    error_code: str  # "InvalidInstanceId"
    occurrence_count: int  # 7
    target_file: str  # "qcloud-cvm-ops/SKILL.md"
    old_content: str  # original content (for L2/L3 context)
    new_content: str  # patched content
    rationale: str  # human-readable reason
    risk_assessment: str  # "LOW: only adds error table row"
    auto_merge: bool  # True for L1 only

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "skill": self.skill,
            "error_code": self.error_code,
            "occurrence_count": self.occurrence_count,
            "target_file": self.target_file,
            "rationale": self.rationale,
            "risk_assessment": self.risk_assessment,
            "auto_merge": self.auto_merge,
        }


def _load_failure_patterns(path: Path | None = None) -> list[dict[str, Any]]:
    """Load failure patterns from docs/failure-patterns.md."""
    if path is None:
        path = FAILURE_PATTERNS_PATH
    if not path.exists():
        return []

    text = path.read_text()
    patterns: list[dict[str, Any]] = []

    # Match ## [skill] / [error]
    section_re = re.compile(r"##\s*\[([^\]]+)\]\s*/\s*\[([^\]]+)\]")
    # Fixed: capture whitespace separately so key starts at group(3), value at group(4)
    kv_re = re.compile(r"^-(\s+)([\w][\w\s]*):\s+(.+)$", re.MULTILINE)

    for m in section_re.finditer(text):
        skill = m.group(1)
        error = m.group(2)
        start = m.start()
        end = m.end()

        # Find block: from this section start to just before the next ## at line start
        # Search from `end` so the newline before the next ## is not consumed
        next_section_match = re.search(r"\n(?=##\s)", text[end:])
        if next_section_match:
            # block_end is one position before the newline before next ##
            block_end = end + next_section_match.start()
            block = text[start:block_end]
        else:
            block = text[start:]

        entry: dict[str, Any] = {"skill": skill, "error": error}
        for kv in kv_re.finditer(block):
            key = kv.group(2).strip().lower().replace(" ", "_")
            value = kv.group(3).strip()
            if key in ("count", "occurrences"):
                key = "count"
                try:
                    value = int(re.sub(r"\D", "", value))
                except ValueError:
                    value = 1
            entry[key] = value

        entry.setdefault("count", 1)
        patterns.append(entry)

    return patterns


def _load_traces(traces_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load recent trace files from .runtime/traces/."""
    if traces_dir is None:
        traces_dir = TRACES_DIR
    if not traces_dir.exists():
        return []

    traces: list[dict[str, Any]] = []
    for tf in sorted(traces_dir.glob("*.jsonl")):
        try:
            text = tf.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                traces.append(json.loads(line))
            except (ValueError, TypeError):
                continue
    return traces


def _skill_to_skill_path(skill: str) -> Path:
    """Map skill name to SKILL.md path."""
    return ROOT / skill / "SKILL.md"


class SelfHealEngine:
    """Analyze recurring failures and generate fix proposals."""

    def __init__(
        self,
        failure_patterns_path: str | Path = FAILURE_PATTERNS_PATH,
        traces_dir: str | Path = TRACES_DIR,
        github_token: str | None = None,
        min_occurrences: int = 5,
        days_window: int = 30,
    ) -> None:
        self.failure_patterns_path = Path(failure_patterns_path)
        self.traces_dir = Path(traces_dir)
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.min_occurrences = min_occurrences
        self.days_window = days_window

    def analyze_failures(self) -> list[FixProposal]:
        """Analyze failure patterns and return FixProposals meeting the threshold."""
        patterns = _load_failure_patterns(self.failure_patterns_path)
        proposals: list[FixProposal] = []

        for p in patterns:
            count = p.get("count", 0)
            if count < self.min_occurrences:
                continue

            skill = p.get("skill", "unknown")
            error = p.get("error", "unknown")
            fix_type = p.get("fix_type") or "L1"
            pattern_tuple = (skill, error, p)

            if fix_type == "L1":
                proposals.append(self.generate_l1_fix(pattern_tuple))
            elif fix_type == "L2":
                proposals.append(self.generate_l2_fix(pattern_tuple))
            else:
                proposals.append(self.generate_l3_fix(pattern_tuple))

        return proposals

    def generate_l1_fix(self, pattern: tuple[str, str, dict[str, Any]]) -> FixProposal:
        """Template-based L1 fix: add error code row to SKILL.md error table."""
        skill, error, meta = pattern
        skill_path = _skill_to_skill_path(skill)
        count = meta.get("count", 0)

        hint = meta.get("fix") or meta.get("recovery_hint") or "See documentation for resolution."
        if not skill_path.exists():
            new_section = textwrap.dedent(
                f"""

                ## Error Reference

                | Error Code | Occurrences | Recovery |
                | --- | --- | --- |
                | `{error}` | {count} | {hint} |
                """
            )
            new_content = new_section.lstrip()
        else:
            text = skill_path.read_text()
            error_table_re = re.compile(r"(##+\s*Error[^\n]*\n)(\|.*?\n)+", re.MULTILINE)
            match = error_table_re.search(text)

            if match:
                insert_pos = match.end()
                new_row = f"| `{error}` | {count} | {hint} |\n"
                new_content = text[:insert_pos] + new_row + text[insert_pos:]
            else:
                new_section = textwrap.dedent(
                    f"""

                    ## Error Reference

                    | Error Code | Occurrences | Recovery |
                    | --- | --- | --- |
                    | `{error}` | {count} | {hint} |
                    """
                )
                new_content = text.rstrip() + new_section
        return FixProposal(
            level="L1",
            skill=skill,
            error_code=error,
            occurrence_count=count,
            target_file=str(skill_path),
            old_content="",
            new_content=new_content,
            rationale=f"L1: Added error table entry after {count} occurrences",
            risk_assessment="LOW: only appends to error table",
            auto_merge=True,
        )

    def generate_l2_fix(self, pattern: tuple[str, str, dict[str, Any]]) -> FixProposal:
        """LLM-based L2 fix: adjust default parameters."""
        skill, error, meta = pattern
        skill_path = _skill_to_skill_path(skill)
        count = meta.get("count", 0)

        l2_hint = (
            "# L2 fix pending — configure LLM_API_KEY to enable LLM-based parameter tuning.\n"
            "# Suggested approach: add --ClientToken for idempotency, increase timeout for slow ops."
        )
        return FixProposal(
            level="L2",
            skill=skill,
            error_code=error,
            occurrence_count=count,
            target_file=str(skill_path),
            old_content="",
            new_content=l2_hint,
            rationale=f"L2: Parameter adjustment needed after {count} occurrences (LLM required)",
            risk_assessment="MEDIUM: modifies default parameters",
            auto_merge=False,
        )

    def generate_l3_fix(self, pattern: tuple[str, str, dict[str, Any]]) -> FixProposal:
        """LLM-based L3 fix: restructure command template."""
        skill, error, meta = pattern
        skill_path = _skill_to_skill_path(skill)
        count = meta.get("count", 0)

        l3_hint = (
            "# L3 fix pending — configure LLM_API_KEY to enable LLM-based template restructuring.\n"
            "# Suggested approach: add pre-check step, reorder API calls, add validation."
        )
        return FixProposal(
            level="L3",
            skill=skill,
            error_code=error,
            occurrence_count=count,
            target_file=str(skill_path),
            old_content="",
            new_content=l3_hint,
            rationale=f"L3: Command template restructuring needed after {count} occurrences (LLM required)",
            risk_assessment="HIGH: modifies command execution flow",
            auto_merge=False,
        )

    def create_pr(self, proposal: FixProposal) -> str:
        """Create a GitHub PR for the fix."""
        if not self.github_token:
            return ""

        remote = self._git_remote()
        if not remote:
            return ""
        owner, repo = remote

        branch_name = f"fix/{proposal.skill}-{proposal.error_code}"
        title = f"fix({proposal.skill}): {proposal.level} fix for `{proposal.error_code}`"
        body = (
            f"## Self-Heal {proposal.level}\n\n"
            f"**Skill**: {proposal.skill}\n"
            f"**Error**: `{proposal.error_code}`\n"
            f"**Occurrences**: {proposal.occurrence_count}\n"
            f"**Rationale**: {proposal.rationale}\n"
            f"**Risk**: {proposal.risk_assessment}\n"
            f"**Auto-merge**: {proposal.auto_merge}\n"
        )

        self._git_checkout_new_branch(branch_name)
        self._apply_fix_to_disk(proposal)
        self._git_commit_push(branch_name, title)

        labels = ["self-heal", f"self-heal/{proposal.level}"]
        if proposal.level == "L2":
            labels.append("needs-human-review")
        elif proposal.level == "L3":
            labels.append("needs-human-approval")

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": "main",
            "labels": labels,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 201:
                pr_data = resp.json()
                return pr_data.get("html_url") or pr_data.get("url") or ""
        except requests.RequestException:
            pass

        return ""

    def verify_fix(self, proposal: FixProposal) -> bool:
        """Run CI verification: ruff check."""
        target = ROOT / proposal.target_file
        if not target.exists():
            return False

        result = subprocess.run(
            ["ruff", "check", str(target)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        return result.returncode == 0

    def apply_fix(self, proposal: FixProposal) -> bool:
        """Apply a FixProposal to the target file."""
        target = ROOT / proposal.target_file
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(proposal.new_content)
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _git_remote(self) -> tuple[str, str] | None:
        """Return (owner, repo) from git remote origin."""
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        m = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
        return None

    def _git_checkout_new_branch(self, branch_name: str) -> None:
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True,
            check=False,
            cwd=str(ROOT),
        )

    def _git_commit_push(self, branch_name: str, message: str) -> None:
        subprocess.run(["git", "add", "."], capture_output=True, check=False, cwd=str(ROOT))
        cr = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(ROOT),
        )
        if cr.returncode == 0:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                capture_output=True,
                check=False,
                cwd=str(ROOT),
            )

    def _apply_fix_to_disk(self, proposal: FixProposal) -> None:
        target = ROOT / proposal.target_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(proposal.new_content)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Heal Engine")
    parser.add_argument("--min-occurrences", type=int, default=5)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    engine = SelfHealEngine(min_occurrences=args.min_occurrences, days_window=args.days)
    proposals = engine.analyze_failures()

    if not proposals:
        print("No high-frequency patterns found.")
        return 0

    print(f"Found {len(proposals)} fix proposal(s):\n")
    for p in proposals:
        print(f"  [{p.level}] {p.skill} / {p.error_code} ({p.occurrence_count}x)")
        print(f"    Risk: {p.risk_assessment}")
        print(f"    Auto-merge: {p.auto_merge}")
        print()

    if args.dry_run:
        return 0

    for p in proposals:
        if args.apply and p.auto_merge:
            ok = engine.apply_fix(p)
            print(f"{'Applied' if ok else 'Failed'}: {p.skill} / {p.error_code}")
        else:
            url = engine.create_pr(p)
            if url:
                print(f"PR created: {url}")
            else:
                print(f"PR skipped (no token or API error): {p.skill} / {p.error_code}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
