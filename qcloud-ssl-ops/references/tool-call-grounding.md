# Tool-Call Grounding — SSL Skill Integration

> **Scope**: `qcloud-ssl-ops` SKILL.md 的工具调用 grounding 指引。  
> **Library**: `references/toolgrounding/` (tool_schema / state_dependency / grounding_trace / hallucination_detector)  
> **Note**: `cli_applicability: dual-path` — `tccli ssl` 主路径，SDK fallback。

---

## 1. Library Modules

| Module | Responsibility |
|--------|---------------|
| `tool_schema` | ParamConstraint 校验 + ErrorCode 枚举 + register / validate_call |
| `state_dependency` | StateTracker 状态依赖显式化 |
| `grounding_trace` | ToolCallTrace 结构化 trace + ParamSource |
| `hallucination_detector` | 三类失效模式检测（tool_not_found / param_out_of_range / state_not_satisfied）|

---

## 2. SSL tccli Commands → ToolSchema Registration

```python
from references.toolgrounding.tool_schema import (
    ToolSchema, ParamConstraint, register, validate_call, ErrorCode
)

# DescribeCertificates
register(ToolSchema(name="ssl_DescribeCertificates", description="查询证书列表", params={
    "Region": ParamConstraint(type="string", required=True),
    "Offset": ParamConstraint(type="number", min_val=0,        default=0),
    "Limit": ParamConstraint(type="number", min_val=1, max_val=100, default=20),
    "CertificateId": ParamConstraint(type="string", required=False),
    "SearchKey": ParamConstraint(type="string", required=False),
    }, returns={"TotalCount": int, "Certificates": list}, error_codes=list(ErrorCode)))

# Validate before execution
ok, msg, code = validate_call("ssl_DescribeCertificates", {"Region": "ap-guangzhou", "Limit": 999})
# → (False, "Param Limit=999 > max 100", PARAM_OUT_OF_RANGE)
```

| Tool | Key params | Returns |
|---|---|---|
| `ssl_UploadCertificate` | Region: string*; Certificate: string*; PrivateKey: string*; CertificateType: string; Alias: string | CertificateId, RequestId |
| `ssl_DeployCertificate` | Region: string*; CertificateId: string*; DeployTarget: array* | RequestId |
| `ssl_DeleteCertificate` | Region: string*; CertificateId: string* | RequestId |
| `ssl_DescribeCertificateDetail` | Region: string*; CertificateId: string* | CertificateId, Subject, ExpireTime, IssueTime |

---

## 3. SSL State Dependencies

SSL 操作相对独立，状态依赖较弱：

```
ssl_UploadCertificate (CertificateId)    ← 基础：先上传证书
  ├── ssl_DescribeCertificateDetail       ← 依赖 CertificateId
  ├── ssl_DeployCertificate               ← 依赖 CertificateId
  └── ssl_DeleteCertificate               ← 依赖 CertificateId
```

```python
from references.toolgrounding.state_dependency import (
    StateTracker, ToolStateSpec, StateAtom, StateDependency
)

SSL_SPECS: dict[str, ToolStateSpec] = {
    "ssl_DeployCertificate": ToolStateSpec(tool_name="ssl_DeployCertificate", provides=[],
        dependency=StateDependency(requires=[StateAtom("ssl_UploadCertificate", "CertificateId")])),
    "ssl_DescribeCertificateDetail": ToolStateSpec(tool_name="ssl_DescribeCertificateDetail", provides=[],
        dependency=StateDependency(requires=[StateAtom("ssl_UploadCertificate", "CertificateId")])),
}

tracker = StateTracker()
tracker.record("ssl_UploadCertificate", {"CertificateId": "cert-abc"})
can, why = tracker.can_call("ssl_DeployCertificate", SSL_SPECS)
# can=True, why=[]
```

---

## 4. SSL Grounding Trace

```python
from references.toolgrounding.grounding_trace import ToolCallTrace, ParamSource

trace = ToolCallTrace.new(
    tool_name="ssl_DeployCertificate",
    params={"Region": "ap-guangzhou", "CertificateId": "cert-abc",
            "DeployTarget": [{"LoadBalancerId": "lb-xxx", "ListenerId": "lbl-xxx"}]},
    reasoning="用户请求将证书 cert-abc 部署到负载均衡器 lb-xxx",
    confidence=0.9,
    source=ParamSource.USER_INSTRUCTION,
    constraints=["CertificateId 必须已上传"],
    result={"error_code": 0, "RequestId": "req-xxx"},
    state_snapshot=tracker.snapshot(),
)
```

---

## 5. SSL Hallucination Detection

```python
from references.toolgrounding.hallucination_detector import GroundingDetector
from references.toolgrounding.tool_schema import REGISTRY

detector = GroundingDetector(REGISTRY, SSL_SPECS, tracker)

# Case 1: 工具名拼错
reports = detector.detect("ssl_ListCertificates", {"Region": "ap-guangzhou"})
# → mode="tool_not_found", suggestion="ssl_DescribeCertificates, ssl_UploadCertificate, ..."

# Case 2: 参数越界
reports = detector.detect("ssl_DescribeCertificates", {"Region": "ap-guangzhou", "Limit": 999})
# → mode="param_out_of_range", detail="Param Limit=999 > max 100"

# Case 3: 状态未满足（证书未上传就部署）
tracker2 = StateTracker(); detector2 = GroundingDetector(REGISTRY, SSL_SPECS, tracker2)
reports = detector2.detect("ssl_DeployCertificate", {"Region": "ap-guangzhou", "CertificateId": "cert-xxx", "DeployTarget": []})
# → mode="state_not_satisfied"
```

---

## 6. Integration Pattern in SKILL.md Execution Flow

```
## Execute: DeployCertificate

1. validate_call("ssl_DeployCertificate", params)  ← 参数 schema 校验
2. tracker.can_call("ssl_DeployCertificate", SSL_SPECS)  ← 状态依赖检查
3. Execute tccli ssl DeployCertificate ... 或 SDK
4. ToolCallTrace.new(...) → audit log
5. On failure → GroundingDetector.detect(...) → report hallucination
```

Minimal change: 不修改 SKILL.md 主体，只在此文件引用本库的 4 个模块。
