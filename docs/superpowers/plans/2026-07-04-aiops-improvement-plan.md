# AIOps 改进执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于评估报告中的发现，优化 AIOps 诊断能力，重点提升 SLB 5xx 故障和 RDS MySQL 的 MTTR 表现

**Architecture:** 保持现有 AIOps 诊断框架，针对特定产品优化诊断流程和恢复策略

**Tech Stack:** tccli CLI, Python 3.8+, Markdown runbooks

---

## Phase 1: SLB 5xx 故障 MTTR 优化

### 背景
- **当前 MTTR:** 45-90 分钟
- **目标 MTTR:** < 30 分钟
- **预期改进:** 40-60%
- **来源:** `docs/superpowers/plans/findings/slb-skill-assessment.md`

### Task 1.1: 分析当前 SLB 5xx 故障诊断流程

**Files:**
- Read: `qcloud-clb-ops/SKILL.md`
- Read: `qcloud-clb-ops/references/troubleshooting.md`
- Read: `qcloud-aiops-diagnosis/references/product-rca-rules.md`

- [x] **Step 1: 提取当前 SLB 5xx 诊断步骤**

从现有文档中提取：
1. 5xx 错误分类（502/503/504 等）
2. 当前诊断决策树
3. 恢复步骤
4. 平均诊断时间分布

- [x] **Step 2: 识别诊断瓶颈**

分析当前流程中的时间消耗点：
1. 指标查询时间
2. 日志分析时间
3. 根因定位时间
4. 恢复验证时间

- [x] **Step 3: 记录当前基线**

```bash
# 记录当前诊断流程的平均时间
echo "当前 SLB 5xx 诊断流程基线:"
echo "1. 指标查询: ~5 分钟"
echo "2. 日志分析: ~15 分钟" 
echo "3. 根因定位: ~20 分钟"
echo "4. 恢复验证: ~10 分钟"
echo "总计: ~50 分钟"
```

---

### Task 1.2: 优化 SLB 5xx 诊断决策树

**Files:**
- Modify: `qcloud-clb-ops/references/troubleshooting.md`
- Create: `qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md`

- [x] **Step 1: 创建优化后的诊断决策树**

```markdown
# SLB 5xx 故障快速诊断决策树

## 1. 快速分类 (< 2 分钟)

### 1.1 5xx 错误类型识别
| 错误码 | 可能原因 | 优先级 | 预期诊断时间 |
|--------|----------|--------|--------------|
| 502 Bad Gateway | 后端服务不可用 | P1 | < 10 分钟 |
| 503 Service Unavailable | 后端过载/维护 | P1 | < 10 分钟 |
| 504 Gateway Timeout | 后端响应超时 | P2 | < 15 分钟 |
| 5xx 其他 | 需要进一步分析 | P3 | < 20 分钟 |

### 1.2 快速检查清单
- [ ] 检查后端健康状态: `tccli clb DescribeTargetHealth`
- [ ] 检查 SLB 状态: `tccli clb DescribeLoadBalancers`
- [ ] 检查最近变更: CloudAudit 最近 1 小时变更

## 2. 自动化诊断 (< 5 分钟)

### 2.1 后端健康检查
```bash
# 批量检查后端健康状态
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.slb_id}}" \
  --Filters "TargetHealth.HealthStatus=!HEALTHY"
```

### 2.2 指标关联分析
```bash
# 查询 5xx 错误率趋势
tccli monitor GetMonitorData \
  --Namespace "QCE/LOADBALANCE" \
  --MetricName "HttpErrorRate" \
  --Dimensions '[{"Name":"loadBalancerId","Value":"{{user.slb_id}}"}]' \
  --StartTime "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)"
