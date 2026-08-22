# Skill Version Matrix + Agent SLO Dashboard — Design

## 1. Background

Skills evolve independently from the agent runtime. Without a compatibility
matrix, agents may invoke skills requiring newer tccli/agent features and fail
at runtime. An SLO dashboard surfaces per-agent reliability and latency health.

## 2. Matrix Model (`scripts/skill_version_matrix.py`)

- `SKILL_COMPAT: dict[str, dict]` — single source of truth. Keys: skill name.
  Values: `{min_agent_version, max_agent_version (None = unbounded), tccli_min, notes}`.
  Covers at least `qcloud-cvm-ops`, `qcloud-cdb-ops`, `qcloud-cos-ops`, `qcloud-finops-ops`.
- `parse_version(v: str) -> tuple[int,int,int]` — semver; `"1.2"` → `(1,2,0)`.
- `is_compatible(skill, agent_version, *, tccli_version=None) -> bool` — range check +
  optional tccli floor. Unknown skill → False.
- `compatible_skills(agent_version) -> list[str]` — filter by `is_compatible`.
- `render_matrix() -> str` — markdown table `| skill | agent range | tccli min | notes |`.

## 3. SLO Model (`scripts/agent_slo.py`)

- `SLO(name, target: float 0-1 or threshold, window: str)` — dataclass frozen.
- Default SLOs: `success_rate≥0.99`, `p95_latency_ms≤2000`, `availability≥0.995` (window `30d`).
- `SLOMonitor` holds `_samples: dict[agent, dict[metric, list[float]]]`.
  - `record(agent, metric, value)` — append sample.
  - `compliance(agent) -> dict[str,float]` — per-SLO pass fraction; no samples → 1.0.
  - `breaches(agent) -> list[str]` — SLOs with compliance < 1.0.
  - Latency SLOs (`latency`/`p95`/`p99`/`duration` in name) use `value <= target`; others `value >= target`.
- `render_dashboard(monitor) -> str` — markdown table per `(agent,SLO)` with target,
  compliance %, breached flag; deterministic (sorted agents/SLOs).

## 4. Verification

- Lint: `python3 -m ruff check scripts/skill_version_matrix.py scripts/skill_version_matrix_test.py scripts/agent_slo.py scripts/agent_slo_test.py`
- Tests: `python3 -m pytest scripts/skill_version_matrix_test.py scripts/agent_slo_test.py -q`
- Manual: `python3 -c "from skill_version_matrix import render_matrix; print(render_matrix())"`

## 5. Files

- `scripts/skill_version_matrix.py`
- `scripts/agent_slo.py`
- `scripts/skill_version_matrix_test.py`
- `scripts/agent_slo_test.py`
