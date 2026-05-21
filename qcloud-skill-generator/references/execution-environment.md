# Execution Environment Setup

This document covers the complete execution environment setup for Tencent Cloud skills: CLI installation, Python SDK configuration, credential management, and verification steps.

## Overview

Tencent Cloud skills use a **dual-path execution model**:
- **Primary path:** `tccli` CLI (Python CLI tool)
- **Fallback path:** `tencentcloud-sdk-python` (Python SDK)

Both paths share the same credential configuration via environment variables.

---

## 1. tccli CLI Installation

### 1.1 Installation Methods

#### Method A: pip (Recommended)

```bash
# Install via pip (Python 3.8+ required)
pip install tccli

# Verify installation
tccli version
```

#### Method B: Homebrew (macOS)

```bash
brew install tccli
tccli version
```

#### Method C: Official Installer

```bash
# Download from official site
# https://cloud.tencent.com/document/product/440/34011

# Or use the pip method above
```

### 1.2 CLI Structure

```bash
# CLI command format
tccli <product> <Action> [--Param1 value1] [--Param2 value2]

# Examples
tccli cvm DescribeInstances --Region ap-guangzhou
tccli cbs DescribeDisks --Region ap-guangzhou
tccli mysql DescribeDBInstances --Region ap-guangzhou
```

### 1.3 CLI Features

- **JSON output by default:** No `--output json` flag needed
- **Environment credentials:** Uses `TENCENTCLOUD_SECRET_ID` and `TENCENTCLOUD_SECRET_KEY`
- **Region parameter:** Use `--Region` (lowercase R)
- **Help system:** `tccli <product> help <Action>`

---

## 2. Python SDK Setup

### 2.1 SDK Installation

```bash
# Install full SDK
pip install tencentcloud-sdk-python

# Or install product-specific module
pip install tencentcloud-sdk-python-cvm
pip install tencentcloud-sdk-python-cbs
pip install tencentcloud-sdk-python-mysql
```

### 2.2 SDK Version Requirements

- **Minimum:** Python 3.8+
- **SDK version:** Latest stable from pip

### 2.3 SDK Structure

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm import cvm_client, models  # Product-specific import

# Create credential
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Create client
client = cvm_client.CvmClient(cred, "ap-guangzhou")

# Create request
req = models.DescribeInstancesRequest()

# Execute
resp = client.DescribeInstances(req)
```

---

## 3. Credential Configuration

### 3.1 Environment Variables (Recommended for Agents)

```bash
# Set environment variables
export TENCENTCLOUD_SECRET_ID="<YOUR_TENCENT_CLOUD_SECRET_ID>"
export TENCENTCLOUD_SECRET_KEY="<YOUR_TENCENT_CLOUD_SECRET_KEY>"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

### 3.2 CLI Interactive Configuration

```bash
# Interactive setup
tccli configure

# Prompts:
# SecretId: [Enter your SecretId]
# SecretKey: [Enter your SecretKey]
# Region: [Enter default region, e.g., ap-guangzhou]
```

### 3.3 Config File Configuration

**Location:** `~/.tccli/config` (YAML format)

```yaml
default:
  secretId: <YOUR_TENCENT_CLOUD_SECRET_ID>
  secretKey: <YOUR_TENCENT_CLOUD_SECRET_KEY>
  region: ap-guangzhou

# Multiple profiles (optional)
profile_prod:
  secretId: AKID_prod_xxxx
  secretKey: prod_xxxx
  region: ap-guangzhou

profile_dev:
  secretId: AKID_dev_xxxx
  secretKey: dev_xxxx
  region: ap-shanghai
```

### 3.4 Credential Priority

1. Environment variables (highest priority)
2. CLI config file (`~/.tccli/config`)
3. Interactive configure settings

---

## 4. Credential Security

### 4.1 Masking Rules (MANDATORY)

> **Security Policy:** Never expose `TENCENTCLOUD_SECRET_KEY` in any output.

