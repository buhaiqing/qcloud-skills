# 7×24 值班交接检查清单

> 每次值班交接时执行，确保接班人员掌握当前系统健康状况。

## 前置检查（接班前 15 分钟）

1. 确认当前值班时段（日/夜/周末）
2. 确认告警通道可用（企业微信/短信/电话）
3. 确认以下工具有访问权限：
   - [ ] 腾讯云控制台（主账号 + 子账号）
   - [ ] 日志平台（CLS）
   - [ ] 监控告警平台（Monitor）
   - [ ] 内部值班群

## 系统健康摘要（必查）

| 检查项 | 命令 | 预期 | 异常处理 |
|--------|------|------|----------|
| 未恢复告警 | `tccli monitor DescribeAlarmHistory` | ≤ 5 条未恢复 | 逐条确认处理人 |
| P0 故障 | 检查内部值班群 / AIOps 诊断记录 | 无未关闭 P0 | 立即升级 |
| 资源水位 | CPU/内存/磁盘 > 80% 的资源列表 | 无持续高水位 | 记录到交接单 |
| 上周变更 | 检查 CloudAudit / 变更记录 | 无未验证变更 | 确认变更后 48h 监控指标 |
| 证书到期 | `tccli ssl DescribeCertificates` | 30 天内无到期 | 排期续期 |
| 余额预警 | `tccli billing DescribeAccountBalance` | 余额 > 阈值 | 通知财务充值 |

## 交接记录模板

```json
{
  "handover_time": "{{user.handover_time}}",
  "from": "{{user.from_person}}",
  "to": "{{user.to_person}}",
  "ongoing_incidents": [
    {
      "id": "INC-xxx",
      "status": "处理中",
      "owner": "姓名",
      "eta": "预计恢复时间"
    }
  ],
  "unresolved_alarms": [],
  "pending_changes": [],
  "health_summary": {
    "status": "GREEN / YELLOW / RED",
    "critical_count": 0,
    "warning_count": 0,
    "info_count": 0
  }
}
```

## 失败场景

| 场景 | 处理方式 |
|------|----------|
| 接班人员 15 分钟未到岗 | 通知值班主管 |
| 关键告警通道不可用 | 切换备用通道，通知运维负责人 |
| 发现未记录的 P0 故障 | 立即启动应急响应，通知 SRE 团队 |
