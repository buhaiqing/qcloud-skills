#!/usr/bin/env python3
"""TE-6: Compress GCL prompt-templates and Quality Gate safety rules.

Links product skills to qcloud-skill-generator/references/gcl-prompt-backbone.md
instead of inlining duplicate G/C/O skeletons. §4 defers to references/rubric.md
§4 (no per-op table duplication). Compresses SKILL.md Quality Gate safety rules
to a compact table pointing at rubric §4.

Usage:
    python3 scripts/te6_gcl_compress.py              # apply to all 24 skills
    python3 scripts/te6_gcl_compress.py --dry-run    # print stats only
    python3 scripts/te6_gcl_compress.py --skill qcloud-redis-ops

Pure stdlib. Idempotent — safe to re-run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKBONE = "../../qcloud-skill-generator/references/gcl-prompt-backbone.md"

GCL_META: dict[str, dict[str, str | int | bool]] = {
    "qcloud-cvm-ops": {"max_iter": 2, "cli": "cvm", "title": "CVM"},
    "qcloud-cdb-ops": {"max_iter": 2, "cli": "cdb", "title": "CDB"},
    "qcloud-clb-ops": {"max_iter": 2, "cli": "clb", "title": "CLB"},
    "qcloud-cos-ops": {"max_iter": 2, "cli": "cos", "title": "COS"},
    "qcloud-es-ops": {"max_iter": 2, "cli": "es", "title": "ES"},
    "qcloud-redis-ops": {"max_iter": 2, "cli": "redis", "title": "Redis"},
    "qcloud-tke-ops": {"max_iter": 2, "cli": "tke", "title": "TKE"},
    "qcloud-vpc-ops": {"max_iter": 2, "cli": "vpc", "title": "VPC"},
    "qcloud-cam-ops": {"max_iter": 2, "cli": "cam", "title": "CAM"},
    "qcloud-cbs-ops": {"max_iter": 2, "cli": "cbs", "title": "CBS"},
    "qcloud-ckafka-ops": {"max_iter": 2, "cli": "ckafka", "title": "CKafka"},
    "qcloud-mongodb-ops": {"max_iter": 2, "cli": "mongodb", "title": "MongoDB"},
    "qcloud-postgres-ops": {"max_iter": 2, "cli": "postgres", "title": "PostgreSQL"},
    "qcloud-cdn-ops": {"max_iter": 3, "cli": "cdn", "title": "CDN"},
    "qcloud-cls-ops": {"max_iter": 3, "cli": "cls", "title": "CLS"},
    "qcloud-scf-ops": {"max_iter": 3, "cli": "scf", "title": "SCF"},
    "qcloud-ssl-ops": {"max_iter": 3, "cli": "ssl", "title": "SSL"},
    "qcloud-agsx-ops": {"max_iter": 3, "cli": "ags", "title": "AGSX", "sdk_only": True},
    "qcloud-monitor-ops": {"max_iter": 3, "cli": "monitor", "title": "Monitor"},
    "qcloud-finops-ops": {"max_iter": 3, "cli": "billing", "title": "FinOps", "advisory": True},
    "qcloud-aiops-diagnosis": {"max_iter": 5, "cli": "monitor", "title": "AIOps", "readonly": True},
    "qcloud-proactive-inspection": {"max_iter": 3, "cli": "monitor", "title": "Inspection"},
    "qcloud-well-architected-review": {"max_iter": 5, "cli": "monitor", "title": "WA Review", "advisory": True},
    "qcloud-skill-generator": {"max_iter": 3, "cli": "n/a", "title": "Generator", "meta": True},
}

SECTION_HEAD = re.compile(r"^## (\d+)\. .+$", re.MULTILINE)
RULE_TABLE_ROW = re.compile(r"^\| (\d+) \| ([^|]+?) \| \*\*(.+?)\*\*")
RULE_HEADER = re.compile(r"^### Rule (\d+): (.+)$", re.MULTILINE)

GENERIC_AP_PATTERNS = (
    "Critic sees the user request",
    "Shared context G",
    "Critic mutates resources",
    "Silently downgrading on Safety fail",
    "Silently downgrade on Safety fail",
    "Trace not persisted",
    "Unbounded loop",
    "Carried over from [AGENTS.md",
)


def split_sections(text: str) -> dict[int, str]:
    matches = list(SECTION_HEAD.finditer(text))
    if not matches:
        return {}
    out: dict[int, str] = {}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[num] = text[start:end].rstrip()
    return out


def parse_rubric_rules(rubric_path: Path) -> list[tuple[str, str, str]]:
    if not rubric_path.is_file():
        return []
    text = rubric_path.read_text(encoding="utf-8")
    m4 = re.search(r"^## 4\. .+$", text, re.MULTILINE)
    if not m4:
        return []
    m5 = re.search(r"^## 5\. .+$", text[m4.end():], re.MULTILINE)
    block = text[m4.start(): m4.end() + m5.start()] if m5 else text[m4.start():]

    rules: list[tuple[str, str, str]] = []
    for line in block.splitlines():
        rm = RULE_TABLE_ROW.match(line.strip())
        if rm:
            gate = rm.group(3).replace("\n", " ")
            if len(gate) > 100:
                gate = gate[:97] + "..."
            rules.append((rm.group(1), rm.group(2).strip(), gate))
    if rules:
        return rules
    for rm in RULE_HEADER.finditer(block):
        rules.append((rm.group(1), rm.group(2).strip(), "see rubric §4"))
    return rules[:5]


def strip_generic_antipatterns(sec5: str) -> str:
    lines = sec5.splitlines()
    out: list[str] = []
    skip_bullet = False
    for line in lines:
        if line.startswith("## 5."):
            out.append(line)
            skip_bullet = False
            continue
        if re.match(r"^### .+-specific anti-patterns", line, re.I):
            skip_bullet = False
            out.append(line)
            continue
        if any(p in line for p in GENERIC_AP_PATTERNS):
            skip_bullet = True
            continue
        if skip_bullet and line.startswith("- ❌"):
            continue
        if skip_bullet and line.strip() == "":
            continue
        if skip_bullet and not line.startswith("- "):
            skip_bullet = False
        out.append(line)
    text = "\n".join(out)
    if "gcl-prompt-backbone" not in text:
        idx = text.find("\n", text.find("## 5."))
        if idx >= 0:
            insert = (
                f"\n\n> Generic GCL anti-patterns: [{BACKBONE}]({BACKBONE}) §4.\n"
                "> Below: **product-only** bans.\n"
            )
            text = text[: idx + 1] + insert + text[idx + 1 :]
    return text.rstrip()


def build_compact_section4(skill: str, meta: dict[str, str | int | bool]) -> str:
    title = str(meta.get("title", skill))
    lines = [
        "## 4. Per-operation variants",
        "",
        f"> **TE-6:** Pre-flight / Critic rule checks are **canonical** in "
        f"[`references/rubric.md`](rubric.md) §4 ({title} — 5 rules). "
        "Do not duplicate gate text here.",
        "",
        "| Role | Action |",
        "|---|---|",
        "| Generator | Load rubric §4; map op → rule 1–5; run gates; "
        "append to trace `preflight` |",
        "| Critic | Score rubric §3 + mark §4 rules "
        "VIOLATED / SATISFIED / NOT-APPLICABLE |",
        "| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; "
        "advisory/read-only: rubric §2 |",
    ]
    if meta.get("readonly"):
        lines.append(
            "\nDiagnosis routing: [`cross-skill-orchestration.md`]"
            "(cross-skill-orchestration.md)."
        )
    elif meta.get("meta"):
        lines.append(
            "\nCharter C1–C7: [SKILL.md §Post-Generation Self-Check]"
            "(../SKILL.md#post-generation-self-check------)."
        )
    elif skill == "qcloud-proactive-inspection":
        lines.append(
            "\nPipeline: Discovery → Assessment → Diagnosis → Recommendation → Report "
            "— [SKILL.md](../SKILL.md)."
        )
    elif skill == "qcloud-well-architected-review":
        lines.append(
            "\nWorkers: [`worker-output-schema.md`](worker-output-schema.md) + "
            "Product Worker Registry in SKILL.md."
        )
    else:
        lines.append(
            "\nAPI flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover)."
        )
    return "\n".join(lines)


def clean_section5(sec5: str) -> str:
    sec5 = strip_generic_antipatterns(sec5)
    lines = sec5.splitlines()
    out: list[str] = []
    in_product = False
    for line in lines:
        if line.startswith("## 5."):
            out.append(line)
            continue
        if line.startswith(">"):
            out.append(line)
            continue
        if re.match(r"^### .+-specific anti-patterns", line, re.I):
            in_product = True
            out.append(line)
            continue
        if line.startswith("- ❌"):
            in_product = True
            out.append(line)
            continue
        if line.startswith("|") or line.startswith("##"):
            out.append(line)
            continue
        if line.strip() == "":
            out.append(line)
            continue
        if in_product:
            out.append(line)
    return "\n".join(out).rstrip()


def fix_changelog(sec6: str) -> str:
    """Merge orphaned changelog rows; ensure 1.3.0 TE-6 §4 entry inside table."""
    sec6 = re.sub(
        r"\n---\n\| 1\.3\.0 \| 2026-06-19 \| TE-6 §4: defer per-op gates to rubric §4 only \|\n\n---",
        "",
        sec6,
    )
    sec6 = re.sub(r"\n---\n\| 1\.2\.0", "\n| 1.2.0", sec6)
    if "1.3.0" not in sec6:
        marker = "| 1.2.0 |"
        if marker in sec6:
            sec6 = sec6.replace(
                marker,
                "| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |\n" + marker,
                1,
            )
        else:
            sec6 = sec6.rstrip() + (
                "\n| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |\n"
            )
    return sec6.rstrip()


def normalize_doc(text: str) -> str:
    return re.sub(r"(---\s*\n\s*){2,}", "---\n\n", text)


def build_compact_sections(
    skill: str, meta: dict[str, str | int | bool],
) -> tuple[str, str, str, str]:
    title = str(meta["title"])
    max_iter = meta["max_iter"]
    cli = meta.get("cli", "n/a")
    notes: list[str] = []
    if meta.get("sdk_only"):
        notes.append("**SDK-only** — no `tccli ags`")
    if meta.get("readonly"):
        notes.append("**Read-only** — no mutations in trace")
    if meta.get("advisory"):
        notes.append("**Advisory** — auto-execute ⇒ Safety=0")
    if meta.get("meta"):
        notes.append("**Meta** — audits generated artifact")
    note_block = "\n".join(f"- {n}" for n in notes)

    sec1 = f"""## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton]({BACKBONE}#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `{skill}` |
