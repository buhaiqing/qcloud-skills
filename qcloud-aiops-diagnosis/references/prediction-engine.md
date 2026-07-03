# Predictive Analysis Engine

> **Predictive analytics for capacity planning and failure prevention.** Extends anomaly detection with trend forecasting, capacity prediction, and proactive alerting. Agent computes predictions from historical monitoring data.
>
> **GCL Integration:** This module participates in the Generator-Critic-Loop (GCL) at the **generation-time** layer. The loop audits the **prediction output** (capacity alerts, trend forecasts), not cloud resources. See `## Quality Gate (GCL)` section for details.

## 1. Prediction Evidence Model

Extend the Anomaly Evidence Model ([`anomaly-detection.md`](anomaly-detection.md) §1) with prediction fields:

```json
{
  "source": "prediction",
  "signal": "capacity_forecast",
  "metric_or_pattern": "DiskUsage",
  "namespace": "QCE/CVM",
  "entity_id": "ins-xxx",
  "entity_type": "cvm_instance",
  "current": {"value": 75, "unit": "%"},
  "historical_data": {
    "data_points": 168,
    "time_range": "7d",
    "granularity": "1h"
  },
  "prediction": {
    "method": "linear_regression",
    "predicted_value": 95,
    "predicted_unit": "%",
    "predicted_time": "2026-07-11T00:00:00+08:00",
    "confidence_interval": {"lower": 90, "upper": 100},
    "confidence_level": 0.95,
    "trend": "increasing",
    "slope": 2.86,
    "r_squared": 0.89
  },
  "capacity_alert": {
    "alert_type": "disk_exhaustion",
    "severity": "HIGH",
    "time_to_exhaustion": "168h",
    "exhaustion_date": "2026-07-11T00:00:00+08:00",
    "recommended_action": "Expand disk or clean up data"
  },
  "timestamp": "2026-07-04T10:00:00+08:00",
  "window_start": "2026-06-27T10:00:00+08:00",
  "window_end": "2026-07-04T10:00:00+08:00"
}
```

### JSON Paths (centralized)

| Field | Path in `GetMonitorData` response |
|---|---|
| Historical values | `DataPoints[0].Values[]` |
| Historical timestamps | `DataPoints[0].Timestamps[]` |
| Current value | `DataPoints[0].Values[-1]` |
| Prediction target | Computed from historical data |

## 2. Prediction Pipeline

```
Resolve target metrics (anomaly-detection.md §2)
  → Fetch historical data (GetMonitorData, 7d window)
  → Clean and preprocess data
  → Fit prediction model
  → Generate forecast
  → Calculate confidence intervals
  → Emit Prediction Finding or Capacity Alert (§5)
```

**API budget:** Max **1 query per metric** for historical data. For prediction scans, cap at `prediction.max_metrics_per_run` (default 10). On rate limit, retry once; then degrade to static threshold warnings.

### Data preprocessing

| Step | Description |
|---|---|
| **Missing value handling** | Interpolate missing data points (linear interpolation) |
| **Outlier removal** | Remove values outside 3σ from moving average |
| **Smoothing** | Apply 3-point moving average to reduce noise |
| **Normalization** | Normalize values to [0, 100] range for percentage metrics |

### Period selection

| Prediction horizon | Historical window | Granularity |
|---|---|---|
| Short-term (1-3 days) | 7 days | 1h |
| Medium-term (1-2 weeks) | 30 days | 6h |
| Long-term (1-3 months) | 90 days | 1d |

## 3. Prediction Methods

### 3.1 Linear Regression (primary)

Simple trend extrapolation using least squares regression:

```python
def linear_regression预测(historical_data: list[float]) -> dict:
    """Fit linear regression model and predict future values."""
    n = len(historical_data)
    x = list(range(n))
    y = historical_data
    
    # Calculate slope and intercept
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    
    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean
    
    # Calculate R-squared
    y_pred = [slope * x[i] + intercept for i in range(n)]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "predicted_value": slope * n + intercept
    }
```

**Use when:**
- Data shows clear linear trend
- R² > 0.7 (good fit)
- No seasonal patterns

### 3.2 Moving Average (secondary)

For data with seasonal patterns or high volatility:

