# Troubleshooting Playbook

## Symptom -> Cause -> Fix

### Sandbox instance fails to start (timeout)

| Possible Cause | Diagnostic | Fix |
|---|---|---|
| Image not pre-cached | DescribeSandboxToolList shows WarmCount=0 | Call CreatePreCacheImageTask with Image name |
| Quota exhausted | Error code QuotaExceeded | Apply quota increase in console |
| Image build broken | Tool status ImageBuildFailed | Rebuild image, check Dockerfile |

### e2b client cannot connect

Error example: WebSocket connection to wss://si-xxx.tencentags.com failed

| Check | Command |
|---|---|
| API key valid | DescribeAPIKey returns Status=Active |
| Instance running | DescribeSandboxInstanceList returns Status=Running |
| Domain matches region | E2B_DOMAIN equals region.tencentags.com |
| Network egress | curl -v https://ap-guangzhou.tencentags.com/health |

### RequestLimitExceeded under load

- Default TPS: 20/s per account on Create APIs.
- Fix: Exponential backoff, batch via single CreateSandboxTool then reuse via many StartSandboxInstance calls.

### InvalidSecretKey after key rotation

1. Verify env vars TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY updated.
2. Check CAM console for key status.
3. Confirm key has policy QcloudAGSFullAccess or QcloudAGSReadOnlyAccess.

### Instance terminated unexpectedly before 24h

| Cause | Evidence |
|---|---|
| OOM kill | CLS log shows OOMKilled |
| Tool deleted | Audit log: DeleteSandboxTool |
| Manual stop | Audit log: StopSandboxInstance |
| Spec mismatch | Tool MemorySpec less than workload requirement |

### CLS logs missing

- Confirm sandbox tool has LoggingConfig.Enabled=true.
- Check CLS logset ags-sandbox-logs exists in same region.
- IAM: sandbox role needs cls:UploadLog permission.

## Escalation

- Ticket: https://console.cloud.tencent.com/workorder/category
- Provide: RequestId, ToolId/InstanceId, region, timestamp (UTC).
