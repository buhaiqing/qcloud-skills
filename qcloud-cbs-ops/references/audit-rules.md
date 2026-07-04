# CBS Audit Rules

> Audit rules for disk encryption, snapshot access, and backup compliance.

## Audit Checklist

- [ ] Verify disk encryption is enabled for all production disks
- [ ] Confirm snapshots are not publicly accessible
- [ ] Validate CAM policies restrict disk/snapshot operations to authorized principals
- [ ] Ensure snapshot lifecycle policies are configured
- [ ] Review access logs for disk operations (Attach/Detach/Delete)

## Disk Encryption

- Enable encryption at disk creation: `tccli cbs CreateDisks --DiskChargeType POSTPAID_BY_HOUR --DiskType CLOUD_SSD --Encrypt true`
- Encrypted disks use Tencent Cloud KMS for key management
- Snapshots of encrypted disks are automatically encrypted

## Compliance Reference

For compliance requirements, refer to Tencent Cloud Security whitepaper and your organization's data retention policy.

## See also
- [SecOps Checklist](secops-checklist.md)
- [Core Concepts](core-concepts.md)