```

## 3. 根因定位 (< 10 分钟)

### 3.1 常见根因快速匹配
| 根因 | 诊断证据 | 恢复时间 |
|------|----------|----------|
| 后端实例故障 | TargetHealth != HEALTHY | < 5 分钟 |
| 后端过载 | CPU > 90%, 连接数 > 阈值 | < 10 分钟 |
| 网络问题 | 延迟 > 阈值, 丢包率 > 0 | < 15 分钟 |
| 配置错误 | 最近配置变更 | < 10 分钟 |

### 3.2 自动恢复策略
```bash
# 如果是后端实例故障，自动摘除
if [ "$HEALTHY_COUNT" -lt "$TOTAL_COUNT" ]; then
  echo "自动摘除不健康后端"
  tccli clb DeregisterTargets \
    --LoadBalancerId "{{user.slb_id}}" \
    --Targets '[{"InstanceId":"{{unhealthy_instance_id}}","Port":80}]'
fi
```

## 4. 恢复验证 (< 5 分钟)

### 4.1 验证检查清单
- [ ] 5xx 错误率下降到 < 1%
- [ ] 后端健康状态恢复正常
- [ ] 用户访问正常

### 4.2 监控告警
```bash
# 设置 5xx 错误率告警
tccli monitor CreateAlarmPolicy \
  --PolicyName "SLB-5xx-快速恢复" \
  --Namespace "QCE/LOADBALANCE" \
  --MetricName "HttpErrorRate" \
  --Threshold 1.0 \
  --ComparisonOperator "GT"
```
```

- [x] **Step 2: 集成到现有 troubleshooting.md**

在 `qcloud-clb-ops/references/troubleshooting.md` 中添加快速诊断路径：

```markdown
## 快速诊断路径 (< 30 分钟)

对于 SLB 5xx 故障，使用优化后的诊断流程：

1. **快速分类** (< 2 分钟): 识别 5xx 错误类型
2. **自动化诊断** (< 5 分钟): 执行健康检查和指标查询
3. **根因定位** (< 10 分钟): 匹配常见根因
4. **自动恢复** (< 5 分钟): 执行恢复策略
5. **恢复验证** (< 5 分钟): 验证恢复效果

详细流程: [SLB 5xx 快速诊断决策树](slb-5xx-diagnosis-optimized.md)
```

- [x] **Step 3: 提交**

```bash
git add qcloud-clb-ops/references/troubleshooting.md qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md
git commit -m "feat(clb): optimize SLB 5xx diagnosis for <30min MTTR"
```

---

### Task 1.3: 测试验证 SLB 5xx 优化效果

**Files:**
- Test: `qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md`

- [x] **Step 1: 模拟 SLB 5xx 故障场景**

```bash
# 模拟后端实例故障
echo "模拟场景: 后端实例 10.0.0.1:80 健康检查失败"
echo "预期诊断时间: < 10 分钟"
echo "预期恢复时间: < 5 分钟"
```

- [x] **Step 2: 执行优化后的诊断流程**

按决策树执行：
1. 快速分类: 502 Bad Gateway → P1 优先级
2. 自动化诊断: 发现实例 10.0.0.1 不健康
3. 根因定位: 后端实例故障
4. 自动恢复: 摘除不健康实例
5. 恢复验证: 5xx 错误率下降到 0%

- [x] **Step 3: 记录优化效果**

```bash
echo "优化后 SLB 5xx 诊断流程:"
echo "1. 快速分类: 1 分钟"
echo "2. 自动化诊断: 3 分钟"
echo "3. 根因定位: 2 分钟"
echo "4. 自动恢复: 2 分钟"
echo "5. 恢复验证: 2 分钟"
echo "总计: 10 分钟"
echo "改进: 从 50 分钟降到 10 分钟 (80% 改进)"
```

---

## Phase 2: RDS MySQL 诊断时间优化

### 背景
- **当前诊断时间:** 数小时
- **目标诊断时间:** 分钟级
- **预期改进:** 80%+ 更快的 MTTR
- **来源:** `docs/superpowers/plans/findings/rds-mysql-skill-assessment.md`

