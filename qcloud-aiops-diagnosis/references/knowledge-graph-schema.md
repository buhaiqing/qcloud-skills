# Knowledge Graph Schema for Fault Diagnosis

> **Structured knowledge representation for fault patterns, root causes, and solutions.** Enables intelligent fault diagnosis through graph-based reasoning and pattern matching.
>
> **GCL Integration:** This module participates in the Generator-Critic-Loop (GCL) at the **generation-time** layer. The loop audits the **knowledge graph schema** (entity definitions, relationship models), not cloud resources. See `## Quality Gate (GCL)` section for details.

## 1. Knowledge Graph Overview

### 1.1 Purpose

The knowledge graph provides:
- **Structured fault patterns**: Symptoms, causes, and solutions
- **Relationship modeling**: Fault propagation paths and dependencies
- **Intelligent reasoning**: Graph-based root cause analysis
- **Knowledge reuse**: Learning from historical incidents

### 1.2 Core Entities

| Entity Type | Description | Example |
|---|---|---|
| **Fault** | A specific failure scenario | "CVM instance unreachable" |
| **Symptom** | Observable indicators of a fault | "High latency", "Connection timeout" |
| **Root Cause** | Underlying reason for the fault | "Network ACL misconfiguration" |
| **Solution** | Action to resolve the fault | "Update network ACL rules" |
| **Resource** | Affected system component | "CVM instance ins-xxx" |
| **Metric** | Measurable attribute | "CPU usage", "Memory usage" |
| **Event** | Occurrence that triggers faults | "Deployment", "Configuration change" |

### 1.3 Relationship Types

| Relationship | From → To | Description |
|---|---|---|
| **HAS_SYMPTOM** | Fault → Symptom | Fault manifests as symptom |
| **CAUSED_BY** | Fault → Root Cause | Fault is caused by root cause |
| **SOLVED_BY** | Fault → Solution | Fault is solved by solution |
| **AFFECTS** | Fault → Resource | Fault affects resource |
| **TRIGGERS** | Event → Fault | Event triggers fault |
| **DEPENDS_ON** | Resource → Resource | Resource depends on another |
| **MEASURED_BY** | Resource → Metric | Resource is measured by metric |
| **INDICATES** | Symptom → Root Cause | Symptom indicates root cause |
| **REQUIRES** | Solution → Resource | Solution requires resource |
| **PRECEDES** | Fault → Fault | One fault leads to another |

## 2. Entity Schemas

### 2.1 Fault Entity

```json
{
  "id": "fault-001",
  "type": "Fault",
  "name": "CVM Instance Unreachable",
  "description": "Cannot SSH into CVM instance",
  "severity": "HIGH",
  "category": "connectivity",
  "product": "cvm",
  "resource_types": ["cvm_instance"],
  "symptoms": ["symptom-001", "symptom-002"],
  "root_causes": ["cause-001", "cause-002"],
  "solutions": ["solution-001", "solution-002"],
  "metrics": ["metric-001", "metric-002"],
  "detection_rules": ["rule-001"],
  "confidence": 0.95,
  "last_updated": "2026-07-04T10:00:00+08:00",
  "version": "2.1.0"
}
```

### 2.2 Symptom Entity

```json
{
  "id": "symptom-001",
  "type": "Symptom",
  "name": "High Latency",
  "description": "Response time > 1000ms",
  "metric": "metric-001",
  "threshold": 1000,
  "unit": "ms",
  "severity": "MEDIUM",
  "category": "performance",
  "detection_method": "static_threshold",
  "confidence": 0.9,
  "false_positive_rate": 0.05
}
```

### 2.3 Root Cause Entity

```json
{
  "id": "cause-001",
  "type": "RootCause",
  "name": "Network ACL Misconfiguration",
  "description": "Network ACL blocks SSH port 22",
  "category": "configuration",
  "product": "vpc",
  "resource_types": ["network_acl"],
  "evidence_required": ["evidence-001"],
  "verification_steps": ["step-001", "step-002"],
  "confidence": 0.85,
  "complexity": "medium",
  "estimated_fix_time": "30m"
}
```

