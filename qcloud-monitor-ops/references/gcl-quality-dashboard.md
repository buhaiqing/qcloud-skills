# GCL Quality Dashboard — Phase 3

> **AGENTS.md GCL Phase 3:** Ingest `gcl-trace-*.json` artifacts and surface skill execution quality for observability. Read-only aggregation — does not mutate cloud alarm policies unless user explicitly requests threshold tuning.

## Overview

```
audit-results/gcl-trace-*.json
        │
        ▼
python3 scripts/gcl_trace_aggregate.py
        │
        ▼
audit-results/gcl-quality-summary-*.json  ──► Monitor dashboard / webhook / inspection embed
```

## Step 1: Aggregate Traces

```bash
# All traces in audit-results/
python3 scripts/gcl_trace_aggregate.py

# Last 24h only
python3 scripts/gcl_trace_aggregate.py --since-hours 24

# Specific files (post CI or single skill run)
python3 scripts/gcl_trace_aggregate.py --input audit-results/gcl-trace-20260613-*.json
```

Output schema: [`assets/gcl-quality-summary.schema.json`](../assets/gcl-quality-summary.schema.json).

## Step 2: Quality Metrics (Local Contract)

| Metric | JSON path | Alert when |
|--------|-----------|------------|
| Pass rate | `pass_rate` | < `gcl_quality.pass_rate_warn` (default 0.85) |
| Safety failures | `totals.SAFETY_FAIL` | > 0 |
| MAX_ITER exhaustion | `totals.MAX_ITER` | > `gcl_quality.max_iter_warn_count` |
| Avg correctness | `avg_rubric_scores.correctness` | < 0.5 |
| Per-skill pass rate | `by_skill.{skill}.PASS / by_skill.{skill}.total` | skill-specific SLO |

Configure thresholds in [`example-config.yaml`](../assets/example-config.yaml) → `gcl_quality`.

## Step 3: Monitor Integration Paths

### A) Webhook / automation (recommended)

After aggregate, POST summary excerpt to an existing Monitor **Webhook** notice channel (no new cloud APIs):

```bash
SUMMARY=$(ls -t audit-results/gcl-quality-summary-*.json | head -1)
python3 -c "
import json, sys
s=json.load(open(sys.argv[1]))
print(json.dumps({
  'event': 'gcl_quality_summary',
  'pass_rate': s['pass_rate'],
  'total_runs': s['totals']['total_runs'],
  'safety_fail': s['totals']['SAFETY_FAIL'],
  'by_skill': s['by_skill']
}))" "$SUMMARY"
# Pipe to your webhook URL configured in Monitor alarm notice
```

### B) CLS log sink (optional)

If `{{user.gcl_cls_topic_id}}` is set, emit one JSON log line per summary for LogSearch dashboards:

```bash
tccli cls UploadLog --TopicId "{{user.gcl_cls_topic_id}}" \
  --LogGroupList '[{"Logs":[{"Time":'$(date +%s)',"Contents":[{"Key":"event","Value":"gcl_quality_summary"},{"Key":"payload","Value":"'"$(cat $SUMMARY | tr -d '\n')"'"}]}]}]'
```

Verify `UploadLog` availability: `tccli cls help`. SDK fallback: [`api-sdk-usage.md`](api-sdk-usage.md).

### C) Custom metric (advanced)

If tenant pre-provisioned a **custom metric** namespace in Cloud Monitor, map:

| Summary field | Suggested metric name | Dimension |
|---------------|----------------------|-----------|
| `pass_rate` | `GCLPassRate` | `skill=aggregate` |
| `totals.SAFETY_FAIL` | `GCLSafetyFailCount` | `skill=aggregate` |
| `by_skill.*.PASS/total` | `GCLPassRate` | `skill={{skill_id}}` |

Use API for latest upload API name: `tccli monitor help` (product evolves). **Do not invent undocumented upload methods.** When upload API unavailable, use path A or B.

## Step 4: Alarm on Quality Regression (optional)

Pre-flight:

- [ ] Latest `gcl-quality-summary-*.json` exists
- [ ] Thresholds from `gcl_quality` config loaded
- [ ] Webhook or CLS topic configured

If `pass_rate < gcl_quality.pass_rate_critical` OR `totals.SAFETY_FAIL > 0`:

1. Emit Monitor alarm **notification** via existing notice template (webhook body from Step 3A).
2. **Do not** auto-modify skill rubrics or cloud resources.
3. Delegate deep RCA to `qcloud-aiops-diagnosis` when quality drop correlates with production incidents.

## Step 5: Phase 4 — Wire rubric pass-rate to Cloud Monitor alarms

