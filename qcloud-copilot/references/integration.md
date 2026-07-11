# AIOps Copilot — Integration

## Integration Principle

**Zero modifications to existing skill directories.** All integration is via
subprocess + JSON pipe. No skill is imported directly as a Python module.

## Skill Dispatch Protocol

1. `SkillDispatcher.validate_skill(skill)` → checks `KNOWN_SKILLS` registry
2. `SkillDispatcher.execute(step, context)` → returns `StepResult`
3. For read-only: tccli first → SDK fallback after 3 retries
4. For destructive: route through product skill's GCL runner

## KNOWN_SKILLS Registry

```python
KNOWN_SKILLS = {
    "qcloud-cvm-ops", "qcloud-redis-ops", "qcloud-cdb-ops",
    "qcloud-tke-ops", "qcloud-monitor-ops",
    "qcloud-cam-ops", "qcloud-vpc-ops", "qcloud-clb-ops",
    "qcloud-vpc-ops", "qcloud-cbs-ops", "qcloud-cos-ops",
    "qcloud-cdn-ops", "qcloud-scf-ops", "qcloud-ssl-ops",
    "qcloud-cdn-ops", "qcloud-finops-ops", "qcloud-monitor-ops",
    "qcloud-monitor-ops", "qcloud-proactive-inspection",
}
```

## GCL Runner Adapter

```python
# copilot/integration/gcl.py
def run_gcl(skill: str, operation: str, params: dict) -> dict:
    cmd = ["python", "-m", "qcloud_agent_infra.gcl_runner",
           "--skill", skill, "--operation", operation,
           "--params", json.dumps(params)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)
```

## Memor Session Persistence

Sessions stored at `~/.omo/memor/copilot/sessions/<session_id>.json`.
Context inheritance: targets, region, customer carry over from prior turns.

## Health Metrics

Events written to `~/.runtime/health/skill-metrics.jsonl` (append-only JSONL).
Schema: `ts`, `skill`, `operation`, `status`, `duration_ms`, `trace_id`, `error_code`.

## Audit Trail

GCL traces persisted to `~/.omo/memor/copilot/audit/<session_id>/step-<id>-trace-<ts>.json`.
