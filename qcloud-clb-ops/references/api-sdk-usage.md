# CLB API & SDK Usage

## Overview

This document covers the API operation map and Python SDK usage for CLB (Load Balancer).

---

## API Operation Map

### Instance Operations

| API | Required Parameters | Rate Limit |
|-----|---------------------|------------|
| `CreateLoadBalancer` | LoadBalancerType, VpcId | 20/s |
| `DescribeLoadBalancers` | LoadBalancerIds (optional) | 20/s |
| `ModifyLoadBalancerAttributes` | LoadBalancerId | 20/s |
| `DeleteLoadBalancer` | LoadBalancerId | 20/s |
| `DescribeLoadBalancersDetail` | LoadBalancerIds | 20/s |

### Listener Operations

| API | Required Parameters | Rate Limit |
|-----|---------------------|------------|
| `CreateListener` | LoadBalancerId, Protocol, Port | 20/s |
| `DescribeListeners` | LoadBalancerId | 20/s |
| `ModifyListener` | ListenerId | 20/s |
| `DeleteListener` | ListenerId | 20/s |
| `CreateRule` | ListenerId, Domain, Url | 20/s |

### Backend Operations

| API | Required Parameters | Rate Limit |
|-----|---------------------|------------|
| `RegisterTargets` | LoadBalancerId, ListenerId, Targets | 20/s |
| `DeregisterTargets` | LoadBalancerId, ListenerId, Targets | 20/s |
| `DescribeTargets` | LoadBalancerId | 20/s |
| `DescribeTargetHealth` | LoadBalancerId | 20/s |
| `ModifyTargetWeight` | Targets[].Weight | 20/s |

---

## Request/Response Schemas

### CreateLoadBalancer

**Request:**
```json
{
  "LoadBalancerType": "OPEN",          // OPEN/Internal
  "VpcId": "vpc-abc123",               // Required
  "LoadBalancerName": "my-lb",         // Optional
  "SubnetId": "subnet-xxx",            // Optional
  "ProjectId": 0,                      // Optional
  "AddressIPVersion": "IPv4",          // IPv4/IPv6/IPv6FullChain
  "ChargeType": "POSTPAID",            // POSTPAID/PREPAID
  "BandwidthPackageId": ""             // Optional
}
```

**Response:**
```json
{
  "Response": {
    "LoadBalancerIds": ["lb-abc123"],
    "RequestId": "req-xxx"
  }
}
```

### RegisterTargets

**Request:**
```json
{
  "LoadBalancerId": "lb-abc123",
  "ListenerId": "listener-xxx",
  "Targets": [
    {
      "InstanceId": "ins-server1",
      "Port": 8080,
      "Weight": 10
    }
  ]
}
```

**Response:**
```json
{
  "Response": {
    "RequestId": "req-xxx"
  }
}
```

---

## Python SDK Usage

### Setup

```bash
pip install tencentcloud-sdk-python-clb
```

### Client Initialization

```python
import os
from tencentcloud.common import credential
from tencentcloud.clb.v20180317 import clb_client, models

# Initialize credential
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Initialize client
client = clb_client.ClbClient(cred, "ap-guangzhou")
```

### Create LoadBalancer

```python
def create_load_balancer(client, vpc_id, lb_name, lb_type="OPEN"):
    # Create a new LoadBalancer
    req = models.CreateLoadBalancerRequest()
    req.LoadBalancerType = lb_type
    req.VpcId = vpc_id
    req.LoadBalancerName = lb_name
    
    resp = client.CreateLoadBalancer(req)
    return resp.LoadBalancerIds[0]

# Usage
lb_id = create_load_balancer(client, "vpc-abc123", "web-lb")
print(f"Created LB: {lb_id}")
```

### Describe LoadBalancers

```python
def describe_load_balancers(client, lb_ids=None):
    # Query LoadBalancer instances
    req = models.DescribeLoadBalancersRequest()
    
    if lb_ids:
        req.LoadBalancerIds = lb_ids
    
    resp = client.DescribeLoadBalancers(req)
    
    return [
        {
            "LoadBalancerId": lb.LoadBalancerId,
            "LoadBalancerName": lb.LoadBalancerName,
            "Status": lb.Status,
            "VipIps": lb.VipIps
        }
        for lb in resp.LoadBalancerSet
    ]
```

### Create Listener

```python
def create_listener(client, lb_id, protocol, port, name=None):
    # Create a listener
    req = models.CreateListenerRequest()
    req.LoadBalancerId = lb_id
    req.Protocol = protocol  # TCP/UDP/HTTP/HTTPS
    req.Port = port
    req.ListenerName = name or f"{protocol}-{port}"
    
    resp = client.CreateListener(req)
    return resp.ListenerIds[0]
```

### Register Targets

```python
def register_targets(client, lb_id, listener_id, targets):
    # Bind backend servers
    req = models.RegisterTargetsRequest()
    req.LoadBalancerId = lb_id
    req.ListenerId = listener_id
    
    req.Targets = [
        models.Target()
        for t in targets
    ]
    
    for i, t in enumerate(targets):
        req.Targets[i].InstanceId = t["InstanceId"]
        req.Targets[i].Port = t["Port"]
        req.Targets[i].Weight = t.get("Weight", 10)
    
    resp = client.RegisterTargets(req)
    return resp.RequestId
```

### Check Target Health

```python
def check_target_health(client, lb_id):
    # Check backend server health status
    req = models.DescribeTargetHealthRequest()
    req.LoadBalancerId = lb_id
    
    resp = client.DescribeTargetHealth(req)
    
    return [
        {
            "InstanceId": t.InstanceId,
            "Port": t.Port,
            "HealthStatus": t.HealthStatus
        }
        for t in resp.Targets
    ]
```

---

## Pagination Handling

```python
def describe_all_load_balancers(client):
    # Paginate through all LoadBalancers
    req = models.DescribeLoadBalancersRequest()
    req.Limit = 100
    req.Offset = 0
    
    all_lbs = []
    
    while True:
        resp = client.DescribeLoadBalancers(req)
        all_lbs.extend(resp.LoadBalancerSet)
        
        if len(resp.LoadBalancerSet) < 100:
            break
        
        req.Offset += 100
    
    return all_lbs
```

---

## Error Handling

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

def safe_create_lb(client, vpc_id, lb_name):
    # Create LB with error handling
    try:
        lb_id = create_load_balancer(client, vpc_id, lb_name)
        return {"success": True, "lb_id": lb_id}
    
    except TencentCloudSDKException as e:
        return {
            "success": False,
            "error_code": e.code,
            "message": e.message,
            "request_id": e.requestId
        }
```

---

## Required vs Optional Parameters

### CreateLoadBalancer

| Parameter | Required | Notes |
|-----------|----------|-------|
| LoadBalancerType | ✓ | OPEN or Internal |
| VpcId | ✓ | VPC ID |
| LoadBalancerName | ✗ | Default: lb-xxx |
| SubnetId | ✗ | Auto-selected if omitted |
| AddressIPVersion | ✗ | Default IPv4 |

### CreateListener

| Parameter | Required | Notes |
|-----------|----------|-------|
| LoadBalancerId | ✓ | LB instance ID |
| Protocol | ✓ | TCP/UDP/HTTP/HTTPS |
| Port | ✓ | Listener port |
| ListenerName | ✗ | Auto-generated |
| CertificateSSLId | ✓ (HTTPS) | SSL certificate ID |