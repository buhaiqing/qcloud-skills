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
# The surfaces that consume the manifest (mirrors scripts/run_gates.py --set).
SURFACES = ("ci", "local", "make")

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


def _scripts_in_shell(text: str) -> set[str]:
    """Scripts invoked by shell text, ignoring comment lines.

    A script named only in a comment is *not* invoked: treating a comment as
    wiring is how a dead gate keeps looking alive (and it is the loophole the
    2026-09-20 critic probed for).
    """
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    return {name for name in SCRIPT_REF.findall(body) if "/" not in name}


def invoked_scripts(root: Path) -> set[str]:
    """Every script an automation surface actually invokes (structural, not textual)."""
    found: set[str] = set()
    for workflow in sorted(root.glob(WORKFLOW_GLOB)):
        data = _load_yaml_mapping(workflow)
        steps = ((data.get("jobs") or {}).get("validate") or {}).get("steps") or []
        for step in steps:
            if isinstance(step, dict):
                found |= _scripts_in_shell(str(step.get("run", "")))
    found |= _surface_scripts_from_validate_local(root / "scripts" / "validate_local.py")
    found |= _surface_scripts_from_makefile(root / "Makefile")
    for path in (root / ".pre-commit-config.yaml", root / ".githooks" / "pre-commit"):
        if path.is_file():
            found |= _scripts_in_shell(path.read_text(encoding="utf-8", errors="replace"))
    return found


def wiring_state(root: Path) -> tuple[list[Path], list[Path], set[str]]:
    """Return (surfaces, scripts, wired stems) with the import closure applied."""
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        raise ConfigError(f"no scripts directory under {root}")
    scripts = sorted(p for p in scripts_dir.glob("*.py") if p.is_file())
    stems = {p.stem for p in scripts}
    surfaces = collect_surfaces(root)

    # Seed with *invocations*, not mentions: a script referenced only in a comment
    # or a docstring is not wired. The extractors return file names; `wired` holds
    # module stems, so normalize here.
    wired: set[str] = {Path(name).stem for name in invoked_scripts(root)} & stems

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

    # Manifest-declared gates are wired *through* the manifest, but only for a
    # surface that actually invokes scripts/run_gates.py: a gate declared
    # `runs_in: [ci]` in a repo whose CI never runs the manifest is not wired,
    # it is just declared.
    consuming = {
        surface
        for surface in SURFACES
        if "run_gates.py" in _surface_scripts(root, surface)
    }
    if consuming:
        manifest_path = root / VALIDATION_MANIFEST
        if manifest_path.is_file():
            manifest = _load_yaml_mapping(manifest_path)
            for ref, runs_in in _manifest_gate_scripts(manifest).values():
                if set(runs_in) & consuming:
                    wired.add(Path(ref).stem)
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


# H-101 / CR-4: scripts that exist but have NO call site — neither invoked by
# any automation surface (CI, Makefile, pre-commit, validate_local) nor
# imported by any wired script. They are not "self-declared dead" like W1
# targets; they are silent: the file compiles, runs in isolation, and
# produces output that no one reads. Code-as-documentation is anti-pattern;
# either a script has a caller (and that caller is recorded here) or it is
# dead-on-arrival.
#
# Exemptions: __init__.py, conftest.py, scripts inside `qcloud-*/scripts/`
# (those are package-internal and have their own wiring tests at the
# package level). Anything else is reported.
_ZERO_WIRING_EXEMPT_STEMS: frozenset[str] = frozenset({
    "__init__",
    "conftest",
})


def check_zero_wiring(root: Path, scripts: list[Path], wired: set[str]) -> list[str]:
    """W5 (CR-4): every non-test, non-exempt script must have ≥1 caller."""
    findings: list[str] = []
    for script in scripts:
        if TEST_FILE.match(script.name):
            continue
        if script.stem in _ZERO_WIRING_EXEMPT_STEMS:
            continue
        # Per-package internal scripts (e.g. qcloud-cvm-ops/scripts/xyz.py)
        # are wired by their own package's test suite, not by the harness's
        # automation surfaces. Skip them so W5 reflects only the top-level
        # `scripts/` directory.
        if script.relative_to(root).parts[:-1] != ("scripts",):
            continue
        if script.stem not in wired:
            findings.append(f"W5 {script.relative_to(root).as_posix()}")
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