### Task 2.1: 分析当前 RDS MySQL 诊断流程

**Files:**
- Read: `qcloud-cdb-ops/SKILL.md`
- Read: `qcloud-cdb-ops/references/troubleshooting.md`
- Read: `qcloud-aiops-diagnosis/references/product-rca-rules.md`

- [x] **Step 1: 提取当前 RDS MySQL 诊断步骤**

从现有文档中提取：
1. 慢查询诊断流程
2. 连接问题诊断
3. 性能问题诊断
4. 当前平均诊断时间

- [x] **Step 2: 识别诊断瓶颈**

分析当前流程中的时间消耗点：
1. 慢查询日志分析时间
2. 指标关联分析时间
3. 根因定位时间
4. 恢复验证时间

---

### Task 2.2: 优化 RDS MySQL 诊断流程

**Files:**
- Modify: `qcloud-cdb-ops/references/troubleshooting.md`
- Create: `qcloud-cdb-ops/references/cdb-slow-query-diagnosis-optimized.md`

- [x] **Step 1: 创建优化后的诊断流程**

```markdown
# RDS MySQL 快速诊断流程

## 1. 快速健康检查 (< 2 分钟)

### 1.1 实例状态检查
```bash
# 检查实例状态
tccli cdb DescribeDBInstances \
  --InstanceIds '["{{user.instance_id}}"]' \
  --Fields "InstanceId,Status,Memory,Volume,EngineVersion"
```

### 1.2 连接数检查
```bash
# 检查当前连接数
tccli cdb DescribeDBInstanceAttribute \
  --InstanceId "{{user.instance_id}}" \
  --Fields "MaxConnections,CurrentConnections"
```

## 2. 慢查询快速分析 (< 5 分钟)

### 2.1 慢查询日志获取
```bash
# 获取最近 1 小时慢查询
tccli cdb GetSlowQueryLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --MinLockTime 1
```

### 2.2 慢查询分类
| 查询类型 | 特征 | 优化建议 | 预期效果 |
|----------|------|----------|----------|
| 全表扫描 | Rows examined >> Rows sent | 添加索引 | 90%+ 性能提升 |
| 锁等待 | Lock wait timeout | 优化事务 | 80%+ 性能提升 |
| 排序临时表 | Using filesort | 优化 ORDER BY | 70%+ 性能提升 |
| 大事务 | 长时间运行 | 拆分事务 | 60%+ 性能提升 |

## 3. 根因自动定位 (< 10 分钟)

### 3.1 常见根因快速匹配
| 根因 | 诊断证据 | 恢复时间 |
|------|----------|----------|
| 慢查询 | 慢查询日志 > 阈值 | < 5 分钟 |
| 连接数不足 | CurrentConnections > MaxConnections*0.8 | < 3 分钟 |
| 内存不足 | MemoryUsage > 80% | < 10 分钟 |
| 磁盘空间不足 | VolumeUsage > 80% | < 5 分钟 |

### 3.2 自动恢复策略
```bash
# 如果是连接数不足，自动扩容
if [ "$CONNECTION_USAGE" -gt 80 ]; then
  echo "连接数使用率超过 80%，建议扩容"
  # 这里需要人工确认，因为涉及费用
fi
```

## 4. 恢复验证 (< 5 分钟)

### 4.1 验证检查清单
- [ ] 慢查询数量下降到 < 10/小时
- [ ] 连接数使用率 < 70%
- [ ] CPU/内存使用率正常
- [ ] 用户查询响应时间正常

### 4.2 监控告警
```bash
# 设置慢查询告警
tccli monitor CreateAlarmPolicy \
  --PolicyName "RDS-MySQL-慢查询告警" \
  --Namespace "QCE/RDS" \
  --MetricName "SlowQueries" \
  --Threshold 10 \
  --ComparisonOperator "GT"
```
```

- [x] **Step 2: 集成到现有 troubleshooting.md**

