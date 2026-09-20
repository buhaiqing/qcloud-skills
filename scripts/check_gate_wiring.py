#!/usr/bin/env python3
"""Static gate-wiring checker: assert both ends of every contract agree (CI gate).

Every contract in this repo has two ends, and they drift silently:

  * a script that advertises itself as a gate  <->  an automation surface that calls it
  * an entry in ``assets/shared/validation_commands.yaml``  <->  a script on disk
  * a key in ``assets/shared/thresholds.json``  <->  a production consumer
  * a store path literal  <->  exactly one declaring module

Automation surfaces are: ``Makefile``, ``.pre-commit-config.yaml``, ``.githooks/pre-commit``,
``.github/workflows/*.yml`` and ``scripts/validate_local.py``. A script counts as *wired*
when its file name or module stem appears in any surface text, or when a wired script
imports it under its bare module name (transitive closure).

Rules (one line per finding, prefixed with the rule code):

  W1  dead gate   -- a ``scripts/*.py`` file (excluding ``*_test.py``/``test_*.py``) whose
                     first 60 lines contain the case-insensitive phrase "CI gate" must be
                     wired; otherwise ``W1 <relative path>``.
  W2  manifest    -- every key under ``gates:`` in ``assets/shared/validation_commands.yaml``
                     must reference existing ``scripts/<name>.py`` files and each of those
                     must be wired; ``tools:`` entries are exempt. A missing ``gates:`` or
                     ``tools:`` section is a config error (exit 2).
  W3a single src  -- every ``thresholds.json`` key needs >= 1 production consumer (non-test
                     ``.py``, ``Makefile`` or workflow text); else ``W3 threshold:<key>``.
  W3b single src  -- the root-relative store expression ``(ROOT|_ROOT) / "docs" /
                     "failure-patterns.md"`` may only appear in
                     ``scripts/_failure_pattern_store.py``; else ``W3 store-path:<modules>``.
                     A lower-case ``root / "docs" / ...`` is a parameterised use, not a
                     declaration, and never counts.

Exit codes: 0 clean, 1 findings, 2 configuration error.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SURFACE_FILES = (
    "Makefile",
    ".pre-commit-config.yaml",
    ".githooks/pre-commit",
    "scripts/validate_local.py",
)
WORKFLOW_GLOB = ".github/workflows/*.yml"

VALIDATION_MANIFEST = "assets/shared/validation_commands.yaml"
THRESHOLDS = "assets/shared/thresholds.json"

TEST_FILE = re.compile(r"^(?:test_.*|.*_test)\.py$")
CI_GATE_MARKER = re.compile(r"ci gate", re.IGNORECASE)
STORE_PATH_DECL = re.compile(r'\b(?:_ROOT|ROOT)\s*/\s*"docs"\s*/\s*"failure-patterns\.md"')
SCRIPT_REF = re.compile(r"scripts/([A-Za-z0-9_./-]+\.py)")
STORE_OWNER = "_failure_pattern_store.py"

# Directories that never hold production consumers (VCS internals, generated output).
SCAN_SKIP_DIRS = frozenset(
    {".git", ".runtime", ".codegraph", ".ruff_cache", ".venv", "node_modules", "audit-results"}
)


class ConfigError(RuntimeError):
    """Raised for malformed or missing configuration; maps to exit code 2."""


def _mention_pattern(stem: str) -> re.Pattern[str]:
    # Word-ish boundaries: `check_test` must not match `check_test_collection`.
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(stem)}(?![A-Za-z0-9_])")


def collect_surfaces(root: Path) -> list[Path]:
    """Return existing automation-surface files, workflows expanded sorted."""
    surfaces = [root / name for name in SURFACE_FILES]
    surfaces.extend(sorted(root.glob(WORKFLOW_GLOB)))
    return [path for path in surfaces if path.is_file()]


def surface_texts(surfaces: list[Path]) -> list[tuple[Path, str]]:
    return [(path, path.read_text(encoding="utf-8", errors="replace")) for path in surfaces]


def bare_imports(path: Path, stems: set[str]) -> set[str]:
    """Module stems imported by `path` under their bare name (no relative import)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in stems:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and node.module in stems:
                found.add(node.module)
    return found


def wiring_state(root: Path) -> tuple[list[Path], list[Path], set[str]]:
    """Return (surfaces, scripts, wired stems) with the import closure applied."""
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        raise ConfigError(f"no scripts directory under {root}")
    scripts = sorted(p for p in scripts_dir.glob("*.py") if p.is_file())
    stems = {p.stem for p in scripts}
    surfaces = collect_surfaces(root)

    wired: set[str] = set()
    texts = surface_texts(surfaces)
    for stem in stems:
        pattern = _mention_pattern(stem)
        if any(pattern.search(text) for _, text in texts):
            wired.add(stem)

    # Transitive closure over bare-name imports of wired scripts.
    edges = {stem: bare_imports(scripts_dir / f"{stem}.py", stems) for stem in stems}
    growing = True
    while growing:
        growing = False
        for stem in tuple(wired):
            for target in edges.get(stem, ()):  # noqa: SIM118 - iterating a set is intended
                if target not in wired:
                    wired.add(target)
                    growing = True
    return surfaces, scripts, wired


