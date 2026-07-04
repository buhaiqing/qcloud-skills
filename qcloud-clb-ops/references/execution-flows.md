---
description: Detailed CLI/SDK execution flows for CLB operations — how to execute each operation
---

# CLB Execution Flows (How-To)

This file contains the detailed CLI/SDK command blocks for each CLB operation.
SKILL.md provides the high-level "what to do" description.

## Index

| Section | Operation | CLI Command | SDK Command |
|---------|-----------|------------|-------------|
| 1 | Create LoadBalancer | `tccli clb CreateLoadBalancer` | `clb_client.CreateLoadBalancer()` |
| 2 | Describe LoadBalancers | `tccli clb DescribeLoadBalancers` | — |
| 3 | Create Listener | `tccli clb CreateListener` | `clb_client.CreateListener()` |
| 4 | Register Targets | `tccli clb RegisterTargets` | `clb_client.RegisterTargets()` |
| 5 | Describe Target Health | `tccli clb DescribeTargetHealth` | `clb_client.DescribeTargetHealth()` |
| 6 | Delete LoadBalancer | `tccli clb DeleteLoadBalancer` | — |
| — | CreateLoadBalancer Polling | `tccli clb DescribeLoadBalancers` | — |

---

## 1. Create LoadBalancer

### CLI (`tccli`)

```bash
tccli clb CreateLoadBalancer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerType "OPEN" \
  --VpcId "{{user.vpc_id}}" \
  --LoadBalancerName "{{user.loadbalancer_name}}"
```

### Python SDK

```python
#!/usr/bin/env python3
"""
SDK fallback script for CLB CreateLoadBalancer
"""
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateLoadBalancerRequest()
        req.LoadBalancerType = "OPEN"
        req.VpcId = "{{user.vpc_id}}"
        req.LoadBalancerName = "{{user.loadbalancer_name}}"

        resp = client.CreateLoadBalancer(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Validation (Polling)

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"{{output.loadbalancer_id}}\"]" | jq -r '.Response.LoadBalancerSet[0].Status')
  [ "$STATUS" = "2" ] && break
  sleep 5
done
```

---

## 2. Describe LoadBalancers

### CLI (`tccli`)

```bash
tccli clb DescribeLoadBalancers --Region {{env.TENCENTCLOUD_REGION}} --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]"
```

---

## 3. Create Listener

### CLI (`tccli`)

```bash
tccli clb CreateListener \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Protocol "{{user.listener_protocol}}" \
  --Port "{{user.listener_port}}" \
  --ListenerName "{{user.listener_name}}"
```

### Python SDK

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateListenerRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"
        req.Protocol = "{{user.listener_protocol}}"
        req.Port = {{user.listener_port}}
        req.ListenerName = "{{user.listener_name}}"

        resp = client.CreateListener(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## 4. Register Targets (Bind Backend Servers)

### CLI (`tccli`)

```bash
tccli clb RegisterTargets \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --ListenerId "{{user.listener_id}}" \
  --Targets "[\"InstanceId\":\"{{user.instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":{{user.target_weight}}}]"
```

### Python SDK

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.RegisterTargetsRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"
        req.ListenerId = "{{user.listener_id}}"

        target = models.Target()
        target.InstanceId = "{{user.instance_id}}"
        target.Port = {{user.target_port}}
        target.Weight = {{user.target_weight}}
        req.Targets = [target]

        resp = client.RegisterTargets(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## 5. Describe Target Health

### CLI (`tccli`)

```bash
tccli clb DescribeTargetHealth \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}"
```

### Python SDK

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = clb_client.ClbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.DescribeTargetHealthRequest()
        req.LoadBalancerId = "{{user.loadbalancer_id}}"

        resp = client.DescribeTargetHealth(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## 6. Delete LoadBalancer

### CLI (`tccli`)

```bash
tccli clb DeleteLoadBalancer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LoadBalancerId "{{user.loadbalancer_id}}"
```

---

## Pre-flight Check Commands

### Verify Python SDK

```bash
pip show tencentcloud-sdk-python-clb
```

### Verify CLI

```bash
tccli version
```

### Verify VPC Exists

```bash
tccli vpc DescribeVpcs --Region {{env.TENCENTCLOUD_REGION}}
```

### Verify LoadBalancer Exists

```bash
tccli clb DescribeLoadBalancers --Region {{env.TENCENTCLOUD_REGION}} --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]"
```

### Verify CVM Instance (via CVM skill)

```bash
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --InstanceIds "[\"{{user.instance_id}}\"]"
```

---

## Environment Setup

### Install tccli

```bash
pip install tccli
```

### Install Python SDK

```bash
pip install tencentcloud-sdk-python-clb
```

### Configure Credentials

```bash
export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
```

### Verify Configuration

```bash
tccli clb DescribeLoadBalancers --Region ap-guangzhou
```
