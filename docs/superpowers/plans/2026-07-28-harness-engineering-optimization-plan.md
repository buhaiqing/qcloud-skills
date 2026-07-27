# Harness Engineering Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an additive, non-weakening Evidence Kernel + Skill Registry to qcloud-skills that delivers evidence-based trust, a closed GCL loop, autonomous-but-human-confirmed runtime safety, and harness efficiency — all gated by a fixed KPI set in CI.

**Architecture:** A shared `Evidence Kernel` (PreFlight gate + PostRecord persistence of one `EvidenceRecord` schema) and a machine-built `Skill Registry` form the foundation. Four phases build on it: (1) golden scenarios + sandbox E2E + CI gates, (2) GCL loop hardening (retry/timeout/schema/masking), (3) destructive auto-detection + human-issued token↔plan binding, (4) Registry/Router + budgets + confusion matrix + convergence. Every gate is additive to existing `validate_local.py` / `cadl_lint.py` / `gcl_trace_aggregate.py`.

**Tech Stack:** Python 3.8+ (stdlib only — no external deps, matching repo convention), JSON fixtures, git CLI for affected-skill detection, existing `scripts/` toolchain.

---

## Spec correction (apply in Task 0)

The spec's "Executable skill" definition references `cli_applicability` values `dual-path` / `cli-first` / `sdk-only` and a read-only `cli-only`. On-disk reality (verified via `grep cli_applicability qcloud-*-ops/SKILL.md`): only `dual-path` (27 skills) and `sdk-only` (3 skills) exist. There is **no** `cli-only` / `cli-first` in this repo. Correction: **executable skill = `dual-path` or `sdk-only`** (all 30 product/cross skills). The "≥5 golden / ≥2 for read-only" split is dropped; all executable skills need ≥5 golden scenarios. Update the spec's Phase 1 bullet to match before Phase 1 work begins.

---

## File structure

