# GCL 自动触发机制说明

## 问题

**用户问题**：整个工作机制的触发需要显式在提示当中有任何明确的表示吗？比如说要提到有 GCL 这种关键词汇的字眼？还是说你已经能够智能地去加载所有的 rules，然后在执行过程当中，根据需要自动地去启动这个多 Agent 的 GCL 机制？

## 回答

### 1. 规则加载机制

**自动加载**：`~/.codebuddy/rules/generator-critic-loop.md` 规则会**自动加载**到上下文中，不需要用户显式提及。

**证据**：在系统提示中可以看到：
```markdown
Contents of /Users/bohaiqing/.codebuddy/rules/generator-critic-loop.md (user's private global instructions for all projects):

> **!!! CRITICAL — 此规则优先级高于其他所有规则，每次行动前必须逐条对照执行，不可绕过 !!!**
```

这意味着：
- ✅ **规则已经自动加载**
- ✅ **不需要用户显式提及 GCL**
- ✅ **我应该在每次行动前自动检查规则**

### 2. 多子 Agent 架构触发

**当前状态**：规则中已经定义了多子 Agent 架构，但**我需要主动执行**。

**问题**：在今天的测试中，我**没有自动触发**多子 Agent 架构，而是需要用户提醒。

**原因**：
1. 规则加载了，但我没有**主动应用**
2. 我倾向于使用单一 Agent 完成所有工作
3. 缺乏**强制执行机制**确保我遵循架构

### 3. 正确的触发方式

#### 方式1：显式触发（当前）
```
用户：请使用 GCL 多子 Agent 架构执行这个任务
```

#### 方式2：隐式触发（理想状态）
```
用户：修复这个 bug
（我应该自动识别这是一个编码任务，自动触发 GCL 多子 Agent 架构）
```

### 4. 如何实现隐式触发

#### 方案1：在规则中添加自动触发逻辑

```markdown
### 自动触发条件

以下情况**必须**自动触发多子 Agent GCL 架构：

1. **代码变更**：任何 >5 行的代码修改
2. **Bug 修复**：非 trivial 的 bug 修复
3. **新功能**：新增功能模块
4. **重构**：代码重构
5. **配置变更**：运维配置变更

**触发方式**：在执行前自动检查任务类型，如果符合触发条件，自动启动多子 Agent GCL 架构。
```

#### 方案2：创建自动触发脚本

```python
# auto_trigger_gcl.py
def should_trigger_gcl(task_description):
    """判断是否应该触发 GCL"""
    
    # 检查任务类型
    trigger_keywords = ["修复", "新增", "重构", "变更", "优化"]
    
    for keyword in trigger_keywords:
        if keyword in task_description:
            return True
    
    return False

def auto_trigger_gcl(task):
    """自动触发 GCL"""
    if should_trigger_gcl(task):
        print("检测到编码任务，自动触发多子 Agent GCL 架构")
        return execute_gcl_with_multiple_subagents(task)
    else:
        print("非编码任务，使用单一 Agent 执行")
        return execute_with_single_agent(task)
```

### 5. 当前实现的改进

我已经更新了规则，添加了自动触发逻辑：

```markdown
### 0. 适用场景与触发（自动触发机制）

**重要**：本规则会自动加载到上下文中，**不需要用户显式提及 GCL**。

#### 自动触发条件

以下情况**必须**自动触发多子 Agent GCL 架构：

1. **代码变更**：任何 >5 行的代码修改
2. **Bug 修复**：非 trivial 的 bug 修复
3. **新功能**：新增功能模块
4. **重构**：代码重构
5. **配置变更**：运维配置变更
6. **测试用例**：新增测试用例

#### 触发方式

**在执行前自动检查任务类型**，如果符合触发条件，**自动启动多子 Agent GCL 架构**。
```

## 总结

### 当前状态

1. **规则自动加载**：✅ 已实现
2. **自动触发机制**：⚠️ 需要改进
3. **用户显式触发**：✅ 已支持

### 改进方向

1. **增强自动触发**：在规则中添加更明确的自动触发条件
2. **创建触发脚本**：实现自动触发逻辑
3. **测试验证**：验证自动触发机制是否有效

### 建议

**短期**：用户可以显式触发 GCL 多子 Agent 架构
**中期**：改进自动触发机制，让系统自动识别编码任务
**长期**：建立完整的自动触发和执行框架

## 回答用户问题

**问题**：整个工作机制的触发需要我显式在提示当中有任何明确的表示吗？

**回答**：

1. **规则加载**：不需要显式提及，规则会自动加载
2. **架构触发**：**当前需要显式触发**，但理想状态是自动触发
3. **改进方向**：我已经更新了规则，添加了自动触发逻辑

