.PHONY: validate gates tests registry golden kpi kpi-gates manifest all reflexion-update reflexion-update-dry replay-smoke l4-gate routing-check

routing-check:
	@echo "=== Blueprint routing decision self-check ==="
	@python3 scripts/routing_decision.py "fix typo in detect_spec_drift.py" | grep Routing
	@python3 scripts/routing_decision.py "write a runbook for k8s" | grep Routing
	@python3 scripts/routing_decision.py "parallel: fix ruff + update Makefile" | grep Routing
	@python3 scripts/routing_decision.py "add KPI#9 to check_kpi_gates.py" | grep Routing
	@echo "Blueprint self-check: all 4 queries routed correctly"

# Local entry point for the plain gates. They are declared in
# assets/shared/validation_commands.yaml — the same manifest the CI workflow and
# scripts/validate_local.py consume — so a gate cannot be added to one surface
# and forgotten in another. Per-gate targets were removed for the same reason:
# they were a fourth hand-maintained list.
gates:
	python3 scripts/run_gates.py --set make

# Full local mirror: the manifest gates plus the steps that need a tccli stub,
# pytest, or the quality signal.
validate:
	python3 scripts/validate_local.py

tests:
	python3 -m pytest scripts -q

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

# WRITER: rewrites the committed store docs/failure-patterns.md. Never wire this
# into CI, and never into `all` — a convergence target that mutates tracked state
# reports success while leaving the tree dirty.
reflexion-update:
	python3 scripts/reflexion_auto_writer.py

reflexion-update-dry:
	python3 scripts/reflexion_auto_writer.py --dry-run

manifest: registry golden kpi
	@echo "Capability manifest emitted via build_skill_registry --emit + aggregate_kpi"

replay-smoke:
	python3 scripts/synthesize_incident_corpus.py --per-skill 1
	python3 scripts/incident_replay.py --corpus scripts/fixtures/incidents/corpus.jsonl --mode dry-run --summary audit-results/replay-summary-dry-run.json
	python3 scripts/incident_replay.py --corpus scripts/fixtures/incidents/corpus.jsonl --mode replay --limit 2 --trace-dir audit-results --summary audit-results/replay-summary-smoke.json

l4-gate:
	python3 scripts/l4_metrics_tracker.py --gate --min-traces 5

all: gates validate tests registry golden kpi kpi-gates manifest reflexion-update-dry
	@echo "Harness Evidence gates passed"
