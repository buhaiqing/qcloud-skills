# 故障排查速查表

> 本文件由 `SKILL.md` 引用。常见问题诊断与解决方案。

## 1. 凭证与权限

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| `AuthFailure.SignatureFailure` | SecretKey 错或签名算法不匹配 | 检查环境变量；升级 tccli 到最新版 |
| `AuthFailure.InvalidSecretId` | SecretID 被禁用/删除 | CAM 控制台确认状态 |
| `AuthFailure.SignatureExpired` | 客户端时间偏差 | 同步系统时间 `ntpdate time1.cloud.tencent.com` |
| `UnauthorizedOperation` | 策略不足 | 见 `setup-and-permissions.md` §2 |
| `InvalidCredential` | 凭证链配置错 | 检查 `~/.tencentcloud/credentials` |
| 配置文件加载失败 | YAML 语法错 | `python -c "import yaml; yaml.safe_load(open('config.yaml'))"` |

## 2. 参数错误

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| `InvalidParameter.Month` | 月份格式错 | 用 `YYYY-MM` 格式 |
| `InvalidParameter.Offset` | Offset 越界 | 重新计算分页 |
| `InvalidParameter.Limit` | Limit 过大 | 最大 1000 |
| `MissingParameter` | 缺少必填参数 | 对照 `references/billing-api-mapping.md` |
| `InvalidParameter.ResourceId` | 资源 ID 格式错 | 复制控制台原值 |

## 3. 数据问题

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| 账单数据缺失 | 子账号未授权 | 追加 `QcloudBillingReadOnlyAccess` |
| 账单数据延迟 | 实时账单 vs 结算账单 | 数据延迟 1-2 天是正常 |
| 金额合计对不上 | 含代金券/资源包/退费 | 用控制台"结算账单"为基准 |
| Tag 数据为空 | 资源未打 Tag | 用 `tccli tag GetResources` 确认 |
| 资源包未列出 | 资源包已过期 | 仅 `Status="active"` 才显示 |
| 订单状态不对 | 状态机时差 | 等待 1-2 分钟重试 |

## 4. 性能与限流

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| `RequestLimitExceeded` | 账号级 QPS 限流 | 降低并发 + 退避 |
| `LimitExceeded.Frequency` | 接口级 QPS 限流 | 详见 `billing-api-mapping.md` §8 |
| 超时 | 数据量大 | 分页 + 缓存 + 异步 |
| 内存溢出 | 一次拉全量 | 分批拉取，写入 COS |
| 重复扣费 | 重试未做幂等 | 加 `RequestId` 幂等控制 |

## 5. CLI 兜底（tccli 字段不全）

| 现象 | 解决方案 |
|---|---|
| tccli 报 `Unknown option` | 升级 tccli 或改用 Python SDK |
| 复杂 JSON 参数 | 改用 `--cli-input-json` 传文件 |
| 嵌套结构 | 改用 Python SDK |

**Python SDK 模板** → `references/sdk-usage.md`

## 6. 联动 Skill 失败

| 现象 | 解决方案 |
|---|---|
| `qcloud-monitor-ops` 拉不到指标 | 确认监控命名空间（如 `QCE/CVM`） |
| `qcloud-cvm-ops` 返错 | 确认实例 ID 在本账号下 |
| `qcloud-proactive-inspection` 不触发 | 确认置信度 = HIGH 才自动派发 |
| `qcloud-aiops-diagnosis` 协同失败 | 单独调用各产品 skill 排查 |

## 7. 异常检测相关

| 现象 | 解决方案 |
|---|---|
| 误报率太高 | 调高阈值（ii: 20% → 30%） |
| 漏报 | 调低阈值 + 启用 i 维度（同期对比） |
| 月初数据不全 | 用上月底数据做基线 |
| 业务季节性强 | 用去年同期做基线（i 维度） |
| 业务快速增长期 | 调高增长率系数（× 1.3） |

## 8. 报告生成失败

| 现象 | 解决方案 |
|---|---|
| Markdown 中文乱码 | 文件存为 UTF-8 |
| CSV Excel 打开乱码 | 加 BOM `\ufeff` 前缀 |
| 图表无法生成 | 改用 Markdown 表格（不依赖图表库） |
| 邮件发送失败 | 委托 `qcloud-monitor-ops` 走告警通道 |

## 9. 紧急情况

### 9.1 凭证泄露

```
1. 立即在 CAM 控制台禁用 SecretID
2. 删除 API 密钥
3. 审计 CloudAudit 日志，确认泄露期间是否有异常调用
4. 创建新密钥，更新配置
5. 通知团队 + 财务
```

### 9.2 账单暴增

```
1. 立即拉本月账单明细
2. 按产品排序，识别 Top 5
3. 对 Top 产品 delegate 到产品 skill
4. 排查是否有：
   - 未授权的访问（CAM 审计）
   - 异常资源创建（资源审计）
   - DDoS/CC 攻击（安全 skill）
5. 必要时：冻结账号、删除异常资源
```

### 9.3 误执行优化操作

```
1. 通过 CloudAudit 找到操作记录
2. 评估影响范围
3. 回滚操作（重建资源、恢复数据）
4. 流程改进：
   - 所有优化建议必须人工审批
   - 关键操作走工单系统
   - 定期 review 自动化脚本
```

## 10. 日志与诊断

### 10.1 启用调试

```bash
# tccli 调试模式
tccli --debug billing DescribeBillList --Month "2026-05"

# Python SDK 调试
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 10.2 关键日志位置

- tccli 日志：`~/.tencentcloud/log/`
- Python SDK 日志：标准 logging
- 腾讯云审计：`CloudAudit` 控制台

### 10.3 诊断信息收集

遇到问题提交工单时，请提供：
1. tccli 版本 + Python SDK 版本
2. 完整错误码 + 错误信息
3. 请求时间 + 请求 ID
4. SecretID（脱敏）+ 账号 ID
5. 配置文件（脱敏）
6. 复现步骤

详细 API 错误码 → `references/api-cross-check.md`。
