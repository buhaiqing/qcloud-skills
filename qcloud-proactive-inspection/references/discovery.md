# Discovery Patterns — Proactive Inspection

## Resource Enumeration

### CVM Discovery
```bash
# All instances in region
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100
# By tag
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} \
  --Filters '[{"Name":"tag:Environment","Values":["Production"]}]'
# By status
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} \
  --Filters '[{"Name":"instance-state","Values":["RUNNING"]}]'
```

### Redis Discovery
```bash
tccli redis DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100
```

### CDB Discovery
```bash
tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100
```

### Paginated Discovery (Python)
```python
def discover_all(client, describe_method, region, limit=100):
    resources = []
    offset = 0
    while True:
        resp = describe_method(Region=region, Offset=offset, Limit=limit)
        items = getattr(resp, resp._answer_member, [])
        resource_type = resp._response._root_elem
        resources.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return resources
```

## Resource Inventory Schema

| Field | Source | Purpose |
|-------|--------|---------|
| resource_id | API response | Unique identifier |
| resource_name | API response | Human-readable name |
| resource_type | Skill context | Product type (cvm, redis, cdb) |
| zone | API response | Availability zone |
| status | API response | Current state |
| instance_type | API response | Spec (CPU/memory) |
| tags | API response | Environment/project tags |
| created_time | API response | Age analysis |
| expiry_time | API response (if prepaid) | Expiry warning |
| vpc_id | API response | Network context |
| subnet_id | API response | Network context |
