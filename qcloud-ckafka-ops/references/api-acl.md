# CKafka ACL API

> CKafka ACL (Access Control List) operations.

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeAcls | Query ACL list | `tccli ckafka DescribeAcls` |
| CreateAcl | Create ACL rule | `tccli ckafka CreateAcl` |
| DeleteAcl | Delete ACL rule | `tccli ckafka DeleteAcl` |

## ACL Operations

### Create ACL Rule
```bash
tccli ckafka CreateAcl --InstanceId ckafka-xxx --ResourceType TOPIC --ResourceName my-topic --Operation 2 --Permission 1 --Host "*"
```

## ACL Permission Values

| Value | Permission |
|-------|------------|
| 1 | Allow |
| 2 | Deny |

## ACL Operation Values

| Value | Operation |
|-------|-----------|
| 1 | ALL |
| 2 | READ |
| 3 | WRITE |
| 4 | CREATE |
| 5 | DELETE |

## See also
- [Core Concepts](core-concepts.md)
- [API Instance](api-instance.md)