### 2.4 Solution Entity

```json
{
  "id": "solution-001",
  "type": "Solution",
  "name": "Update Network ACL Rules",
  "description": "Add SSH port 22 to network ACL inbound rules",
  "category": "configuration",
  "product": "vpc",
  "steps": [
    "1. Identify current network ACL rules",
    "2. Add inbound rule for port 22",
    "3. Apply changes to affected subnets",
    "4. Verify SSH connectivity"
  ],
  "prerequisites": ["prerequisite-001"],
  "risks": ["risk-001"],
  "estimated_time": "15m",
  "automation_level": "semi-automatic",
  "success_rate": 0.92
}
```

### 2.5 Resource Entity

```json
{
  "id": "resource-001",
  "type": "Resource",
  "name": "CVM Instance",
  "product": "cvm",
  "resource_type": "instance",
  "attributes": {
    "instance_id": "ins-xxx",
    "instance_type": "S5.SMALL1",
    "status": "RUNNING",
    "zone": "ap-guangzhou-3"
  },
  "metrics": ["metric-001", "metric-002"],
  "dependencies": ["resource-002", "resource-003"],
  "health_status": "healthy"
}
```

### 2.6 Metric Entity

```json
{
  "id": "metric-001",
  "type": "Metric",
  "name": "CPU Usage",
  "namespace": "QCE/CVM",
  "metric_name": "CpuUsage",
  "unit": "%",
  "thresholds": {
    "warning": 70,
    "critical": 90
  },
  "collection_interval": 60,
  "retention_days": 30
}
```

## 3. Relationship Schemas

### 3.1 Fault-Symptom Relationship

```json
{
  "id": "rel-001",
  "type": "HAS_SYMPTOM",
  "source": "fault-001",
  "target": "symptom-001",
  "strength": 0.8,
  "confidence": 0.9,
  "temporal_pattern": "concurrent",
  "description": "High latency often accompanies instance unreachability"
}
```

### 3.2 Fault-Root Cause Relationship

```json
{
  "id": "rel-002",
  "type": "CAUSED_BY",
  "source": "fault-001",
  "target": "cause-001",
  "strength": 0.85,
  "confidence": 0.85,
  "probability": 0.7,
  "description": "Network ACL misconfiguration is a common cause of instance unreachability"
}
```

### 3.3 Fault-Solution Relationship

```json
{
  "id": "rel-003",
  "type": "SOLVED_BY",
  "source": "fault-001",
  "target": "solution-001",
  "strength": 0.9,
  "confidence": 0.92,
  "effectiveness": 0.88,
  "description": "Updating network ACL rules resolves most connectivity issues"
}
```

### 3.4 Resource Dependency Relationship

```json
{
  "id": "rel-004",
  "type": "DEPENDS_ON",
  "source": "resource-001",
  "target": "resource-002",
  "dependency_type": "network",
  "criticality": "high",
  "description": "CVM instance depends on VPC for network connectivity"
}
```

## 4. Graph Query Patterns

### 4.1 Find Root Causes for Fault

```cypher
MATCH (f:Fault {name: $fault_name})-[:CAUSED_BY]->(rc:RootCause)
RETURN rc.name, rc.description, rc.confidence
ORDER BY rc.confidence DESC
```

### 4.2 Find Solutions for Fault

```cypher
MATCH (f:Fault {name: $fault_name})-[:SOLVED_BY]->(s:Solution)
RETURN s.name, s.steps, s.estimated_time, s.success_rate
ORDER BY s.success_rate DESC
```

### 4.3 Find Fault Propagation Path

```cypher
MATCH path = (f1:Fault)-[:PRECEDES*]->(f2:Fault)
WHERE f1.name = $initial_fault
RETURN path, length(path) as path_length
ORDER BY path_length ASC
```

### 4.4 Find Related Faults

```cypher
MATCH (f:Fault {name: $fault_name})-[:HAS_SYMPTOM]->(s:Symptom)<-[:HAS_SYMPTOM]-(related:Fault)
WHERE related.name <> $fault_name
RETURN related.name, related.severity, count(s) as common_symptoms
ORDER BY common_symptoms DESC
```