def check_dead_gates(root: Path, scripts: list[Path], wired: set[str]) -> list[str]:
    """W1: self-declared CI gates must be reachable from an automation surface."""
    findings: list[str] = []
    for script in scripts:
        if TEST_FILE.match(script.name):
            continue
        head = script.read_text(encoding="utf-8", errors="replace").splitlines()[:60]
        if not any(CI_GATE_MARKER.search(line) for line in head):
            continue
        if script.stem not in wired:
            findings.append(f"W1 {script.relative_to(root).as_posix()}")
    return findings


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without PyYAML
        raise ConfigError(f"PyYAML is required to read {path.name}: {exc}") from exc
    if not path.is_file():
        raise ConfigError(f"missing validation manifest: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"unparseable {path.name}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"{path.name} must contain a top-level mapping")
    return loaded


def check_manifest(root: Path, wired: set[str]) -> list[str]:
    """W2: every `gates:` entry must exist on disk and be wired; `tools:` is exempt."""
    path = root / VALIDATION_MANIFEST
    manifest = _load_yaml_mapping(path)
    for section in ("gates", "tools"):
        if section not in manifest:
            raise ConfigError(f"{path.name} is missing the top-level `{section}:` section")
        value = manifest[section]
        if value is not None and not isinstance(value, dict):
            raise ConfigError(f"`{section}:` in {path.name} must be a mapping")

    findings: list[str] = []
    gates = manifest.get("gates") or {}
    for key in sorted(gates):
        command = str(gates[key])
        for ref in SCRIPT_REF.findall(command):
            target = root / "scripts" / ref
            if not target.is_file():
                findings.append(f"W2 {key}: command references missing scripts/{ref}")
            elif target.stem not in wired:
                findings.append(f"W2 {key}: unwired gate scripts/{ref}")
    return findings


def _iter_py_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in SCAN_SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if TEST_FILE.match(path.name):
            continue
        out.append(path)
    return out


def check_thresholds(root: Path) -> list[str]:
    """W3a: every threshold key must be read by at least one production consumer."""
    path = root / THRESHOLDS
    if not path.is_file():
        raise ConfigError(f"missing thresholds file: {path}")
    try:
        thresholds = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"unparseable {path.name}: {exc}") from exc
    if not isinstance(thresholds, dict):
        raise ConfigError(f"{path.name} must contain a JSON object")
    if not thresholds:
        return []

    keys = {str(key): _mention_pattern(str(key)) for key in thresholds}
    seen: set[str] = set()
    consumers: list[Path] = _iter_py_files(root)
    consumers.append(root / "Makefile")
    consumers.extend(sorted(root.glob(WORKFLOW_GLOB)))
    for source in consumers:
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        for key, pattern in keys.items():
            if key not in seen and pattern.search(text):
                seen.add(key)

    return [f"W3 threshold:{key}" for key in sorted(keys) if key not in seen]


def check_store_path(root: Path) -> list[str]:
    """W3b: the store path literal lives in exactly one declaring module.

    Test files are exempt: their fixtures legitimately build the same path under a
    temporary root (``tmp / "docs" / "failure-patterns.md"``), which is scaffolding
    rather than a second declaration of the production store.
    """
    offenders: list[str] = []
    for script in sorted((root / "scripts").glob("*.py")):
        if script.name == STORE_OWNER or TEST_FILE.match(script.name):
            continue
        text = script.read_text(encoding="utf-8", errors="replace")
        if STORE_PATH_DECL.search(text):
            offenders.append(script.stem)
    if not offenders:
        return []
    return [f"W3 store-path:{', '.join(offenders)}"]


def run_checks(root: Path) -> tuple[list[str], dict[str, object]]:
    surfaces, scripts, wired = wiring_state(root)
    findings: list[str] = []
    findings.extend(check_dead_gates(root, scripts, wired))
    findings.extend(check_manifest(root, wired))
    findings.extend(check_thresholds(root))
    findings.extend(check_store_path(root))
    report: dict[str, object] = {
        "root": str(root),
        "surfaces": [p.relative_to(root).as_posix() for p in surfaces],
        "scripts": len(scripts),
        "wired": len(wired),
        "findings": [
            {"code": line.split(" ", 1)[0], "detail": line.split(" ", 1)[1]} for line in findings
        ],
    }
    return findings, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assert both ends of every gate contract are wired (W1-W3)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: the root owning this script)",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        findings, report = run_checks(root)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    report["finding_count"] = len(findings)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        for line in findings:
            print(line)
        if findings:
            print(f"{len(findings)} finding(s) — contracts drifted (see rule codes W1-W3).")
        else:
            print(
                f"gate wiring OK: {report['wired']}/{report['scripts']} scripts wired, "
                f"{len(report['surfaces'])} automation surface(s)."
            )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
