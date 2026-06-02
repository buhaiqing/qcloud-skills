# 月度账单报告模板

> 本文件由 `SKILL.md` 模块 7 引用。月度账单报告标准模板，含双维度对比、TopN、优化建议、资源包分析、置信度判定。

## 模板

```markdown
# 腾讯云月度账单报告 · {YYYY-MM}

> 生成时间：{timestamp}
> 数据来源：腾讯云 Billing / Trade / Voucher API
> 报告周期：{start_date} 至 {end_date}
> 置信度：{confidence} | 状态：{status_emoji}

---

## 1. 本月总览

| 指标 | 数值 | 同比 | 环比 |
|---|---|---|---|
| 本月总费用 | ¥{current_total} | {yoy:+X.X%} | {mom:+X.X%} |
| 现金支付 | ¥{cash_paid} | {yoy_cash} | {mom_cash} |
| 代金券抵扣 | ¥{voucher_used} | {yoy_voucher} | {mom_voucher} |
| 资源包抵扣 | ¥{package_used} | {yoy_package} | {mom_package} |
| 实际净费用 | ¥{net_cost} | {yoy_net} | {mom_net} |
| 订单数 | {order_count} | {yoy_orders} | {mom_orders} |
| 资源数 | {resource_count} | {yoy_resources} | {mom_resources} |

**关键状态**：
- {status_emoji} 综合判定：{overall_status}
- 💰 账户余额：¥{balance}（现金）/ ¥{available_credit}（可用信用）
- 🎟️ 代金券余额：¥{voucher_remaining}（{voucher_count} 张）

---

## 2. [维度 ii] 滚动对比

> 与近 3 月均值对比，捕捉业务波动

| 指标 | 数值 |
|---|---|
| 本月费用 | ¥{current_total} |
| 近 3 月均值 | ¥{avg_3m} |
| 偏差金额 | ¥{delta_3m}（{ii_ratio:+X.X%}）|
| 阈值 | {ii_threshold:20%} |
| 状态 | {ii_status_emoji} {ii_status} |

**近 6 月趋势**：

```
[折线图占位，ASCII 简版]
2025-12: ████████████████████  ¥{m1}
2026-01: █████████████████████ ¥{m2}
2026-02: ███████████████████   ¥{m3}
2026-03: █████████████████████ ¥{m4}  ← 近 3 月起点
2026-04: █████████████████████ ¥{m5}
2026-05: ████████████████████████████ ¥{m6}  ← 本月
```

**ii 维度判定**：
- ✅ 正常：偏差 < 20%
- ⚠️ 异常：偏差 ≥ 20%（MEDIUM 置信度触发条件之一）

---

## 3. [维度 iii] 预算对比

> 与本月预算对比，捕捉预算执行情况

| 指标 | 数值 |
|---|---|
| 本月预算 | ¥{budget_amount} |
| 已使用 | ¥{current_total}（{iii_ratio:X.X%}）|
| 剩余 | ¥{budget_remaining} |
| 阈值（80%）| ¥{warn_threshold} |
| 状态 | {iii_status_emoji} {iii_status} |

**预算执行率**：

```
[进度条占位]
0% ──────── 50% ──────── 80%(warn) ──────── 100%(critical) ────────►
                  {progress_bar_filled} 当前 {iii_ratio}%
