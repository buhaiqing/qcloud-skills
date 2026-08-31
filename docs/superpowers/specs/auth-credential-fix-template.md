# Auth Credential 一键修复模板 (auth_credential)

## Problem Statement

`auth_credential`（MTTR ≈ 3.0m，未模板化）是 GCL 里唯一**无法自动修复**的 BLOCKER：
凭证错误必须人工解决。trace 调研（75 文件 / 111 iterations）建议分布：

| suggestion | 次数 | 含义 |
|------------|------|------|
| `auth failure — exit_code=-2, credentials invalid` | 6 | tccli 鉴权失败（SecretId/Key/Region 问题） |
| `Generator exit_code=127; fix command or credentials` | 6 | 命令不存在（tccli 未安装 / 不在 PATH） |
| `Generator exit_code=-2; fix command or credentials` | 3 | 同 exit_code=-2 |

MTTR 高的根因不是定位难（suggestion 已给出 exit_code），而是**每次从零排查凭证链**：
环境变量 → .env → CAM 权限 → 重试。模板把排查顺序固定为一张清单。

## 失败模式分类决策树（先查表，再动手）

```
exit_code = -2（tccli 鉴权失败）
├─ 是 → 场景 1（凭证无效：SecretId/Key/Region）
exit_code = 127（command not found）
├─ 是 → 场景 2（tccli 未安装 / 不在 PATH）
错误码为 AuthFailure / InvalidCredential（SDK 路径）
└─ 是 → 场景 3（CAM 权限 / 密钥过期轮换）
```

## 标准修复步骤（5 步）

| # | 步骤 | 动作 | 耗时 |
|---|---|---|---|
| 1 | 分类 | 按决策树查 exit_code / 错误码 | ~10s |
| 2 | 凭证检查 | 跑下方「凭证检查清单」：环境变量 → .env → CAM | ~1m |
| 3 | 修复 | 按场景修正（export / 填 .env / 装 tccli / 提 CAM 权限） | ~1m |
| 4 | 复跑 | 重跑原命令确认 exit=0 | ~30s |
| 5 | 验收 | 跑下方验收清单 | ~30s |

## 场景 1: exit_code=-2 — 凭证无效

tccli 返回 `-2` = 凭据鉴权失败。按顺序检查：

```bash
# 1. 环境变量是否已设置（值为空 / 未 export 都是问题）
env | grep -E "TENCENTCLOUD_(SECRET_ID|SECRET_KEY|REGION)" || echo "环境变量缺失"

# 2. 若用 .env：确认 .env 存在且已加载
ls -la .env && grep -c "SECRET" .env

# 3. 用 tccli 直接验证凭据（排除命令本身问题）
tccli cvm DescribeZones --Region ap-guangzhou
```

**修复**：
```bash
export TENCENTCLOUD_SECRET_ID=<你的 SecretId>
export TENCENTCLOUD_SECRET_KEY=<你的 SecretKey>
export TENCENTCLOUD_REGION=ap-guangzhou
# 或写 .env 后 source（见仓库 README prerequisites）
```

**判断技巧（<30s）**：`-2` 最常见原因是**新 shell 没重新 export** 或 **SecretKey 被轮换**。
先 `env | grep` 确认变量存在，再看 CAM 控制台核对 Key 是否仍有效。

## 场景 2: exit_code=127 — 命令不存在

`127` = command not found，凭证没问题的**前提**是 tccli 装好。

```bash
which tccli || echo "tccli 不在 PATH"
pip show tccli 2>/dev/null || echo "tccli 未安装"
```

**修复**：
```bash
pip install tccli      # 或按项目 prerequisites 安装
# 若用 venv：确认激活的 venv 里装了 tccli（错误路径常见于裸 python 与 venv python 混用）
```

## 场景 3: AuthFailure / InvalidCredential（SDK 路径）

SDK 报 `AuthFailure` / `InvalidCredential` 时按顺序排查：

| 错误码 | 含义 | 动作 |
|--------|------|------|
| `AuthFailure.SecretIdNotFound` | SecretId 不存在 | CAM 控制台核对 SecretId |
| `AuthFailure.SignatureFailure` | SecretKey 错误 | 重新生成 Key 对 |
| `InvalidCredential` | 密钥过期/失效 | 轮换 SecretKey |
| `AuthFailure.UnauthorizedOperation` | CAM 权限不足 | 给子账号加对应产品策略 |

## 凭证检查清单（每次 -2 / 127 前必跑）

- [ ] `env | grep TENCENTCLOUD_` — 三个变量都在且非空
- [ ] `.env` 存在且含 `SECRET_ID` / `SECRET_KEY` / `REGION`（`grep -c` 非 0）
- [ ] SecretKey 未被轮换（与 CAM 控制台比对，若有疑问重生成）
- [ ] `which tccli` 非空；若用 venv，确认 venv 已激活
- [ ] 子账号场景：CAM 策略覆盖目标产品（`tccli <product> help` 可过不代表写操作可过）
- [ ] Region 有效（`ap-guangzhou` 等，见 `.env.example`）

## 验收检查清单

- [ ] 重跑原命令 `exit=0`（不再是 -2 / 127）
- [ ] `python3 scripts/auto_fix_gcl_blockers.py --self-test` → 0
- [ ] 修复后的 GCL trace 中该命令 `exit_code=0` 且 `result_excerpt` 含真实响应
- [ ] **凭证不回显**：任何输出/commit/日志中 SecretId/Key 均以 `<masked>` 出现
- [ ] 若为环境问题（非代码问题）：在 commit message 注明（如 `auth: re-export creds in runner shell`）

## 防复发

- 跑 GCL 前先跑一遍「凭证检查清单」（5 项 <1m），避免把凭证问题烧进迭代预算
- CI 环境用 Secret 注入而非 .env；本地首次 clone 后必须 `cp .env.example .env` 再填
- GCL Critic 见到 `exit_code=-2` / `127` 时：直接引用本模板路径 + 场景号，
  不再让 Generator 自行猜（凭证问题 Generator 无法自动修，标 `auth_credential (no auto-fix)`）
