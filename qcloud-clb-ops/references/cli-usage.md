# CLB CLI Usage

## Overview

This document covers `tccli clb` commands for Load Balancer operations. CLI is the **primary execution path** per `cli_applicability: dual-path`.

## Prerequisites

```bash
# Install CLI
pip install tccli

# Configure credentials
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

## Core Commands

### Instance Operations

```bash
# Create load balancer
tccli clb CreateLoadBalancer \
  --LoadBalancerType "OPEN" \
  --VpcId "vpc-xxx" \
  --LoadBalancerName "my-lb"

# Describe load balancers
tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"lb-xxx\"]"

# List all load balancers
tccli clb DescribeLoadBalancers

# Modify load balancer attributes
tccli clb ModifyLoadBalancerAttributes \
  --LoadBalancerId "lb-xxx" \
  --LoadBalancerName "new-name"

# Delete load balancer
tccli clb DeleteLoadBalancer \
  --LoadBalancerId "lb-xxx"
```

### Listener Operations

```bash
# Create TCP listener
tccli clb CreateListener \
  --LoadBalancerId "lb-xxx" \
  --Protocol "TCP" \
  --Port 80 \
  --ListenerName "tcp-listener"

# Create HTTP listener
tccli clb CreateListener \
  --LoadBalancerId "lb-xxx" \
  --Protocol "HTTP" \
  --Port 80 \
  --ListenerName "http-listener"

# Create HTTPS listener
tccli clb CreateListener \
  --LoadBalancerId "lb-xxx" \
  --Protocol "HTTPS" \
  --Port 443 \
  --ListenerName "https-listener" \
  --CertificateSSLId "cert-xxx"

# Describe listeners
tccli clb DescribeListeners \
  --LoadBalancerId "lb-xxx"

# Delete listener
tccli clb DeleteListener \
  --LoadBalancerId "lb-xxx" \
  --ListenerId "listener-xxx"
```

### Backend Server Operations

```bash
# Register targets (bind backend)
tccli clb RegisterTargets \
  --LoadBalancerId "lb-xxx" \
  --ListenerId "listener-xxx" \
  --Targets "[{\"InstanceId\":\"ins-xxx\",\"Port\":8080,\"Weight\":10}]"

# Batch register targets
tccli clb BatchRegisterTargets \
  --LoadBalancerId "lb-xxx" \
  --ListenerId "listener-xxx" \
  --Targets "[{\"InstanceId\":\"ins-1\",\"Port\":8080,\"Weight\":10},{\"InstanceId\":\"ins-2\",\"Port\":8080,\"Weight\":10}]"

# Describe targets
tccli clb DescribeTargets \
  --LoadBalancerId "lb-xxx" \
  --ListenerIds "[\"listener-xxx\"]"

# Check target health
tccli clb DescribeTargetHealth \
  --LoadBalancerId "lb-xxx"

# Modify target weight
tccli clb ModifyTargetWeight \
  --LoadBalancerId "lb-xxx" \
  --ListenerId "listener-xxx" \
  --Targets "[{\"InstanceId\":\"ins-xxx\",\"Port\":8080,\"Weight\":20}]"

# Deregister targets (unbind backend)
tccli clb DeregisterTargets \
  --LoadBalancerId "lb-xxx" \
  --ListenerId "listener-xxx" \
  --Targets "[{\"InstanceId\":\"ins-xxx\",\"Port\":8080}]"
```

### Target Group Operations

```bash
# Create target group
tccli clb CreateTargetGroup \
  --TargetGroupName "my-group" \
  --VpcId "vpc-xxx"

# Register instances to target group
tccli clb RegisterTargetGroupInstances \
  --TargetGroupId "targetgroup-xxx" \
  --TargetGroupInstances "[{\"InstanceId\":\"ins-xxx\",\"Port\":8080,\"Weight\":10}]"

# Describe target groups
tccli clb DescribeTargetGroups \
  --TargetGroupIds "[\"targetgroup-xxx\"]"
```

## JSON Output Parsing

```bash
# Get LoadBalancer ID
LB_ID=$(tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"lb-xxx\"]" | jq -r '.Response.LoadBalancerSet[0].LoadBalancerId')

# Get Listener ID
LISTENER_ID=$(tccli clb DescribeListeners --LoadBalancerId "lb-xxx" | jq -r '.Response.ListenerSet[0].ListenerId')

# Check health status
HEALTH=$(tccli clb DescribeTargetHealth --LoadBalancerId "lb-xxx" | jq -r '.Response.Targets[0].HealthStatus')
```

## CLI Coverage Gaps

Operations not exposed via CLI (requires SDK):

| Operation | CLI Status | SDK Alternative |
|-----------|------------|-----------------|
| SetLoadBalancerClsLog | Not exposed | Use SDK for log integration |
| CreateClsLogSet | Not exposed | Use SDK for log set creation |

## Rate Limits

All CLB APIs share a rate limit of 20 requests per second. Check current limits via API documentation at `https://cloud.tencent.com/document/api/214`.

## Error Handling Patterns

```bash
# Check for errors
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"lb-invalid\"]" | jq '.Response.Error'

# Common error check
if tccli clb CreateLoadBalancer ... | jq -e '.Response.Error' > /dev/null; then
  echo "Error detected"
fi
```