---
name: qcloud-test-ops
description: >-
  M3 acceptance stub skill — zero-code routing/delegate verification.
  No hardcoded entries in qcloud-copilot/copilot/integration/skills.py.
  Validates Phase 1 Success criterion: new skills discoverable by
  SkillRegistry without code changes.
license: MIT
compatibility: >-
  No runtime dependencies (validation-only stub). SkillRegistry reads SKILL.md
  via the qcloud-*-ops/SKILL.md glob, no CLI/SDK required.
metadata:
  author: phase1-acceptance
  version: "0.1.0"
  last_updated: "2026-08-01"
  cli_applicability: cli-only
  product_name: test
  delegate_to:
    - skill: qcloud-monitor-ops
      reason: Stub delegates to monitor for M3 acceptance
      trigger: acceptance
---

# M3 Acceptance Stub

This skill exists solely to validate Phase 1 Success criterion:
"新建一个 stub skill 零代码修改即被 SkillRegistry.route() 路由".

No hardcoded entries in:
- qcloud-copilot/copilot/integration/skills.py::KNOWN_SKILLS
- SKILL_TO_PRODUCT
- OPERATION_ALIAS
- SKILL_PARAM_MAPPING

SkillRegistry should:
1. Discover this skill via `qcloud-*-ops/SKILL.md` glob
2. Validate via `reg.validate("qcloud-test-ops")` → True
3. Route via `reg.route("...test ops...")` → "qcloud-test-ops"
4. Return delegate_to = [{"skill": "qcloud-monitor-ops", ...}]
5. topological_order includes this skill
