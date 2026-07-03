# CAM Troubleshooting

## Error Code Diagnostics

| Error Code | Description | Recovery |
|------------|-------------|----------|
| `AuthFailure.Unauthorized` | Caller lacks CAM permissions | 1. Check caller identity<br>2. List attached policies<br>3. Verify required actions Attach `QcloudCamFullAccess` or custom policy with needed actions |
| `FailedOperation.PolicyNameAlreadyExists` | Policy name already taken | 1. `GetPolicy --PolicyName <name>`<br>2. Review existing policy Use `CreatePolicyVersion` to add new version |
| `InvalidParameter.PolicyDocument` | Policy JSON is invalid | 1. Validate JSON syntax<br>2. Check required fields (version, statement, effect, action, resource) Fix JSON, ensure all required fields present |
| `LimitExceeded.PolicyVersionLimit` | Max policy versions (5) reached | 1. `GetPolicyVersionList`<br>2. Identify unused versions Delete old versions via `DeletePolicyVersion` |
| `AuthFailure.InvalidSecretId` | Invalid credentials | 1. Verify `TENCENTCLOUD_SECRET_ID`<br>2. Check if key disabled Reconfigure credentials with valid SecretId |
| `ResourceNotFound.User` | CAM user not found | 1. `ListUsers` to find correct name<br>2. Check for typos Use correct user name |
| `ResourceNotFound.Role` | CAM role not found | 1. `ListRole` to find correct name<br>2. Check trust relationships Use correct role name |
| `FailedOperation.UserAlreadyInGroup` | User already in group | 1. `GetGroup --GroupName <name>`<br>2. Check members list Skip operation, user already has group permissions |
| `AuthFailure.MFAFailure` | MFA required but not provided | 1. Check if MFA enabled for caller<br>2. Verify MFA token Complete MFA verification before operation |
| `LimitExceeded.PolicyNumberExceed` | Too many policies per user/group/role | 1. `ListAttachedUserPolicies`<br>2. Count policies Detach unused policies (max 10 per entity) |
| `FailedOperation.PolicyHasUser` | Policy has attached users | 1. `ListAttachedPolicyUsers`<br>2. Review attachments Detach from users first, then delete |
| `OperationDenied.AccountIsFrozen` | Account is frozen | 1. Check account status<br>2. Contact Tencent Cloud support Unfreeze account before operations |

## Common Diagnostic Patterns

### Permission Denied Debugging
```bash
# Check what permissions caller has
tccli cam ListAttachedUserPolicies --TargetUin $(tccli cam GetUser --Name $CALLER | jq -r '.Uin')

# Test if specific action is allowed
tccli cam GetPolicy --PolicyName <policy_name>
```

### Policy Conflict Resolution
1. List all policies attached to the user (direct + via groups + via roles)
2. Check for explicit deny statements (deny always wins)
3. Verify resource scope matches the target resource
4. Check condition expressions for time/IP restrictions
