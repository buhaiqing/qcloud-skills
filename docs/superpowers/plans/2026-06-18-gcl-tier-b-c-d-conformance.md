# GCL Tier B/C/D Conformance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all 24 skills to consistent GCL Tier A conformance (8 rubric sections + 7 prompt sections + `## Quality Gate (GCL)` SKILL.md section) by fleshing out 19 under-conforming skills and adding GCL artifacts to `qcloud-skill-generator`.

**Architecture:**
- Establish one canonical Tier A template (already exists at `qcloud-cdb-ops/references/rubric.md` and `qcloud-cos-ops/references/prompt-templates.md` as best-of-breed examples).
- Add CI enforcement so conformance is durable: `scripts/check_gcl_conformance.py` walks all 24 skills and fails the build when any skill is missing artifacts or sections.
- Tier B skills copy §1 Scope, §2 Dimensions, §3 Per-dim Checklist, §5 Output Schema, §6 Worked Examples from the canonical template, then customize the §4 product-specific safety rules (which already exist).
- Tier C skills (`aiops-diagnosis`, `proactive-inspection`, `well-architected-review`) get renumbered/expanded to the canonical format. `well-architected-review` is already at 6/7 sections — just add §6 worked examples (currently §6 is Changelog).
- Tier D skill (`qcloud-skill-generator`) gets the full set: rubric.md (with 5 meta-skill-specific safety rules), prompt-templates.md, and `## Quality Gate (GCL)` SKILL.md section noting `GCL applicability: optional` and what "the loop" means for a meta-skill (the generated skill must pass Charter C7; the generator itself has no destructive cloud operations).

**Tech Stack:** Python 3.10+ stdlib only (per AGENTS.md TE-1); markdown editing; no new dependencies.

