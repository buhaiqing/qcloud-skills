# CCN CLI Usage (tccli)

> **cli_applicability: dual-path** — every execution flow in `SKILL.md` shows both `tccli` and Python SDK. This file is a quick reference for the most common CLI patterns.

## Verify CLI Support

```bash
tccli vpc help | grep -i ccn
# Expected: CreateCCN, DescribeCCNs, DeleteCCN, AttachCcnInstances, ...
```

## Common Patterns

### List CCNs

```bash
tccli vpc DescribeCCNs --Region ap-guangzhou
```

### Create CCN

```bash
tccli vpc CreateCCN \
  --Region ap-guangzhou \
  --CcnName "global-mesh" \
  --CcnDescription "Production multi-region backbone" \
  --ClientToken "$(date +%s%N)"
```

### Attach VPC

```bash
tccli vpc AttachCcnInstances \
  --Region ap-guangzhou \
  --CcnId "ccn-xxx" \
  --Instances '[{"InstanceType":"VPC","InstanceId":"vpc-aaa","InstanceRegion":"ap-guangzhou"}]'
```

Cross-account:

```bash
tccli vpc AttachCcnInstances \
  --Region ap-guangzhou \
  --CcnId "ccn-xxx" \
  --Instances '[{"InstanceType":"VPC","InstanceId":"vpc-bbb","InstanceRegion":"ap-shanghai","InstanceAccountId":{"AccountId":123456789}}]'
```

### Set Inter-Region Bandwidth

```bash
tccli vpc SetCcnRegionBandwidthLimits \
  --Region ap-guangzhou \
  --CcnId "ccn-xxx" \
  --CcnBandwidthLimitSet '[{"SrcRegion":"ap-guangzhou","DestRegion":"ap-shanghai","BandwidthLimit":100}]'
```

### Inspect Routes

```bash
tccli vpc DescribeCcnRoutes \
  --Region ap-guangzhou \
  --CcnId "ccn-xxx"
```

## Coverage Gap (CLI vs SDK)

| API | `tccli vpc` |
|---|---|
| `CreateCCN` / `DescribeCCNs` / `DeleteCCN` | ✅ |
| `AttachCcnInstances` / `DetachCcnInstances` / `DescribeCcnAttachedInstances` | ✅ |
| `CreateCcnRoute` / `DeleteCcnRoute` / `DescribeCcnRoutes` | ✅ |
| `SetCcnRegionBandwidthLimits` / `DescribeCcnRegionBandwidthLimits` | ✅ |
| `DescribeCcnRouteTables` | ✅ |

> SDK fallback is required for any future operation not exposed by the CLI; the dual-path pattern in `SKILL.md` already covers this.

## Error-Handling Pattern

CLI responses wrap the real error in `Response.Error`. To detect API errors from CLI:

```bash
out=$(tccli vpc CreateCCN --Region ap-guangzhou --CcnName "test" 2>&1)
if echo "$out" | jq -e '.Response.Error' >/dev/null 2>&1; then
  code=$(echo "$out" | jq -r '.Response.Error.Code')
  msg=$(echo "$out" | jq -r '.Response.Error.Message')
  echo "[ERROR] $code: $msg"
  exit 1
fi
```
