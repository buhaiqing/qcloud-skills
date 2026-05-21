# Enhanced Self-Healing Framework

This document defines mandatory self-healing patterns for all installation and setup flows in Tencent Cloud skills.

---

## Overview

Self-healing enables automatic recovery from installation and configuration errors without user intervention. Every `qcloud-[product]-ops` skill MUST implement self-healing for:

1. CLI installation (`tccli`)
2. Python SDK setup (`tencentcloud-sdk-python`)
3. Credential configuration
4. Environment verification

---

## Self-Healing Principles

### 1. Fail-Safe Design

- **Pre-flight checks:** Validate before attempting operation
- **Error classification:** Categorize errors for appropriate recovery
- **Multi-path recovery:** ≥ 3 recovery options per error type
- **Health verification:** Confirm successful recovery
- **Graceful degradation:** Partial functionality when full recovery fails

### 2. Recovery Metrics (Success Criteria)

| Metric | Target |
|--------|--------|
| Health score | ≥ 8/10 |
| Self-healing duration | < 30s |
| User intervention rate | < 20% |

---

## Pre-flight Checks

### Python Runtime Check

```python
import sys

def check_python_version():
    """Pre-flight: Python version ≥ 3.8"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return False, "Python 3.8+ required"
    return True, f"Python {version.major}.{version.minor} OK"

# Usage
ok, msg = check_python_version()
if not ok:
    # Trigger recovery path
    pass
```

### CLI Check

```bash
# Pre-flight: tccli exists and functional
check_tccli() {
  if ! command -v tccli &> /dev/null; then
    return 1  # Trigger installation recovery
  fi
  
  # Verify functionality
  tccli version &> /dev/null || return 2
  
  return 0
}
```

### SDK Check

```python
def check_sdk():
    """Pre-flight: tencentcloud SDK installed"""
    try:
        import tencentcloud
        return True, "SDK installed"
    except ImportError:
        return False, "SDK not installed"
```

### Credential Check

```bash
# Pre-flight: credentials configured (existence only, never echo)
check_credentials() {
  test -n "$TENCENTCLOUD_SECRET_ID" || return 1
  test -n "$TENCENTCLOUD_SECRET_KEY" || return 2
  return 0
}
```

---

## Error Classification

### Classification Matrix

| Error Type | Category | Recovery Strategy |
|------------|----------|-------------------|
| `command not found` | Missing dependency | Install package |
| `ImportError` | Missing dependency | Install package |
| `Permission denied` | Permission | Use --user, fix permissions |
| `Network timeout` | Network | Retry with mirror, offline install |
| `SSL error` | Security | Update certs, use trusted hosts |
| `InvalidSecretKey` | Credential | HALT (user must fix) |

### HALT vs Retry

| Condition | Action |
|-----------|--------|
| Credential invalid | HALT (user intervention required) |
| Permission denied (root required) | HALT (suggest sudo) |
| Network timeout (after 3 retries) | HALT (suggest offline) |
| Quota exceeded | HALT (user must request increase) |
| Transient network error | Retry (exponential backoff) |
| Rate limit | Retry (backoff) |
| Temporary unavailable | Retry (backoff) |

---

## Multi-Path Recovery

### CLI Installation Recovery

| Path | Method | When Used |
|------|--------|-----------|
| 1 | `pip install tccli` | Standard pip available |
| 2 | `python3 -m pip install tccli` | pip not in PATH |
| 3 | `brew install tccli` | macOS with Homebrew |
| 4 | `sudo pip install tccli` | Permission issue (--user failed) |
| 5 | Manual download | Network blocked |

```bash
install_tccli() {
  # Recovery Path 1: Standard pip
  pip install tccli && return 0
  
  # Recovery Path 2: python -m pip
  python3 -m pip install tccli && return 0
  
  # Recovery Path 3: Homebrew (macOS)
  if command -v brew &> /dev/null; then
    brew install tccli && return 0
  fi
  
  # Recovery Path 4: --user flag
  pip install --user tccli && return 0
  
  # Recovery Path 5: Graceful degradation
  echo "⚠️ tccli installation failed. SDK fallback will be used."
  return 1
}
```

### SDK Installation Recovery

