# Rate Limiting and Retry Strategies

> **Operational guidelines for API rate limiting and retry strategies** in AIOps diagnosis operations. Ensures robust execution under API constraints.

## 1. Rate Limiting

### 1.1 Tencent Cloud API Rate Limits

| API Category | Typical Rate Limit | Notes |
|---|---|---|
| **Monitor APIs** | 20 requests/second | GetMonitorData, DescribeBaseMetrics |
| **Product APIs** | 10-20 requests/second | Varies by product (CVM, CDB, etc.) |
| **CLS APIs** | 10 requests/second | GetLogRecords, DescribeTopics |
| **CAM APIs** | 10 requests/second | Read-only operations |

### 1.2 Rate Limiting Strategy

#### Token Bucket Algorithm
```python
class RateLimiter:
    def __init__(self, rate: int, burst: int):
        self.rate = rate  # requests per second
        self.burst = burst  # maximum burst size
        self.tokens = burst
        self.last_time = time.time()
    
    def acquire(self) -> bool:
        now = time.time()
        elapsed = now - self.last_time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_time = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

#### Application-Level Rate Limiting
- **Per-API rate limiting**: Different limits for different API categories
- **Per-skill rate limiting**: Limit total API calls per diagnosis session
- **Adaptive rate limiting**: Adjust based on API response headers

### 1.3 Rate Limit Headers

Monitor these headers from API responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when window resets

## 2. Retry Strategies

### 2.1 Retry Decision Matrix

| Error Type | Retry? | Strategy | Max Retries |
|---|---|---|---|
| **Transient Errors** | Yes | Exponential backoff | 3 |
| **Rate Limit Exceeded** | Yes | Linear backoff | 5 |
| **Authentication Error** | No | HALT | 0 |
| **Invalid Parameter** | No | HALT | 0 |
| **Resource Not Found** | No | HALT | 0 |
| **Internal Server Error** | Yes | Exponential backoff | 3 |
| **Service Unavailable** | Yes | Exponential backoff | 5 |

### 2.2 Exponential Backoff

```python
def exponential_backoff(retry_count: int, base_delay: float = 1.0) -> float:
    """Calculate exponential backoff delay."""
    import random
    
    # Exponential backoff with jitter
    delay = base_delay * (2 ** retry_count)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter
```

**Configuration**:
- Base delay: 1 second
- Maximum delay: 60 seconds
- Jitter: 10% of delay
- Maximum retries: 3

### 2.3 Linear Backoff (for Rate Limits)

```python
def linear_backoff(retry_count: int, base_delay: float = 1.0) -> float:
    """Calculate linear backoff for rate limits."""
    return base_delay * retry_count
```

**Configuration**:
- Base delay: 1 second
- Maximum delay: 30 seconds
- Maximum retries: 5

### 2.4 Retry with Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
```

## 3. Implementation Guidelines

### 3.1 Pre-flight Rate Limit Check

Before executing API calls:
1. Check rate limit headers from previous responses
2. Calculate required API calls for the operation
3. If insufficient quota, wait or degrade gracefully

### 3.2 Retry Execution Flow

```
1. Attempt API call
2. On success:
   → Record success in circuit breaker
   → Return result
3. On failure:
   → Check error type
   → If retryable:
     → Increment retry count
     → Calculate backoff delay
     → Wait delay
     → Retry from step 1
   → If not retryable:
     → HALT with error message
     → Record failure in circuit breaker
```

### 3.3 Graceful Degradation

When rate limits or failures prevent full execution:

1. **Partial Results**: Return available results with warnings
2. **Static Fallback**: Use cached or static data when API unavailable
3. **Simplified Analysis**: Reduce scope of analysis to stay within limits
4. **User Notification**: Clearly communicate degraded state

### 3.4 Monitoring and Alerting

Monitor these metrics:
- **API success rate**: Alert if < 95%
- **Retry rate**: Alert if > 20% of requests are retried
- **Circuit breaker trips**: Alert when circuit opens
- **Rate limit hits**: Track frequency of rate limit errors

## 4. AIOps-Specific Considerations

### 4.1 Diagnosis Session Rate Budget

For a typical diagnosis session:
- **Maximum API calls**: 100 calls per session
- **Rate budget allocation**:
  - Metric queries: 60% (60 calls)
  - Log queries: 20% (20 calls)
  - Product queries: 20% (20 calls)

### 4.2 Multi-Metric Correlation

When correlating multiple metrics:
1. **Sequential queries**: Avoid parallel API calls to prevent rate limiting
2. **Batch queries**: Use batch APIs where available (e.g., GetMonitorData supports multiple metrics)
3. **Caching**: Cache results for repeated queries within the same session

### 4.3 Cross-Skill Delegation

When delegating to other skills:
1. **Rate limit awareness**: Each delegated skill consumes from the same rate budget
2. **Quota sharing**: Coordinate API calls across skills to avoid exceeding limits
3. **Fallback strategies**: If delegated skill fails due to rate limits, proceed with available data

## 5. Error Handling Examples

### 5.1 Rate Limit Exceeded

```python
def handle_rate_limit(retry_count: int) -> dict:
    """Handle rate limit exceeded error."""
    if retry_count < 5:
        delay = linear_backoff(retry_count)
        time.sleep(delay)
        return {"action": "retry", "delay": delay}
    else:
        return {
            "action": "halt",
            "error": "Rate limit exceeded after 5 retries",
            "suggestion": "Reduce API call frequency or wait before retrying"
        }
```

### 5.2 Transient Error with Exponential Backoff

```python
def handle_transient_error(retry_count: int) -> dict:
    """Handle transient errors with exponential backoff."""
    if retry_count < 3:
        delay = exponential_backoff(retry_count)
        time.sleep(delay)
        return {"action": "retry", "delay": delay}
    else:
        return {
            "action": "halt",
            "error": "Persistent transient error",
            "suggestion": "Check service status or contact support"
        }
```

### 5.3 Circuit Breaker Trip

```python
def handle_circuit_breaker_trip() -> dict:
    """Handle circuit breaker trip."""
    return {
        "action": "degrade",
        "error": "Circuit breaker tripped due to repeated failures",
        "suggestion": "Using cached data or static thresholds",
        "fallback_strategy": "static_thresholds"
    }
```

## 6. Best Practices

1. **Always implement retry logic** for transient errors
2. **Use exponential backoff** with jitter to avoid thundering herd
3. **Implement circuit breakers** to prevent cascade failures
4. **Monitor rate limit headers** and adjust behavior proactively
5. **Provide graceful degradation** when rate limits are hit
6. **Log all retry attempts** for debugging and monitoring
7. **Set reasonable timeouts** to prevent hanging requests
8. **Use batch APIs** where available to reduce total API calls

## 7. Reference

- [AGENTS.md §9 Anti-patterns](../../AGENTS.md#9-anti-patterns-banned)
- [troubleshooting.md](troubleshooting.md)
- [anomaly-detection.md](anomaly-detection.md)
- [multi-source-rca.md](multi-source-rca.md)