| Scenario | Safe Pattern | Unsafe Pattern |
|----------|-------------|----------------|
| Bash output | `TENCENTCLOUD_SECRET_KEY=<masked>` | `echo $TENCENTCLOUD_SECRET_KEY` |
| Python print | `print("Key configured: ***")` | `print(os.environ.get("SECRET_KEY"))` |
| Error message | `Error: credential invalid` | `Error: invalid key 'xxx...'` |
| Verification | `test -n "$TENCENTCLOUD_SECRET_KEY"` | `cat ~/.tccli/config` |

### 4.2 Verification Commands (Safe)

```bash
# Check if credentials are set (DO NOT print values)
test -n "$TENCENTCLOUD_SECRET_ID" && echo "✅ SecretId is set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ SecretKey is set"

# Quick API test (validates credentials)
tccli cvm DescribeZones --Region ap-guangzhou
```

```python
# Python verification (safe)
import os
if os.environ.get("TENCENTCLOUD_SECRET_ID"):
    print("✅ SecretId configured")
if os.environ.get("TENCENTCLOUD_SECRET_KEY"):
    print("✅ SecretKey configured")
```

---

## 5. Region Configuration

### 5.1 Region Codes

Tencent Cloud region codes:

| Region | Code | Location |
|--------|------|----------|
| 广州 | `ap-guangzhou` | South China |
| 上海 | `ap-shanghai` | East China |
| 北京 | `ap-beijing` | North China |
| 成都 | `ap-chengdu` | Southwest China |
| 重庆 | `ap-chongqing` | Southwest China |
| 深圳 | `ap-shenzhen-fsi` | South China (Finance) |
| 南京 | `ap-nanjing` | East China |
| 香港 | `ap-hongkong` | Hong Kong |
| Singapore | `ap-singapore` | Southeast Asia |
| Tokyo | `ap-tokyo` | Japan |
| Seoul | `ap-seoul` | South Korea |
| Mumbai | `ap-mumbai` | India |
| Bangkok | `ap-bangkok` | Thailand |
| Virginia | `na-ashburn` | US East |
| Silicon Valley | `na-siliconvalley` | US West |
| Frankfurt | `eu-frankfurt` | Germany |

### 5.2 Region Selection

```bash
# Set default region
export TENCENTCLOUD_REGION="ap-guangzhou"

# Override in CLI command
tccli cvm DescribeInstances --Region ap-shanghai
```

```python
# Python SDK region
client = cvm_client.CvmClient(cred, "ap-guangzhou")
```

---

## 6. Self-Healing Installation

### 6.1 Pre-flight Checks

```bash
# Check Python version
python3 --version | grep -E "3\.[89]|3\.1[0-9]" || {
  echo "⚠️ Python 3.8+ required"
  # Attempt installation or graceful degradation
}

# Check pip
pip --version || {
  echo "⚠️ pip not available"
  # Fallback to system package manager
}

# Check tccli
tccli version || {
  echo "⚠️ tccli not installed"
  pip install tccli
}

# Check SDK
python3 -c "import tencentcloud" || {
  echo "⚠️ SDK not installed"
  pip install tencentcloud-sdk-python
}
```

### 6.2 Installation Recovery Paths

| Error | Recovery Path 1 | Recovery Path 2 | Recovery Path 3 |
|-------|----------------|-----------------|-----------------|
| pip not found | Use `python3 -m pip` | Use system package manager | Manual download |
| Network timeout | Use mirror (pypi.tuna.tsinghua.edu.cn) | Retry with backoff | Offline install |
| Permission denied | Use `--user` flag | Use virtualenv | Fix permissions |
| SSL error | Use trusted hosts | Update certifi | Manual cert bundle |

---

## 7. Verification Tests

### 7.1 Quick Validation