```python
def moving_average预测(historical_data: list[float], window: int = 7) -> float:
    """Predict using weighted moving average."""
    if len(historical_data) < window:
        return sum(historical_data) / len(historical_data)
    
    # Weight recent data more heavily
    weights = list(range(1, window + 1))
    weighted_sum = sum(historical_data[-window:] * weights)
    weight_sum = sum(weights)
    
    return weighted_sum / weight_sum
```

**Use when:**
- Data shows seasonal patterns
- Linear regression R² < 0.7
- Short-term predictions (1-3 days)

### 3.3 Exponential Smoothing (tertiary)

For data with trend and seasonality:

```python
def exponential_smoothing预测(
    historical_data: list[float], 
    alpha: float = 0.3, 
    beta: float = 0.1
) -> dict:
    """Holt's linear exponential smoothing."""
    if len(historical_data) < 2:
        return {"level": historical_data[0], "trend": 0}
    
    level = historical_data[0]
    trend = historical_data[1] - historical_data[0]
    
    for value in historical_data[1:]:
        last_level = level
        level = alpha * value + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
    
    return {
        "level": level,
        "trend": trend,
        "predicted_value": level + trend
    }
```

**Use when:**
- Data has both trend and seasonality
- Need adaptive forecasting
- Medium-term predictions (1-2 weeks)

## 4. Confidence Intervals

Calculate prediction confidence intervals using standard error:

```python
def calculate_confidence_interval(
    predictions: list[float], 
    confidence_level: float = 0.95
) -> dict:
    """Calculate confidence interval for predictions."""
    import math
    
    n = len(predictions)
    mean = sum(predictions) / n
    variance = sum((x - mean) ** 2 for x in predictions) / (n - 1)
    std_error = math.sqrt(variance / n)
    
    # Z-score for 95% confidence
    z_score = 1.96 if confidence_level == 0.95 else 2.58
    
    margin_of_error = z_score * std_error
    
    return {
        "lower": mean - margin_of_error,
        "upper": mean + margin_of_error,
        "confidence_level": confidence_level
    }
```

## 5. Prediction Output Schema

### 5.1 Capacity Alert

```json
{
  "alert_type": "disk_exhaustion|memory_exhaustion|cpu_saturation|network_saturation",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "time_to_exhaustion": "168h",
  "exhaustion_date": "2026-07-11T00:00:00+08:00",
  "current_usage": 75,
  "predicted_usage": 95,
  "recommended_action": "Expand resource or optimize usage",
  "priority": 1
}
```

### 5.2 Trend Prediction

```json
{
  "trend": "increasing|decreasing|stable|seasonal",
  "slope": 2.86,
  "r_squared": 0.89,
  "predicted_value": 95,
  "confidence_interval": {"lower": 90, "upper": 100},
  "prediction_horizon": "7d",
  "accuracy_assessment": "high|medium|low"
}
```

## 6. Capacity Planning Rules

### Rule P1: Disk Exhaustion Prediction

```
IF metric == "DiskUsage" AND prediction.predicted_value >= 90
AND prediction.time_to_exhaustion <= 7d
THEN
  severity = CRITICAL
  action = "Immediate disk expansion required"
  include = ["current_usage", "predicted_usage", "time_to_exhaustion", "recommended_commands"]
```

### Rule P2: Memory Saturation Prediction

```
IF metric == "MemUsage" AND prediction.predicted_value >= 85
AND prediction.time_to_exhaustion <= 3d
THEN
  severity = HIGH
  action = "Optimize memory usage or scale up"
  include = ["memory_trend", "top_memory_consumers", "optimization_suggestions"]
```

### Rule P3: CPU Saturation Prediction

```
IF metric == "CpuUsage" AND prediction.predicted_value >= 80
AND trend == "increasing" AND slope > 1.0
THEN
  severity = MEDIUM
  action = "Review workload and consider scaling"
  include = ["cpu_trend", "workload_analysis", "scaling_options"]
```

### Rule P4: Network Saturation Prediction

