# GCL 多子 Agent 架构规则

## 规则概述

本文档定义了 **Generator-Critic-Loop (GCL) 多子 Agent 架构**的强制执行规则。该规则确保所有编码任务和运维配置变更都使用多子 Agent 架构进行质量保证。

## 规则位置

```
/Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md
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

### 步骤1：复制规则文件

```bash
# 复制规则到目标项目
cp /Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md /path/to/target-project/.codebuddy/rules/
```

### 步骤2：配置项目级设置

在目标项目根目录创建 `.gcl-enforcement.yaml`：

```yaml
# GCL 强制执行配置
gcl_enforcement:
  enabled: true
  strict_mode: true
  
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
1. 多子 Agent 架构的要求
2. 强制执行机制
3. 违规处理流程

## 验证脚本

### 创建验证脚本

```python
#!/usr/bin/env python3
"""validate_gcl_architecture.py - 验证 GCL 架构合规性"""

def validate_gcl_architecture():
    """验证 GCL 架构合规性"""
    
    checks = [
        check_multiple_subagents(),
        check_parallel_execution(),
        check_role_separation(),
        check_orchestrator_independence(),
        check_trace_recording()
    ]
    
    return all(checks)

def check_multiple_subagents():
    """检查是否使用了多个子 Agent"""
    # 实现检查逻辑
    pass

def check_parallel_execution():
    """检查是否并行执行"""
    # 实现检查逻辑
    pass

def check_role_separation():
    """检查角色是否分离"""
    # 实现检查逻辑
    pass

def check_orchestrator_independence():
    """检查编排器是否独立"""
    # 实现检查逻辑
    pass

def check_trace_recording():
    """检查是否记录了 trace"""
    # 实现检查逻辑
    pass

if __name__ == "__main__":
    if validate_gcl_architecture():
        print("✅ GCL 架构合规")
    else:
        print("❌ GCL 架构不合规")
        exit(1)
```

### 集成到项目

```bash
# 将验证脚本添加到项目
cp validate_gcl_architecture.py /path/to/target-project/scripts/
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