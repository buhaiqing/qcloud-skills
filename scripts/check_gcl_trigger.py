#!/usr/bin/env python3
"""
GCL 触发检查脚本

检查是否需要触发 Generator-Critic-Loop 多子 Agent 架构。
"""

import sys
import fnmatch


def check_gcl_trigger(task_description: str, files_to_modify: list[str]) -> tuple[bool, str]:
    """
    检查是否需要触发 GCL
    
    Args:
        task_description: 任务描述
        files_to_modify: 需要修改的文件列表
    
    Returns:
        (should_trigger, reason)
    """
    
    # 1. 任务类型检查
    trigger_keywords = [
        "修复", "新增", "重构", "变更", "优化", "测试",
        "fix", "add", "refactor", "change", "optimize", "test"
    ]
    
    for keyword in trigger_keywords:
        if keyword in task_description:
            return True, f"任务包含关键词: {keyword}"
    
    # 2. 代码行数检查（需要估算）
    # 这里需要人工判断或基于任务描述估算
    # 如果任务描述中提到"多个文件"或"完整功能"，可能需要触发
    
    # 3. 文件类型检查
    gcl_core_patterns = [
        "*/SKILL.md",
        "*/references/rubric.md",
        "*/references/prompt-templates.md",
        "AGENTS.md",
        "qcloud-skill-generator/SKILL.md",
        "docs/gcl-spec.md",
        "docs/reflexion-memory.md"
    ]
    
    for file_path in files_to_modify:
        for pattern in gcl_core_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True, f"修改 GCL 核心文件: {file_path}"
    
    # 4. 运维配置检查
    config_patterns = ["*.yaml", "*.yml", "*.json", "*.toml", "*.hcl", "*.tf"]
    for file_path in files_to_modify:
        for pattern in config_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True, f"修改配置文件: {file_path}"
    
    return False, "无需触发 GCL"


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python check_gcl_trigger.py <task_description> [file1] [file2] ...")
        sys.exit(1)
    
    task_description = sys.argv[1]
    files_to_modify = sys.argv[2:] if len(sys.argv) > 2 else []
    
    should_trigger, reason = check_gcl_trigger(task_description, files_to_modify)
    
    if should_trigger:
        print(f"✅ 必须触发 GCL: {reason}")
        print("\n触发步骤:")
        print("1. 创建 worktree")
        print("2. 输出模型配置公示")
        print("3. 启动 Generator 子 Agent")
        print("4. 启动至少 2 个 Critic 子 Agent")
        print("5. 执行 GCL 循环（最多 3 轮）")
        print("6. 汇总结果并提交")
        sys.exit(1)  # 非零退出码表示需要触发
    else:
        print(f"❌ 无需触发 GCL: {reason}")
        sys.exit(0)  # 零退出码表示无需触发


if __name__ == "__main__":
    main()