# Enhanced Self-Healing Framework (Redis)

## Overview

Mandatory self-healing patterns for Redis skill installation and setup flows.

## Pre-flight Checks

```bash
check_python() {
  python3 --version 2>/dev/null | grep -qE "3\.[89]|3\.1[0-9]" && return 0
  return 1
}

check_tccli() {
  command -v tccli &> /dev/null && tccli redis help CreateInstance &> /dev/null && return 0
  return 1
}

check_sdk() {
  python3 -c "from tencentcloud.redis import redis_client" 2>/dev/null && return 0
  return 1
}

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
| pip not found | Use `python3 -m pip` | System package manager | Manual download |
| Network timeout | Tsinghua mirror | Douban mirror | Retry with backoff |
| Permission denied | Use `--user` flag | Use virtualenv | Suggest sudo |
| tccli not found | `pip install tccli` | `pip install --user tccli` | `python3 -m pip install tccli` |
| SDK not found | `pip install tencentcloud-sdk-python-redis` | Mirror install | Full SDK |
| Credential invalid | HALT (user must fix) | HALT | HALT |

## Multi-Path Recovery Scripts

### CLI Installation

```bash
install_tccli() {
  pip install tccli && return 0
  python3 -m pip install tccli && return 0
  pip install --user tccli && export PATH="$HOME/.local/bin:$PATH" && return 0
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple tccli && return 0
  echo "⚠️ tccli installation failed. Using SDK fallback."
  return 1
}
```

### SDK Installation

```bash
install_redis_sdk() {
  pip install tencentcloud-sdk-python-redis && return 0
  pip install --user tencentcloud-sdk-python-redis && return 0
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple tencentcloud-sdk-python-redis && return 0
  pip install tencentcloud-sdk-python && return 0
  echo "⚠️ Redis SDK installation failed."
  return 1
}
```

## Health Verification

```bash
calculate_health_score() {
  SCORE=0
  python3 --version &> /dev/null && SCORE=$((SCORE + 2))
  command -v tccli &> /dev/null && SCORE=$((SCORE + 3))
  python3 -c "from tencentcloud.redis import redis_client" 2>/dev/null && SCORE=$((SCORE + 2))
  test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY" && SCORE=$((SCORE + 2))
  test -n "$TENCENTCLOUD_REGION" && SCORE=$((SCORE + 1))
  echo "Health score: $SCORE/10"
  [ $SCORE -ge 8 ]
}
```

## Connectivity Verification

```bash
verify_redis_connectivity() {
  tccli redis DescribeInstanceList --Region "$TENCENTCLOUD_REGION" --Offset 0 --Limit 1 &> /dev/null
  if [ $? -eq 0 ]; then
    echo "✅ Redis API connectivity verified"
    return 0
  else
    echo "⚠️ Redis API connectivity failed"
    return 1
  fi
}
```