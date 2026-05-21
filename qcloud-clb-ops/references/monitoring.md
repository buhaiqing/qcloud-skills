# CLB Monitoring

## Monitor Namespace

CLB metrics are in namespace: **`QCE/LB_PUBLIC`** (public CLB) and **`QCE/LB_PRIVATE`** (internal CLB)

## Key Metrics

### Traffic Metrics
| Metric | Unit | Description |
|--------|------|-------------|
| `ClientConnum` | Count | Client connections per second |
| `ClientOutputTraffic` | Bytes | Outbound traffic from client perspective |
| `ClientInputTraffic` | Bytes | Inbound traffic from client perspective |
| `TrafficOut` | Bytes | Outbound traffic (backend → client) |
| `TrafficIn` | Bytes | Inbound traffic (client → backend) |

### Connection Metrics
| Metric | Unit | Description |
|--------|------|-------------|
| `Connum` | Count | Active connections |
| `NewConn` | Count | New connections per second |
| `HttpCode2XX` | Count | HTTP 2XX responses |
| `HttpCode3XX` | Count | HTTP 3XX responses |
| `HttpCode4XX` | Count | HTTP 4XX responses |
| `HttpCode5XX` | Count | HTTP 5XX responses |

### Health Metrics
| Metric | Unit | Description |
|--------|------|-------------|
| `HealthCheckCode` | Code | Health check status code |
| `HealthCheckFailedNum` | Count | Failed health checks |

### Dimension

Use `LoadBalancerId` as dimension for metric queries:

```bash
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "ClientConnum" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"lb-xxx\"}]"
```

## Recommended Alarm Policies

### High Connection Alert
```json
{
  "Namespace": "QCE/LB_PUBLIC",
  "MetricName": "ClientConnum",
  "CalcType": "Greater",
  "CalcValue": "10000",
  "ContinueTime": 60
}
```

### HTTP Error Alert
```json
{
  "Namespace": "QCE/LB_PUBLIC",
  "MetricName": "HttpCode5XX",
  "CalcType": "Greater",
  "CalcValue": "100",
  "ContinueTime": 60
}
```

### Backend Health Alert
```json
{
  "Namespace": "QCE/LB_PUBLIC",
  "MetricName": "HealthCheckFailedNum",
  "CalcType": "Greater",
  "CalcValue": "5",
  "ContinueTime": 60
}
```

## Dashboard Metrics

Recommended dashboard widgets:
1. Connection trend (ClientConnum)
2. Traffic bandwidth (TrafficIn/Out)
3. HTTP status distribution (2XX/4XX/5XX)
4. Backend health status
5. Response time (if HTTP)

## Monitoring Integration

```yaml
# CLB monitoring integration with qcloud-monitor-ops
namespace: QCE/LB_PUBLIC
dimension_key: LoadBalancerId
delegate_to: qcloud-clb-ops for backend operations
```