| CLI | `tccli {cli} help` |
| max_iterations | {max_iter} |
{note_block}

Load rubric §4 before Execute; append gate results to trace `preflight`."""

    sec2 = f"""## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton]({BACKBONE}#2-critic-prompt-template) — no `{{{{user.request}}}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 ({title})."""

    sec3 = f"""## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton]({BACKBONE}#3-orchestrator-prompt-template).
> `max_iterations`: **{max_iter}**."""

    sec4 = build_compact_section4(skill, meta)
    return sec1, sec2, sec3, sec4


def compress_prompt(skill: str, dry_run: bool) -> tuple[int, int]:
    prompt_path = ROOT / skill / "references" / "prompt-templates.md"
    if not prompt_path.is_file():
        return 0, 0
    old = prompt_path.read_text(encoding="utf-8")
    old_lines = len(old.splitlines())
    meta = GCL_META.get(skill, {"max_iter": 3, "cli": "?", "title": skill})
    sections = split_sections(old)
    if not sections or 4 not in sections:
        print(f"  SKIP {skill}: missing §4", file=sys.stderr)
        return old_lines, old_lines

    title_line = old.splitlines()[0] if old.startswith("#") else f"# {skill} GCL Prompt Templates"
    te6 = (
        f"{title_line}\n\n"
        f"> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`]({BACKBONE}); "
        f"§4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.\n"
    )

    s1, s2, s3, s4 = build_compact_sections(skill, meta)
    sec5 = clean_section5(sections.get(5, "## 5. Anti-patterns\n"))
    sec6 = fix_changelog(sections.get(6, "## 6. Changelog\n"))
    sec7 = sections.get(7, f"## 7. See also\n\n- [`gcl-prompt-backbone.md`]({BACKBONE})\n")

    new = normalize_doc(
        te6 + "\n---\n\n" + "\n\n---\n\n".join([s1, s2, s3, s4, sec5, sec6, sec7]) + "\n"
    )
    new_lines = len(new.splitlines())
    if not dry_run:
        prompt_path.write_text(new, encoding="utf-8")
    return old_lines, new_lines


