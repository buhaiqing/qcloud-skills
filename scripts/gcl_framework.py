#!/usr/bin/env python3
"""
GCL 通用框架

提供跨项目的 GCL（Generator-Critic-Loop）支持，包括：
1. 配置驱动的触发检查
2. 通用的执行验证
3. 可扩展的 Agent 管理

使用方法：
1. 复制 gcl_config.yaml 到你的项目
2. 根据项目需求修改配置
3. 使用本框架的函数进行检查和验证
"""

import sys
import yaml
import json
import fnmatch
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class GCLFramework:
    """GCL 通用框架"""
    
    def __init__(self, config_path: str = None):
        """
        初始化框架
        
        Args:
            config_path: 配置文件路径，默认为 scripts/gcl_config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "gcl_config.yaml"
        
        self.config = self._load_config(config_path)
        self.project_root = self._find_project_root()
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _find_project_root(self) -> Path:
        """查找项目根目录"""
        current = Path.cwd()
        while current != current.parent:
            # 检查常见的项目根目录标识
            if (current / ".git").exists() or (current / "package.json").exists() or \
               (current / "pyproject.toml").exists() or (current / "AGENTS.md").exists():
                return current
            current = current.parent
        return Path.cwd()
    
    def check_trigger(self, task_description: str, files_to_modify: List[str] = None) -> Tuple[bool, str]:
        """
        检查是否需要触发 GCL
        
        Args:
            task_description: 任务描述
            files_to_modify: 需要修改的文件列表
        
        Returns:
            (should_trigger, reason)
        """
        if files_to_modify is None:
            files_to_modify = []
        
        trigger_config = self.config.get("trigger", {})
        
        # 1. 关键词检查
        keywords = trigger_config.get("keywords", [])
        for keyword in keywords:
            if keyword in task_description:
                return True, f"任务包含关键词: {keyword}"
        
        # 2. 文件模式检查
        file_patterns = trigger_config.get("file_patterns", [])
        for file_path in files_to_modify:
            for pattern in file_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return True, f"修改匹配文件: {file_path} (模式: {pattern})"
        
        # 3. 配置文件检查
        config_patterns = trigger_config.get("config_patterns", [])
        for file_path in files_to_modify:
            for pattern in config_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return True, f"修改配置文件: {file_path}"
        
        # 4. 代码行数检查（需要估算）
        # 这里可以根据项目需求扩展
        
        return False, "无需触发 GCL"
    
    def verify_execution(self, task_description: str, commit_hash: str = None) -> Dict[str, Any]:
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
        
        verification_config = self.config.get("verification", {})
        checks_config = verification_config.get("checks", [])
        
        # 执行配置的检查项
        for check_config in checks_config:
            check_name = check_config["name"]
            required = check_config.get("required", True)
            
            if check_name == "GCL 轨迹文件":
                self._check_trace_files(result, check_config)
            elif check_name == "Multi sub-Agent 架构":
                self._check_multi_agent(result, check_config)
            elif check_name == "Critic 评审":
                self._check_critics(result, check_config)
            elif check_name == "Git 提交标记":
                self._check_git_commit(result, check_config, commit_hash)
        
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
    
    def _check_trace_files(self, result: Dict, config: Dict):
        """检查 GCL 轨迹文件"""
        trace_path = self.config.get("verification", {}).get("trace_path", "audit-results/gcl-trace-*.json")
        
        # 将 glob 模式转换为实际路径
        trace_dir = Path(trace_path).parent
        trace_pattern = Path(trace_path).name
        
        if trace_dir.exists():
            trace_files = list(trace_dir.glob(trace_pattern))
            if trace_files:
                result["checks"].append({
                    "name": "GCL 轨迹文件",
                    "status": "PASS",
                    "details": f"找到 {len(trace_files)} 个轨迹文件"
                })
            else:
                result["checks"].append({
                    "name": "GCL 轨迹文件",
                    "status": "FAIL",
                    "details": "未找到 GCL 轨迹文件"
                })
                result["issues"].append("未找到 GCL 轨迹文件")
        else:
            result["checks"].append({
                "name": "GCL 轨迹文件",
                "status": "FAIL",
                "details": f"轨迹目录不存在: {trace_dir}"
            })
            result["issues"].append(f"轨迹目录不存在: {trace_dir}")
    
    def _check_multi_agent(self, result: Dict, config: Dict):
        """检查 Multi sub-Agent 架构"""
        trace_path = self.config.get("verification", {}).get("trace_path", "audit-results/gcl-trace-*.json")
        trace_dir = Path(trace_path).parent
        trace_pattern = Path(trace_path).name
        
        if trace_dir.exists():
            trace_files = list(trace_dir.glob(trace_pattern))
            if trace_files:
                latest_trace = max(trace_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_trace, 'r', encoding='utf-8') as f:
                        trace_data = json.load(f)
                    
                    min_agents = config.get("min_agents", 2)
                    agents = trace_data.get("agents", [])
                    
                    if len(agents) >= min_agents:
                        result["checks"].append({
                            "name": "Multi sub-Agent 架构",
                            "status": "PASS",
                            "details": f"使用了 {len(agents)} 个 Agent (最少需要 {min_agents})"
                        })
                    else:
                        result["checks"].append({
                            "name": "Multi sub-Agent 架构",
                            "status": "FAIL",
                            "details": f"Agent 数量不足: {len(agents)} < {min_agents}"
                        })
                        result["issues"].append(f"Agent 数量不足: {len(agents)} < {min_agents}")
                except Exception as e:
                    result["checks"].append({
                        "name": "轨迹文件解析",
                        "status": "FAIL",
                        "details": f"解析轨迹文件失败: {str(e)}"
                    })
                    result["issues"].append(f"轨迹文件解析失败: {str(e)}")
    
    def _check_critics(self, result: Dict, config: Dict):
        """检查 Critic 评审"""
        trace_path = self.config.get("verification", {}).get("trace_path", "audit-results/gcl-trace-*.json")
        trace_dir = Path(trace_path).parent
        trace_pattern = Path(trace_path).name
        
        if trace_dir.exists():
            trace_files = list(trace_dir.glob(trace_pattern))
            if trace_files:
                latest_trace = max(trace_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_trace, 'r', encoding='utf-8') as f:
                        trace_data = json.load(f)
                    
                    min_critics = config.get("min_critics", 2)
                    critics = trace_data.get("critics", [])
                    
                    if len(critics) >= min_critics:
                        result["checks"].append({
                            "name": "Critic 评审",
                            "status": "PASS",
                            "details": f"有 {len(critics)} 个 Critic 评审 (最少需要 {min_critics})"
                        })
                    else:
                        result["checks"].append({
                            "name": "Critic 评审",
                            "status": "FAIL",
                            "details": f"Critic 数量不足: {len(critics)} < {min_critics}"
                        })
                        result["issues"].append(f"Critic 数量不足: {len(critics)} < {min_critics}")
                except Exception as e:
                    result["checks"].append({
                        "name": "轨迹文件解析",
                        "status": "FAIL",
                        "details": f"解析轨迹文件失败: {str(e)}"
                    })
                    result["issues"].append(f"轨迹文件解析失败: {str(e)}")
    
    def _check_git_commit(self, result: Dict, config: Dict, commit_hash: str = None):
        """检查 Git 提交"""
        if not commit_hash:
            result["checks"].append({
                "name": "Git 提交标记",
                "status": "WARN",
                "details": "未提供 commit_hash，跳过检查"
            })
            return
        
        try:
            import subprocess
            cmd = ["git", "log", "--oneline", "-1", commit_hash]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            
            markers = config.get("markers", ["GCL", "gcl"])
            for marker in markers:
                if marker in output:
                    result["checks"].append({
                        "name": "Git 提交标记",
                        "status": "PASS",
                        "details": f"提交 {commit_hash[:8]} 包含标记: {marker}"
                    })
                    return
            
            result["checks"].append({
                "name": "Git 提交标记",
                "status": "WARN",
                "details": f"提交 {commit_hash[:8]} 未包含 GCL 标记"
            })
        except Exception as e:
            result["checks"].append({
                "name": "Git 提交检查",
                "status": "FAIL",
                "details": f"检查 Git 提交失败: {str(e)}"
            })
    
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """
        获取 Agent 配置
        
        Args:
            agent_type: Agent 类型 (generator, critics)
        
        Returns:
            Agent 配置字典
        """
        execution_config = self.config.get("execution", {})
        agents_config = execution_config.get("agents", {})
        
        if agent_type == "generator":
            return agents_config.get("generator", {})
        elif agent_type == "critics":
            return agents_config.get("critics", [])
        else:
            return {}
    
    def should_use_multi_agent(self) -> bool:
        """检查是否应该使用 Multi sub-Agent 架构"""
        execution_config = self.config.get("execution", {})
        architecture_config = execution_config.get("architecture", {})
        return architecture_config.get("use_multi_agent", True)
    
    def get_max_iterations(self) -> int:
        """获取最大迭代轮次"""
        execution_config = self.config.get("execution", {})
        return execution_config.get("max_iterations", 3)


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python gcl_framework.py check <task_description> [file1] [file2] ...")
        print("  python gcl_framework.py verify <task_description> [commit_hash]")
        print("  python gcl_framework.py config")
        sys.exit(1)
    
    command = sys.argv[1]
    framework = GCLFramework()
    
    if command == "check":
        task_description = sys.argv[2] if len(sys.argv) > 2 else ""
        files_to_modify = sys.argv[3:] if len(sys.argv) > 3 else []
        
        should_trigger, reason = framework.check_trigger(task_description, files_to_modify)
        
        if should_trigger:
            print(f"✅ 必须触发 GCL: {reason}")
            sys.exit(1)
        else:
            print(f"❌ 无需触发 GCL: {reason}")
            sys.exit(0)
    
    elif command == "verify":
        task_description = sys.argv[2] if len(sys.argv) > 2 else ""
        commit_hash = sys.argv[3] if len(sys.argv) > 3 else None
        
        result = framework.verify_execution(task_description, commit_hash)
        
        print(f"\n{'='*60}")
        print(f"GCL 执行验证报告")
        print(f"{'='*60}")
        print(f"任务: {task_description}")
        print(f"时间: {result['timestamp']}")
        print(f"总体状态: {result['overall_status']}")
        print(f"\n详细检查:")
        
        for check in result["checks"]:
            status_icon = "✅" if check["status"] == "PASS" else "❌" if check["status"] == "FAIL" else "⚠️"
            print(f"  {status_icon} {check['name']}: {check['details']}")
        
        if result["issues"]:
            print(f"\n发现的问题:")
            for issue in result["issues"]:
                print(f"  - {issue}")
        
        print(f"\n{'='*60}")
        
        if result["overall_status"] == "PASS":
            print("✅ GCL 执行验证通过")
            sys.exit(0)
        else:
            print("❌ GCL 执行验证失败")
            sys.exit(1)
    
    elif command == "config":
        print("当前配置:")
        print(json.dumps(framework.config, indent=2, ensure_ascii=False))
        sys.exit(0)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
