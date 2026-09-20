#!/usr/bin/env python3
"""Execute the manifest gates declared for one surface.

`assets/shared/validation_commands.yaml` is the single source of truth for which
gate runs where. This runner is how each surface consumes it, so CI, the local
mirror and `make` execute the same commands in the same order instead of three
hand-maintained lists that drift apart.

Usage:
  python3 scripts/run_gates.py --set ci          # gates declared runs_in: [ci]
  python3 scripts/run_gates.py --set local
  python3 scripts/run_gates.py --set make
  python3 scripts/run_gates.py --set ci --list   # print, do not execute
  python3 scripts/run_gates.py --set ci --json

Exit codes:
  0  every gate for that surface passed
  1  a gate failed (its name and output tail are printed)
  2  the manifest is unusable (missing / malformed / unknown set) — never a pass
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dependency of the manifest
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("assets/shared/validation_commands.yaml")
SURFACES = ("ci", "local", "make")
TAIL_LINES = 20


class ManifestError(Exception):
    """The manifest cannot be trusted to describe what should run."""


@dataclass(frozen=True)
class Gate:
    name: str
    command: str
    runs_in: tuple[str, ...]


def load_manifest(root: Path = ROOT) -> list[Gate]:
    """Return the gates in declaration order; raise ManifestError if unusable."""
    if yaml is None:
        raise ManifestError("PyYAML is required to read the gate manifest")
    path = root / MANIFEST
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError(f"{path}: top level must be a mapping")
    entries = raw.get("gates")
    if not isinstance(entries, list) or not entries:
        raise ManifestError(f"{path}: `gates:` must be a non-empty list")
    gates: list[Gate] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ManifestError(f"{path}: gates[{index}] must be a mapping")
        name = entry.get("name")
        command = entry.get("command")
        runs_in = entry.get("runs_in")
        if not isinstance(name, str) or not name.strip():
            raise ManifestError(f"{path}: gates[{index}] needs a non-empty `name`")
        if name in seen:
            raise ManifestError(f"{path}: duplicate gate name {name!r}")
        seen.add(name)
        if not isinstance(command, str) or not command.strip():
            raise ManifestError(f"{path}: gate {name!r} needs a non-empty `command`")
        if not isinstance(runs_in, list) or not runs_in:
            raise ManifestError(f"{path}: gate {name!r} needs a non-empty `runs_in` list")
        unknown = [s for s in runs_in if s not in SURFACES]
        if unknown:
            raise ManifestError(
                f"{path}: gate {name!r} declares unknown surface(s) {unknown}; "
                f"known: {list(SURFACES)}"
            )
        gates.append(Gate(name=name, command=command.strip(), runs_in=tuple(runs_in)))
    return gates


def gates_for(gates: list[Gate], surface: str) -> list[Gate]:
    if surface not in SURFACES:
        raise ManifestError(f"unknown surface {surface!r}; known: {list(SURFACES)}")
    return [g for g in gates if surface in g.runs_in]


def run_gate(gate: Gate, root: Path) -> tuple[int, str]:
    """Run one gate; return (exit_code, combined output)."""
    argv = shlex.split(gate.command)
    if not argv:
        raise ManifestError(f"gate {gate.name!r} has an empty command")
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        return 127, f"cannot execute {argv[0]}: {exc}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", dest="surface", choices=SURFACES, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--list", action="store_true", help="Print gates; do not execute.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report on stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        gates = gates_for(load_manifest(root), args.surface)
    except ManifestError as exc:
        print(f"MANIFEST ERROR: {exc}", file=sys.stderr)
        return 2
    if not gates:
        print(f"MANIFEST ERROR: no gate declares runs_in: [{args.surface}]", file=sys.stderr)
        return 2

    if args.list:
        for gate in gates:
            print(f"{gate.name}: {gate.command}")
        return 0

    results: list[dict[str, Any]] = []
    for gate in gates:
        print(f"==> [{args.surface}] {gate.name}")
        print(f"$ {gate.command}")
        code, output = run_gate(gate, root)
        results.append({"name": gate.name, "exit_code": code})
        if code != 0:
            tail = "\n".join(output.strip().splitlines()[-TAIL_LINES:])
            if tail:
                print(tail)
            print(f"FAILED: {gate.name} exited with {code}", file=sys.stderr)
            if args.json:
                print(json.dumps({"surface": args.surface, "status": "fail", "results": results}))
            return 1

    print(f"OK: {len(results)} manifest gate(s) passed for surface '{args.surface}'")
    if args.json:
        print(json.dumps({"surface": args.surface, "status": "pass", "results": results}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
