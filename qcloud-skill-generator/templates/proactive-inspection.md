# 主动巡检流程模板

五步闭环主动巡检流程模板。

## 1. 五步闭环模板结构

```
proactive-inspection/
├── config/
│   ├── inspection.yaml       # 巡检配置
│   └── targets.yaml          # 巡检目标清单
├── workflows/
│   ├── discovery.py          # 发现阶段
│   ├── collection.py         # 采集阶段
│   ├── detection.py          # 检测阶段
│   ├── diagnosis.py          # 诊断阶段
│   └── report.py             # 报告阶段
├── scripts/
│   ├── cli_inspection.sh     # CLI 执行脚本
│   └── automation.py         # 自动化脚本
├── reports/
│   └── template.md           # 报告模板
└── README.md
```

## 2. Discovery (发现)

### 资源发现模板

```python
#!/usr/bin/env python3
"""
资源发现模块 - 自动发现待巡检资源
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Resource:
    """资源对象"""
    resource_id: str
    resource_type: str
    region: str
    name: str
    tags: Dict
    metadata: Dict


class ResourceDiscovery(ABC):
    """资源发现抽象基类"""
    
    @abstractmethod
    def discover(self, filters: Optional[Dict] = None) -> List[Resource]:
        # 执行资源发现
        pass


class CVMResourceDiscovery(ResourceDiscovery):
    """CVM 资源发现"""
    
    def __init__(self, client):
        self.client = client
    
    def discover(self, filters: Optional[Dict] = None) -> List[Resource]:
        # 发现 CVM 实例
        resources = []
        
        # 查询所有区域
        regions = self._get_zones()
        
        for region in regions:
            # 构建查询请求
            request = models.DescribeInstancesRequest()
            request.Limit = 100
            
            if filters:
                if 'instance_ids' in filters:
                    request.InstanceIds = filters['instance_ids']
                if 'tags' in filters:
                    request.Tags = filters['tags']
            
            # 分页查询
            offset = 0
            while True:
                request.Offset = offset
                response = self.client.DescribeInstances(request)
                
                for instance in response.InstanceSet:
                    resource = Resource(
                        resource_id=instance.InstanceId,
                        resource_type='CVM',
                        region=region,
                        name=instance.get('InstanceName', ''),
                        tags={tag.Key: tag.Value 
                              for tag in instance.get('Tags', [])},
                        metadata={
                            'status': instance.get('Status'),
                            'instance_type': instance.get('InstanceType'),
                            'cpu': instance.get('CPU'),
                            'memory': instance.get('Memory')
                        }
                    )
                    resources.append(resource)
                
                if len(response.InstanceSet) < 100:
                    break
                offset += 100
        
        return resources
    
    def _get_zones(self) -> List[str]:
        # 获取所有可用区
        response = self.client.DescribeZones(models.DescribeZonesRequest())
        return [z.Zone for z in response.ZoneSet]


class MySQLResourceDiscovery(ResourceDiscovery):
    """MySQL 资源发现"""
    
    def __init__(self, client):
        self.client = client
    
    def discover(self, filters: Optional[Dict] = None) -> List[Resource]:
        # 发现 MySQL 实例
        resources = []
        
        request = models.DescribeDBInstancesRequest()
        request.Limit = 100
        
        response = self.client.DescribeDBInstances(request)
        
        for db in response.Items:
            resource = Resource(
                resource_id=db.InstanceId,
                resource_type='MySQL',
                region=db.Region,
                name=db.get('InstanceName', ''),
                tags={},
                metadata={
                    'engine': db.get('Engine'),
                    'status': db.get('Status'),
                    'instance_type': db.get('InstanceType')
                }
            )
            resources.append(resource)
        
        return resources


class DiscoveryPipeline:
    """发现流水线"""
    
    def __init__(self):
        self.discoveries: List[ResourceDiscovery] = []
    
    def register(self, discovery: ResourceDiscovery):
        # 注册发现器
        self.discoveries.append(discovery)
    
    def run(self, filters: Optional[Dict] = None) -> Dict[str, List[Resource]]:
        # 执行所有发现
        results = {}
        
        for discovery in self.discoveries:
            resources = discovery.discover(filters)
            resource_type = resources[0].resource_type if resources else 'Unknown'
            results[resource_type] = resources
        
        return results
    
    def export_inventory(self, results: Dict, filepath: str):
        # 导出资源清单
        import json
        
        inventory = {
            'generated_at': datetime.now().isoformat(),
            'total_resources': sum(len(r) for r in results.values()),
            'resources_by_type': {
                rtype: [
                    {
                        'resource_id': r.resource_id,
                        'region': r.region,
                        'name': r.name,
                        'tags': r.tags
                    }
                    for r in resources
                ]
                for rtype, resources in results.items()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)


# 配置示例
discovery_config = '''
# discovery-config.yaml
discovery:
  # 启用发现的资源类型
  enabled_types:
    - CVM
    - CBS
    - MySQL
    - Redis
    - CLB
    - VPC
    
  # 过滤条件
  filters:
    # 只发现特定标签的资源
    tags:
      - Key: Environment
        Value: Production
      - Key: ManagedBy
        Value: Ops
    
    # 排除特定资源
    exclude:
      instance_ids:
        - ins-excluded1
        - ins-excluded2
      name_patterns:
        - "*test*"
        - "*temp*"
      
  # 区域范围
  regions:
    - ap-guangzhou
    - ap-shanghai
    - ap-beijing
'''
```