### 4.5 Find Affected Resources

```cypher
MATCH (f:Fault {name: $fault_name})-[:AFFECTS]->(r:Resource)
RETURN r.name, r.product, r.health_status
```

## 5. Knowledge Graph Construction

### 5.1 Data Sources

| Source | Data Type | Update Frequency |
|---|---|---|
| **Historical Incidents** | Fault patterns, root causes | Daily |
| **API Documentation** | Resource relationships, metrics | Weekly |
| **Monitoring Data** | Metric thresholds, baselines | Real-time |
| **User Feedback** | Solution effectiveness | Weekly |
| **Expert Knowledge** | Domain expertise | Monthly |

### 5.2 Construction Pipeline

```
1. Extract entities from historical incidents
2. Extract relationships from incident reports
3. Validate entities against API documentation
4. Enrich with monitoring data
5. Score confidence based on evidence
6. Build graph structure
7. Validate graph consistency
8. Deploy to production
```

### 5.3 Quality Metrics

| Metric | Description | Target |
|---|---|---|
| **Entity Coverage** | % of known faults in graph | > 80% |
| **Relationship Accuracy** | % of correct relationships | > 90% |
| **Confidence Calibration** | Predicted vs actual confidence | ±5% |
| **Freshness** | Days since last update | < 7 days |
| **Completeness** | % of faults with solutions | > 70% |

## 6. Graph Reasoning Algorithms

### 6.1 Fault Propagation Analysis

```python
def analyze_fault_propagation(fault_id: str, depth: int = 3) -> list:
    """Analyze how a fault propagates through the system."""
    # BFS to find propagation path
    queue = [(fault_id, 0)]
    visited = set()
    propagation_path = []
    
    while queue:
        current_fault, current_depth = queue.pop(0)
        if current_depth > depth or current_fault in visited:
            continue
        
        visited.add(current_fault)
        propagation_path.append({
            "fault": current_fault,
            "depth": current_depth,
            "next_faults": get_following_faults(current_fault)
        })
        
        for next_fault in get_following_faults(current_fault):
            queue.append((next_fault, current_depth + 1))
    
    return propagation_path
```

### 6.2 Root Cause Ranking

```python
def rank_root_causes(fault_id: str) -> list:
    """Rank root causes by probability and confidence."""
    root_causes = get_root_causes(fault_id)
    
    ranked_causes = []
    for cause in root_causes:
        score = calculate_cause_score(cause)
        ranked_causes.append({
            "cause": cause,
            "score": score,
            "probability": cause.probability,
            "confidence": cause.confidence,
            "evidence_count": len(get_evidence_for_cause(cause.id))
        })
    
    return sorted(ranked_causes, key=lambda x: x["score"], reverse=True)
```

### 6.3 Solution Recommendation

```python
def recommend_solutions(fault_id: str, context: dict) -> list:
    """Recommend solutions based on fault and context."""
    solutions = get_solutions_for_fault(fault_id)
    
    recommended = []
    for solution in solutions:
        relevance = calculate_solution_relevance(solution, context)
        feasibility = check_solution_feasibility(solution, context)
        
        if relevance > 0.7 and feasibility > 0.8:
            recommended.append({
                "solution": solution,
                "relevance": relevance,
                "feasibility": feasibility,
                "estimated_time": solution.estimated_time,
                "success_rate": solution.success_rate
            })
    
    return sorted(recommended, key=lambda x: x["relevance"] * x["feasibility"], reverse=True)
```

## 7. Integration with Existing Skills

### 7.1 Anomaly Detection Integration

```python
def enhance_anomaly_with_knowledge(anomaly: dict) -> dict:
    """Enhance anomaly detection with knowledge graph insights."""
    # Find related faults
    related_faults = find_faults_by_symptoms(anomaly["symptoms"])
    
    # Find possible root causes
    possible_causes = []
    for fault in related_faults:
        causes = get_root_causes_for_fault(fault["id"])
        possible_causes.extend(causes)
    
    # Rank root causes
    ranked_causes = rank_root_causes_by_evidence(possible_causes, anomaly)
    
    anomaly["knowledge_graph"] = {
        "related_faults": related_faults,
        "possible_causes": ranked_causes[:3],  # Top 3 causes
        "confidence_boost": calculate_confidence_boost(ranked_causes)
    }
    
    return anomaly
```

