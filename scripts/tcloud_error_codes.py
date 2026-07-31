#!/usr/bin/env python3
"""tcloud_error_codes.py — Tencent Cloud API error code registry.

Phase 1.3 extension. The original 9-code registry is preserved at the
top of ``TCLOUD_ERROR_CODES`` for backward compatibility (existing
callers that index by code only). New product-level codes live in
``PRODUCT_ERROR_CODES`` with the full Phase 1.3 schema:

    {
        "code": str,
        "product": str,            # tccli product name (e.g. "cvm")
        "severity": str,           # minor | major | critical
        "category": str,           # auth | param | state | rate_limit | ...
        "action": str,             # HALT | RETRY | FIX | DELEGATE
        "max_retries": int,
        "backoff_strategy": str,   # "fixed" | "exponential"
        "backoff_seconds": list[int],
        "delegate_to": str | None, # skill name (e.g. "qcloud-vpc-ops")
        "fix": str,                # legacy "fix" hint (preserved)
    }

Public API:

    TCLOUD_ERROR_CODES   original 9-code dict (back-compat)
    PRODUCT_ERROR_CODES  list[dict] with full Phase 1.3 schema
    ALL_ERROR_CODES      merged dict (top-level + product) keyed by code
    parse_error(response) -> dict  (existing contract preserved)
    to_error_rule(record) -> ErrorRule  (bridge for ErrorEscalator)

Usage:
    from tcloud_error_codes import PRODUCT_ERROR_CODES
    from error_escalator import ErrorEscalator, ErrorRule

    esc = ErrorEscalator()
    for rec in PRODUCT_ERROR_CODES:
        esc.add_rule(to_error_rule(rec))
"""

TCLOUD_ERROR_CODES = {
    "AuthFailure": {"severity": "major", "category": "auth", "fix": "Check SecretId/Key and CAM policy"},
    "InvalidParameter": {"severity": "minor", "category": "param", "fix": "Verify all required parameters are present and valid"},
    "InvalidCredential": {"severity": "major", "category": "auth", "fix": "SecretKey may be expired or invalid"},
    "ResourceNotFound": {"severity": "minor", "category": "state", "fix": "Resource may have been deleted; verify existence first"},
    "UnsupportedOperation": {"severity": "major", "category": "api", "fix": "Operation not supported in this region or for this resource type"},
    "RequestLimitExceeded": {"severity": "major", "category": "rate_limit", "fix": "Reduce request frequency; implement exponential backoff"},
    "InternalError": {"severity": "major", "category": "unknown", "fix": "Retry with exponential backoff; if persists, contact support"},
    "ResourceInsufficient": {"severity": "major", "category": "quota", "fix": "Check account quota; request increase if needed"},
    "DryRunOperation": {"severity": "minor", "category": "dry_run", "fix": "Dry run passed; operation is safe to execute"},
}


# ---------------------------------------------------------------------------
# Phase 1.3 — product-level error codes (≥30)
# ---------------------------------------------------------------------------
# Schema: code, product, severity, category, action, max_retries,
#         backoff_strategy, backoff_seconds, delegate_to, fix.