```
IF metric == "NetworkOut" AND prediction.predicted_value >= 80% of bandwidth
AND prediction.time_to_exhaustion <= 24h
THEN
  severity = HIGH
  action = "Optimize network usage or increase bandwidth"
  include = ["bandwidth_usage", "top_consumers", "optimization_recommendations"]
```

## 7. Integration with Existing Skills

### 7.1 Anomaly Detection Integration

```python
def enhanced_anomaly_detection(metrics: list) -> list:
    """Combine anomaly detection with predictive analysis."""
    anomalies = detect_anomalies(metrics)
    predictions = predict_trends(metrics)
    
    # Enhance anomalies with predictions
    for anomaly in anomalies:
        matching_prediction = find_matching_prediction(anomaly, predictions)
        if matching_prediction:
            anomaly["prediction"] = matching_prediction
            anomaly["confidence"] = "HIGH" if matching_prediction.r_squared > 0.8 else "MEDIUM"
    
    return anomalies
```

### 7.2 Capacity Planning Integration

```python
def capacity_planning_report(entities: list) -> dict:
    """Generate capacity planning report with predictions."""
    report = {
        "summary": {"total_entities": len(entities)},
        "predictions": [],
        "alerts": [],
        "recommendations": []
    }
    
    for entity in entities:
        prediction = predict_capacity(entity)
        if prediction["alert_type"]:
            report["alerts"].append(prediction["alert"])
        report["predictions"].append(prediction)
    
    # Generate recommendations
    report["recommendations"] = generate_recommendations(report["alerts"])
    
    return report
```

## 8. Validation and Accuracy

### 8.1 Prediction Accuracy Metrics

| Metric | Description | Target |
|---|---|---|
| **MAE** | Mean Absolute Error | < 5% for percentage metrics |
| **MAPE** | Mean Absolute Percentage Error | < 10% |
| **R²** | Coefficient of Determination | > 0.7 for reliable predictions |
| **Coverage** | Confidence interval coverage | 95% for 95% confidence level |

### 8.2 Model Selection Heuristics

| Data Pattern | Recommended Method | Reason |
|---|---|---|
| Linear trend | Linear Regression | Simple, interpretable, good fit |
| Seasonal patterns | Exponential Smoothing | Handles trend + seasonality |
| Volatile data | Moving Average | Smooths noise, stable predictions |
| Limited data (< 30 points) | Moving Average | More robust with limited data |
| Long-term predictions | Linear Regression | Better for trend extrapolation |

## 9. Error Handling

### Prediction-specific error codes

| Error Code | Description | Recovery |
|---|---|---|
| `InsufficientData` | Less than 24h historical data | Use static thresholds; request more data |
| `ModelFittingFailed` | Cannot fit prediction model | Degrade to moving average |
| `ConfidenceTooLow` | R² < 0.5 or wide confidence interval | Mark prediction as LOW confidence |
| `DataQualityIssue` | Too many missing values or outliers | Clean data; retry with smoothing |
| `PredictionHorizonTooLong` | Prediction beyond 90 days | Limit to 90 days; warn about accuracy |

## 10. Example Usage

### 10.1 Disk Capacity Prediction

```python
# Predict disk exhaustion for a CVM instance
prediction = predict_disk_capacity(
    instance_id="ins-xxx",
    historical_days=7,
    prediction_horizon="7d"
)

if prediction["alert_type"] == "disk_exhaustion":
    print(f"⚠️ Disk will be full in {prediction['time_to_exhaustion']}")
    print(f"Current: {prediction['current_usage']}%")
    print(f"Predicted: {prediction['predicted_usage']}%")
    print(f"Recommended: {prediction['recommended_action']}")
```

### 10.2 Memory Usage Trend

```python
# Analyze memory usage trend
trend = analyze_memory_trend(
    instance_id="ins-xxx",
    time_range="30d"
)

print(f"Trend: {trend['trend']}")
print(f"Slope: {trend['slope']:.2f}% per day")
print(f"R²: {trend['r_squared']:.2f}")
print(f"Predicted 30-day usage: {trend['predicted_value']}%")
```

## 11. Limitations and Assumptions

1. **Linear assumptions**: Linear regression assumes constant growth rate
2. **No external factors**: Predictions don't account for planned changes (deployments, scaling)
3. **Data quality**: Accuracy depends on historical data quality
4. **Short-term focus**: Most accurate for 1-7 day predictions
5. **Resource-specific**: Different metrics may need different prediction methods

