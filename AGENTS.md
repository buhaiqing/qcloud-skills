# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter that an agent reads as an instruction document — these are NOT executable code.

## Structure

```
qcloud-[product]-ops/     # 23 skill directories
  SKILL.md                # Core skill: YAML frontmatter (metadata) + Markdown runbook
  assets/
    eval_queries.json     # Intent classification test set for SKILL.md matching evaluation
    example-config.yaml   # Optional example YAML
  references/             # Supporting docs: cli-usage, api-sdk-usage, troubleshooting, etc.
```

Cross-product skills (no single-product prefix):
- `qcloud-aiops-diagnosis/` — multi-metric correlation diagnosis
- `qcloud-proactive-inspection/` — 5-step inspection pipeline
- `qcloud-well-architected-review/` — 4-pillar architecture assessment
- `qcloud-skill-generator/` — **meta-skill** for generating/updating other skills

## Key conventions

- **Dual-path execution**: `tccli` CLI is primary; `tencentcloud-sdk-python` is fallback for edge cases CLI does not cover. Never use web console as agent execution path.
- **Pre-check → Execute → Verify → Recover** workflow in every runbook.
- **Cross-skill delegation**: CVM delegates to VPC/CLB/COS; Monitor delegates to CVM/CLB/VPC; CDB/ES delegate to VPC/Monitor/COS. Check skills for explicit `delegate-to` markers.
- **UX spec** defined in `qcloud-skill-generator/references/user-experience-spec.md` — onboarding, minimal prompts, smart defaults, clear feedback.

## Prerequisites for execution

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

Requires `tccli` (pip-installable) and Python 3.8+.

## SKILL.md frontmatter fields

Key metadata used for agent routing and compatibility:
- `name` / `description` — skill identity and trigger conditions
- `compatibility` — execution environment requirements
- `cli_applicability` — `dual-path` means show both CLI and SDK steps
- `environment` — required env vars

## Evaluation

Each skill with `assets/eval_queries.json` provides intent classification test cases (`should_trigger: true/false`) for validating whether an agent correctly routes queries. No test runner exists in-repo — these are for external evaluation.

## Files that do NOT exist

- No `package.json`, `Makefile`, CI configs, or any executable code
- No linting, typechecking, or testing scripts
- Existing `AGENTS.md`, `CLAUDE.md`, `opencode.json` — all absent
- `.omc/`, `.omo/`, `.codebuddy/` are gitignored cache data
