# Failure Patterns — Reflexion Memory

> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to 预防 (prevent) known errors.
>
> **Maintenance**: Updated automatically via Self-Review Round 3 (Lessons Learned).
> **Token budget**: ≤ 200 lines. When exceeded, prune low-frequency patterns (count < 3).

---

## 1. CLI Parameter Errors

> 从 GCL trace 中提取的 tccli 参数错误模式。注意：tccli 参数格式与 aliyun CLI 不同。

| Skill | Command | Error Pattern | Root Cause | Fix | Count |
|-------|---------|---------------|------------|-----|-------|
| `qcloud-cvm-ops` | `TerminateInstances` | `MissingParameter` | 缺少必填参数 InstanceIds | `--InstanceIds "[\"ins-xxx\"]"` (JSON 数组) | 0 |
| `qcloud-cvm-ops` | `RunInstances` | `InvalidParameter` | SecurityGroupIds 格式错误 | `--SecurityGroupIds "[\"sg-xxx\"]"` | 0 |
| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameterValue` | Zone 格式错误 | 使用 `ap-guangzhou` 而非 `guangzhou` | 0 |
| `qcloud-redis-ops` | `DestroyInstances` | `MissingParameter` | 缺少 InstanceIds | `--InstanceIds "[\"crs-xxx\"]"` | 0 |
| `qcloud-cdb-ops` | `IsolateDBInstance` | `InvalidParameter` | InstanceId 格式错误 | 使用 `cdb-xxx` 格式 | 0 |
| `qcloud-clb-ops` | `DeleteLoadBalancers` | `MissingParameter` | 缺少 LoadBalancerIds | `--LoadBalancerIds "[\"lb-xxx\"]"` | 0 |
| `qcloud-cam-ops` | `DeleteUser` | `InvalidParameter` | Name 参数拼写错误 | 确认参数名为 `Name` 非 `UserName` | 0 |
| `qcloud-cos-ops` | `DeleteBucket` | `InvalidParameterValue` | Bucket 名含大写或特殊字符 | Bucket 名必须全小写、仅含字母数字和 `-` | 0 |
| `qcloud-tke-ops` | `DeleteCluster` | `ResourceNotFound` | 集群已处于删除中或不存在 | 查询集群状态后重试 | 0 |
| `qcloud-monitor-ops` | `PutMetricAlarm` | `InvalidParameter` | Period 不在有效范围 | 使用 10/30/60/300/3600/21600/86400 | 0 |
| — | `AuthFailure.SecretIdNotFound` | `AuthFailure` | SecretId 不存在或环境变量未设置 | 检查 `TENCENTCLOUD_SECRET_ID` | 0 |
| — | `AuthFailure.InvalidAuthorization` | `AuthFailure` | 签名计算错误 | 确认 SDK 版本和 TC3-HMAC-SHA256 签名 | 0 |
| — | `UnauthorizedOperation.CamNoAuth` | `UnauthorizedOperation` | CAM 策略缺少权限 | 授予对应 `QcloudXxxFullAccess` 或自定义策略 | 0 |

**tccli 参数格式要点**（与 aliyun CLI 不同）：
- 数组参数：`--InstanceIds "[\"ins-xxx\"]"` (JSON 数组)，**不需要** `.N` 后缀
- 单值参数：`--InstanceId ins-xxx`，直接赋值
- 嵌套对象：`--Tag.0.Key=env --Tag.0.Value=prod` (从 0 开始)

---

## 2. Skill Generation Issues

> Skill 生成器（qcloud-skill-generator）常见的结构错误模式。

| Issue Type | Frequency | Fix Pattern | First Seen |
|------------|-----------|-------------|------------|
| Missing YAML frontmatter | 0x | Always start with `---` block containing name, description, compatibility, cli_applicability, metadata | 2026-06 |
| TE-6 violation (cross-file duplication) | 0x | Delete duplicate from references/, keep SKILL.md as authoritative | 2026-06 |
| Missing SHOULD/SHOULD NOT section | 0x | Add trigger conditions chapter with delegation rules | 2026-06 |
| Broken relative links | 0x | Use `../` prefix for references/ → assets/ links | 2026-06 |
| Missing Well-Architected table | 0x | Add four-pillar table (Reliability, Security, Cost, Efficiency) | 2026-06 |
| TE-1 violation (hardcoded versions) | 0x | Replace with `tccli` query command for dynamic version fetching | 2026-06 |
| Missing `cli_applicability` field | 0x | Add `dual-path` / `cli-first` / `cli-only` / `sdk-only` to frontmatter | 2026-06 |
| Missing `cli_support_evidence` | 0x | Cite verification command (e.g. `tccli cvm help`) | 2026-06 |

---

## 3. Cross-Skill Composition Failures

> 跨 Skill 调用链中的失败模式（含 SDK 常见错误）。

| Source Skill | Target Skill | Failure Pattern | Resolution | Count |
|--------------|--------------|-----------------|------------|-------|
| `qcloud-redis-ops` | `qcloud-cvm-ops` | `tccli cvm RunCommand` 编码失败 | 使用 base64 编码 command content | 0 |
| `qcloud-cdb-ops` | `qcloud-cvm-ops` | 大 SQL 文件执行超时 | 拆分为 < 10KB 的 chunk | 0 |
| `qcloud-redis-ops` | `qcloud-cvm-ops` | 目标 ECS 上 redis-cli 未安装 | Pre-flight 中添加幂等安装探测 | 0 |
| `qcloud-monitor-ops` | `qcloud-cvm-ops` | 新告警 DescribeAlarms 返回空 | PutMetricAlarm 后等待 60s 再查询 | 0 |
| `qcloud-well-architected-review` | `qcloud-*-ops` | Worker 返回空 `{{output.product_assessment}}` | 验证 skill 有 `## Read-Only Assessment Mode` 节 | 0 |
| `qcloud-proactive-inspection` | `qcloud-*-ops` | Discovery 委派返回无资源 | 检查 `delegate-to` 标记和凭证范围 | 0 |
| — | — | SDK import 路径错误 | `from tencentcloud.{product}.{version} import {product}_client, models` | 0 |
| — | — | SDK 版本不匹配 | `pip install tencentcloud-sdk-python --upgrade` | 0 |
| — | — | SDK 异常未捕获 | 捕获 `TencentCloudSDKException` 并检查 `Code` 字段 | 0 |

