# CDB 慢查询快速诊断 — 优化版 Runbook

> **目标:** 将慢查询诊断的 MTTD 从 1-2 小时降低到 5 分钟以内，MTTR 从 3-4 小时降低到 30 分钟以内。

> **安全:** 禁止在 Agent 输出中记录或暴露 IP 地址、实例 ID 或凭据。所有敏感标识符使用 `<masked>` 遮盖。

> **跨平台日期:** macOS 和 Linux 的 date 命令不同。使用以下跨平台辅助函数：
> ```bash
> # 跨平台：计算 N 分钟前的时间戳
> date_minus_minutes() {
>   local mins=$1
>   if date -v-"${mins}"M +%s >/dev/null 2>&1; then
>     date -u -v-"${mins}"M +%Y-%m-%dT%H:%M:%S+00:00  # macOS
>   else
>     date -u -d "-${mins} minutes" +%Y-%m-%dT%H:%M:%S+00:00  # Linux
>   fi
> }
> ```

> **工具依赖:** 以下所有 `jq` 命令需要 `jq` 已安装。使用前验证：
> ```bash
> command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq not installed — install via: brew install jq / apt install jq"; exit 1; }
> ```

## 时间指标

| 指标 | 基线 | 目标 | 测量方式 |
|------|------|------|----------|
| **MTTD** (平均检测时间) | 1-2 小时 | < 2 分钟 | 告警触发 → Agent 开始诊断 |
| **MTTI** (平均识别时间) | 30-60 分钟 | < 5 分钟 | Agent 开始 → 根因定位 |
| **MTTR** (平均恢复时间) | 3-4 小时 | < 30 分钟 | 告警触发 → 服务恢复 |

---

## 阶段 1：快速分类 (< 2 分钟)

**触发条件:** 用户报告慢查询、CPU 高、应用超时，或监控告警触发。

**目标:** 在 2 分钟内完成慢查询类型分类。

### 步骤 1：确认慢查询存在

```bash
# 检查最近 1 小时的慢查询（按查询时间降序）
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 10 \
  --OrderBy "QueryTime" \
  --Order "DESC"
```

### 步骤 2：获取实例资源指标（并行）

```bash
# CPU 使用率（最近 1 小时）
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "CpuUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"

# 连接数（最近 1 小时）
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "ConnectionUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### 步骤 3：检查慢查询日志配置

```bash
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["slow_query_log","long_query_time","log_queries_not_using_indexes"]'
```

### 快速分类决策矩阵

| 条件 | 类型 | 下一阶段 |
|------|------|----------|
| 存在 QueryTime > 10s 的查询 | **Type A: 超长查询** | 阶段 2A |
| CPU > 80% 且平均 QueryTime > 3s | **Type B: 资源瓶颈** | 阶段 2B |
| LockTime/QueryTime 平均比 > 50% | **Type C: 锁等待** | 阶段 2C |
| QueryTime 在 1-10s 之间但无其他异常 | **Type D: 查询优化** | 阶段 2D |
| 慢查询日志未开启 | **配置缺失** | 阶段 2E |

---

## 阶段 2A：超长查询诊断 (Type A)

**时间预算:** < 5 分钟

**特征:** 单个查询执行时间 > 10s，通常导致应用超时和连接堆积。

### 步骤 1：获取超长查询详情

```bash
# 获取 TOP 5 慢查询详情
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"
```

### 步骤 2：检查当前运行中的查询

```bash
# 通过 SQL 查询当前运行线程（需 mysql 客户端访问）
# 如果没有直接访问权限，检查实例参数获取线程相关信息
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["thread_cache_size","max_connections"]'
```

### 常见根因及修复

| 根因 | 证据 | 修复 |
|------|------|------|
| 缺少索引导致全表扫描 | 慢查询中有 `Using filesort` 或 `Using where` 但无索引 | 添加合适的索引 |
| 大表全扫描 | 表行数超过千万级别且查询无 WHERE 条件 | 添加 WHERE 条件限制范围 |
| 笛卡尔积连接 | 多个表连接但缺少连接条件 | 修复 SQL 添加 JOIN 条件 |
| 数据倾斜导致排序 | 大数据量 `ORDER BY` + `LIMIT` 无索引 | 添加覆盖索引 |
| 函数导致索引失效 | WHERE 条件中使用函数（`DATE()`、`YEAR()` 等） | 改写为范围查询 |

### 自动化恢复

```bash
# 紧急终止超长查询（需要 mysql 客户端访问）
# 从慢查询日志中获取 ThreadId，然后执行：
CALL mysql.rds_kill(<thread_id>);

# 或者修改 long_query_time 临时降低阈值以捕获更多信息
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[{"Name":"long_query_time","CurrentValue":"2"}]'
```

---

## 阶段 2B：资源瓶颈诊断 (Type B)

**时间预算:** < 8 分钟

**特征:** CPU > 80%，并发查询量大，平均响应时间升高。

### 步骤 1：分析资源指标趋势

```bash
# CPU 使用率趋势（最近 2 小时）
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "CpuUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 300 \
  --StartTime "$(date_minus_minutes 120)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"

