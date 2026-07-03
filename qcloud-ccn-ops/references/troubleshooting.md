# CCN Troubleshooting

## Symptom: Attach stays in `PENDING`

| Cause | Fix |
|---|---|
| Cross-account attachment awaiting accept | Have the peer account run `AcceptAttachCcnInstances` (or accept in the console). |
| Quota exhausted | `tccli vpc DescribeAccountAttributes --Name "CCN_ATTACHMENT_QUOTA"`; raise if needed. |
| VPC or region mismatch | Reconfirm the `VpcId` and `InstanceRegion`; both must reference a real VPC in the named region. |

## Symptom: Auto-learned route does not appear in the CCN route table

| Cause | Fix |
|---|---|
| Attachment not yet `ACTIVE` | Wait for `InstanceState = ACTIVE`; routes propagate after that. |
| VPC's route table does not have a route pointing at the CCN | Add a route in the VPC's route table with `NextType=CCN` and `NextHubId=<ccn-id>` (use `qcloud-vpc-ops`). |
| Static route is shadowing it | `DescribeCcnRoutes` filtered by `route-type=Static`; remove the conflicting static entry. |

## Symptom: Cross-region traffic throttled or dropped

| Cause | Fix |
|---|---|
| Bandwidth limit too low | `tccli vpc DescribeCcnRegionBandwidthLimits`; raise with `SetCcnRegionBandwidthLimits`. |
| CCN instance is `ISOLATED` (overdue) | Settle the account; CCN returns to `AVAILABLE` automatically. |

## Symptom: `DeleteCCN` returns `ResourceInUse.Ccn`

| Cause | Fix |
|---|---|
| Attachments still present | `DescribeCcnAttachedInstances`; `DetachCcnInstances` for each, then retry. |
| Static routes in CCN route table | `DescribeCcnRoutes` filtered by `route-type=Static`; `DeleteCcnRoute` for each, then retry. |
| VPC route-table entries pointing at this CCN | In each attached VPC's route table, remove the route whose `NextHubId` is this CCN (`qcloud-vpc-ops`). |

## Symptom: Cross-account attach fails with `UnauthorizedOperation`

| Cause | Fix |
|---|---|
| The peer account's CAM role does not allow `vpc:AcceptAttachCcnInstances` | Coordinate with the peer account's admin; see `qcloud-cam-ops` for the role definition. |
| The `InstanceAccountId` is wrong (not a Uin) | Confirm the peer account Uin; `DescribeAccountAttributes` may help, or ask the peer. |