PRODUCT_ERROR_CODES: list[dict] = [
    # ---- CVM ---------------------------------------------------------------
    {
        "code": "InvalidVpc.NotFound", "product": "cvm", "severity": "major",
        "category": "dependency", "action": "DELEGATE", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": "qcloud-vpc-ops",
        "fix": "VPC missing — delegate to qcloud-vpc-ops CreateVpc then retry CVM",
    },
    {
        "code": "InvalidSubnet.NotFound", "product": "cvm", "severity": "major",
        "category": "dependency", "action": "DELEGATE", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": "qcloud-vpc-ops",
        "fix": "Subnet missing — delegate to qcloud-vpc-ops",
    },
    {
        "code": "InvalidSecurityGroup.NotFound", "product": "cvm", "severity": "major",
        "category": "dependency", "action": "DELEGATE", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": "qcloud-vpc-ops",
        "fix": "Security group missing — delegate to qcloud-vpc-ops",
    },
    {
        "code": "ResourceInsufficient.CvmInstanceQuotaIsFull", "product": "cvm",
        "severity": "critical", "category": "quota", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "CVM quota exhausted — request quota increase or delete unused instances",
    },
    {
        "code": "QuotaExceeded.SecurityGroupLimit", "product": "cvm",
        "severity": "major", "category": "quota", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "SG quota exceeded — use existing SG or request increase",
    },
    {
        "code": "InvalidParameter.ImageIdMalformed", "product": "cvm",
        "severity": "minor", "category": "param", "action": "FIX", "max_retries": 1,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Use DescribeImages to find valid img-xxx",
    },
    {
        "code": "InvalidParameterValue.InstanceTypeUnsupported", "product": "cvm",
        "severity": "minor", "category": "param", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Check zone-instance matrix via DescribeZoneInstanceConfigInfos",
    },
    {
        "code": "InvalidInstance.NotSupported", "product": "cvm",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Instance type does not accept the operation",
    },
    {
        "code": "InvalidInstanceState.InstanceIsRunning", "product": "cvm",
        "severity": "minor", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Instance must be STOPPED before destructive op",
    },
    # ---- CBS ---------------------------------------------------------------
    {
        "code": "InvalidDisk.NotSupported", "product": "cbs",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Disk type does not support this operation on this instance",
    },
    {
        "code": "InvalidDisk.DiskAttached", "product": "cbs",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Disk already attached to an instance",
    },
    {
        "code": "InvalidDisk.DiskBusy", "product": "cbs",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Unmount filesystem, wait for I/O to drain, then retry",
    },
    {
        "code": "InvalidDisk.NotAttached", "product": "cbs",
        "severity": "minor", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Disk not attached to the specified instance",
    },
    # ---- CDB ---------------------------------------------------------------
    {
        "code": "FailedOperation.CreateOrderFailed", "product": "cdb",
        "severity": "major", "category": "billing", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Check account payment / balance before retrying",
    },
    {
        "code": "OperationDenied.InstanceStatusError", "product": "cdb",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Check current CDB instance status",
    },
    {
        "code": "InternalError.DBError", "product": "cdb",
        "severity": "major", "category": "internal", "action": "RETRY", "max_retries": 3,
        "backoff_strategy": "fixed", "backoff_seconds": [2, 4, 8], "delegate_to": None,
        "fix": "Database-side error — retry; escalate with RequestId if persists",
    },
    {
        "code": "LimitExceeded.ExceedMaxInstanceCount", "product": "cdb",
        "severity": "major", "category": "quota", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Per-region CDB instance count exceeded; raise quota",
    },
    # ---- Redis -------------------------------------------------------------
    {
        "code": "InvalidParameter.ClusterNotFound", "product": "redis",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Redis cluster does not exist; verify via DescribeInstances",
    },
    {
        "code": "RedisConnectError", "product": "redis",
        "severity": "major", "category": "network", "action": "RETRY", "max_retries": 2,
        "backoff_strategy": "exponential", "backoff_seconds": [], "delegate_to": None,
        "fix": "Transient network error; back off and retry",
    },
    # ---- MongoDB -----------------------------------------------------------
    {
        "code": "OplogError", "product": "mongodb",
        "severity": "major", "category": "internal", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Check oplog window; investigate replica state",
    },
    # ---- TKE ---------------------------------------------------------------
    {
        "code": "ClusterNotFound", "product": "tke",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "TKE cluster missing; verify via DescribeClusters",
    },
    {
        "code": "NodePoolQuotaExceeded", "product": "tke",
        "severity": "major", "category": "quota", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Node pool quota exhausted; request increase",
    },
    # ---- CLB ---------------------------------------------------------------
    {
        "code": "InvalidParameter.LoadBalancerNotFound", "product": "clb",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "CLB not found; verify via DescribeLoadBalancers",
    },
    # ---- CKafka ------------------------------------------------------------
    {
        "code": "InvalidTopic.NotFound", "product": "ckafka",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "CKafka topic missing; create via CreateTopic",
    },
    # ---- COS ---------------------------------------------------------------
    {
        "code": "NoSuchBucket", "product": "cos",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Bucket does not exist; verify via HeadBucket",
    },
    {
        "code": "NoSuchKey", "product": "cos",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Object key does not exist",
    },
    # ---- CDN ---------------------------------------------------------------
    {
        "code": "DomainNotFound", "product": "cdn",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "CDN domain not registered; add domain first",
    },
    # ---- SCF ---------------------------------------------------------------
    {
        "code": "FunctionNotFound", "product": "scf",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "SCF function missing; verify via GetFunction",
    },
    # ---- SSL ---------------------------------------------------------------
    {
        "code": "CertificateNotFound", "product": "ssl",
        "severity": "major", "category": "state", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "SSL certificate ID not found",
    },
    # ---- Cross-cutting (product-agnostic top-level codes) ------------------
    {
        "code": "RequestLimitExceeded", "product": "", "severity": "major",
        "category": "rate_limit", "action": "RETRY", "max_retries": 3,
        "backoff_strategy": "exponential", "backoff_seconds": [], "delegate_to": None,
        "fix": "Reduce request frequency; back off and retry",
    },
    {
        "code": "InternalError", "product": "", "severity": "major",
        "category": "internal", "action": "RETRY", "max_retries": 3,
        "backoff_strategy": "fixed", "backoff_seconds": [2, 4, 8], "delegate_to": None,
        "fix": "Internal error — retry; escalate with RequestId if persists",
    },
    {
        "code": "AuthFailure", "product": "", "severity": "critical",
        "category": "auth", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Verify SecretId/Key and CAM policy",
    },
    {
        "code": "TradeError.PriceError", "product": "", "severity": "major",
        "category": "billing", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Check billing eligibility for target instance type",
    },
    {
        "code": "LimitExceeded.RegionUnavailable", "product": "", "severity": "major",
        "category": "region", "action": "HALT", "max_retries": 0,
        "backoff_strategy": "fixed", "backoff_seconds": [], "delegate_to": None,
        "fix": "Region not available; try another region",
    },
]


