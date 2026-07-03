# GCL 多子 Agent 架构规则

## 规则概述

本文档定义了 **Generator-Critic-Loop (GCL) 多子 Agent 架构**的强制执行规则。该规则确保所有编码任务和运维配置变更都使用多子 Agent 架构进行质量保证。

## 规则位置（重要：单一来源）

**规则只在一个位置**：`/Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md`

**不要复制规则到具体项目！** 规则应该只有一个来源，便于统一管理和更新。

### 正确的架构

```
~/.codebuddy/rules/
└── generator-critic-loop.md  # 全局规则（唯一位置）

/path/to/project-a/
├── .gcl-enforcement.yaml     # 项目级配置（引用全局规则）
└── ...

/path/to/project-b/
├── .gcl-enforcement.yaml     # 项目级配置（引用全局规则）
└── ...
```

## 核心要求

### 1. 强制使用多子 Agent 架构

**适用场景**：所有非 trivial 的任务（>5 行代码变更）

**架构要求**：
```
GCL Orchestrator (主 Agent)
├── Generator Sub-Agent (1个)
└── Critic Sub-Agents (N个，N≥2)
    ├── Sub-Agent 1: 数据质量验证
    ├── Sub-Agent 2: 模型准确度验证
    └── Sub-Agent 3: 安全规则验证
```

### 2. 强制执行机制

#### 执行前
- 验证执行计划是否符合架构
- 拒绝不符合架构的计划

#### 执行中
- 实时监控角色分离
- 监控并行执行
- 自动检测和修复违规

#### 执行后
- 强制审计架构合规性
- 记录完整执行轨迹
- 生成合规性报告

### 3. 违规处理

| 违规类型 | 严重等级 | 处理方式 |
|---|---|---|
| 角色分离违规 | CRITICAL | 立即终止，重新执行 |
| 并行执行违规 | HIGH | 自动修复，重新并行执行 |
| 编排器独立性违规 | HIGH | 创建新编排器，重新执行 |
| trace 记录违规 | MEDIUM | 补充记录，继续执行 |

## 应用到其他项目

### 步骤1：确认全局规则已安装

确保 `/Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md` 包含多子 Agent 架构要求。

### 步骤2：创建项目级配置

在目标项目根目录创建 `.gcl-enforcement.yaml`（**不是复制规则文件**）：

```yaml
# GCL 强制执行配置（项目级）
gcl_enforcement:
  enabled: true
  strict_mode: true
  
  # 引用全局规则（不需要复制）
  global_rule: "~/.codebuddy/rules/generator-critic-loop.md"
  
  # 项目特定的配置覆盖（可选）
  architecture:
    must_use_multiple_subagents: true
    must_parallelize_critics: true
    must_separate_roles: true
    must_independent_orchestrator: true
```

### 步骤3：集成到 CI/CD

在 CI 配置中添加 GCL 验证步骤：

```yaml
# GitHub Actions 示例
- name: "GCL 架构合规检查"
  run: python3 scripts/validate_gcl_architecture.py
  if: always()
```

### 步骤4：培训团队

确保团队成员了解：
1. 全局规则的位置和内容
2. 项目级配置的作用
3. 强制执行机制和违规处理

## 验证脚本

### 创建验证脚本

```python
#!/usr/bin/env python3
"""validate_gcl_architecture.py - 验证 GCL 架构合规性

此脚本验证当前执行是否符合全局 GCL 多子 Agent 架构规则。
规则位置：/Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md
"""

import yaml
from pathlib import Path

def validate_gcl_architecture():
    """验证 GCL 架构合规性"""
    
    # 1. 检查全局规则是否存在
    global_rule_path = Path.home() / ".codebuddy/rules/generator-critic-loop.md"
    if not global_rule_path.exists():
        print("❌ 全局 GCL 规则不存在")
        return False
    
    # 2. 检查项目配置
    project_config = load_project_config()
    if not project_config.get("gcl_enforcement", {}).get("enabled", False):
        print("⚠️ 项目未启用 GCL 强制执行")
        return True  # 不强制，但警告
    
    # 3. 验证架构要求
    checks = [
        check_multiple_subagents(),
        check_parallel_execution(),
        check_role_separation(),
        check_orchestrator_independence(),
        check_trace_recording()
    ]
    
    return all(checks)

def load_project_config():
    """加载项目配置"""
    config_path = Path(".gcl-enforcement.yaml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}

# ... 其他检查函数保持不变
```

### 集成到项目

```bash
# 将验证脚本添加到项目（脚本本身是项目特定的）
cp validate_gcl_architecture.py /path/to/target-project/scripts/

# 脚本会自动查找全局规则，不需要复制规则文件
```

## 监控和告警

### 实时监控

```python
# 实时监控系统
class GCLMonitor:
    def __init__(self):
        self.violation_threshold = 0  # 零容忍
    
    def monitor_execution(self, execution):
        """监控执行过程"""
        violations = self.detect_violations(execution)
        
        if len(violations) > self.violation_threshold:
            self.send_alert(violations)
            
            if self.is_critical_violation(violations):
                self.block_deployment()
```

### 告警配置

```yaml
# 告警配置
alerting:
  enabled: true
  channels:
    - type: "slack"
      webhook: "https://hooks.slack.com/services/xxx"
    - type: "email"
      recipients: ["team@example.com"]
  
  rules:
    - name: "GCL 架构违规"
      severity: "critical"
      condition: "violations > 0"
      action: "block_deployment"
```

## 最佳实践

### 执行前
1. 验证执行计划符合架构
2. 配置正确的模型选型
3. 准备清晰的任务规格

### 执行中
1. 并行启动所有子 Agent
2. 实时监控执行过程
3. 及时响应违规

### 执行后
1. 强制审计架构合规性
2. 记录完整执行轨迹
3. 生成合规性报告

## 常见问题

### Q: 什么时候可以跳过多子 Agent 架构？
A: 只有以下情况可以跳过：
- 小于 5 行的 typo 修复
- 纯注释/文档变更
- 紧急 hotfix（需人工确认）

### Q: 如何处理违规？
A: 根据违规严重等级：
- CRITICAL: 立即终止，重新执行
- HIGH: 自动修复，重新执行
- MEDIUM: 补充记录，继续执行

### Q: 如何验证架构合规性？
A: 使用验证脚本：
```bash
python3 scripts/validate_gcl_architecture.py
```

## 总结

通过实施这个强制执行规则，可以确保：

1. **100% 架构合规**：每次 GCL 执行都符合多子 Agent 架构
2. **实时监控**：违规被实时检测
3. **自动修复**：大部分违规被自动修复
4. **完整审计**：所有执行都有完整记录

**核心目标**：将架构要求从"建议"转变为"强制约束"，通过技术手段确保每次执行都遵循这些约束。