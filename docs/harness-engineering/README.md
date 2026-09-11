# Harness Engineering Methodology

This directory contains the methodology distilled from building and operating
`qcloud-skills` (a 34-skill OpenSpec AI agent runbook repo). It is **medium
abstraction**: every pattern has a `qcloud-skills` example you can trace to
real files, so the pattern is not abstract in the sense of being unanchored.

## Why this exists

A Harness is the layer that turns a model's raw capability into a
**bounded, observable, evolvable engineering system**. Three properties
distinguish a Harness from a one-off agent script:

1. **Bounded** — destructive actions require human-issued confirmation
   tokens bound to a specific plan; costs and latencies have budgets.
2. **Observable** — every run emits a structured trace with provenance;
   KPI failures surface as CI errors, not vibes.
3. **Evolvable** — failures are catalogued (Reflexion), patterns are
   distilled (CADL), and the harness itself improves without manual review.

Without a Harness, an agent is a clever demo. With one, it is an asset.

## The four dimensions

| # | Dimension | Question it answers | qcloud-skills anchor |
|---|-----------|---------------------|---------------------|
| 1 | **Trust** | "Does this skill work as claimed?" | `assets/golden/` + `sandbox_e2e.py` |
| 2 | **Loop**   | "Does the GCL actually close the loop?" | `gcl_runner.py` + `evidence-kernel-schema.json` |
| 3 | **Safety** | "Are destructive ops gated by humans?" | `harness_safety.py` + `HARNESS_CONFIRM_TOKEN` |
| 4 | **Efficiency** | "Are we fast, cheap, and routing correctly?" | `harness_router.py` + `check_kpi_gates.py` |

A healthy Harness has all four green in CI. The order matters: build Trust
first (you cannot iterate on what you cannot measure), then Safety (so the
iteration does not leak), then Loop (so iteration becomes systematic), then
Efficiency (so iteration becomes affordable).

> ⚠️ **This ordering is a judgment call, not a spec.** It is the
> first-author's recommendation based on observed failure modes in
> `qcloud-skills`. A Harness where Safety matters more than Trust (e.g.
> a public-facing deployment) should reorder. The point is that all four
> must be green, not the order in which you reach them.

## Pattern library

| File | Pattern | Status |
|------|---------|--------|
| [kpi-pattern.md](./kpi-pattern.md) | 8-attribute KPI design template | ✅ Ready |
| [spec-drift-gate.md](./spec-drift-gate.md) | Detect when code drifts from spec | ✅ Ready |
| [preflight-checklist.md](./preflight-checklist.md) | Pre-merge self-review checklist | ✅ Ready |
| [agent-routing-blueprint.md](./agent-routing-blueprint.md) | Multi-agent decision contract | ⏳ Pending — needs ≥2 cross-project usage to validate |

## How to consume this directory

- **Building a new Harness?** Read the four dimension files in order. Each
  one tells you what to build, why, and what failure looks like.
- **Auditing an existing Harness?** Run the four dimensions as a checklist.
  Any "?" answer is a gap. Each gap has a fix-on-find rule: do it in the
  same change set, not as a follow-up ticket.
- **Forking `qcloud-skills`?** The patterns are template-shaped; the
  `qcloud-skills` example column tells you what the realisation looks like
  in this repo. Adapt the pattern, not the example.

## What is NOT in this directory

- **Tooling tutorials.** This is methodology, not a tccli or MCP walkthrough.
- **Per-skill runbooks.** Those live in each `qcloud-*-ops/SKILL.md`.
- **Versioned release notes.** Those live in `CHANGELOG.md`.

## License & lineage

This methodology is distilled from real PRs against `qcloud-skills`. Every
pattern carries an evidence trail back to a specific commit, file, or KPI
gate. If a pattern cannot be traced, it is a candidate for deletion; the
[self-review checklist](./preflight-checklist.md) names the discipline
that prevents phantom references from creeping in.
