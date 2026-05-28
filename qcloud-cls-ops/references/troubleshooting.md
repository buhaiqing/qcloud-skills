# CLS Troubleshooting Guide

## Error Codes

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| `InvalidParameter` | Invalid parameter | No | Check parameter format |
| `InvalidParameter.TopicId` | Topic not found | No | Verify topic ID |
| `InvalidParameter.LogsetId` | Logset not found | No | Verify logset ID |
| `InvalidParameter.Content` | Log content invalid | No | Check size (<512KB) |
| `InternalError` | Server error | Yes (3x) | Retry with backoff |
| `LimitExceeded` | Quota exceeded | No | Request quota increase |
| `LimitExceeded.Logset` | Logset quota reached | No | Delete unused logsets |
| `LimitExceeded.Topic` | Topic quota reached | No | Delete unused topics |
| `LimitExceeded.Partition` | Partition limit reached | No | Reduce partition count |
| `ResourceNotFound` | Resource not found | No | Verify resource ID |
| `ResourceInUse` | Resource in use | No | Remove dependencies first |
| `UnauthorizedOperation` | Permission denied | No | Check CAM permissions |
| `FailedOperation` | Operation failed | Yes (1x) | Check specific error |
| `FailedOperation.Timeout` | Operation timeout | Yes (3x) | Retry with timeout |
| `FailedOperation.IndexNotReady` | Index not ready | Yes (3x) | Wait and retry |
| `OperationDenied` | Operation denied | No | Check resource status |
| `OperationDenied.AccountDestroy` | Account closed | No | Contact support |
| `OperationDenied.AccountIsolate` | Account isolated | No | Contact support |

## Diagnostic Procedures

### 1. Log Collection Failures

#### Symptom: Logs not appearing in CLS

**Step 1: Verify LogListener Status**
```bash
# Check if LogListener is running
sudo systemctl status loglistener

# Check LogListener logs
sudo tail -f /var/log/loglistener/loglistener.log
```

**Expected Result:** Service status should be "active (running)"

**Step 2: Verify Machine Group Health**
```bash
# Check agent status in console
tccli cls DescribeMachineGroups --Region ap-guangzhou

# Verify IP is in machine group
MACHINES=$(tccli cls DescribeMachineGroups \
  --Region ap-guangzhou \
  --Filters '[{"Key":"groupName","Value":"my-group"}]' | \
  jq -r '.Response.MachineGroups[0].MachineGroupType.Values[]')
echo "$MACHINES"
```

**Step 3: Verify Config-Topic Association**
```bash
# Check if config is applied to machine group
tccli cls DescribeConfigs \
  --Region ap-guangzhou \
  --Filters '[{"Key":"machineGroupId","Value":"group-xxx"}]'
```

**Step 4: Verify File Path Pattern**
```bash
# Check if log files exist and match pattern
ls -la /var/log/nginx/*.log

# Check file permissions
test -r /var/log/nginx/access.log && echo "Readable" || echo "Not readable"
```

**Step 5: Check Log Format**
```bash
# View sample log lines
tail -5 /var/log/nginx/access.log

# Verify JSON format (if using json_log)
tail -1 /var/log/app.log | jq . >/dev/null 2>&1 && echo "Valid JSON" || echo "Invalid JSON"
```

#### Common Collection Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Logs delayed | Network latency | Check network, increase buffer |
| Partial logs | File rotation | Use `*` wildcard in path |
| Duplicate logs | Multiple configs | Ensure unique output topics |
| Missing fields | ExtractRule error | Verify parse regex |
| Permission denied | File access | Fix file permissions (chmod 644) |

### 2. Search Returns No Results

#### Symptom: Query returns empty results

**Step 1: Verify Time Range**
```bash
# Check if logs exist in time range
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --From $(date -v-1d +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 1
```

**Expected Result:** Should return log entries if data exists

**Step 2: Verify Index Configuration**
```bash
# Check index exists
tccli cls DescribeIndex \
  --Region ap-guangzhou \
  --TopicId "topic-xxx"
```

**Expected Result:** Index status should be "normal"

**Step 3: Verify Query Syntax**
```bash
# Test with simple wildcard query
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --From $(date -v-1H +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 10

# Test field query (if key-value index exists)
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --From $(date -v-1H +%s)000 \
  --To $(date +%s)000 \
  --Query 'level:*' \
  --Limit 10
```

**Step 4: Check Index Status**
```bash
# Index may not be ready
tccli cls DescribeIndex \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" | \
  jq -r '.Response.Status'
```

**Expected Result:** Status should be "normal", not "creating"