> **AGENTS.md §10.10 Phase 4:** Close the loop by ensuring Cloud Monitor alarm
> policies exist for GCL quality SLOs. Custom metric namespace `qce/gcl_custom`
> holds two metrics: `GCLPassRate` (gauge, 0–1) and `GCLSafetyFailCount` (counter).

### 5.1 Plan first (no mutations)

```bash
python3 scripts/gcl_alarm_wire.py plan \
  --config qcloud-monitor-ops/assets/example-config.yaml
# Or with a specific summary:
python3 scripts/gcl_alarm_wire.py plan \
  --summary audit-results/gcl-quality-summary-LATEST.json
```

Output is a JSON report: thresholds, breach evaluation, and the alarm-policy
operations that **would** be applied. Exit code `1` ⇒ SLO breach detected;
exit code `0` ⇒ within SLO. CI / first-time setup should run `plan` only.

### 5.2 Apply (idempotent — safe to re-run)

```bash
# Dry-run first (recommended)
python3 scripts/gcl_alarm_wire.py apply --dry-run

# Real apply — invokes `tccli monitor CreateAlarmPolicy`
python3 scripts/gcl_alarm_wire.py apply
```

The script enforces three alarm policies by default:

| Policy | Severity | Metric | Trigger |
|---|---|---|---|
| `gcl-quality-pass-rate-critical` | CRITICAL | `GCLPassRate` | `< gcl_quality.pass_rate_critical` (default 0.70) for 5 min |
| `gcl-quality-pass-rate-warn` | WARN | `GCLPassRate` | `< gcl_quality.pass_rate_warn` (default 0.85) for 10 min |
| `gcl-safety-fail-critical` | CRITICAL | `GCLSafetyFailCount` | `> 0` for 1 min (any SAFETY_FAIL) |

### 5.3 Custom metric upload (GCL → Cloud Monitor)

For Cloud Monitor to evaluate the policies above, the runtime must publish
`GCLPassRate` and `GCLSafetyFailCount` into namespace `qce/gcl_custom`. Two
patterns:

```bash
# Path A — Inline upload after each aggregate (recommended)
SUMMARY=$(ls -t audit-results/gcl-quality-summary-*.json | head -1)
python3 - <<'PY'
import json, subprocess, sys
s = json.load(open("$SUMMARY".replace("$SUMMARY", "$SUMMARY")))
metric_value = s["pass_rate"]
# tccli monitor PutMonitorData — verify with `tccli monitor help`
# Custom metric upload: namespace="qce/gcl_custom", metricName="GCLPassRate",
# dimensions=[{"Name":"skill","Value":"aggregate"}], value=metric_value
PY

# Path B — Cron / scheduled task writes a JSON file the script ingests
# (preferred for stable deployment)
```

If `tccli monitor PutMonitorData` is unavailable in your account (some
sub-accounts have monitoring-write restrictions), fall back to **Path A
webhook only** (Step 3A) and let the alarm policies fire on stale data;
the dashboard surfaces the breach via webhook regardless.

### 5.4 Operational checklist

| # | Check |
|---|--------|
| 1 | `tccli monitor help` lists `CreateAlarmPolicy` and `PutMonitorData` |
| 2 | `python3 scripts/gcl_alarm_wire.py plan` exits 0 with latest summary |
| 3 | `python3 scripts/gcl_alarm_wire.py apply` ran clean (no FAILED lines) |
| 4 | `tccli monitor DescribeAlarmPolicies --Module monitor --PolicyName gcl-quality-pass-rate-critical` returns the policy |
| 5 | Custom metric `qce/gcl_custom / GCLPassRate` is registered (one-time via Cloud Monitor console or `tccli monitor CreateCustomMetric` if supported in your version) |

## Cross-Skill Hooks

| Producer | Consumer | Handoff |
|----------|----------|---------|
| Any skill GCL run | This workflow | `audit-results/gcl-trace-*.json` |
| `gcl_trace_aggregate.py` | Monitor dashboard | `gcl-quality-summary-*.json` |
| `qcloud-aiops-diagnosis` | Monitor | Optional `gcl_trace_ref` on RCA/Event bundle |
| `qcloud-proactive-inspection` | Report §GCL Quality | Embed summary when `--since-hours` overlaps inspection window |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Phase 3 initial — aggregate script integration, webhook/CLS paths, config thresholds |
| 1.1.0 | 2026-06-18 | **Phase 4:** added `scripts/gcl_alarm_wire.py` (`plan` / `apply` / `--dry-run`); Step 5 covers tccli `CreateAlarmPolicy` for `GCLPassRate` / `GCLSafetyFailCount`; custom-metric upload path documented; operational checklist |