### 7.2 Capacity Prediction Integration

```python
def enhance_prediction_with_knowledge(prediction: dict) -> dict:
    """Enhance capacity prediction with knowledge graph insights."""
    # Find related faults for predicted resource exhaustion
    if prediction["alert_type"] == "disk_exhaustion":
        related_faults = find_faults_by_resource_type("disk")
        
        # Find historical solutions
        solutions = []
        for fault in related_faults:
            fault_solutions = get_solutions_for_fault(fault["id"])
            solutions.extend(fault_solutions)
        
        prediction["knowledge_graph"] = {
            "related_faults": related_faults,
            "historical_solutions": solutions,
            "prevention_strategies": extract_prevention_strategies(solutions)
        }
    
    return prediction
```

## 8. Knowledge Graph Maintenance

### 8.1 Update Triggers

| Trigger | Action | Frequency |
|---|---|---|
| **New Incident** | Extract fault patterns | Daily |
| **API Change** | Update resource relationships | Weekly |
| **Solution Update** | Refresh solution effectiveness | Weekly |
| **Expert Review** | Validate and refine knowledge | Monthly |
| **Performance Review** | Optimize graph structure | Quarterly |

### 8.2 Versioning

```json
{
  "version": "2.1.0",
  "last_updated": "2026-07-04T10:00:00+08:00",
  "changes": [
    "Added 5 new fault patterns",
    "Updated 3 root cause relationships",
    "Improved solution success rates"
  ],
  "statistics": {
    "total_faults": 150,
    "total_symptoms": 300,
    "total_root_causes": 200,
    "total_solutions": 180,
    "total_relationships": 850
  }
}
```

### 8.3 Quality Assurance

1. **Automated validation**: Check graph consistency daily
2. **Expert review**: Monthly review by domain experts
3. **Performance testing**: Validate reasoning algorithms weekly
4. **User feedback**: Collect and incorporate user feedback weekly

## 9. Example Knowledge Graph

### 9.1 CVM Instance Unreachable Fault

```
Fault: CVM Instance Unreachable
  ├── HAS_SYMPTOM → High Latency
  ├── HAS_SYMPTOM → Connection Timeout
  ├── CAUSED_BY → Network ACL Misconfiguration
  ├── CAUSED_BY → Security Group Rules
  ├── CAUSED_BY → Instance Status Check Failed
  ├── SOLVED_BY → Update Network ACL Rules
  ├── SOLVED_BY → Modify Security Group
  ├── SOLVED_BY → Restart Instance
  ├── AFFECTS → CVM Instance ins-xxx
  ├── AFFECTS → VPC vpc-xxx
  └── TRIGGERS → Deployment Event
```

### 9.2 Disk Exhaustion Fault

```
Fault: Disk Exhaustion
  ├── HAS_SYMPTOM → High Disk Usage
  ├── HAS_SYMPTOM → Write Latency Increase
  ├── CAUSED_BY → Log Accumulation
  ├── CAUSED_BY → Large Data Files
  ├── CAUSED_BY → Inadequate Disk Size
  ├── SOLVED_BY → Clean Up Logs
  ├── SOLVED_BY → Archive Old Data
  ├── SOLVED_BY → Expand Disk
  ├── AFFECTS → CBS Disk vol-xxx
  └── PRECEDES → Instance Crash
```

## 10. Limitations and Future Work

### 10.1 Current Limitations

1. **Manual curation**: Knowledge graph requires expert maintenance
2. **Static relationships**: Relationships don't adapt to changing environments
3. **Limited reasoning**: Current algorithms are rule-based, not ML-based
4. **Data quality**: Depends on quality of historical incident data

### 10.2 Future Enhancements

1. **ML-based reasoning**: Use graph neural networks for better reasoning
2. **Dynamic relationships**: Adapt relationships based on real-time data
3. **Automated extraction**: Extract knowledge from logs and metrics automatically
4. **Cross-product reasoning**: Reason across multiple products and services
5. **Interactive visualization**: Provide graph visualization tools

