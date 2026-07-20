# CloudBase Troubleshooting Guide

## Error Code Reference

| Code | Meaning | Agent Action |
|------|---------|--------------|
| `InvalidParameter` | Parameter validation failed | Fix parameter value |
| `InvalidParameterValue` | Parameter value out of range | Adjust per API spec |
| `MissingParameter` | Required parameter missing | Add missing parameter |
| `ResourceNotFound` | Environment or resource not found | Verify EnvId; list resources |
| `ResourceInsufficient` | Quota exceeded | HALT; delete unused envs |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `InvalidSecretId` | Credential ID invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit exceeded | Backoff; retry (3x) |
| `InternalError` | Server error | Retry (3x); escalate with RequestId |
| `OperationDenied` | Operation not allowed in current state | Wait; check env status |

> Full error taxonomy with **UX Feedback** strings per error code — see SKILL.md § Failure Recovery.
## Diagnostic Procedures

### Procedure 1: Environment Creation Fails

**Symptom**: `CreateEnv` returns error or hangs

**Steps**:
1. Verify CloudBase service is enabled: `tccli tcb CheckTcbService --Region {{region}}`
2. Check env quota: call `DescribeEnvInfo` and count existing envs
3. Verify region support: try `ap-guangzhou` if current region fails
4. Check credentials: `tccli tcb DescribeEnvInfo` with minimal call

**Decision Tree**:
- ServiceAvailable != true → User must enable CloudBase in console
- Quota exceeded → Delete unused environments
- Credentials invalid → Fix env vars

---

### Procedure 2: Environment Status Unexpected

**Symptom**: Environment status is not `0` (正常)

**Steps**:
1. Poll `DescribeEnvInfo` with specific EnvId
2. Check Status meaning:
   - `-1` = 未初始化 → Wait or recreate
   - `-2` = 删除中 → Environment is being deleted
   - Other negative values → Check for async operation in progress
3. Wait for stable state (300s timeout)

**Decision Tree**:
- Status != 0 after 300s → HALT; escalate with RequestId
- Status = -2 → Environment is being deleted; cannot recover

---

### Procedure 3: Database ACL Not Applied

**Symptom**: Database permissions not working as expected

**Steps**:
1. Describe current ACL: `tccli tcb DescribeDatabaseACL --EnvId {{env_id}}`
2. Verify collection name matches exactly (case-sensitive)
3. Check ACL mode matches expected behavior:
   - `admin`: all users can read and write
   - `readOnly`: all users read, only admin writes
   - `writeOnly`: only admin reads, all users write
   - `none`: only admin can read and write

**Decision Tree**:
- Wrong ACL mode → Recreate with correct mode
- Collection not found → Check collection name in database

---

### Procedure 4: API Key Issues

**Symptom**: Cannot authenticate with API key

**Steps**:
1. List keys: `tccli tcb DescribeApiKeyLists` (SecretKey is masked)
2. Verify key ID is correct (ApiKeyId not the SecretKey)
3. If SecretKey lost → Delete old key and create new one

**Decision Tree**:
- Key exists but fails → Delete and recreate; note SecretKey shown only once
- No keys → Create new API key

---

### Procedure 5: Auth Domain Not Working

**Symptom**: Browser blocked from accessing CloudBase resources

**Steps**:
1. List auth domains: `tccli tcb DescribeAuthDomains --EnvId {{env_id}}`
2. Verify domain is present and spelled correctly
3. Check domain type (`web` vs `qiniu`)
4. Verify domain has HTTPS (required for some operations)

**Decision Tree**:
- Domain missing → CreateAuthDomain with correct domain
- Wrong type → Delete and recreate with correct type

---

## Multi-Round Diagnosis

### Round 1: Initial Assessment

```yaml
round_1:
  checks:
    - service_enabled
    - credentials_valid
    - env_exists
    - env_status_valid
  actions:
    - CheckTcbService
    - DescribeEnvInfo
  decision:
    - if all pass: proceed to Round 2
    - if any fail: fix issue
```

### Round 2: Resource-Specific Diagnosis

```yaml
round_2:
  checks:
    - quota_available
    - region_supported
    - parameter_valid
  actions:
    - DescribeEnvInfo (count envs)
    - DescribeBillingInfo (check quota)
  decision:
    - if issue found: attempt fix
    - if no issue: escalate
```

### Round 3: Root Cause Determination

```yaml
round_3:
  checks:
    - request_traces
    - recent_operations_log
    - dependency_status
  actions:
    - collect RequestId
    - document timeline
  output:
    - root_cause_hypothesis
    - resolution_recommendation
```

## Common Scenarios

### Scenario 1: Cannot Create Environment

**Problem**: CreateEnv returns `ResourceInsufficient` or hangs

**Most Likely Causes**:
1. Environment quota already used (max 5 personal / 10 enterprise)
2. CloudBase service not enabled for account
3. Region not supported

**Resolution**:
```bash
# Step 1: Check service status
tccli tcb CheckTcbService --Region {{region}}

# Step 2: Count existing envs
tccli tcb DescribeEnvInfo --Region {{region}} \
  | jq -r '.Response.EnvList | length'

# Step 3: Delete unused envs if quota hit
```

---

### Scenario 2: Database Access Denied

**Problem**: Users cannot read/write to database collections

**Diagnosis Steps**:
1. Check collection ACL: `DescribeDatabaseACL`
2. Verify collection exists in database
3. Check if using correct EnvId

**Resolution**:
- ACL too restrictive → CreateDatabaseACL with broader permissions
- Wrong collection name → Use exact collection name from database

---

### Scenario 3: SecretKey Lost

**Problem**: API key SecretKey was not saved at creation time

**Resolution**:
1. List existing keys: `DescribeApiKeyLists` (get ApiKeyId)
2. Delete lost key: `DeleteApiKey`
3. Create new key: `CreateApiKey` — **save SecretKey immediately**

**Warning**: There is no way to recover a lost SecretKey. If the key is actively used, coordinate rotation to avoid downtime.

## Escalation Criteria

Escalate when:
- `InternalError` persists after 3 retries
- Environment stuck in non-normal state for > 300s
- Platform-level issue suspected (multiple users affected)
- Async operation times out without clear result

**Escalation Protocol**:
1. Collect `RequestId` from last API call
2. Document: EnvId, Action attempted, Error, Timestamp
3. Contact Tencent Cloud support with: EnvId, RequestId, Timestamp, Error messages

## References

- [CloudBase API Error Codes](https://cloud.tencent.com/document/api/876/36418)
- [CloudBase Console](https://console.cloud.tencent.com/tcb)