def compress_quality_gate(skill: str, dry_run: bool) -> tuple[int, int]:
    skill_path = ROOT / skill / "SKILL.md"
    rubric_path = ROOT / skill / "references" / "rubric.md"
    if not skill_path.is_file():
        return 0, 0
    old = skill_path.read_text(encoding="utf-8")
    old_lines = len(old.splitlines())
    if "## Quality Gate (GCL)" not in old:
        return old_lines, old_lines

    rules = parse_rubric_rules(rubric_path)
    if not rules:
        return old_lines, old_lines

    pat = re.compile(
        r"(### [^\n]*(?:specific safety rules|FinOps-specific rules)[^\n]*\n\n)"
        r".*?(?=\n### |\n---|\n## [^Q])",
        re.DOTALL | re.IGNORECASE,
    )
    m = pat.search(old)
    if not m:
        return old_lines, old_lines

    meta = GCL_META.get(skill, {})
    rows = "\n".join(f"| {n} | {ops} | {gate} |" for n, ops, gate in rules)
    abort = "Missing any ⇒ **Safety = 0** ⇒ **ABORT**."
    if meta.get("readonly") or meta.get("advisory"):
        abort = "Auto-execute / credential leak ⇒ **Safety = 0**; see rubric §2 for advisory thresholds."

    replacement = (
        f"{m.group(1)}"
        f"Full rules: [`references/rubric.md`](references/rubric.md) §4.\n\n"
        f"| # | Operation(s) | Gate (summary) |\n|---:|---|---|\n{rows}\n\n{abort}\n"
    )
    new = old[: m.start()] + replacement + old[m.end() :]
    new_lines = len(new.splitlines())
    if not dry_run:
        skill_path.write_text(new, encoding="utf-8")
    return old_lines, new_lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skill", action="append", dest="skills")
    args = parser.parse_args()
    skills = args.skills or sorted(GCL_META.keys())

    prompt_saved = qg_saved = 0
    for skill in skills:
        po, pn = compress_prompt(skill, args.dry_run)
        qo, qn = compress_quality_gate(skill, args.dry_run)
        ps, qs = po - pn, qo - qn
        prompt_saved += ps
        qg_saved += qs
        if ps or qs:
            print(f"  {skill}: prompt {po}→{pn} (-{ps}), QG -{qs}")

    print(f"Total saved: prompt -{prompt_saved} lines, Quality Gate -{qg_saved} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
