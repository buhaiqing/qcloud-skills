# AIOps Diagnosis — Reference Index

Navigate by **symptom**, **output type**, or **workflow**.

## By Symptom

| Symptom | Start here |
|---------|------------|
| CPU/memory/latency spike | [`diagnosis-framework.md`](diagnosis-framework.md) → Workflow 1 |
| Connection timeout / refused | Workflow 2 + [`network-rca.md`](network-rca.md) Rule G |
| Disk/quota full | Workflow 3 |
| TKE alarm storm | [`alarm-handling.md`](alarm-handling.md) → Workflow 5 |
| CLB 5xx + Pod/Node | [`multi-source-rca.md`](multi-source-rca.md) → Workflow 6 |
| Post-deploy regression | [`change-correlation.md`](change-correlation.md) Rule F |
| CDB/Redis/ES primary | [`product-rca-rules.md`](product-rca-rules.md) Rules H–J |
| COS/CKafka/MongoDB/Postgres | [`product-rca-rules.md`](product-rca-rules.md) Rules K–N |
| SCF/CDN | [`product-rca-rules.md`](product-rca-rules.md) Rules O–P |
| CKafka lag/disk | [`product-rca-rules.md`](product-rca-rules.md) Rule L |
| SCF error/timeout | [`product-rca-rules.md`](product-rca-rules.md) Rule O |
| CDN origin 5xx | [`product-rca-rules.md`](product-rca-rules.md) Rule P |
| Bill + metrics joint | [`cross-skill-orchestration.md`](cross-skill-orchestration.md) F1/F2 |
| Proactive baseline scan | [`anomaly-detection.md`](anomaly-detection.md) → Workflow 8 |

## By Output Bundle

See [`output-schemas.md`](output-schemas.md) for JSON paths.

## By Workflow (#)

| # | Name | File |
|---|------|------|
| 1–4 | Symptom decision trees | [`diagnostic-workflows.md`](diagnostic-workflows.md) |
| 5 | TKE Event Bundle | [`alarm-handling.md`](alarm-handling.md) |
| 6 | Multi-Source RCA | [`multi-source-rca.md`](multi-source-rca.md) |
| 7 | Incident Timeline | [`incident-timeline.md`](incident-timeline.md) |
| 8 | Anomaly Bundle | [`anomaly-detection.md`](anomaly-detection.md) |
| 9 | Product + Network RCA | [`product-rca-rules.md`](product-rca-rules.md), [`network-rca.md`](network-rca.md) |
| 10 | Impact + KB | [`incident-knowledge.md`](incident-knowledge.md) |
| 11 | Cross-Skill | [`cross-skill-orchestration.md`](cross-skill-orchestration.md) |

## Execution & Quality

| Topic | File |
|-------|------|
| CLI + SDK (dual-path) | [`cli-usage.md`](cli-usage.md), [`api-sdk-usage.md`](api-sdk-usage.md) |
| Cross-skill routing | [`delegation-matrix.md`](delegation-matrix.md) |
| Log patterns | [`log-intelligence.md`](log-intelligence.md) |
| Errors / HALT / retry | [`troubleshooting.md`](troubleshooting.md) |
| GCL rubric | [`rubric.md`](rubric.md) |
| GCL prompts | [`prompt-templates.md`](prompt-templates.md) |
