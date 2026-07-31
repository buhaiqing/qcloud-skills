#!/usr/bin/env python3
"""SkillRegistry — dynamic skill registration & routing.

Phase 1 module 1.2. Replaces 4 hardcoded registries in
qcloud-copilot/copilot/integration/skills.py.

Backwards compatible:
- Reads qcloud-*-ops/SKILL.md YAML frontmatter.
- When frontmatter lacks structured fields (product_name / operation_aliases /
  param_mapping / delegate_to), falls back to a hardcoded mapping (the same
  dicts the old SkillDispatcher used).
- `delegate_to` accepts either a structured YAML list of dicts OR the prose
  string from existing `related_skills`.

Public API:
    SkillEntry            dataclass
    SkillRegistry         main registry class
        from_skill_dirs(root, hardcoded=...)  → SkillRegistry
        discover()                              → list[str]
        validate(skill_name)                    → bool
        get_entry(skill_name)                   → SkillEntry
        get_product(skill_name)                 → str | None
        resolve_operation(skill, op)           → str (raises ValueError)
        resolve_param(skill, op)               → str | None
        get_dependencies(skill)                → set[str]
        get_dependents(skill)                  → set[str]
        topological_order()                    → list[str]
        route(query)                            → (skill_name, confidence)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# ---------------------------------------------------------------------------
# YAML frontmatter parsing (minimal, no PyYAML dependency)
# ---------------------------------------------------------------------------

def _simple_yaml_parse(block: str) -> dict[str, Any]:
    """Minimal YAML parser sufficient for SKILL.md frontmatter.

    Supports:
      - key: scalar
      - key: |
          multi-line block scalar (preserves newlines)
      - key: >-
          folded scalar (joined with spaces)
      - key:
          list:
            - item
          dict:
            subkey: value
    Does NOT support anchors, references, tags.
    """
    fm: dict[str, Any] = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        # block scalar indicator
        if val in ("|", "|-", "|+", ">", ">-", ">+"):
            indicator = val
            body: list[str] = []
            j = i + 1
            while j < len(lines) and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                body.append(lines[j].lstrip())
                j += 1
            if indicator.startswith(">"):
                fm[key] = " ".join(b.strip() for b in body if b.strip())
            else:
                fm[key] = "\n".join(body)
            i = j
            continue
        # nested list/dict: read indented lines
        if val == "":
            body = []
            j = i + 1
            while j < len(lines) and (lines[j].startswith("  ") or lines[j].startswith("\t") or lines[j].startswith("- ")):
                body.append(lines[j].lstrip())
                j += 1
            if body and body[0].startswith("- "):
                # list
                items = []
                for b in body:
                    if b.startswith("- "):
                        item_raw = b[2:]
                        # If item has inline `key: value`, treat as dict
                        if ":" in item_raw:
                            sub: dict[str, Any] = {}
                            sub_lines = [item_raw]
                            k = j  # look ahead for continuation
                            # collect indented continuation
                            while k < len(lines) and (lines[k].startswith("      ") or lines[k].startswith("\t")) and ":" in lines[k]:
                                sub_lines.append(lines[k].lstrip())
                                k += 1
                            _absorb_kv_block(sub, sub_lines)
                            items.append(sub)
                        else:
                            items.append(item_raw.strip())
                    elif ":" in b:
                        # continuation of previous dict item
                        if items and isinstance(items[-1], dict):
                            _absorb_kv_block(items[-1], [b])
                fm[key] = items
            elif body and ":" in body[0]:
                sub = {}
                _absorb_kv_block(sub, body)
                fm[key] = sub
            else:
                fm[key] = val
            i = j
            continue
        # plain scalar
        fm[key] = val.strip('"').strip("'")
        i += 1
    return fm


def _absorb_kv_block(d: dict[str, Any], lines: list[str]) -> None:
    """Helper: merge `key: value` lines into dict d (one level)."""
    for ln in lines:
        if ":" not in ln:
            continue
        k, _, v = ln.partition(":")
        d[k.strip()] = v.strip().strip('"').strip("'")


def parse_frontmatter(text: str) -> dict[str, Any]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(m.group(1)) or {}
    except ImportError:
        return _simple_yaml_parse(m.group(1))


# ---------------------------------------------------------------------------
# Intent keyword extraction
# ---------------------------------------------------------------------------

def _camel_split(token: str) -> list[str]:
    """Split CamelCase / PascalCase into lowercase word parts."""
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", token)
    return [p.lower() for p in parts if p]


def _load_intent_keywords(skill_dir: Path, description: str) -> list[str]:
    """backtick API names from description + curated intent from eval_queries.json."""
    backtick = re.findall(r"`([^`]+)`", description)
    eq = skill_dir / "assets" / "eval_queries.json"
    intents: list[str] = []
    if eq.exists():
        try:
            data = json.loads(eq.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data, dict):
            data = data.get("queries", [])
        intents = [q["intent"] for q in data if isinstance(q, dict) and q.get("intent")]
    keywords = backtick + intents
    seen: set[str] = set()
    return [k for k in keywords if not (k in seen or seen.add(k))]


# ---------------------------------------------------------------------------
# SkillEntry
# ---------------------------------------------------------------------------

@dataclass
class SkillEntry:
    name: str
    path: Path
    cli_applicability: str
    description: str
    intent_keywords: list[str]
    # structured list[dict] from frontmatter `delegate_to`, or [] if prose
    delegate_to: list[dict[str, Any]]
    product_name: str
    operation_aliases: dict[str, str]
    param_mapping: dict[str, str]
    version: str
    last_updated: str


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """Single source of truth for skill routing & metadata."""

    def __init__(self, entries: dict[str, SkillEntry]):
        self._entries = entries
        self._keyword_index = self._build_keyword_index(entries)

    # ---- factory -----------------------------------------------------------

    @classmethod
    def from_skill_dirs(cls, root: Path, hardcoded: dict | None = None) -> SkillRegistry:
        hc = hardcoded or {}
        products: dict[str, str] = dict(hc.get("SKILL_TO_PRODUCT", {}))
        aliases: dict[tuple[str, str], str] = dict(hc.get("OPERATION_ALIAS", {}))
        param_map: dict[tuple[str, str], str] = dict(hc.get("SKILL_PARAM_MAPPING", {}))

        entries: dict[str, SkillEntry] = {}
        for sk in sorted(root.glob("qcloud-*-ops/SKILL.md")):
            fm = parse_frontmatter(sk.read_text(encoding="utf-8"))
            if not fm:
                continue
            name = str(fm.get("name") or sk.parent.name)
            desc = str(fm.get("description", ""))
            intent = _load_intent_keywords(sk.parent, desc)
            meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}

            # delegate_to: prefer structured YAML list; else prose
            d_to_raw = fm.get("delegate_to", "") or ""
            if isinstance(d_to_raw, list):
                delegate_to = [d for d in d_to_raw if isinstance(d, dict)]
            elif isinstance(d_to_raw, str) and d_to_raw.strip():
                # prose: keep as single {"skill": "<text>"} for legacy compat
                delegate_to = [{"skill": d_to_raw.strip(), "reason": "(legacy prose)", "trigger": "legacy"}]
            else:
                delegate_to = []

            # operation_aliases: prefer frontmatter dict; else from hardcoded
            op_aliases_fm = fm.get("operation_aliases")
            op_aliases: dict[str, str] = dict(op_aliases_fm) if isinstance(op_aliases_fm, dict) else {}
            for (s, op), canonical in aliases.items():
                if s == name:
                    op_aliases.setdefault(op, canonical)

            # param_mapping
            pm_fm = fm.get("param_mapping")
            pm: dict[str, str] = dict(pm_fm) if isinstance(pm_fm, dict) else {}
            for (s, op), flag in param_map.items():
                if s == name:
                    pm.setdefault(op, flag)

            # product_name: prefer frontmatter top-level, else metadata, else hardcoded
            prod = str(
                fm.get("product_name")
                or (meta.get("product_name") if isinstance(meta, dict) else "")
                or products.get(name, "")
            )

            # cli_applicability / version / last_updated: prefer metadata.*, fallback top-level
            cli_app = str(
                (meta.get("cli_applicability") if isinstance(meta, dict) else "")
                or fm.get("cli_applicability", "")
            )
            ver = str(
                (meta.get("version") if isinstance(meta, dict) else "")
                or fm.get("version", "")
            )
            lu = str(
                (meta.get("last_updated") if isinstance(meta, dict) else "")
                or fm.get("last_updated", "")
            )

            entries[name] = SkillEntry(
                name=name,
                path=sk.parent,
                cli_applicability=cli_app,
                description=desc,
                intent_keywords=intent,
                delegate_to=delegate_to,
                product_name=prod,
                operation_aliases=op_aliases,
                param_mapping=pm,
                version=ver,
                last_updated=lu,
            )
        return cls(entries)

    # ---- introspection -----------------------------------------------------

    def discover(self) -> list[str]:
        return sorted(self._entries.keys())

    def validate(self, skill_name: str) -> bool:
        return skill_name in self._entries

    def get_entry(self, skill_name: str) -> SkillEntry:
        if skill_name not in self._entries:
            raise KeyError(skill_name)
        return self._entries[skill_name]

    def get_product(self, skill_name: str) -> str | None:
        e = self._entries.get(skill_name)
        if e is None:
            return None
        return e.product_name or None

    # ---- operation resolution ---------------------------------------------

    def resolve_operation(self, skill_name: str, operation: str) -> str:
        """Return canonical (kebab-case) operation name. Raises ValueError for unknown skill."""
        e = self._entries.get(skill_name)
        if e is None:
            raise ValueError(f"Unknown skill: {skill_name}")
        return e.operation_aliases.get(operation, operation)

    def resolve_param(self, skill_name: str, operation: str) -> str | None:
        e = self._entries.get(skill_name)
        if e is None:
            return None
        return e.param_mapping.get(operation)

    # ---- dependency graph --------------------------------------------------

    def get_dependencies(self, skill_name: str) -> set[str]:
        e = self._entries.get(skill_name)
        if e is None:
            return set()
        deps: set[str] = set()
        for d in e.delegate_to:
            if isinstance(d, dict) and d.get("skill"):
                deps.add(str(d["skill"]))
        return deps

    def get_dependents(self, skill_name: str) -> set[str]:
        result: set[str] = set()
        for name in self._entries:
            if skill_name in self.get_dependencies(name):
                result.add(name)
        return result

    def topological_order(self) -> list[str]:
        """Kahn's algorithm. Skills with no deps come first; cycles append sorted tail."""
        in_deg: dict[str, int] = {n: 0 for n in self._entries}
        adj: dict[str, set[str]] = {n: set() for n in self._entries}
        for name in self._entries:
            for dep in self.get_dependencies(name):
                if dep in self._entries:
                    adj[dep].add(name)
                    in_deg[name] += 1
        queue = sorted([n for n, d in in_deg.items() if d == 0])
        order: list[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for nxt in sorted(adj[n]):
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self._entries):
            remaining = sorted(set(self._entries) - set(order))
            order.extend(remaining)
        return order

    # ---- routing -----------------------------------------------------------

    def route(self, query: str) -> tuple[str, float]:
        """Return (best_skill_name, confidence) by token overlap on intent_keywords.

        Returns ("", 0.0) when no skill matches.
        """
        tokens = {t.lower() for t in re.findall(r"[A-Za-z0-9]+", query)}
        if not tokens:
            return ("", 0.0)
        scores: dict[str, float] = {}
        for name, kw_tokens in self._keyword_index.items():
            hits = tokens & kw_tokens
            if hits:
                # confidence = fraction of query tokens matched, weighted by hit density
                scores[name] = len(hits) / max(len(tokens), 1)
        if not scores:
            return ("", 0.0)
        best_name, best_score = max(scores.items(), key=lambda kv: (kv[1], -len(kv[0])))
        return (best_name, float(best_score))

    # ---- internal ----------------------------------------------------------

    def _build_keyword_index(self, entries: dict[str, SkillEntry]) -> dict[str, set[str]]:
        idx: dict[str, set[str]] = {}
        for name, e in entries.items():
            tokens: set[str] = set()
            for kw in e.intent_keywords:
                tokens.add(kw.lower())
                for part in _camel_split(kw):
                    if len(part) >= 3:
                        tokens.add(part)
            idx[name] = tokens
        return idx


