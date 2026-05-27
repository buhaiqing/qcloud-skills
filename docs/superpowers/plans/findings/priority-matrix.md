# Cloud Resource Tool Priority Matrix

> **Purpose**: Prioritize cloud resource analysis skill development based on business value, usage patterns, and technical complexity.
>
> **Last Updated**: 2026-05-27
> **Status**: Draft - Pending Review

---

## 1. Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Business Value** | 30% | Importance to daily operations and business continuity |
| **Usage Frequency** | 25% | How often the tool is called in real-world scenarios |
| **Complexity** | 20% | Development difficulty (higher = more valuable to encapsulate as a skill) |
| **Synergy Value** | 15% | Coordination potential with other existing skills |
| **Data Richness** | 10% | Completeness and actionability of tool return data |

---

## 2. Candidate Resource Scoring

### Scoring Methodology

Each resource is scored on a 1-10 scale across all dimensions. The weighted score is calculated as:

```
Weighted Score = (Business × 0.30) + (Frequency × 0.25) + (Complexity × 0.20) + (Synergy × 0.15) + (Richness × 0.10)
```

### Scoring Results

| Resource | Business Value (1-10) | Usage Frequency (1-10) | Complexity (1-10) | Synergy (1-10) | Data Richness (1-10) | **Weighted Score** | Priority |
|----------|:---------------------:|:----------------------:|:-----------------:|:--------------:|:--------------------:|:------------------:|:--------:|
| **RDS MySQL** | 10 | 9 | 8 | 8 | 9 | **8.95** | **P0** |
| **SLB** | 10 | 8 | 7 | 9 | 7 | **8.45** | **P0** |
| **PolarDB** | 7 | 4 | 8 | 5 | 6 | **6.05** | **P1** |
| **PostgreSQL** | 6 | 5 | 7 | 6 | 7 | **6.05** | **P2** |
| **Alarm Info** | 5 | 4 | 4 | 7 | 6 | **4.90** | **P3** |
| **Alarm Rules** | 4 | 3 | 4 | 7 | 5 | **4.15** | **P3** |

### Score Breakdown Analysis

#### P0 - Critical Priority (Score ≥ 8.0)

| Resource | Rationale |
|----------|-----------|
| **RDS MySQL** | Highest business value (10), most frequently used (9), excellent data richness. Core database service used across nearly all projects. |
| **SLB** | High business value (10) for load balancing analysis, strong synergy with other network-related skills, high usage frequency in production environments. |

#### P1 - High Priority (6.0 ≤ Score < 8.0)

| Resource | Rationale |
|----------|-----------|
| **PolarDB** | Moderate business value, lower usage frequency due to fewer adopters. High complexity makes it valuable to encapsulate. |

#### P2 - Medium Priority (5.0 ≤ Score < 6.0)

| Resource | Rationale |
|----------|-----------|
| **PostgreSQL** | Lower business value compared to MySQL variants, but still relevant for specific projects. Moderate usage frequency. |

#### P3 - Low Priority (Score < 5.0)

| Resource | Rationale |
|----------|-----------|
| **Alarm Info** | Limited standalone value. Better integrated into diagnostic workflows. |
| **Alarm Rules** | Configuration-focused, rarely needs standalone analysis. Best as auxiliary data source. |

---

## 3. Scoring Distribution

```
Score Range    | Priority | Count | Resources
---------------|----------|-------|------------------
8.0 - 10.0     | P0       |   2   | RDS MySQL, SLB
6.0 - 7.9      | P1/P2    |   2   | PolarDB, PostgreSQL
4.0 - 5.9      | P3       |   2   | Alarm Info, Alarm Rules
```

---

## 4. Development Timeline

| Phase | Timeline | Resources | Priority | Status |
|-------|----------|-----------|----------|--------|
| **Phase 1** | Immediate | RDS MySQL + SLB | P0 | Planned |
| **Phase 2** | Within 1 month | PolarDB | P1 | Planned |
| **Phase 3** | 2-3 months | PostgreSQL | P2 | Planned |
| **Phase 4** | As needed | Alarm tools | P3 | **Not standalone** |

### Phase 4 Note

> **Alarm tools (Alarm Info, Alarm Rules) are NOT recommended as standalone skills.** They should be integrated into diagnostic and troubleshooting workflows as auxiliary data sources within existing skills like `ecs-analysis-aliyun` or future database analysis skills.

---

## 5. Dependency Analysis

### Skill Synergy Map

```
┌──────────────┐
│  RDS MySQL   │◄────┐
│   (P0)       │     │
└──────┬───────┘     │
       │             │
       ▼             │
┌──────────────┐     │
│     SLB      │     │
│   (P0)       │     │
└──────┬───────┘     │
       │             │
       ▼             │
┌──────────────┐     │
│   PolarDB    │     │
│   (P1)       │     │
└──────┬───────┘     │
       │             │
       ▼             │
┌──────────────┐     │
│ PostgreSQL   │     │
│   (P2)       │     │
└──────┬───────┘     │
       │             │
       └─────────────┘
     Shared patterns & utilities

┌──────────────┐
│ Alarm Tools  │──► Integrate into above skills
│   (P3)       │    as auxiliary data sources
└──────────────┘
```

---

## 6. Review Checklist

- [ ] Scoring dimensions reviewed by team
- [ ] Business value scores validated with stakeholders
- [ ] Usage frequency verified against tool call logs
- [ ] Complexity assessment reviewed by senior developers
- [ ] Timeline approved by project management
- [ ] Risk assessment completed

---

*This document is part of the Cloud Resource Skill Development Plan series.*