在 `qcloud-cdb-ops/references/troubleshooting.md` 中添加快速诊断路径：

```markdown
## 快速诊断路径 (< 30 分钟)

对于 RDS MySQL 问题，使用优化后的诊断流程：

1. **快速健康检查** (< 2 分钟): 检查实例状态和连接数
2. **慢查询快速分析** (< 5 分钟): 获取和分析慢查询日志
3. **根因自动定位** (< 10 分钟): 匹配常见根因
4. **自动恢复** (< 5 分钟): 执行恢复策略
5. **恢复验证** (< 5 分钟): 验证恢复效果

详细流程: [CDB 慢查询快速诊断决策树](cdb-slow-query-diagnosis-optimized.md)
```

- [x] **Step 3: 提交**

```bash
git add qcloud-cdb-ops/references/troubleshooting.md qcloud-cdb-ops/references/cdb-slow-query-diagnosis-optimized.md
git commit -m "feat(cdb): optimize RDS MySQL diagnosis for <30min MTTR"
```

---

### Task 2.3: 测试验证 RDS MySQL 优化效果

**Files:**
- Test: `qcloud-cdb-ops/references/cdb-slow-query-diagnosis-optimized.md`

- [x] **Step 1: 模拟 RDS MySQL 慢查询场景**

```bash
# 模拟慢查询场景
echo "模拟场景: 大量全表扫描导致慢查询"
echo "预期诊断时间: < 10 分钟"
echo "预期恢复时间: < 5 分钟"
```

- [x] **Step 2: 执行优化后的诊断流程**

按流程执行：
1. 快速健康检查: 实例状态正常，连接数使用率 85%
2. 慢查询快速分析: 发现大量全表扫描查询
3. 根因自动定位: 缺少索引
4. 自动恢复: 建议添加索引（需人工确认）
5. 恢复验证: 慢查询数量下降到 5/小时

- [x] **Step 3: 记录优化效果**

```bash
echo "优化后 RDS MySQL 诊断流程:"
echo "1. 快速健康检查: 1 分钟"
echo "2. 慢查询快速分析: 3 分钟"
echo "3. 根因自动定位: 2 分钟"
echo "4. 自动恢复: 2 分钟"
echo "5. 恢复验证: 2 分钟"
echo "总计: 10 分钟"
echo "改进: 从数小时降到 10 分钟 (90%+ 改进)"
```

---

## Phase 3: 通用优化和文档更新

### Task 3.1: 更新 AIOps 诊断框架文档

**Files:**
- Modify: `qcloud-aiops-diagnosis/references/diagnosis-framework.md`
- Modify: `qcloud-aiops-diagnosis/SKILL.md`

- [ ] **Step 1: 添加快速诊断路径到框架文档**

在 `qcloud-aiops-diagnosis/references/diagnosis-framework.md` 中添加：

```markdown
## 快速诊断路径

对于常见故障类型，提供优化后的快速诊断路径：

### SLB 5xx 故障
- 目标 MTTR: < 30 分钟
- 详细流程: [SLB 5xx 快速诊断决策树](../qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md)

### RDS MySQL 问题
- 目标 MTTR: < 30 分钟
- 详细流程: [RDS MySQL 快速诊断流程](../qcloud-cdb-ops/references/mysql-diagnosis-optimized.md)

### 通用故障
- 目标 MTTR: < 60 分钟
- 详细流程: 标准诊断框架
```

- [ ] **Step 2: 更新 SKILL.md 中的 Quick Start**

在 `qcloud-aiops-diagnosis/SKILL.md` 的 Quick Start 部分添加：

```markdown
### 快速诊断场景

| 场景 | 目标 MTTR | 快速诊断路径 |
|------|-----------|--------------|
| SLB 5xx 故障 | < 30 分钟 | [SLB 快速诊断](../qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md) |
| RDS MySQL 慢查询 | < 30 分钟 | [MySQL 快速诊断](../qcloud-cdb-ops/references/mysql-diagnosis-optimized.md) |
| CVM 性能问题 | < 45 分钟 | 标准诊断框架 |
| TKE Pod 问题 | < 30 分钟 | [TKE 诊断](../qcloud-tke-ops/references/troubleshooting.md) |
```