---

## 4. Runtime Execution Patterns

> GCL 执行中发现的运行时失败模式。

| Skill | Operation | Failure Pattern | Root Cause | Prevention |
|-------|-----------|-----------------|------------|------------|
| `qcloud-cvm-ops` | `StopInstances` | Instance stuck in Stopping state | Dependent services not stopped | Check running processes before stop |
| `qcloud-cdb-ops` | `CreateDBInstance` | Quota exceeded error | Account-level instance limit | Query quota before creation |
| `qcloud-redis-ops` | `ClearInstance` | Permission denied | CAM policy missing `credis:*Action` | Verify CAM policy in Pre-flight |
| `qcloud-clb-ops` | `RegisterTargets` | Backend health check fails | Target ECS security group blocks CLB | Verify SG rules before add |
| `qcloud-cos-ops` | `PutObject` | Bucket does not exist | Bucket deleted or wrong region | Verify bucket exists and region matches |
| `qcloud-tke-ops` | `CreateCluster` | Insufficient VPC subnet IPs | Subnet CIDR too small | Plan CIDR before cluster creation |
| `qcloud-cdn-ops` | `DeleteCdnDomain` | Fixed max_iter=3 too conservative for destructive ops | Irreversible operations need stricter iteration control | Implement dynamic max_iterations per operation risk: destructive=2, cache mutation=1, sensitive config=3 |
| `qcloud-proactive-inspection` | analyzer `_add_finding(..., name)` | Findings emitted with empty `resource` / `resource_id`; reports cannot locate the offending instance | Position args shifted: `name` landed in `action` slot, `resource` defaulted to `""` | Always call `_add_finding(..., resource=..., action=...)` as kwargs; never pass positionally after action |

---

## 5. Token Efficiency Violations

> Token Efficiency 规则的常见违反模式。

| TE Rule | Common Violation | Fix | Frequency |
|---------|------------------|-----|-----------|
| TE-1 | Hardcoded region/zone lists in references/ | Use `tccli cvm DescribeZones` query | 0x |
| TE-3 | Error table with > 3 columns | Merge columns, 1 error code per row | 0x |
| TE-4 | JSON paths scattered across file | Declare at file top in one block | 0x |
| TE-6 | Same script in SKILL.md and references/ | Delete from references, keep SKILL.md copy | 0x |

---

## Usage Guidelines

### For Agents (Pre-flight)

```
# Optional: Load failure patterns before executing a skill
# 1. Read this file (lazy-load, ~130 lines)
# 2. Filter patterns by current skill name
# 3. Inject relevant patterns into Generator context as prevention hints
```

### For Self-Review (Round 3: Lessons Learned)

```
# After completing R1 + R2:
# 1. Extract new failure patterns from this session
# 2. Check if pattern already exists (dedup by skill + command + error)
# 3. If new: append to appropriate section with count=1
# 4. If existing: increment count
# 5. If total lines > 200: prune patterns with count < 3
```

### For GCL Traces

```
# When a GCL iteration fails, record the failure pattern:
{
  "failure_pattern": {
    "category": "cli_parameter" | "skill_generation" | "cross_skill" | "runtime" | "token_efficiency",
    "skill": "qcloud-xxx-ops",
    "command": "tccli xxx ...",
    "error": "InvalidParameter: ...",
    "fix": "Use JSON array format for array params",
    "reusable": true | false
  }
}
```
