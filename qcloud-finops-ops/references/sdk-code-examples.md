# FinOps SDK Code Examples

Python SDK code examples for operations where `tccli` fields are incomplete or complex JSON parameters are needed.

## Anomaly Detection Algorithm

```python
def is_anomaly(current, history_3m, budget):
    avg_3m = mean(history_3m)
    ii_ratio  = (current - avg_3m) / avg_3m      # 滚动对比
    iii_ratio = current / budget.amount           # 预算对比
    ii_violated  = ii_ratio  > 0.20               # ii 阈值 20%
    iii_violated = iii_ratio > 0.80               # iii 阈值 80%
    if ii_violated and iii_violated:   confidence = "HIGH"
    elif ii_violated or iii_violated:  confidence = "MEDIUM"
    else:                              confidence = "NORMAL"
    return {"confidence": confidence,
            "ii_violated": ii_violated,  "ii_ratio": ii_ratio,
            "iii_violated": iii_violated, "iii_ratio": iii_ratio}
```