def _manifest_gate_scripts(manifest: dict[str, object]) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Return {gate_name: (script_rel, runs_in)} for every `gates:` entry naming a script.

    Existence is *not* validated here: a missing script is a W2 finding, not a
    config error, and `wiring_state` needs this list even when a script is absent.
    """
    entries = manifest.get("gates")
    if not isinstance(entries, list) or not entries:
        raise ConfigError("`gates:` must be a non-empty list of {name, command, runs_in}")
    out: dict[str, tuple[str, tuple[str, ...]]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"gates[{index}] must be a mapping")
        name = entry.get("name")
        command = entry.get("command")
        if not isinstance(name, str) or not isinstance(command, str):
            raise ConfigError(f"gates[{index}] needs string `name` and `command`")
        runs_in = entry.get("runs_in")
        if not isinstance(runs_in, list) or not runs_in:
            raise ConfigError(f"gate {name!r} needs a non-empty `runs_in` list")
        refs = SCRIPT_REF.findall(command)
        if refs:
            out[name] = (refs[0], tuple(str(s) for s in runs_in))
    return out


def check_manifest(root: Path, wired: set[str]) -> list[str]:
    """W2: every `gates:` entry must exist on disk and be wired; `tools:` is exempt.

    A gate listed in the manifest is wired *through* the manifest: the surfaces
    execute it via `scripts/run_gates.py`, so the gate's script does not need its
    own mention in the workflow. `wiring_state` folds that in — this check only
    reports a gate whose script is unreachable from any surface at all.
    """
    path = root / VALIDATION_MANIFEST
    manifest = _load_yaml_mapping(path)
    for section in ("gates", "tools", "surface_specific"):
        if section not in manifest:
            raise ConfigError(f"{path.name} is missing the top-level `{section}:` section")
    tools = manifest["tools"]
    if tools is not None and not isinstance(tools, list):
        raise ConfigError(f"`tools:` in {path.name} must be a list")
    surfaces = manifest["surface_specific"]
    if not isinstance(surfaces, dict):
        raise ConfigError(f"`surface_specific:` in {path.name} must be a mapping")

    findings: list[str] = []
    for name, (ref, _runs_in) in sorted(_manifest_gate_scripts(manifest).items()):
        if not (root / "scripts" / ref).is_file():
            findings.append(f"W2 {name}: command references missing scripts/{ref}")
        elif Path(ref).stem not in wired:
            findings.append(f"W2 {name}: unwired gate scripts/{ref}")
    return findings


def _surface_scripts_from_workflow(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = _load_yaml_mapping(path)
    steps = ((data.get("jobs") or {}).get("validate") or {}).get("steps") or []
    found: set[str] = set()
    for step in steps:
        if isinstance(step, dict):
            found |= _scripts_in_shell(str(step.get("run", "")))
    return found


def _surface_scripts_from_validate_local(path: Path) -> set[str]:
    """Scripts referenced by `Step(...)` argv tuples (AST, so comments don't count)."""
    if not path.is_file():
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "Step":
            continue
        for arg in node.args:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    found.update(SCRIPT_REF.findall(sub.value))
    return {name for name in found if "/" not in name}


def _surface_scripts_from_makefile(path: Path) -> set[str]:
    found: set[str] = set()
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("\t") or line.lstrip().startswith("#"):
            continue  # only recipe lines, and never comments
        found.update(SCRIPT_REF.findall(line))
    return {name for name in found if "/" not in name}


def _surface_scripts(root: Path, surface: str) -> set[str]:
    if surface == "ci":
        out: set[str] = set()
        for workflow in sorted(root.glob(WORKFLOW_GLOB)):
            out |= _surface_scripts_from_workflow(workflow)
        return out
    if surface == "local":
        return _surface_scripts_from_validate_local(root / "scripts" / "validate_local.py")
    return _surface_scripts_from_makefile(root / "Makefile")


def _surface_text(root: Path, surface: str) -> str:
    """Raw text of the surface's files (used for the reverse, tolerant check)."""
    if surface == "ci":
        files = sorted(root.glob(WORKFLOW_GLOB))
    elif surface == "local":
        files = [root / "scripts" / "validate_local.py"]
    else:
        files = [root / "Makefile"]
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files if p.is_file())


def check_surfaces(root: Path) -> list[str]:
    """W4: each surface must consume the manifest, and declare what it runs directly.

    Both directions matter. A surface that declares gates must actually invoke
    `scripts/run_gates.py` (otherwise the declaration is a lie), and every script a
    surface invokes *explicitly* must be declared under `surface_specific` with a
    reason — so a surface cannot grow an undeclared gate, and a declared exemption
    cannot outlive the step it describes.

    The forward direction reads argv/YAML/recipe structure (so a script named only
    in a comment does not count as run). The reverse direction is deliberately
    looser — a plain mention of `<script>.py` in the surface counts — because some
    steps build the path at runtime (e.g. validate_local's quality-score step).
    """
    path = root / VALIDATION_MANIFEST
    manifest = _load_yaml_mapping(path)
    declared_raw = manifest.get("surface_specific") or {}
    gates = manifest.get("gates") or []
    findings: list[str] = []

    for surface in SURFACES:
        runs_manifest = any(
            isinstance(entry, dict) and surface in (entry.get("runs_in") or []) for entry in gates
        )
        entries = declared_raw.get(surface) or []
        if not isinstance(entries, list):
            raise ConfigError(f"surface_specific.{surface} must be a list")
        declared: dict[str, str] = {}
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not str(entry.get("reason", "")).strip():
                raise ConfigError(
                    f"surface_specific.{surface}[{index}] needs a non-empty `reason`"
                )
            script = entry.get("script")
            if script:
                declared[str(script)] = str(entry.get("name", "?"))

        actual = _surface_scripts(root, surface)
        if runs_manifest and "run_gates.py" not in actual:
            findings.append(
                f"W4 {surface}: declares manifest gates but never runs scripts/run_gates.py"
            )
        allowed = set(declared) | {"run_gates.py"}
        for script in sorted(actual - allowed):
            findings.append(
                f"W4 {surface}: runs scripts/{script} without declaring it in "
                f"surface_specific.{surface}"
            )
        text = _surface_text(root, surface)
        for script, name in sorted(declared.items()):
            if script not in text:
                findings.append(
                    f"W4 {surface}: surface_specific entry {name!r} (scripts/{script}) is "
                    f"no longer referenced by this surface"
                )
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
    findings.extend(check_surfaces(root))
    # W5 (CR-4): silent scripts — neither surface-invoked nor transitively
    # imported. Run last so W1-W4 findings surface first; W5 is the
    # "nothing else reported, but a script exists" catch-all.
    findings.extend(check_zero_wiring(root, scripts, wired))
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
