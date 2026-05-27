# CVM Integration Guide

SDK setup, environment configuration, Cloud Shell, and cross-skill delegation.

---

## 1. Execution Environments

CVM skill supports three execution environments:

| Environment | Setup Required | Use Case |
|-------------|---------------|----------|
| **Local CLI** | Install tccli + credentials | Development, automation scripts |
| **Local SDK** | Python 3.8+ + SDK package | Complex operations, batch processing |
| **Cloud Shell** | Zero setup (browser-based) | Quick operations, troubleshooting |

---

## 2. Cloud Shell Integration

### What is Cloud Shell

Cloud Shell is a browser-based shell environment provided by Tencent Cloud:

- **Pre-installed**: `tccli`, `tencentcloud-sdk-python`, common tools
- **Pre-authenticated**: Uses console login credentials automatically
- **Persistent storage**: 10GB persistent disk for scripts
- **Multi-region**: Switch regions with `--Region` flag
- **Free**: No additional cost (within quota)

### Access Cloud Shell

1. Login to [Tencent Cloud Console](https://console.cloud.tencent.com)
2. Click **Cloud Shell** icon (top right toolbar)
3. Terminal opens in browser

### Cloud Shell Features

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tencent Cloud Console                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Cloud Shell Terminal                                        ││
│  │  ┌───────────────────────────────────────────────────────┐  ││
│  │  │ $ tccli cvm DescribeInstances --Region ap-guangzhou    │  ││
│  │  │ Response: {...}                                        │  ││
│  │  │                                                        │  ││
│  │  │ Features:                                              │  ││
│  │  │ ✓ Pre-installed tccli (latest)                        │  ││
│  │  │ ✓ Pre-installed Python SDK                            │  ││
│  │  │ ✓ Auto-authenticated (console login)                  │  ││
│  │  │ ✓ Persistent storage (/data/)                         │  ││
│  │  │ ✓ Upload/download files                               │  ││
│  │  │ ✓ Multiple sessions                                   │  ││
│  │  └───────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Cloud Shell Commands

```bash
# Check tccli version
tccli version
# Output: tccli 3.0.x

# Check Python SDK
python3 -c "import tencentcloud.cvm; print('SDK OK')"
# Output: SDK OK

# Switch region (no credential setup needed)
tccli cvm DescribeInstances --Region ap-shanghai

# Save scripts to persistent storage
mkdir -p /data/scripts
vim /data/scripts/my_script.py
# Scripts persist across sessions

# Upload files from local machine
# Use Cloud Shell toolbar → Upload button

# Download files to local machine
# Use Cloud Shell toolbar → Download button
```

### Cloud Shell Best Practices

| Practice | Description |
|----------|-------------|
| Use `/data/` | Persistent storage location |
| Save scripts | Keep frequently used scripts in `/data/scripts/` |
| Region switch | Always specify `--Region` explicitly |
| Session limit | Max 10 concurrent sessions |
| Timeout | Sessions timeout after 30 min idle |

### Cloud Shell Limitations

| Limitation | Workaround |
|------------|------------|
| 30 min idle timeout | Use automation scripts, not interactive |
| 10GB storage max | Download large files, don't store permanently |
| No SSH to external | Use console VNC for instance access |
| Network restrictions | Only Tencent Cloud endpoints accessible |
| Browser-based | Not suitable for CI/CD automation |

---

## 3. Local CLI Setup

### Install tccli

```bash
# Via pip (recommended)
pip install tccli

# Via Homebrew (macOS)
brew install tccli

# Verify
tccli version
tccli cvm help
```

### Configure Credentials

**Option 1: Environment Variables (Recommended for Agents)**

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"

# CLI reads from environment automatically
tccli cvm DescribeInstances
```

**Option 2: Interactive Configure**

```bash
tccli configure
# Prompts for:
# - secretId
# - secretKey
# - region
# Creates ~/.tccli/config
```

**Option 3: Config File**

```yaml
# ~/.tccli/config
default:
  secretId: AKIDxxxx
  secretKey: xxxxx
  region: ap-guangzhou
```

### Security Best Practices

```bash
# NEVER commit credentials
echo ".env" >> ~/.gitignore

# NEVER echo credentials
# ✅ Safe: Check existence only
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "Credential set"

# ❌ Unsafe: Expose value
echo $TENCENTCLOUD_SECRET_KEY
```

---

## 4. Python SDK Setup

### Install SDK

```bash
# Full SDK
pip install tencentcloud-sdk-python

# CVM-specific SDK (lighter)
pip install tencentcloud-sdk-python-cvm

# Verify
python3 -c "from tencentcloud.cvm import cvm_client; print('OK')"
```

### SDK Credential Setup

```python
from tencentcloud.common import credential
import os

# From environment (recommended)
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# From file (alternative)
with open("~/.tccli/config") as f:
    # Parse config file
    pass
```

---

## 5. Environment Variables

### Required Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `TENCENTCLOUD_SECRET_ID` | CAM | API access key ID |
| `TENCENTCLOUD_SECRET_KEY` | CAM | API secret key |
| `TENCENTCLOUD_REGION` | User | Default region code |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TENCENTCLOUD_ZONE` | Default zone | None (required per operation) |
| `TENCENTCLOUD_PROFILE` | API profile | `default` |

### Setting Variables

```bash
# Temporary (session)
export TENCENTCLOUD_REGION="ap-guangzhou"

# Permanent (.bashrc/.zshrc)
echo 'export TENCENTCLOUD_REGION="ap-guangzhou"' >> ~/.zshrc

# Python dotenv (.env)
TENCENTCLOUD_SECRET_ID=AKIDxxxx
TENCENTCLOUD_SECRET_KEY=xxxxx
TENCENTCLOUD_REGION=ap-guangzhou
```

---

## 6. Cross-Skill Delegation Matrix

| Operation | Primary Skill | CVM Skill Role |
|-----------|--------------|----------------|
| VPC creation | `qcloud-vpc-ops` | Verify VPC exists before RunInstances |
| Subnet creation | `qcloud-vpc-ops` | Verify Subnet exists |
| Security Group | `qcloud-vpc-ops` | Verify SG exists, add rules |
| CLB attach | `qcloud-clb-ops` | CVM instance as backend target |
| MySQL deployment | `qcloud-mysql-ops` | Separate skill for DB |
| Redis deployment | `qcloud-redis-ops` | Separate skill for cache |
| CAM permissions | `qcloud-cam-ops` | Grant CVM API permissions |
| Billing queries | `qcloud-billing-ops` | Cost analysis, price inquiry |

### Delegation Pattern

```python
# Before creating CVM, verify VPC exists
def verify_vpc_exists(vpc_client, vpc_id):
    # Delegate to VPC skill for verification
    from qcloud_vpc_ops import DescribeVpcsRequest
    
    req = DescribeVpcsRequest()
    req.VpcIds = [vpc_id]
    
    resp = vpc_client.DescribeVpcs(req)
    if resp.TotalCount == 0:
        raise ValueError(f"VPC {vpc_id} not found. Create VPC first using qcloud-vpc-ops")
    
    return resp.VpcSet[0]

# Before creating CVM, verify Security Group exists
def verify_sg_exists(vpc_client, sg_id):
    # Delegate to VPC skill for verification
    req = DescribeSecurityGroupsRequest()
    req.SecurityGroupIds = [sg_id]
    
    resp = vpc_client.DescribeSecurityGroups(req)
    if resp.TotalCount == 0:
        raise ValueError(f"Security Group {sg_id} not found. Create SG first using qcloud-vpc-ops")
    
    return resp.SecurityGroupSet[0]
```

---

## 7. Automation Integration

### Terraform Integration

```hcl
# CVM instance via Terraform
resource "tencentcloud_cvm_instance" "web_server" {
  instance_name  = "web-server"
  instance_type  = "S5.LARGE4"
  image_id       = "img-xxx"
  zone           = "ap-guangzhou-3"
  vpc_id         = "vpc-xxx"
  subnet_id      = "subnet-xxx"
  security_groups = ["sg-xxx"]
  
  system_disk {
    disk_type = "CLOUD_PREMIUM"
    disk_size = 50
  }
  
  data_disks {
    disk_type = "CLOUD_PREMIUM"
    disk_size = 100
  }
  
  tags = {
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}
```

### Ansible Integration

```yaml
# CVM instance via Ansible
- name: Create CVM instance
  tencentcloud_cvm:
    instance_name: "web-server"
    instance_type: "S5.LARGE4"
    image_id: "img-xxx"
    zone: "ap-guangzhou-3"
    vpc_id: "vpc-xxx"
    subnet_id: "subnet-xxx"
    security_groups:
      - "sg-xxx"
    state: present
```

### CI/CD Integration

```yaml
# GitLab CI example
create_instance:
  script:
    - pip install tccli
    - export TENCENTCLOUD_SECRET_ID=$CI_SECRET_ID
    - export TENCENTCLOUD_SECRET_KEY=$CI_SECRET_KEY
    - export TENCENTCLOUD_REGION="ap-guangzhou"
    - tccli cvm RunInstances --Placement '{"Zone":"ap-guangzhou-3"}' ...
```

---

## 8. File Structure Reference

```
qcloud-cvm-ops/
├── SKILL.md                      # Main runbook (entry point)
├── references/
│   ├── core-concepts.md          # Architecture, limits, types
│   ├── api-sdk-usage.md          # SDK operation map
│   ├── cli-usage.md              # tccli command reference
│   ├── troubleshooting.md        # Error codes, diagnostics
│   ├── monitoring.md             # Metrics, alarms
│   ├── integration.md            # This file (setup, delegation)
│   ├── well-architected-assessment.md  # Four-pillar assessment
│   └── idempotency-checklist.md  # Retry safety (optional)
├── assets/
│   ├── example-config.yaml       # Example configurations
│   └── eval_queries.json         # Trigger accuracy eval queries
```

---

## 9. Quick Environment Check

```bash
# One-line verification (Cloud Shell or Local)
python3 << 'EOF'
import os, sys
try:
    from tencentcloud.common import credential
    from tencentcloud.cvm import cvm_client
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID", ""),
        os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
    )
    if not cred.secretId or not cred.secretKey:
        print("❌ Credentials not set")
        sys.exit(1)
    client = cvm_client.CvmClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    print("✅ SDK OK, Credentials OK")
except Exception as e:
    print(f"❌ {e}")
EOF
```

---

## References

- [Cloud Shell Docs](https://cloud.tencent.com/document/product/153)
- [tccli Installation](https://cloud.tencent.com/document/product/440)
- [Python SDK Docs](https://cloud.tencent.com/document/sdk/Python)
- [CAM Credential Management](https://cloud.tencent.com/document/product/598)