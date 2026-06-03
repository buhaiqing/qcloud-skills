# Well-Architected Review Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-well-architected-review`.
> **Advisory / read-only** — `max_iter=5`, no Safety=0 ABORT.

---

## 4. Well-Architected Review-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Assessment scope clarity | **Surface the assessment scope explicitly (which products, which pillars); warn if any pillar is skipped due to data unavailability; do NOT evaluate skipped pillars as "N/A" — mark as "NOT ASSESSED"** | The most common confusion: "The assessment gave the architecture a score of 85 but excluded the Security pillar because the CAM data was unavailable — the user thought the architecture was secure" |
| 2 | Read-only cross-skill data | **All data collection must use read-only APIs; confirm read-only delegation; do NOT modify any alarm policies or security groups during the review** | Assessment must be non-invasive. The most common pattern: "The assessment modified the backup policy to test if it works" |
| 3 | No false certainty | **For each finding, surface confidence (HIGH / MEDIUM / LOW); if any data source is incomplete or unavailable, add a caveat "finding based on partial data"; do NOT present automated assessment as a professional audit** | Automated assessments are inherently limited. The most common misinterpretation: "The automated assessment said the architecture is 'Well-Architected' but the manual review found 10 critical security gaps" |
| 4 | Cross-pillar consistency | **When evaluating across pillars (Reliability + Security + Cost + Efficiency), surface any conflicting recommendations; e.g., "recommending multi-AZ (Reliability) increases cost (Cost)"; flag these trade-offs** | Pillar recommendations can conflict. The most common pattern: "The assessment recommended multi-AZ deployment for reliability, but the Cost pillar flagged it as expensive — the user didn't know which to prioritize" |
| 5 | Delegation matrix respect | **Before collecting data from a delegated skill, confirm the skill is in the Delegation Matrix; do NOT collect data from skills not listed; for missing skills, recommend the user run the assessment again after the skill is added** | The delegation matrix defines the assessment boundary. Going outside it produces misleading results. The most common pattern: "The assessment read data from a product skill that wasn't in the matrix and the data was incomplete, making the score too low" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Well-Architected Review rollout: rubric (5 rules: scope clarity, read-only collection, confidence disclosure, cross-pillar consistency, delegation matrix respect) |