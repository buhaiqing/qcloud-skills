# SLB 5xx 故障 MTTR 优化执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 SLB 5xx 故障诊断流程，将 MTTR 从 45-90 分钟降到 < 30 分钟

**Background:**
- **当前 MTTR:** 45-90 分钟（手动分析）
- **目标 MTTR:** < 30 分钟
- **预期改进:** 40-60%
- **来源:** `docs/superpowers/plans/findings/slb-skill-assessment.md`

**Architecture:** 在现有 `qcloud-clb-ops` skill 基础上，添加优化的 5xx 故障诊断决策树和自动化恢复步骤

**Tech Stack:** tccli CLI, Python 3.8+, Markdown runbooks

---

## Task 1: 创建 SLB 5xx 快速诊断文档

**Files:**
- Create: `qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md`

- [ ] **Step 1: 创建优化后的诊断决策树**

创建 `qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md`：

```markdown
# SLB 5xx 故障快速诊断决策树

> 目标 MTTR: < 30 分钟（相比当前 45-90 分钟改进 40-60%）

## 1. 快速分类 (< 2 分钟)

### 1.1 5xx 错误类型识别

| 错误码 | 可能原因 | 优先级 | 预期诊断时间 |
|--------|----------|--------|--------------|
| 502 Bad Gateway | 后端服务不可用/连接失败 | P1 | < 10 分钟 |
| 503 Service Unavailable | 后端过载/维护/限流 | P1 | < 10 分钟 |
| 504 Gateway Timeout | 后端响应超时 | P2 | < 15 分钟 |
| 5xx 其他 | 需要进一步分析 | P3 | < 20 分钟 |

### 1.2 快速检查清单

```bash
# 1. 检查后端健康状态
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.slb_id}}" \
  --Filters "TargetHealth.HealthStatus=!HEALTHY"

# 2. 检查 SLB 状态
tccli clb DescribeLoadBalancers \
  --LoadBalancerIds '["{{user.slb_id}}"]'

# 3. 检查最近变更（CloudAudit 最近 1 小时）
tccli cloudaudit DescribeEvents \
  --StartTime "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)"
```

## 2. 自动化诊断 (< 5 分钟)

### 2.1 后端健康检查

```bash
# 批量检查后端健康状态
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.slb_id}}" \
  --Filters "TargetHealth.HealthStatus=!HEALTHY"

# 解析不健康后端
# 输出: InstanceId, Port, HealthStatus, Reason
```

### 2.2 指标关联分析

```bash
# 查询 5xx 错误率趋势
tccli monitor GetMonitorData \
  --Namespace "QCE/LOADBALANCE" \
  --MetricName "HttpErrorRate" \
  --Dimensions '[{"Name":"loadBalancerId","Value":"{{user.slb_id}}"}]' \
  --StartTime "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --Period 60

# 查询活跃连接数
tccli monitor GetMonitorData \
  --Namespace "QCE/LOADBALANCE" \
  --MetricName "ActiveConnections" \
  --Dimensions '[{"Name":"loadBalancerId","Value":"{{user.slb_id}}"}]' \
  --StartTime "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --Period 60
```

## 3. 根因定位 (< 10 分钟)

### 3.1 常见根因快速匹配

| 根因 | 诊断证据 | 恢复时间 | 自动化程度 |
|------|----------|----------|------------|
| **后端实例故障** | TargetHealth != HEALTHY | < 5 分钟 | 可自动摘除 |
| **后端过载** | CPU > 90%, 连接数 > 阈值 | < 10 分钟 | 需扩容 |
| **网络问题** | 延迟 > 阈值, 丢包率 > 0 | < 15 分钟 | 需网络排查 |
| **配置错误** | 最近配置变更 | < 10 分钟 | 需回滚配置 |
| **证书问题** | HTTPS 证书过期/不匹配 | < 5 分钟 | 需更新证书 |

### 3.2 自动恢复策略

```bash
# 如果是后端实例故障，自动摘除不健康后端
UNHEALTHY_COUNT=$(tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.slb_id}}" \
  --Filters "TargetHealth.HealthStatus=!HEALTHY" | jq '.Response.Targets | length')

TOTAL_COUNT=$(tccli clb DescribeTargets \
  --LoadBalancerId "{{user.slb_id}}" | jq '.Response.Targets | length')