---

## Quality Gate (GCL) — Multiple Sub-Agents Architecture

This module implements **GCL with Multiple Sub-Agents** for knowledge graph schema validation. The architecture uses a main GCL orchestrator that spawns multiple specialized sub-agents for parallel validation.

### GCL with Multiple Sub-Agents Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   GCL Orchestrator (Main Agent)              │
│  - Coordinates Generator and multiple Critic sub-agents     │
│  - Aggregates results from all sub-agents                   │
│  - Makes final PASS/RETRY/ABORT decision                    │
│  - Controls iteration count (max 3)                         │
└──────────┬──────────────────────────────────────┬──────────┘
           │ spawn Generator Sub-Agent            │ spawn Multiple Critic Sub-Agents
           ▼                                      ▼
┌──────────────────────┐           ┌──────────────────────────┐
│  Generator Sub-Agent │           │  Critic Sub-Agents (3)   │
│  - Generates         │ ──notify─►│                          │
│    knowledge graph   │  ◄─feedback│  Sub-Agent 1: Schema Quality│
│  - Validates         │           │  Sub-Agent 2: Graph Consistency│
│    relationships     │           │  Sub-Agent 3: Safety Rules│
└──────────────────────┘           └──────────────────────────┘
```

### Sub-Agent Roles and Responsibilities

#### 1. Generator Sub-Agent
- **Role**: Generate knowledge graph schema
- **Responsibilities**:
  - Define entity schemas (Fault, Symptom, Root Cause, Solution, Resource, Metric, Event)
  - Define relationship schemas (HAS_SYMPTOM, CAUSED_BY, SOLVED_BY, etc.)
  - Validate schema against API documentation
  - Generate example instances
- **Output**: Knowledge graph schema JSON with validation results

#### 2. Critic Sub-Agent 1: Schema Quality
- **Role**: Validate schema design quality
- **Responsibilities**:
  - Check entity completeness (all required fields present)
  - Validate relationship cardinality (1:1, 1:N, N:M)
  - Verify naming conventions (consistent, descriptive)
  - Check for redundant or missing entities
- **Output**: Schema quality score (0-1) with specific issues

#### 3. Critic Sub-Agent 2: Graph Consistency
- **Role**: Validate graph consistency
- **Responsibilities**:
  - Check referential integrity (all relationships point to existing entities)
  - Validate cycle detection (no circular dependencies)
  - Verify acyclic relationships where required
  - Check for orphan entities (no relationships)
- **Output**: Graph consistency score (0-1) with specific issues

#### 4. Critic Sub-Agent 3: Safety Rules
- **Role**: Enforce knowledge graph safety rules
- **Responsibilities**:
  - Verify no sensitive data in schema (credentials, secrets)
  - Validate data privacy compliance
  - Check for potentially harmful relationships
  - Ensure schema doesn't enable malicious reasoning
- **Output**: Safety compliance score (0 or 1) with rule violations

### GCL with Multiple Sub-Agents Workflow

```
1. GCL Orchestrator spawns Generator Sub-Agent
   → Generator creates knowledge graph schema

2. GCL Orchestrator spawns 3 Critic Sub-Agents in parallel
   → Sub-Agent 1: Schema Quality validation
   → Sub-Agent 2: Graph Consistency validation
   → Sub-Agent 3: Safety Rules validation

3. GCL Orchestrator aggregates Sub-Agent results
   → Calculate overall score (weighted average)
   → Identify blocking issues (safety violations)

4. Decision logic:
   → Safety=0 OR blocking issues → ABORT
   → All thresholds met → PASS
   → Else → RETRY (max 3 iterations)

5. On PASS: Output knowledge graph schema
   On ABORT: Output error report with recommendations
