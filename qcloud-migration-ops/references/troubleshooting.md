# Migration Troubleshooting

## Common Migration Issues

### Host Migration Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Agent connection failed | Network/firewall blocking | Open required ports (443, 80) |
| Disk space error | Insufficient temp space | Free up disk space or add volume |
| Driver compatibility | Unsupported hardware | Use compatible target instance type |
| Migration speed slow | Bandwidth limitation | Schedule during off-peak hours |
| Boot failure after migration | Driver/UUID mismatch | Update fstab, reinstall drivers |

### Database Migration Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Connection timeout | Network/security group | Check security group rules |
| Replication lag | High write throughput | Increase DTS instance specs |
| Schema incompatibility | Version/feature mismatch | Review compatibility matrix |
| Data inconsistency | Concurrent writes | Enable consistency check |
| Permission denied | Insufficient privileges | Grant required database permissions |

### Storage Migration Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Transfer failed | Object too large | Use multipart upload |
| Checksum mismatch | Network corruption | Retry with verification |
| Rate limiting | Too many requests | Reduce concurrency, add backoff |
| Metadata loss | Unsupported attributes | Map attributes manually |

## Error Code Quick Reference

| Error Code | Meaning | Action |
|------------|---------|--------|
| `InvalidParameter` | Parameter validation failed | Check request parameters |
| `ResourceNotFound` | Resource doesn't exist | Verify resource ID |
| `ResourceQuotaExceeded` | Quota limit reached | Request quota increase |
| `OperationDenied` | Operation not allowed | Check permissions |
| `InternalError` | Service internal error | Retry with backoff |

## Debug Steps

1. **Verify source accessibility**:
   ```bash
   # Test network connectivity
   ping <source-ip>
   telnet <source-ip> <port>
   ```

2. **Check credentials**:
   ```bash
   # Verify source credentials
   test -n "$SOURCE_ACCESS_KEY" && echo "Source key set"
   ```

3. **Review migration logs**:
   ```bash
   # Check migration task logs
   tccli msp DescribeMigrationTask --TaskId <task-id>
   ```

4. **Validate target readiness**:
   ```bash
   # Check target resource status
   tccli cvm DescribeInstances --Filters "Name=instance-id,Values=<target-id>"
   ```

5. **Network path test**:
   ```bash
   # Test from source to Tencent Cloud
   curl -I https://msp.tencentcloudapi.com
   ```

## Cutover Failure Patterns

### Cutover Aborted — Sync Lag Exceeded

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Final sync lag > 60s before cutover | Source write rate exceeds sync bandwidth | Pause source writes; wait for lag to drop; consider off-hours cutover |
| Sync lag growing during cutover window | Network bandwidth contention | Increase DTS instance specs; schedule cutover during low-traffic window |

### Post-Cutover Application Failure

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Health endpoint returns 5xx | Target application config mismatch | **Immediate rollback**; compare env vars, config files, connection strings |
| SSL/TLS certificate error | Certificate not installed on target | Revert DNS; install certificate on target; retry |
| Database connection refused | Security group or network ACL blocking | Open target security group; verify VPC/ subnet routing |
| Performance degradation > 2x | Target instance under-sized | Scale up target spec; if > 5 min to scale, rollback first |

### Data Inconsistency Post-Cutover

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Row count mismatch | Some tables missed in final sync | Incremental sync affected tables; verify with checksum |
| Checksum mismatch | Write happened on source during final sync | Re-sync table; tighten write-block window |
| Missing objects (storage) | Object created after last sync | Manual object copy; set lifecycle policy for ongoing sync |
| Sequence/auto-increment mismatch | Source continued accepting writes | Reset sequences on target to MAX(source)+gap |

### Rollback Recovery

| Step | Command/Action | Verification |
|------|---------------|--------------|
| 1. Revert DNS/proxy | Update DNS A record or LB target group to source | `dig +short {{user.endpoint}}` returns source IP |
| 2. Verify source health | `curl https://{{user.source_endpoint}}/health` | HTTP 200 |
| 3. Notify stakeholders | Slack/email/IM with rollback reason and timeline | Confirmation received |
| 4. Stop migration task | `tccli msp ModifyMigrationTaskStatus --TaskId "{{user.task_id}}" --Status STOPPED` | Status = STOPPED |
| 5. Post-mortem doc | Document: timestamp, error root cause, data gap, retry plan | Doc filed in audit-results/ |
| 6. Retry planning | Address root cause before next cutover attempt | All root cause items resolved |
