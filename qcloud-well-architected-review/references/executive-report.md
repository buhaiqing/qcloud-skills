# 卓越架构评估 — 管理层战略报告

> 生成面向 CTO/VP 的可视化摘要，包含风险排名、投入建议和 ROI 估算。

## 报告结构

### 1. 执行摘要

- 整体架构健康评分（满分 5 分）
- 与上次评估的评分变化趋势
- 核心风险数量（Critical / High / Medium）

### 2. 四支柱评分总览

| 支柱 | 评分 | 趋势 | 关键发现 |
|------|------|------|----------|
| 可靠性 | X/5 | ↑/↓/→ | ... |
| 安全性 | X/5 | ↑/↓/→ | ... |
| 成本 | X/5 | ↑/↓/→ | ... |
| 效率 | X/5 | ↑/↓/→ | ... |

### 3. 风险排名（按严重程度）

| 排名 | 风险描述 | 影响范围 | 严重程度 | 建议投入(人天) | ROI 估算 |
|------|----------|----------|----------|---------------|----------|
| 1 | ... | ... | Critical | ... | ... |
| 2 | ... | ... | High | ... | ... |

### 4. 投入产出建议

按 ROI 排序的投资建议：

| 优先级 | 建议 | 预计投入 | 预计收益 | 回收期 |
|--------|------|----------|----------|--------|
| P0 | ... | ... | ... | ... |
| P1 | ... | ... | ... | ... |

### 5. 行动计划

| 阶段 | 内容 | 时间线 | 负责人 |
|------|------|--------|--------|
| Phase 1 | ... | Q3 2026 | ... |
| Phase 2 | ... | Q4 2026 | ... |

## 生成方法

```python
#!/usr/bin/env python3
"""
Executive Report Generator
Aggregates worker outputs into strategic summary
"""
import json
from datetime import datetime

def generate_executive_report(worker_outputs):
    """
    worker_outputs: List of product assessment outputs
    Returns: Executive summary dict
    """
    # Aggregate pillar scores
    pillar_scores = {
        "reliability": [],
        "security": [],
        "cost": [],
        "efficiency": []
    }
    
    for output in worker_outputs:
        for pillar in pillar_scores:
            if pillar in output.get("pillar_scores", {}):
                pillar_scores[pillar].append(output["pillar_scores"][pillar])
    
    # Calculate overall scores
    report = {
        "generated_at": datetime.now().isoformat(),
        "overall_score": sum(
            sum(scores) / len(scores) if scores else 0 
            for scores in pillar_scores.values()
        ) / 4,
        "pillar_summary": {
            pillar: {
                "score": sum(scores) / len(scores) if scores else 0,
                "trend": "→"  # Compare with historical
            }
            for pillar, scores in pillar_scores.items()
        },
        "top_risks": [],  # Extract critical/high risks
        "recommendations": []  # ROI-sorted recommendations
    }
    
    return report
```

## 使用示例

```bash
# Generate executive report from assessment
tccli wellarchitected GenerateExecutiveReport \
  --AssessmentId wa-xxx \
  --ReportFormat markdown
```
