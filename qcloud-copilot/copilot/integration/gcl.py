"""GCL Runner thin adapter for qcloud-skills."""

from __future__ import annotations

import json
import subprocess

from copilot.blackboard import find_repo_root


def run_gcl(skill: str, operation: str, params: dict) -> dict:
    runner = find_repo_root() / "scripts" / "gcl_runner.py"
    cmd = [
        "python3",
        str(runner),
        "--skill",
        skill,
        "--operation",
        operation,
        "--params",
        json.dumps(params),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(find_repo_root()))
    if result.returncode != 0:
        return {"status": "error", "error": result.stderr}
    return json.loads(result.stdout)