# IOPS 使用率
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "IopsUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 300 \
  --StartTime "$(date_minus_minutes 120)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### 步骤 2：检查慢查询并发数

```bash
# 查看慢查询日志中的并发模式
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 120)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 50 \
  --OrderBy "QueryTime" \
  --Order "DESC" \
  | jq '.Response.SlowLogData[].Timestamp'
```

### 常见根因及修复

| 根因 | 证据 | 修复 |
|------|------|------|
| 实例规格不足 | CPU > 80% 持续 30 分钟以上 | 升级实例规格（`UpgradeDBInstance`） |
| 大量慢查询并发 | 同一时间段内大量慢查询 | 终止部分查询；优化最耗时的几个 |
| 缓存命中率低 | `QPS` 高但 `CacheHitRate` 低 | 调整 `innodb_buffer_pool_size` |
| 写压力过大 | IOPS 使用率持续 > 80% | 考虑读写分离或升级实例 |

### 自动化恢复

```bash
# 参数调优 - 临时增加 buffer pool 大小
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[{"Name":"innodb_buffer_pool_size","CurrentValue":"{{user.new_buffer_pool_size}}"}]'

# 规格升级 - 长期解决方案
tccli cdb UpgradeDBInstance \
  --InstanceId "{{user.instance_id}}" \
  --Memory "{{user.new_memory}}" \
  --Volume "{{user.new_volume}}"
```

---

## 阶段 2C：锁等待诊断 (Type C)

**时间预算:** < 5 分钟

**特征:** LockTime/QueryTime > 50%，查询大部分时间在等待锁。

### 步骤 1：分析锁等待

```bash
# 检查是否有长时间锁等待（通过 MySQL 连接）
# 获取当前锁等待信息
SELECT * FROM information_schema.INNODB_TRX\G
SELECT * FROM information_schema.INNODB_LOCKS\G
SELECT * FROM information_schema.INNODB_LOCK_WAITS\G

# 或通过实例参数间接判断
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["innodb_lock_wait_timeout","innodb_deadlock_detect"]'
```

### 步骤 2：检查事务和连接

```bash
# 获取当前连接数
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "ConnectionUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 5)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### 常见根因及修复

| 根因 | 证据 | 修复 |
|------|------|------|
| 长事务未提交 | 同一行锁被持有超过 30s | 终止长事务 |
| 死锁 | 应用报死锁错误 | 调整应用 SQL 顺序；启用死锁检测 |
| 间隙锁 | 范围查询导致的间隙锁 | 降低隔离级别或使用等值条件 |
| DDL 阻塞 | `ALTER TABLE` 等待元数据锁 | 在低峰期执行 DDL |

### 自动化恢复

```bash
# 终止阻塞事务（需要 mysql 客户端）
# 从 INNODB_TRX 获取 trx_mysql_thread_id
CALL mysql.rds_kill(<trx_mysql_thread_id>);

# 调整锁超时时间
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[{"Name":"innodb_lock_wait_timeout","CurrentValue":"50"}]'
```

---

## 阶段 2D：查询优化诊断 (Type D)

**时间预算:** < 5 分钟

**特征:** QueryTime 1-10s，无锁等待，CPU 和内存正常。

### 步骤 1：分析查询模式

```bash
# 获取慢查询详情，关注 SQL 模板
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 20 \
  --OrderBy "QueryTime" \
  --Order "DESC" \
  | jq '.Response.SlowLogData[] | {sql: .Sql, queryTime: .QueryTime, lockTime: .LockTime, rowsExamined: .RowsExamined, rowsSent: .RowsSent}'
```

### 步骤 2：分析查询效率

```bash
# 检查 rows_examined / rows_sent 比例
# 如果 rows_examined >> rows_sent，说明扫描了大量数据
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 60)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 20 \
  --OrderBy "QueryTime" \
  --Order "DESC" \
  | jq '[.Response.SlowLogData[] | {ratio: (.RowsExamined / .RowsSent), rowsExamined: .RowsExamined, rowsSent: .RowsSent}]'
```

### 常见根因及修复

| 根因 | 证据 | 修复 |
|------|------|------|
| 缺少索引 | `rows_examined` >> `rows_sent` | 添加合适索引 |
| 索引选择性差 | 扫描大量行但返回少量结果 | 创建复合索引 |
| 查询未使用最优索引 | `EXPLAIN` 显示 `type: index` 或 `ALL` | `FORCE INDEX` 或优化 SQL |
| 子查询效率低 | 慢查询中包含子查询 | 改写为 JOIN |
| OR 条件导致全表扫描 | WHERE 中包含多个 OR 条件 | 改写为 UNION 或 IN |

### 自动化恢复

```bash
# 添加索引（需要 mysql 客户端访问）
CREATE INDEX idx_<column> ON <table>(<column>);