## 12. Future Enhancements

1. **Machine learning models**: Integrate Prophet, ARIMA for better accuracy
2. **External factor integration**: Include deployment schedules, scaling plans
3. **Anomaly-aware predictions**: Adjust predictions when anomalies are detected
4. **Multi-resource predictions**: Predict across correlated resources
5. **Interactive forecasting**: Allow users to adjust prediction parameters

---

## Quality Gate (GCL) — Multiple Sub-Agents Architecture

This module implements **GCL with Multiple Sub-Agents** for robust quality assurance. The architecture uses a main GCL orchestrator that spawns multiple specialized sub-agents for parallel validation.

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
│    predictions       │  ◄─feedback│  Sub-Agent 1: Data Quality│
│  - Uses historical   │           │  Sub-Agent 2: Model Accuracy│
│    data              │           │  Sub-Agent 3: Safety Rules│
└──────────────────────┘           └──────────────────────────┘
```

### Sub-Agent Roles and Responsibilities

#### 1. Generator Sub-Agent
- **Role**: Generate predictions using historical data
- **Responsibilities**:
  - Fetch historical monitoring data (7-30 days)
  - Apply prediction algorithms (linear regression, moving average, exponential smoothing)
  - Generate confidence intervals
  - Create capacity alerts and trend forecasts
- **Output**: Prediction JSON with confidence intervals and accuracy metrics

#### 2. Critic Sub-Agent 1: Data Quality
- **Role**: Validate input data quality
- **Responsibilities**:
  - Check data completeness (>80% non-null values)
  - Validate data freshness (within 24 hours)
  - Detect outliers and anomalies in historical data
  - Verify data source consistency
- **Output**: Data quality score (0-1) with specific issues

#### 3. Critic Sub-Agent 2: Model Accuracy
- **Role**: Validate prediction model accuracy
- **Responsibilities**:
  - Calculate R², MAE, MAPE metrics
  - Validate confidence interval coverage
  - Check prediction horizon limitations (≤90 days)
  - Compare with baseline methods (static thresholds)
- **Output**: Model accuracy score (0-1) with specific issues

#### 4. Critic Sub-Agent 3: Safety Rules
- **Role**: Enforce prediction safety rules
- **Responsibilities**:
  - Verify predictions use real historical data (not fabricated)
  - Ensure confidence intervals are provided
  - Validate prediction horizons (≤90 days)
  - Check accuracy assessments are included
  - Verify capacity alerts include recommended actions
- **Output**: Safety compliance score (0 or 1) with rule violations

### GCL with Multiple Sub-Agents Workflow

```
1. GCL Orchestrator spawns Generator Sub-Agent
   → Generator generates predictions using historical data

2. GCL Orchestrator spawns 3 Critic Sub-Agents in parallel
   → Sub-Agent 1: Data Quality validation
   → Sub-Agent 2: Model Accuracy validation
   → Sub-Agent 3: Safety Rules validation

3. GCL Orchestrator aggregates Sub-Agent results
   → Calculate overall score (weighted average)
   → Identify blocking issues (safety violations)

4. Decision logic:
   → Safety=0 OR blocking issues → ABORT
   → All thresholds met → PASS
   → Else → RETRY (max 3 iterations)

5. On PASS: Output prediction report
   On ABORT: Output error report with recommendations
