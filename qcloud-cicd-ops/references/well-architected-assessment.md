# Well-Architected Assessment — CI/CD

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Reliability

- **Pipeline retry strategy**: Configure auto-retry for transient failures
- **Multi-stage approval**: Require manual approval before production deploy
- **Artifact versioning**: Tag every build with unique version
- **Rollback capability**: Maintain ability to rollback to previous versions

## Security

- **Credential management**: Use environment variables (masked) for secrets
- **Code scanning**: Integrate SAST/DAST in pipeline
- **Access control**: Restrict pipeline modification permissions
- **Audit logging**: Enable comprehensive operation logging

## Cost

- **Build cache**: Enable dependency caching to reduce build time
- **Runner optimization**: Use appropriate compute resources
- **Artifact lifecycle**: Auto-delete old artifacts
- **Resource scheduling**: Schedule non-critical builds during off-peak

## Efficiency

- **Parallel stages**: Run independent tests concurrently
- **Pipeline templates**: Reuse standardized pipeline definitions
- **Caching**: Cache dependencies across builds
- **Incremental builds**: Build only changed components when possible

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Pipeline has automated rollback | High |
| Reliability | Critical deployments require approval | High |
| Security | Secrets are not in source code | Critical |
| Security | Pipeline has security scanning | High |
| Cost | Build cache is enabled | Medium |
| Cost | Unused artifacts are cleaned up | Medium |
| Efficiency | Parallel stage execution | Medium |
| Efficiency | Pipeline templates are used | Low |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cicd-ops` |
| `product` | `cicd` |
| Finding `id` pattern | `cicd-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability section |
| `security` | Security section |
| `cost` | Cost section |
| `efficiency` | Efficiency section |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local "Score Calculation" sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-cicd-ops",
  "product": "cicd",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-04T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 2,
  "pillars": {
    "reliability": {
      "score": 80,
      "status": "assessed",
      "findings": [
        {
          "id": "cicd-rel-001",
          "severity": "Medium",
          "confidence": "MEDIUM",
          "title": "No pipeline rollback strategy",
          "evidence": "Pipeline does not have automated rollback configured",
          "recommendation": "Configure auto-rollback for production deployments",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 85,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 70,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 75,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "Medium",
      "pillar": "reliability",
      "action": "Configure auto-rollback for production deployments",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [],
    "request_ids": []
  },
  "errors": []
}
```

## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/xxx)
- [CI/CD Best Practices](https://cloud.tencent.com/document/product/)
