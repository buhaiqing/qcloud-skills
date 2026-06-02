# 凭证与权限配置

> 本文件由 `SKILL.md` 引用。详细配置说明、最小权限策略、凭证轮换、安全建议等请查阅本文件。

## 1. 单账号配置（默认）

### 1.1 环境变量方式

```bash
export TENCENTCLOUD_SECRET_ID=AKIDxxxxxxxxxxxxxxxx
export TENCENTCLOUD_SECRET_KEY=xxxxxxxxxxxxxxxx
export TENCENTCLOUD_REGION=ap-guangzhou
```

**优先级**：
1. `$TENCENTCLOUD_FINOPS_CONFIG` 配置文件（如设置）
2. 环境变量 `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY`
3. tccli 默认凭证链（`~/.tencentcloud/credentials`）

### 1.2 配置文件方式（推荐生产环境）

```bash
export TENCENTCLOUD_FINOPS_CONFIG=/etc/qcloud-finops/config.yaml
```

完整模板见 `assets/example-config.yaml`。支持：
- 预算定义（按产品/项目/标签）
- 告警通道（电话/短信/邮件/企业微信/钉钉/飞书）
- Tag 标签映射（业务/部门/环境）
- 异常检测阈值（默认 ii=20%, iii=80%）
- **预留**：多账号数组字段（当前不读取）

## 2. 最小权限策略

### 2.1 起步（最简，推荐先用这个）

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "billing:DescribeBill*",
        "billing:DescribeCost*",
        "billing:DescribeAccountBalance",
        "billing:DescribeBillAdjust",
        "trade:DescribeOrders",
        "trade:DescribePayDeals",
        "voucher:DescribeVoucherList"
      ],
      "resource": "*"
    }
  ]
}
```

### 2.2 完整版（包含联动分析所需的产品元数据权限）

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "billing:*",
        "trade:*",
        "voucher:*",
        "tag:GetTagKeys",
        "tag:GetTagValues",
        "tag:GetResources"
      ],
      "resource": "*"
    },
    {
      "effect": "allow",
      "action": [
        "cvm:Describe*Instances",
        "cvm:Describe*Images",
        "cdb:Describe*Instances",
        "clb:Describe*LoadBalancers",
        "cos:GetBucket",
        "cos:ListBucket",
        "vpc:Describe*",
        "monitor:Describe*"
      ],
      "resource": "*"
    }
  ]
}
```

### 2.3 按产品 ReadOnlyAccess（最简版无需授权时）

- `QcloudBillingReadOnlyAccess`
- `QcloudTradeReadOnlyAccess`
- `QcloudCAMReadOnlyAccess`
- `QcloudTagReadOnlyAccess`
- `QcloudMonitorReadOnlyAccess`
- 各产品 `ReadOnlyAccess`（按需追加）

> **最小权限原则**：先 2.1 节起步，跑通后再追加产品 ReadOnlyAccess。

## 3. 多账号扩展（预留，当前版本不启用）

```yaml
# 未来启用时，取消注释并填入
# credentials:
#   mode: multi
#   primary:
#     secret_id: ${TENCENTCLOUD_SECRET_ID}
#     secret_key: ${TENCENTCLOUD_SECRET_KEY}
#   sub_accounts:
#     - account_id: "1000xxxxxxxxx"
#       assume_role_arn: "qcs::cam::uin/1000xxxxxxxxx:roleName/FinOpsReadOnly"
#       alias: "业务账号A"
#     - account_id: "1000yyyyyyyyy"
#       assume_role_arn: "qcs::cam::uin/1000yyyyyyyyy:roleName/FinOpsReadOnly"
#       alias: "业务账号B"
```

启用条件：
- 主账号已通过 `qcloud-cam-ops` 创建 FinOpsReadOnly 角色
- 子账号已信任主账号的 role-arn
- 主账号 CAM 策略含 `sts:AssumeRole`

## 4. 凭证安全建议

| 建议 | 说明 |
|---|---|
| **定期轮换** | SecretKey 90 天轮换一次（参考 `qcloud-cam-ops`） |
| **最小权限** | 严格按本文件 §2.1 起步，禁用 `*:*` |
| **IP 白名单** | CAM 用户绑定 IP 白名单（公网出口固定时） |
| **MFA** | 高权限账号启用 MFA |
| **审计日志** | 开启 `CloudAudit` 记录所有 API 调用 |
| **不使用主账号** | 创建专用 FinOps 子账号，避免主账号密钥泄露 |

## 5. 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `AuthFailure.SignatureFailure` | 密钥错或签名算法不匹配 | 检查环境变量 + tccli 升级 |
| `AuthFailure.InvalidSecretId` | SecretID 被禁用/删除 | CAM 控制台确认 |
| `UnauthorizedOperation` | 策略不足 | 按本文件 §2 追加策略 |
| `RequestLimitExceeded` | 账号级 QPS 限流 | 降低并发 + 退避重试 |
| 配置文件加载失败 | YAML 语法错 | 用 `python -c "import yaml; yaml.safe_load(open('config.yaml'))"` 校验 |

详细 API 错误码 → `references/api-cross-check.md`。