# ---------------------------------------------------------------------------
# Public helper: load hardcoded fallback from the legacy copilot module
# ---------------------------------------------------------------------------

def load_hardcoded_from_copilot() -> dict[str, Any]:
    """Read KNOWN_SKILLS/SKILL_TO_PRODUCT/OPERATION_ALIAS/SKILL_PARAM_MAPPING
    from qcloud-copilot/copilot/integration/skills.py at import time.

    Returns empty dict if module is not importable.
    """
    try:
        # Walk up to project root
        here = Path(__file__).resolve().parent
        root = here.parent
        copilot_pkg = root / "qcloud-copilot"
        if not copilot_pkg.exists():
            return {}
        # Add qcloud-copilot to sys.path so the relative import
        # `from copilot.models import ...` works.
        import sys as _sys
        copilot_root = str(copilot_pkg.resolve())
        if copilot_root not in _sys.path:
            _sys.path.insert(0, copilot_root)
        # Pre-register the copilot package and its models submodule
        # so that `from copilot import models` resolves.
        import importlib
        if "copilot" not in _sys.modules:
            copilot_pkg_init = copilot_pkg / "copilot" / "__init__.py"
            if copilot_pkg_init.exists():
                import importlib.util
                spec_pkg = importlib.util.spec_from_file_location(
                    "copilot", copilot_pkg / "copilot" / "__init__.py",
                    submodule_search_locations=[str(copilot_pkg / "copilot")],
                )
                if spec_pkg is not None and spec_pkg.loader is not None:
                    mod_pkg = importlib.util.module_from_spec(spec_pkg)
                    _sys.modules["copilot"] = mod_pkg
                    spec_pkg.loader.exec_module(mod_pkg)
        # Load the integration/skills.py module via file path
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "copilot_integration_skills",
            copilot_pkg / "copilot" / "integration" / "skills.py",
        )
        if spec is None or spec.loader is None:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {
            "SKILL_TO_PRODUCT": dict(getattr(mod, "SKILL_TO_PRODUCT", {})),
            "OPERATION_ALIAS": dict(getattr(mod, "OPERATION_ALIAS", {})),
            "SKILL_PARAM_MAPPING": dict(getattr(mod, "SKILL_PARAM_MAPPING", {})),
        }
    except (ImportError, AttributeError, FileNotFoundError, SyntaxError):
        return {}


if __name__ == "__main__":
    # CLI smoke test
    import sys
    root = Path(__file__).resolve().parent.parent
    reg = SkillRegistry.from_skill_dirs(root, hardcoded=load_hardcoded_from_copilot())
    print(f"discovered {len(reg.discover())} skills")
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        name, conf = reg.route(q)
        print(f"route({q!r}) → {name} (conf={conf:.3f})")