#### Common Search Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No results | No index configured | Create index first |
| No results | Index not ready | Wait 1-5 minutes |
| No results | Time range too narrow | Expand time range |
| Partial results | Field not indexed | Add field to key-value index |
| Slow search | Full scan | Add more specific filters |
| Syntax error | Invalid query | Use correct query syntax |

### 3. Index Configuration Errors

#### Symptom: Index creation fails or search doesn't work

**Step 1: Validate Index JSON**
```bash
# Test JSON validity
cat index-rule.json | jq . >/dev/null 2>&1 && echo "Valid JSON" || echo "Invalid JSON"
```

**Step 2: Check Field Type Compatibility**
```bash
# For numeric fields, ensure values are numbers
# For text fields, ensure tokenizer is specified
```

**Step 3: Verify Index Update**
```bash
# Modify index (update triggers reindex)
tccli cls ModifyIndex \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --Rule file://index-rule.json

# Wait for reindex
echo "Waiting for index to be ready..."
sleep 60
```

#### Index Best Practices Checklist

- [ ] Field names match log structure
- [ ] Numeric fields use `"Type": "long"` or `"Type": "double"`
- [ ] Text fields have tokenizer configured
- [ ] JSON fields properly nested (use dot notation)
- [ ] Index size within quota (500 fields max)

### 4. Machine Group Issues

#### Symptom: Agent shows offline

**Step 1: Check Agent Status**
```bash
# Check if agent is running
ps aux | grep loglistener

# Check network connectivity
curl -I https://cls.tencentcloudapi.com
```

**Step 2: Verify API Credentials**
```bash
# Check secret ID/Key configured
cat /etc/loglistener.conf | grep -i secret

# Test credential validity
tccli cls DescribeLogsets --Region ap-guangzhou
```

**Step 3: Check Resource Quotas**
```bash
# Check machine group count
GROUP_COUNT=$(tccli cls DescribeMachineGroups \
  --Region ap-guangzhou | \
  jq -r '.Response.MachineGroups | length')
echo "Machine groups: $GROUP_COUNT / 100"
```

### 5. Log Upload Failures

#### Symptom: API/SDK upload returns error

**Step 1: Check Log Size**
```bash
# Verify log size < 512KB
LOG_SIZE=$(echo "$LOG_CONTENT" | wc -c)
if [ "$LOG_SIZE" -gt 524288 ]; then
  echo "Log too large: $LOG_SIZE bytes (max 512KB)"
fi
```

**Step 2: Check Topic Exists**
```bash
tccli cls DescribeTopics \
  --Region ap-guangzhou \
  --TopicIds '["topic-xxx"]' | \
  jq -r '.Response.Topics | length'
```

**Expected Result:** Should return 1 (topic exists)

**Step 3: Check Authentication**
```bash
# Verify credentials have CLS write permission
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --From $(date -v-1m +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 1
```

### 6. High Latency Issues

#### Symptom: Log search or collection is slow

**Step 1: Check Partition Count**
```bash
# Verify topic partition count
tccli cls DescribeTopics \
  --Region ap-guangzhou \
  --TopicIds '["topic-xxx"]' | \
  jq -r '.Response.Topics[0].PartitionCount'
```

**Recommendation:** Increase partitions if write throughput is high

**Step 2: Check Query Complexity**
```bash
# Simple query should be fast
time tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-xxx" \
  --From $(date -v-1H +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 100
```

**Step 3: Check Index Efficiency**
```bash
# Queries on indexed fields are faster
# Avoid wildcards at start of term
# Use specific time ranges
```

## Multi-Round Diagnostic Steps

### Round 1: Basic Connectivity

```bash
echo "=== Round 1: Basic Connectivity ==="

# 1. Check LogListener service
sudo systemctl is-active loglistener || echo "LogListener not running"

# 2. Check API access
tccli cls DescribeLogsets --Region ap-guangzhou > /dev/null && echo "API OK" || echo "API Error"

# 3. Check network
ping -c 3 cls.tencentcloudapi.com > /dev/null && echo "Network OK" || echo "Network Issue"
```

### Round 2: Configuration Validation

```bash
echo "=== Round 2: Configuration Validation ==="

TOPIC_ID="your-topic-id"
GROUP_ID="your-group-id"

# 1. Verify topic exists
tccli cls DescribeTopics \
  --Region ap-guangzhou \
  --TopicIds "[\"$TOPIC_ID\"]" | \
  jq -r ".Response.Topics[0].TopicName // \"Topic not found\""

# 2. Verify machine group
tccli cls DescribeMachineGroups \
  --Region ap-guangzhou \
  --Filters "[{\"Key\":\"groupId\",\"Value\":\"$GROUP_ID\"}]" | \
  jq -r ".Response.MachineGroups | length"

# 3. Check index status
tccli cls DescribeIndex \
  --Region ap-guangzhou \
  --TopicId "$TOPIC_ID" | \
  jq -r '.Response.Status // "No index"'
```

