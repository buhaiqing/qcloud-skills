# 示例工作流：异常账单 → 自动巡检 → 根因报告

> 本文件由 `SKILL.md` 模块 8 引用。**端到端工作流手册**：从异常检测到根因报告的完整 5 阶段操作流程，含调用模板、产物路径、失败处理。

## 场景描述

**触发条件**：本月账单异常（ii 维度或 iii 维度违反），置信度 ≥ MEDIUM

**目标**：
1. 自动识别异常
2. 派发巡检工单
3. 联动产品 skill 做根因分析
4. 生成结构化报告
5. 通知相关负责人

**适用人员**：FinOps 团队、业务方、财务

## 整体流程图

```
┌────────────────────────────────────────────────────────────────────┐
│ 阶段 1：异常检测（Detect）                                          │
│  · 输入：账单 API + 历史数据                                         │
│  · 处理：is_anomaly() 算法（ii + iii 双维度）                       │
│  · 输出：confidence + ii_ratio + iii_ratio + violated_dims          │
│  · 工具：tccli + Python SDK                                        │
│  · 产物：detection_result.json                                     │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
                  ┌────────────┴────────────┐
                  │ confidence?              │
                  └────────────┬────────────┘
                               ↓
        ┌──────────────────────┼──────────────────────┐
        │ NORMAL               │ MEDIUM               │ HIGH
        ↓                      ↓                      ↓
┌──────────────┐    ┌────────────────────┐    ┌────────────────────┐
│ 阶段 1b：归档 │    │ 阶段 2-4 同 HIGH    │    │ 阶段 2-4 全流程    │
│ · 写归档日志  │    │ 但跳过自动派发      │    │ · 自动派发巡检工单  │
│ · 结束       │    │ · 仅通知 owner      │    │ · 全链路联动        │
└──────────────┘    └────────────────────┘    └────────┬───────────┘
                                                         ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段 2：自动派发巡检（Dispatch）                                     │
│  · 输入：detection_result + 异常产品列表                              │
│  · 处理：调用 qcloud-proactive-inspection 创建工单                    │
│  · 输出：ticket_id + assignee + deadline                            │
│  · 产物：ticket.json                                                │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段 3：根因分析（Root Cause）                                      │
│  · 输入：异常产品列表 + 资源元数据 + 监控指标                          │
│  · 处理：delegate 到对应产品 skill（cvm/cdb/cos/clb）                  │
│  · 输出：每个异常产品的根因报告                                       │
│  · 产物：root_cause_{product}.json                                  │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段 4：报告生成（Report）                                          │
│  · 输入：所有阶段产物                                                │
│  · 处理：聚合 + 模板渲染                                             │
│  · 输出：Markdown / CSV / JSON 三种格式                              │
│  · 产物：anomaly_report_{YYYY-MM}.md                                │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段 5：通知（Notify）                                              │
│  · 输入：anomaly_report + ticket_id                                 │
│  · 处理：调用 qcloud-monitor-ops 触发告警通道                         │
│  · 输出：邮件 + 短信 + 飞书/钉钉/企业微信                              │
│  · 产物：notification_log.json                                      │
└────────────────────────────────────────────────────────────────────┘
```

## 阶段 1：异常检测（Detect）

### 1.1 目标

判断本月账单是否异常，输出置信度（HIGH/MEDIUM/NORMAL）。

### 1.2 输入

- 腾讯云凭证（环境变量）
- 本月账单数据（实时拉取）
- 历史 3 月数据
- 本月预算（从 `example-config.yaml` 读取）

### 1.3 步骤

#### Step 1.1：拉取本月账单

```bash
# tccli 方式
tccli billing DescribeBillSummaryByMonth \
  --Month "2026-05" \
  --PayType "prePayAndPostPay" \
  > /tmp/current_bill.json

# 提取总费用
current=$(jq -r '.SummaryTotal.RealTotalCost' /tmp/current_bill.json)
```

#### Step 1.2：拉取历史 3 月数据

```bash
for m in 2026-02 2026-03 2026-04; do
  tccli billing DescribeBillSummaryByMonth \
    --Month "$m" \
    --PayType "prePayAndPostPay" \
    > "/tmp/bill_${m}.json"
done
```

#### Step 1.3：读取预算

```bash
# 从配置文件读取
budget=$(yq '.budgets[] | select(.name=="全账号月度预算") | .amount' \
  $TENCENTCLOUD_FINOPS_CONFIG)
```

#### Step 1.4：执行异常检测算法

