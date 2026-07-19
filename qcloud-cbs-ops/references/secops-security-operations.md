# CBS SecOps Checklist

> Security operations checklist for CBS.

## Pre-Deployment Security Checklist

- [ ] Enable disk encryption for sensitive data (`--Encrypt true`)
- [ ] Use CAM to restrict disk operations to specific IAM principals
- [ ] Place disks in VPC-subnet for network-level isolation
- [ ] Review and configure security group rules for CVM access

## Ongoing Operations Checklist

- [ ] Regular snapshot backups (weekly or per RPO)
- [ ] Monitor disk I/O for anomalies (potential data exfiltration)
- [ ] Review CAM policy changes monthly
- [ ] Rotate encryption keys periodically
- [ ] Audit disk attach/detach events in CloudAudit logs

## Incident Response

If disk compromise is suspected:
1. Detach the disk immediately: `tccli cbs DetachDisks --DiskId disk-xxx`
2. Create a forensic snapshot for analysis
3. Review CloudAudit logs for unauthorized operations
4. Notify security team before re-attaching

## See also
- [Audit Rules](audit-rules.md)
- [Core Concepts](core-concepts.md)