## 3. Collection (采集)

### 指标采集模板

```python
#!/usr/bin/env python3
"""
指标采集模块 - 采集资源指标数据
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


@dataclass
class MetricData:
    """指标数据"""
    resource_id: str
    metric_name: str
    timestamp: datetime
    value: float
    unit: str
    labels: Dict[str, str]


@dataclass
class CollectionTask:
    """采集任务"""
    resource: 'Resource'
    metrics: List[str]
    start_time: datetime
    end_time: datetime


class MetricCollector:
    """指标采集器"""
    
    def __init__(self, monitor_client):
        self.client = monitor_client
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def collect(self, tasks: List[CollectionTask]) -> Dict[str, List[MetricData]]:
        # 并行采集指标
        
        Args:
            tasks: 采集任务列表
            
        Returns:
            按资源 ID 组织的指标数据
        results = {}
        
        # 提交所有任务
        futures = {
            self.executor.submit(self._collect_single, task): task
            for task in tasks
        }
        
        # 收集结果
        for future in as_completed(futures):
            task = futures[future]
            try:
                metrics = future.result()
                results[task.resource.resource_id] = metrics
            except Exception as e:
                print(f"采集失败: {task.resource.resource_id} - {e}")
        
        return results
    
    def _collect_single(self, task: CollectionTask) -> List[MetricData]:
        # 单个资源指标采集
        metrics_data = []
        
        for metric_name in task.metrics:
            # 构建请求
            request = models.GetMonitorDataRequest()
            request.Namespace = self._get_namespace(task.resource.resource_type)
            request.MetricName = metric_name
            request.Dimensions = [
                {
                    'Name': self._get_dimension_name(task.resource.resource_type),
                    'Value': task.resource.resource_id
                }
            ]
            request.StartTime = task.start_time.isoformat()
            request.EndTime = task.end_time.isoformat()
            request.Period = 300  # 5分钟粒度
            
            response = self.client.GetMonitorData(request)
            
            for datapoint in response.DataPoints:
                metrics_data.append(
                    MetricData(
                        resource_id=task.resource.resource_id,
                        metric_name=metric_name,
                        timestamp=datetime.fromtimestamp(datapoint.Timestamp),
                        value=datapoint.Value,
                        unit=datapoint.Unit,
                        labels={'region': task.resource.region}
                    )
                )
        
        return metrics_data
    
    def _get_namespace(self, resource_type: str) -> str:
        # 获取监控命名空间
        namespaces = {
            'CVM': 'QCE/CVM',
            'CBS': 'QCE/CBS',
            'MySQL': 'QCE/CDB',
            'Redis': 'QCE/REDIS',
            'CLB': 'QCE/LB_PUBLIC'
        }
        return namespaces.get(resource_type, '')
    
    def _get_dimension_name(self, resource_type: str) -> str:
        # 获取维度名称
        dimensions = {
            'CVM': 'InstanceId',
            'CBS': 'DiskId',
            'MySQL': 'InstanceId',
            'Redis': 'InstanceId',
            'CLB': 'LoadBalancerId'
        }
        return dimensions.get(resource_type, '')


# CVM 常用指标
cvm_metrics = [
    'CPUUsage',           # CPU使用率
    'MemUsage',           # 内存使用率
    'DiskUsage',          # 磁盘使用率
    'NetworkIn',          # 入带宽
    'NetworkOut',         # 出带宽
    'TrafficIn',          # 入流量
    'TrafficOut',         # 出流量
]

# MySQL 常用指标
mysql_metrics = [
    'CpuUseRate',         # CPU使用率
    'MemoryUseRate',      # 内存使用率
    'VolumeRate',         # 磁盘使用率
    'SlowQuery',          # 慢查询数
    'Connection',         # 连接数
    'IORead',             # 读IO
    'IOWrite',            # 写IO
]
```

