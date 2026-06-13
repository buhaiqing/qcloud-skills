# Reporting Templates — Proactive Inspection

## Report Structure

### Executive Summary
```markdown
## 巡检报告 - {{date}}
**巡检范围**: {{user.products}} / {{env.TENCENTCLOUD_REGION}}
**资源总数**: {{count}} 个实例
**健康评分**: {{score}}/100

### 风险概览
| 级别 | 数量 | Top 3 风险 |
|------|------|-----------|
| Critical | {{count}} | - |
| Warning | {{count}} | - |
| Info | {{count}} | - |
```

### Detail Breakdown
```markdown
## 资源详情

### CVM 实例
| 实例ID | 名称 | CPU | 内存 | 磁盘 | 状态 | 风险 |
|--------|------|-----|------|------|------|------|
| ins-xxx | api-01 | 45% | 72% | 68% | RUNNING | - |
| ins-yyy | db-01 | 92% | 88% | 91% | RUNNING | ⚠ CPU, ⚠ Disk |
```

### Actionable Items
```markdown
## 修复建议

### Critical (立即处理)
1. [DOPS-xxxx] ins-yyy CPU 92% 持续 2h → 排查慢查询/流量突增
2. [DOPS-xxxx] ins-yyy 磁盘 91% → 清理日志/扩容

### Warning (本周内处理)
1. ins-zzz 内存使用率 85% → 监控趋势，必要时升配
2. cbp-aaa 未关联实例 45 天 → 确认是否可删除
```

## GCL Quality Section (Phase 3)

When `./audit-results/gcl-trace-*.json` exists in the inspection window, embed skill execution quality:

```markdown
## Agent 技能质量 (GCL)

**数据窗口**: 最近 {{gcl_since_hours}}h | **汇总文件**: {{gcl_summary_path}}

| 指标 | 值 |
|------|-----|
| 总执行次数 | {{gcl.totals.total_runs}} |
| 通过率 | {{gcl.pass_rate}} |
| Safety 失败 | {{gcl.totals.SAFETY_FAIL}} |
| MAX_ITER 耗尽 | {{gcl.totals.MAX_ITER}} |

### 按技能 breakdown
| 技能 | 总数 | PASS | SAFETY_FAIL | MAX_ITER |
|------|------|------|-------------|----------|
| {{skill}} | {{total}} | {{PASS}} | {{SAFETY_FAIL}} | {{MAX_ITER}} |

> 生成命令: `python3 scripts/gcl_trace_aggregate.py --since-hours {{gcl_since_hours}}`  
> 告警阈值: 见 `qcloud-monitor-ops` → `gcl_quality` config
```

Pre-flight: run aggregate script; if no traces, omit this section (do not fabricate metrics).

## Report Generation (Python)
```python
def generate_report(resources, metrics, detections, format='markdown'):
    report = {
        'executive_summary': {
            'total_resources': len(resources),
            'health_score': calculate_health_score(detections),
            'risk_counts': count_by_severity(detections)
        },
        'resource_details': format_resource_details(resources, metrics),
        'findings': format_findings(detections),
        'recommendations': generate_recommendations(detections)
    }
    if format == 'markdown':
        return render_markdown(report)
    return report
```
