# MTTR 自动追踪

> 每次故障诊断后自动记录：故障时间 → 诊断时间 → 恢复时间。

## 追踪字段

| 字段 | 来源 | 说明 |
|------|------|------|
| incident_id | AIOps 诊断记录 | 故障唯一 ID，格式：INC-YYYYMMDD-XXXX |
| detected_at | 告警触发时间 | 首次告警时间戳 (ISO 8601) |
| diagnosis_at | 诊断完成时间 | AIOps 输出根因时间戳 |
| resolved_at | 用户确认恢复时间 | 资源恢复时间戳 |
| mttd | detected_at → diagnosis_at | 平均诊断时间 (分钟) |
| mttr | detected_at → resolved_at | 平均恢复时间 (分钟) |
| product | 涉及产品 | cvm/cdb/tke/clb/... |
| severity | 严重程度 | P0/P1/P2/P3 |
| root_cause | 根因分类 | 基础设施/应用/配置/网络/... |

## MTTR 记录流程

### 1. 故障检测 (Detected)

```python
incident_record = {
    "incident_id": generate_incident_id(),
    "detected_at": alarm["trigger_time"],  # 来自监控告警
    "product": detect_product_from_alarm(alarm),
    "severity": alarm["severity"],
    "status": "DETECTED"
}
```

### 2. 诊断完成 (Diagnosed)

```python
# AIOps 诊断完成后
incident_record.update({
    "diagnosis_at": datetime.now().isoformat(),
    "root_cause": diagnosis_result["root_cause_category"],
    "mttd": calculate_minutes(
        incident_record["detected_at"], 
        datetime.now()
    ),
    "status": "DIAGNOSED"
})
```

### 3. 恢复确认 (Resolved)

```python
# 用户确认恢复后
incident_record.update({
    "resolved_at": datetime.now().isoformat(),
    "mttr": calculate_minutes(
        incident_record["detected_at"],
        datetime.now()
    ),
    "status": "RESOLVED"
})

# 持久化到存储
save_to_incident_db(incident_record)
```

## 月报聚合

### SQL 查询模板

```sql
-- 按产品的 MTTR 统计
SELECT
  product,
  COUNT(*) as total_incidents,
  AVG(mttd) as avg_mttd_minutes,
  AVG(mttr) as avg_mttr_minutes,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mttr) as p95_mttr,
  COUNT(CASE WHEN severity = 'P0' THEN 1 END) as p0_count
FROM incidents
WHERE detected_at >= date_trunc('month', NOW())
GROUP BY product
ORDER BY avg_mttr_minutes DESC;
```

### 趋势分析

```sql
-- 周环比 MTTR 趋势
SELECT
  date_trunc('week', detected_at) as week,
  AVG(mttr) as avg_mttr,
  AVG(mttd) as avg_mttd
FROM incidents
WHERE detected_at >= NOW() - INTERVAL '12 weeks'
GROUP BY week
ORDER BY week;
```

## 集成到诊断流程

在 SKILL.md 的故障诊断流程末尾，添加 MTTR 记录步骤：

```markdown
### Post-diagnosis: MTTR Recording

在输出诊断报告后，记录本次诊断的时间指标：

| Field | Value | Source |
|-------|-------|--------|
| `incident_id` | {{output.incident_id}} | Generated at detection |
| `detected_at` | {{alarm.trigger_time}} | Monitor alarm |
| `diagnosis_at` | {{output.diagnosis_completed_at}} | This diagnosis |
| `product` | {{output.affected_product}} | Diagnosis result |
| `severity` | {{alarm.severity}} | Monitor alarm |
| `root_cause` | {{output.root_cause.category}} | Diagnosis result |

MTTR Record JSON:
```json
{
  "incident_id": "{{output.incident_id}}",
  "detected_at": "{{alarm.trigger_time}}",
  "diagnosis_at": "{{output.diagnosis_completed_at}}",
  "product": "{{output.affected_product}}",
  "severity": "{{alarm.severity}}",
  "root_cause": "{{output.root_cause.category}}",
  "mttd": "{{output.metrics.mttd_minutes}}"
}
```
```

## 报告输出

### 月度 MTTR 报告

```markdown
# MTTR 月报 — 2026年7月

## 概览

| 指标 | 本月 | 上月 | 变化 |
|------|------|------|------|
| 总故障数 | 45 | 52 | ↓ 13% |
| 平均 MTTR | 28.5 min | 35.2 min | ↓ 19% |
| 平均 MTTD | 5.2 min | 6.8 min | ↓ 24% |
| P0 故障数 | 2 | 3 | ↓ 33% |

## 按产品 MTTR

| 产品 | 故障数 | 平均 MTTR | P95 MTTR |
|------|--------|-----------|----------|
| CVM | 12 | 22 min | 45 min |
| CDB | 8 | 35 min | 78 min |
| TKE | 15 | 25 min | 52 min |
| CLB | 10 | 30 min | 60 min |

## 改进建议

1. **CDB 恢复时间偏长**: 建议优化备份恢复流程
2. **MTTD 已达标**: 平均 5.2 分钟低于 10 分钟目标
```

## 工具脚本

```python
#!/usr/bin/env python3
"""
MTTR Tracker - 命令行工具
"""
import json
import sqlite3
from datetime import datetime

def record_incident(incident_data):
    # 记录故障数据
    conn = sqlite3.connect('incidents.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO incidents 
        (incident_id, detected_at, diagnosis_at, resolved_at, 
         product, severity, root_cause, mttd, mttr)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        incident_data['incident_id'],
        incident_data['detected_at'],
        incident_data.get('diagnosis_at'),
        incident_data.get('resolved_at'),
        incident_data['product'],
        incident_data['severity'],
        incident_data.get('root_cause'),
        incident_data.get('mttd'),
        incident_data.get('mttr')
    ))
    
    conn.commit()
    conn.close()

def generate_monthly_report(year, month):
    # 生成月报
    conn = sqlite3.connect('incidents.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT product, COUNT(*), AVG(mttr), AVG(mttd)
        FROM incidents
        WHERE strftime('%Y-%m', detected_at) = ?
        GROUP BY product
    ''', (f"{year}-{month:02d}",))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'report':
        report = generate_monthly_report(2026, 7)
        for row in report:
            print(f"{row[0]}: {row[1]} incidents, MTTR={row[2]:.1f}min")
```
