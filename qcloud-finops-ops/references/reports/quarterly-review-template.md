# 季度 FinOps 复盘报告模板

> 本文件由 `SKILL.md` 模块 7 引用。季度复盘标准模板，含季度趋势、ROI 闭环、TCO 目标达成、FinOps 成熟度评估、上季度承诺回顾。

## 模板

```markdown
# 腾讯云季度 FinOps 复盘报告 · {YYYY} Q{quarter}

> 报告周期：{start_date} 至 {end_date}
> 生成时间：{timestamp}
> 数据来源：腾讯云 Billing / Trade / Monitor API
> 报告人：{author} | 审阅人：{reviewer}

---

## 0. 执行摘要（Executive Summary）

> 1 页摘要，给 CFO/CEO 看

### 季度关键指标

| 指标 | Q{q} | Q{q-1} | 环比 | 年度目标 | 达成率 |
|---|---|---|---|---|---|
| 季度总成本 | ¥{q_total} | ¥{q_prev_total} | {qoq:+X.X%} | ¥{annual_target} | {q_achievement}% |
| 月均成本 | ¥{q_avg_monthly} | ¥{q_prev_avg} | {qoq:+X.X%} | ¥{monthly_target} | {m_achievement}% |
| 优化节省金额 | ¥{q_saving} | ¥{q_prev_saving} | {qoq:+X.X%} | ¥{saving_target} | {saving_achievement}% |
| 异常告警次数 | {q_alerts} | {q_prev_alerts} | {qoq_alerts} | < {alert_target} | {alert_status} |
| 资源 Tag 覆盖率 | {tag_coverage}% | {tag_prev_coverage}% | {qoq_tag} | ≥ 95% | {tag_achievement}% |

### 本季度三大亮点

1. ✨ **{highlight_1_title}**：{highlight_1_desc}，节省 ¥{highlight_1_saving}
2. ✨ **{highlight_2_title}**：{highlight_2_desc}，节省 ¥{highlight_2_saving}
3. ✨ **{highlight_3_title}**：{highlight_3_desc}，节省 ¥{highlight_3_saving}

### 本季度三大挑战

1. ⚠️ **{challenge_1_title}**：{challenge_1_desc}
2. ⚠️ **{challenge_2_title}**：{challenge_2_desc}
3. ⚠️ **{challenge_3_title}**：{challenge_3_desc}

### 下季度三大承诺

1. 🎯 **{commitment_1}**：{commitment_1_desc}
2. 🎯 **{commitment_2}**：{commitment_1_desc}
3. 🎯 **{commitment_3}**：{commitment_3_desc}

---

## 1. 季度成本总览

### 1.1 季度成本趋势

| 月份 | 费用 | 环比 | 累计 | 同比 |
|---|---|---|---|---|
| M1 | ¥{m1_cost} | {m1_mom} | ¥{m1_cost} | {m1_yoy} |
| M2 | ¥{m2_cost} | {m2_mom} | ¥{m1_m2_total} | {m2_yoy} |
| M3 | ¥{m3_cost} | {m3_mom} | ¥{q_total} | {m3_yoy} |
| **季度合计** | **¥{q_total}** | - | - | {q_yoy:+X.X%} |

```
[季度趋势 ASCII 图]
M1: ████████████████████  ¥{m1_cost}
M2: █████████████████████ ¥{m2_cost}  (+{m2_mom})
M3: ██████████████████████ ¥{m3_cost}  (+{m3_mom})
```

### 1.2 季度预算执行

| 维度 | 预算 | 实际 | 偏差 | 状态 |
|---|---|---|---|---|
| 季度总预算 | ¥{q_budget} | ¥{q_total} | {q_budget_delta:+X.X%} | {q_budget_status_emoji} |
| 月度均值 | ¥{m_avg_budget} | ¥{m_avg_actual} | {m_avg_delta:+X.X%} | {m_budget_status_emoji} |

**ii 维度（滚动对比）**：
- Q{q} vs 近 4 季均值：{q_ii_ratio:+X.X%}
- 状态：{q_ii_status_emoji}

**iii 维度（预算对比）**：
- Q{q} 实际 / 季度预算：{q_iii_ratio:X.X%}
- 状态：{q_iii_status_emoji}

**季度综合置信度**：{q_confidence} · {q_overall_status_emoji}

---

## 2. 产品成本分析

### 2.1 Top 10 产品成本

| 排名 | 产品 | 本季 | 上季 | 环比 | 占比 | 状态 |
|---|---|---|---|---|---|---|
| 1 | {p1} | ¥{c1} | ¥{c1_prev} | {delta1} | {pct1}% | {s1} |
| 2 | {p2} | ¥{c2} | ¥{c2_prev} | {delta2} | {pct2}% | {s2} |
| 3 | {p3} | ¥{c3} | ¥{c3_prev} | {delta3} | {pct3}% | {s3} |
| 4 | {p4} | ¥{c4} | ¥{c4_prev} | {delta4} | {pct4}% | {s4} |
| 5 | {p5} | ¥{c5} | ¥{c5_prev} | {delta5} | {pct5}% | {s5} |
| 6 | {p6} | ¥{c6} | ¥{c6_prev} | {delta6} | {pct6}% | {s6} |
| 7 | {p7} | ¥{c7} | ¥{c7_prev} | {delta7} | {pct7}% | {s7} |
| 8 | {p8} | ¥{c8} | ¥{c8_prev} | {delta8} | {pct8}% | {s8} |
| 9 | {p9} | ¥{c9} | ¥{c9_prev} | {delta9} | {pct9}% | {s9} |
| 10 | {p10} | ¥{c10} | ¥{c10_prev} | {delta10} | {pct10}% | {s10} |
| - | **其他** | ¥{others} | ¥{others_prev} | {delta_others} | {pct_others}% | - |
| - | **合计** | **¥{total}** | ¥{total_prev} | {qoq} | 100% | - |

**Top 10 集中度**：{top10_concentration}%（越低越健康）

### 2.2 异常产品分析

> 环比 > 30% 的产品需重点分析

| 产品 | 本季 | 上季 | 环比 | 主要驱动 | 根因 | 状态 |
|---|---|---|---|---|---|---|
| {abnormal_p1} | ¥{c_a1} | ¥{c_a1_prev} | {delta_a1} | {driver_a1} | {root_cause_a1} | {status_a1} |
| {abnormal_p2} | ¥{c_a2} | ¥{c_a2_prev} | {delta_a2} | {driver_a2} | {root_cause_a2} | {status_a2} |

**异常处理**：
- {abnormal_action_1}
- {abnormal_action_2}

---

## 3. 优化 ROI 闭环

### 3.1 本季度优化成果

| 优化项 | 类别 | 实施日期 | 月节省 | 季度累计节省 | ROI | 状态 |
|---|---|---|---|---|---|---|
| {opt_1} | {type_opt_1} | {date_opt_1} | ¥{ms_opt_1} | ¥{qs_opt_1} | {roi_opt_1} | {status_opt_1} |
| {opt_2} | {type_opt_2} | {date_opt_2} | ¥{ms_opt_2} | ¥{qs_opt_2} | {roi_opt_2} | {status_opt_2} |
| {opt_3} | {type_opt_3} | {date_opt_3} | ¥{ms_opt_3} | ¥{qs_opt_3} | {roi_opt_3} | {status_opt_3} |
| {opt_4} | {type_opt_4} | {date_opt_4} | ¥{ms_opt_4} | ¥{qs_opt_4} | {roi_opt_4} | {status_opt_4} |
| {opt_5} | {type_opt_5} | {date_opt_5} | ¥{ms_opt_5} | ¥{qs_opt_5} | {roi_opt_5} | {status_opt_5} |
| **合计** | - | - | **¥{ms_total}** | **¥{qs_total}** | {roi_avg} | - |

**季度累计节省**：¥{qs_total}
**对比目标**：¥{saving_target}（达成 {saving_achievement}%）
**对比上季**：¥{q_prev_saving}（{qoq_saving:+X.X%}）

### 3.2 待实施优化（Next Quarter Pipeline）

| 优化项 | 类别 | 预期月节省 | 风险 | owner | 计划实施日期 |
|---|---|---|---|---|---|
| {pipe_1} | {type_pipe_1} | ¥{ms_pipe_1} | {risk_pipe_1} | {owner_pipe_1} | {date_pipe_1} |
| {pipe_2} | {type_pipe_2} | ¥{ms_pipe_2} | {risk_pipe_2} | {owner_pipe_2} | {date_pipe_2} |
| {pipe_3} | {type_pipe_3} | ¥{ms_pipe_3} | {risk_pipe_3} | {owner_pipe_3} | {date_pipe_3} |
| {pipe_4} | {type_pipe_4} | ¥{ms_pipe_4} | {risk_pipe_4} | {owner_pipe_4} | {date_pipe_4} |
| {pipe_5} | {type_pipe_5} | ¥{ms_pipe_5} | {risk_pipe_5} | {owner_pipe_5} | {date_pipe_5} |
| **合计** | - | **¥{pipe_total}** | - | - | - |

**Pipeline 预期季度节省**（按 50% 实施率）：¥{pipe_estimated}

### 3.3 上季度承诺回顾

| 序号 | 上季度承诺 | 计划完成日期 | 实际完成日期 | 状态 | 备注 |
|---|---|---|---|---|---|
| 1 | {commit_prev_1} | {date_commit_1} | {date_actual_1} | {status_commit_1} | {note_commit_1} |
| 2 | {commit_prev_2} | {date_commit_2} | {date_actual_2} | {status_commit_2} | {note_commit_2} |
| 3 | {commit_prev_3} | {date_commit_3} | {date_actual_3} | {status_commit_3} | {note_commit_3} |
| 4 | {commit_prev_4} | {date_commit_4} | {date_actual_4} | {status_commit_4} | {note_commit_4} |
| 5 | {commit_prev_5} | {date_commit_5} | {date_actual_5} | {status_commit_5} | {note_commit_5} |

**承诺达成率**：{commit_achievement}%

---

## 4. 异常账单复盘

### 4.1 本季度异常事件汇总

| 月份 | 异常类型 | 置信度 | 异常产品 | 根因 | 解决状态 |
|---|---|---|---|---|---|
| M1 | {m1_anomaly_type} | {m1_conf} | {m1_product} | {m1_cause} | {m1_status} |
| M2 | {m2_anomaly_type} | {m2_conf} | {m2_product} | {m2_cause} | {m2_status} |
| M3 | {m3_anomaly_type} | {m3_conf} | {m3_product} | {m3_cause} | {m3_status} |

**异常次数**：{q_anomaly_count}（vs 上季 {q_prev_anomaly_count}）
**平均响应时间**：{avg_response_time}小时
**平均解决时间**：{avg_resolution_time}小时

### 4.2 重点异常事件复盘

> 选取本季度 1-2 个最严重异常事件做深度复盘

#### 事件 1：{event_1_title}

- **时间**：{event_1_time}
- **置信度**：{event_1_confidence}
- **异常金额**：¥{event_1_amount}
- **影响范围**：{event_1_impact}

**时间线**：

| 时间 | 事件 |
|---|---|
| {tl_1_time_1} | {tl_1_event_1} |
| {tl_1_time_2} | {tl_1_event_2} |
| {tl_1_time_3} | {tl_1_event_3} |
| {tl_1_time_4} | {tl_1_event_4} |
| {tl_1_time_5} | {tl_1_event_5}（已恢复）|

**根因分析**：
- **直接原因**：{direct_cause}
- **根本原因**：{root_cause}
- **系统性问题**：{systemic_issue}

**改进措施**：
- {improvement_1}
- {improvement_2}
- {improvement_3}

**owner**：{event_1_owner} | **状态**：{event_1_status}

#### 事件 2：{event_2_title}
（同上结构）

---

## 5. 成本分摊（Tag 归因）

### 5.1 按业务线

| 业务线 | Q{q} | Q{q-1} | 环比 | 占比 | 年度预算 | 预算执行率 |
|---|---|---|---|---|---|---|
| {bl_1} | ¥{bl_1_q} | ¥{bl_1_q_prev} | {delta_bl_1} | {pct_bl_1}% | ¥{bl_1_budget} | {bl_1_achievement}% |
| {bl_2} | ¥{bl_2_q} | ¥{bl_2_q_prev} | {delta_bl_2} | {pct_bl_2}% | ¥{bl_2_budget} | {bl_2_achievement}% |
| {bl_3} | ¥{bl_3_q} | ¥{bl_3_q_prev} | {delta_bl_3} | {pct_bl_3}% | ¥{bl_3_budget} | {bl_3_achievement}% |
| 未分类 | ¥{bl_uncat_q} | ¥{bl_uncat_q_prev} | {delta_bl_uncat} | {pct_bl_uncat}% | - | - |

### 5.2 按环境

| 环境 | Q{q} | 占比 | 趋势 |
|---|---|---|---|
| 生产 | ¥{prod_q} | {pct_prod}% | {prod_trend} |
| 预发 | ¥{staging_q} | {pct_staging}% | {staging_trend} |
| 测试 | ¥{dev_q} | {pct_dev}% | {dev_trend} |

### 5.3 按部门

| 部门 | Q{q} | 占比 | 环比 | 人均成本 |
|---|---|---|---|---|
| {dept_1} | ¥{dept_1_q} | {pct_dept_1}% | {delta_dept_1} | ¥{per_capita_1}/人 |
| {dept_2} | ¥{dept_2_q} | {pct_dept_2}% | {delta_dept_2} | ¥{per_capita_2}/人 |
| {dept_3} | ¥{dept_3_q} | {pct_dept_3}% | {delta_dept_3} | ¥{per_capita_3}/人 |

### 5.4 Tag 覆盖率

| 维度 | 应打标资源 | 实际打标 | 覆盖率 | 趋势 |
|---|---|---|---|---|
| 业务线 | {should_tag} | {actual_tag_bl} | {cov_bl}% | {trend_bl} |
| 部门 | {should_tag} | {actual_tag_dept} | {cov_dept}% | {trend_dept} |
| 环境 | {should_tag} | {actual_tag_env} | {cov_env}% | {trend_env} |
| 项目 | {should_tag} | {actual_tag_proj} | {cov_proj}% | {trend_proj} |

**未打标资源成本**：¥{untagged_cost}（占 {untagged_pct}%）

---

## 6. 资源包与代金券

### 6.1 资源包使用率

| 资源包 | 类型 | 总额 | 已用 | 剩余 | 使用率 | 状态 | 建议 |
|---|---|---|---|---|---|---|---|
| {pkg_q_1} | {pkg_type_1} | ¥{total_pkg_1} | ¥{used_pkg_1} | ¥{remaining_pkg_1} | {usage_pkg_1}% | {status_pkg_1} | {rec_pkg_1} |
| {pkg_q_2} | {pkg_type_2} | ¥{total_pkg_2} | ¥{used_pkg_2} | ¥{remaining_pkg_2} | {usage_pkg_2}% | {status_pkg_2} | {rec_pkg_2} |
| {pkg_q_3} | {pkg_type_3} | ¥{total_pkg_3} | ¥{used_pkg_3} | ¥{remaining_pkg_3} | {usage_pkg_3}% | {status_pkg_3} | {rec_pkg_3} |

**资源包效率评分**：{pkg_efficiency_score}/100

### 6.2 代金券

| 状态 | 数量 | 金额 |
|---|---|---|
| 可用 | {unused_q_count} | ¥{unused_q_amount} |
| 本季消耗 | {used_q_count} | ¥{used_q_amount} |
| 已过期 | {expired_q_count} | ¥{expired_q_amount} |

**代金券利用率**：{voucher_utilization}%
**代金券贡献折扣**：¥{voucher_discount}（占 {voucher_discount_pct}%）

---

## 7. 容量规划

### 7.1 资源增长趋势

| 资源类型 | Q{q-1} 末 | Q{q} 末 | 增长 | 增长率 | 趋势 |
|---|---|---|---|---|---|
| CVM | {cvm_prev} | {cvm_q} | {cvm_growth} | {cvm_growth_pct}% | {cvm_trend} |
| CDB | {cdb_prev} | {cdb_q} | {cdb_growth} | {cdb_growth_pct}% | {cdb_trend} |
| COS 存储 | {cos_prev} | {cos_q} | {cos_growth} | {cos_growth_pct}% | {cos_trend} |
| CLB | {clb_prev} | {clb_q} | {clb_growth} | {clb_growth_pct}% | {clb_trend} |

### 7.2 下季度容量预测

| 资源类型 | Q{q+1} 预测 | 预测依据 | 预留策略 |
|---|---|---|---|
| CVM | {cvm_forecast} | {cvm_basis} | {cvm_strategy} |
| CDB | {cdb_forecast} | {cdb_basis} | {cdb_strategy} |
| COS | {cos_forecast} | {cos_basis} | {cos_strategy} |
| CLB | {clb_forecast} | {clb_basis} | {clb_strategy} |

**预测方法**：
- 线性回归（基于近 4 季数据）
- 业务增长率调整
- 季节性系数（如有）

---

## 8. TCO 目标达成

### 8.1 年度 TCO 目标

| 指标 | 年度目标 | Q{q} 累计 | 达成率 | 预测全年 | 预测达成 |
|---|---|---|---|---|---|
| 年度总成本 | ≤ ¥{annual_tco} | ¥{ytd_cost} | {ytd_pct}% | ¥{forecast_annual} | {forecast_achievement}% |
| 单业务请求成本 | ≤ ¥{unit_cost} | ¥{unit_cost_actual} | {unit_achievement}% | - | - |
| 单位营收成本 | ≤ ¥{cost_per_revenue}% | {cost_per_rev_actual}% | {cpr_achievement}% | - | - |

### 8.2 FinOps 成熟度评估

| 维度 | 等级（1-5）| 描述 |
|---|---|---|
| 可视化（Inform）| {level_inform} | {desc_inform} |
| 优化（Optimize）| {level_optimize} | {desc_optimize} |
| 运营（Operate）| {level_operate} | {desc_operate} |
| **综合等级** | **{level_overall}** | {desc_overall} |

**成熟度模型**：
- L1 初始：手动导出 + 事后分析
- L2 重复：月度报告 + 定期 review
- L3 定义：标准化流程 + 工具化
- L4 量化：数据驱动决策 + 自动化
- L5 优化：持续优化 + 行业最佳实践

**本季度成熟度变化**：{level_change}

---

## 9. 风险与改进

### 9.1 识别的风险

| 风险 | 等级 | 描述 | 缓解措施 | owner |
|---|---|---|---|---|
| {risk_1} | {level_risk_1} | {desc_risk_1} | {mitigation_1} | {owner_risk_1} |
| {risk_2} | {level_risk_2} | {desc_risk_2} | {mitigation_2} | {owner_risk_2} |
| {risk_3} | {level_risk_3} | {desc_risk_3} | {mitigation_3} | {owner_risk_3} |

### 9.2 流程改进建议

| # | 改进项 | 类别 | 预期收益 | owner | 优先级 |
|---|---|---|---|---|---|
| 1 | {improvement_1} | {category_imp_1} | {benefit_imp_1} | {owner_imp_1} | P{priority_imp_1} |
| 2 | {improvement_2} | {category_imp_2} | {benefit_imp_2} | {owner_imp_2} | P{priority_imp_2} |
| 3 | {improvement_3} | {category_imp_3} | {benefit_imp_3} | {owner_imp_3} | P{priority_imp_3} |
| 4 | {improvement_4} | {category_imp_4} | {benefit_imp_4} | {owner_imp_4} | P{priority_imp_4} |
| 5 | {improvement_5} | {category_imp_5} | {benefit_imp_5} | {owner_imp_5} | P{priority_imp_5} |

---

## 10. 下季度承诺

| 序号 | 承诺 | 衡量指标 | 目标值 | owner | 完成日期 |
|---|---|---|---|---|---|
| 1 | {next_commit_1} | {kpi_1} | {target_1} | {owner_next_1} | {date_next_1} |
| 2 | {next_commit_2} | {kpi_2} | {target_2} | {owner_next_2} | {date_next_2} |
| 3 | {next_commit_3} | {kpi_3} | {target_3} | {owner_next_3} | {date_next_3} |
| 4 | {next_commit_4} | {kpi_4} | {target_4} | {owner_next_4} | {date_next_4} |
| 5 | {next_commit_5} | {kpi_5} | {target_5} | {owner_next_5} | {date_next_5} |

---

## 11. 附录

### 11.1 数据来源

- 账单：`billing DescribeBillSummaryByMonth` × 3 月
- 账单明细：`billing DescribeBillList`（L3 级）
- 账户余额：`billing DescribeAccountBalance`
- 代金券：`voucher DescribeVoucherList`
- 订单：`trade DescribeOrders`
- 资源包：`billing DescribeResourcePackageList`
- 监控（联动）：`qcloud-monitor-ops`
- 资源元数据（联动）：23 个产品 skill

### 11.2 报告元数据

| 项 | 值 |
|---|---|
| 报告版本 | v1.0 |
| 模板版本 | v1.0 |
| 生成时间 | {timestamp} |
| 生成系统 | qcloud-finops-ops v1.0 |
| 数据范围 | {start_date} - {end_date} |
| 报告人 | {author} |
| 审阅人 | {reviewer} |
| 下次报告时间 | {next_run} |

### 11.3 术语表

| 术语 | 解释 |
|---|---|
| ii 维度 | 滚动对比：与近 3 月均值对比 |
| iii 维度 | 预算对比：与本月预算对比 |
| HIGH 置信度 | 双维度违反，触发自动派发巡检 |
| TCO | Total Cost of Ownership，总拥有成本 |
| FinOps 成熟度 | L1-L5 评估模型 |

---

> **审阅与发布**：
> - FinOps 团队 review：{review_finops_date}
> - 财务 review：{review_finance_date}
> - 高管 review：{review_exec_date}
> - 正式发布：{publish_date}
> - 下季度报告：{next_quarter_date}

> **本报告由 qcloud-finops-ops 自动生成**
```

