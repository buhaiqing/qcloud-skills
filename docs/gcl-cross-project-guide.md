# GCL 跨项目通用方案指南

## 概述

GCL（Generator-Critic-Loop）是一个通用的质量保证框架，可以通过配置驱动的方式应用于各种项目类型。

## 通用性分析

### 通用组件（可直接复用）

| 组件 | 通用性 | 说明 |
|------|--------|------|
| GCL 框架核心 | ✅ 高 | `scripts/gcl_framework.py` |
| 配置模板 | ✅ 高 | `scripts/gcl_config.yaml` |
| 触发检查逻辑 | ✅ 高 | 关键词、文件模式、配置文件 |
| 验证检查逻辑 | ✅ 高 | 轨迹文件、Multi-Agent、Critic |
| Agent 架构 | ✅ 高 | Generator + Critics 并行 |

### 项目特定组件（需要自定义）

| 组件 | 项目特定性 | 自定义方法 |
|------|-----------|-----------|
| 触发关键词 | 中 | 修改配置文件中的 `trigger.keywords` |
| 文件模式 | 高 | 修改配置文件中的 `trigger.file_patterns` |
| Agent 配置 | 中 | 修改配置文件中的 `execution.agents` |
| 验证项目 | 中 | 修改配置文件中的 `verification.checks` |

## 跨项目使用步骤

### Step 1: 复制框架文件

将以下文件复制到你的项目中：

```bash
# 复制框架核心
cp scripts/gcl_framework.py <your-project>/scripts/
cp scripts/gcl_config.yaml <your-project>/scripts/

# 复制检查脚本（可选）
cp scripts/check_gcl_trigger.py <your-project>/scripts/
cp scripts/verify_gcl_execution.py <your-project>/scripts/
```

### Step 2: 修改配置文件

根据你的项目需求修改 `gcl_config.yaml`：

```yaml
# 项目信息
project:
  name: "your-project"
  type: "code-repository"  # 根据项目类型选择
  description: "Your project description"

# 触发条件
trigger:
  keywords:
    - "修复"
    - "新增"
    - "重构"
    # ... 添加你的关键词
  
  file_patterns:
    - "*/src/**/*.py"  # Python 项目
    - "*/lib/**/*.js"  # JavaScript 项目
    - "*/cmd/**/*.go"  # Go 项目
    # ... 添加你的文件模式
  
  config_patterns:
    - "*.yaml"
    - "*.json"
    - "*.toml"
    # ... 添加你的配置文件模式

# Agent 配置
execution:
  agents:
    generator:
      name: "Generator Agent"
      model: "your-preferred-model"  # 选择你的模型
    
    critics:
      - name: "Code Quality Critic"
        description: "验证代码质量"
        model: "your-preferred-model"
      
      - name: "Security Critic"
        description: "验证安全性"
        model: "your-preferred-model"
```

### Step 3: 集成到项目工作流

#### 方式 1: 命令行使用

```bash
# 检查是否需要触发 GCL
python3 scripts/gcl_framework.py check "修复 bug" src/main.py

# 验证 GCL 执行
python3 scripts/gcl_framework.py verify "修复 bug" abc1234

# 查看当前配置
python3 scripts/gcl_framework.py config
```

#### 方式 2: 集成到 CI/CD

在 `.github/workflows/ci.yml` 或类似文件中添加：

```yaml
- name: Check GCL Trigger
  run: |
    python3 scripts/gcl_framework.py check "${{ github.event.head_commit.message }}" ${{ changed_files }}

- name: Verify GCL Execution
  if: success()
  run: |
    python3 scripts/gcl_framework.py verify "${{ github.event.head_commit.message }}" ${{ github.sha }}
```

#### 方式 3: 集成到 Agent 规则

在你的 `AGENTS.md` 或类似规则文件中添加：

```markdown
### GCL 强制执行规则

在执行任何编码任务前，**必须**运行以下检查：

```bash
python3 scripts/gcl_framework.py check "<task_description>" <files>
```

如果返回需要触发 GCL，则**必须**使用 Multi sub-Agent 架构执行。

任务完成后，**必须**运行验证：

```bash
python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>
```
```

## 不同项目类型的配置示例

### 示例 1: Python 项目

```yaml
project:
  name: "python-project"
  type: "code-repository"

trigger:
  keywords:
    - "fix"
    - "add"
    - "refactor"
    - "optimize"
    - "test"
  
  file_patterns:
    - "*/src/**/*.py"
    - "*/tests/**/*.py"
    - "*/lib/**/*.py"
  
  config_patterns:
    - "*.yaml"
    - "*.yml"
    - "*.json"
    - "*.toml"
    - "requirements*.txt"
    - "setup.py"
    - "pyproject.toml"

execution:
  agents:
    generator:
      model: "claude-3-5-sonnet"
    
    critics:
      - name: "Code Quality Critic"
        model: "gpt-4"
      
      - name: "Security Critic"
        model: "gpt-4"
      
      - name: "Type Safety Critic"
        model: "gpt-4"

verification:
  trace_path: "audit-results/gcl-trace-*.json"
  checks:
    - name: "GCL 轨迹文件"
      required: true
    - name: "Multi sub-Agent 架构"
      required: true
      min_agents: 2
    - name: "Critic 评审"
      required: true
      min_critics: 2
```

### 示例 2: JavaScript/TypeScript 项目

