# CLI Usage — CAM

## Command Reference

| Operation | tccli Command | Notes |
|-----------|--------------|-------|
| Create policy | `tccli cam CreatePolicy --PolicyName <name> --PolicyDocument '<json>'` | JSON must be valid |
| Get policy | `tccli cam GetPolicy --PolicyName <name>` | Returns policy details + versions |
| List policies | `tccli cam ListPolicies --Page 1 --Rp 20` | Paginated, max 200 per page |
| Update policy | `tccli cam UpdatePolicy --PolicyName <name> --PolicyDocument '<json>'` | Creates new version |
| Delete policy | `tccli cam DeletePolicy --PolicyName <name>` | Fails if attached to users |
| Create policy version | `tccli cam CreatePolicyVersion --PolicyName <name> --PolicyDocument '<json>'` | Max 5 versions |
| List policy versions | `tccli cam GetPolicyVersionList --PolicyName <name>` | Shows all versions |
| Add user | `tccli cam AddUser --Name <name> --Remark '<remark>'` | Creates new CAM user |
| Delete user | `tccli cam DeleteUser --Name <name>` | Delete API keys first |
| Get user | `tccli cam GetUser --Name <name>` | Returns UIN, email, phone |
| List users | `tccli cam ListUsers --Page 1 --Rp 20` | Paginated user list |
| Create group | `tccli cam CreateGroup --GroupName <name> --Remark '<remark>'` | Creates new group |
| Delete group | `tccli cam DeleteGroup --GroupName <name>` | Must be empty first |
| List groups | `tccli cam ListGroup --Page 1 --Rp 20` | Paginated group list |
| Add user to group | `tccli cam AddUserToGroup --GroupName <name> --UserName <user>` | Links user to group |
| Create role | `tccli cam CreateRole --RoleName <name> --PrincipalService <service>` | Trust relationship set |
| Delete role | `tccli cam DeleteRole --RoleName <name>` | Detach policies first |
| List roles | `tccli cam ListRole` | All roles in account |
| Attach role policy | `tccli cam AttachRolePolicy --RoleName <name> --PolicyName <policy>` | Links policy to role |
| Update assume-role trust policy | `tccli cam UpdateAssumeRolePolicy --RoleName <name> --PolicyDocument '<json>'` | ⚠️ Trust widening risk; see rubric §4 rule 4 |
| List API keys | `tccli cam ListApiKey --SecretId <sid>` | Returns all keys for SecretId |
| Delete API key | `tccli cam DeleteApiKey --AccessKeyId <key>` | Irreversible |
| Create SAML provider | `tccli cam CreateSAMLProvider --Name <name> --SAMLMetadata '<xml>'` | SSO setup |
| Create OIDC provider | `tccli cam CreateOIDCProvider --Name <name> --OIDCConfig '<json>'` | OIDC SSO setup |
| Get OIDC provider | `tccli cam GetOIDCProvider --OIDCProviderId <id>` | OIDC config check |
| List OIDC providers | `tccli cam ListOIDCProviders` | OIDC provider audit |
| Delete OIDC provider | `tccli cam DeleteOIDCProvider --OIDCProviderId <id>` | OIDC cleanup |

## Coverage Gap Table

| Operation | CLI Support | SDK Needed? |
|-----------|-------------|-------------|
| Policy CRUD | ✓ | No |
| User CRUD | ✓ | No |
| Group CRUD | ✓ | No |
| Role CRUD | ✓ | No |
| API key management | ✓ | No |
| SAML provider | ✓ | No |
| OIDC provider | ✓ | No |
| Complex policy validation | Partial | Yes (for JSON validation) |
| Batch operations | Manual loop | Yes (for efficiency) |
