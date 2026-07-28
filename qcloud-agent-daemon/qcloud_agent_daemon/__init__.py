"""qcloud-agent-daemon — Persistent event-driven scheduler (L3→L4).

Per ADR-0002. Zero-invasion: this package does not modify any existing
qcloud-*-ops/SKILL.md. All integration via public APIs:
  - scripts/gcl_runner.run_gcl(..., safety_confirm=...)
  - qcloud-copilot/copilot/blackboard.BlackboardClient
  - scripts/harness_safety
"""
__version__ = "0.1.0"
