# SecOps Phase 1: SecOps 文件标准化 — Design & Plan

> 将全仓库 secOps 文件名统一为 `secops-security-operations.md`，修复幽灵引用，建立验证门禁。

---

## 1. 背景与动机

### 问题

当前仓库 secOps 文件存在两个文件名混用：

| 文件名 | 使用的 Skill |
|--------|-------------|
| `secops-checklist.md` | `qcloud-cvm-ops`、`qcloud-cbs-ops` |
| `secops-security-operations.md` | `qcloud-vpc-ops`、`qcloud-vpn-ops`、`qcloud-cos-ops`、`qcloud-clb-ops`、`qcloud-cdn-ops`、`qcloud-monitor-ops` |

Generator 模板统一在 `qcloud-skill-generator/references/secops-security-operations.md`，
但 SKILL.md 导航和实际文件之间存在路径不一致。

### 现状梳理

```
secops-checklist.md（需重命名）:
  qcloud-cvm-ops/references/secops-checklist.md        ← 存在，内容完整
  qcloud-cbs-ops/references/secops-checklist.md        ← 存在，内容较薄

secops-security-operations.md（目标文件名）:
  qcloud-skill-generator/references/secops-security-operations.md  ← 模板
  qcloud-vpc-ops/references/secops-security-operations.md         ← 存在
  qcloud-vpn-ops/references/secops-security-operations.md         ← 存在
  qcloud-cos-ops/references/secops-security-operations.md         ← 存在
  qcloud-clb-ops/references/secops-security-operations.md         ← 存在
  qcloud-cdn-ops/references/secops-security-operations.md         ← 存在
  qcloud-monitor-ops/references/secops-security-operations.md     ← 存在

幽灵引用（SKILL.md 引用了不存在的文件）:
  qcloud-vpn-ops/SKILL.md → secops-security-operations.md（实际文件存在，路径正确）
  qcloud-cbs-ops/SKILL.md → secops-checklist.md（文件存在）
  其他 skill 的 SKILL.md 引用 secOps 时可能指向错误文件名
```

### 解法

1. **统一文件名**：`secops-checklist.md` → `secops-security-operations.md`
2. **修复所有引用**：SKILL.md 导航、模板、See also 段落
3. **建立验证门禁**：`validate_local.py` 增加 secOps 完整性检查
4. **self-verify**：确保所有 secOps 引用指向真实存在的文件

---

## 2. 架构

### 2.1 文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 重命名 | `qcloud-cvm-ops/references/secops-checklist.md` → `secops-security-operations.md` |
| 重命名 | `qcloud-cbs-ops/references/secops-checklist.md` → `secops-security-operations.md` |
| 重命名 | `qcloud-cvm-ops/references/audit-rules.md` → `secops-audit-rules.md`（文件名含 `secops-`，与目标名同族，不改） |

> 决定：`audit-rules.md` 含 `secops-` 前缀，与目标命名体系同族，**不重命名**，仅确保 SKILL.md 导航中路径正确。

### 2.2 引用修复范围

```
SKILL.md 中的 secOps 引用（glob 所有 qcloud-*-ops/SKILL.md）：
  "secops-checklist.md"        → "secops-security-operations.md"
  "secops-security-operations" → 保持不变（已是目标名）
  相对路径 "../qcloud-skill-generator/references/secops-security-operations.md" → 保持不变

secOps 文件末尾的 "See also" 引用：
  "secops-checklist.md"        → "secops-security-operations.md"
  其他 secOps 文件互相引用 → 路径正确则保持
```

### 2.3 新增验证脚本

```
scripts/check_secops_completeness.py    ← 新建
  输入：所有 qcloud-*-ops/SKILL.md
  检查：
    a) secOps 相关引用（secops-*.md）的目标文件是否真实存在
    b) 被 SKILL.md 引用的 secOps 文件在对应 references/ 目录下是否存在
  输出：json 格式的检查报告
```

---

## 3. 算法 / 规则

### 3.1 文件重命名规则

- 只重命名 `secops-checklist.md`（其他文件名已是 `secops-security-operations.md`）
- 重命名后，原文件的 Git 历史保留（`git mv`）

### 3.2 引用替换规则

```
替换模式（grep + ast_edit）：
  文件内 "secops-checklist.md" → "secops-security-operations.md"
  
  限定范围：所有 *.md 文件（SKILL.md 和 references/*.md）
  排除：.git/、docs/、manual/ 等非 skill 目录（除非其中有 skill 引用）
```

### 3.3 验证规则

```
check_secops_completeness.py:
  1. 遍历所有 qcloud-*-ops 目录
  2. 读取每个 skill 的 SKILL.md，用正则提取 secOps 相关引用
  3. 对每个引用，拼接绝对路径，检查文件是否存在
  4. 输出缺失文件列表（severity=HIGH 对应 SKILL.md 直接引用但文件不存在）
```

---

## 4. Schema

