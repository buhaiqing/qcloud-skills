.PHONY: validate registry golden kpi kpi-gates manifest all reflexion-update replay-smoke l4-gate compounding-checks

validate:
	python3 scripts/validate_local.py

compounding-checks:
	python3 scripts/check_spec_file_refs.py
	python3 scripts/check_doc_code_drift.py
	python3 scripts/check_yaml_python_drift.py

registry:
	python3 scripts/build_skill_registry.py --emit

golden:
	python3 scripts/sandbox_e2e.py --skill-dir qcloud-cvm-ops

kpi:
	@if ls audit-results/evidence-*.json >/dev/null 2>&1; then \
		python3 scripts/aggregate_kpi.py audit-results/evidence-*.json; \
	else \
		echo "no evidence files — KPI gate skipped"; \
	fi

# Aggregated CI gate for spec-mandated KPIs (KPI#1/#2/#3/#7).
# - KPI#1/#2 require evidence-*.json and are skipped otherwise (informational).
# - KPI#3 and KPI#7 are always enforced.
# Spec anchor: docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md
kpi-gates:
	python3 scripts/check_kpi_gates.py

reflexion-update:
	python3 scripts/reflexion_auto_writer.py

manifest: registry golden kpi
	@echo "Capability manifest emitted via build_skill_registry --emit + aggregate_kpi"

replay-smoke:
	python3 scripts/synthesize_incident_corpus.py --per-skill 1
	python3 scripts/incident_replay.py --corpus scripts/fixtures/incidents/corpus.jsonl --mode dry-run --summary audit-results/replay-summary-dry-run.json
	python3 scripts/incident_replay.py --corpus scripts/fixtures/incidents/corpus.jsonl --mode replay --limit 2 --trace-dir audit-results --summary audit-results/replay-summary-smoke.json

l4-gate:
	python3 scripts/l4_metrics_tracker.py --gate --min-traces 5

all: validate registry golden kpi kpi-gates manifest reflexion-update
	@echo "Harness Evidence gates passed"