```

**iii 维度判定**：
- ✅ 正常：使用 < 80%
- ⚠️ 警戒：80% ≤ 使用 < 100%
- 🚨 超支：使用 ≥ 100%

---

## 4. 综合判断

**置信度评估**：

| ii_violated | iii_violated | 置信度 | 状态 |
|---|---|---|---|
| ❌ | ❌ | NORMAL | 🟢 正常 |
| ✅ | ❌ | MEDIUM | 🟡 需关注 |
| ❌ | ✅ | MEDIUM | 🟡 需关注 |
| ✅ | ✅ | **HIGH** | 🔴 **异常告警** |

**本月判定**：**{confidence} 置信度 · {overall_status_emoji}**

**触发动作**：
- 🟢 NORMAL：归档备查
- 🟡 MEDIUM：通知 owner，准备 review
- 🔴 HIGH：通知 owner + 财务，**自动派发巡检工单**（qcloud-proactive-inspection）

---

## 5. Top 5 成本来源

| 排名 | 产品 | 本月 | 上月 | 同比 | 环比 | 占比 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | {product_1} | ¥{cost_1} | ¥{cost_1_prev} | {yoy_1} | {mom_1} | {pct_1}% | {delta_emoji_1} |
| 2 | {product_2} | ¥{cost_2} | ¥{cost_2_prev} | {yoy_2} | {mom_2} | {pct_2}% | {delta_emoji_2} |
| 3 | {product_3} | ¥{cost_3} | ¥{cost_3_prev} | {yoy_3} | {mom_3} | {pct_3}% | {delta_emoji_3} |
| 4 | {product_4} | ¥{cost_4} | ¥{cost_4_prev} | {yoy_4} | {mom_4} | {pct_4}% | {delta_emoji_4} |
| 5 | {product_5} | ¥{cost_5} | ¥{cost_5_prev} | {yoy_5} | {mom_5} | {pct_5}% | {delta_emoji_5} |
| - | **其他** | ¥{cost_others} | ¥{cost_others_prev} | {yoy_others} | {mom_others} | {pct_others}% | - |
| - | **合计** | **¥{total}** | ¥{total_prev} | - | - | 100% | - |

**Top 5 占比**：{top5_pct}%

**异常产品**（环比 > 30%）：{abnormal_products}

---

## 6. Top 5 优化建议

> 详见 `references/finops-methodology.md` §3 完整 28 类建议

### 建议 #1：{type_1} - {resource_1}

- **资源**：`{resource_id_1}`（{env_1}，{spec_1}，{pay_mode_1}）
- **触发条件**：{trigger_1}
- **当前成本**：¥{current_cost_1}/月
- **优化后成本**：¥{optimized_cost_1}/月
- **节省金额**：¥{saving_1}/月（{saving_pct_1}）
- **风险等级**：{risk_level_1}
- **审批 owner**：{owner_1}
- **预期年化节省**：¥{annual_saving_1}
- **回本周期**：{payback_1}
- **实施步骤**：
  1. {step_1_1}
  2. {step_1_2}
  3. {step_1_3}

### 建议 #2：{type_2} - {resource_2}
（同上结构）

### 建议 #3：{type_3} - {resource_3}
（同上结构）

### 建议 #4：{type_4} - {resource_4}
（同上结构）

### 建议 #5：{type_5} - {resource_5}
（同上结构）

**Top 5 预期月节省合计**：¥{total_saving}/月
**Top 5 预期年化节省**：¥{annual_total_saving}

---

## 7. 资源包使用率

| 资源包 | 类型 | 总额 | 已用 | 剩余 | 使用率 | 状态 | 建议 |
|---|---|---|---|---|---|---|---|
| {pkg_1} | CDN 流量 | ¥{total_1} | ¥{used_1} | ¥{remaining_1} | {usage_1}% | {pkg_status_1} | {rec_1} |
| {pkg_2} | SCF 调用 | ¥{total_2} | ¥{used_2} | ¥{remaining_2} | {usage_2}% | {pkg_status_2} | {rec_2} |
| {pkg_3} | COS 存储 | ¥{total_3} | ¥{used_3} | ¥{remaining_3} | {usage_3}% | {pkg_status_3} | {rec_3} |

**状态判定**：
- ✅ 健康：30% ≤ 使用率 ≤ 90%
- ⚠️ 偏低：使用率 < 30%（可能资源包规格过大）
- 🚨 紧张：使用率 > 90%（快用完，需追加）
- ⏰ 过期：资源包 30 天内过期

---

## 8. 按 Tag 分摊（成本归因）

### 8.1 按业务线

| 业务线 | 本月费用 | 占比 | 环比 |
|---|---|---|---|
| {bl_1} | ¥{cost_bl_1} | {pct_bl_1}% | {mom_bl_1} |
| {bl_2} | ¥{cost_bl_2} | {pct_bl_2}% | {mom_bl_2} |
| {bl_3} | ¥{cost_bl_3} | {pct_bl_3}% | {mom_bl_3} |
| 未分类 | ¥{cost_bl_uncat} | {pct_bl_uncat}% | {mom_bl_uncat} |

### 8.2 按环境

| 环境 | 本月费用 | 占比 | 环比 |
|---|---|---|---|
| 生产 | ¥{cost_prod} | {pct_prod}% | {mom_prod} |
| 预发 | ¥{cost_staging} | {pct_staging}% | {mom_staging} |
| 测试 | ¥{cost_dev} | {pct_dev}% | {mom_dev} |

### 8.3 按部门

| 部门 | 本月费用 | 占比 | 环比 |
|---|---|---|---|
| {dept_1} | ¥{cost_dept_1} | {pct_dept_1}% | {mom_dept_1} |
| {dept_2} | ¥{cost_dept_2} | {pct_dept_2}% | {mom_dept_2} |
| {dept_3} | ¥{cost_dept_3} | {pct_dept_3}% | {mom_dept_3} |

**未打标资源**：{untagged_count} 个，¥{untagged_cost}（占 {untagged_pct}%）

---

## 9. 订单与代金券

### 9.1 订单统计

| 状态 | 数量 | 金额 |
|---|---|---|
| 已支付 | {paid_count} | ¥{paid_amount} |
| 未支付 | {unpaid_count} | ¥{unpaid_amount} |
| 已取消 | {cancelled_count} | ¥{cancelled_amount} |
| 退款中 | {refunding_count} | ¥{refunding_amount} |

**重点订单**：
- {important_order_1}
- {important_order_2}

### 9.2 代金券

| 状态 | 数量 | 金额 |
|---|---|---|
| 可用 | {unused_count} | ¥{unused_amount} |
| 已用 | {used_count} | ¥{used_amount} |
| 已过期 | {expired_count} | ¥{expired_amount} |

**本月消耗代金券**：¥{voucher_used_this_month}（来自 {voucher_used_count} 张）

---

## 10. 异常事件（如有）

> 仅 HIGH 置信度时填写

### 10.1 异常告警

- **告警时间**：{alert_time}
- **告警类型**：{alert_type}（ii / iii / 双维度）
- **置信度**：{confidence}
- **通知通道**：{channels}

### 10.2 巡检工单

- **工单标题**：【FinOps 告警】{YYYY-MM} 账单异常 · HIGH 置信度
- **工单 ID**：{ticket_id}
- **派发对象**：{assignee}
- **截止时间**：{deadline}
- **状态**：{ticket_status}

### 10.3 根因摘要

> 详见 `references/cost-analysis-queries.md` §6 完整根因报告

- **Top 1 异常产品**：{top_abnormal_product}（增量 {abnormal_delta}）
- **主因**：{main_cause}
- **次因**：{secondary_cause}

---

## 11. 行动项与跟进

| 序号 | 行动项 | owner | 截止 | 优先级 |
|---|---|---|---|---|
| 1 | {action_1} | {owner_1} | {deadline_1} | P{priority_1} |
| 2 | {action_2} | {owner_2} | {deadline_2} | P{priority_2} |
| 3 | {action_3} | {owner_3} | {deadline_3} | P{priority_3} |
| 4 | {action_4} | {owner_4} | {deadline_4} | P{priority_4} |
| 5 | {action_5} | {owner_5} | {deadline_5} | P{priority_5} |

---

## 12. 附录

### 12.1 数据来源

- 账单汇总：`billing DescribeBillSummaryByMonth`
- 账单明细：`billing DescribeBillList`（L3 级，{n_records} 条记录）
- 账户余额：`billing DescribeAccountBalance`
- 代金券：`voucher DescribeVoucherList`
- 订单：`trade DescribeOrders`
- 资源包：`billing DescribeResourcePackageList`

### 12.2 API 调用时间戳

| API | 调用时间 | 耗时 |
|---|---|---|
| DescribeBillSummaryByMonth | {ts_1} | {duration_1} |
| DescribeBillList | {ts_2} | {duration_2} |
| ... | ... | ... |

### 12.3 异常检测参数

```yaml
anomaly_detection:
  rolling:
    history_months: 3
    threshold: 0.20
  budget:
    threshold: 0.80
  confidence:
    auto_dispatch_on: HIGH
