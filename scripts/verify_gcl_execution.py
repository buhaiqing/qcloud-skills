#!/usr/bin/env python3
"""
GCL 执行验证脚本

验证 GCL 是否被正确执行，包括：
1. 是否使用了 Multi sub-Agent 架构
2. 是否有完整的执行轨迹
3. 是否有 Critic 评审结果
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def verify_gcl_execution(task_description: str, commit_hash: str = None) -> dict:
    """
    验证 GCL 执行情况
    
    Args:
        task_description: 任务描述
        commit_hash: 提交哈希（可选）
    
    Returns:
        验证结果字典
    """
    result = {
        "task": task_description,
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "overall_status": "UNKNOWN",
        "issues": []
    }
    
    # 1. 检查是否有 GCL 轨迹文件
    trace_files = list(Path("audit-results").glob("gcl-trace-*.json"))
    if trace_files:
        result["checks"].append({
            "name": "GCL 轨迹文件",
            "status": "PASS",
            "details": f"找到 {len(trace_files)} 个轨迹文件"
        })
        
        # 检查最新的轨迹文件
        latest_trace = max(trace_files, key=lambda f: f.stat().st_mtime)
        try:
            with open(latest_trace, 'r', encoding='utf-8') as f:
                trace_data = json.load(f)
            
            # 检查是否有 Multi sub-Agent 架构
            if "agents" in trace_data and len(trace_data["agents"]) > 1:
                result["checks"].append({
                    "name": "Multi sub-Agent 架构",
                    "status": "PASS",
                    "details": f"使用了 {len(trace_data['agents'])} 个 Agent"
                })
            else:
                result["checks"].append({
                    "name": "Multi sub-Agent 架构",
                    "status": "FAIL",
                    "details": "未使用 Multi sub-Agent 架构"
                })
                result["issues"].append("未使用 Multi sub-Agent 架构")
            
            # 检查是否有 Critic 评审
            if "critics" in trace_data and len(trace_data["critics"]) > 0:
                result["checks"].append({
                    "name": "Critic 评审",
                    "status": "PASS",
                    "details": f"有 {len(trace_data['critics'])} 个 Critic 评审"
                })
            else:
                result["checks"].append({
                    "name": "Critic 评审",
                    "status": "FAIL",
                    "details": "未找到 Critic 评审记录"
                })
                result["issues"].append("未找到 Critic 评审记录")
                
        except Exception as e:
            result["checks"].append({
                "name": "轨迹文件解析",
                "status": "FAIL",
                "details": f"解析轨迹文件失败: {str(e)}"
            })
            result["issues"].append(f"轨迹文件解析失败: {str(e)}")
    else:
        result["checks"].append({
            "name": "GCL 轨迹文件",
            "status": "FAIL",
            "details": "未找到 GCL 轨迹文件"
        })
        result["issues"].append("未找到 GCL 轨迹文件")
    
    # 2. 检查 Git 提交（如果提供了 commit_hash）
    if commit_hash:
        try:
            import subprocess
            cmd = ["git", "log", "--oneline", "-1", commit_hash]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            
            if "GCL" in output or "gcl" in output.lower():
                result["checks"].append({
                    "name": "Git 提交包含 GCL 标记",
                    "status": "PASS",
                    "details": f"提交 {commit_hash[:8]} 包含 GCL 标记"
                })
            else:
                result["checks"].append({
                    "name": "Git 提交包含 GCL 标记",
                    "status": "WARN",
                    "details": f"提交 {commit_hash[:8]} 未包含 GCL 标记"
                })
        except Exception as e:
            result["checks"].append({
                "name": "Git 提交检查",
                "status": "FAIL",
                "details": f"检查 Git 提交失败: {str(e)}"
            })
    
    # 3. 检查是否有模型配置公示
    # 这里可以通过检查输出日志或轨迹文件来验证
    
    # 计算总体状态
    failed_checks = [c for c in result["checks"] if c["status"] == "FAIL"]
    warn_checks = [c for c in result["checks"] if c["status"] == "WARN"]
    
    if len(failed_checks) == 0 and len(warn_checks) == 0:
        result["overall_status"] = "PASS"
    elif len(failed_checks) == 0:
        result["overall_status"] = "WARN"
    else:
        result["overall_status"] = "FAIL"
    
    return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python verify_gcl_execution.py <task_description> [commit_hash]")
        print("\n示例:")
        print("  python verify_gcl_execution.py '新增 Service Mesh Skill'")
        print("  python verify_gcl_execution.py '新增 Service Mesh Skill' abc1234")
        sys.exit(1)
    
    task_description = sys.argv[1]
    commit_hash = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = verify_gcl_execution(task_description, commit_hash)
    
    # 输出结果
    print(f"\n{'='*60}")
    print("GCL 执行验证报告")
    print(f"{'='*60}")
    print(f"任务: {task_description}")
    print(f"时间: {result['timestamp']}")
    print(f"总体状态: {result['overall_status']}")
    print("\n详细检查:")
    
    for check in result["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌" if check["status"] == "FAIL" else "⚠️"
        print(f"  {status_icon} {check['name']}: {check['details']}")
    
    if result["issues"]:
        print("\n发现的问题:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    
    print(f"\n{'='*60}")
    
    # 返回退出码
    if result["overall_status"] == "PASS":
        print("✅ GCL 执行验证通过")
        sys.exit(0)
    elif result["overall_status"] == "WARN":
        print("⚠️ GCL 执行验证有警告")
        sys.exit(0)
    else:
        print("❌ GCL 执行验证失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
