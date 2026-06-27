#!/usr/bin/env python3
"""Commit Hygiene Trial — collect & report.

Subcommands:
    collect  Read past N days of git log, parse trailers, append to jsonl.
    report   Read jsonl + scores, generate weekly Markdown report.

Trailer schema (non-mandatory; absent → "missing"):
    Commit-Hygiene-Verdict: ok | partial | red-line-stop
    Commit-Hygiene-Products: cvm,cos
    Commit-Hygiene-Files-Modified: 3
    Commit-Hygiene-Files-Added: 1
    Commit-Hygiene-Reason: <one-line>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import commit_hygiene_score as chs  # noqa: E402

AUDIT = _ROOT / "audit-results"
FACTS_JSONL = AUDIT / "commit-hygiene-trial.jsonl"
SCORES_JSONL = AUDIT / "commit-hygiene-trial-scores.jsonl"
DOCS = _ROOT / "docs"
INDEX_MD = DOCS / "commit-hygiene-trial-index.md"

VALID_VERDICTS = {"ok", "partial", "red-line-stop"}


def _git_log(since_iso: str) -> list[dict]:
    """Return list of commits since `since_iso`, newest first.

    Each item: {sha, subject, body, ts_iso}

    Two-pass approach for reliability over `%x00` separators:
      Pass 1: list SHAs + timestamps (single line per commit).
      Pass 2: for each SHA, fetch full message with %B (preserves newlines).
    Ponytail: simple beats clever — separate calls are slower but never
    confuse empty fields or commit-message bodies containing arbitrary
    characters.
    """
    list_out = subprocess.run(
        ["git", "log", f"--since={since_iso}", "--pretty=format:%H%x00%aI", "--no-merges"],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    shas_ts: list[tuple[str, str]] = []
    for line in list_out.splitlines():
        if not line:
            continue
        parts = line.split("\x00", 1)
        if len(parts) == 2:
            shas_ts.append((parts[0], parts[1]))

    commits: list[dict] = []
    for sha, ts in shas_ts:
        msg_out = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%B", sha],
            cwd=_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        # %B = subject\n\nbody
        if "\n\n" in msg_out:
            subject, body = msg_out.split("\n\n", 1)
        else:
            subject, body = msg_out, ""
        commits.append({"sha": sha, "subject": subject, "ts_iso": ts, "body": body})
    return commits


_TRAILER_RE = re.compile(r"^([A-Za-z0-9-]+):\s*(.*)$")


def _parse_trailers(body: str) -> dict[str, str]:
    """Extract trailing `Key: value` blocks (Git trailer format)."""
    trailers: dict[str, str] = {}
    for line in body.split("\n"):
        m = _TRAILER_RE.match(line)
        if m and m.group(1).startswith("Commit-Hygiene-"):
            trailers[m.group(1)] = m.group(2).strip()
    return trailers


def _record_from_commit(c: dict) -> dict:
    """Map a git commit to a trial record.

    Missing trailer is normalized to 'partial' so it counts toward M2
    (per P2: 'missing trailer = mild 👎, counts toward M2 but does not
    terminate'). The raw missing_trailer flag is preserved for reporting.
    """
    trailers = _parse_trailers(c["body"])
    verdict = trailers.get("Commit-Hygiene-Verdict", "")
    missing = verdict == ""
    if verdict and verdict not in VALID_VERDICTS:
        verdict = ""
        missing = True
    if missing:
        verdict = "partial"  # normalize so M2 picks it up
    products_raw = trailers.get("Commit-Hygiene-Products", "")
    products = [p.strip() for p in products_raw.split(",") if p.strip()] if products_raw else []
    try:
        files_modified = int(trailers.get("Commit-Hygiene-Files-Modified", "0"))
    except ValueError:
        files_modified = 0
    try:
        files_added = int(trailers.get("Commit-Hygiene-Files-Added", "0"))
    except ValueError:
        files_added = 0
    return {
        "commit": c["sha"][:12],
        "ts": c["ts_iso"],
        "subject": c["subject"],
        "verdict": verdict,
        "products": products,
        "files_modified": files_modified,
        "files_added": files_added,
        "reason": trailers.get("Commit-Hygiene-Reason", ""),
        "missing_trailer": missing,
    }


def cmd_collect(days: int) -> int:
    """Collect commits from the past `days` days, append to facts jsonl."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    commits = _git_log(since)
    if not commits:
        print(f"No commits in the past {days} days. Nothing to append.")
        return 0

    AUDIT.mkdir(parents=True, exist_ok=True)
    existing_shas: set[str] = set()
    if FACTS_JSONL.exists():
        for line in FACTS_JSONL.read_text(encoding="utf-8").splitlines():
            try:
                existing_shas.add(json.loads(line)["commit"])
            except (json.JSONDecodeError, KeyError):
                continue

    new_records = []
    for c in commits:
        rec = _record_from_commit(c)
        if rec["commit"] in existing_shas:
            continue
        new_records.append(rec)

    if not new_records:
        print(f"All {len(commits)} commits already in {FACTS_JSONL.name}.")
        return 0

    with FACTS_JSONL.open("a", encoding="utf-8") as f:
        for r in new_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Appended {len(new_records)} records to {FACTS_JSONL}.")
    return 0


def _load_facts() -> list[dict]:
    if not FACTS_JSONL.exists():
        return []
    out = []
    for line in FACTS_JSONL.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def cmd_score() -> dict:
    """Score all facts and append to scores jsonl. Returns current metrics."""
    facts = _load_facts()
    metrics = chs.score_window(facts)
    metrics["recommend"] = chs.recommend(metrics)
    metrics["ts"] = datetime.now(timezone.utc).isoformat()
    metrics["n_total"] = len(facts)

    AUDIT.mkdir(parents=True, exist_ok=True)
    with SCORES_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    return metrics


def _status_emoji(metrics: dict, recommend: str) -> str:
    if recommend == "rollback":
        return "🔴"
    if recommend == "extend":
        return "🟡"
    if recommend == "promote":
        return "🟢"
    return "⚪"


def _render_report(metrics: dict, recent: list[dict]) -> str:
    rec_emoji = _status_emoji(metrics, metrics["recommend"])
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    lines = [
        f"# Commit Hygiene Trial — Weekly Report {today}",
        "",
        "## Summary",
        f"- Total commits scored: **{metrics['n_total']}**",
        f"- Recommendation: {rec_emoji} **{metrics['recommend']}**",
        "",
        "## Metrics",
        "",
        "| ID | Metric | Value | Threshold | Status |",
        "|----|--------|-------|-----------|--------|",
        f"| M1 | Hard-stop violations | {metrics['m1_violations']} | = 0 | {'✅' if metrics['m1_violations'] == 0 else '❌'} |",
        f"| M2 | Granularity rollback rate | {metrics['m2_rate']:.0%} ({metrics['m2_rollback']}/{metrics['m2_total']}) | ≤ 20% | {'✅' if metrics['m2_rate'] <= 0.20 else '❌'} |",
        "",
        "## Recent Commits",
        "",
        "| Commit | Verdict | Products | Modified | Added | Reason |",
        "|--------|---------|----------|----------|-------|--------|",
    ]
    for r in recent[-10:]:
        verdict_disp = "(missing)" if r.get("missing_trailer") else r["verdict"]
        reason = r["reason"][:60].replace("|", "\\|")
        products = ",".join(r["products"]) or "—"
        lines.append(
            f"| `{r['commit']}` | {verdict_disp} | {products} | {r['files_modified']} | {r['files_added']} | {reason} |"
        )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    if metrics["recommend"] == "promote":
        lines.append("**升档** — 指标达标,规则可正式落档。")
    elif metrics["recommend"] == "extend":
        lines.append("**延长** — M2 超过 20% 阈值,继续观察下周。")
    elif metrics["recommend"] == "rollback":
        lines.append("**回退** — M1 出现违规,试运行应立即终止,规则回炉评审。")
    else:
        lines.append(f"**观察** — 累计提交数 ({metrics['n_total']}) 未达最小窗口 (5),继续累积样本。")
    lines.append("")
    return "\n".join(lines)


def cmd_report() -> int:
    """Generate the weekly Markdown report and update index."""
    metrics = cmd_score()
    facts = _load_facts()
    DOCS.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = DOCS / f"commit-hygiene-trial-report-{today}.md"
    report_path.write_text(_render_report(metrics, facts), encoding="utf-8")
    print(f"Wrote {report_path}")

    # Update index
    if INDEX_MD.exists():
        index = INDEX_MD.read_text(encoding="utf-8")
    else:
        index = "# Commit Hygiene Trial — Weekly Index\n\n| Date | Recommendation | M1 | M2 | Report |\n|-----|----------------|----|----|--------|\n"
    rec = metrics["recommend"]
    row = f"| {today} | {rec} | {metrics['m1_violations']} | {metrics['m2_rate']:.0%} | [report](commit-hygiene-trial-report-{today}.md) |\n"
    if f"commit-hygiene-trial-report-{today}.md" not in index:
        index += row
        INDEX_MD.write_text(index, encoding="utf-8")
        print(f"Updated {INDEX_MD}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit Hygiene Trial driver")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect").add_argument("--days", type=int, default=7)
    sub.add_parser("score")
    sub.add_parser("report")
    args = parser.parse_args(argv)

    if args.cmd == "collect":
        return cmd_collect(args.days)
    if args.cmd == "score":
        cmd_score()
        return 0
    if args.cmd == "report":
        return cmd_report()
    return 1


if __name__ == "__main__":
    sys.exit(main())