# ---------------------------------------------------------------------------
# Aggregated view: ALL_ERROR_CODES[code] -> merged record
# ---------------------------------------------------------------------------

def _build_all_codes() -> dict:
    merged: dict[str, dict] = {}
    for code, info in TCLOUD_ERROR_CODES.items():
        rec = dict(info)
        rec.setdefault("code", code)
        rec.setdefault("product", "")
        rec.setdefault("action", "HALT")
        rec.setdefault("max_retries", 0)
        rec.setdefault("backoff_strategy", "fixed")
        rec.setdefault("backoff_seconds", [])
        rec.setdefault("delegate_to", None)
        merged[code] = rec
    for rec in PRODUCT_ERROR_CODES:
        code = rec["code"]
        existing = merged.get(code, {})
        existing.update(rec)
        merged[code] = existing
    return merged


ALL_ERROR_CODES: dict[str, dict] = _build_all_codes()


# ---------------------------------------------------------------------------
# Public bridge: ErrorEscalator ↔ registry
# ---------------------------------------------------------------------------

def to_error_rule(record: dict):
    """Convert a registry record (top-level or product-level) to an
    ``error_escalator.ErrorRule``. Lazy import keeps the import order
    one-directional (this module loads fast, ErrorEscalator stays decoupled).
    """
    from error_escalator import Action, ErrorRule

    try:
        action = Action(record.get("action", "HALT"))
    except ValueError:
        action = Action.HALT
    return ErrorRule(
        code=record["code"],
        product=record.get("product", ""),
        action=action,
        max_retries=int(record.get("max_retries", 0)),
        backoff_seconds=list(record.get("backoff_seconds", []) or []),
        backoff_strategy=record.get("backoff_strategy", "fixed"),
        delegate_to=record.get("delegate_to"),
        recovery_hint=record.get("fix", ""),
    )


def parse_error(response: dict) -> dict:
    """Parse a Tencent Cloud API response and return structured error info."""
    err = response.get("Response", {}).get("Error", {})
    code = err.get("Code", "")
    msg = err.get("Message", "")
    info = ALL_ERROR_CODES.get(
        code,
        {"severity": "unknown", "category": "unknown", "fix": "Check error message and API documentation"},
    )
    return {"code": code, "message": msg, **info}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", action="store_true", help="Run self-test and print all error codes")
    ap.add_argument("--count", action="store_true", help="Print registry size")
    args = ap.parse_args()

    if args.test:
        for code in sorted(ALL_ERROR_CODES.keys()):
            info = ALL_ERROR_CODES[code]
            print(f"  {code}: action={info.get('action')} "
                  f"product={info.get('product')!r} delegate_to={info.get('delegate_to')}")
        print(f"Total: {len(ALL_ERROR_CODES)} error codes "
              f"({len(PRODUCT_ERROR_CODES)} product-level)")
    elif args.count:
        print(f"{len(ALL_ERROR_CODES)} total, {len(PRODUCT_ERROR_CODES)} product-level")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())