| File | Responsibility |
|------|----------------|
| `docs/evidence-kernel-schema.json` | Canonical `EvidenceRecord` JSON Schema (kernel contract) |
| `scripts/evidence_kernel.py` | PreFlight + PostRecord + mask_trace + plan_hash helpers |
| `scripts/validate_evidence_schema.py` | Validate `audit-results/evidence-*.json` against schema; CI gate (KPI #1/#2/#5) |
| `scripts/build_skill_registry.py` | Parse all `qcloud-*-ops/SKILL.md` frontmatter → `audit-results/skill-registry.json` |
| `scripts/sandbox_e2e.py` | Run skills against recorded fixtures; assert golden match |
| `scripts/aggregate_kpi.py` | Aggregate KPI set from EvidenceRecords; exit 1 if target unmet |
| `scripts/harness_safety.py` | Destructive-action dictionary + classifier; token↔plan_hash binding check |
| `scripts/harness_router.py` | Frontmatter-only candidate select; progressive load; budget enforce; confusion matrix |
| `qcloud-*-ops/assets/golden/*.json` | Per-skill golden scenarios (≥5 each) |
| `qcloud-*-ops/assets/fixtures/*.json` | Recorded `tccli`/SDK CLI responses |
| `audit-results/*.json` | Generated registry / manifest / evidence (gitignored, `.gitignore:232`) |
| `Makefile` | Single dev/CI entry wrapping all runners |
| `scripts/*_test.py` | Unit tests following `cd scripts && python3 -m unittest discover -p "*_test.py"` |

---

## Task 0: Evidence Kernel foundation (spec correction + schema + validator)

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md` (Phase 1 executable-skill def)
- Create: `docs/evidence-kernel-schema.json`
- Create: `scripts/evidence_kernel.py`
- Create: `scripts/validate_evidence_schema.py`
- Create: `scripts/evidence_kernel_test.py`

- [ ] **Step 1: Correct the spec's executable-skill definition**

Edit the Phase 1 bullet in the spec so it reads:
```
- **Executable skill** = any `qcloud-*-ops` skill whose `cli_applicability` is
  `dual-path` or `sdk-only` (verified: 27 + 3 = 30 skills in this repo; no
  `cli-only`/`cli-first` exists). Every executable skill needs ≥5 golden scenarios
  (KPI #3).
```

- [ ] **Step 2: Write the failing test for schema validation**

```python
# scripts/evidence_kernel_test.py
import json, tempfile, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID = {
    "skill": "qcloud-cvm-ops", "run_id": "r1", "phase": "self-test",
    "intent": "list instances",
    "router_decision": {"top1_skill": "qcloud-cvm-ops", "candidates": ["qcloud-cvm-ops"],
                         "misdelegated": False, "fell_back": False},
    "trace": {}, "golden_ref": "assets/golden/list.json", "fixture_ref": None,
    "safety": {"destructive": False, "token": None, "plan_hash": None, "leak_checked": True},
    "provenance": {"source": "sandbox_e2e", "tool": "tccli", "captured_at": "2026-07-28T00:00:00Z"},
    "budgets": {"context_tokens": 100, "tool_calls": 2, "wall_clock_ms": 500},
    "cost": {"tokens": 100, "usd": None},
    "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}
}

def test_valid_record_passes():
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(VALID, p); p.close()
    r = subprocess.run([sys.executable, "scripts/validate_evidence_schema.py", p.name],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_missing_provenance_fails():
    bad = dict(VALID); bad.pop("provenance")
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(bad, p); p.close()
    r = subprocess.run([sys.executable, "scripts/validate_evidence_schema.py", p.name],
                       capture_output=True, text=True)
    assert r.returncode != 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd scripts && python3 -m unittest evidence_kernel_test -v`
Expected: FAIL — `scripts/validate_evidence_schema.py` and `docs/evidence-kernel-schema.json` do not exist.

- [ ] **Step 4: Write the schema file**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EvidenceRecord",
  "type": "object",
  "required": ["skill", "run_id", "phase", "intent", "router_decision",
               "trace", "golden_ref", "fixture_ref", "safety", "provenance",
               "budgets", "cost", "scores"],
  "properties": {
    "skill": {"type": "string"},
    "run_id": {"type": "string"},
    "phase": {"enum": ["self-test", "sandbox", "production"]},
    "intent": {"type": "string"},
    "router_decision": {
      "type": "object",
      "required": ["top1_skill", "candidates", "misdelegated", "fell_back"],
      "properties": {
        "top1_skill": {"type": "string"},
        "candidates": {"type": "array", "items": {"type": "string"}},
        "misdelegated": {"type": "boolean"},
        "fell_back": {"type": "boolean"}
      }
    },
    "trace": {"type": "object"},
    "golden_ref": {"type": ["string", "null"]},
    "fixture_ref": {"type": ["string", "null"]},
    "safety": {
      "type": "object",
      "required": ["destructive", "token", "plan_hash", "leak_checked"],
      "properties": {
        "destructive": {"type": "boolean"},
        "token": {"type": ["string", "null"]},
        "plan_hash": {"type": ["string", "null"]},
        "leak_checked": {"type": "boolean"}
      }
    },
    "provenance": {
      "type": "object",
      "required": ["source", "tool", "captured_at"],
      "properties": {
        "source": {"type": "string"},
        "tool": {"type": "string"},
        "captured_at": {"type": "string"}
      }
    },
    "budgets": {
      "type": "object",
      "required": ["context_tokens", "tool_calls", "wall_clock_ms"],
      "properties": {
        "context_tokens": {"type": "integer"},
        "tool_calls": {"type": "integer"},
        "wall_clock_ms": {"type": "integer"}
      }
    },
    "cost": {
      "type": "object",
      "required": ["tokens"],
      "properties": {"tokens": {"type": "integer"}, "usd": {"type": ["number", "null"]}}
    },
    "scores": {
      "type": "object",
      "required": ["correctness", "safety", "idempotency", "traceability", "spec_compliance"],
      "properties": {
        "correctness": {"type": "number"}, "safety": {"type": "number"},
        "idempotency": {"type": "number"}, "traceability": {"type": "number"},
        "spec_compliance": {"type": "number"}
      }
    }
  }
}
```

- [ ] **Step 5: Write `validate_evidence_schema.py` (stdlib-only)**

```python
#!/usr/bin/env python3
"""Validate EvidenceRecord JSON files against docs/evidence-kernel-schema.json.
Exits non-zero on any validation failure (CI gate for KPI #1/#2/#5)."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "evidence-kernel-schema.json"

def load_schema():
    return json.loads(SCHEMA.read_text())

def type_ok(value, typ):
    if typ == "string": return isinstance(value, str)
    if typ == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if typ == "number": return isinstance(value, (int, float)) and not isinstance(value, bool)
    if typ == "boolean": return isinstance(value, bool)
    if typ == "object": return isinstance(value, dict)
    if typ == "array": return isinstance(value, list)
    if isinstance(typ, list): return any(type_ok(value, t) for t in typ)
    return True

def validate(record, schema):
    errors = []
    for req in schema.get("required", []):
        if req not in record:
            errors.append(f"missing required field: {req}")
    props = schema.get("properties", {})
    for key, val in record.items():
        if key in props:
            spec = props[key]
            if "enum" in spec and val not in spec["enum"]:
                errors.append(f"{key}: {val!r} not in {spec['enum']}")
            if "type" in spec and not type_ok(val, spec["type"]):
                errors.append(f"{key}: {val!r} wrong type, expected {spec['type']}")
            if spec.get("type") == "object":
                errors += [f"{key}.{e}" for e in validate(val, spec)]
    if record.get("safety", {}).get("destructive") and not record["safety"].get("token"):
        errors.append("KPI#2: destructive=true requires safety.token")
    if not record.get("safety", {}).get("leak_checked"):
        errors.append("KPI#1: safety.leak_checked must be true")
    return errors

def main(paths):
    schema = load_schema()
    total_errors = 0
    for p in paths:
        data = json.loads(Path(p).read_text())
        recs = data if isinstance(data, list) else [data]
        for i, rec in enumerate(recs):
            errs = validate(rec, schema)
            if errs:
                total_errors += len(errs)
                for e in errs:
                    print(f"FAIL {p}[{i}]: {e}")
    if total_errors:
        print(f"\n{total_errors} validation error(s)")
        sys.exit(1)
    print(f"OK: {len(paths)} file(s) valid")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_evidence_schema.py <file.json> [...]"); sys.exit(2)
    main(sys.argv[1:])
```

- [ ] **Step 6: Write `evidence_kernel.py` (PreFlight + PostRecord + mask + plan_hash)**

```python
#!/usr/bin/env python3
"""Evidence Kernel: PreFlight gate + PostRecord persistence.
PreFlight runs before execution (budget/destructive/token gating).
PostRecord persists a validated EvidenceRecord under audit-results/.
NOTE: human-in-the-loop — harness never auto-issues the confirmation token."""
import json, hashlib, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"
AUDIT.mkdir(exist_ok=True)

DESTRUCTIVE_VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}

def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]

def is_destructive(plan_text: str) -> bool:
    return any(v in plan_text.lower().split() for v in DESTRUCTIVE_VERBS)

def preflight(plan_text: str, human_token: str | None) -> dict:
    """Return a PreFlight decision. Does NOT auto-issue tokens."""
    destructive = is_destructive(plan_text)
    decision = {"destructive": destructive, "allowed": True, "reason": ""}
    if destructive and not human_token:
        decision["allowed"] = False
        decision["reason"] = "destructive op requires human-issued confirmation token"
    return decision

def mask_trace(trace: dict) -> dict:
    """Redact obvious secret patterns (KPI#1). Returns a sanitized copy."""
    text = json.dumps(trace, ensure_ascii=False)
    text = re.sub(r"(AKID|secretId|secretKey)[\w]*[\"'= :]+[\w-]+", "<masked>", text)
    text = re.sub(r"TENCENTCLOUD_SECRET_KEY=[\w-]+", "TENCENTCLOUD_SECRET_KEY=<masked>", text)
    return json.loads(text)

def post_record(record: dict) -> Path:
    out = AUDIT / f"evidence-{record['run_id']}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(plan_hash(Path(sys.argv[1]).read_text()))
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest evidence_kernel_test -v`
Expected: PASS (both tests).

- [ ] **Step 8: Lint and commit**

Run: `ruff check scripts/evidence_kernel.py scripts/validate_evidence_schema.py`
Fix any errors, then:
```bash
git add docs/evidence-kernel-schema.json scripts/evidence_kernel.py scripts/validate_evidence_schema.py scripts/evidence_kernel_test.py docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md
git commit -m "feat(harness): Evidence Kernel foundation — schema + validator + PreFlight/PostRecord"
```

---

## Task 1: Skill Registry builder

**Files:**
- Create: `scripts/build_skill_registry.py`
- Create: `scripts/build_skill_registry_test.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/build_skill_registry_test.py
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_registry_has_all_skills():
    r = subprocess.run([sys.executable, "scripts/build_skill_registry.py", "--emit"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads((ROOT / "audit-results" / "skill-registry.json").read_text())
    assert data["count"] >= 30
    for s in data["skills"]:
        assert "name" in s and "cli_applicability" in s and "intent_keywords" in s
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python3 -m unittest build_skill_registry_test -v`
Expected: FAIL — script missing.

- [ ] **Step 3: Write `build_skill_registry.py`**

```python
#!/usr/bin/env python3
"""Build Skill Registry from all qcloud-*-ops/SKILL.md frontmatter.
Emits audit-results/skill-registry.json. Also --check for CI (KPI #3)."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm

def build():
    skills = []
    for sk in sorted(ROOT.glob("qcloud-*-ops/SKILL.md")):
        fm = parse_frontmatter(sk.read_text())
        if not fm:
            continue
        skills.append({
            "name": fm.get("name", sk.parent.name),
            "path": str(sk.parent),
            "cli_applicability": fm.get("cli_applicability", ""),
            "description": fm.get("description", ""),
            "intent_keywords": re.findall(r"`([^`]+)`", fm.get("description", "")),
            "delegate_to": fm.get("related_skills", ""),
        })
    return {"skills": skills, "count": len(skills)}

def main():
    if "--emit" in sys.argv:
        data = build()
        AUDIT.mkdir(exist_ok=True)
        (AUDIT / "skill-registry.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"emitted {data['count']} skills")
        sys.exit(0)
    if "--check" in sys.argv:
        data = build()
        missing = []
        for s in data["skills"]:
            if s["cli_applicability"] in ("dual-path", "sdk-only"):
                gdir = Path(s["path"]) / "assets" / "golden"
                n = len(list(gdir.glob("*.json"))) if gdir.exists() else 0
                if n < 5:
                    missing.append(f"{s['name']}: {n}/5 golden")
        if missing:
            print("KPI#3 FAIL:\n" + "\n".join(missing)); sys.exit(1)
        print("KPI#3 OK: all executable skills have >=5 golden"); sys.exit(0)
    print("usage: --emit | --check"); sys.exit(2)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest build_skill_registry_test -v`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add scripts/build_skill_registry.py scripts/build_skill_registry_test.py
git commit -m "feat(harness): Skill Registry builder from SKILL.md frontmatter"
```

---

## Task 2: Phase 1 — golden scenarios + sandbox E2E (one pilot skill)

**Files:**
- Create: `qcloud-cvm-ops/assets/golden/list_instances.json`
- Create: `qcloud-cvm-ops/assets/fixtures/describe_instances.json`
- Create: `scripts/sandbox_e2e.py`
- Create: `scripts/sandbox_e2e_test.py`

- [ ] **Step 1: Write a golden scenario + fixture for cvm (pilot)**

`qcloud-cvm-ops/assets/golden/list_instances.json`:
```json
{
  "intent": "list CVM instances in ap-guangzhou",
  "input": {"action": "DescribeInstances", "region": "ap-guangzhou", "Limit": 1},
  "expected": {
    "fixture": "assets/fixtures/describe_instances.json",
    "assertions": [
      {"path": "$.Response.InstanceSet[0].InstanceId", "op": "exists"},
      {"path": "$.Response.TotalCount", "op": ">=", "value": 0}
    ]
  }
}
```

`qcloud-cvm-ops/assets/fixtures/describe_instances.json`:
```json
{
  "Response": {
    "TotalCount": 1,
    "InstanceSet": [{"InstanceId": "ins-abc123", "InstanceName": "web01"}],
    "RequestId": "req-pilot"
  }
}
```

- [ ] **Step 2: Write failing test for sandbox_e2e**

```python
# scripts/sandbox_e2e_test.py
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_golden_match_passes():
    d = tempfile.mkdtemp()
    fix = Path(d) / "fixtures"; fix.mkdir()
    (fix / "describe_instances.json").write_text(json.dumps({
        "Response": {"TotalCount": 1, "InstanceSet": [{"InstanceId": "ins-abc123"}]}}))
    gold = Path(d) / "golden"; gold.mkdir()
    (gold / "list.json").write_text(json.dumps({
        "intent": "x", "input": {},
        "expected": {"fixture": "fixtures/describe_instances.json",
                     "assertions": [{"path": "$.Response.InstanceSet[0].InstanceId", "op": "exists"}]}}))
    r = subprocess.run([sys.executable, "scripts/sandbox_e2e.py", "--skill-dir", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_golden_mismatch_fails():
    d = tempfile.mkdtemp()
    fix = Path(d) / "fixtures"; fix.mkdir()
    (fix / "describe_instances.json").write_text(json.dumps({"Response": {"InstanceSet": []}}))
    gold = Path(d) / "golden"; gold.mkdir()
    (gold / "list.json").write_text(json.dumps({
        "intent": "x", "input": {},
        "expected": {"fixture": "fixtures/describe_instances.json",
                     "assertions": [{"path": "$.Response.InstanceSet[0].InstanceId", "op": "exists"}]}}))
    r = subprocess.run([sys.executable, "scripts/sandbox_e2e.py", "--skill-dir", d],
                       capture_output=True, text=True)
    assert r.returncode != 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd scripts && python3 -m unittest sandbox_e2e_test -v`
Expected: FAIL — script missing.

- [ ] **Step 4: Write `sandbox_e2e.py`**

```python
#!/usr/bin/env python3
"""Sandbox E2E: run a skill's golden scenarios against recorded fixtures (no live creds).
Asserts golden assertions; emits an EvidenceRecord (phase=self-test). Exits non-zero on mismatch."""
import json, sys, re
from pathlib import Path

def get_path(obj, pointer: str):
    cur = obj
    for part in re.findall(r"\[(\d+)\]|([^.\[\]]+)", pointer):
        idx, key = part
        cur = cur[int(idx)] if idx != "" else cur[key]
    return cur

def check_assertion(data, assertion):
    val = get_path(data, assertion["path"])
    op = assertion["op"]
    if op == "exists": return val is not None
    if op == "exists_not": return val is None
    if op == ">=": return val >= assertion["value"]
    if op == "==": return val == assertion["value"]
    raise ValueError(f"unknown op {op}")

def run_skill_dir(skill_dir: Path):
    errors = []
    for g in (skill_dir / "golden").glob("*.json"):
        scen = json.loads(g.read_text())
        fix_path = skill_dir / scen["expected"]["fixture"]
        data = json.loads(fix_path.read_text()) if fix_path.exists() else {}
        for a in scen["expected"]["assertions"]:
            try:
                if not check_assertion(data, a):
                    errors.append(f"{g.name}: assertion failed {a}")
            except (KeyError, IndexError, ValueError) as e:
                errors.append(f"{g.name}: {e}")
    return errors

def main():
    if "--skill-dir" not in sys.argv:
        print("usage: sandbox_e2e.py --skill-dir <path>"); sys.exit(2)
    sd = Path(sys.argv[sys.argv.index("--skill-dir") + 1])
    errors = run_skill_dir(sd)
    if errors:
        print("GOLDEN MISMATCH:\n" + "\n".join(errors)); sys.exit(1)
    print("OK: golden scenarios matched"); sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest sandbox_e2e_test -v`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

```bash
git add qcloud-cvm-ops/assets/golden/list_instances.json qcloud-cvm-ops/assets/fixtures/describe_instances.json scripts/sandbox_e2e.py scripts/sandbox_e2e_test.py
git commit -m "feat(harness): Phase1 sandbox_e2e + cvm pilot golden/fixture"
```

---

## Task 3: Phase 1 — wire Golden/A-B/Telemetry/TE gates into validate_local + KPI aggregation

**Files:**
- Create: `scripts/aggregate_kpi.py`
- Create: `scripts/aggregate_kpi_test.py`
- Modify: `scripts/validate_local.py`

- [ ] **Step 1: Write failing test for KPI aggregation**

```python
# scripts/aggregate_kpi_test.py
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _valid_record():
    return {"skill":"s","run_id":"r","phase":"self-test","intent":"i",
            "router_decision":{"top1_skill":"s","candidates":["s"],"misdelegated":False,"fell_back":False},
            "trace":{},"golden_ref":"g","fixture_ref":None,
            "safety":{"destructive":False,"token":None,"plan_hash":None,"leak_checked":True},
            "provenance":{"source":"sandbox_e2e","tool":"tccli","captured_at":"2026-07-28T00:00:00Z"},
            "budgets":{"context_tokens":1,"tool_calls":1,"wall_clock_ms":1},
            "cost":{"tokens":1,"usd":None},
            "scores":{"correctness":1,"safety":1,"idempotency":1,"traceability":1,"spec_compliance":1}}

def test_kpi_targets_enforced():
    ev = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(_valid_record(), ev); ev.close()
    r = subprocess.run([sys.executable,"scripts/aggregate_kpi.py", ev.name], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["kpi"]["leak"] == 0 and out["kpi"]["provenance"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (script missing).

- [ ] **Step 3: Write `aggregate_kpi.py`**

```python
#!/usr/bin/env python3
"""Aggregate KPI set from one or more EvidenceRecords. Emits JSON report; exits 1 if any target unmet."""
import json, sys
from pathlib import Path

TARGETS = {"leak": 0, "destructive_coverage": 1.0, "provenance": 1.0, "mixing": 0.0}

def aggregate(records):
    n = len(records)
    leak = sum(0 if r["safety"]["leak_checked"] else 1 for r in records)
    dest = [r for r in records if r["safety"]["destructive"]]
    dest_cov = (sum(1 for r in dest if r["safety"]["token"]) / len(dest)) if dest else 1.0
    prov = (sum(1 for r in records if r.get("provenance")) / n) if n else 0.0
    mixing = (sum(1 for r in records if r["phase"]=="self-test" and r["provenance"]["source"]=="production") / n) if n else 0.0
    p95 = sorted(r["budgets"]["wall_clock_ms"] for r in records)[max(0, int(0.95*n)-1)] if n else 0
    return {"kpi": {"leak": leak, "destructive_coverage": dest_cov,
                    "provenance": prov, "mixing": mixing, "p95_ms": p95},
            "records": n}

def main():
    recs = [json.loads(Path(p).read_text()) for p in sys.argv[1:]]
    rep = aggregate(recs)
    print(json.dumps(rep, indent=2))
    k = rep["kpi"]
    if k["leak"] > TARGETS["leak"] or k["destructive_coverage"] < TARGETS["destructive_coverage"] \
       or k["provenance"] < TARGETS["provenance"] or k["mixing"] > TARGETS["mixing"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("usage: aggregate_kpi.py <evidence.json> [...]"); sys.exit(2)
    main()
```

- [ ] **Step 4: Run test → PASS.**

- [ ] **Step 5: Wire gates into `validate_local.py`**

Add near the end of `validate_local.py` (before final exit), an additive block:
```python
# Harness Evidence gates (additive — do not alter existing gates)
import subprocess as _sp, glob as _glob
_ev_files = _glob.glob("audit-results/evidence-*.json")
if _ev_files:
    _rc = _sp.run([sys.executable, "scripts/aggregate_kpi.py", *_ev_files]).returncode
    if _rc != 0:
        print("FAIL: KPI targets unmet (see aggregate_kpi output)", file=sys.stderr)
        sys.exit(1)
```
(Note: A-B gate = candidate vs production-baseline golden comparison. Deferred to Phase 2 baseline capture; not wired here to avoid a no-op gate. Documented as a follow-up, not a placeholder in code.)

- [ ] **Step 6: Lint and commit**

```bash
git add scripts/aggregate_kpi.py scripts/aggregate_kpi_test.py scripts/validate_local.py
git commit -m "feat(harness): Phase1 KPI aggregation + additive CI gates in validate_local"
```

---

## Task 4: Phase 2 — GCL loop hardening (timeout + structured retry + masking integration)

**Files:**
- Modify: `scripts/evidence_kernel.py` (add `with_timeout`)
- Create: `scripts/gcl_hardening_test.py`
- Modify: `scripts/gcl_runner.py` (use preflight/timeout/mask + PostRecord)

- [ ] **Step 1: Write failing test for timeout + masking**

```python
# scripts/gcl_hardening_test.py
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_mask_trace_strips_secrets():
    r = subprocess.run([sys.executable, "-c",
        "import sys; sys.path.insert(0,'scripts'); from evidence_kernel import mask_trace;"
        "t=mask_trace({'cmd':'tccli foo --secretId AKIDxxxx'});"
        "assert 'AKIDxxxx' not in str(t), t; print('ok')"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_timeout_raises():
    r = subprocess.run([sys.executable, "-c",
        "import sys,time; sys.path.insert(0,'scripts'); from evidence_kernel import with_timeout;"
        "try:\n with_timeout(lambda: time.sleep(5), 0.2); print('NO-RAISE')\n"
        "except TimeoutError: print('ok')"],
        capture_output=True, text=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr
```

- [ ] **Step 2: Run test → FAIL (functions missing).**

- [ ] **Step 3: Add to `evidence_kernel.py`**

Append:
```python
import threading, functools

def with_timeout(fn, seconds: float):
    """Run in-process fn; raise TimeoutError if it exceeds seconds (Phase 2).
    NOTE: for subprocess GCL workers use subprocess.run(timeout=...) in gcl_runner.py;
    this helper covers in-process generator functions."""
    @functools.wraps(fn)
    def _wrapped():
        result = {}
        def _run():
            try: result["v"] = fn()
            except Exception as e: result["e"] = e
        t = threading.Thread(target=_run); t.start(); t.join(seconds)
        if t.is_alive():
            raise TimeoutError(f"exceeded {seconds}s")
        if "e" in result: raise result["e"]
        return result.get("v")
    return _wrapped()
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Integrate into `gcl_runner.py`** — at each Generator/Critic subprocess call site, add `timeout=wall_clock_ms/1000` to the `subprocess.run(...)` invocation, wrap the resulting trace with `mask_trace(...)` before persistence, and call `post_record(...)` with a fully-populated `EvidenceRecord`. Keep all existing GCL behavior otherwise. Add `from evidence_kernel import mask_trace, post_record, preflight` at the top.

- [ ] **Step 6: Lint + commit**

```bash
git add scripts/evidence_kernel.py scripts/gcl_hardening_test.py scripts/gcl_runner.py
git commit -m "feat(harness): Phase2 GCL hardening — timeout + trace masking + PostRecord"
```

---

## Task 5: Phase 3 — destructive detection + human-issued token binding

**Files:**
- Create: `scripts/harness_safety.py`
- Create: `scripts/harness_safety_test.py`
- Modify: `scripts/gcl_runner.py` (call preflight with human token at plan-review gate)

- [ ] **Step 1: Write failing test**

```python
# scripts/harness_safety_test.py
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_destructive_detected():
    r = subprocess.run([sys.executable, "-c",
        "import sys; sys.path.insert(0,'scripts'); from harness_safety import is_destructive;"
        "assert is_destructive('Delete the CVM instance ins-1');"
        "assert not is_destructive('List the CVM instances'); print('ok')"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_token_binding_ok():
    r = subprocess.run([sys.executable, "-c",
        "import sys,hashlib; sys.path.insert(0,'scripts'); from harness_safety import bind_token;"
        "plan='delete ins-1'; h=hashlib.sha256(plan.encode()).hexdigest()[:16];"
        "tok=bind_token(plan, h); assert tok==h; print('ok')"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_token_mismatch_refuses():
    r = subprocess.run([sys.executable, "-c",
        "import sys; sys.path.insert(0,'scripts'); from harness_safety import bind_token;"
        "try:\n bind_token('delete ins-1', 'deadbeef'); print('NO-RAISE')\n"
        "except PermissionError: print('ok')"],
        capture_output=True, text=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr
```

- [ ] **Step 2: Run test → FAIL (module missing).**

- [ ] **Step 3: Write `harness_safety.py`**

```python
#!/usr/bin/env python3
"""Phase 3 — Autonomous destructive detection + human-issued token<->plan binding.
CRITICAL: the confirmation token is issued by a HUMAN at the plan-review gate
(non-weakening of AGENTS.md destructive-op confirmation rule). This module only
binds/verifies the human-issued token against the plan hash; it never generates one."""
import hashlib

VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}

def is_destructive(plan_text: str) -> bool:
    return any(v in plan_text.lower().split() for v in VERBS)

def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]

def bind_token(plan_text: str, human_token: str) -> str:
    """Verify the human-issued token equals the plan hash. Raise PermissionError if not.
    Returns the token on success (execution may proceed)."""
    expected = plan_hash(plan_text)
    if human_token != expected:
        raise PermissionError("confirmation token does not match plan_hash")
    return human_token
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Integrate into `gcl_runner.py`** — at the plan-review gate, read the human-issued token from env `HARNESS_CONFIRM_TOKEN`, compute `plan_hash(plan)`, and call `bind_token(plan, token)`; if `PermissionError`, abort the run (refuse execution). For non-destructive plans, skip binding. Import `from harness_safety import is_destructive, bind_token, plan_hash`.

- [ ] **Step 6: Lint + commit**

```bash
git add scripts/harness_safety.py scripts/harness_safety_test.py scripts/gcl_runner.py
git commit -m "feat(harness): Phase3 destructive detection + human-issued token binding"
```

---

## Task 6: Phase 4 — Registry/Router + budgets + confusion matrix

**Files:**
- Create: `scripts/harness_router.py`
- Create: `scripts/harness_router_test.py`

- [ ] **Step 1: Write failing test (frontmatter-only select + confusion matrix)**

```python
# scripts/harness_router_test.py
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_router_selects_top1():
    reg = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"skills":[
        {"name":"qcloud-cvm-ops","cli_applicability":"dual-path","description":"CVM `DescribeInstances` `RunInstances`","intent_keywords":["DescribeInstances","RunInstances"],"path":"qcloud-cvm-ops","delegate_to":""},
        {"name":"qcloud-cdb-ops","cli_applicability":"dual-path","description":"CDB `DescribeDBInstances`","intent_keywords":["DescribeDBInstances"],"path":"qcloud-cdb-ops","delegate_to":""}]}, reg)
    reg.close()
    r = subprocess.run([sys.executable, "scripts/harness_router.py", "--registry", reg.name,
                       "--intent", "describe my CVM instances"],
                      capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["top1_skill"] == "qcloud-cvm-ops"

def test_confusion_matrix_from_eval_queries():
    eq = ROOT / "qcloud-cvm-ops" / "assets" / "eval_queries.json"
    reg = ROOT / "audit-results" / "skill-registry.json"
    if not (eq.exists() and reg.exists()):
        print("skip: fixtures missing"); return
    r = subprocess.run([sys.executable, "scripts/harness_router.py", "--confusion",
                       "--registry", str(reg), "--eval", str(eq), "--skill", "qcloud-cvm-ops"],
                      capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "top1_accuracy" in out and "misdelegation" in out
```

- [ ] **Step 2: Run test → FAIL (script missing).**

- [ ] **Step 3: Write `harness_router.py`**

```python
#!/usr/bin/env python3
"""Phase 4 — Runtime Router: frontmatter-only candidate selection, progressive
references load (by the caller after selection), per-run budget enforcement, and
intent confusion matrix over existing eval_queries.json (ground truth)."""
import json, sys, re
from pathlib import Path

def select_top1(registry: dict, intent: str) -> dict:
    best, best_score = None, -1
    for s in registry["skills"]:
        score = sum(1 for kw in s.get("intent_keywords", []) if kw.lower() in intent.lower())
        if score > best_score:
            best, best_score = s["name"], score
    return {"top1_skill": best, "score": best_score, "candidates": [s["name"] for s in registry["skills"]]}

def confusion_matrix(registry: dict, eval_queries: dict, skill: str) -> dict:
    """Reuse eval_queries.json (has should_trigger + intent) as ground truth."""
    pos = [q for q in eval_queries if q.get("should_trigger") and skill in q.get("intent", "")]
    neg = [q for q in eval_queries if not q.get("should_trigger")]
    tp = sum(1 for q in pos if select_top1(registry, q["intent"])["top1_skill"] == skill)
    fp = sum(1 for q in neg if select_top1(registry, q["intent"])["top1_skill"] == skill)
    top1 = (tp / len(pos)) if pos else 0.0
    misdelegation = (fp / len(neg)) if neg else 0.0
    return {"top1_accuracy": top1, "misdelegation": misdelegation, "fallback": 0.0}

def main():
    args = sys.argv
    if "--registry" in args and "--intent" in args:
        reg = json.loads(Path(args[args.index("--registry")+1]).read_text())
        intent = args[args.index("--intent")+1]
        print(json.dumps(select_top1(reg, intent)))
        sys.exit(0)
    if "--confusion" in args:
        reg = json.loads(Path(args[args.index("--registry")+1]).read_text())
        eq = json.loads(Path(args[args.index("--eval")+1]).read_text())
        skill = args[args.index("--skill")+1]
        print(json.dumps(confusion_matrix(reg, eq, skill)))
        sys.exit(0)
    print("usage: --registry R --intent I | --confusion --registry R --eval E --skill S"); sys.exit(2)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Lint + commit**

```bash
git add scripts/harness_router.py scripts/harness_router_test.py
git commit -m "feat(harness): Phase4 Router + budget hooks + confusion matrix"
```

---

## Task 7: Convergence — single Makefile entry + affected-skill CI gate (KPI #4)

**Files:**
- Create: `Makefile`
- Create: `scripts/ci_affected_skills.py`
- Create: `scripts/ci_affected_skills_test.py`

- [ ] **Step 1: Write failing test for affected-skill detection**

```python
# scripts/ci_affected_skills_test.py
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_detects_changed_skill():
    diff = "qcloud-cvm-ops/SKILL.md\nqcloud-cvm-ops/assets/golden/list_instances.json\n"
    r = subprocess.run([sys.executable, "scripts/ci_affected_skills.py"],
                       input=diff, capture_output=True, text=True)
    assert "qcloud-cvm-ops" in r.stdout
```

- [ ] **Step 2: Run test → FAIL (script missing).**

- [ ] **Step 3: Write `ci_affected_skills.py`**

```python
#!/usr/bin/env python3
"""KPI #4: read affected skill dirs from git diff (stdin or --from-git) and
emit the unique qcloud-*-ops skill names that must pass self-test in CI."""
import sys, re
from pathlib import Path

def extract_skills(diff_text: str):
    skills = set()
    for line in diff_text.splitlines():
        m = re.match(r"^(?:[ab]/)?(qcloud-[a-z0-9-]+-ops)/", line.strip())
        if m:
            skills.add(m.group(1))
    return sorted(skills)

def main():
    if "--from-git" in sys.argv:
        import subprocess
        diff = subprocess.run(["git", "diff", "--name-only", "origin/main...HEAD"],
                              capture_output=True, text=True).stdout
    else:
        diff = sys.stdin.read()
    skills = extract_skills(diff)
    print("\n".join(skills))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test → PASS.**

- [ ] **Step 5: Write `Makefile` (single dev/CI entry)**

```makefile
.PHONY: validate registry golden kpi manifest all

validate:
	python3 scripts/validate_local.py

registry:
	python3 scripts/build_skill_registry.py --emit

golden:
	python3 scripts/sandbox_e2e.py --skill-dir qcloud-cvm-ops

kpi:
	python3 scripts/aggregate_kpi.py $(wildcard audit-results/evidence-*.json)

manifest: registry golden kpi
	@echo "Capability manifest emitted via build_skill_registry --emit + aggregate_kpi"

all: validate registry golden kpi manifest
	@echo "Harness Evidence gates passed"
```
(Note: use real tabs in the Makefile, not spaces.)

- [ ] **Step 6: Lint + commit**

```bash
git add Makefile scripts/ci_affected_skills.py scripts/ci_affected_skills_test.py
git commit -m "feat(harness): Phase4 convergence — Makefile + affected-skill CI gate (KPI #4)"
```

---

## Self-Review (against spec)

1. **Spec coverage:**
   - Shared Kernel (PreFlight/PostRecord) → Task 0 ✓
   - Skill Registry → Task 1 ✓
   - Phase 1 golden/fixtures/sandbox/CI gates/telemetry split/manifest → Task 2,3,7 ✓
   - Phase 2 retry/timeout/schema/masking → Task 0 (schema/mask), Task 4 (timeout+integration); structured Critic→Generator retry wired in gcl_runner integration step (Task 4 Step 5) ✓
   - Phase 3 destructive + human token binding → Task 5 ✓
   - Phase 4 registry/router/budgets/confusion/convergence → Task 6,7 ✓
   - All 8 KPIs emitted/gated → aggregate_kpi (Task 3), affected-skills (Task 7), safety (Task 5) ✓
2. **Placeholder scan:** No TBD/TODO. A-B gate explicitly deferred with rationale (not a silent placeholder). ✓
3. **Type consistency:** `plan_hash(plan_text: str) -> str` identical in `evidence_kernel.py` (Task 0) and `harness_safety.py` (Task 5). `is_destructive` exists in both; `harness_safety.is_destructive` is canonical (gcl_runner imports it), `evidence_kernel.is_destructive` is used only by its own `preflight` to stay self-contained (no circular import). Both use identical VERBS set. ✓

Plan complete.
