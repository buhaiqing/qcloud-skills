# Enhanced Self-Healing Framework

## Overview

This document defines mandatory self-healing patterns for TKE skill installation and setup flows. Every installation step MUST implement auto-recovery.

## Pre-flight Checks

### Python Runtime Check

```bash
check_python() {
  python3 --version 2>/dev/null | grep -qE "3\.[89]|3\.1[0-9]" && return 0
  return 1
}
```

### CLI Check

```bash
check_tccli() {
  command -v tccli &> /dev/null && tccli tke help CreateCluster &> /dev/null && return 0
  return 1
}
```

### SDK Check

```bash
check_sdk() {
  python3 -c "from tencentcloud.tke import tke_client" 2>/dev/null && return 0
  return 1
}
```

### Credential Check

```bash
check_credentials() {
  test -n "$TENCENTCLOUD_SECRET_ID" || return 1
  test -n "$TENCENTCLOUD_SECRET_KEY" || return 2
  test -n "$TENCENTCLOUD_REGION" || return 3
  return 0
}
```

## Error Classification and Recovery

| Error Type | Recovery Path 1 | Recovery Path 2 | Recovery Path 3 |
|------------|-----------------|-----------------|-----------------|
| pip not found | Use `python3 -m pip` | Use system package manager | Manual download |
| Network timeout | Use Tsinghua mirror | Use Douban mirror | Retry with backoff |
| Permission denied | Use `--user` flag | Use virtualenv | Suggest sudo |
| tccli not found | `pip install tccli` | `pip install --user tccli` | `python3 -m pip install tccli` |
| SDK not found | `pip install tencentcloud-sdk-python-tke` | Mirror install | Install full SDK |
| Credential invalid | HALT (user must fix) | HALT | HALT |

## Multi-Path Recovery Scripts

### CLI Installation with Healing

```bash
install_tccli_with_healing() {
  # Path 1: Standard pip
  pip install tccli && return 0
  
  # Path 2: python -m pip
  python3 -m pip install tccli && return 0
  
  # Path 3: --user flag
  pip install --user tccli && export PATH="$HOME/.local/bin:$PATH" && return 0
  
  # Path 4: Tsinghua mirror
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple tccli && return 0
  
  # Graceful degradation
  echo "⚠️ tccli installation failed. Attempting Python SDK fallback."
  return 1
}
```

### SDK Installation with Healing

```bash
install_tke_sdk() {
  pip install tencentcloud-sdk-python-tke && return 0
  pip install --user tencentcloud-sdk-python-tke && return 0
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple tencentcloud-sdk-python-tke && return 0
  pip install tencentcloud-sdk-python && return 0  # Full SDK as fallback
  echo "⚠️ TKE SDK installation failed."
  return 1
}
```

## Health Verification

```bash
calculate_health_score() {
  SCORE=0
  
  python3 --version &> /dev/null && SCORE=$((SCORE + 2))
  command -v tccli &> /dev/null && SCORE=$((SCORE + 3))
  python3 -c "from tencentcloud.tke import tke_client" 2>/dev/null && SCORE=$((SCORE + 2))
  test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY" && SCORE=$((SCORE + 2))
  test -n "$TENCENTCLOUD_REGION" && SCORE=$((SCORE + 1))
  
  echo "Health score: $SCORE/10"
  [ $SCORE -ge 8 ]
}
```

## Connectivity Verification

```bash
verify_tke_connectivity() {
  tccli tke DescribeClusters --Region "$TENCENTCLOUD_REGION" --Offset 0 --Limit 1 &> /dev/null
  if [ $? -eq 0 ]; then
    echo "✅ TKE API connectivity verified"
    return 0
  else
    echo "⚠️ TKE API connectivity failed"
    return 1
  fi
}
```

## Graceful Degradation

| Component | Required | Degradation if Missing |
|-----------|----------|------------------------|
| Python 3.8+ | Yes | HALT — cannot execute SDK fallback |
| Credentials | Yes | HALT — cannot authenticate |
| Region | Yes | Ask user for region |
| tccli CLI | Recommended | Use Python SDK fallback |
| tke SDK | Recommended | Use CLI primary path |