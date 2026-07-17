#!/usr/bin/env python3
"""Success Patterns Miner — aggregate PASS traces into layered success memory.

Usage:
  # Daily batch: consume pending + merge into hot/warm/cold layers
  python3 scripts/success_pattern_mine.py --batch

  # Full scan: replay all existing gcl-trace-*.json into initial store
  python3 scripts/success_pattern_mine.py --full-scan

  # Dry-run: show what would happen without writing
  python3 scripts/success_pattern_mine.py --batch --dry-run

Architecture (see docs/superpowers/specs/success-patterns-design.md):
  - hot layer:   success-patterns.md   (≤ 200 rows, active)
  - warm layer:  success-patterns-warm.md  (≤ 500 rows, semi-active)
  - cold layer:  success-patterns-cold.md  (≤ 2000 rows, archived)
  - pending log: audit-results/gcl-success-pending.jsonl

Self-verification (runs after every merge):
  V1: no duplicate keys across layers
  V2: hot ≤ 200, warm ≤ 500
  V3: no key exists in two layers simultaneously
  V4: all required fields present
  V5: last_hit format YYYY-MM-DD
"""

from __future__ import annotations

import argparse
import fcntl
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit-results"

PENDING_PATH = AUDIT_DIR / "gcl-success-pending.jsonl"
PENDING_LOCK = Path("/tmp/success-patterns-pending.lock")
HOT_PATH = ROOT / "docs" / "success-patterns.md"
WARM_PATH = ROOT / "docs" / "success-patterns-warm.md"
COLD_PATH = ROOT / "docs" / "success-patterns-cold.md"

HOT_LIMIT = 200
WARM_LIMIT = 500
COLD_LIMIT = 2000
SILENCE_THRESHOLD_DAYS = 30   # hot → warm
COLD_THRESHOLD_DAYS = 90       # warm → cold

# Fields required in every stored entry
_REQUIRED_FIELDS = (
    "skill", "operation", "command_signature",
    "count", "first_hit", "last_hit",
)
# Fields that form the unique key
_KEY_FIELDS = ("skill", "operation", "command_signature")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class SuccessEntry:
    __slots__ = (
        "skill", "operation", "command_signature", "full_command",
        "iter", "count", "first_hit", "last_hit",
        "scores", "avg_iter",
    )

    def __init__(self, **kwargs: Any) -> None:
        for f in self.__slots__:
            setattr(self, f, kwargs.get(f))
        # defaults
        if self.count is None:
            self.count = 1
        if self.first_hit is None:
            self.first_hit = kwargs.get("timestamp", "")[:10]
        if self.last_hit is None:
            self.last_hit = self.first_hit
        if self.avg_iter is None:
            self.avg_iter = float(self.iter) if self.iter is not None else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__slots__}

    @classmethod
    def from_pending(cls, raw: dict[str, Any]) -> "SuccessEntry":
        """Build entry from a pending JSON line."""
        cmd = raw.get("command", "")
        sig = cmd[:80] if cmd else ""
        scores = raw.get("scores") or {}
        iter_count = raw.get("iter") or 1
        return cls(
            skill=raw.get("skill") or "",
            operation=raw.get("operation") or "",
            command_signature=sig,
            full_command=cmd,
            iter=iter_count,
            count=1,
            first_hit=raw.get("timestamp", "")[:10],
            last_hit=raw.get("timestamp", "")[:10],
            scores=scores,
            avg_iter=float(iter_count),
        )


# ---------------------------------------------------------------------------
# Parsing (md → dict)
# ---------------------------------------------------------------------------

def _parse_table_row(line: str) -> list[str]:
    cells, current = [], ""
    in_backtick = False
    for ch in line:
        if ch == "`":
            in_backtick = not in_backtick
        elif ch == "|" and not in_backtick:
            cells.append(current.strip())
            current = ""
        else:
            current += ch
    cells.append(current.strip())
    return [c.strip() for c in cells[1:-1]]


