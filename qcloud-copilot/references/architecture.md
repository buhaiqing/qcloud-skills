# AIOps Copilot — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (copilot/)                           │
│  ask / run / sessions / health                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CopilotEngine                                  │
│  ask(query, session_id, audience) → Report                         │
│                                                                  │
│  State machine:                                                  │
│  IDLE → PARSING → CLASSIFYING → L0 → PLANNING → L1              │
│    → EXECUTING → L2 → REPORTING → L3 → COMPLETED                │
└────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────────┘
     │      │      │      │      │      │      │
     ▼      ▼      ▼      ▼      ▼      ▼      ▼
  Parser Classifier PlanGen  L0    L1    L2    L3
  (parse) (classify) (generate)          (gate) (gate) (gate)
                 │
                 ▼
          ┌──────────────┐
          │   Engine     │
          │ _execute_plan │  ← topological DAG executor
          └──────┬───────┘
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
  skill_call   cruise_run    report
     │
     ▼
  SkillDispatcher
     │
     ├─ tccli (read-only)
     ├─ GCL Runner (destructive via thin adapter)
     └─ Product skills (subprocess)
```

## Key Modules

| Module | Responsibility |
|--------|---------------|
| `models.py` | All dataclasses: ParsedRequest, ClassifiedIntent, ExecutionPlan, StepResult, Report |
| `parser.py` | NL normalization, entity extraction, confidence scoring |
| `classifier.py` | Intent classification, skill routing, target detection |
| `plan_gen.py` | Template-based plan generation per IntentType |
| `engine.py` | Topological DAG executor, state machine |
| `report_gen.py` | Dual-template synthesis (detailed/summary) |
| `session.py` | SessionManager: context persistence via Memor |
| `safety/l0-l3.py` | Four-tier safety gate validators |
| `integration/skills.py` | SkillDispatcher: skill validation |
| `integration/gcl.py` | GCL Runner thin adapter (15-line subprocess wrapper) |
| `integration/memor.py` | Memor session persistence bridge |
| `quality/hallucination.py` | Copilot-level H layer |
| `quality/audit.py` | GCL audit trail persistence |
| `quality/health.py` | Skill health metrics bridge |
| `quality/reflexion.py` | Reflexion write-back bridge |

## Data Flow

1. **Parse**: raw NL → `ParsedRequest` with entities + confidence
2. **Classify**: `ParsedRequest` → `ClassifiedIntent` with primary/secondary intent + targets
3. **Plan**: `ClassifiedIntent` → `ExecutionPlan` (DAG of `PlanStep`)
4. **Safety L0/L1**: Validate before execution
5. **Execute**: Topological sort, parallel for independent steps
6. **Safety L2**: Destructive confirmation gate
7. **Report**: `ExecutionResult` → `Report` (detailed or summary)
8. **Safety L3**: Critical findings review gate

## Session Model

SessionManager persists to `~/.omo/memor/copilot/sessions/<session_id>.json`.
Follow-up queries inherit targets, region, customer from prior turns.
