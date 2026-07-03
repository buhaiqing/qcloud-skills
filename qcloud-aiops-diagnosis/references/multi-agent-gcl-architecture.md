# GCL with Multiple Sub-Agents Architecture for AIOps

> **Generator-Critic-Loop (GCL) with Multiple Sub-Agents architecture for AIOps modules.** Uses a main GCL orchestrator that spawns multiple specialized sub-agents for parallel validation of predictions, knowledge graphs, and other AIOps outputs.

## 1. Architecture Overview

### 1.1 Multi-Agent GCL Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                   Main Agent (Orchestrator)                  │
│  - Coordinates all sub-agents                               │
│  - Aggregates results and makes final decision              │
│  - Controls iteration count (max 3)                         │
│  - Persists trace for audit                                 │
└──────────┬──────────────────────────────────────┬──────────┘
           │ spawn Generator Agent                │ spawn Critic Agents
           ▼                                      ▼
┌──────────────────────┐           ┌──────────────────────────┐
│  Generator Agent     │           │    Critic Agents (N)     │
│  - Generates output  │ ──notify─►│                          │
│  - Uses domain logic │  ◄─feedback│  Agent 1: Validation 1   │
│  - Captures trace    │           │  Agent 2: Validation 2   │
└──────────────────────┘           │  Agent N: Validation N   │
                                   └──────────────────────────┘
```

### 1.2 Core Principles

1. **Isolation**: Generator and Critic agents run in isolated contexts
2. **Parallelism**: Multiple Critic agents run simultaneously
3. **Specialization**: Each agent focuses on specific validation aspect
4. **Aggregation**: Main agent aggregates results with weighted scoring
5. **Traceability**: Complete audit trail of all agent interactions

## 2. Agent Types and Roles

### 2.1 Generator Agent

**Role**: Produce the primary output (predictions, knowledge graph, etc.)

**Responsibilities**:
- Execute domain-specific logic
- Use external APIs and data sources
- Capture execution trace
- Return structured JSON output

**Characteristics**:
- Single Generator per GCL cycle
- Has access to external tools (APIs, data sources)
- Produces the output that Critic agents evaluate

### 2.2 Critic Agents

**Role**: Validate specific aspects of Generator output

**Types**:
1. **Data Quality Agent**: Validates input data quality
2. **Model Accuracy Agent**: Validates algorithm accuracy
3. **Safety Rules Agent**: Enforces domain-specific safety rules
4. **Schema Quality Agent**: Validates schema design (for knowledge graphs)
5. **Graph Consistency Agent**: Validates graph consistency (for knowledge graphs)

**Characteristics**:
- Multiple Critic agents per GCL cycle
- Run in parallel for efficiency
- Each agent focuses on specific validation aspect
- Produces scores and specific issues

### 2.3 Main Agent (Orchestrator)

**Role**: Coordinate the GCL cycle and make final decision

**Responsibilities**:
- Spawn Generator and Critic agents
- Aggregate Critic results
- Apply decision logic
- Persist trace for audit
- Control iteration count

**Decision Logic**:
```
1. Safety=0 OR blocking issues → ABORT
2. current_iter >= max_iterations → MAX_ITER (best-so-far)
3. All dimension thresholds met → PASS
4. Else → RETRY (inject feedback into next Generator run)
```

## 3. Multi-Agent GCL Workflow

### 3.1 Standard Workflow

```
Phase 1: Initialization
  - Main Agent receives user request
  - Main Agent spawns Generator Agent
  - Main Agent spawns N Critic Agents

Phase 2: Generation
  - Generator Agent executes domain logic
  - Generator Agent captures trace
  - Generator Agent returns output JSON

Phase 3: Validation (Parallel)
  - Critic Agent 1 validates aspect 1
  - Critic Agent 2 validates aspect 2
  - Critic Agent N validates aspect N
  - All Critic agents run simultaneously

Phase 4: Aggregation
  - Main Agent collects all Critic results
  - Main Agent calculates weighted scores
  - Main Agent identifies blocking issues

Phase 5: Decision
  - Main Agent applies decision logic
  - If PASS: Output final result
  - If ABORT: Output error report
  - If RETRY: Inject feedback and repeat from Phase 2

Phase 6: Persistence
  - Main Agent persists trace to audit-results/
  - Main Agent updates knowledge base (if applicable)
```

### 3.2 Configuration Example

```yaml
gcl_config:
  max_iterations: 3
  agents:
    generator:
      type: "prediction_generator"  # or "knowledge_graph_generator"
      model: "default"
      timeout: 300
    critics:
      - type: "data_quality"
        model: "reasoning"
        timeout: 60
        weight: 0.3
        threshold: 0.7
      - type: "model_accuracy"
        model: "reasoning"
        timeout: 60
        weight: 0.4
        threshold: 0.6
      - type: "safety_rules"
        model: "default"
        timeout: 30
        weight: 0.3
        threshold: 1.0
  scoring:
    method: "weighted_average"
    aggregation: "parallel"