```bash
# Test CLI connectivity
tccli cvm DescribeZones --Region ap-guangzhou | jq '.Response.TotalCount'
# Expected: number of zones

# Test SDK connectivity
python3 -c "
from tencentcloud.common import credential
from tencentcloud.cvm import cvm_client, models
import os

cred = credential.Credential(
    os.environ.get('TENCENTCLOUD_SECRET_ID'),
    os.environ.get('TENCENTCLOUD_SECRET_KEY')
)
client = cvm_client.CvmClient(cred, 'ap-guangzhou')
req = models.DescribeZonesRequest()
resp = client.DescribeZones(req)
print(f'Zones: {len(resp.ZoneSet)}')
"
```

### 7.2 Full Validation

```bash
# Run full validation script
cat > /tmp/validate_qcloud_env.sh << 'EOF'
#!/bin/bash

echo "=== Tencent Cloud Environment Validation ==="

# Check Python
PYTHON_VER=$(python3 --version 2>&1 | grep -oE "3\.[0-9]+")
echo "✅ Python version: $PYTHON_VER"

# Check tccli
if command -v tccli &> /dev/null; then
  echo "✅ tccli installed: $(tccli version)"
else
  echo "❌ tccli not installed"
fi

# Check SDK
if python3 -c "import tencentcloud" 2>/dev/null; then
  SDK_VER=$(python3 -c "import tencentcloud; print(tencentcloud.__version__ or 'unknown')")
  echo "✅ SDK installed: $SDK_VER"
else
  echo "❌ SDK not installed"
fi

# Check credentials (existence only)
test -n "$TENCENTCLOUD_SECRET_ID" && echo "✅ SECRET_ID set" || echo "❌ SECRET_ID not set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ SECRET_KEY set" || echo "❌ SECRET_KEY not set"
test -n "$TENCENTCLOUD_REGION" && echo "✅ REGION set: $TENCENTCLOUD_REGION" || echo "⚠️ REGION not set"

# Test API call
if tccli cvm DescribeZones --Region ap-guangzhou 2>/dev/null | jq -e '.Response.ZoneSet' > /dev/null; then
  echo "✅ API connectivity verified"
else
  echo "❌ API connectivity failed"
fi

echo "=== Validation Complete ==="
EOF

chmod +x /tmp/validate_qcloud_env.sh
/tmp/validate_qcloud_env.sh
```

---

## 8. Virtual Environment (Optional)

### 8.1 Create Virtual Environment

```bash
# Create venv
python3 -m venv ~/.qcloud-venv

# Activate
source ~/.qcloud-venv/bin/activate

# Install dependencies
pip install tccli tencentcloud-sdk-python
```

### 8.2 Agent Integration

```bash
# In agent script, activate before execution
source ~/.qcloud-venv/bin/activate 2>/dev/null || true
tccli cvm DescribeInstances --Region ap-guangzhou
```

---

## 9. Troubleshooting

### 9.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `command not found: tccli` | Not installed | `pip install tccli` |
| `ModuleNotFoundError: tencentcloud` | SDK not installed | `pip install tencentcloud-sdk-python` |
| `InvalidSecretKey` | Wrong credential | Verify env vars or config |
| `RequestLimitExceeded` | Rate limit | Reduce request frequency |
| `Network timeout` | Connectivity | Check network or use mirror |

### 9.2 Debug Mode

```bash
# CLI debug (be careful with credential exposure)
tccli cvm DescribeInstances --Region ap-guangzhou --debug 2>&1 | grep -v "SecretKey"

# SDK debug
import logging
logging.basicConfig(level=logging.DEBUG)
# Note: DEBUG mode may expose credentials - use caution
```

---

## 10. Integration with Generated Skills

Generated `qcloud-[product]-ops` skills should:

1. **Reference this document** for setup instructions
2. **Include quick verification** in their Quick Start section
3. **Use environment variables** for credentials (never config file in skill instructions)
4. **Provide product-specific SDK import example**

---

## References

- [tccli Documentation](https://cloud.tencent.com/document/product/440)
- [Python SDK Documentation](https://cloud.tencent.com/document/sdk/Python)
- [API Key Management](https://console.cloud.tencent.com/cam/capi)