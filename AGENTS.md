# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter that an agent reads as an instruction document — these are **NOT executable code**. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback) at runtime.

## Layout

```
qcloud-[product]-ops/      # 24 skill directories (see Skills Inventory below)
  SKILL.md                 # YAML frontmatter (metadata) + Markdown runbook
  assets/
    eval_queries.json      # Intent classification test set (should_trigger true/false)
    example-config.yaml    # Optional example YAML
  references/              # Supporting docs: cli-usage, api-sdk-usage, troubleshooting, ...
```

## Skills inventory (24)

Product-scoped skills (20): `cvm`, `cdb`, `clb`, `cos`, `es`, `redis`, `monitor`, `tke`, `vpc`, `cam`, `cdn`, `cbs`, `cls`, `ckafka`, `scf`, `mongodb`, `postgres`, `ssl`, `agsx`, `finops`.

Cross-product skills (3): `qcloud-aiops-diagnosis` (multi-metric correlation), `qcloud-proactive-inspection` (5-step pipeline), `qcloud-well-architected-review` (4-pillar assessment).

Meta-skill (1): `qcloud-skill-generator` — **scaffolds/updates** other skills, not for live ops. Always check this before manually editing a `SKILL.md` if the change is structural.

Run `ls qcloud-*-ops/` for the canonical list. The `README.md` skill list is also maintained but lags behind when new skills land.

## Key conventions

- **Dual-path execution**: `tccli` CLI is primary; `tencentcloud-sdk-python` is fallback. The `cli_applicability` frontmatter field declares the policy per skill: `cli-first` / `dual-path` (most common — must ship `references/cli-usage.md` and document BOTH paths in every flow) / `cli-only` (read-only skills) / `sdk-only` (e.g. `qcloud-agsx-ops` — `tccli` does not ship an `ags` subcommand; verify via `tccli ags help`).
- **Pre-check → Execute → Verify → Recover** is the standard 4-step runbook shape. Every operation must follow it.
- **Cross-skill delegation**: CVM → VPC/CLB/COS; Monitor → CVM/CLB/VPC; CDB/ES → VPC/Monitor/COS. Check the target skill's `## Trigger & Scope` for explicit `delegate-to` markers before inventing a flow.
- **Five Core Standards** (P0 quality gates, all skills must satisfy): Clear Boundaries, Structured I/O (`{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders), Explicit Actionable Steps, Complete Failure Strategies (≥ 10 product-specific error codes with HALT vs retry), Absolute Single Responsibility.
- **No web console as agent execution path.** The console may be referenced for product docs but never for state changes.
- **UX spec** in `qcloud-skill-generator/references/user-experience-spec.md` is mandatory for all generated skills.

## Mandatory rule: 2-round self-review after every skill update

After any modification to a skill's `SKILL.md`, `references/`, or `assets/`, the agent **MUST** run **2 rounds of self-review** before declaring done. This is non-negotiable.

**Round 1 — Self-check against the template & standards** (run before claiming complete):
1. Re-read `qcloud-skill-generator/references/qcloud-skill-template.md` and `qcloud-skill-generator/SKILL.md` for the canonical shape; diff the changed skill against the template.
2. Run the **Five Core Standards** checklist (above). Each must be marked satisfied or N/A with reason.
3. Cross-check `cli_applicability` against actual CLI support. If `dual-path`, confirm every execution flow shows BOTH `tccli` and SDK steps; if `sdk-only`, confirm the absence of `references/cli-usage.md` is intentional and `cli_support_evidence` cites the verification (`tccli ags help` → "Invalid product" for agsx).
4. Verify the YAML frontmatter is valid, `version` and `last_updated` are bumped, and `related_skills` reflect the new state.
5. Confirm credentials are never printed in any output path — only `<masked>`.
6. Check that eval_queries.json coverage of new triggers is updated (add 2–4 positive + 2–4 negative cases for new functionality).

**Round 2 — Adversarial review** (mirror the meta-skill's governance doc):
1. Apply the four review categories from `qcloud-skill-generator/references/governance-and-adversarial-review.md`: **R1 Security** (credential leaks), **R2 API Fidelity** (invented methods, wrong params — must match official API doc), **R3 Safety Gates** (delete confirmations, pre-backup, rollback), **R4 UX** (Quick Start present, error format, output schema).
2. Walk through the **Adversarial Scenarios** in the same file and confirm none apply.
3. Verify cross-skill delegation works: if the new flow touches another product, confirm the `delegate-to` skill is named and the right `SKILL.md` reference is included.

**Fix-on-find** — any problem surfaced in either round must be fixed in the same change set, not deferred. The change is not "done" until both rounds report clean. Do not skip a round because the diff "looks small"; templates and reference paths drift silently.

## Prerequisites for execution

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

Requires `tccli` (pip-installable) and Python 3.8+. `qcloud-finops-ops` additionally needs `TENCENTCLOUD_FINOPS_CONFIG` pointing at `assets/example-config.yaml` in production.

## SKILL.md frontmatter — required fields

- `name` / `description` — skill identity and trigger conditions (triggers are how agents route; vague descriptions break routing).
- `compatibility` — execution environment (CLI/SDK, Python version, network).
- `cli_applicability` — `dual-path` / `cli-first` / `cli-only` / `sdk-only`. Determines whether `references/cli-usage.md` is mandatory.
- `cli_support_evidence` — cite the verification command (e.g. `tccli cvm help` showing the operations, or `tccli ags help` returning "Invalid product" for sdk-only).
- `environment` — list of required env vars.
- `metadata.version` / `metadata.last_updated` — bump on every change.

## Evaluation

`assets/eval_queries.json` per skill holds intent-classification test cases (`should_trigger: true/false`). No test runner exists in-repo; these are for external evaluation harnesses. When adding capability, add eval cases in the same change.

## Adding or modifying a skill

1. **New skill** → use `qcloud-skill-generator` (do not hand-roll). It enforces the 2-round review internally.
2. **Existing skill update** → read the meta-skill's `SKILL.md` workflow section, then apply the 2-round self-review above.
3. After `git add`, re-run round 2 once more against the staged version to catch anything the in-editor view hid.

## Files that do NOT exist

- No `package.json`, `Makefile`, CI configs, build scripts, linter, typechecker, or test runner.
- No `CLAUDE.md`, `opencode.json`, `.cursorrules` in this repo.
- `.omc/`, `.omo/`, `.codebuddy/`, `.omc/project-memory.json` are gitignored cache data — not source.
- `docs/superpowers/plans/` contains historical planning notes; safe to read but not a runtime source of truth.