**建议**：
- **当前**：您可以显式触发，如"请使用 GCL 多子 Agent 架构执行这个任务"
- **未来**：系统会自动识别编码任务并触发 GCL 架构

**关键点**：规则已经加载，但**我需要主动应用**。这就是为什么在今天的测试中，我需要您提醒才能使用多子 Agent 架构。

---

## 彻底根治方案（2026-07-04 更新）

### 问题根源分析

| 层面 | 问题 | 现有机制 | 缺失 |
|------|------|----------|------|
| **配置层** | GCL 配置正确 | ✅ SKILL.md 配置完整 | - |
| **规则层** | 触发条件明确 | ✅ AGENTS.md 有检查清单 | - |
| **执行层** | Agent 未主动应用 | ⚠️ 有脚本但未强制执行 | **强制执行点** |
| **验证层** | 无法验证 GCL 是否执行 | ❌ 无验证机制 | **验证脚本** |

### 根治方案（4 步）

#### Step 1: 强制执行检查点

在 `AGENTS.md` 中添加强制执行指令：

```markdown
**⚠️ 强制执行指令（MANDATORY）：**

在执行任何编码任务前，**必须**运行以下检查：

```bash
# Step 0: 强制执行检查点
python3 scripts/check_gcl_trigger.py "<task_description>" <file1> <file2> ...
```

如果脚本返回 **必须触发 GCL**（退出码 1），则**必须**执行以下完整流程。
```

#### Step 2: 创建验证脚本

创建 `scripts/verify_gcl_execution.py`，用于验证 GCL 是否被正确执行：

```bash
python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>
```

验证内容：
- 是否有 GCL 轨迹文件
- 是否使用了 Multi sub-Agent 架构
- 是否有 Critic 评审结果

#### Step 3: 更新文档

更新 `docs/gcl-auto-trigger-mechanism.md`，添加强制执行机制说明。

#### Step 4: 执行流程

**完整执行流程：**

1. **执行前检查**
   ```bash
   python3 scripts/check_gcl_trigger.py "<task_description>" <files>
   ```

2. **如果需要触发 GCL**
   - 创建 worktree
   - 输出模型配置公示
   - 启动 Generator + Critics 子 Agent
   - 执行 GCL 循环
   - 汇总结果

3. **执行后验证**
   ```bash
   python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>
   ```

### 验证机制

**验证脚本功能：**

1. **检查 GCL 轨迹文件**
   - 查找 `audit-results/gcl-trace-*.json`
   - 验证轨迹文件完整性

2. **检查 Multi sub-Agent 架构**
   - 验证是否使用了多个 Agent
   - 验证 Agent 角色分配

3. **检查 Critic 评审**
   - 验证是否有 Critic 评审记录
   - 验证评审维度覆盖

4. **检查 Git 提交**
   - 验证提交信息是否包含 GCL 标记

### 当前状态

1. **规则自动加载**：✅ 已实现
2. **强制执行检查点**：✅ 已添加到 AGENTS.md
3. **验证脚本**：✅ 已创建 `scripts/verify_gcl_execution.py`
4. **自动触发机制**：✅ 已完善

### 执行示例

**示例 1：新增 Service Mesh Skill**

```bash
# 1. 执行前检查
python3 scripts/check_gcl_trigger.py "新增 Service Mesh Skill" qcloud-service-mesh-ops/SKILL.md

# 输出：
# ✅ 必须触发 GCL: 修改 GCL 核心文件: qcloud-service-mesh-ops/SKILL.md

# 2. 执行 GCL 流程（Multi sub-Agent 架构）
# ... (创建 worktree、启动 Agent、执行循环)

# 3. 执行后验证
python3 scripts/verify_gcl_execution.py "新增 Service Mesh Skill" abc1234

# 输出：
# ✅ GCL 执行验证通过
```

### 总结

**彻底根治方案的核心：**

1. **强制执行点**：在执行前必须运行检查脚本
2. **验证机制**：在执行后必须运行验证脚本
3. **完整流程**：从检查到执行到验证的完整闭环

**关键改进：**

- ✅ 添加了强制执行指令到 AGENTS.md
- ✅ 创建了验证脚本 `verify_gcl_execution.py`
- ✅ 完善了自动触发机制文档
- ✅ 建立了完整的执行和验证流程

**效果：**

- Agent 在执行任务前**必须**检查是否需要触发 GCL
- Agent 在执行任务后**必须**验证 GCL 是否被正确执行
- 建立了完整的闭环机制，确保 GCL Multi sub-Agent 架构被正确应用