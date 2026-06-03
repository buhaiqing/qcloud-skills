# Proactive Inspection Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-proactive-inspection`.
> **Advisory** — `max_iter=3`. Idempotency is the main risk.

---

## 4. Proactive Inspection-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Inspection run (any, especially repeated) | **Check if an inspection was already run for the same scope/time-range within the last hour; if so, warn the user and ask if they want a fresh run (force=yes) or to reuse the previous results; track inspection ID for idempotency** | Running the same inspection twice within minutes produces redundant reports. The most common pattern: "I ran the inspection, then ran it again because I was not sure it completed — but the second run generated duplicate reports and confused the team" |
| 2 | Cross-skill data collection | **All product skill calls during inspection must be read-only; confirm read-only delegation in trace; do NOT trigger any alarm or notification during collection** | Inspection reads must not cause side effects. The most common pattern: "The inspection queried the alarm policies to check coverage, and the API call generated a false-positive alarm" |
| 3 | Credential safety in report | **Inspection report output must NOT contain raw credentials, API keys, or secret content; mask with `<masked>`; check report content before writing to output** | Inspection reports may capture environment variable dumps or API responses that contain secrets |
| 4 | Real-time vs snapshot clarity | **Surface the inspection time range; warn that the results are a snapshot in time and may not reflect current state; for resources that change frequently (e.g., auto-scaling groups), add "state as of <timestamp>"** | The most common misinterpretation: "The inspection said my CVM was running — but it was terminated 5 minutes after the inspection" |
| 5 | Report file path security | **When writing the inspection report to disk, check that the output path is not world-readable (umask check); do NOT upload the report to a public URL unless explicitly confirmed** | Inspection reports contain infrastructure details that should not be publicly accessible |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Proactive Inspection rollout: rubric (5 rules: run idempotency, read-only collection, credential safety, snapshot timing, report path security) |