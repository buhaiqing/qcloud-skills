# Idempotency Checklist — TencentDB for MongoDB

Automation and retry-safe behavior for `qcloud-mongodb-ops` operations.

## Response Fields (Idempotency Keys)

| Field | Path | Use |
|-------|------|-----|
| InstanceId | `$.Response.InstanceDetails[0].InstanceId` | Existence check before create/modify |
| DealId | `$.Response.DealId` | Async create/renew tracking |
| FlowId | `$.Response.FlowId` | FlashBack / version upgrade async tracking |
| RequestId | `$.Response.RequestId` | Audit log correlation |

## Operation Idempotency Matrix

| Operation | Idempotent? | Retry Strategy | Notes |
|-----------|-------------|----------------|-------|
| DescribeDBInstances | Yes | Safe to retry | Read-only |
| CreateDBInstance / CreateDBInstanceHour | No | HALT on success with DealId | Check DescribeDBInstances by name before retry |
| ModifyDBInstanceSpec | Partial | Retry only if no DealId/FlowId returned | Poll status=2 before re-submit |
| IsolateDBInstance | Partial | Safe if already status=3 | Check status first |
| OfflineIsolatedDBInstance | No | HALT after first success | Irreversible |
| CreateBackupDBInstance | No | Safe to create duplicate backups | Each call creates new backup |
| RestoreDBInstance | No | HALT after submit | Data overwrite — never blind retry |
| FlashBackDBInstance | No | HALT after FlowId returned | Data overwrite |
| CreateAccountUser | Partial | HALT if account exists | DescribeAccountUsers first |
| ResetDBInstancePassword | No | HALT after success | Each call changes password |
| SetBackupRules | Yes | Safe to retry with same params | Overwrites rules |
| ModifyInstanceParams | Yes | Safe to retry with same key/value | Same final state |

## Pre-Retry Checklist

1. **Existence:** `DescribeDBInstances --InstanceIds '["{{user.instance_id}}"]'` — confirm target state
2. **Async in flight:** `DescribeAsyncRequestInfo --DealId` or poll instance status — do not duplicate create/modify
3. **Lock:** On `FailedOperation.OperationNotAllowedInInstanceLocking`, wait 30s, max 3 retries
4. **Throttle:** On `LimitExceeded.TooManyRequests`, exponential backoff (2s, 4s, 8s), max 3 retries

## Automation Patterns

```bash
# Idempotent describe-or-create guard (by instance name)
NAME="{{user.instance_name}}"
EXISTING=$(tccli mongodb DescribeDBInstances --Limit 100 | jq -r --arg n "$NAME" '.Response.InstanceDetails[] | select(.InstanceName==$n) | .InstanceId')
if [ -n "$EXISTING" ]; then
  echo "Instance already exists: $EXISTING"
else
  tccli mongodb CreateDBInstanceHour --Zone "{{user.zone}}" ...
fi
```

> Full Pre-flight → Execute → Validate → Recover flows: see `SKILL.md` only (TE-6).