| Path | Method | When Used |
|------|--------|-----------|
| 1 | `pip install tencentcloud-sdk-python` | Standard |
| 2 | `pip install --user tencentcloud-sdk-python` | Permission issue |
| 3 | Mirror: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple` | Network timeout |
| 4 | Product-specific module | Minimal footprint |

```python
def install_sdk():
    """Multi-path SDK installation recovery"""
    import subprocess
    
    paths = [
        ["pip", "install", "tencentcloud-sdk-python"],
        ["python3", "-m", "pip", "install", "tencentcloud-sdk-python"],
        ["pip", "install", "--user", "tencentcloud-sdk-python"],
        ["pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "tencentcloud-sdk-python"],
    ]
    
    for cmd in paths:
        try:
            subprocess.run(cmd, check=True)
            return True, "SDK installed"
        except subprocess.CalledProcessError:
            continue
    
    return False, "SDK installation failed after all paths"
```

### Network Timeout Recovery

```bash
# Network timeout with mirror fallback
pip_install_with_mirror() {
  PACKAGE="$1"
  
  # Primary: Official pypi
  pip install "$PACKAGE" && return 0
  
  # Recovery 1: Tsinghua mirror (China)
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "$PACKAGE" && return 0
  
  # Recovery 2: Douban mirror
  pip install -i https://pypi.doubanio.com/simple "$PACKAGE" && return 0
  
  # Recovery 3: Aliyun mirror
  pip install -i https://mirrors.aliyun.com/pypi/simple "$PACKAGE" && return 0
  
  return 1
}
```

---

## Health Verification

### Post-Recovery Health Score

```bash
calculate_health_score() {
  SCORE=0
  MAX_SCORE=10
  
  # Check Python (2 points)
  python3 --version &> /dev/null && SCORE=$((SCORE + 2))
  
  # Check tccli (3 points)
  command -v tccli &> /dev/null && SCORE=$((SCORE + 3))
  
  # Check SDK (2 points)
  python3 -c "import tencentcloud" 2>/dev/null && SCORE=$((SCORE + 2))
  
  # Check credentials (2 points)
  test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY" && SCORE=$((SCORE + 2))
  
  # Check region (1 point)
  test -n "$TENCENTCLOUD_REGION" && SCORE=$((SCORE + 1))
  
  echo "Health score: $SCORE/$MAX_SCORE"
  
  # Success criteria
  [ $SCORE -ge 8 ] && return 0 || return 1
}
```

### Connectivity Verification

```bash
verify_connectivity() {
  # Test API call (credential + network verification)
  if tccli cvm DescribeZones --Region ap-guangzhou &> /dev/null; then
    echo "✅ API connectivity verified"
    return 0
  else
    echo "⚠️ API connectivity failed"
    return 1
  fi
}
```

---

## Graceful Degradation

### Partial Functionality

```bash
# When tccli unavailable, fall back to SDK
if ! command -v tccli &> /dev/null; then
  echo "⚠️ tccli unavailable. Using Python SDK fallback."
  
  # Ensure SDK is available
  python3 -c "import tencentcloud" || pip install tencentcloud-sdk-python
  
  # Execute via SDK script
  python3 /tmp/sdk_fallback_script.py
fi
```

### Minimal Requirements

| Component | Required for | Degradation if Missing |
|-----------|--------------|------------------------|
| Python 3.8+ | All operations | HALT |
| Credentials | All operations | HALT |
| Region | All operations | Use default or ask |
| tccli | CLI operations | Use SDK fallback |
| SDK | SDK operations | HALT if tccli unavailable |

---

## Self-Healing Duration Tracking

```bash
# Track self-healing duration
SELF_HEAL_START=$(date +%s)

# ... self-healing operations ...

SELF_HEAL_END=$(date +%s)
DURATION=$((SELF_HEAL_END - SELF_HEAL_START))

echo "Self-healing duration: ${DURATION}s"

# Success criteria: < 30s
[ $DURATION -lt 30 ] && echo "✅ Within target" || echo "⚠️ Exceeded 30s target"
```

---

## Integration in Generated Skills

Each generated skill MUST:

1. **Include self-healing checks** in prerequisites section
2. **Document recovery paths** for CLI and SDK installation
3. **Track health score** after setup
4. **Implement graceful degradation** when components unavailable

### Skill Template Section

```markdown
## Prerequisites

### Self-Healing Setup

The skill automatically performs self-healing for:

| Component | Auto-recovery |
|-----------|---------------|
| Python 3.8+ | Checks version; HALT if < 3.8 |
| tccli CLI | 3 recovery paths: pip, --user, brew |
| Python SDK | 3 recovery paths: pip, mirror, --user |
| Credentials | HALT (user must configure) |

### Quick Start with Self-Healing

```bash
# Self-healing is automatic
# Just run any operation:

tccli [product] DescribeInstances --Region ap-guangzhou

# If components missing, skill attempts recovery
# Duration target: < 30s
# Health score target: ≥ 8/10
```
```

---

## Metrics Dashboard

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Health score | N/A | ≥ 8/10 | TBD |
| Self-heal duration | N/A | < 30s | TBD |
| User intervention | N/A | < 20% | TBD |
| Recovery success rate | N/A | ≥ 95% | TBD |

---

## References

- [Execution Environment](execution-environment.md)
- [Troubleshooting Guide](troubleshooting.md)