```python
# finops_workflow.py
import json
from statistics import mean

def is_anomaly(current, history_3m, budget, ii_threshold=0.20, iii_threshold=0.80):
    avg_3m = mean(history_3m)
    ii_ratio = (current - avg_3m) / avg_3m
    iii_ratio = current / budget

    ii_violated = ii_ratio > ii_threshold
    iii_violated = iii_ratio > iii_threshold

    if ii_violated and iii_violated:
        confidence = "HIGH"
    elif ii_violated or iii_violated:
        confidence = "MEDIUM"
    else:
        confidence = "NORMAL"

    return {
        "current": current,
        "avg_3m": avg_3m,
        "ii_ratio": round(ii_ratio, 4),
        "iii_ratio": round(iii_ratio, 4),
        "ii_violated": ii_violated,
        "iii_violated": iii_violated,
        "confidence": confidence,
        "is_anomaly": confidence != "NORMAL"
    }

# 实际数据（从 API 拉取）
result = is_anomaly(
    current=128450.20,
    history_3m=[98000, 99500, 101000],
    budget=100000
)
print(json.dumps(result, indent=2, ensure_ascii=False))
```

#### Step 1.5：写入产物

```bash
# 产物路径
mkdir -p ./workflow_artifacts/2026-05
echo $result | jq '.' > ./workflow_artifacts/2026-05/detection_result.json
```

### 1.4 输出产物

**`./workflow_artifacts/2026-05/detection_result.json`**：

```json
{
  "current": 128450.20,
  "avg_3m": 99500.00,
  "ii_ratio": 0.2910,
  "iii_ratio": 1.2845,
  "ii_violated": true,
  "iii_violated": true,
  "confidence": "HIGH",
  "is_anomaly": true,
  "timestamp": "2026-05-31T23:59:59+08:00"
}
```

### 1.5 失败处理

| 失败 | 处理 |
|---|---|
| API 限流 | 退避重试 3 次，指数退避 |
| 历史数据不足 3 月 | 使用可用数据，标注"基线不完整" |
| 预算未配置 | 跳过 iii 维度，仅做 ii 检测 |
| 计算异常（除零）| 兜底使用 ii 单维度 |

## 阶段 2：自动派发巡检（Dispatch）

### 2.1 目标

将异常事件转化为可追踪的巡检工单。

### 2.2 触发条件

- `confidence == "HIGH"`：自动派发
- `confidence == "MEDIUM"`：通知 owner 但不自动派发（人工 review 后决定）
- `confidence == "NORMAL"`：跳过此阶段

### 2.3 步骤

#### Step 2.1：构造工单

```python
# finops_workflow.py（续）
ticket = {
    "title": f"【FinOps 告警】2026-05 账单异常 · {result['confidence']} 置信度",
    "description": f"""
        **异常概览**：
        - 本月费用：¥{result['current']}
        - 近 3 月均值：¥{result['avg_3m']}
        - 偏差：{result['ii_ratio']*100:.1f}%（阈值 20%）
        - 预算使用率：{result['iii_ratio']*100:.1f}%（阈值 80%）
        - 置信度：{result['confidence']}

        **后续动作**：详见根因报告
    """,
    "priority": "P1" if result['confidence'] == "HIGH" else "P2",
    "assignee": "finops-team@company.com",
    "cc": ["cfo@company.com", "business-owner@company.com"],
    "deadline": "3 个工作日",
    "tags": ["finops", "billing-anomaly", f"confidence-{result['confidence'].lower()}"],
    "created_by": "qcloud-finops-ops"
}
```

#### Step 2.2：调用 qcloud-proactive-inspection

```bash
# 通过 Agent 路由到 qcloud-proactive-inspection
# 输入：上述 ticket JSON
# 输出：ticket_id
```

**Agent 调用模板**：

```python
# finops_workflow.py（续）
inspection_result = delegate_to_skill(
    skill="qcloud-proactive-inspection",
    action="create_ticket",
    params=ticket
)
ticket_id = inspection_result["ticket_id"]
```

#### Step 2.3：写入产物

```bash
echo $ticket | jq '.' > ./workflow_artifacts/2026-05/ticket.json
echo "{\"ticket_id\": \"$ticket_id\"}" > ./workflow_artifacts/2026-05/ticket_id.json
```

### 2.4 输出产物

**`./workflow_artifacts/2026-05/ticket.json`**：

```json
{
  "title": "【FinOps 告警】2026-05 账单异常 · HIGH 置信度",
  "priority": "P1",
  "assignee": "finops-team@company.com",
  "tags": ["finops", "billing-anomaly", "confidence-high"]
}
```

**`./workflow_artifacts/2026-05/ticket_id.json`**：