## 4. Detection (检测)

### 异常检测模板

```python
#!/usr/bin/env python3
"""
异常检测模块 - 检测资源异常状态
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
import statistics


@dataclass
class Anomaly:
    """异常对象"""
    resource_id: str
    resource_type: str
    anomaly_type: str
    severity: str  # HIGH, MEDIUM, LOW
    metric_name: str
    current_value: float
    threshold: float
    description: str
    recommendation: str


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = config.get('thresholds', {})
    
    def detect(self, metrics: Dict[str, List[MetricData]]) -> List[Anomaly]:
        # 检测所有资源异常
        anomalies = []
        
        for resource_id, metric_list in metrics.items():
            # 按指标名称分组
            metrics_by_name = {}
            for m in metric_list:
                metrics_by_name.setdefault(m.metric_name, []).append(m)
            
            # 对每个指标进行检测
            for metric_name, values in metrics_by_name.items():
                anomaly = self._detect_single_metric(resource_id, metric_name, values)
                if anomaly:
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_single_metric(
        self, 
        resource_id: str, 
        metric_name: str, 
        values: List[MetricData]
    ) -> Optional[Anomaly]:
        # 单指标异常检测
        # 获取阈值配置
        threshold_config = self.thresholds.get(metric_name, {})
        if not threshold_config:
            return None
        
        # 计算统计值
        recent_values = [v.value for v in values[-10:]]  # 最近10个数据点
        avg_value = statistics.mean(recent_values)
        max_value = max(recent_values)
        
        # 阈值检测
        high_threshold = threshold_config.get('high', 90)
        medium_threshold = threshold_config.get('medium', 70)
        
        # 判断异常等级
        severity = None
        if max_value >= high_threshold:
            severity = 'HIGH'
        elif avg_value >= medium_threshold:
            severity = 'MEDIUM'
        elif max_value >= medium_threshold:
            severity = 'LOW'
        
        if not severity:
            return None
        
        # 获取资源类型
        resource_type = values[0].labels.get('resource_type', 'Unknown')
        
        return Anomaly(
            resource_id=resource_id,
            resource_type=resource_type,
            anomaly_type='threshold_breach',
            severity=severity,
            metric_name=metric_name,
            current_value=max_value,
            threshold=high_threshold if severity == 'HIGH' else medium_threshold,
            description=f'{metric_name} 超过阈值: 当前 {max_value:.2f}%, 阈值 {threshold_config.get(severity.lower())}%',
            recommendation=self._get_recommendation(metric_name, severity)
        )
    
    def _get_recommendation(self, metric_name: str, severity: str) -> str:
        # 获取优化建议
        recommendations = {
            'CPUUsage': {
                'HIGH': '立即扩容或优化应用性能',
                'MEDIUM': '考虑扩容或优化代码',
                'LOW': '监控趋势,必要时优化'
            },
            'MemUsage': {
                'HIGH': '立即扩容内存或优化内存使用',
                'MEDIUM': '检查内存泄漏或考虑扩容',
                'LOW': '持续监控'
            },
            'DiskUsage': {
                'HIGH': '立即扩容磁盘或清理无用文件',
                'MEDIUM': '计划磁盘扩容或清理',
                'LOW': '监控磁盘使用趋势'
            }
        }
        return recommendations.get(metric_name, {}).get(severity, '请关注该指标变化')


# 阈值配置示例
threshold_config = '''
thresholds:
  CPUUsage:
    high: 90    # 告警阈值
    medium: 70  # 预警阈值
    low: 50     # 关注阈值
  
  MemUsage:
    high: 90
    medium: 75
    low: 60
  
  DiskUsage:
    high: 95
    medium: 80
    low: 70
  
  # MySQL 指标
  SlowQuery:
    high: 100    # 每分钟慢查询数
    medium: 50
    low: 20
  
  Connection:
    high: 80    # 连接数百分比
    medium: 60
    low: 40
'''
```

