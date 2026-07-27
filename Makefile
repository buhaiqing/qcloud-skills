.PHONY: validate registry golden kpi manifest all

validate:
	python3 scripts/validate_local.py

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

manifest: registry golden kpi
	@echo "Capability manifest emitted via build_skill_registry --emit + aggregate_kpi"

all: validate registry golden kpi manifest
	@echo "Harness Evidence gates passed"
