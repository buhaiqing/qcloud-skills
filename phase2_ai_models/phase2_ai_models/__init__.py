# Copyright (c) 2026. All rights reserved.
"""phase2_ai_models — Phase 2 Intent-Aware AI modules (L3→L4).

Per ADR-0005. Contains:
  - adaptive_workflow: Dynamic plan revision and conditional branching
  - goal_inference: Intent-to-goal inference with multi-plan generation
  - orchestration: Cross-skill pattern selection (F1/F2/P1/A1/A2)
  - model_loader: Model loading with versioned checkpoint management

All modules integrate with qcloud-copilot via public APIs:
  - copilot.dispatcher (PlanDispatcher)
  - copilot.engine (CopilotEngine)
  - copilot.models (ExecutionPlan, PlanStep)
"""

__version__ = "0.1.0"