if [ "$UNHEALTHY_COUNT" -gt 0 ] && [ "$UNHEALTHY_COUNT" -lt "$TOTAL_COUNT" ]; then
  echo "发现 $UNHEALTHY_COUNT 个不健康后端，自动摘除"
  
  # 获取不健康后端列表
  UNHEALTHY_BACKENDS=$(tccli clb DescribeTargetHealth \
    --LoadBalancerId "{{user.slb_id}}" \
    --Filters "TargetHealth.HealthStatus=!HEALTHY" | \
    jq -r '.Response.Targets[] | {InstanceId: .InstanceId, Port: .Port}')
  
  # 摘除不健康后端
  for BACKEND in $UNHEALTHY_BACKENDS; do
    INSTANCE_ID=$(echo $BACKEND | jq -r '.InstanceId')
    PORT=$(echo $BACKEND | jq -r '.Port')
    
    tccli clb DeregisterTargets \
      --LoadBalancerId "{{user.slb_id}}" \
      --Targets "[{\"InstanceId\":\"$INSTANCE_ID\",\"Port\":$PORT}]"
    
    echo "已摘除后端: $INSTANCE_ID:$PORT"
  done
  
  echo "自动摘除完成，验证 5xx 错误率"
fi
```

## 4. 恢复验证 (< 5 分钟)

### 4.1 验证检查清单

- [ ] 5xx 错误率下降到 < 1%
- [ ] 后端健康状态恢复正常
- [ ] 用户访问正常
- [ ] 监控告警恢复

### 4.2 验证命令

```bash
# 验证 5xx 错误率
ERROR_RATE=$(tccli monitor GetMonitorData \
  --Namespace "QCE/LOADBALANCE" \
  --MetricName "HttpErrorRate" \
  --Dimensions '[{"Name":"loadBalancerId","Value":"{{user.slb_id}}"}]' \
  --StartTime "$(date -d '-5 minutes' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --Period 60 | jq '.Response.MetricDataSet[-1].Values[-1].Value')

if (( $(echo "$ERROR_RATE < 1.0" | bc -l) )); then
  echo "✅ 5xx 错误率已恢复正常: ${ERROR_RATE}%"
else
  echo "❌ 5xx 错误率仍偏高: ${ERROR_RATE}%，需要进一步排查"
fi
```

## 5. 时间指标记录

### 5.1 MTTR 记录

诊断完成后，记录时间指标：

| Field | Value | Source |
|-------|-------|--------|
| `incident_id` | {{output.incident_id}} | Generated at detection |
| `detected_at` | {{alarm.trigger_time}} | Monitor alarm |
| `diagnosis_at` | {{output.diagnosis_completed_at}} | This diagnosis |
| `resolved_at` | {{output.resolved_at}} | User confirmation |
| `product` | CLB | Diagnosis result |
| `severity` | {{alarm.severity}} | Monitor alarm |
| `root_cause` | {{output.root_cause.category}} | Diagnosis result |
| `mttd` | Minutes from detected_at to diagnosis_at | Auto-calculated |
| `mttr` | Minutes from detected_at to resolved_at | Auto-calculated |

### 5.2 改进效果跟踪

```sql
-- SLB 5xx MTTR 改进效果跟踪
SELECT
  date_trunc('week', detected_at) as week,
  COUNT(*) as incident_count,
  AVG(mttr) as avg_mttr,
  AVG(mttd) as avg_mttd,
  COUNT(CASE WHEN mttr < 30 THEN 1 END) * 100.0 / COUNT(*) as target_achieved_pct
FROM incidents
WHERE product = 'CLB'
  AND root_cause LIKE '%5xx%'
  AND detected_at >= NOW() - INTERVAL '12 weeks'
GROUP BY week
ORDER BY week;
```

---

## Task 2: 更新现有 troubleshooting.md

**Files:**
- Modify: `qcloud-clb-ops/references/troubleshooting.md`

- [ ] **Step 1: 在 troubleshooting.md 开头添加快速诊断路径**

在文件开头添加：

```markdown
## 快速诊断路径 (< 30 分钟)

对于 SLB 5xx 故障，使用优化后的诊断流程：

1. **快速分类** (< 2 分钟): 识别 5xx 错误类型
2. **自动化诊断** (< 5 分钟): 执行健康检查和指标查询
3. **根因定位** (< 10 分钟): 匹配常见根因
4. **自动恢复** (< 5 分钟): 执行恢复策略
5. **恢复验证** (< 5 分钟): 验证恢复效果

详细流程: [SLB 5xx 快速诊断决策树](slb-5xx-diagnosis-optimized.md)

---

## 常见问题和解决方案
```

- [ ] **Step 2: 添加 5xx 错误相关章节**

在 troubleshooting.md 中添加：

```markdown
### 5xx 错误（502/503/504）

**Symptom:** SLB 返回 5xx 错误码

**Diagnostic Steps:**
1. 检查后端健康状态
2. 查询 5xx 错误率趋势
3. 检查后端 CPU/内存使用率
4. 检查网络延迟和丢包率

**快速诊断:** 参考 [SLB 5xx 快速诊断决策树](slb-5xx-diagnosis-optimized.md)

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| 后端实例故障 | 摘除不健康后端，修复实例 |
| 后端过载 | 扩容或限流 |
| 网络问题 | 排查网络链路 |
| 配置错误 | 回滚配置 |
```

- [ ] **Step 3: 提交**

```bash
git add qcloud-clb-ops/references/troubleshooting.md qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md
git commit -m "feat(clb): optimize SLB 5xx diagnosis for <30min MTTR"
```

---

## Task 3: 更新 SKILL.md

**Files:**
- Modify: `qcloud-clb-ops/SKILL.md`

- [ ] **Step 1: 在 SKILL.md 的 Operations 部分添加快速诊断引用**

在 SKILL.md 的 Execution Flows 部分添加：

```markdown
### 快速诊断场景

| 场景 | 目标 MTTR | 快速诊断路径 |
|------|-----------|--------------|
| SLB 5xx 故障 | < 30 分钟 | [SLB 5xx 快速诊断决策树](references/slb-5xx-diagnosis-optimized.md) |
| 健康检查失败 | < 15 分钟 | [健康检查诊断](references/troubleshooting.md#health-check-failures) |
| 连接失败 | < 20 分钟 | [连接诊断](references/troubleshooting.md#connection-failures) |
```

- [ ] **Step 2: 提交**

```bash
git add qcloud-clb-ops/SKILL.md
git commit -m "docs(clb): add quick diagnosis paths to SKILL.md"
```

---

## Task 4: 测试验证

**Files:**
- Test: `qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md`

- [ ] **Step 1: 模拟 SLB 5xx 故障场景**

```bash
# 模拟后端实例故障
echo "模拟场景: 后端实例 10.0.0.1:80 健康检查失败"
echo "预期诊断时间: < 10 分钟"
echo "预期恢复时间: < 5 分钟"
```

- [ ] **Step 2: 执行优化后的诊断流程**

按决策树执行：
1. 快速分类: 502 Bad Gateway → P1 优先级
2. 自动化诊断: 发现实例 10.0.0.1 不健康
3. 根因定位: 后端实例故障
4. 自动恢复: 摘除不健康实例
5. 恢复验证: 5xx 错误率下降到 0%

- [ ] **Step 3: 记录优化效果**

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

- [ ] **Step 4: 运行验证命令**

```bash
# 验证 markdown 内容
python3 scripts/check_markdown_python.py --root .

# 验证 skill 结构
python3 scripts/validate_skills_frontmatter.py
```

---

## 执行计划总结

### 优先级排序
1. **Task 1**: 创建 SLB 5xx 快速诊断文档（核心）
2. **Task 2**: 更新现有 troubleshooting.md（集成）
3. **Task 3**: 更新 SKILL.md（文档）
4. **Task 4**: 测试验证（验证）

### 执行策略
- **顺序执行**: Task 1 → Task 2 → Task 3 → Task 4
- **验证点**: 每个 Task 完成后运行验证命令

### 预期成果
1. **SLB 5xx MTTR**: 从 45-90 分钟降到 < 30 分钟
2. **自动化程度**: 60% 的恢复步骤可自动化
3. **诊断效率**: 提升 40-60%

### 验证命令
```bash
# 验证 markdown 内容
python3 scripts/check_markdown_python.py --root .

# 验证 skill 结构
python3 scripts/validate_skills_frontmatter.py

# 验证 GCL 合规性
python3 scripts/check_gcl_conformance.py
```