## 5. Diagnosis (诊断)

### 诊断分析模板

```python
#!/usr/bin/env python3
"""
诊断分析模块 - 深度诊断异常根因
"""
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DiagnosisResult:
    """诊断结果"""
    anomaly: 'Anomaly'
    root_cause: str
    evidence: List[str]
    impact: str
    action_plan: List[str]


class Diagnostician:
    """诊断器"""
    
    def __init__(self, clients: Dict):
        self.clients = clients
    
    def diagnose(self, anomalies: List[Anomaly]) -> List[DiagnosisResult]:
        # 诊断所有异常
        results = []
        
        for anomaly in anomalies:
            result = self._diagnose_single(anomaly)
            if result:
                results.append(result)
        
        return results
    
    def _diagnose_single(self, anomaly: Anomaly) -> Optional[DiagnosisResult]:
        # 单异常诊断
        # 根据资源类型和异常类型选择诊断策略
        strategy = self._get_strategy(anomaly)
        
        if not strategy:
            return None
        
        # 执行诊断
        root_cause, evidence = strategy(anomaly)
        
        # 生成行动计划
        action_plan = self._generate_action_plan(anomaly, root_cause)
        
        return DiagnosisResult(
            anomaly=anomaly,
            root_cause=root_cause,
            evidence=evidence,
            impact=self._assess_impact(anomaly),
            action_plan=action_plan
        )
    
    def _get_strategy(self, anomaly: Anomaly) -> Optional[callable]:
        # 获取诊断策略
        strategies = {
            ('CVM', 'CPUUsage'): self._diagnose_cpu_high,
            ('CVM', 'MemUsage'): self._diagnose_memory_high,
            ('MySQL', 'SlowQuery'): self._diagnose_slow_query,
            ('MySQL', 'Connection'): self._diagnose_connection_high,
        }
        return strategies.get((anomaly.resource_type, anomaly.metric_name))
    
    def _diagnose_cpu_high(self, anomaly: Anomaly) -> Tuple[str, List[str]]:
        # CPU 使用率过高诊断
        cvm_client = self.clients['cvm']
        
        # 检查进程状态
        request = models.DescribeInstancesRequest()
        request.InstanceIds = [anomaly.resource_id]
        response = cvm_client.DescribeInstances(request)
        
        evidence = []
        root_causes = []
        
        # 检查实例规格
        instance = response.InstanceSet[0]
        cpu_count = instance.CPU
        
        evidence.append(f'实例规格: {cpu_count} vCPU')
        
        # 分析 CPU 使用分布
        if cpu_count < 4:
            root_causes.append('实例规格过小,建议升级')
        
        # 检查负载均衡
        # TODO: 检查是否需要横向扩展
        
        root_cause = ' | '.join(root_causes) if root_causes else '应用性能问题或流量突增'
        
        return root_cause, evidence
    
    def _diagnose_memory_high(self, anomaly: Anomaly) -> Tuple[str, List[str]]:
        # 内存使用率过高诊断
        evidence = []
        root_causes = []
        
        # 检查内存泄漏
        # TODO: 应用层诊断
        
        evidence.append('需要进一步分析进程内存占用')
        
        if anomaly.severity == 'HIGH':
            root_causes.append('可能存在内存泄漏或内存配置不足')
        
        root_cause = ' | '.join(root_causes) if root_causes else '内存资源紧张'
        
        return root_cause, evidence
    
    def _diagnose_slow_query(self, anomaly: Anomaly) -> Tuple[str, List[str]]:
        # 慢查询诊断
        mysql_client = self.clients['mysql']
        
        evidence = []
        
        # 获取慢查询日志分析
        # TODO: 查询慢查询详情
        
        evidence.append('慢查询数量超出正常范围')
        root_cause = 'SQL 性能问题或索引缺失'
        
        return root_cause, evidence
    
    def _generate_action_plan(self, anomaly: Anomaly, root_cause: str) -> List[str]:
        # 生成行动计划
        plans = {
            'CPUUsage': [
                '1. 分析当前进程 CPU 占用',
                '2. 评估是否需要升级实例规格',
                '3. 考虑横向扩展或负载均衡优化',
                '4. 优化应用性能瓶颈'
            ],
            'MemUsage': [
                '1. 检查是否存在内存泄漏',
                '2. 评估内存扩容需求',
                '3. 优化应用内存使用',
                '4. 调整系统内存参数'
            ],
            'SlowQuery': [
                '1. 分析慢查询 SQL 语句',
                '2. 添加缺失索引',
                '3. 优化查询逻辑',
                '4. 调整数据库参数'
            ]
        }
        
        return plans.get(anomaly.metric_name, ['请人工介入分析'])
    
    def _assess_impact(self, anomaly: Anomaly) -> str:
        # 评估影响
        severity_impact = {
            'HIGH': '严重影响业务可用性,需立即处理',
            'MEDIUM': '影响性能,建议尽快处理',
            'LOW': '潜在风险,建议持续关注'
        }
        return severity_impact.get(anomaly.severity, '影响待评估')


from typing import Tuple
```