### Round 3: Data Flow Verification

```bash
echo "=== Round 3: Data Flow Verification ==="

# 1. Check recent logs
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "$TOPIC_ID" \
  --From $(date -v-5M +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 1 | \
  jq -r '.Response.Results | length'

# 2. Check log file modification
stat -f "%Sm" /var/log/nginx/access.log

# 3. Check LogListener logs for errors
sudo grep -i "error\|fail\|exception" /var/log/loglistener/loglistener.log | tail -5
```

### Round 4: Performance Analysis

```bash
echo "=== Round 4: Performance Analysis ==="

# 1. Measure search latency
time tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "$TOPIC_ID" \
  --From $(date -v-1H +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 1000 > /dev/null

# 2. Check partition utilization
tccli cls DescribeTopics \
  --Region ap-guangzhou \
  --TopicIds "[\"$TOPIC_ID\"]" | \
  jq -r '.Response.Topics[0] | {PartitionCount, AutoSplit, MaxSplitPartitions}'
```

## Escalation Criteria

### Support Ticket Required When:

| Condition | Evidence Required |
|-----------|-------------------|
| Server-side error persists | Error code + RequestId + Timestamp |
| Data loss suspected | Before/after log counts + Time range |
| Quota increase needed | Current usage + Business justification |
| Service degradation | Latency metrics + Time range |
| Billing discrepancy | Usage report + Expected vs actual |

### Information to Collect

```bash
# Generate diagnostic report
REPORT_FILE="cls-diagnostics-$(date +%Y%m%d-%H%M%S).txt"

echo "=== CLS Diagnostic Report ===" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "1. Logsets:" >> "$REPORT_FILE"
tccli cls DescribeLogsets --Region ap-guangzhou 2>/dev/null | jq '.Response.Logsets | length' >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "2. Topics:" >> "$REPORT_FILE"
tccli cls DescribeTopics --Region ap-guangzhou 2>/dev/null | jq '.Response.Topics | length' >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "3. Machine Groups:" >> "$REPORT_FILE"
tccli cls DescribeMachineGroups --Region ap-guangzhou 2>/dev/null | jq '.Response.MachineGroups | length' >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "4. LogListener Status:" >> "$REPORT_FILE"
sudo systemctl is-active loglistener 2>/dev/null >> "$REPORT_FILE" || echo "Not installed/running" >> "$REPORT_FILE"

echo "Report saved to: $REPORT_FILE"
```

## Quick Reference Commands

### Check Log Collection Health
```bash
# All-in-one health check
TOPIC_ID="your-topic-id"
echo "Topic: $TOPIC_ID"
echo "Index: $(tccli cls DescribeIndex --Region ap-guangzhou --TopicId "$TOPIC_ID" 2>/dev/null | jq -r '.Response.Status // "None"')"
echo "Recent logs: $(tccli cls SearchLog --Region ap-guangzhou --TopicId "$TOPIC_ID" --From $(date -v-1H +%s)000 --To $(date +%s)000 --Query '*' --Limit 1 2>/dev/null | jq -r '.Response.Results | length')"
```

### Verify Complete Pipeline
```bash
# Verify logset → topic → index chain
LOGSET_ID="your-logset-id"
TOPIC_ID="your-topic-id"

echo "Logset: $(tccli cls DescribeLogsets --Region ap-guangzhou 2>/dev/null | jq -r ".Response.Logsets[] | select(.LogsetId==\"$LOGSET_ID\") | .LogsetName // \"Not found\"")"
echo "Topic: $(tccli cls DescribeTopics --Region ap-guangzhou 2>/dev/null | jq -r ".Response.Topics[] | select(.TopicId==\"$TOPIC_ID\") | .TopicName // \"Not found\"")"
echo "Index: $(tccli cls DescribeIndex --Region ap-guangzhou --TopicId "$TOPIC_ID" 2>/dev/null | jq -r '.Response.Rule.FullText.Tokenizer // "Not configured"')"
```

## References

- [CLS Common Errors](https://cloud.tencent.com/document/product/614/12446)
- [LogListener Troubleshooting](https://cloud.tencent.com/document/product/614/17416)
- [CLS FAQs](https://cloud.tencent.com/document/product/614/12449)
- [CLS Service Level Agreement](https://cloud.tencent.com/document/product/614/30248)