```json
{
  "ticket_id": "DOPS-20260531-001"
}
```

## 阶段 3：根因分析（Root Cause）

### 3.1 目标

对每个异常产品，定位具体根因（新增资源 / 既有涨价 / 用量激增）。

### 3.2 步骤

#### Step 3.1：拉取账单明细（L3 级）

```bash
# 拉全量明细（分页）
tccli billing DescribeBillList \
  --Month "2026-05" \
  --Offset 0 \
  --Limit 1000 \
  --PayType "prePayAndPostPay" \
  > /tmp/bill_details_p1.json

# 翻页（如需要）
tccli billing DescribeBillList \
  --Month "2026-05" \
  --Offset 1000 \
  --Limit 1000 \
  --PayType "prePayAndPostPay" \
  > /tmp/bill_details_p2.json
```

#### Step 3.2：按产品聚合 + 对比上月

```python
# finops_workflow.py（续）
import yaml
from collections import defaultdict

# 聚合本月
current_by_product = defaultdict(float)
for record in bill_details:
    product = record["BusinessCodeName"]
    current_by_product[product] += float(record["RealCost"])

# 聚合上月（同样的方法）
# ...

# 计算 delta
delta_by_product = {
    product: current_by_product[product] - prev_by_product.get(product, 0)
    for product in current_by_product
}

# Top 5 异常产品
top5_abnormal = sorted(
    delta_by_product.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]
```

#### Step 3.3：delegate 到产品 skill

> **核心**：对每个异常产品，调用对应的产品 skill 拉取资源列表 + 监控数据

**CVM 异常分析**（delegate `qcloud-cvm-ops`）：

```python
cvm_analysis = delegate_to_skill(
    skill="qcloud-cvm-ops",
    action="analyze_cost",
    params={
        "month": "2026-05",
        "delta_threshold": 5000,  # CNY
        "include_metrics": ["CPUUsage", "MemoryUsage"],
        "lookback_days": 7
    }
)
# 返回：
# {
#   "new_instances": [
#     {"id": "cvm-abc1", "spec": "8C16G", "monthly_cost": 1500}
#   ],
#   "increased_usage": [
#     {"id": "cvm-xyz1", "old_qps": 100, "new_qps": 300, "delta_cost": 13500}
#   ],
#   "stable_instances": [...],
#   "root_cause": "业务上线新活动，用量激增 3 倍"
# }
```

**CDB 异常分析**（delegate `qcloud-cdb-ops`）：

```python
cdb_analysis = delegate_to_skill(
    skill="qcloud-cdb-ops",
    action="analyze_cost",
    params={
        "month": "2026-05",
        "delta_threshold": 3000
    }
)
```

**COS 异常分析**（delegate `qcloud-cos-ops`）：

```python
cos_analysis = delegate_to_skill(
    skill="qcloud-cos-ops",
    action="analyze_cost",
    params={
        "month": "2026-05",
        "check_lifecycle_rules": True
    }
)
```

#### Step 3.4：聚合所有产品的根因

```python
all_root_causes = {
    "cvm": cvm_analysis,
    "cdb": cdb_analysis,
    "cos": cos_analysis,
    # ... 其他 Top 5
}
```

#### Step 3.5：写入产物

```python
for product, analysis in all_root_causes.items():
    with open(f"./workflow_artifacts/2026-05/root_cause_{product}.json", "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
```

### 3.3 输出产物

每个异常产品一个 JSON：

**`./workflow_artifacts/2026-05/root_cause_cvm.json`**：

```json
{
  "product": "CVM",
  "month": "2026-05",
  "total_delta": 15000,
  "new_instances": [
    {"id": "cvm-abc1", "spec": "8C16G", "monthly_cost": 1500, "created_at": "2026-05-10"},
    {"id": "cvm-abc2", "spec": "8C16G", "monthly_cost": 1500, "created_at": "2026-05-10"},
    {"id": "cvm-abc3", "spec": "8C16G", "monthly_cost": 1500, "created_at": "2026-05-12"}
  ],
  "increased_usage": [
    {
      "id": "cvm-xyz1",
      "spec": "4C8G",
      "old_daily_cost": 50,
      "new_daily_cost": 500,
      "delta_monthly": 13500,
      "trigger_event": "2026-05-15 业务上线新活动",
      "metrics": {"old_qps": 100, "new_qps": 300}
    }
  ],
  "root_cause": "业务上线新活动，3 台新实例 + 既有 3 台用量激增 3 倍"
}
```

## 阶段 4：报告生成（Report）

### 4.1 目标

将所有阶段产物聚合为结构化报告（Markdown + CSV + JSON）。

