# VPC SDK Templates

> **Init/poll/error boilerplate** for Python SDK fallback paths.

## Common Imports

```python
#!/usr/bin/env python3
import os
import json
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.vpc import vpc_client, models
```

## Client Initialization

```python
def init_vpc_client():
    """Initialize VPC client with environment credentials."""
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    
    httpProfile = HttpProfile()
    httpProfile.endpoint = "vpc.tencentcloudapi.com"
    
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    
    return vpc_client.VpcClient(
        cred, 
        os.environ.get("TENCENTCLOUD_REGION"),
        clientProfile
    )
```

## Error Handling Pattern

```python
def handle_vpc_error(e):
    """Handle VPC API errors with retry logic."""
    error_code = e.code
    error_message = e.message
    
    # Retryable errors
    retryable_errors = [
        'RequestLimitExceeded',
        'InternalError',
        'OperationConflict'
    ]
    
    if error_code in retryable_errors:
        return {'retry': True, 'wait': 2}
    
    # Fatal errors
    fatal_errors = [
        'InvalidSecretKey',
        'InvalidSecretId',
        'ResourceQuotaExceeded.Vpc',
        'ResourceQuotaExceeded.Subnet'
    ]
    
    if error_code in fatal_errors:
        return {'retry': False, 'halt': True}
    
    # Other errors
    return {'retry': False, 'halt': False}
```

## Polling Pattern

```python
def poll_resource_status(client, resource_type, resource_id, target_status, max_wait=120):
    """Poll resource status until target or timeout."""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if resource_type == 'vpc':
            req = models.DescribeVpcsRequest()
            req.VpcIds = [resource_id]
            resp = client.DescribeVpcs(req)
            status = resp.Response.VpcSet[0].State if resp.Response.VpcSet else None
            
        elif resource_type == 'subnet':
            req = models.DescribeSubnetsRequest()
            req.SubnetIds = [resource_id]
            resp = client.DescribeSubnets(req)
            status = resp.Response.SubnetSet[0].State if resp.Response.SubnetSet else None
            
        elif resource_type == 'route_table':
            req = models.DescribeRouteTablesRequest()
            req.RouteTableIds = [resource_id]
            resp = client.DescribeRouteTables(req)
            status = resp.Response.RouteTableSet[0].State if resp.Response.RouteTableSet else None
        
        if status == target_status:
            return {'success': True, 'status': status}
        
        if status in ['DELETED', 'DELETING', 'FAILED']:
            return {'success': False, 'status': status, 'error': 'Resource in terminal state'}
        
        time.sleep(5)
    
    return {'success': False, 'status': status, 'error': 'Timeout'}
```

## Idempotency Token

```python
def generate_client_token():
    """Generate idempotency token."""
    return str(int(time.time() * 1000000))
```

## Response Parsing

```python
def parse_vpc_response(resp):
    """Parse VPC API response to standard format."""
    if hasattr(resp, 'Response') and hasattr(resp.Response, 'Error'):
        return {
            'success': False,
            'error': {
                'code': resp.Response.Error.Code,
                'message': resp.Response.Error.Message,
                'request_id': resp.Response.RequestId
            }
        }
    
    return {
        'success': True,
        'data': json.loads(resp.to_json_string()),
        'request_id': resp.Response.RequestId
    }
```