```

### Scoring and Thresholds

| Dimension | Weight | Threshold | Sub-Agent |
|---|---|---|---|
| **Data Quality** | 0.3 | ≥ 0.7 | Critic Sub-Agent 1 |
| **Model Accuracy** | 0.4 | ≥ 0.6 | Critic Sub-Agent 2 |
| **Safety Compliance** | 0.3 | = 1.0 (strict) | Critic Sub-Agent 3 |

**Overall Score** = (Data Quality × 0.3) + (Model Accuracy × 0.4) + (Safety Compliance × 0.3)

### Prediction-Specific Safety Rules (rubric §4)

1. **Rule P1**: Predictions MUST be based on real historical data (not fabricated)
2. **Rule P2**: Confidence intervals MUST be provided for all predictions
3. **Rule P3**: Prediction horizons MUST be limited to 90 days
4. **Rule P4**: All predictions MUST include accuracy assessment (R², MAE, MAPE)
5. **Rule P5**: Capacity alerts MUST include recommended actions and priority

**Missing any ⇒ Safety = 0 ⇒ ABORT**

### GCL with Multiple Sub-Agents Configuration

```yaml
gcl_config:
  max_iterations: 3
  sub_agents:
    generator:
      type: "prediction_generator"
      model: "default"
      timeout: 300
    critics:
      - type: "data_quality"
        model: "reasoning"
        timeout: 60
      - type: "model_accuracy"
        model: "reasoning"
        timeout: 60
      - type: "safety_rules"
        model: "default"
        timeout: 30
  scoring:
    weights:
      data_quality: 0.3
      model_accuracy: 0.4
      safety_compliance: 0.3
    thresholds:
      data_quality: 0.7
      model_accuracy: 0.6
      safety_compliance: 1.0
```

### Trace and Audit

All sub-agent interactions are logged in trace file:
```
audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
```

Trace includes:
- Generator sub-agent output (predictions)
- Each Critic sub-agent's evaluation
- Aggregated scores
- Decision rationale
- Iteration history

### Example GCL with Multiple Sub-Agents Run

**Scenario**: Predict disk capacity for CVM instance

1. **Generator Sub-Agent**:
   - Fetches 7 days of disk usage data
   - Applies linear regression
   - Generates prediction: "Disk will be full in 5 days"
   - Calculates R² = 0.89, MAE = 2.3%

2. **Critic Sub-Agent 1 (Data Quality)**:
   - Data completeness: 95% (PASS)
   - Data freshness: 2 hours old (PASS)
   - Outliers detected: 0 (PASS)
   - **Score: 0.95**

3. **Critic Sub-Agent 2 (Model Accuracy)**:
   - R² = 0.89 > 0.6 threshold (PASS)
   - MAE = 2.3% < 5% threshold (PASS)
   - Prediction horizon: 5 days ≤ 90 days (PASS)
   - Confidence interval provided (PASS)
   - **Score: 0.90**

4. **Critic Sub-Agent 3 (Safety Rules)**:
   - Rule P1: Real historical data used (PASS)
   - Rule P2: Confidence interval provided (PASS)
   - Rule P3: Horizon 5 days ≤ 90 days (PASS)
   - Rule P4: R², MAE included (PASS)
   - Rule P5: Recommended action included (PASS)
   - **Score: 1.0**

5. **GCL Orchestrator Aggregation**:
   - Overall = (0.95 × 0.3) + (0.90 × 0.4) + (1.0 × 0.3) = 0.945
   - All thresholds met
   - **Decision: PASS**

6. **Output**: Prediction report with high confidence

### Benefits of GCL with Multiple Sub-Agents

1. **Parallel Validation**: Multiple critic sub-agents run simultaneously, reducing total time
2. **Specialized Expertise**: Each sub-agent focuses on specific validation aspect
3. **Robust Scoring**: Weighted aggregation provides balanced evaluation
4. **Clear Accountability**: Each sub-agent has specific responsibilities
5. **Detailed Traceability**: Complete audit trail of all sub-agent validations

### Integration with Existing Skills

The GCL with Multiple Sub-Agents architecture integrates with:
- **Anomaly Detection**: Shares historical data and baseline methods
- **Capacity Planning**: Provides prediction accuracy metrics
- **Knowledge Graph**: Feeds fault patterns and solutions
- **Cross-Skill Orchestration**: Coordinates with FinOps and inspection skills

---

## Reference Directory

| File | Purpose |
|------|---------|
| [anomaly-detection.md](anomaly-detection.md) | Dynamic baseline anomaly detection |
| [multi-source-rca.md](multi-source-rca.md) | Multi-source root cause analysis |
| [capacity-planning.md](capacity-planning.md) | Capacity planning and optimization |
| [prediction-engine.md](prediction-engine.md) | Predictive analytics and forecasting |
| [knowledge-graph-schema.md](knowledge-graph-schema.md) | Knowledge graph for fault patterns |