---

## 章节结构

| # | 章节 | 定位 | 必选 |
|---|---|---|---|
| 0 | 执行摘要 | 1 页给高管 | ✅ |
| 1 | 季度成本总览 | 季度核心数据 | ✅ |
| 2 | 产品成本分析 | Top 10 + 异常 | ✅ |
| 3 | 优化 ROI 闭环 | **季度核心价值** | ✅ |
| 4 | 异常账单复盘 | 深度复盘 1-2 个 | ✅ |
| 5 | 成本分摊 | Tag 归因 | ✅ |
| 6 | 资源包与代金券 | 财务工具 | ⭐ |
| 7 | 容量规划 | 下季度预测 | ⭐ |
| 8 | TCO 目标达成 | 战略目标 | ⭐ |
| 9 | 风险与改进 | 风险管理 | ⭐ |
| 10 | 下季度承诺 | 闭环 | ✅ |
| 11 | 附录 | 可审计 | ✅ |

## 与月度报告的关系

| 维度 | 月度 | 季度 |
|---|---|---|
| 时间跨度 | 1 月 | 3 月 |
| 视角 | 当月运营 | 趋势 + 战略 |
| 受众 | 财务 + 业务 | CFO + CEO + 业务 |
| 重点 | 异常检测 | ROI 闭环 |
| 深度 | 表格为主 | 含复盘 + 改进 |
| 频次 | 每月 1 日 | 每季首月 1 日 |

## 关键设计

| 设计 | 体现 |
|---|---|
| **承诺闭环** | §3.3 上季度承诺回顾 + §10 下季度承诺 |
| **ROI 闭环** | §3.1 本季度成果 + §3.2 下季 pipeline |
| **异常复盘** | §4 完整时间线 + 根因 + 改进措施 |
| **成熟度评估** | §8.2 L1-L5 模型 |
| **容量预测** | §7.2 线性回归 + 业务调整 |

## 使用方式

```bash
# 自动生成（推荐）
qcloud-finops-ops report quarterly --quarter 2026Q2 --output ./reports/

# 手动填写（紧急）
cp quarterly-review-template.md 2026Q2-review.md
# 替换 {xxx} 占位符
```

## 联动建议

- §3 优化 ROI → 联动 `qcloud-monitor-ops` 拉取实施后效果
- §4 异常复盘 → 联动 `qcloud-aiops-diagnosis` 提供根因分析
- §7 容量规划 → 联动各产品 skill 拉取资源增长趋势
- §8 成熟度 → 参考 `qcloud-well-architected-review` 评估模型