### 4.2 步骤

#### Step 4.1：加载所有产物

```python
import json
from pathlib import Path

artifacts_dir = Path("./workflow_artifacts/2026-05")
detection = json.load(open(artifacts_dir / "detection_result.json"))
ticket = json.load(open(artifacts_dir / "ticket.json"))
ticket_id = json.load(open(artifacts_dir / "ticket_id.json"))["ticket_id"]

root_causes = {}
for f in artifacts_dir.glob("root_cause_*.json"):
    product = f.stem.replace("root_cause_", "")
    root_causes[product] = json.load(open(f))
```

#### Step 4.2：渲染 Markdown 报告

使用 `references/reports/monthly-bill-template.md` 作为模板（简化版）。

```python
# finops_workflow.py（续）
def render_anomaly_report(detection, ticket_id, root_causes):
    md = f"""
# 异常账单根因报告 · 2026-05

> 生成时间：{timestamp}
> 工单 ID：{ticket_id}

## 1. 异常概览

- **本月费用**：¥{detection['current']}（环比 +{detection['ii_ratio']*100:.1f}%，超预算 {(detection['iii_ratio']-1)*100:.1f}%）
- **置信度**：**{detection['confidence']}**（ii + iii 双维度违反）
- **ii 维度**：{detection['ii_ratio']*100:.1f}% > 20% 阈值
- **iii 维度**：{detection['iii_ratio']*100:.1f}% > 80% 阈值

## 2. Top 5 异常产品根因

"""
    for i, (product, analysis) in enumerate(root_causes.items(), 1):
        md += f"### {i}. {product.upper()}（增量 ¥{analysis['total_delta']}）\n\n"
        md += f"**根因**：{analysis['root_cause']}\n\n"

        if analysis.get('new_instances'):
            md += "**新增资源**：\n"
            for inst in analysis['new_instances'][:5]:
                md += f"- `{inst['id']}`（{inst['spec']}）¥{inst['monthly_cost']}/月\n"
            md += "\n"

        if analysis.get('increased_usage'):
            md += "**既有资源涨价**：\n"
            for inst in analysis['increased_usage'][:5]:
                md += f"- `{inst['id']}`：{inst.get('trigger_event', '用量激增')}，增量 ¥{inst['delta_monthly']}/月\n"
            md += "\n"

    md += """
## 3. 巡检工单

- **标题**：{ticket['title']}
- **工单 ID**：{ticket_id}
- **优先级**：{ticket['priority']}
- **截止时间**：3 个工作日

## 4. 优化建议

详见月度账单报告 `references/reports/monthly-bill-template.md` §6
"""
    return md

report_md = render_anomaly_report(detection, ticket_id, root_causes)
```

#### Step 4.3：生成 CSV（数据导出）

```python
import csv

with open("./reports/2026-05-anomaly.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Product", "Delta", "Root Cause", "New Instances", "Increased Usage"])
    for product, analysis in root_causes.items():
        writer.writerow([
            product,
            analysis['total_delta'],
            analysis['root_cause'],
            len(analysis.get('new_instances', [])),
            len(analysis.get('increased_usage', []))
        ])
```

#### Step 4.4：生成 JSON（API 复用）

```python
full_report = {
    "detection": detection,
    "ticket": ticket,
    "ticket_id": ticket_id,
    "root_causes": root_causes,
    "timestamp": "2026-05-31T23:59:59+08:00"
}

with open("./reports/2026-05-anomaly.json", "w") as f:
    json.dump(full_report, f, indent=2, ensure_ascii=False)
```

### 4.3 输出产物

| 文件 | 格式 | 用途 |
|---|---|---|
| `./reports/2026-05-anomaly.md` | Markdown | 发邮件/飞书/钉钉 |
| `./reports/2026-05-anomaly.csv` | CSV | BI/数据中台 |
| `./reports/2026-05-anomaly.json` | JSON | API 复用 |

## 阶段 5：通知（Notify）

### 5.1 目标

通过多通道通知 owner + 财务 + 业务方。

### 5.2 步骤

#### Step 5.1：调用 qcloud-monitor-ops

```python
# finops_workflow.py（续）
notification = delegate_to_skill(
    skill="qcloud-monitor-ops",
    action="send_alert",
    params={
        "alert_type": "finops_billing_anomaly",
        "severity": "critical" if detection['confidence'] == "HIGH" else "warning",
        "title": f"【FinOps 告警】2026-05 账单异常 · {detection['confidence']}",
        "content": report_md,
        "channels": ["email", "wecom", "sms"],
        "recipients": {
            "email": ["finops-team@company.com", "cfo@company.com"],
            "sms": ["+8613800000000"],
            "wecom": ["@finops-team"]
        },
        "ticket_id": ticket_id,
        "report_url": "https://reports.company.com/finops/2026-05-anomaly.html"
    }
)
```

