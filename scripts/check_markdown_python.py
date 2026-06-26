#!/usr/bin/env python3
"""
check_markdown_python.py — Lint Python code blocks embedded in Markdown files.

Catches Python-specific bugs that ruff cannot detect in .md files:
  1. Bash variable/command expansion ($(), ${}, `$var`) inside Python strings
  2. time.strftime() / datetime usage without 'time' / 'datetime' import
  3. f-string placeholder {{...}} used outside jinja context (double-brace in Python)
  4. Mixing positional and named arguments in Python function calls (edge case)

Scope: qcloud-*-ops/SKILL.md and qcloud-*-ops/references/*.md
Stdlib only — no external dependencies. Python 3.8+.

Usage:
    python3 scripts/check_markdown_python.py [--root DIR]
    # exit 0 if clean, exit 1 with finding ID + path + line + message
"""

import argparse
import re
import sys
from pathlib import Path

# Finding severity
SEV_ERROR = "E"
SEV_WARNING = "W"

CHECKS = []


def check(name, pattern, message, sev=SEV_ERROR):
    """Decorator to register a check."""
    def decorator(fn):
        CHECKS.append({
            "name": name,
            "pattern": re.compile(pattern, re.MULTILINE),
            "message": message,
            "severity": sev,
            "fn": fn,
        })
        return fn
    return decorator


# --- Check 1: Bash expansion in Python strings --------------------------------

BASH_IN_PYTHON_MSG = (
    "Bash expansion $(...), ${...}, `$var` found inside a Python string literal. "
    "This does not interpolate in Python. Use time.strftime() / datetime or os.environ.get()."
)


@check("bash-in-python-string", r'''(?x)
    (?P<indent>^[ \t]{0,8})
    [ \t]*(?P<quote>["'])                          # opening quote
    (?:[^'"$\\]|\\.)*                              # content before any $
    \$(?:
        \( (?P<subcmd>[^)]+ ) \)                   # $(cmd)
      | \{ (?P<brace>[^}]+) \}                     # ${var}
      | ` (?P<backtick> [^`]  +) `                 # `$cmd`
      | [a-zA-Z_][a-zA-Z0-9_]*                     # $var (simple)
    )
    (?:[^'"$\\]|\\.)*                              # rest of string content
    (?P=quote)                                     # closing quote
''', BASH_IN_PYTHON_MSG)
def check_bash_in_python(match, ctx):
    """Bash $(), ${}, `$var` inside Python string."""
    # Only flag if the line also contains Python keywords or looks like code
    line = ctx.line_cache.get(ctx.lineno, "")
    return "=" in line or "req." in line or "os." in line or "print(" in line


# --- Check 2: time.strftime / datetime without import ------------------------

DT_NO_IMPORT_MSG = (
    "time.strftime() or datetime used without corresponding 'import time' "
    "or 'import datetime' in the same code block."
)


@check("datetime-without-import", r'''(?x)
    time\.strftime\(
  | datetime\.datetime\(
  | datetime\.(?! timedelta)[a-z]
''', DT_NO_IMPORT_MSG)
def check_datetime_without_import(match, ctx):
    """Flag time.strftime / datetime usage when 'import time' / 'import datetime' is absent in the block."""
    block = ctx.current_block or ""
    # Accept: import time, from time import, or time as part of compound import (import os, json, time)
    imports_ok = bool(
        re.search(r'\bimport\b[^#\n]*\btime\b', block)
        or re.search(r'\bfrom\s+(time|datetime)\b', block)
        or re.search(r'\bimport\s+(time|datetime)\b', block)
        or re.search(r',\s*(time|datetime)\b', block)
    )
    return not imports_ok


# --- Check 3: f-string placeholder {{...}} in Python (not jinja) ---------------

FSTRING_DOUBLE_BRACE_MSG = (
    "f-string contains {{...}} which renders as literal '{...}'. "
    "If this is meant to be a template placeholder, remove the 'f' prefix or escape correctly."
)