## 6. Report (报告)

### 报告生成模板

```python
#!/usr/bin/env python3
"""
报告生成模块 - 生成巡检报告
"""
from typing import List, Dict
from datetime import datetime
import json


class ReportGenerator:
    """报告生成器"""
    
    def generate(self, diagnosis_results: List[DiagnosisResult], output_format: str = 'markdown') -> str:
        # 生成报告
        if output_format == 'markdown':
            return self._generate_markdown(diagnosis_results)
        elif output_format == 'json':
            return self._generate_json(diagnosis_results)
        else:
            raise ValueError(f'不支持的格式: {output_format}')
    
    def _generate_markdown(self, results: List[DiagnosisResult]) -> str:
        # 生成 Markdown 报告
        report = []
        
        # 标题
        report.append('# 腾讯云资源主动巡检报告')
        report.append(f'\n**巡检时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        report.append(f'\n**发现问题数**: {len(results)}')
        
        # 概览
        high_count = sum(1 for r in results if r.anomaly.severity == 'HIGH')
        medium_count = sum(1 for r in results if r.anomaly.severity == 'MEDIUM')
        low_count = sum(1 for r in results if r.anomaly.severity == 'LOW')
        
        report.append('\n## 问题概览')
        report.append(f'- **高危问题**: {high_count}')
        report.append(f'- **中危问题**: {medium_count}')
        report.append(f'- **低危问题**: {low_count}')
        
        # 详情
        report.append('\n## 问题详情')
        
        for i, result in enumerate(results, 1):
            anomaly = result.anomaly
            report.append(f'\n### 问题 {i}: {anomaly.resource_id}')
            report.append(f'- **资源类型**: {anomaly.resource_type}')
            report.append(f'- **异常指标**: {anomaly.metric_name}')
            report.append(f'- **严重等级**: {anomaly.severity}')
            report.append(f'- **当前值**: {anomaly.current_value:.2f}%')
            report.append(f'- **阈值**: {anomaly.threshold}%')
            report.append(f'- **根本原因**: {result.root_cause}')
            report.append(f'- **影响评估**: {result.impact}')
            
            report.append('\n**诊断依据**:')
            for evidence in result.evidence:
                report.append(f'  - {evidence}')
            
            report.append('\n**行动计划**:')
            for action in result.action_plan:
                report.append(f'  - {action}')
        
        # 建议
        report.append('\n## 总结建议')
        if high_count > 0:
            report.append(f'\n⚠️ 发现 {high_count} 个高危问题,建议立即处理!')
        if medium_count > 0:
            report.append(f'\n📝 发现 {medium_count} 个中危问题,建议优先处理.')
        if low_count > 0:
            report.append(f'\n💡 发现 {low_count} 个低危问题,建议持续关注.')
        
        return '\n'.join(report)
    
    def _generate_json(self, results: List[DiagnosisResult]) -> str:
        # 生成 JSON 报告
        report_data = {
            'inspection_time': datetime.now().isoformat(),
            'total_issues': len(results),
            'summary': {
                'high': sum(1 for r in results if r.anomaly.severity == 'HIGH'),
                'medium': sum(1 for r in results if r.anomaly.severity == 'MEDIUM'),
                'low': sum(1 for r in results if r.anomaly.severity == 'LOW')
            },
            'issues': [
                {
                    'resource_id': r.anomaly.resource_id,
                    'resource_type': r.anomaly.resource_type,
                    'metric_name': r.anomaly.metric_name,
                    'severity': r.anomaly.severity,
                    'current_value': r.anomaly.current_value,
                    'threshold': r.anomaly.threshold,
                    'root_cause': r.root_cause,
                    'impact': r.impact,
                    'evidence': r.evidence,
                    'action_plan': r.action_plan
                }
                for r in results
            ]
        }
        
        return json.dumps(report_data, indent=2, ensure_ascii=False)


# 报告模板示例
report_template = '''
# 腾讯云资源主动巡检报告

**巡检时间**: 2026-05-21 10:00:00
**巡检范围**: ap-guangzhou 区域
**发现问题数**: 5

## 问题概览

| 等级 | 数量 | 状态 |
|------|------|------|
| 高危 | 1 | 🔴 需立即处理 |
| 中危 | 2 | 🟡 建议优先处理 |
| 低危 | 2 | 🟢 持续关注 |

## 问题详情

### 问题 1: ins-xxx (高危)

- **资源类型**: CVM
- **异常指标**: CPUUsage
- **当前值**: 95.00%
- **阈值**: 90%
- **根本原因**: 实例规格过小,流量突增
- **影响评估**: 严重影响业务可用性

**行动计划**:
1. 立即升级实例规格
2. 添加负载均衡分散流量
3. 优化应用性能

---

### 问题 2: cdb-xxx (中危)

- **资源类型**: MySQL
- **异常指标**: SlowQuery
- **当前值**: 150/分钟
- **阈值**: 100/分钟
- **根本原因**: 索引缺失,查询未优化

**行动计划**:
1. 分析慢查询日志
2. 添加缺失索引
3. 优化查询语句

---

## 总结建议

⚠️ **立即行动**: ins-xxx CPU 使用率过高,影响业务稳定性

📝 **优先处理**: 数据库慢查询问题影响性能

💡 **持续关注**: 内存使用率上升趋势
'''
```