### 4.1 check_secops_completeness.py 输出格式

```json
{
  "check": "secops-completeness",
  "timestamp": "2026-07-19T00:00:00+08:00",
  "total_skills": 34,
  "issues": [
    {
      "skill": "qcloud-xxx-ops",
      "type": "broken_reference",
      "referenced_file": "secops-security-operations.md",
      "referenced_from": "SKILL.md line 42",
      "severity": "HIGH",
      "detail": "SKILL.md references secops-security-operations.md but file does not exist at references/secops-security-operations.md"
    },
    {
      "skill": "qcloud-yyy-ops",
      "type": "legacy_filename",
      "file": "references/secops-checklist.md",
      "severity": "MEDIUM",
      "detail": "secops-checklist.md exists but should be renamed to secops-security-operations.md"
    }
  ],
  "summary": {
    "broken_references": 0,
    "legacy_filenames": 2,
    "pass": false
  }
}
```

### 4.2 validate_local.py 集成格式

```python
# 在 validate_local.py 中新增 secOps 检查项：
SECOPS_CHECK = {
    "name": "secops-completeness",
    "script": "scripts/check_secops_completeness.py",
    "severity": "HIGH",
    "description": "Check all secOps file references in SKILL.md point to existing files"
}
```

---

## 5. 实施清单

### Phase 1: 分析与文件操作

- [ ] `git mv` 重命名 `qcloud-cvm-ops/references/secops-checklist.md` → `secops-security-operations.md`
- [ ] `git mv` 重命名 `qcloud-cbs-ops/references/secops-checklist.md` → `secops-security-operations.md`
- [ ] 确认 `audit-rules.md` 不重命名（与目标命名体系同族）

### Phase 2: 引用修复

- [ ] 扫描所有 `qcloud-*-ops/references/` 下的 `secops-checklist.md` 引用 → 替换为 `secops-security-operations.md`
- [ ] 扫描所有 `qcloud-*-ops/SKILL.md` 中的 `secops-checklist.md` 引用 → 替换
- [ ] 扫描 `qcloud-skill-generator/` 下的 secOps 模板引用 → 确认正确
- [ ] 扫描 `docs/`、`manual/` 中的 secOps 引用 → 替换（如有）

### Phase 3: 新建验证脚本

- [ ] 新建 `scripts/check_secops_completeness.py`（含 JSON 输出 + self-verify）
- [ ] 运行 `check_secops_completeness.py`，确认无 broken_reference
- [ ] ruff 检查无 errors

### Phase 4: 集成到 validate_local.py

- [ ] 在 `validate_local.py` 中增加 `SECOPS_CHECK` 项
- [ ] 运行 `python3 scripts/validate_local.py` 全量通过

### Phase 5: Self-verify

- [ ] `git status` 确认只改了需要改的文件（无意外变更）
- [ ] `git log --oneline -3` 确认提交信息正确
- [ ] 确认无 `secops-checklist.md` 文件残留（find . -name "secops-checklist.md" 应为空）

---

## 6. Self-check（自验证逻辑）

```python
# 在 check_secops_completeness.py 末尾自验证：
import json, subprocess, sys, os

def self_verify():
    # 1. 无 broken_reference（severity=HIGH）
    # 2. 无 legacy_filename（secops-checklist.md 全部已重命名）
    # 3. validate_local.py 新增项能正常执行（不抛异常）
    
    result = subprocess.run(
        ["python3", "scripts/check_secops_completeness.py"],
        capture_output=True, text=True
    )
    report = json.loads(result.stdout)
    
    errors = []
    if report["summary"]["broken_references"] > 0:
        errors.append(f"broken_references = {report['summary']['broken_references']}")
    if report["summary"]["legacy_filenames"] > 0:
        errors.append(f"legacy_filenames = {report['summary']['legacy_filenames']}")
    
    assert not errors, f"Self-verify failed: {errors}"
    print("Self-verify: PASS")
```

---

## 7. 文件清单

| 文件 | 操作 |
|------|------|
| `qcloud-cvm-ops/references/secops-checklist.md` | 重命名为 `secops-security-operations.md` |
| `qcloud-cbs-ops/references/secops-checklist.md` | 重命名为 `secops-security-operations.md` |
| `scripts/check_secops_completeness.py` | 新建 |
| `scripts/validate_local.py` | 修改（新增 SECOPS_CHECK 项） |
| 所有 `qcloud-*-ops/SKILL.md` | 修改（替换 secops-checklist.md 引用） |
| 所有 `qcloud-*-ops/references/*.md` | 修改（替换 secops-checklist.md 引用） |

---

## 8. 后续 Phase（不在 Phase 1 scope）

- **Phase 2**: 为缺少 secOps 的 skill（CVM/CDB/TKE/Redis 等）补充 secOps 文件
- **Phase 3**: secOps 与 GCL rubric 双向引用
- **Phase 4**: 产品差异化 credential rotation 和 audit event ID registry