def _parse_section(heading: str, lines: list[str]) -> dict[str, SuccessEntry]:
    """Parse one md file (hot/warm/cold) into {key: SuccessEntry}."""
    patterns: dict[str, SuccessEntry] = {}
    table_headers: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            table_headers = []
            continue
        if stripped.startswith("|") and "---" not in stripped and "Skill" in stripped:
            table_headers = [h.lower().replace(" ", "").replace("-", "") for h in _parse_table_row(stripped)]
            continue
        if stripped.startswith("|") and "---" not in stripped and table_headers:
            cells = _parse_table_row(stripped)
            if len(cells) < 4:
                continue
            row: dict[str, str] = {}
            for h, v in zip(table_headers, cells):
                row[h] = v

            skill = row.get("skill", "").strip().strip("`")
            operation = row.get("operation", "").strip().strip("`")
            sig = row.get("commandsignature", "").strip().strip("`")
            if not skill:
                continue

            count_str = row.get("count", "0").strip()
            try:
                count = int(count_str)
            except ValueError:
                count = 0

            last_hit = row.get("lasthit", row.get("lasthit", "")).strip()
            first_hit = row.get("firsthit", "").strip()

            # Parse scores JSON from cell
            scores: dict[str, float] = {}
            scores_raw = row.get("scores", "").strip()
            if scores_raw and scores_raw not in ("{}", ""):
                try:
                    scores = json.loads(scores_raw.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    scores = {}

            avg_iter_str = row.get("avgiter", "1.0").strip()
            try:
                avg_iter = float(avg_iter_str)
            except ValueError:
                avg_iter = 1.0

            key = (skill, operation, sig)
            patterns[key] = SuccessEntry(
                skill=skill,
                operation=operation,
                command_signature=sig,
                full_command=row.get("fullcommand", "").strip(),
                iter=1,
                count=count,
                first_hit=first_hit or last_hit,
                last_hit=last_hit,
                scores=scores,
                avg_iter=avg_iter,
            )
    return patterns


def load_layer(path: Path) -> dict[str, SuccessEntry]:
    if not path.exists():
        return {}
    return _parse_section(path.stem, path.read_text(encoding="utf-8").splitlines())


def load_all_layers() -> tuple[
    dict[str, SuccessEntry],
    dict[str, SuccessEntry],
    dict[str, SuccessEntry],
]:
    return load_layer(HOT_PATH), load_layer(WARM_PATH), load_layer(COLD_PATH)


# ---------------------------------------------------------------------------
# Serialisation (dict → md)
# ---------------------------------------------------------------------------

def _scores_to_str(scores: dict[str, float]) -> str:
    if not scores:
        return "{}"
    # Compact JSON without spaces
    return json.dumps(scores, separators=(",", ":"))


def _emit_table(entries: dict[str, SuccessEntry], title: str) -> list[str]:
    headers = [
        "Skill", "Operation", "CommandSignature", "FullCommand",
        "Iter", "Count", "FirstHit", "LastHit", "Scores", "AvgIter"
    ]
    lines = [title, "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for key, e in sorted(entries.items(), key=lambda x: (-x[1].count, x[0][0])):
        s = e.skill or "—"
        o = e.operation or "—"
        sig = (e.command_signature or "").replace("|", "\\|")[:80]
        full = (e.full_command or "").replace("|", "\\|")
        # Truncate full_command to avoid huge cells
        if len(full) > 200:
            full = full[:200] + "..."
        lines.append(
            f"| `{s}` | `{o}` | `{sig}` | `{full}` | "
            f"{e.iter} | {e.count} | {e.first_hit} | {e.last_hit} | "
            f"{_scores_to_str(e.scores)} | {e.avg_iter:.1f} |"
        )
    return lines


def _emit_header(title: str) -> list[str]:
    now = datetime.now().strftime("%Y-%m-%d")
    return [
        f"# Success Patterns — {title}",
        "",
        f"> **Generated**: {now} by success_pattern_mine.py",
        "> **Purpose**: Positive knowledge — what command/parameter combinations have succeeded.",
        "> **Query**: use `scripts/success_pattern_retrieve.py` for retrieval.",
        "",
    ]


def save_layer(path: Path, entries: dict[str, SuccessEntry], title: str) -> None:
    lines = _emit_header(title) + _emit_table(entries, "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Pending log
# ---------------------------------------------------------------------------

def load_pending(path: Path) -> list[dict[str, Any]]:
    """Load all pending entries from jsonl."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"WARN: skip malformed line in {path.name}", file=sys.stderr)
    return entries


def write_pending_with_lock(path: Path, entry: dict[str, Any]) -> None:
    """Append one entry to pending log (called by gcl_runner.py after PASS)."""
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def make_key(e: SuccessEntry) -> tuple[str, str, str]:
    return (e.skill or "", e.operation or "", e.command_signature or "")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def days_between(older: str, newer: str) -> int:
    """Days from older to newer. Returns 0 if either is empty/invalid."""
    if not older or not newer:
        return 0
    try:
        d1 = datetime.strptime(older[:10], "%Y-%m-%d")
        d2 = datetime.strptime(newer[:10], "%Y-%m-%d")
        return max(0, (d2 - d1).days)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Merge algorithm (core)
# ---------------------------------------------------------------------------

def merge_batch(
    pending: list[dict[str, Any]],
    hot: dict[str, SuccessEntry],
    warm: dict[str, SuccessEntry],
    cold: dict[str, SuccessEntry],
) -> tuple[dict, dict, dict]:
    """Merge pending entries into hot/warm/cold layers.

    Algorithm:
      1. Substitution: same-key entry from pending updates hot/warm (count++, last_hit++)
      2. Silence eviction: hot full → oldest last_hit entries demoted to warm
      3. Warm cap: warm full → oldest last_hit entries archived to cold
      4. Cold cap: cold full → lowest count entries pruned

    Returns (hot, warm, cold) — mutated in-place for clarity but returned.
    """
    for raw in pending:
        if not raw.get("skill") or not raw.get("command"):
            continue
        entry = SuccessEntry.from_pending(raw)
        key = make_key(entry)

        # --- Substitution: check hot first ---
        if key in hot:
            h = hot[key]
            h.count += 1
            h.last_hit = today_str()
            # Weighted average of avg_iter
            total = h.avg_iter * (h.count - 1) + float(entry.iter or 1)
            h.avg_iter = total / h.count
            # Update scores with latest
            if entry.scores:
                h.scores = entry.scores
            # Update iter to latest
            h.iter = entry.iter
            # Update full_command if changed
            if entry.full_command:
                h.full_command = entry.full_command

        # --- Substitution: check warm ---
        elif key in warm:
            # Can it be revived to hot? (revival window: ≤ SILENCE_THRESHOLD_DAYS since last warm hit)
            gap = days_between(warm[key].last_hit, today_str())
            if gap <= SILENCE_THRESHOLD_DAYS:
                # Revive: move from warm to hot
                warm[key].last_hit = today_str()
                warm[key].count += 1
                hot[key] = warm[key]
                del warm[key]
            else:
                # No revival: create new entry in hot (warm gets stale, will be evicted later)
                hot[key] = entry

        # --- Fresh entry ---
        else:
            hot[key] = entry

    # --- Silence eviction: hot cap ---
    if len(hot) > HOT_LIMIT:
        # Sort by last_hit ascending (oldest first), then count ascending (least-hit first)
        evict_keys = sorted(
            hot.keys(),
            key=lambda k: (hot[k].last_hit or "", hot[k].count),
        )
        needed = len(hot) - HOT_LIMIT
        for k in evict_keys[:needed]:
            e = hot[k]
            # Move to warm if not already there
            if k not in warm:
                warm[k] = e
            else:
                # Merge into warm: keep higher count
                if warm[k].count < e.count:
                    warm[k] = e
            del hot[k]

    # --- Warm cap: evict to cold ---
    if len(warm) > WARM_LIMIT:
        evict_keys = sorted(
            warm.keys(),
            key=lambda k: (warm[k].last_hit or "", warm[k].count),
        )
        needed = len(warm) - WARM_LIMIT
        for k in evict_keys[:needed]:
            cold[k] = warm[k]
            del warm[k]

    # --- Cold cap: hard prune lowest count ---
    if len(cold) > COLD_LIMIT:
        keep_keys = sorted(
            cold.keys(),
            key=lambda k: -cold[k].count,
        )[:COLD_LIMIT]
        # Save entries before clearing, then rebuild
        kept_entries = {k: cold[k] for k in keep_keys}
        cold.clear()
        cold.update(kept_entries)

    return hot, warm, cold


# ---------------------------------------------------------------------------
# Self-verification
# ---------------------------------------------------------------------------

def self_verify(
    hot: dict[str, SuccessEntry],
    warm: dict[str, SuccessEntry],
    cold: dict[str, SuccessEntry],
) -> list[str]:
    """Run V1-V5 checks. Returns list of error strings (empty = pass)."""
    errors: list[str] = []

    # V1: no duplicate keys across layers
    for name_a, d_a in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for name_b, d_b in [("hot", hot), ("warm", warm), ("cold", cold)]:
            if name_a >= name_b:
                continue
            dup = set(d_a.keys()) & set(d_b.keys())
            if dup:
                errors.append(
                    f"V1 FAIL: duplicate keys across {name_a} and {name_b}: {list(dup)[:3]}"
                )

    # V2: capacity limits
    if len(hot) > HOT_LIMIT:
        errors.append(f"V2 FAIL: hot has {len(hot)} entries (limit {HOT_LIMIT})")
    if len(warm) > WARM_LIMIT:
        errors.append(f"V2 FAIL: warm has {len(warm)} entries (limit {WARM_LIMIT})")
    if len(cold) > COLD_LIMIT:
        errors.append(f"V2 FAIL: cold has {len(cold)} entries (limit {COLD_LIMIT})")

    # V3: key uniqueness (redundant with V1, but explicit)
    all_keys = set(hot.keys()) | set(warm.keys()) | set(cold.keys())
    total = len(hot) + len(warm) + len(cold)
    if len(all_keys) != total:
        errors.append(f"V3 FAIL: total entries {total} != unique keys {len(all_keys)}")

    # V4: required fields
    for layer_name, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            for field in _REQUIRED_FIELDS:
                if getattr(e, field, None) is None:
                    errors.append(
                        f"V4 FAIL: key {k} in {layer_name} missing field '{field}'"
                    )

    # V5: last_hit date format
    for layer_name, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            lh = e.last_hit
            if lh and not DATE_RE.match(str(lh)):
                errors.append(
                    f"V5 FAIL: key {k} in {layer_name} invalid last_hit: '{lh}'"
                )

    return errors


# ---------------------------------------------------------------------------
# Full scan (initial load from existing gcl traces)
# ---------------------------------------------------------------------------

def full_scan() -> tuple[dict[str, SuccessEntry], dict[str, SuccessEntry], dict[str, SuccessEntry]]:
    """Replay all existing gcl-trace-*.json (status=PASS) into initial layers."""
    hot: dict[str, SuccessEntry] = {}
    warm: dict[str, SuccessEntry] = {}
    cold: dict[str, SuccessEntry] = {}

    audit_dir = ROOT / "audit-results"
    if not audit_dir.is_dir():
        print("No audit-results/ directory found, returning empty layers.", file=sys.stderr)
        return hot, warm, cold

    trace_files = sorted(audit_dir.glob("gcl-trace-*.json"))
    print(f"Scanning {len(trace_files)} trace files...")
    pending: list[dict[str, Any]] = []
    for tf in trace_files:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        final = data.get("final") or {}
        if final.get("status") != "PASS":
            continue
        # Extract skill and operation from trace
        skill = data.get("skill") or ""
        # Try to derive operation from the first generator command
        iters = data.get("iterations") or []
        operation = ""
        command = ""
        if iters:
            gen = iters[0].get("generator") or {}
            cmd = gen.get("command") or ""
            # Extract operation name (e.g., "RunInstances" from "tccli cvm RunInstances ...")
            m = re.search(r"tccli\s+\w+\s+(\w+)", cmd)
            if m:
                operation = m.group(1)
            command = cmd

        if not skill:
            continue
        pending.append({
            "skill": skill,
            "operation": operation,
            "command": command,
            "iter": final.get("iter", 1),
            "scores": {},
            "timestamp": tf.stem.split("gcl-trace-")[1] if "gcl-trace-" in tf.stem else today_str(),
        })

    print(f"Found {len(pending)} PASS traces.")
    return merge_batch(pending, hot, warm, cold)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_batch(args: argparse.Namespace) -> int:
    # Acquire lock on pending file
    lock_path = PENDING_LOCK
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
    except (IOError, OSError) as e:
        print(f"WARN: could not acquire lock {lock_path}: {e}", file=sys.stderr)

    try:
        pending = load_pending(PENDING_PATH)
        if not pending:
            print("No pending entries to merge.")
            return 0

        print(f"Loaded {len(pending)} pending entries.")
        hot, warm, cold = load_all_layers()
        print(f"Existing layers: hot={len(hot)}, warm={len(warm)}, cold={len(cold)}")

        hot, warm, cold = merge_batch(pending, hot, warm, cold)
        errors = self_verify(hot, warm, cold)

        if errors:
            print("SELF-VERIFICATION FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  {err}", file=sys.stderr)
            if not args.dry_run:
                # Don't write corrupt data
                return 1

        print(f"After merge: hot={len(hot)}, warm={len(warm)}, cold={len(cold)}")

        if args.dry_run:
            print("[dry-run] Would write:")
            print(f"  hot  -> {HOT_PATH} ({len(hot)} entries)")
            print(f"  warm -> {WARM_PATH} ({len(warm)} entries)")
            print(f"  cold -> {COLD_PATH} ({len(cold)} entries)")
            print("  pending file not cleared in dry-run mode.")
        else:
            save_layer(HOT_PATH, hot, "Hot Layer")
            save_layer(WARM_PATH, warm, "Warm Layer")
            save_layer(COLD_PATH, cold, "Cold Layer")
            # Clear pending
            PENDING_PATH.write_text("", encoding="utf-8")
            print(f"Wrote: {HOT_PATH.relative_to(ROOT)}")
            print(f"Wrote: {WARM_PATH.relative_to(ROOT)}")
            print(f"Wrote: {COLD_PATH.relative_to(ROOT)}")
            print(f"Cleared: {PENDING_PATH.relative_to(ROOT)}")

        return 0
    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


def cmd_full_scan(args: argparse.Namespace) -> int:
    print("Full scan: replaying all existing gcl-trace-*.json...")
    hot, warm, cold = full_scan()
    errors = self_verify(hot, warm, cold)
    if errors:
        print("SELF-VERIFICATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[dry-run] Would write: hot={len(hot)}, warm={len(warm)}, cold={len(cold)}")
        return 0

    save_layer(HOT_PATH, hot, "Hot Layer")
    save_layer(WARM_PATH, warm, "Warm Layer")
    save_layer(COLD_PATH, cold, "Cold Layer")
    print(f"Written: {HOT_PATH.relative_to(ROOT)} ({len(hot)} entries)")
    print(f"Written: {WARM_PATH.relative_to(ROOT)} ({len(warm)} entries)")
    print(f"Written: {COLD_PATH.relative_to(ROOT)} ({len(cold)} entries)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    sub = parser.add_subparsers(dest="cmd", required=True)

    batch = sub.add_parser("batch", help="Daily batch: merge pending → layers")
    batch.set_defaults(func=cmd_batch)

    full = sub.add_parser("full-scan", help="Full scan: replay all PASS traces into initial store")
    full.set_defaults(func=cmd_full_scan)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