```

## 4. Scoring and Decision Making

### 4.1 Scoring Formula

**Overall Score** = Σ (Critic_i_score × Weight_i)

Where:
- `Critic_i_score` = Score from Critic Agent i (0-1)
- `Weight_i` = Weight for Critic Agent i (sum to 1.0)

### 4.2 Thresholds

| Dimension | Typical Weight | Typical Threshold | Notes |
|---|---|---|---|
| Data Quality | 0.3 | ≥ 0.7 | Input data validation |
| Model Accuracy | 0.4 | ≥ 0.6 | Algorithm accuracy |
| Safety Compliance | 0.3 | = 1.0 | Strict safety rules |
| Schema Quality | 0.4 | ≥ 0.8 | Knowledge graph schemas |
| Graph Consistency | 0.4 | ≥ 0.9 | Graph integrity |

### 4.3 Decision Matrix

| Condition | Action | Description |
|---|---|---|
| Safety=0 | ABORT | Critical safety violation |
| Blocking issues | ABORT | Must-fix problems found |
| All thresholds met | PASS | Output is acceptable |
| Below thresholds | RETRY | Inject feedback, try again |
| Max iterations reached | MAX_ITER | Return best-so-far |

## 5. Implementation Examples

### 5.1 Prediction Engine Multi-Agent GCL

**Generator Agent**:
- Fetches historical monitoring data
- Applies prediction algorithms
- Generates capacity alerts and trend forecasts
- Returns prediction JSON

**Critic Agent 1 (Data Quality)**:
- Validates data completeness (>80% non-null)
- Checks data freshness (within 24 hours)
- Detects outliers in historical data
- Returns data quality score

**Critic Agent 2 (Model Accuracy)**:
- Calculates R², MAE, MAPE metrics
- Validates confidence intervals
- Checks prediction horizons (≤90 days)
- Returns model accuracy score

**Critic Agent 3 (Safety Rules)**:
- Verifies real historical data used
- Ensures confidence intervals provided
- Validates prediction horizons
- Checks accuracy assessments included
- Returns safety compliance score (0 or 1)

### 5.2 Knowledge Graph Multi-Agent GCL

**Generator Agent**:
- Creates entity schemas (Fault, Symptom, Root Cause, etc.)
- Defines relationship schemas
- Validates against API documentation
- Returns knowledge graph schema JSON

**Critic Agent 1 (Schema Quality)**:
- Checks entity completeness
- Validates relationship cardinality
- Verifies naming conventions
- Returns schema quality score

**Critic Agent 2 (Graph Consistency)**:
- Validates referential integrity
- Checks for cycles
- Verifies acyclic relationships
- Returns graph consistency score

**Critic Agent 3 (Safety Rules)**:
- Verifies no sensitive data in schema
- Validates no privilege escalation relationships
- Checks for hardcoded IPs/hostnames
- Returns safety compliance score (0 or 1)

## 6. Trace and Audit

### 6.1 Trace Structure

```json
{
  "gcl_run_id": "gcl-20260704-123456",
  "skill": "qcloud-aiops-diagnosis",
  "module": "prediction-engine",
  "timestamp": "2026-07-04T12:34:56+08:00",
  "iterations": [
    {
      "iteration": 1,
      "generator_output": { ... },
      "critic_results": [
        {"agent": "data_quality", "score": 0.95, "issues": []},
        {"agent": "model_accuracy", "score": 0.90, "issues": []},
        {"agent": "safety_rules", "score": 1.0, "issues": []}
      ],
      "overall_score": 0.945,
      "decision": "PASS"
    }
  ],
  "final_decision": "PASS",
  "final_output": { ... }
}
```

### 6.2 Audit Requirements

1. **Complete trace**: All agent interactions logged
2. **Masked credentials**: No sensitive data in trace
3. **Decision rationale**: Clear explanation of PASS/ABORT
4. **Iteration history**: All retry attempts documented
5. **Persistent storage**: Trace saved to `audit-results/`

## 7. Integration with Existing GCL

### 7.1 Compatibility with Single-Agent GCL

Multi-Agent GCL is **backward compatible** with existing single-agent GCL:
- Same rubric dimensions (correctness, safety, idempotency, traceability, spec_compliance)
- Same trace format
- Same decision logic
- Enhanced with parallel validation and specialized agents

### 7.2 Migration Path

1. **Phase 1**: Implement multi-agent GCL for new modules (prediction, knowledge graph)
2. **Phase 2**: Migrate existing modules to multi-agent GCL
3. **Phase 3**: Deprecate single-agent GCL for complex modules

### 7.3 Shared Infrastructure

- **GCL Runner**: `scripts/gcl_runner.py` supports both single and multi-agent modes
- **Trace Aggregation**: `scripts/gcl_trace_aggregate.py` handles multi-agent traces
- **Rubric System**: Existing rubrics work with multi-agent scoring
- **Prompt Templates**: Extended with agent-specific templates

## 8. Performance Considerations

### 8.1 Parallel Execution Benefits

- **Reduced latency**: Multiple validators run simultaneously
- **Better coverage**: More aspects validated in same time
- **Scalability**: Add new validators without increasing latency

### 8.2 Resource Management

- **Agent pooling**: Reuse agents across GCL cycles
- **Timeout handling**: Prevent hanging agents
- **Error isolation**: One agent failure doesn't affect others

### 8.3 Optimization Strategies

- **Lazy spawning**: Only spawn agents when needed
- **Result caching**: Cache validation results for repeated patterns
- **Adaptive thresholds**: Adjust thresholds based on historical performance

## 9. Example Configurations

### 9.1 Prediction Engine Configuration

```yaml
prediction_gcl:
  max_iterations: 3
  agents:
    generator:
      type: "prediction_generator"
      model: "default"
      timeout: 300
    critics:
      - type: "data_quality"
        model: "reasoning"
        timeout: 60
        weight: 0.3
        threshold: 0.7
      - type: "model_accuracy"
        model: "reasoning"
        timeout: 60
        weight: 0.4
        threshold: 0.6
      - type: "safety_rules"
        model: "default"
        timeout: 30
        weight: 0.3
        threshold: 1.0