```yaml
project:
  name: "js-project"
  type: "code-repository"

trigger:
  keywords:
    - "fix"
    - "add"
    - "refactor"
    - "optimize"
    - "test"
  
  file_patterns:
    - "src/**/*.ts"
    - "src/**/*.tsx"
    - "src/**/*.js"
    - "src/**/*.jsx"
    - "tests/**/*.ts"
    - "tests/**/*.js"
  
  config_patterns:
    - "*.json"
    - "*.yaml"
    - "*.yml"
    - "package.json"
    - "tsconfig.json"
    - ".eslintrc*"
    - ".prettierrc*"

execution:
  agents:
    generator:
      model: "claude-3-5-sonnet"
    
    critics:
      - name: "Code Quality Critic"
        model: "gpt-4"
      
      - name: "Type Safety Critic"
        model: "gpt-4"
      
      - name: "Security Critic"
        model: "gpt-4"

verification:
  trace_path: "audit-results/gcl-trace-*.json"
  checks:
    - name: "GCL 轨迹文件"
      required: true
    - name: "Multi sub-Agent 架构"
      required: true
      min_agents: 2
    - name: "Critic 评审"
      required: true
      min_critics: 2
```

### 示例 3: 基础设施项目 (Terraform/Ansible)

```yaml
project:
  name: "infra-project"
  type: "infrastructure"

trigger:
  keywords:
    - "fix"
    - "add"
    - "refactor"
    - "change"
    - "update"
  
  file_patterns:
    - "*.tf"
    - "*.tfvars"
    - "*.hcl"
    - "ansible/**/*.yml"
    - "ansible/**/*.yaml"
    - "k8s/**/*.yaml"
    - "k8s/**/*.yml"
  
  config_patterns:
    - "*.tf"
    - "*.hcl"
    - "*.yaml"
    - "*.yml"
    - "*.json"

execution:
  agents:
    generator:
      model: "claude-3-5-sonnet"
    
    critics:
      - name: "Security Critic"
        description: "验证安全性、权限配置"
        model: "gpt-4"
      
      - name: "Cost Optimization Critic"
        description: "验证成本优化"
        model: "gpt-4"
      
      - name: "Compliance Critic"
        description: "验证合规性"
        model: "gpt-4"

verification:
  trace_path: "audit-results/gcl-trace-*.json"
  checks:
    - name: "GCL 轨迹文件"
      required: true
    - name: "Multi sub-Agent 架构"
      required: true
      min_agents: 2
    - name: "Critic 评审"
      required: true
      min_critics: 2
    - name: "Security Review"
      required: true
```

## 高级功能

### 1. 自定义 Critic 维度

你可以根据项目需求自定义 Critic 维度：

```yaml
execution:
  agents:
    critics:
      - name: "Performance Critic"
        description: "验证性能优化"
        model: "gpt-4"
        dimensions:
          - "time_complexity"
          - "space_complexity"
          - "memory_usage"
      
      - name: "Accessibility Critic"
        description: "验证可访问性"
        model: "gpt-4"
        dimensions:
          - "wcag_compliance"
          - "screen_reader_support"
          - "keyboard_navigation"
```

### 2. 条件触发

支持基于条件的触发：

```yaml
trigger:
  conditions:
    - type: "file_change_count"
      threshold: 10
      action: "force_trigger"
    
    - type: "directory_change"
      patterns:
        - "src/security/**"
        - "src/auth/**"
      action: "force_trigger"
    
    - type: "commit_message"
      patterns:
        - "SECURITY"
        - "CRITICAL"
      action: "force_trigger"
```

### 3. 集成到 IDE

在 VS Code `.vscode/settings.json` 中添加：

```json
{
  "gcl.enabled": true,
  "gcl.configPath": "scripts/gcl_config.yaml",
  "gcl.autoCheck": true,
  "gcl.autoVerify": true
}
```

## 最佳实践

### 1. 配置管理

- 将 `gcl_config.yaml` 纳入版本控制
- 为不同环境维护不同的配置文件
- 使用环境变量覆盖配置

### 2. 渐进式采用

1. **Phase 1**: 只启用触发检查
2. **Phase 2**: 启用验证检查
3. **Phase 3**: 启用完整的 GCL 流程

### 3. 监控和度量

- 记录 GCL 触发次数
- 跟踪验证通过率
- 分析常见失败原因

### 4. 团队培训

- 为团队成员提供 GCL 框架培训
- 创建项目特定的使用指南
- 定期回顾和优化配置

## 故障排除

### 问题 1: 触发检查不准确

**解决方案**：
- 调整 `trigger.keywords` 列表
- 修改 `trigger.file_patterns` 模式
- 添加更精确的触发条件

### 问题 2: 验证失败

**解决方案**：
- 检查轨迹文件是否存在
- 验证 Agent 数量是否足够
- 确认 Critic 评审是否完整

### 问题 3: 性能问题

**解决方案**：
- 优化轨迹文件存储
- 减少不必要的检查项
- 使用异步验证

## 总结

GCL 通用框架通过配置驱动的方式，实现了跨项目的质量保证。通过修改配置文件，可以快速适配不同项目类型，建立统一的质量门禁机制。

**核心优势**：
- ✅ 配置驱动，易于定制
- ✅ 跨项目通用，可复用
- ✅ 完整的检查和验证机制
- ✅ 支持渐进式采用

**适用场景**：
- 代码仓库
- 文档项目
- 基础设施项目
- Skill 仓库