#### Step 5.2：写入通知日志

```python
import json
notification_log = {
    "ticket_id": ticket_id,
    "channels_sent": ["email", "wecom", "sms"],
    "recipients_count": 3,
    "report_url": "https://reports.company.com/finops/2026-05-anomaly.html",
    "timestamp": "2026-05-31T23:59:59+08:00"
}

with open("./workflow_artifacts/2026-05/notification_log.json", "w") as f:
    json.dump(notification_log, f, indent=2, ensure_ascii=False)
```

### 5.3 输出产物

**`./workflow_artifacts/2026-05/notification_log.json`**：

```json
{
  "ticket_id": "DOPS-20260531-001",
  "channels_sent": ["email", "wecom", "sms"],
  "recipients_count": 3,
  "report_url": "https://reports.company.com/finops/2026-05-anomaly.html",
  "timestamp": "2026-05-31T23:59:59+08:00"
}
```

## 端到端集成脚本

```python
#!/usr/bin/env python3
# finops_anomaly_workflow.py
# 用法：python finops_anomaly_workflow.py --month 2026-05

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from statistics import mean

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="YYYY-MM")
    args = parser.parse_args()

    artifacts_dir = Path(f"./workflow_artifacts/{args.month}")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 阶段 1：异常检测
    print("[1/5] 异常检测...")
    detection = detect_anomaly(args.month)
    json.dump(detection, open(artifacts_dir / "detection_result.json", "w"),
              indent=2, ensure_ascii=False)

    if not detection['is_anomaly']:
        print("✅ 正常，结束工作流")
        return

    print(f"⚠️ 异常 {detection['confidence']} 置信度")

    # 阶段 2：派发巡检
    if detection['confidence'] == "HIGH":
        print("[2/5] 派发巡检工单...")
        ticket_id = dispatch_inspection(detection, args.month)
        json.dump({"ticket_id": ticket_id},
                  open(artifacts_dir / "ticket_id.json", "w"))

    # 阶段 3：根因分析
    print("[3/5] 根因分析...")
    root_causes = analyze_root_cause(args.month)
    for product, analysis in root_causes.items():
        json.dump(analysis,
                  open(artifacts_dir / f"root_cause_{product}.json", "w"),
                  indent=2, ensure_ascii=False)

    # 阶段 4：报告生成
    print("[4/5] 报告生成...")
    report_path = generate_report(detection, root_causes, ticket_id, args.month)

    # 阶段 5：通知
    if detection['confidence'] == "HIGH":
        print("[5/5] 发送通知...")
        send_notification(detection, report_path, ticket_id)

    print(f"✅ 工作流完成，报告：{report_path}")

if __name__ == "__main__":
    main()
```

## 完整产物清单

```
workflow_artifacts/
└── 2026-05/
    ├── detection_result.json          # 阶段 1
    ├── ticket.json                    # 阶段 2
    ├── ticket_id.json                 # 阶段 2
    ├── root_cause_cvm.json            # 阶段 3
    ├── root_cause_cdb.json            # 阶段 3
    ├── root_cause_cos.json            # 阶段 3
    ├── root_cause_clb.json            # 阶段 3
    └── notification_log.json          # 阶段 5

reports/
├── 2026-05-anomaly.md                # 阶段 4
├── 2026-05-anomaly.csv               # 阶段 4
└── 2026-05-anomaly.json              # 阶段 4
```

## 失败处理汇总

| 阶段 | 失败 | 处理 |
|---|---|---|
| 1 | API 限流 | 退避重试 3 次 |
| 1 | 历史数据不足 | 标注"基线不完整"继续 |
| 2 | 工单创建失败 | 写 alert_escalation 日志，通知人工 |
| 3 | 产品 skill delegate 失败 | 单产品跳过，不阻塞整体 |
| 4 | 报告生成失败 | 写 partial_report，标记缺失章节 |
| 5 | 通知发送失败 | 重试 + 写 notification_failed 日志 |

## 复用与参考

| 文档 | 用途 |
|---|---|
| `SKILL.md` §模块 4.3 | 异常检测算法 |
| `references/finops-methodology.md` §2 | 算法推导 + 变体 |
| `references/cost-analysis-queries.md` §6 | 根因报告输出示例 |
| `references/reports/monthly-bill-template.md` | 月度报告模板 |
| `references/troubleshooting.md` | 故障排查 |
