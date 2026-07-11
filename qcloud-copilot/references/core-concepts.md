# AIOps Copilot — Core Concepts

## What is AIOps Copilot?

AIOps Copilot is a natural-language orchestration layer that sits above all Tencent Cloud product skills.
Users describe operations in plain language, and Copilot converts the request into a structured
execution plan, routes sub-tasks to the correct skills, and returns a human-readable report.

## User Personas

| Type | Who | Input Style | Output Needs |
|------|-----|-------------|--------------|
| **A** | Ops engineer | Terse, semi-structured ("查 ins-abc 磁盘") | Raw data, metrics |
| **C** | Non-technical manager | Vague ("最近系统有没有问题") | Summary with findings/recommendations |

## Architecture (High-Level)

```
NL Request → Parser → Classifier → Safety L0 → Plan Generator → Safety L1
  → Engine (topological DAG executor) → Safety L2 → Report Generator → Safety L3 → Output
```

## Intent Types

| Intent | Meaning | Example |
|--------|---------|---------|
| `diagnose` | Root cause analysis | "Why is my VM slow?" |
| `inspect` | Status check | "Show me ins-abc" |
| `cruise` | Full-link inspection | "Run a health check" |
| `act` | Mutation | "Restart the VM" |
| `compare` | Trend comparison | "Compare this week vs last" |
| `report` | Summary generation | "Weekly report" |

## Safety Gates

| Gate | Location | What It Checks |
|------|----------|----------------|
| L0 | After Classifier | Skill/resource/region validity |
| L1 | After Plan Gen | Plan coherence, step budget |
| L2 | Before destructive step | User confirmation with impact assessment |
| L3 | Before final output | Report review for destructive results |

## Session Model

Copilot maintains conversational context via Memor. Follow-up questions inherit
targets, region, and customer from the previous turn unless explicitly overridden.

## Integration Principle

**Zero modifications to existing skills.** All integration is via subprocess + JSON pipe.
