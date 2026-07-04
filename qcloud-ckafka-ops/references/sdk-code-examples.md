# SDK Code Examples

This file contains Python SDK code examples extracted from the main SKILL.md for better readability and maintenance.

## CreateInstance - SDK Polling with Adaptive Backoff

```python
# SDK polling with adaptive backoff
# Phase 1: Fast polling (first 5 min) - check every 10s
# Phase 2: Slow polling (after 5 min) - check every 30s
# Total timeout: 20 minutes
import time

for i in range(50):
    desc_req = models.DescribeInstancesRequest()
    desc_req.InstanceIds = ["{{output.instance_id}}"]
    resp = client.DescribeInstances(desc_req)
    status = json.loads(resp.to_json_string())["Response"]["Result"][0]["Status"]
    if status == 1:
        break
    # Adaptive sleep: 10s for first 30 checks (5 min), then 30s
    sleep_time = 10 if i < 30 else 30
    time.sleep(sleep_time)

# Check timeout
if status != 1:
    raise TimeoutError(f"CKafka instance not ready after 20 min (status: {status})")
```

**Context**: This code is used in the Post-execution Validation phase of the CreateInstance operation to poll until the CKafka instance reaches running status (Status = 1).