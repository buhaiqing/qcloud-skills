from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


DOCS_FAILURE_PATTERNS = Path("docs/failure-patterns.md")
SCRATCH_DIR = Path.cwd() / ".runtime" / "reflexion"


def write_reflexion(
    category: str,
    skill: str,
    command: str,
    error: str,
    fix: str,
) -> None:
    """Append a failure pattern to the daily scratch file.

    This prevents test runs from polluting docs/failure-patterns.md.
    Call aggregate_scratch() at session end to merge into the canonical file.
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scratch_file = SCRATCH_DIR / f"{today}-scratch.md"

    if not scratch_file.exists():
        scratch_file.write_text("# Reflexion Scratch\n\n")

    # Escape pipe characters in free-text fields
    safe_cmd = command[:50].replace("|", "/")
    safe_error = error[:80].replace("|", "/")
    safe_fix = fix[:80].replace("|", "/")

    entry = f"\n| {category} | {skill} | {safe_cmd} | {safe_error} | {safe_fix} | 1 | true |"
    scratch_file.open("a").write(entry)


def aggregate_scratch(date: str | None = None) -> int:
    """Read scratch file(s) and merge into docs/failure-patterns.md.

    Dedup by (category, skill, error): if a row already exists, increment its count.
    Otherwise append as new row before the Usage Guidelines section.

    Args:
        date: If provided, only aggregate this date's scratch file (format: "2026-07-10").
              If None, aggregate all scratch files in SCRATCH_DIR.

    Returns:
        Number of new entries merged (0 if all were duplicates).
    """
    if not DOCS_FAILURE_PATTERNS.exists():
        return 0

    scratch_files = []
    if date:
        sf = SCRATCH_DIR / f"{date}-scratch.md"
        if sf.exists():
            scratch_files.append(sf)
    else:
        scratch_files = sorted(SCRATCH_DIR.glob("*-scratch.md"))

    if not scratch_files:
        return 0

    # Parse existing patterns from docs/failure-patterns.md
    existing = DOCS_FAILURE_PATTERNS.read_text()
    lines = existing.splitlines(keepends=True)

    # Build (category, skill, error) -> line index from scratch-format rows
    existing_rows: dict[tuple[str, str, str], int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            not stripped.startswith("|")
            or stripped.startswith("|-")
            or stripped.startswith("| Scenario")
            or stripped.startswith("| Skill")
        ):
            continue
        parts = [p.strip() for p in stripped.split("|") if p.strip()]
        if len(parts) >= 6:
            # (category, skill, error) is fields 0, 1, 3
            existing_rows[(parts[0], parts[1], parts[3])] = i

    known_keys: set[tuple[str, str, str]] = set(existing_rows.keys())
    merged = 0
    rows_to_append: list[str] = []

    for sf in scratch_files:
        for line in sf.read_text().splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|-") or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < 6:
                continue
            category, skill, command, error, fix = (
                parts[0],
                parts[1],
                parts[2],
                parts[3],
                parts[4],
            )
            key = (category, skill, error)
            if key in known_keys:
                # Duplicate — increment count in the existing row (once per key)
                line_idx = existing_rows.get(key)
                if line_idx is not None and line_idx >= 0:
                    cells = lines[line_idx].split("|")
                    if len(cells) > 6:
                        old_val = cells[6].strip()
                        if old_val.isdigit():
                            new_val = str(int(old_val) + 1)
                            cells[6] = cells[6].replace(old_val, new_val, 1)
                            lines[line_idx] = "|".join(cells)
                    existing_rows[key] = -1  # mark as already incremented
            else:
                known_keys.add(key)
                merged += 1
                rows_to_append.append(
                    f"| {category} | {skill} | {command} | {error} | {fix} | 1 | true |\n"
                )

    if merged > 0 or any(v < 0 for v in existing_rows.values()):
        if rows_to_append:
            # Insert new rows before the Usage Guidelines section
            insert_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("## Usage Guidelines"):
                    insert_idx = i
                    break
            if insert_idx is not None:
                lines.insert(insert_idx, "\n")  # blank line separator
                for row in reversed(rows_to_append):
                    lines.insert(insert_idx, row)
            else:
                lines.append("\n")
                lines.extend(rows_to_append)

        DOCS_FAILURE_PATTERNS.write_text("".join(lines))

    return merged