```

### 9.2 Knowledge Graph Configuration

```yaml
knowledge_graph_gcl:
  max_iterations: 3
  agents:
    generator:
      type: "knowledge_graph_generator"
      model: "default"
      timeout: 300
    critics:
      - type: "schema_quality"
        model: "reasoning"
        timeout: 60
        weight: 0.4
        threshold: 0.8
      - type: "graph_consistency"
        model: "reasoning"
        timeout: 60
        weight: 0.4
        threshold: 0.9
      - type: "safety_rules"
        model: "default"
        timeout: 30
        weight: 0.2
        threshold: 1.0
```

## 10. Benefits of Multi-Agent GCL

1. **Robustness**: Multiple validation aspects reduce false positives
2. **Efficiency**: Parallel execution reduces total validation time
3. **Specialization**: Each agent focuses on specific expertise
4. **Transparency**: Clear accountability for each validation aspect
5. **Scalability**: Easy to add new validation agents
6. **Maintainability**: Easier to update individual agents
7. **Auditability**: Complete trace of all validation decisions

## 11. Future Enhancements

1. **Dynamic agent spawning**: Spawn agents based on output characteristics
2. **Adaptive weighting**: Adjust weights based on historical performance
3. **Machine learning agents**: Use ML models for validation
4. **Cross-module validation**: Agents validate across multiple modules
5. **Real-time monitoring**: Monitor agent performance in production

---

## Quality Gate (GCL)

This architecture participates in the **Generator-Critic-Loop (GCL)** at the **generation-time**
layer. The loop audits the **architecture design** (agent roles, workflow, scoring),
not cloud resources.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override |
| Rubric instance | [`references/rubric.md`](rubric.md) | 5 dimensions + architecture-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Why this architecture is `optional` (not `required`)

The GCL architecture **does not mutate cloud resources**. Its output is an
architecture design document checked into git. Safety is enforced by the **build-time**
2-round self-review (already mandatory above) and by the **Charter C7 enforcement**
that requires generated skills to ship with their own Tier A rubric.md +
prompt-templates.md + Quality Gate chapter. The GCL loop on this architecture is
therefore a **double-check**: it verifies that the architecture was designed
correctly.

### Architecture-specific safety rules (rubric §4)

1. **Rule ARCH1**: Generator and Critic agents MUST run in isolated contexts
2. **Rule ARCH2**: Critic agents MUST NOT see the original user request
3. **Rule ARCH3**: All agent interactions MUST be traced and auditable
4. **Rule ARCH4**: Safety=0 MUST trigger immediate ABORT (no partial results)
5. **Rule ARCH5**: Max iterations MUST be bounded (no infinite loops)

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Model selection requirements

| Agent Type | Model Requirement | Vendor Requirement | Reason |
|---|---|---|---|
| **Generator** | Medium model (economical) | Vendor A | Coding tasks consume many tokens; use economical model |
| **Critic** | Stronger model (flagship) | Vendor B (different) | Review requires stronger reasoning; heterogeneous models avoid bias |

- **MUST** use models from different vendors (e.g., Generator: Claude Sonnet, Critic: Gemini Pro)
- **MUST** ensure Critic model capability ≥ Generator model capability

### Worked example — designing a prediction GCL architecture

| Dimension | Score |
|---|---|
| Correctness | 1 (agent roles properly defined) |
| **Safety** | **1** (all 5 rules satisfied) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 0.5 (missing model vendor specification) |

`decision: RETRY`. Recovery suggestion: "Add explicit model vendor requirements in §2 Agent Types."

See [`references/rubric.md`](rubric.md) §6 for two more examples.

---

## Reference

- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
- [gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md)
- [prediction-engine.md](prediction-engine.md)
- [knowledge-graph-schema.md](knowledge-graph-schema.md)