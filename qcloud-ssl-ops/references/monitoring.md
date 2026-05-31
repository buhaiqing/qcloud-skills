# Monitoring & Alerts — SSL Certificate Service

## Key Monitoring Metrics

| Metric | Description | Recommended Alert |
|--------|-------------|-------------------|
| Days until expiry | Remaining days before certificate expires | Alert at 90, 30, 14, 7, 3 days |
| Certificate status | Current certificate status (valid/expired/revoked) | Alert on status change |
| Deployment status | Certificate deployed to cloud resources | Alert on deployment failure |
| Number of certificates | Total certificates per account | Alert at 80% of limit |

## Expiry Monitoring

### Check Expiring Certificates

```bash
# Check certificates expiring within 30 days
tccli ssl DescribeCertificates --Limit 100 | \
  jq '.Response.Certificates[] | select(.CertEndTime != null) | select(.CertEndTime | strptime("%Y-%m-%d %H:%M:%S") | mktime < now + 2592000) | {CertificateId, Alias, Domain, CertEndTime}'
```

### Set Up Cloud Monitor Alerts

```bash
# Create alarm policy for certificate expiry (30 days)
tccli monitor CreateAlarmPolicy \
  --PolicyName "SSL Certificate Expiry Alert (30d)" \
  --Condition '{"MetricName":"certificate_expiry","Period":86400,"Statistics":"last","Threshold":30,"Operator":"le"}'
```

## Recommended Alert Thresholds

| Alert Level | Days Before Expiry | Action |
|-------------|-------------------|--------|
| Info | 90 days | Review certificate inventory |
| Warning | 30 days | Plan renewal or replacement |
| Critical | 14 days | Initiate renewal process |
| Emergency | 7 days | Expedite renewal |
| Expired | 0 days | Replace immediately, check for outages |

## Dashboard

Create a custom Cloud Monitor dashboard with:
- Certificates expiring within 30 days
- Certificate count by type
- Deployment status
- Recent certificate operations

## AIOps: Anomaly Detection Patterns

| Pattern | Symptom | Likely Cause | Action |
|---------|---------|-------------|--------|
| Bulk expiry | Multiple certs expire within same week | All applied at same time or same domain group | Schedule batch renewal; stagger future applications |
| Deployment failure cascade | Deploy fails on multiple resources | Same cert deployed everywhere; one failure blocks all | Check cert status first; deploy to one target at a time |
| Certificate not found after upload | Upload returns OK but describe shows nothing | Async processing delay | Retry describe after 10s; if still missing, re-upload |
| Chain broken after renewal | Renewed cert missing intermediate CA | Renewal CA changed certificate chain | Download full chain; verify with openssl verify |
| Quota approaching limit | < 3 free certs remaining | Heavy use of free tier | Migrate stable domains to paid certs |

## Cost & Performance Metrics

| Metric | Consideration |
|--------|--------------|
| Free certificate limit | 20/account; plan for paid certs beyond that |
| Renewal cost | Renewal may cost less than new purchase |
| Deployment cost | Free for all cloud resources |
| Validation time | DV: minutes-hours; OV/EV: 1-5 business days |
| Unused certificate cost | Non-deployed certs still consume quota; delete unused |
| Chain verification cost | Free to check with openssl CLI |