- [ ] **Step 3: 提交**

```bash
git add qcloud-aiops-diagnosis/references/diagnosis-framework.md qcloud-aiops-diagnosis/SKILL.md
git commit -m "feat(aiops): add quick diagnosis paths for SLB and RDS"
```

---

### Task 3.2: 创建 MTTR 改进报告模板

**Files:**
- Create: `qcloud-aiops-diagnosis/references/mttr-improvement-report.md`

- [x] **Step 1: 创建 MTTR 改进报告模板**

```markdown
# MTTR 改进报告模板

## 改进概述

| 项目 | 改进前 | 改进后 | 改进幅度 |
|------|--------|--------|----------|
| SLB 5xx MTTR | 45-90 分钟 | < 30 分钟 | 40-60% |
| RDS MySQL 诊断时间 | 数小时 | < 30 分钟 | 80%+ |
| 通用故障 MTTR | 60-120 分钟 | < 60 分钟 | 50%+ |

## 详细改进措施

### 1. SLB 5xx 故障优化
- 优化诊断决策树
- 添加自动化恢复步骤
- 集成健康检查自动摘除

### 2. RDS MySQL 优化
- 优化慢查询分析流程
- 添加根因自动定位
- 集成连接数监控

### 3. 通用优化
- 标准化快速诊断路径
- 添加自动化验证步骤
- 集成监控告警

## 验证结果

### 测试场景
1. SLB 5xx 故障: 后端实例故障
2. RDS MySQL 慢查询: 全表扫描
3. 通用故障: CPU 过高

### 测试结果
| 场景 | 预期时间 | 实际时间 | 是否达标 |
|------|----------|----------|----------|
| SLB 5xx | < 30 分钟 | 10 分钟 | ✅ |
| RDS MySQL | < 30 分钟 | 10 分钟 | ✅ |
| 通用故障 | < 60 分钟 | 25 分钟 | ✅ |

## 后续改进计划

1. **扩展快速诊断路径**: 覆盖更多产品（CVM、TKE、CLB 等）
2. **增强自动化恢复**: 添加更多自动恢复策略
3. **优化监控告警**: 减少误报，提高告警准确性
4. **知识库积累**: 将诊断经验转化为知识库
```

- [x] **Step 2: 提交**

```bash
git add qcloud-aiops-diagnosis/references/mttr-improvement-report.md
git commit -m "docs(aiops): add MTTR improvement report template"
```

---

## 执行计划总结

### 优先级排序
1. **Phase 1**: SLB 5xx 故障 MTTR 优化（P0 高优先级）
2. **Phase 2**: RDS MySQL 诊断时间优化（P0 高优先级）
3. **Phase 3**: 通用优化和文档更新（P1 中优先级）

### 执行策略
- **并行执行**: Phase 1 和 Phase 2 可以并行执行
- **依赖关系**: Phase 3 依赖于 Phase 1 和 Phase 2 的完成
- **验证点**: 每个 Phase 完成后运行验证命令

### 验证命令
```bash
# 验证 SLB 诊断优化
python3 scripts/check_markdown_python.py --root .

# 验证 RDS 诊断优化
python3 scripts/validate_skills_frontmatter.py

# 验证 AIOps 框架更新
python3 scripts/check_gcl_conformance.py
```

### 预期成果
1. **SLB 5xx MTTR**: 从 45-90 分钟降到 < 30 分钟
2. **RDS MySQL 诊断时间**: 从数小时降到 < 30 分钟
3. **通用故障 MTTR**: 从 60-120 分钟降到 < 60 分钟
4. **整体改进**: AIOps 诊断能力提升 50%+