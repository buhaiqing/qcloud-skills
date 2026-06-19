#!/usr/bin/env python3
"""Validate local Markdown links and explicit repository path references.

This is a lightweight, stdlib-only guard for token-efficient documentation:
when AGENTS.md links out to detailed specs, those local paths must stay
reachable. The checker intentionally ignores historical planning notes and
command-like snippets to avoid noisy false positives.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIR_PARTS = {
    ".git",
    ".github",
    ".omc",
    ".omo",
    ".codebuddy",
    "audit-results",
}

IGNORED_MARKDOWN_PREFIXES = (
    "docs/superpowers/plans/",
)

PATH_PREFIXES = (
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "docs/",
    "scripts/",
    "qcloud-",
    ".github/",
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class Finding:
    file: Path
    line: int
    target: str
    reason: str


def iter_markdown_files(root: Path) -> list[Path]:
    """Return always-loaded entry docs and top-level extracted specs.

    Product skill docs contain many historical/template relative links. This
    guard focuses on the docs that now act as navigation roots after AGENTS.md
    token compression: AGENTS.md, README.md, and top-level docs/*.md files.
    """
    candidates = [root / "AGENTS.md", root / "README.md"]
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        candidates.extend(sorted(docs_dir.glob("*.md")))

    files: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in IGNORED_DIR_PARTS for part in path.relative_to(root).parts):
            continue
        if rel.startswith(IGNORED_MARKDOWN_PREFIXES):
            continue
        files.append(path)
    return sorted(files)


def normalize_target(raw: str) -> str | None:
    target = raw.strip()
    if not target:
        return None
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith("<") and target.endswith(">"):
        return None
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return target or None


def looks_like_repo_path(text: str) -> bool:
    if any(ch.isspace() for ch in text):
        return False
    if text.startswith(("http://", "https://", "mailto:", "#", "{{", "<")):
        return False
    if "<" in text or ">" in text:
        return False
    if any(symbol in text for symbol in ("*", "|", "--", "=", "[", "]", "{", "}")):
        return False
    return text.startswith(PATH_PREFIXES)


def resolve_target(root: Path, source: Path, target: str) -> Path:
    candidate = Path(target)
    if candidate.is_absolute():
        return candidate
    if target.startswith(PATH_PREFIXES):
        return root / candidate
    return source.parent / candidate


def target_exists(root: Path, source: Path, target: str) -> bool:
    path = resolve_target(root, source, target)
    if any(part in ("*", "...") for part in path.parts):
        return True
    return path.exists()


def check_file(root: Path, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in LINK_RE.finditer(line):
            target = normalize_target(match.group(1))
            if target and not target_exists(root, path, target):
                findings.append(Finding(path, line_no, target, "missing markdown link target"))

        for match in BACKTICK_RE.finditer(line):
            raw = match.group(1).strip()
            target = normalize_target(raw)
            if not target or not looks_like_repo_path(target):
                continue
            if not target_exists(root, path, target):
                findings.append(Finding(path, line_no, target, "missing backtick path target"))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    findings: list[Finding] = []
    for path in iter_markdown_files(root):
        findings.extend(check_file(root, path))

    if findings:
        for finding in findings:
            rel = finding.file.relative_to(root).as_posix()
            print(f"{rel}:{finding.line}: {finding.reason}: {finding.target}", file=sys.stderr)
        print(f"ERROR: {len(findings)} broken Markdown path reference(s)", file=sys.stderr)
        return 1

    print("OK: Markdown local links and repository path references validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
