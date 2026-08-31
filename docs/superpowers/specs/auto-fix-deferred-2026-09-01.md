# Deferred Blocks — Auto-Fix 2026-09-01

5 blocks remain after HIGH-confidence auto-apply. Require manual `> 权威实现见 <path>` annotation.

## D1: gcl-enforcement-plan.md:244

**Block**: 35 lines — `execute_gcl_with_monitoring(user_request)` integration function
**First line**: `# 在 GCL 执行中集成监控`
**Pattern**: Chinese comment header, no class/func match in `scripts/`

| Candidate | Evidence |
|-----------|----------|
| `scripts/gcl_monitor.py` | Block uses `GCLExecutionMonitor` class defined there |
| `scripts/gcl_enforcer.py` | Block creates `GCLOrchestrator` from enforcer module |

**Recommendation**: `> 权威实现见 scripts/gcl_monitor.py` (block references GCLExecutionMonitor)

---

## D2: gcl-multi-subagent-rule.md:118

**Block**: 45 lines — `validate_gcl_architecture()` + `load_project_config()`
**First line**: `#!/usr/bin/env python3`
**Pattern**: Shebang header; functions exist only as local/helper patterns

| Candidate | Evidence |
|-----------|----------|
| `scripts/check_gcl_conformance.py` | Script is the validator for this rule doc |
| none | Functions `validate_gcl_architecture`/`load_project_config` are NOT defined in scripts/ |

**Recommendation**: Manual review needed — script `validate_gcl_architecture.py` referenced in doc does not exist in repo.

---

## D3: superpowers/plans/2026-07-28-harness-engineering-optimization-plan.md:176

**Block**: 65 lines — `evidence_kernel.py` validator (load_schema/type_ok/validate/main)
**First line**: `#!/usr/bin/env python3`
**Pattern**: Shebang header; `load_schema` is a local function inside `validate()`, not top-level

| Candidate | Evidence |
|-----------|----------|
| `scripts/evidence_kernel.py` | Block docstring explicitly references this file |
| none | `load_schema` is nested, not a top-level def |

**Recommendation**: `> 权威实现见 scripts/evidence_kernel.py` (confirmed by block docstring)

---

## D4: superpowers/specs/aiops-cruise-enhancement-design.md:376

**Block**: 49 lines — ML module self-test (IsolationForestDetector/ThresholdDetector/LinearTrendPredictor)
**First line**: `# ML 模块自验`
**Pattern**: No class name match in `scripts/`/`references/`

| Candidate | Evidence |
|-----------|----------|
| `qcloud-copilot/copilot/ml/` | External module not in SEARCH_ROOTS |
| none | Classes not found in `scripts/` or `references/` |

**Recommendation**: Manual — classes may be in `qcloud-copilot` submodule or unimplemented.

---

## D5: superpowers/specs/obs-1-observability-enhancement-design.md:62

**Block**: 39 lines — Observable protocol (MetricKind/Metric/Span/ObservableSink)
**First line**: `from __future__ import annotations`
**Pattern**: Classes `MetricKind`, `Metric`, `Span`, `ObservableSink` exist in `qcloud-copilot/copilot/observ.py`

| Candidate | Evidence |
|-----------|----------|
| `qcloud-copilot/copilot/observ.py` | Classes defined there (outside SEARCH_ROOTS) |
| `scripts/` | Not found in scripts/ |

**Recommendation**: `> 权威实现见 qcloud-copilot/copilot/observ.py` (requires SEARCH_ROOTS to include `qcloud-copilot/` — future enhancement)

---

## Summary Table

| ID | File | Line | Lines | Reason Unfixable |
|----|------|------|-------|-----------------|
| D1 | gcl-enforcement-plan.md | 244 | 35 | Chinese header, class match possible |
| D2 | gcl-multi-subagent-rule.md | 118 | 45 | Shebang + no script exists |
| D3 | harness-optimization-plan.md | 176 | 65 | Shebang + nested function name |
| D4 | aiops-cruise-enhancement-design.md | 376 | 49 | Classes in qcloud-copilot submodule |
| D5 | obs-1-observability-design.md | 62 | 39 | Classes in qcloud-copilot submodule |
