# CAM API & SDK Usage

## Operation Mapping

| Operation | API Method | Required Params | Response Key |
|-----------|-----------|-----------------|-------------|
| Create policy | `CreatePolicy` | PolicyName, PolicyDocument | PolicyId |
| Get policy | `GetPolicy` | PolicyName | PolicyVersion, CreateDate |
| List policies | `ListPolicies` | Page, Rp (pagination) | List, TotalNum |
| Update policy | `UpdatePolicy` | PolicyName, PolicyDocument | RequestId |
| Delete policy | `DeletePolicy` | PolicyName | RequestId |
| Create policy version | `CreatePolicyVersion` | PolicyName, PolicyDocument | VersionId |
| Add user | `AddUser` | Name, Remark | Uin |
| Delete user | `DeleteUser` | Name | RequestId |
| Get user | `GetUser` | Name | Uin, Email, PhoneNumber |
| List users | `ListUsers` | Page, Rp (pagination) | UserInfo, TotalNum |
| Create group | `CreateGroup` | GroupName, Remark | GroupId |
| Delete group | `DeleteGroup` | GroupName | RequestId |
| Add user to group | `AddUserToGroup` | GroupName, UserName | RequestId |
| Create role | `CreateRole` | RoleName, PrincipalService | RoleId |
| Delete role | `DeleteRole` | RoleName | RequestId |
| Attach role policy | `AttachRolePolicy` | RoleName, PolicyName | RequestId |
| Assume role | `AssumeRole` | RoleName, RoleSessionName | Credentials (Token, SecretId, SecretKey, ExpiredTime) |
| Create API key | `CreateApiKey` | SecretId | SecretKey, CreatedOn |
| Delete API key | `DeleteApiKey` | AccessKeyId | RequestId |
| List API keys | `ListApiKey` | SecretId | SecretKeys |

## Python SDK Example

```python
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cam.v20190116 import cam_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

client = cam_client.CamClient(cred, "ap-guangzhou")

# Create policy
req = models.CreatePolicyRequest()
req.PolicyName = "MyCustomPolicy"
req.PolicyDocument = '{"version":"2.0","statement":[{"effect":"allow","action":["cvm:Describe*"],"resource":["*"]}]}'
resp = client.CreatePolicy(req)
print(f"Policy created with ID: {resp.PolicyId}")
```