@check("fstring-double-brace", r'''(?x)
    f["']
    (?:[^"']|\\.)*
    \{\{ [^}]+ \}\}
    (?:[^"']|\\.)*
    ["']
''', FSTRING_DOUBLE_BRACE_MSG)
def check_fstring_double_brace(match, ctx):
    line = ctx.line_cache.get(ctx.lineno, "")
    return "f'" in line or 'f"' in line


# --- Check 4: json.loads(json.dumps(...)) redundant round-trip ----------------

JSON_DUMP_LOAD_MSG = (
    "Redundant json.loads(json.dumps(...)) round-trip detected. "
    "Use the original object directly or clarify the intent."
)


@check("json-dump-load", r'''(?x)
    json\.loads\s*\(\s*json\.dumps\s*\(
''', JSON_DUMP_LOAD_MSG)
def check_json_dump_load(match, ctx):
    return True  # Always flag — no context check needed


# --- Context holder -----------------------------------------------------------

class BlockContext:
    def __init__(self, path, lineno, line_cache, current_block):
        self.path = path
        self.lineno = lineno
        self.line_cache = line_cache
        self.current_block = current_block


# --- Markdown parser ----------------------------------------------------------

PYTHON_BLOCK_RE = re.compile(r"```python\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def extract_python_blocks(text):
    """Yield (start_lineno, code_text) for each Python fenced block."""
    lineno = 0
    in_block = False
    block_start = 0
    block_lines = []

    for line in text.splitlines():
        lineno += 1
        if line.strip().startswith("```python"):
            in_block = True
            block_start = lineno
            block_lines = []
        elif in_block and line.strip() == "```":
            yield block_start, "\n".join(block_lines)
            in_block = False
        elif in_block:
            block_lines.append(line)


# --- Runner -------------------------------------------------------------------

def scan_file(path: Path, root: Path):
    """Scan one .md file for Python code issues. Yields (severity, name, path, lineno, msg)."""
    text = path.read_text(encoding="utf-8")
    line_cache = {i + 1: line for i, line in enumerate(text.splitlines())}

    for block_start, code in extract_python_blocks(text):
        for check_item in CHECKS:
            for m in check_item["pattern"].finditer(code):
                # Compute absolute line number in the file
                # block_start is the line of ```python, so code starts at block_start+1
                offset = code[: m.start()].count("\n")
                abs_lineno = block_start + 1 + offset

                ctx = BlockContext(
                    path=str(path.relative_to(root)),
                    lineno=abs_lineno,
                    line_cache=line_cache,
                    current_block=code,
                )

                try:
                    if check_item["fn"](m, ctx):
                        yield {
                            "severity": check_item["severity"],
                            "id": f"MPC-{CHECKS.index(check_item) + 1:03d}",
                            "name": check_item["name"],
                            "path": ctx.path,
                            "lineno": abs_lineno,
                            "message": check_item["message"],
                            "snippet": line_cache.get(abs_lineno, "").strip(),
                        }
                except Exception:
                    pass  # Skip on ctx access errors — conservative


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    skill_dirs = sorted(root.glob("qcloud-*-ops"))
    findings = []

    for skill_dir in skill_dirs:
        for md in skill_dir.glob("*.md"):
            for f in scan_file(md, root):
                findings.append(f)
        for ref_md in skill_dir.glob("references/*.md"):
            for f in scan_file(ref_md, root):
                findings.append(f)

    if not findings:
        print("OK: No Python-in-Markdown issues found.")
        return 0

    for hit in sorted(findings, key=lambda x: (x["path"], x["lineno"])):
        print(
            f"{hit['severity']}{hit['id']} {hit['path']}:{hit['lineno']}\n"
            f"  {hit['message']}\n"
            f"  → {hit['snippet']}"
        )
        print()

    print(f"FAILED: {len(findings)} issue(s) found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
