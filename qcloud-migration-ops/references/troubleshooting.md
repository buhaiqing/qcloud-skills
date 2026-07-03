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