```

### Scoring and Thresholds

| Dimension | Weight | Threshold | Sub-Agent |
|---|---|---|---|
| **Schema Quality** | 0.4 | ≥ 0.8 | Critic Sub-Agent 1 |
| **Graph Consistency** | 0.4 | ≥ 0.9 | Critic Sub-Agent 2 |
| **Safety Compliance** | 0.2 | = 1.0 (strict) | Critic Sub-Agent 3 |

**Overall Score** = (Schema Quality × 0.4) + (Graph Consistency × 0.4) + (Safety Compliance × 0.2)

### Knowledge Graph Safety Rules (rubric §4)

1. **Rule KG1**: No sensitive data (credentials, secrets) in schema
2. **Rule KG2**: No relationships that could enable privilege escalation
3. **Rule KG3**: No hardcoded IP addresses or internal hostnames
4. **Rule KG4**: No personally identifiable information (PII) in schema
5. **Rule KG5**: Schema must support audit logging and access control

**Missing any ⇒ Safety = 0 ⇒ ABORT**

### GCL with Multiple Sub-Agents Configuration

```yaml
gcl_config:
  max_iterations: 3
  sub_agents:
    generator:
      type: "knowledge_graph_generator"
      model: "default"
      timeout: 300
    critics:
      - type: "schema_quality"
        model: "reasoning"
        timeout: 60
      - type: "graph_consistency"
        model: "reasoning"
        timeout: 60
      - type: "safety_rules"
        model: "default"
        timeout: 30
  scoring:
    weights:
      schema_quality: 0.4
      graph_consistency: 0.4
      safety_compliance: 0.2
    thresholds:
      schema_quality: 0.8
      graph_consistency: 0.9
      safety_compliance: 1.0
```

### Trace and Audit

All sub-agent interactions are logged in trace file:
```
audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
```

Trace includes:
- Generator sub-agent output (knowledge graph schema)
- Each Critic sub-agent's evaluation
- Aggregated scores
- Decision rationale
- Iteration history

### Example GCL with Multiple Sub-Agents Run

**Scenario**: Validate knowledge graph schema for CVM fault diagnosis

1. **Generator Sub-Agent**:
   - Creates schema with 7 entity types and 10 relationship types
   - Defines example instances for CVM instance unreachable fault
   - Validates against API documentation
   - **Output**: Schema JSON with 150 entities and 850 relationships

2. **Critic Sub-Agent 1 (Schema Quality)**:
   - Entity completeness: 95% (PASS)
   - Relationship cardinality: Valid (PASS)
   - Naming conventions: Consistent (PASS)
   - Redundant entities: 2 found (MINOR)
   - **Score: 0.85**

3. **Critic Sub-Agent 2 (Graph Consistency)**:
   - Referential integrity: 100% (PASS)
   - Cycle detection: No cycles (PASS)
   - Orphan entities: 0 (PASS)
   - Acyclic validation: Passed (PASS)
   - **Score: 0.95**

4. **Critic Sub-Agent 3 (Safety Rules)**:
   - Rule KG1: No sensitive data (PASS)
   - Rule KG2: No privilege escalation (PASS)
   - Rule KG3: No hardcoded IPs (PASS)
   - Rule KG4: No PII (PASS)
   - Rule KG5: Audit logging supported (PASS)
   - **Score: 1.0**

5. **GCL Orchestrator Aggregation**:
   - Overall = (0.85 × 0.4) + (0.95 × 0.4) + (1.0 × 0.2) = 0.92
   - All thresholds met
   - **Decision: PASS**

6. **Output**: Validated knowledge graph schema

### Benefits of GCL with Multiple Sub-Agents for Knowledge Graph

1. **Comprehensive Validation**: Multiple sub-agents check different aspects
2. **Parallel Execution**: Faster validation than sequential approach
3. **Specialized Expertise**: Each sub-agent focuses on specific validation
4. **Robust Quality**: Weighted scoring provides balanced evaluation
5. **Clear Accountability**: Each sub-agent has specific responsibilities

### Integration with Existing Skills

The GCL with Multiple Sub-Agents architecture integrates with:
- **Anomaly Detection**: Provides fault patterns for knowledge graph
- **Capacity Planning**: Feeds prediction patterns into knowledge graph
- **Cross-Skill Orchestration**: Coordinates with FinOps and inspection skills
- **Incident Knowledge**: Updates knowledge graph with historical incidents