**Reference docs:**
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
- [qcloud-cdb-ops/references/rubric.md](../../qcloud-cdb-ops/references/rubric.md) — canonical Tier A rubric (8 sections)
- [qcloud-cos-ops/references/prompt-templates.md](../../qcloud-cos-ops/references/prompt-templates.md) — canonical Tier A prompt (7 sections)
- [qcloud-cvm-ops/SKILL.md `## Quality Gate (GCL)`](../../qcloud-cvm-ops/SKILL.md#quality-gate-gcl) — canonical SKILL.md chapter

---

## File Structure

**New files (this plan):**
- `scripts/check_gcl_conformance.py` — CI gate; one script replaces ad-hoc shell loops
- `qcloud-skill-generator/references/rubric.md` — Tier D artifact
- `qcloud-skill-generator/references/prompt-templates.md` — Tier D artifact
- `scripts/gcl_conformance_test.py` — unit tests for `check_gcl_conformance.py`

**Modified files (this plan):**
- 15 Tier B skills' `references/rubric.md` (flesh out to 8 sections)
- 15 Tier B skills' `references/prompt-templates.md` (flesh out to 7 sections)
- 15 Tier B skills' `SKILL.md` (expand `## Quality Gate (GCL)` to Tier A pattern: add "When the loop runs" + "Decision flow" + "Worked example")
- `qcloud-aiops-diagnosis/references/{rubric.md,prompt-templates.md}` — renumber/expand
- `qcloud-proactive-inspection/references/{rubric.md,prompt-templates.md}` — renumber/expand
- `qcloud-well-architected-review/references/{rubric.md,prompt-templates.md}` — add §6 worked examples (currently misnumbered as §6 Changelog)
- `qcloud-skill-generator/SKILL.md` — add `## Quality Gate (GCL)` section
- `.github/workflows/validate-skills.yml` — add Charter C7 enforcement step
- `AGENTS.md` — bump Phase 4.1 (Tier B/C/D conformance) with completion date

**Untouched:**
- `scripts/gcl_runner.py`, `scripts/gcl_runner_test.py`, `scripts/gcl_alarm_wire.py`, `scripts/gcl_trace_aggregate.py` — already complete

---

## Phase 1: CI Enforcement Gate

Without a machine-readable conformance check, every future PR risks regressing. Phase 1 adds the gate before any Tier B/C/D work, so subsequent tasks can run it locally to validate their work.

### Task 1.1: Create the conformance checker

**Files:**
- Create: `scripts/check_gcl_conformance.py`
- Test: `scripts/gcl_conformance_test.py`

**Background:** The audit script must encode what "Tier A" means:
- Every skill in `AGENTS.md` §8 must exist as a directory.
- Every skill must have `references/rubric.md` and `references/prompt-templates.md`.
- `references/rubric.md` must contain 8 numbered sections (`^## [1-8]\.`).
- `references/prompt-templates.md` must contain 7 numbered sections (`^## [1-7]\.`).
- `SKILL.md` must contain `^## Quality Gate (GCL)$` heading.

- [ ] **Step 1.1.1: Write the failing test (skill list from AGENTS.md)**

```python
# scripts/gcl_conformance_test.py
from __future__ import annotations

import unittest
from pathlib import Path

import check_gcl_conformance as gclc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class SkillListTests(unittest.TestCase):
    def test_24_skills_from_agents_md(self) -> None:
        """The conformance checker must enumerate the same 24 skills declared in AGENTS.md §8."""
        expected = {
            "qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-clb-ops", "qcloud-cos-ops",
            "qcloud-es-ops", "qcloud-redis-ops", "qcloud-tke-ops", "qcloud-vpc-ops",
            "qcloud-cam-ops", "qcloud-cdn-ops", "qcloud-cbs-ops", "qcloud-cls-ops",
            "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-mongodb-ops",
            "qcloud-postgres-ops", "qcloud-ssl-ops", "qcloud-agsx-ops",
            "qcloud-finops-ops", "qcloud-monitor-ops", "qcloud-aiops-diagnosis",
            "qcloud-proactive-inspection", "qcloud-well-architected-review",
            "qcloud-skill-generator",
        }
        self.assertEqual(gclc.GCL_SKILLS, expected)


class ConformanceTests(unittest.TestCase):
    def test_all_24_pass(self) -> None:
        """Once this plan completes, the conformance check passes on all 24 skills."""
        result = gclc.check_all(ROOT)
        failing = [r for r in result if not r["ok"]]
        self.assertEqual(
            failing, [],
            f"{len(failing)} skills fail conformance: {[r['skill'] for r in failing]}",
        )

    def test_rubric_section_count(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertEqual(
                    r["rubric_sections"], 8,
                    f"{r['skill']} rubric has {r['rubric_sections']} sections, expected 8",
                )

    def test_prompt_section_count(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertEqual(
                    r["prompt_sections"], 7,
                    f"{r['skill']} prompt-templates has {r['prompt_sections']} sections, expected 7",
                )

    def test_quality_gate_present(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertTrue(
                    r["has_quality_gate"],
                    f"{r['skill']} SKILL.md missing '## Quality Gate (GCL)' section",
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1.1.2: Run the test to verify it fails (no module yet)**

```bash
cd scripts && python3 -m unittest gcl_conformance_test 2>&1 | tail -10
# Expected: ModuleNotFoundError: No module named 'check_gcl_conformance'
```

- [ ] **Step 1.1.3: Write the conformance checker**

```python
#!/usr/bin/env python3
"""GCL Tier-A conformance checker (CI gate for plan 2026-06-18-gcl-tier-b-c-d-conformance).

Validates every skill in ``AGENTS.md`` §8 has the three GCL artifacts at Tier A quality:
- ``references/rubric.md`` with 8 numbered sections (§1 Scope, §2 Dimensions,
  §3 Per-dim checklist, §4 Product-specific rules, §5 Output schema, §6 Worked examples,
  §7 Changelog, §8 See also)
- ``references/prompt-templates.md`` with 7 numbered sections (§1 Generator,
  §2 Critic, §3 Orchestrator, §4 Per-op variants, §5 Anti-patterns, §6 Changelog,
  §7 See also)
- ``SKILL.md`` with ``## Quality Gate (GCL)`` heading

Exit codes:
  0 — all skills conform
  1 — at least one skill fails conformance (CI failure)
  2 — repository layout unexpected
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Mirrors AGENTS.md §8. Single source of truth — when AGENTS.md changes,
# update this set and re-run check.
GCL_SKILLS: frozenset[str] = frozenset({
    "qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-clb-ops", "qcloud-cos-ops",
    "qcloud-es-ops", "qcloud-redis-ops", "qcloud-tke-ops", "qcloud-vpc-ops",
    "qcloud-cam-ops", "qcloud-cdn-ops", "qcloud-cbs-ops", "qcloud-cls-ops",
    "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-mongodb-ops",
    "qcloud-postgres-ops", "qcloud-ssl-ops", "qcloud-agsx-ops",
    "qcloud-finops-ops", "qcloud-monitor-ops", "qcloud-aiops-diagnosis",
    "qcloud-proactive-inspection", "qcloud-well-architected-review",
    "qcloud-skill-generator",
})

EXPECTED_RUBRIC_SECTIONS = 8  # §1..§8
EXPECTED_PROMPT_SECTIONS = 7  # §1..§7
_NUMBERED_HEADING = re.compile(r"^##\s+(\d+)\.\s+\S", re.MULTILINE)
_QUALITY_GATE = re.compile(r"^##\s+Quality Gate \(GCL\)\s*$", re.MULTILINE)


def _count_numbered_sections(text: str, target: int) -> int:
    """Return the highest-numbered section heading; -1 if none.

    Conformance rule: sections 1..target must all be present, and the highest
    present number must equal target (no gaps).
    """
    matches = [int(m.group(1)) for m in _NUMBERED_HEADING.finditer(text)]
    if not matches:
        return 0
    # All sections 1..target must appear at least once.
    return max(matches) if set(range(1, target + 1)).issubset(set(matches)) else 0


def check_skill(root: Path, skill: str) -> dict[str, Any]:
    """Return a per-skill conformance report. ``ok`` is True iff all three artifacts conform."""
    skill_dir = root / skill
    rubric_path = skill_dir / "references" / "rubric.md"
    prompt_path = skill_dir / "references" / "prompt-templates.md"
    skill_path = skill_dir / "SKILL.md"

    rubric_text = rubric_path.read_text(encoding="utf-8") if rubric_path.exists() else ""
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    rubric_sections = _count_numbered_sections(rubric_text, EXPECTED_RUBRIC_SECTIONS)
    prompt_sections = _count_numbered_sections(prompt_text, EXPECTED_PROMPT_SECTIONS)
    has_quality_gate = bool(_QUALITY_GATE.search(skill_text))

    rubric_ok = bool(rubric_path.exists()) and rubric_sections == EXPECTED_RUBRIC_SECTIONS
    prompt_ok = bool(prompt_path.exists()) and prompt_sections == EXPECTED_PROMPT_SECTIONS
    skill_ok = bool(skill_path.exists()) and has_quality_gate

    return {
        "skill": skill,
        "rubric_sections": rubric_sections,
        "prompt_sections": prompt_sections,
        "has_quality_gate": has_quality_gate,
        "rubric_ok": rubric_ok,
        "prompt_ok": prompt_ok,
        "skill_ok": skill_ok,
        "ok": rubric_ok and prompt_ok and skill_ok,
    }


def check_all(root: Path) -> list[dict[str, Any]]:
    """Run the full conformance sweep; returns one report per skill in GCL_SKILLS."""
    return [check_skill(root, skill) for skill in sorted(GCL_SKILLS)]


def cmd_check(args: argparse.Namespace) -> int:
    reports = check_all(args.root)
    failing = [r for r in reports if not r["ok"]]
    summary = {
        "total": len(reports),
        "passing": len(reports) - len(failing),
        "failing": len(failing),
        "failing_skills": [r["skill"] for r in failing],
    }
    if args.json:
        print(json.dumps({"summary": summary, "reports": reports}, indent=2))
    else:
        print(f"GCL conformance: {summary['passing']}/{summary['total']} skills conform.")
        if failing:
            print(f"\nFAILING ({len(failing)}):")
            for r in failing:
                reasons = []
                if not r["rubric_ok"]:
                    reasons.append(f"rubric={r['rubric_sections']}/8")
                if not r["prompt_ok"]:
                    reasons.append(f"prompt={r['prompt_sections']}/7")
                if not r["skill_ok"]:
                    reasons.append("no Quality Gate")
                print(f"  - {r['skill']}: {', '.join(reasons)}")
    return 1 if failing else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.set_defaults(func=cmd_check)
    return p


def main() -> int:
    return build_parser().parse_args().func()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 1.1.4: Run the test to verify it now passes on the canonical skills**

```bash
cd scripts && python3 -m unittest gcl_conformance_test -v 2>&1 | tail -10
# Expected: 4 tests pass — cvm/cdb/clb/cos/tke conform. The test_all_24_pass
# will FAIL (19 skills failing) — that's the audit baseline.
```

- [ ] **Step 1.1.5: Commit**

```bash
git add scripts/check_gcl_conformance.py scripts/gcl_conformance_test.py
git commit -m "feat(gcl): add Tier-A conformance checker (Phase 1 CI gate)"
```

### Task 1.2: Wire the checker into CI

**Files:**
- Modify: `.github/workflows/validate-skills.yml` (append step)

- [ ] **Step 1.2.1: Add the conformance check to the workflow**

Append after the existing `GCL alarm wire plan` step:

```yaml
      - name: GCL Tier-A conformance (Charter C7)
        run: |
          python3 scripts/check_gcl_conformance.py
```

- [ ] **Step 1.2.2: Run locally to confirm it shows the baseline 19 failures**

```bash
cd /Users/bohaiqing/opensource/git/qcloud-skills && python3 scripts/check_gcl_conformance.py 2>&1 | tail -25
# Expected output: "GCL conformance: 5/24 skills conform." plus 19 failing entries
```

- [ ] **Step 1.2.3: Commit**

```bash
git add .github/workflows/validate-skills.yml
git commit -m "ci(gcl): run Tier-A conformance check on every PR"
```

---

## Phase 2: Tier B Rubric Flesh-Out (8 skills × 5 sections each)

Each Tier B rubric currently has only §4 (safety rules) and §7 (changelog). Phases 2.1-2.8 copy the canonical template (8 sections) and adapt the new sections to the product.

**Canonical template:** `qcloud-cdb-ops/references/rubric.md` (8 sections, 18471 bytes) is the cleanest Tier A reference. Open it as the starting point for every Phase 2 task.

### Task 2.1: qcloud-redis-ops rubric flesh-out

**Files:**
- Modify: `qcloud-redis-ops/references/rubric.md` (4040 → ~14000 bytes)

- [ ] **Step 2.1.1: Open the canonical rubric and the current Redis rubric side-by-side**

```bash
diff -u qcloud-cdb-ops/references/rubric.md qcloud-redis-ops/references/rubric.md | head -200
```

Note: cdb-ops has §1 Scope, §2 Dimensions, §3 Per-dim Checklist, §5 Output Schema, §6 Worked Examples that Redis is missing.

- [ ] **Step 2.1.2: Copy §1 Scope and adapt**

Insert at the top of `qcloud-redis-ops/references/rubric.md` (after the frontmatter quote block):

```markdown
## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every Redis mutation operation invoked by this skill: `CreateInstances`, `DestroyInstances`, `IsolateInstance`, `ModifyInstanceSpec`, `UpgradeInstance`, `ResetPassword`, `ClearInstance` (FLUSHALL/FLUSHDB), `BackupDownload` | Pure read operations (`DescribeInstances`, `DescribeInstanceMonitorBigKey`, `DescribeInstanceParamRecords`) — scored at the discretion of the Orchestrator; recommend max_iter=1, no hard abort |
| Batch operations (any op with `len(InstanceIds) > 1`) | Cross-skill delegations handled by `qcloud-cvm-ops` / `qcloud-clb-ops` (CLB ↔ Redis cluster peering) |
| Operations routed to SDK fallback when `tccli` fails | Validation-only polling loops (`DescribeInstances` after `CreateInstances`) — these are part of the parent op's trace, not standalone scored runs |

If the operation is not in the left column, the Orchestrator MAY skip the GCL loop and
return directly (audit trail is still recommended for destructive reads that may influence
later mutations, e.g. `DescribeInstances` before `DestroyInstances`).
```

- [ ] **Step 2.1.3: Insert §2 Dimensions, §3 Per-dim Checklist, §5 Output Schema, §6 Worked Examples**

Insert before `## 4. Redis-specific safety rules`. Use the cdb-ops versions as the template and replace each dimension's product-specific scoring table with Redis-specific checks. Required sections:

- `## 2. Five rubric dimensions (mandatory)` — same as cdb-ops; in the per-dimension table, replace CDB-specific examples (e.g., "IsolateDBInstance", "DropDB") with Redis-specific ones (e.g., "DestroyInstances", "ClearInstance").
- `## 3. Per-dimension scoring checklist` — 5 sub-sections (Correctness, Safety, Idempotency, Traceability, Spec Compliance). Each must have a Score 1 / Score 0.5 / Score 0 column. Reference `redis run command not found`, `TENCENTCLOUD_SECRET_KEY leak`, `FLUSHALL not idempotent` as Redis-specific examples.
- `## 5. Output schema (returned by Critic)` — same JSON template as cdb-ops §5; populate `rule_violations` example with Redis rule references.
- `## 6. Worked examples` — at least 3 examples (PASS on `DescribeInstances`, SAFETY_FAIL on `ClearInstance` (FLUSHALL without confirmation), RETRY on `ResetPassword` on non-existent account).

- [ ] **Step 2.1.4: Insert `## 8. See also` at the bottom (between §7 Changelog and end)**

```markdown
## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-redis-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
```

- [ ] **Step 2.1.5: Run conformance and tests**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep redis-ops
# Expected: "redis-ops" no longer in failing list (8/8 rubric sections)
cd scripts && python3 -m unittest gcl_conformance_test 2>&1 | tail -3
```

- [ ] **Step 2.1.6: Commit**

```bash
git add qcloud-redis-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-redis-ops rubric to Tier A (8 sections)"
```

### Task 2.2: qcloud-es-ops rubric flesh-out

**Files:**
- Modify: `qcloud-es-ops/references/rubric.md` (3451 → ~14000 bytes)

- [ ] **Step 2.2.1: Repeat Task 2.1 steps for qcloud-es-ops**

Same pattern. ES-specific safety rule examples:
- `DeleteCluster` — irreversibly removes indexed data; check for snapshots first
- `DeleteIndex` — data loss; require confirmation with index name and doc count
- `UpdateInstance` (vertical scaling) — triggers cluster restart; brief unavailability window
- `RestartInstance` — same
- `ModifyIndex` (settings changes) — affects search behavior; not destructive but high impact

ES-specific correctness examples: `DescribeInstances` returns `Status=2` (green), `InstanceType` matches request, region/zone match.

- [ ] **Step 2.2.2: Commit**

```bash
git add qcloud-es-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-es-ops rubric to Tier A (8 sections)"
```

### Task 2.3: qcloud-vpc-ops rubric flesh-out

**Files:**
- Modify: `qcloud-vpc-ops/references/rubric.md` (4040 → ~14000 bytes)

- [ ] **Step 2.3.1: Repeat Task 2.1 steps for qcloud-vpc-ops**

VPC-specific safety rule examples (already in §4):
- `DeleteVpc` cascade
- `DeleteSubnet` with running resources
- `ReleaseAddresses` (EIP)
- `DeleteRouteTable` / `DeleteRoutes` (default route)
- `DeleteSecurityGroup`

VPC-specific correctness: `DescribeVpcs` returns empty after DeleteVpc; route table reflects deletion; SG rules list matches expected after DeleteRules.

- [ ] **Step 2.3.2: Commit**

```bash
git add qcloud-vpc-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-vpc-ops rubric to Tier A (8 sections)"
```

### Task 2.4: qcloud-cam-ops rubric flesh-out

**Files:**
- Modify: `qcloud-cam-ops/references/rubric.md` (3884 → ~14000 bytes)

- [ ] **Step 2.4.1: Repeat Task 2.1 steps for qcloud-cam-ops**

CAM-specific safety rule examples:
- `DeleteUser` — irreversible; check attached policies, access keys, group memberships first
- `DetachUserPolicy` — silently removes permissions; user may still have other policies but listing them is required
- `DeletePolicy` — affects all attached users/groups/roles; list all attachments before delete
- `RotateAccessKey` — invalidates the old key immediately; warn that running services may break
- `DeleteRole` — affects any service assuming it

- [ ] **Step 2.4.2: Commit**

```bash
git add qcloud-cam-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-cam-ops rubric to Tier A (8 sections)"
```

### Task 2.5: qcloud-cbs-ops rubric flesh-out

**Files:**
- Modify: `qcloud-cbs-ops/references/rubric.md` (4819 → ~14000 bytes)

- [ ] **Step 2.5.1: Repeat Task 2.1 steps for qcloud-cbs-ops**

CBS-specific safety rule examples:
- `TerminateDisks` — irreversible; warn data loss; require snapshot first
- `ResizeDisk` (shrink) — forbidden for most disk types; warn data loss
- `CreateSnapshot` — not destructive but accumulates cost; warn retention
- `ApplySnapshot` (rollback) — overwrites current data
- `UnattachDisk` — instance loses access; not destructive but high impact

- [ ] **Step 2.5.2: Commit**

```bash
git add qcloud-cbs-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-cbs-ops rubric to Tier A (8 sections)"
```

### Task 2.6: qcloud-ckafka-ops rubric flesh-out

**Files:**
- Modify: `qcloud-ckafka-ops/references/rubric.md` (4691 → ~14000 bytes)

- [ ] **Step 2.6.1: Repeat Task 2.1 steps for qcloud-ckafka-ops**

CKafka-specific safety rule examples:
- `DeleteInstance` — irreversible; warn consumer offset loss
- `DeleteTopic` — irreversibly removes topic + data + offsets
- `ModifyTopic` — broker rebalance; brief unavailability
- `CreateConsumer` — not destructive but accumulates offsets; warn retention
- `DeleteConsumerGroup` — removes offset commits; in-flight consumers fail

- [ ] **Step 2.6.2: Commit**

```bash
git add qcloud-ckafka-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-ckafka-ops rubric to Tier A (8 sections)"
```

### Task 2.7: qcloud-mongodb-ops rubric flesh-out

**Files:**
- Modify: `qcloud-mongodb-ops/references/rubric.md` (3913 → ~14000 bytes)

- [ ] **Step 2.7.1: Repeat Task 2.1 steps for qcloud-mongodb-ops**

MongoDB-specific safety rule examples:
- `TerminateDBInstance` — irreversible; warn data + oplog loss
- `DropDB` — MongoDB has no UNDROP; data + indexes gone
- `TerminateDBInstances` (batch) — fleet wipe
- `ModifyDBInstanceSpec` (downgrade) — may exceed current data size; check
- `DropCollection` — collection gone; warn indexes gone too

- [ ] **Step 2.7.2: Commit**

```bash
git add qcloud-mongodb-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-mongodb-ops rubric to Tier A (8 sections)"
```

### Task 2.8: qcloud-postgres-ops rubric flesh-out

**Files:**
- Modify: `qcloud-postgres-ops/references/rubric.md` (3307 → ~14000 bytes)

- [ ] **Step 2.8.1: Repeat Task 2.1 steps for qcloud-postgres-ops**

Postgres-specific safety rule examples:
- `TerminateDBInstance` — irreversible
- `DropDB` — DDL with no UNDROP in standard PG
- `ModifyDBInstanceSpec` (downgrade storage) — may fail if data > new size
- `ModifyAccountPrivileges` (`REVOKE ALL`) — silently removes access for running apps
- `IsolateDBInstance` — moves to recycle bin; warn retention window

- [ ] **Step 2.8.2: Commit**

```bash
git add qcloud-postgres-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-postgres-ops rubric to Tier A (8 sections)"
```

---

## Phase 3: Tier B Recommended-Skill Rubric Flesh-Out (6 skills)

### Task 3.1: qcloud-cdn-ops rubric flesh-out

**Files:**
- Modify: `qcloud-cdn-ops/references/rubric.md` (3417 → ~14000 bytes)

- [ ] **Step 3.1.1: Repeat Task 2.1 steps for qcloud-cdn-ops**

CDN-specific safety rule examples:
- `DeleteCdnDomain` — DNS cutover; warn propagation delay
- `PurgeUrlsCache` / `PurgePathCache` — brief cache miss storm; warn QPS impact
- `PushUrlsCache` — prefetch cost
- `DisableCdnDomain` — silent cutover; warn users hit origin directly
- `ModifyCdnConfig` (HTTPS cert swap) — warn brief TLS handshake failures

- [ ] **Step 3.1.2: Commit**

```bash
git add qcloud-cdn-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-cdn-ops rubric to Tier A (8 sections)"
```

### Task 3.2: qcloud-cls-ops rubric flesh-out

**Files:**
- Modify: `qcloud-cls-ops/references/rubric.md` (3422 → ~14000 bytes)

- [ ] **Step 3.2.1: Repeat Task 2.1 steps for qcloud-cls-ops**

CLS-specific safety rule examples:
- `DeleteLogset` — irreversibly removes ALL topics + indexed data
- `DeleteTopic` — irreversibly removes topic + retention data
- `ModifyTopic` (retention reduction) — historical data truncated
- `CreateIndex` (full-text) — accumulates cost; warn retention × traffic
- `DeleteIndex` — search queries on that index fail until recreated

- [ ] **Step 3.2.2: Commit**

```bash
git add qcloud-cls-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-cls-ops rubric to Tier A (8 sections)"
```

### Task 3.3: qcloud-scf-ops rubric flesh-out

**Files:**
- Modify: `qcloud-scf-ops/references/rubric.md` (3512 → ~14000 bytes)

- [ ] **Step 3.3.1: Repeat Task 2.1 steps for qcloud-scf-ops**

SCF-specific safety rule examples:
- `DeleteFunction` — code + versions + triggers gone
- `DeleteNamespace` — affects all functions in namespace
- `UpdateFunctionCode` — overwrites current; warn rollback path is git tag, not API
- `UpdateFunctionConfiguration` (memory reduction) — may OOM
- `DeleteTrigger` — event source no longer fires; silently breaks async workflows

- [ ] **Step 3.3.2: Commit**

```bash
git add qcloud-scf-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-scf-ops rubric to Tier A (8 sections)"
```

### Task 3.4: qcloud-ssl-ops rubric flesh-out

**Files:**
- Modify: `qcloud-ssl-ops/references/rubric.md` (3709 → ~14000 bytes)

- [ ] **Step 3.4.1: Repeat Task 2.1 steps for qcloud-ssl-ops**

SSL-specific safety rule examples:
- `DeleteCertificates` — SSL handshake fails for any domain bound to this cert
- `ReplaceCertificate` — brief TLS handshake failures during propagation
- `BindCertificate` (to wrong CLB) — wrong cert served; browser warnings
- `UnbindCertificate` — domains lose HTTPS
- `ModifyCertificateProject` (move between projects) — RBAC changes; access may be lost

- [ ] **Step 3.4.2: Commit**

```bash
git add qcloud-ssl-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-ssl-ops rubric to Tier A (8 sections)"
```

### Task 3.5: qcloud-agsx-ops rubric flesh-out

**Files:**
- Modify: `qcloud-agsx-ops/references/rubric.md` (3254 → ~14000 bytes)

- [ ] **Step 3.5.1: Repeat Task 2.1 steps for qcloud-agsx-ops**

Note: `qcloud-agsx-ops` is **SDK-only** (per AGENTS.md §8). The rubric's Spec Compliance section MUST include a check that the operation was invoked via Python SDK (not `tccli`, since tccli does not expose this product). Reference `references/cli-behavior.md` in the skill for verification commands.

AGSX-specific safety rule examples:
- `DeleteAgentPool` — all agents in pool lose registration
- `DeleteApplication` — affects running containers
- `ModifyApplication` (replicas reduction) — may orphan in-flight tasks
- `DeleteConfigMap` — pods that consume it fail to start
- `RollbackApplication` — not destructive but warn current state lost

- [ ] **Step 3.5.2: Commit**

```bash
git add qcloud-agsx-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-agsx-ops rubric to Tier A (8 sections, SDK-only)"
```

### Task 3.6: qcloud-monitor-ops rubric flesh-out

**Files:**
- Modify: `qcloud-monitor-ops/references/rubric.md` (3929 → ~14000 bytes)

- [ ] **Step 3.6.1: Repeat Task 2.1 steps for qcloud-monitor-ops**

Monitor-specific safety rule examples:
- `DeleteAlarmPolicy` — alarms silently stop firing; may go unnoticed
- `UnbindAlarmRuleResource` — resources lose alarm coverage
- `ModifyAlarmPolicy` (threshold drift) — alert noise or missed incidents
- `CreateAlarmNotice` with no receivers — alarms fire but no one notified
- `SetDefaultAlarmPolicy` — affects ALL unbinding instances; broad blast radius

- [ ] **Step 3.6.2: Commit**

```bash
git add qcloud-monitor-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-monitor-ops rubric to Tier A (8 sections)"
```

---

## Phase 4: Tier B Optional-Skill Rubric (1 skill)

### Task 4.1: qcloud-finops-ops rubric flesh-out

**Files:**
- Modify: `qcloud-finops-ops/references/rubric.md` (3167 → ~14000 bytes)

- [ ] **Step 4.1.1: Repeat Task 2.1 steps for qcloud-finops-ops**

FinOps-specific safety rule examples (read-mostly skill — safety rules emphasize "do not auto-execute billing changes"):
- `ModifyBudget` (threshold reduction) — may trigger false alarms
- `CreateCostAllocationTag` — affects billing reports retroactively
- `DeleteBillSummary` — historical data lost (rare but irreversible)
- `RenewInstances` — auto-renew flips; may not be reversible easily
- `TerminateInstances` invoked from FinOps recommendation — double-confirm; cross-skill delegation to cvm-ops

Note: This skill is `optional`, so the rubric's `correctness = 1.0 required` for destructive should remain at the standard 0.5 threshold. Document this in §2 explicitly: "FinOps rarely performs destructive ops directly; when it does (e.g., terminating idle resources), the threshold tightens to 1.0."

- [ ] **Step 4.1.2: Commit**

```bash
git add qcloud-finops-ops/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-finops-ops rubric to Tier A (8 sections)"
```

---

## Phase 5: Tier B Prompt-Templates Flesh-Out (15 skills × 3 sections each)

Each Tier B prompt currently has 4 sections. Phase 5 fleshes out the prompts to 7 sections matching `qcloud-cos-ops/references/prompt-templates.md`.

**Canonical template:** `qcloud-cos-ops/references/prompt-templates.md` (14887 bytes, 7 sections).

The 3 missing sections are: §1 Generator (currently may be condensed), §2 Critic (currently may be condensed), §5 Anti-patterns (banned) — and §6 Changelog + §7 See also (currently §6 is just Changelog + See also combined).

### Task 5.1: qcloud-redis-ops prompt-templates flesh-out

**Files:**
- Modify: `qcloud-redis-ops/references/prompt-templates.md` (1931 → ~14000 bytes)

- [ ] **Step 5.1.1: Open canonical prompt and diff**

```bash
diff -u qcloud-cos-ops/references/prompt-templates.md qcloud-redis-ops/references/prompt-templates.md | head -200
```

- [ ] **Step 5.1.2: Expand §1 Generator, §2 Critic, §3 Orchestrator to cos-ops depth**

The cos-ops versions are ~300-500 lines each. The Redis versions currently have ~50 lines each. Bring them to parity. Required per the template:
- §1 must list per-operation pre-flight: `CreateInstances` (zone × spec matrix, VPC check, password complexity), `DestroyInstances` (recycle-bin window check), `ClearInstance` (FLUSHALL confirmation capture), `ResetPassword` (default account warning), `BackupDownload` (sensitive data warning).
- §2 Critic must list 5 Redis-specific rules (already in rubric §4) and how each is checked.
- §3 Orchestrator decision logic must reference the rubric's `block_thresholds`.

- [ ] **Step 5.1.3: Add §5 Anti-patterns (banned) section**

Copy the anti-patterns block from cos-ops prompt-templates.md §5 verbatim, replacing "CVM" / "TerminateInstances" with "Redis" / "DestroyInstances" / "ClearInstance" / "FLUSHALL" examples.

- [ ] **Step 5.1.4: Split existing §6 into §6 Changelog + §7 See also**

```markdown
## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Redis rollout: Generator + Critic + Orchestrator templates |
| 1.1.0 | 2026-06-18 | Tier A flesh-out: full G/C/O detail + per-op variants + anti-patterns |

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill)
- [rubric.md](rubric.md)
- [SKILL.md](../SKILL.md)
```

- [ ] **Step 5.1.5: Run conformance + tests**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep redis-ops
# Expected: redis-ops no longer in failing list (prompt 7/7)
cd scripts && python3 -m unittest gcl_conformance_test gcl_runner_test 2>&1 | tail -3
```

- [ ] **Step 5.1.6: Commit**

```bash
git add qcloud-redis-ops/references/prompt-templates.md
git commit -m "feat(gcl): flesh out qcloud-redis-ops prompt-templates to Tier A (7 sections)"
```

### Task 5.2-5.15: Repeat Task 5.1 for the remaining 14 Tier B skills

For each skill below, repeat Task 5.1 with skill-specific substitutions:

| Task | Skill | Product-specific substitutions |
|---|---|---|
| 5.2 | qcloud-es-ops | ES: `DeleteCluster`, `DeleteIndex`, cluster-restart ops |
| 5.3 | qcloud-vpc-ops | VPC: `DeleteVpc`, `DeleteSubnet`, route blackhole |
| 5.4 | qcloud-cam-ops | CAM: `DeleteUser`, `DetachUserPolicy`, `RotateAccessKey` |
| 5.5 | qcloud-cbs-ops | CBS: `TerminateDisks`, `ResizeDisk` (shrink blocked) |
| 5.6 | qcloud-ckafka-ops | CKafka: `DeleteInstance`, `DeleteTopic`, consumer offset loss |
| 5.7 | qcloud-mongodb-ops | Mongo: `TerminateDBInstance`, `DropDB`, oplog loss |
| 5.8 | qcloud-postgres-ops | PG: `TerminateDBInstance`, `DropDB`, no UNDROP |
| 5.9 | qcloud-cdn-ops | CDN: `DeleteCdnDomain`, cache purge, propagation delay |
| 5.10 | qcloud-cls-ops | CLS: `DeleteLogset`, `DeleteTopic`, retention truncation |
| 5.11 | qcloud-scf-ops | SCF: `DeleteFunction`, code overwrite, rollback path |
| 5.12 | qcloud-ssl-ops | SSL: `DeleteCertificates`, TLS handshake failure, RBAC |
| 5.13 | qcloud-agsx-ops | AGSX: SDK-only path; reference `references/cli-behavior.md` |
| 5.14 | qcloud-monitor-ops | Monitor: `DeleteAlarmPolicy`, silent alarm stop, threshold drift |
| 5.15 | qcloud-finops-ops | FinOps: optional skill; emphasize "do not auto-execute billing changes" |

For each task, run:
```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep <skill>
cd scripts && python3 -m unittest gcl_conformance_test gcl_runner_test 2>&1 | tail -3
git add <skill>/references/prompt-templates.md
git commit -m "feat(gcl): flesh out <skill> prompt-templates to Tier A (7 sections)"
```

---

## Phase 6: Tier B SKILL.md Quality Gate Expansion (15 skills)

Each Tier B SKILL.md currently has a 23-line `## Quality Gate (GCL)` section (just the 5-rule list). Phase 6 expands it to Tier A (50+ lines) matching `qcloud-cvm-ops/SKILL.md` (57 lines).

### Task 6.1: qcloud-redis-ops SKILL.md Quality Gate expansion

**Files:**
- Modify: `qcloud-redis-ops/SKILL.md` (expand `## Quality Gate (GCL)`)

- [ ] **Step 6.1.1: Open canonical cvm-ops Quality Gate section as template**

```bash
awk '/^## Quality Gate \(GCL\)/{flag=1; print; next} /^## /{if(flag){flag=0; exit}} flag' qcloud-cvm-ops/SKILL.md | head -60
```

- [ ] **Step 6.1.2: Replace qcloud-redis-ops/SKILL.md Quality Gate with Tier A version**

The replacement must contain:
- 5-row property table (already present)
- `### When the loop runs` table (3 rows: destructive / mutating / read-only)
- `### Decision flow (first match wins)` 4-row list
- `### Redis-specific safety rules (rubric §4)` (already present, keep the 5 rules)
- `### Worked example` (1 example minimum; recommended: `ClearInstance` FLUSHALL safety fail)
- Closing sentence: "See `references/rubric.md` §6 for two more examples."

- [ ] **Step 6.1.3: Verify conformance + commit**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep redis-ops
# Expected: redis-ops passes all three checks (rubric 8/8, prompt 7/7, QualityGate present)
git add qcloud-redis-ops/SKILL.md
git commit -m "feat(gcl): expand qcloud-redis-ops SKILL.md Quality Gate to Tier A"
```

### Task 6.2-6.15: Repeat for the remaining 14 Tier B skills

Same pattern; one task per skill. Per-skill substitutions match the rubric's safety rules.

---

## Phase 7: Tier C Special-Case Skills (3 skills)

### Task 7.1: qcloud-aiops-diagnosis rubric — renumber to canonical 8 sections

**Files:**
- Modify: `qcloud-aiops-diagnosis/references/rubric.md` (currently non-numbered headings)

Current state: uses `## Rubric Dimensions` / `## Safety Rules` / `## Scoring Examples` / `## Changelog`.

- [ ] **Step 7.1.1: Renumber headings**

Map current → canonical:
- `## Rubric Dimensions` → `## 2. Five rubric dimensions (mandatory)`
- `## Safety Rules (Rubric §4)` → `## 4. AIOps-specific safety rules` (rename + renumber)
- `## Scoring Examples` → `## 6. Worked examples`
- `## Changelog` → `## 7. Changelog`

- [ ] **Step 7.1.2: Insert missing §1, §3, §5, §8**

Insert:
- §1 Scope and applicability (AIOps: applies to log/metric/event correlation; not for cloud resource mutations — those go to qcloud-*-ops skills)
- §3 Per-dimension scoring checklist (5 dimensions × 3 score columns)
- §5 Output schema (same JSON template as cdb-ops)
- §8 See also

- [ ] **Step 7.1.3: Run conformance + commit**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep aiops-diagnosis
git add qcloud-aiops-diagnosis/references/rubric.md
git commit -m "feat(gcl): renumber qcloud-aiops-diagnosis rubric to canonical 8 sections"
```

### Task 7.2: qcloud-aiops-diagnosis prompt-templates — add 7-section structure

**Files:**
- Modify: `qcloud-aiops-diagnosis/references/prompt-templates.md` (currently non-numbered, 5420 bytes)

- [ ] **Step 7.2.1: Inspect current headings**

```bash
grep -E "^## " qcloud-aiops-diagnosis/references/prompt-templates.md
```

- [ ] **Step 7.2.2: Renumber to canonical §1..§7**

AIOps-diagnosis prompt must emphasize:
- §1 Generator: cross-skill correlation patterns (Loki + CLB + CVM); root cause hypothesis generation
- §2 Critic: read-only enforcement (no resource mutation); correlation logic validity
- §3 Orchestrator: delegation rules to qcloud-monitor-ops / qcloud-cvm-ops
- §4 Per-op variants: diagnosis flow-specific (log → metric → event correlation)
- §5 Anti-patterns: Critic MUST NOT mutate; correlation MUST be evidence-based

- [ ] **Step 7.2.3: Commit**

```bash
git add qcloud-aiops-diagnosis/references/prompt-templates.md
git commit -m "feat(gcl): flesh out qcloud-aiops-diagnosis prompt-templates to 7 sections"
```

### Task 7.3: qcloud-proactive-inspection rubric — flesh out from 2 to 8 sections

**Files:**
- Modify: `qcloud-proactive-inspection/references/rubric.md` (2471 → ~14000 bytes)

- [ ] **Step 7.3.1: Repeat Task 2.1 pattern for proactive-inspection**

Proactive Inspection-specific safety rule examples:
- `Discovery` over-broad scope — accidentally enumerating prod resources
- `Assessment` false-positive — flagging healthy resources as degraded
- `Report` PII leak — exposing user data in summary
- `Remediation` auto-execute — must NEVER auto-execute (read-only by design)
- `Cross-skill delegation` — must verify target skill supports the resource before delegating

- [ ] **Step 7.3.2: Commit**

```bash
git add qcloud-proactive-inspection/references/rubric.md
git commit -m "feat(gcl): flesh out qcloud-proactive-inspection rubric to 8 sections"
```

### Task 7.4: qcloud-proactive-inspection prompt-templates — flesh out from 2 to 7 sections

**Files:**
- Modify: `qcloud-proactive-inspection/references/prompt-templates.md` (960 → ~8000 bytes)

- [ ] **Step 7.4.1: Repeat Task 5.1 pattern for proactive-inspection**

Proactive Inspection prompt must emphasize: 5-step pipeline (Discovery → Assessment → Diagnosis → Recommendation → Report); idempotency is the main risk (re-running on same window must not double-count); cross-skill delegation handoff.

- [ ] **Step 7.4.2: Commit**

```bash
git add qcloud-proactive-inspection/references/prompt-templates.md
git commit -m "feat(gcl): flesh out qcloud-proactive-inspection prompt-templates to 7 sections"
```

### Task 7.5: qcloud-well-architected-review rubric — add §6 worked examples

**Files:**
- Modify: `qcloud-well-architected-review/references/rubric.md` (currently §6 is misnumbered as Changelog)

- [ ] **Step 7.5.1: Inspect current numbering**

```bash
grep -E "^## " qcloud-well-architected-review/references/rubric.md
# Current: §1, §2, §3, §4 Threshold summary, §5 WA-specific rules, §6 Changelog, §7 (missing)
```

- [ ] **Step 7.5.2: Insert §6 Worked examples**

Move Changelog to §7. Insert §6 worked examples between §5 and the old §6:
- PASS on a 4-pillar assessment where all dimensions meet SLO
- RETRY on Reliability pillar where recovery time objective (RTO) exceeds tenant SLA
- SAFETY_FAIL on Security pillar where credential leak was detected

- [ ] **Step 7.5.3: Add §8 See also section**

```markdown
## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-well-architected-review` is `optional`, `max_iter=5`
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md](../SKILL.md)
```

- [ ] **Step 7.5.4: Commit**

```bash
git add qcloud-well-architected-review/references/rubric.md
git commit -m "feat(gcl): add §6 worked examples to qcloud-well-architected-review rubric"
```

---

## Phase 8: Tier D Skill (qcloud-skill-generator)

The meta-skill has no destructive cloud operations, but it DOES have build-time safety rules (Charter C1-C7). Phase 8 adds GCL artifacts framing the generator's own loop.

### Task 8.1: qcloud-skill-generator rubric

**Files:**
- Create: `qcloud-skill-generator/references/rubric.md`

- [ ] **Step 8.1.1: Write the meta-skill rubric**

The rubric must use a 5-dimension structure adapted to the generation context:

```markdown
# qcloud-skill-generator Quality-Gate Rubric (GCL)

> Runtime scoring rubric for **Generator-Critic-Loop (GCL)** of `qcloud-skill-generator`.
> This skill has **no destructive cloud operations**, so the rubric audits the **generated
> artifact** (a `qcloud-*-ops/SKILL.md` + `references/` tree), not cloud resources.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every skill-generation run: populating `SKILL.md`, `references/*`, `assets/*` from API spec | Live execution against cloud accounts (use the generated `qcloud-*-ops` skill instead) |
| Regeneration / realignment when API docs change | One-off debugging with no intent to maintain a reusable skill |
| Charter C1-C7 self-check after population | Skill execution at runtime (governed by the generated skill's own rubric) |

## 2. Five rubric dimensions (mandatory)

| # | Dimension | Threshold | Why this threshold for skill-generation |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for Charter C1, C5) | A half-correct frontmatter is unusable; half-correct Variables section breaks prompt injection safety |
| 2 | **Safety** | **= 1** (strict) | Generator MUST NOT emit `TENCENTCLOUD_SECRET_KEY` literals; MUST require env-var injection |
| 3 | **Idempotency** | ≥ 0.5 | Regenerating an existing skill must not duplicate sections; 2-round self-review already covers this |
| 4 | **Traceability** | ≥ 0.5 | Every generated `SKILL.md` must cite the API doc URL it was derived from |
| 5 | **Spec Compliance** | ≥ 0.5 | Generated skill must pass Charter C1-C7 (frontmatter, SHOULD/SHOULD NOT, Five Core Standards, Well-Architected, Variables, Token Efficiency, GCL Quality Gate) |

**Safety = 0 → ABORT immediately**. See [AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Frontmatter has `name`, `description`, `license`, `compatibility`, `metadata` (Charter C1) | ✓ all 5 present | 1 missing | ≥ 2 missing |
| API operation list matches `tccli <product> help` (PRIMARY) or tencentcloud-sdk-python (FALLBACK) | ✓ verified against `tccli help` output for the product slug | 1 of N operations missing | Operation invoked that does not exist in API |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Generated skill does NOT contain `SecretKey=...` or `TENCENTCLOUD_SECRET_KEY=...` literals in any example | ✓ | any literal credential present |
| Frontmatter `environment:` block lists `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_REGION` (Charter C1) | ✓ | missing or hard-coded |
| Generated `references/rubric.md` has `safety = 1.0` threshold for destructive ops | ✓ | threshold < 1.0 |
| Generated `references/prompt-templates.md` §2 Critic prompt is **isolated-context** (Critic does not see user request) | ✓ | shared-context G+C |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Re-running on existing skill does not duplicate sections | ✓ | duplicates introduced but logged | silently overwrites user-edited sections |
| 2-round self-review (`R1` content audit + `R2` governance) executed | ✓ both | R1 only | neither |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Every cited API operation has a doc URL in the trace | ✓ | partial | none |
| Charter C1-C7 self-check log persisted to trace | ✓ | C1-C5 only | no log |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Charter C7 (GCL Quality Gate) passes for generated skill | ✓ | partial (rubric OR prompt, not both) | neither |
| Five Core Standards table populated with product-specific content | ✓ | table present but cells empty | table missing |
| Well-Architected four-pillar table populated | ✓ | one pillar empty | two or more empty |

## 4. qcloud-skill-generator-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Populate `references/rubric.md` | MUST include `safety = 1.0` threshold for destructive ops of the generated product; MUST list ≥ 5 product-specific safety rules; MUST cross-reference the generated skill's SKILL.md `## Safety Gates` chapter | Generated skills that ship without a tight safety rubric are not safe to merge |
| 2 | Populate `references/prompt-templates.md` | §2 Critic prompt MUST be **isolated-context** (Critic does not see raw user request); MUST include `rule_violations` field for audit; MUST cite the rubric's `thresholds` block | Without isolated-context, the Critic rubber-stamps the Generator (AGENTS.md §2) |
| 3 | Populate `## Quality Gate (GCL)` in SKILL.md | MUST include the 5-row property table (`GCL applicability` / `max_iterations` / `Rubric instance` / `Prompt templates` / `Trace path`); MUST list the product-specific safety rules in the SKILL.md chapter | Charter C7 enforcement; ensures generated skills are GCL-conformant from birth |
| 4 | Populate frontmatter `metadata.cli_applicability` | MUST be one of `cli-first` / `dual-path` / `sdk-only` / `cli-only`; MUST cite evidence in `cli_support_evidence` | Missing applicability breaks the dual-path / SDK-only execution decision in generated skills |
| 5 | Real-time API doc changes | MUST diff old vs new spec and surface breaking changes in trace; MUST bump `metadata.last_updated` and the skill's changelog | Silent realignment causes generation drift |

## 5. Output schema (returned by Critic)

Strict JSON, same shape as the GCL spec in [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false,
  "charter_violations": [
    {"rule": "C7", "rationale": "Generated qcloud-foo-ops missing references/rubric.md"}
  ],
  "thresholds": {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "rubric_version": "v1"
}
```

`charter_violations` is **qcloud-skill-generator-specific** (rules 1-5 in §4) and is the
audit trail the meta-skill emits to track which Charter checks fire most often.

## 6. Worked examples

### Example A — PASS on generating qcloud-cvm-ops

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Frontmatter has all 5 keys (Charter C1); operations verified against `tccli cvm help` |
| Safety | 1 | No credential literals; rubric has `safety = 1.0`; Critic prompt is isolated-context |
| Idempotency | 1 | 2-round self-review (R1 + R2) executed; no section duplication |
| Traceability | 1 | All API ops cited; C1-C7 self-check logged to trace |
| Spec Compliance | 1 | Charter C7 passes; Five Core Standards + Well-Architected tables populated |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on generating qcloud-foo-ops with credential leak

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | — |
| **Safety** | **0** | Rule 1 violated: generated `references/api-sdk-usage.md` contains `TENCENTCLOUD_SECRET_KEY=AKID...` literal in example |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| Spec Compliance | 0.5 | Charter C7 partial — rubric is present but prompt templates §2 Critic uses shared-context |

`blocking: true`. `charter_violations: [{rule: "C1", rationale: "credential literal in api-sdk-usage.md example"}]`. **ABORT** — recover by replacing the literal with `{{env.TENCENTCLOUD_SECRET_KEY}}`.

### Example C — RETRY on missing Quality Gate section

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Frontmatter OK |
| Safety | 1 | — |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| **Spec Compliance** | **0** | Charter C7 violated: generated SKILL.md has no `## Quality Gate (GCL)` section |

`blocking: true`. After re-generation with the GCL section appended, Spec Compliance scores 1.

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-18 | Phase D meta-skill rubric (5 dimensions, 5 generator-specific safety rules, worked examples) |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-skill-generator` is `optional`, `max_iter=3`
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Post-Generation Self-Check](../SKILL.md#post-generation-self-check------) — build-time sibling

---

### Task 8.2: qcloud-skill-generator prompt-templates

**Files:**
- Create: `qcloud-skill-generator/references/prompt-templates.md`

- [ ] **Step 8.2.1: Write the meta-skill prompt skeletons**

The 7 sections, adapted to generation context:

- **§1 Generator** — populates `SKILL.md` + `references/*` from API spec; pre-flight verifies API doc URL is reachable; per-rule (Charter C1-C7) section-by-section population plan.
- **§2 Critic** — audits the generated artifact in isolation; scores against rubric.md 5 dimensions; explicit `charter_violations` list.
- **§3 Orchestrator** — decision flow: PASS (commit), RETRY (regenerate with critic feedback), ABORT (Charter violation cannot be auto-fixed).
- **§4 Per-rule variants** — for each Charter rule (C1-C7), what to verify in the generated artifact.
- **§5 Anti-patterns** — banned: generating without API doc URL; copying from another skill without re-deriving; emitting credential literals; generating without 2-round self-review.
- **§6 Changelog** — version 1.0.0, 2026-06-18.
- **§7 See also** — links to AGENTS.md, rubric.md, SKILL.md.

- [ ] **Step 8.2.2: Verify conformance + commit**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep skill-generator
# Expected: skill-generator prompt_sections == 7
git add qcloud-skill-generator/references/prompt-templates.md
git commit -m "feat(gcl): add prompt-templates to qcloud-skill-generator (Tier D)"
```

### Task 8.3: qcloud-skill-generator SKILL.md Quality Gate section

**Files:**
- Modify: `qcloud-skill-generator/SKILL.md` (add `## Quality Gate (GCL)` chapter)

- [ ] **Step 8.3.1: Insert the Quality Gate chapter**

Insert at the end of `qcloud-skill-generator/SKILL.md`, after `## Post-Generation Self-Check`:

```markdown
## Quality Gate (GCL)

This meta-skill participates in the **Generator-Critic-Loop (GCL)** at the **generation-time**
layer. The loop audits the **generated artifact** (a `qcloud-*-ops/SKILL.md` + `references/`
tree), not cloud resources.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 generator-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Why this skill is `optional` (not `required`)

The meta-skill **does not mutate cloud resources**. Its output is a skill
checked into git. Safety is enforced by the **build-time** Charter C1-C7
self-check + 2-round self-review (already mandatory above) and by the
**Charter C7 enforcement** that requires generated skills to ship with their
own Tier A rubric.md + prompt-templates.md + Quality Gate chapter. The GCL
loop on this meta-skill is therefore a **double-check**: it verifies that
the Charter was followed during generation.

### Decision flow

1. **Safety = 0** (e.g., credential literal emitted) ⇒ **ABORT** — emit
   recovery: replace literal with `{{env.*}}` placeholder
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved
   Charter violations in `final.unresolved`
3. **All Charter C1-C7 checks pass** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's `charter_violations` injected

### Meta-skill-specific safety rules (rubric §4)

1. Generated `references/rubric.md` MUST have `safety = 1.0` threshold for destructive ops
2. Generated `references/prompt-templates.md` §2 Critic MUST be isolated-context
3. Generated `SKILL.md` MUST include `## Quality Gate (GCL)` chapter (Charter C7)
4. Frontmatter `metadata.cli_applicability` MUST be set with `cli_support_evidence`
5. Real-time API doc changes MUST surface breaking changes in trace + bump version

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — generating a hypothetical `qcloud-foo-ops`

| Dimension | Score |
|---|---|
| Correctness | 1 (frontmatter has all 5 keys) |
| **Safety** | **0** (rule 1 violated: rubric.md missing `safety = 1.0` for `DeleteFoo`) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 0.5 (Charter C7 partial — rubric.md present, prompt-templates.md missing) |

`decision: ABORT`. Recovery suggestion: "Add `safety = 1.0` to rubric.md §2 dimensions and scaffold prompt-templates.md from cos-ops reference".

See [`references/rubric.md`](references/rubric.md) §6 for two more examples.
```

- [ ] **Step 8.3.2: Verify full conformance + commit**

```bash
python3 scripts/check_gcl_conformance.py --root . 2>&1 | grep skill-generator
# Expected: skill-generator passes all three (rubric 8/8, prompt 7/7, QualityGate present)
cd scripts && python3 -m unittest gcl_conformance_test gcl_runner_test 2>&1 | tail -3
# Expected: all tests pass
git add qcloud-skill-generator/SKILL.md
git commit -m "feat(gcl): add Quality Gate chapter to qcloud-skill-generator (Tier D)"
```

---

## Phase 9: End-to-End GCL Loop Test per Skill

Once conformance is achieved, every skill must pass an actual GCL run.

### Task 9.1: Per-skill smoke run

- [ ] **Step 9.1.1: For each of the 24 skills, run a structural-critic GCL pass**

```bash
for skill in qcloud-cvm-ops qcloud-cdb-ops qcloud-clb-ops qcloud-cos-ops \
             qcloud-es-ops qcloud-redis-ops qcloud-tke-ops qcloud-vpc-ops \
             qcloud-cam-ops qcloud-cdn-ops qcloud-cbs-ops qcloud-cls-ops \
             qcloud-ckafka-ops qcloud-scf-ops qcloud-mongodb-ops \
             qcloud-postgres-ops qcloud-ssl-ops qcloud-agsx-ops \
             qcloud-finops-ops qcloud-monitor-ops qcloud-aiops-diagnosis \
             qcloud-proactive-inspection qcloud-well-architected-review \
             qcloud-skill-generator; do
  python3 scripts/gcl_runner.py run \
    --skill "$skill" \
    --request "GCL conformance smoke test" \
    --command 'echo {"Response":{"RequestId":"conformance-smoke"}}' \
    --max-iter 1 \
    --structural-critic-only
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "FAIL: $skill (exit=$rc)"
  fi
done
```

- [ ] **Step 9.1.2: Verify all 24 produced a passing trace**

```bash
ls audit-results/gcl-trace-*.json | wc -l
# Expected: ≥ 24 trace files from this run

python3 scripts/gcl_trace_aggregate.py --since-hours 1 2>&1
# Expected: pass_rate = 1.0, total_runs = 24
```

- [ ] **Step 9.1.3: Commit (no code changes; CI artifact only)**

```bash
git add audit-results/gcl-trace-*.json
git commit -m "ci(gcl): 24-skill structural smoke run (Tier A conformance verified)"
```

---

## Phase 10: AGENTS.md Phase 4.1 Update

### Task 10.1: Document the Tier B/C/D conformance phase in AGENTS.md

**Files:**
- Modify: `AGENTS.md` (append Phase 4.1 entry after Phase 4)

- [ ] **Step 10.1.1: Add Phase 4.1 entry**

Insert after the Phase 4 paragraph (line 368) and before `### 11. Relationship to existing 2-round self-review`:

```markdown
- **Phase 4.1** — Tier B/C/D conformance: bring all 24 skills to Tier A (8 rubric sections + 7 prompt sections + `## Quality Gate (GCL)` chapter). **Done (2026-06-18):** `scripts/check_gcl_conformance.py` is the durable CI gate; 19 under-conforming skills (15 Tier B + 3 Tier C + 1 Tier D) fleshed out to Tier A; `qcloud-skill-generator` (Tier D) gained `references/rubric.md`, `references/prompt-templates.md`, and `## Quality Gate (GCL)` SKILL.md chapter.
```

- [ ] **Step 10.1.2: Bump changelog**

In `AGENTS.md` §12 Changelog, append:

```markdown
| 1.2.0 | 2026-06-18 | **Phase 4.1 Tier A conformance:** `scripts/check_gcl_conformance.py` (CI gate); 19 skills fleshed out to 8-section rubric + 7-section prompt-templates + Tier A SKILL.md Quality Gate chapter; `qcloud-skill-generator` (Tier D) gained full GCL artifacts |
```

- [ ] **Step 10.1.3: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): bump Phase 4.1 (Tier A conformance) + changelog 1.2.0"
```

---

## Self-Review

After writing this plan, I checked it against the spec with the writing-plans checklist:

**1. Spec coverage:**
- ✅ "剩下的 skills" interpreted as: 15 Tier B + 3 Tier C + 1 Tier D = 19 under-conforming skills
- ✅ Per-skill checklist (rubric 8 sections, prompt 7 sections, Quality Gate chapter)
- ✅ CI enforcement (`scripts/check_gcl_conformance.py`)
- ✅ Tier D special case (meta-skill has Charter C1-C7 framing instead of cloud destructive ops)
- ✅ End-to-end verification (Phase 9 runs all 24 through `gcl_runner.py`)
- ✅ AGENTS.md docs update (Phase 4.1)

**2. Placeholder scan:** No "TBD" / "implement later" / "fill in details". Every task has either concrete code, concrete commands, or a concrete reference to existing canonical templates (`qcloud-cdb-ops`, `qcloud-cos-ops`).

**3. Type consistency:** Function names (`check_skill`, `check_all`, `cmd_check`), module names (`check_gcl_conformance`), and class names are consistent across Tasks 1.1, 1.2, 9.1.

**One open question for the user:** The Phase 5 pattern compresses 14 skills into Task 5.2-5.15 with one task list per skill. If you want truly bite-sized execution (one task = one skill = one PR), this is correct. If you prefer batched execution (one task = batch all 14 skills in one PR), I should split Task 5.2-5.15 into a single Task 5.2 with a per-skill step table.

**Default choice:** Keep as-is (one task per skill) — matches the writing-plans skill's "bite-sized 2-5 minute steps" guidance and makes review between skills easier.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-18-gcl-tier-b-c-d-conformance.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task (or per skill for the Phase 2/3/5/6 batches). Review between tasks for fast iteration. Best for: 19 skills × multiple sections = high volume; subagents can work in parallel batches.

**2. Inline Execution** — Execute tasks in this session using executing-plans. Batch execution with checkpoints for review. Best for: tighter control over each commit; easier to pause/resume.

**Which approach?**

If you choose **Subagent-Driven**, I will:
- Use the `dispatching-parallel-agents` skill to batch Tier B skills (e.g., 8 required-tier skills in parallel).
- Each subagent gets a self-contained Task 2.X spec + canonical template path + product-specific substitutions table.
- After each batch, run `scripts/check_gcl_conformance.py` to verify the batch.

If you choose **Inline Execution**, I will:
- Work through phases sequentially in this session.
- Commit after each task (per the writing-plans "frequent commits" rule).
- Run conformance + tests after each task.
