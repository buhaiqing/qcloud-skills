#!/usr/bin/env python3
"""tcloud_error_codes.py — Tencent Cloud API error code registry."""

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


def parse_error(response: dict) -> dict:
    """Parse a Tencent Cloud API response and return structured error info."""
    err = response.get("Response", {}).get("Error", {})
    code = err.get("Code", "")
    msg = err.get("Message", "")
    info = TCLOUD_ERROR_CODES.get(
        code,
        {"severity": "unknown", "category": "unknown", "fix": "Check error message and API documentation"},
    )
    return {"code": code, "message": msg, **info}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", action="store_true", help="Run self-test and print all error codes")
    args = ap.parse_args()

    if args.test:
        for code, info in TCLOUD_ERROR_CODES.items():
            print(f"  {code}: {info}")
        print(f"Total: {len(TCLOUD_ERROR_CODES)} error codes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
