#!/usr/bin/env python3
"""Migrate SKILL.md frontmatter to add structured routing fields.

Phase 1 Step 1.2.3. Adds product_name / operation_aliases / param_mapping
under metadata.* for each skill based on the legacy hardcoded mapping in
qcloud-copilot/copilot/integration/skills.py.

Modes:
  --dry-run       Print diff per skill, do NOT modify files
  --apply         Modify SKILL.md files
  --root PATH     Override repo root (default: parent of scripts/)

Uses ruamel.yaml to preserve YAML formatting (comments, key order, block
scalars). Falls back to PyYAML if ruamel.yaml is unavailable.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[1]

FRONTMATTER_RE = None  # lazy; we use ruamel to parse

try:
    from ruamel.yaml import YAML  # type: ignore
    _HAS_RUAMEL = True
except ImportError:
    _HAS_RUAMEL = False


def _make_yaml() -> Any:
    if _HAS_RUAMEL:
        y = YAML(typ="rt")  # round-trip mode: preserves comments/keys/scalars
        y.preserve_quotes = True
        y.width = 1000
        # Preserve per-sequence indent (some lists use 2-space, others 4-space).
        y.indent(mapping=2, sequence=4, offset=2)
        return y
    import yaml  # type: ignore
    return yaml  # fallback


def _parse(text: str) -> tuple[Any, str]:
    """Split text into (yaml_doc, body_after). Returns (None, text) if no frontmatter."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fm_block = text[4:end]
    body_start = end + 4
    body = text[body_start:]
    y = _make_yaml()
    if _HAS_RUAMEL:
        from io import StringIO

        from ruamel.yaml.comments import CommentedMap
        data = y.load(StringIO(fm_block)) or CommentedMap()
        if not isinstance(data, CommentedMap):
            # wrap plain dict
            cm = CommentedMap()
            for k, v in data.items():
                cm[k] = v
            data = cm
    else:
        import yaml
        data = yaml.safe_load(fm_block) or {}
    return data, body


def _dump_yaml(doc: Any) -> str:
    y = _make_yaml()
    if _HAS_RUAMEL:
        from io import StringIO
        buf = StringIO()
        y.dump(doc, buf)
        return buf.getvalue().rstrip("\n")
    import yaml
    return yaml.safe_dump(doc, default_flow_style=False, sort_keys=False,
                          allow_unicode=True, width=1000).rstrip("\n")


def _derive_fields(name: str, hardcoded: dict) -> dict[str, Any]:
    """Compute the new structured fields for a given skill name."""
    products: dict[str, str] = hardcoded.get("SKILL_TO_PRODUCT", {})
    aliases: dict[tuple[str, str], str] = hardcoded.get("OPERATION_ALIAS", {})
    param_map: dict[tuple[str, str], str] = hardcoded.get("SKILL_PARAM_MAPPING", {})

    out: dict[str, Any] = {}
    if name in products:
        out["product_name"] = products[name]
    skill_aliases = {op: canonical for (s, op), canonical in aliases.items() if s == name}
    if skill_aliases:
        out["operation_aliases"] = skill_aliases
    skill_params = {op: flag for (s, op), flag in param_map.items() if s == name}
    if skill_params:
        out["param_mapping"] = skill_params
    return out


def _inject_metadata(doc: Any, new_fields: dict[str, Any]) -> bool:
    """Inject new_fields under doc['metadata']. Returns True if changed."""
    if not new_fields:
        return False
    if _HAS_RUAMEL:
        from ruamel.yaml.comments import CommentedMap
        if "metadata" not in doc or doc["metadata"] is None:
            doc["metadata"] = CommentedMap()
        meta = doc["metadata"]
    else:
        meta = doc.setdefault("metadata", {})
        if not isinstance(meta, dict):
            return False

    changed = False
    for k, v in new_fields.items():
        if k not in meta:
            meta[k] = v
            changed = True
    return changed


def migrate_file(skill_md: Path, *, dry_run: bool, hardcoded: dict) -> tuple[str, str]:
    """Migrate a single SKILL.md. Returns (original_text, new_text).

    If no changes are needed, original == new.
    """
    original = skill_md.read_text(encoding="utf-8")
    doc, body = _parse(original)
    if doc is None:
        return original, original

    name = doc.get("name") or skill_md.parent.name
    new_fields = _derive_fields(str(name), hardcoded)

    if not _inject_metadata(doc, new_fields):
        return original, original

    fm_text = _dump_yaml(doc)
    new_text = f"---\n{fm_text}\n---{body}"

    if not dry_run:
        skill_md.write_text(new_text, encoding="utf-8")
    return original, new_text


def diff_text(a: str, b: str, label: str = "") -> str:
    return "\n".join(difflib.unified_diff(
        a.splitlines(keepends=True),
        b.splitlines(keepends=True),
        fromfile=f"{label} (before)" if label else "before",
        tofile=f"{label} (after)" if label else "after",
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry-run", action="store_true", help="Print diff, do not modify")
    parser.add_argument("--apply", action="store_true", help="Modify SKILL.md files")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Repo root path")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("ERROR: must specify --dry-run or --apply", file=sys.stderr)
        sys.exit(2)

    root = Path(args.root).resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from skill_registry import load_hardcoded_from_copilot
    hardcoded = load_hardcoded_from_copilot()

    total = 0
    changed = 0
    for sk in sorted(root.glob("qcloud-*-ops/SKILL.md")):
        total += 1
        original, new = migrate_file(sk, dry_run=args.dry_run, hardcoded=hardcoded)
        if original != new:
            changed += 1
            if args.dry_run:
                label = sk.parent.name
                print(f"--- {label} ---")
                print(diff_text(original, new, label=label), end="")
                print()
    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"{mode}: {changed}/{total} skills would change / changed")
    sys.exit(0)


if __name__ == "__main__":
    main()