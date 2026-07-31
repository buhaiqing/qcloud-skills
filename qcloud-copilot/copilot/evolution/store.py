"""EVO-1 Memory layer.

Reads the curated reflexion memory tables (``docs/failure-patterns.md`` and
``docs/success-patterns.md``) and exposes them as deduped, confidence-weighted
:class:`Pattern` objects that the decision layer (``policy``) and guard layer
(``guard``) consume.

The parser is intentionally tolerant of the multiple table shapes that live in
those docs (backticked cells, ``—`` placeholders, ``count = 0`` rows, sections
without a ``Skill`` column). Only rows that resolve to a real ``qcloud-*`` skill
are materialised as patterns; the rest are skipped so they can never pollute
routing or allowlist decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from copilot.quality.reflexion import normalize_reflexion_key

# Maps a markdown section title (normalised) to a stable Pattern.category.
SECTION_CATEGORY = {
    "cli parameter errors": "cli_parameter",
    "skill generation issues": "skill_generation",
    "cross-skill composition failures": "cross_skill",
    "runtime execution patterns": "runtime",
    "token efficiency violations": "token_efficiency",
}

# Maps a normalised header cell to a semantic Pattern field.
HEADER_SEMANTIC = {
    "skill": "skill",
    "source skill": "skill",
    "command": "command",
    "operation": "command",
    "error pattern": "error",
    "failure pattern": "error",
    "pattern": "error",
    "root cause": "root_cause",
    "fix": "fix",
    "fix pattern": "fix",
    "resolution": "fix",
    "prevention": "fix",
    "count": "count",
    "frequency": "count",
    "severity": "severity",
    "lastseen": "last_seen",
    "last seen": "last_seen",
}

SEVERITY_WEIGHT = {"critical": 1.0, "major": 0.7, "minor": 0.4}

PLACEHOLDER = "—"


@dataclass(frozen=True)
class Pattern:
    """A single curated memory record (failure or success)."""

    category: str
    skill: str
    command: str
    error: str
    fix: str
    count: int
    confidence: float
    kind: str  # "failure" | "success"


def _default_docs_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "docs" / "failure-patterns.md").exists():
            return p
    return here.parents[2]  # fallback: two levels up (qcloud-copilot)


def _clean(cell: str) -> str:
    if cell is None:
        return ""
    s = cell.strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        s = s[1:-1].strip()
    return s


def _to_int(cell: str) -> int:
    s = _clean(cell)
    if s in ("", PLACEHOLDER):
        return 0
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else 0


def _recency_factor(last_seen: str) -> float:
    """0.2..1.0; recent dates score high, unknown dates fall back to 0.6."""
    s = _clean(last_seen)
    if not s or s == PLACEHOLDER:
        return 0.6
    m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", s)
    if not m:
        return 0.6
    year, month = int(m.group(1)), int(m.group(2))
    day = int(m.group(3)) if m.group(3) else 1
    try:
        dt = datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return 0.6
    days = max(0, (datetime.now(UTC) - dt).days)
    return round(max(0.2, min(1.0, 1.0 / (1.0 + days / 60.0))), 3)


def _confidence(count: int, severity: str, last_seen: str) -> float:
    count_factor = min(1.0, count / 5.0)
    sev_weight = SEVERITY_WEIGHT.get(_clean(severity).lower() or "minor", 0.4)
    return round(min(1.0, count_factor * sev_weight * _recency_factor(last_seen)), 3)


def _norm_header(cell: str) -> str:
    return _clean(cell).lower()


def _section_category(line: str, fallback: str) -> str:
    title = re.sub(r"^#+\s*", "", line).strip()
    title = re.sub(r"^\d+\.\s*", "", title).lower().strip()
    return SECTION_CATEGORY.get(title, fallback)


def _build_map(norm_cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, h in enumerate(norm_cells):
        semantic = HEADER_SEMANTIC.get(h)
        if semantic and semantic not in mapping:
            mapping[semantic] = idx
    return mapping


def _is_separator(line: str) -> bool:
    return bool(line) and set(line) <= set("|-: ")


def _row_to_pattern(
    cells: list[str], hmap: dict[str, int], kind: str, category: str
) -> Pattern | None:
    if "skill" not in hmap:
        return None
    skill = _clean(cells[hmap["skill"]])
    if not skill or skill == PLACEHOLDER or not skill.startswith("qcloud-"):
        return None
    command = _clean(cells[hmap["command"]]) if "command" in hmap else ""
    if command == PLACEHOLDER:
        command = ""
    error = _clean(cells[hmap["error"]]) if "error" in hmap else ""
    if error == PLACEHOLDER:
        error = ""
    fix = ""
    for key in ("fix", "root_cause"):
        if key in hmap:
            fix = _clean(cells[hmap[key]])
            if fix and fix != PLACEHOLDER:
                break
    count = _to_int(cells[hmap["count"]]) if "count" in hmap else 0
    severity = _clean(cells[hmap["severity"]]) if "severity" in hmap else "minor"
    last_seen = _clean(cells[hmap["last_seen"]]) if "last_seen" in hmap else ""
    return Pattern(
        category=category,
        skill=skill,
        command=command,
        error=error,
        fix=fix,
        count=count,
        confidence=_confidence(count, severity, last_seen),
        kind=kind,
    )


def _parse_tables(text: str, kind: str) -> list[Pattern]:
    out: list[Pattern] = []
    hmap: dict[str, int] | None = None
    category = "success" if kind == "success" else "runtime"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            category = _section_category(stripped, category)
            hmap = None
            continue
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        norm = [_norm_header(c) for c in cells]
        if "skill" in norm or "source skill" in norm:
            hmap = _build_map(norm)
            continue
        if hmap is None or _is_separator(stripped):
            continue
        pat = _row_to_pattern(cells, hmap, kind, category)
        if pat:
            out.append(pat)
    return out


class EvolutionStore:
    """Reads failure/success markdown tables and deduplicates them as Patterns."""

    def __init__(
        self,
        failure_path: str | Path | None = None,
        success_path: str | Path | None = None,
    ):
        root = _default_docs_root()
        self._failure_path = (
            Path(failure_path) if failure_path else root / "docs" / "failure-patterns.md"
        )
        self._success_path = (
            Path(success_path) if success_path else root / "docs" / "success-patterns.md"
        )

    def load(self) -> list[Pattern]:
        """Return deduped patterns (failure first, then success)."""
        patterns: dict[str, Pattern] = {}
        for kind, path in (("failure", self._failure_path), ("success", self._success_path)):
            if not path.exists():
                continue
            for pat in _parse_tables(path.read_text(encoding="utf-8"), kind):
                key = normalize_reflexion_key(pat.category, pat.skill, pat.command, pat.error)
                existing = patterns.get(key)
                if existing is None or pat.count > existing.count:
                    patterns[key] = pat
        return list(patterns.values())

    # -- convenience views -------------------------------------------------

    def failures(self) -> list[Pattern]:
        return [p for p in self.load() if p.kind == "failure"]

    def successes(self) -> list[Pattern]:
        return [p for p in self.load() if p.kind == "success"]

    def by_skill(self, skill: str) -> list[Pattern]:
        return [p for p in self.load() if p.skill == skill]

    def high_confidence(self, kind: str = "failure", min_conf: float = 0.7) -> list[Pattern]:
        return [p for p in self.load() if p.kind == kind and p.confidence >= min_conf]
