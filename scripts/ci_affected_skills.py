#!/usr/bin/env python3
"""KPI #4: read affected skill dirs from git diff (stdin or --from-git) and emit
the unique qcloud-*-ops skill names that must pass self-test in CI.
Each emitted name is on its own line (empty output if none)."""
import re
import sys
from typing import List

SKILL_RE = re.compile(r"^(?:[ab]/)?(qcloud-[a-z0-9-]+-ops)/")


def extract_skills(diff_text: str) -> List[str]:
    skills = set()
    for line in diff_text.splitlines():
        m = SKILL_RE.match(line.strip())
        if m:
            skills.add(m.group(1))
    return sorted(skills)


def main() -> int:
    if "--from-git" in sys.argv:
        import subprocess

        # compare against the merge-base with the default remote branch
        base = subprocess.run(
            ["git", "merge-base", "HEAD", "origin/main"],
            capture_output=True,
            text=True,
        ).stdout.strip() or "HEAD~1"
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True,
            text=True,
        ).stdout
    else:
        diff = sys.stdin.read()
    for name in extract_skills(diff):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