```

### 12.4 报告生成

- 模板版本：v1.0
- 生成时间：{timestamp}
- 生成人/系统：{author_or_system}
- 下次报告时间：{next_run}

---

> **审阅建议**：
> - 🟢 NORMAL：财务归档备查
> - 🟡 MEDIUM：FinOps 团队 review，72 小时内确认
> - 🔴 HIGH：业务方 + 财务 + FinOps 共同 review，启动根因分析

> **本报告由 qcloud-finops-ops 自动生成**
```

---

## 字段说明

| 字段 | 数据源 | 备注 |
|---|---|---|
| `{current_total}` | `DescribeBillSummaryByMonth` | 本月实际总费用 |
| `{avg_3m}` | 过去 3 月汇总取均值 | 滚动对比基线 |
| `{ii_ratio}` | `(current - avg_3m) / avg_3m` | 维度 ii 偏差率 |
| `{iii_ratio}` | `current / budget.amount` | 维度 iii 使用率 |
| `{confidence}` | `is_anomaly()` 算法输出 | HIGH / MEDIUM / NORMAL |
| `{top5_pct}` | Top 5 金额合计 / 总金额 | 集中度指标 |
| `{total_saving}` | Top 5 优化建议月节省合计 | ROI 评估 |

## 使用方式

```bash
# 自动生成（推荐）
qcloud-finops-ops report monthly --month 2026-05 --output ./reports/

# 手动填写（紧急）
cp monthly-bill-template.md 2026-05-bill-report.md
# 替换 {xxx} 占位符
```

## 关键章节清单

| # | 章节 | 必选 | 备注 |
|---|---|---|---|
| 1 | 本月总览 | ✅ | 必选 |
| 2 | ii 维度对比 | ✅ | 必选 |
| 3 | iii 维度对比 | ✅ | 必选 |
| 4 | 综合判断 | ✅ | 必选 |
| 5 | Top 5 成本来源 | ✅ | 必选 |
| 6 | Top 5 优化建议 | ✅ | 必选 |
| 7 | 资源包使用率 | ⭐ 推荐 | 有资源包时必填 |
| 8 | Tag 分摊 | ⭐ 推荐 | 有 Tag 数据时填 |
| 9 | 订单与代金券 | ⭐ 推荐 | 月度必填 |
| 10 | 异常事件 | 🔴 HIGH 必填 | 仅 HIGH 置信度 |
| 11 | 行动项 | ✅ | 必选 |
| 12 | 附录 | ✅ | 必选（可审计）|