# 或通过 SQL 分析后建议索引
# 使用 EXPLAIN 验证索引效果
EXPLAIN SELECT ...;
```

---

## 阶段 2E：配置缺失诊断 (Type E)

**时间预算:** < 2 分钟

**特征:** 慢查询日志未开启或阈值过高，导致无法捕获问题查询。

### 步骤 1：检查慢查询配置

```bash
# 检查慢查询相关参数
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["slow_query_log","long_query_time","log_queries_not_using_indexes","log_slow_admin_statements"]'
```

### 自动化恢复

```bash
# 开启慢查询日志并设置合理阈值
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[
    {"Name":"slow_query_log","CurrentValue":"ON"},
    {"Name":"long_query_time","CurrentValue":"2"},
    {"Name":"log_queries_not_using_indexes","CurrentValue":"ON"}
  ]'
```

---

## 阶段 3：恢复验证 (< 5 分钟)

应用修复后，验证恢复效果：

### 步骤 1：检查慢查询是否减少

```bash
# 等待 5 分钟后检查
sleep 300

# 检查最近 5 分钟的慢查询
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date_minus_minutes 5)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"
```

### 步骤 2：验证资源使用率下降

```bash
# 验证 CPU 使用率
tccli monitor GetMonitorData \
  --Namespace "QCE/CDB" \
  --MetricName "CpuUseRate" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"{{user.instance_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 10)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### 步骤 3：验证应用端到端可用性

```bash
# 检查实例状态和连接数
tccli cdb DescribeDBInstances \
  --InstanceIds '["{{user.instance_id}}"]' \
  | jq '.Response.Items[0] | {Status, Memory, Volume, Vip, Vport, EngineVersion}'
# 期望: Status=1 (running), 连接数正常
```

---

## 阶段 4：事后处理

### 1. 记录根因

记录以下信息：
- 慢查询类型 (Type A/B/C/D/E)
- 根因类别 (索引/锁/资源/配置)
- 检测 → 识别 → 恢复的时间
- 应用的修复措施
- 慢查询 SQL 模板（脱敏后）

### 2. 防止复发

| 类别 | 预防措施 |
|------|----------|
| 索引缺失 | 添加慢查询监控告警；定期 review 慢查询日志 |
| 锁等待 | 应用层优化事务逻辑；避免长事务 |
| 资源瓶颈 | 设置 CPU/连接数告警阈值；规划容量 |
| 配置缺失 | 新实例默认开启慢查询日志 |
| SQL 质量 | 代码审查中加入 SQL 性能检查 |

### 3. 更新告警阈值

基于本次事件调整：
- `CpuUseRate` 阈值（默认 > 80%）
- `ConnectionUseRate` 阈值（默认 > 80%）
- `SlowQueryCount` 阈值（每分钟慢查询数）

---

## 快速参考：决策树

```
慢查询检测
    │
    ├─ QueryTime > 10s?
    │   └─ YES → 阶段 2A (超长查询)
    │       ├─ 缺少索引 → 添加索引
    │       ├─ 全表扫描 → 添加 WHERE 条件
    │       ├─ 笛卡尔积 → 修复 JOIN
    │       ├─ 函数导致索引失效 → 改写查询
    │       └─ 紧急情况 → 终止查询
    │
    ├─ CPU > 80%?
    │   └─ YES → 阶段 2B (资源瓶颈)
    │       ├─ 实例规格不足 → 升级规格
    │       ├─ 缓存命中率低 → 调优 buffer pool
    │       ├─ 写压力过大 → 读写分离
    │       └─ 大量并发 → 终止部分查询
    │
    ├─ LockTime/QueryTime > 50%?
    │   └─ YES → 阶段 2C (锁等待)
    │       ├─ 长事务 → 终止事务
    │       ├─ 死锁 → 调整 SQL 顺序
    │       ├─ 间隙锁 → 降低隔离级别
    │       └─ DDL 阻塞 → 低峰期执行
    │
    ├─ QueryTime 1-10s 且资源正常?
    │   └─ YES → 阶段 2D (查询优化)
    │       ├─ 缺少索引 → 添加索引
    │       ├─ 子查询效率低 → 改写为 JOIN
    │       └─ OR 导致全表扫描 → 改写为 UNION
    │
    └─ 慢查询日志未开启?
        └─ YES → 阶段 2E (配置缺失)
            ├─ 开启 slow_query_log
            └─ 设置 long_query_time=2

修复后 → 阶段 3 (验证)
恢复后 → 阶段 4 (事后处理)
```

---

## 跨技能委托

| 诊断项 | 委托技能 | 上下文 |
|--------|----------|--------|
| 实例规格升级 | `qcloud-cdb-ops` (本技能) | `UpgradeDBInstance` |
| 监控告警配置 | `qcloud-monitor-ops` | 慢查询告警、CPU 告警阈值设置 |
| 网络/安全组 | `qcloud-vpc-ops` | 连接问题排查 |