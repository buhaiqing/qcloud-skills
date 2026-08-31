#!/usr/bin/env python3
"""
check_idempotency.py — Pre-commit hook: detect non-idempotent tccli/sdk/requests calls.

Exits 0 = all clear, 1 = issues found (commit blocked).

Detection rules:
  A. tccli subprocess: subprocess.run(["tccli", ...]) / subprocess.run("tccli", ...)
     → requires --ClientToken somewhere in the command list
  B. tencentcloud-sdk: from tencentcloud.X import Y / client.Call(...)
     → requires ClientToken field in request object
  C. requests: requests.post(...) / requests.get(...) / requests.request(...)
     → requires headers={"Idempotency-Key": ...} or "Idempotency-Key" in headers dict
  D. boto3 (aws-sdk): client.method(...) calls
     → requires ClientToken kwarg
  E. azure-sdk: arm resource calls via azure-mgmt-*
     → requires x-ms-client-request-id header or Operation-Location polling
  F. google-cloud-python: storage/bigquery/pubsub mutation calls
     → requires request_id or destination_id parameter

Usage (pre-commit hook, no args):
    python3 scripts/check_idempotency.py

Usage (self-test):
    python3 scripts/check_idempotency.py --self-test
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ─── Rule A: tccli subprocess ─────────────────────────────────────────────────

_TCCLI_RE = re.compile(r"subprocess\.run\s*\(\s*(\[|\")", re.IGNORECASE)
_CLIENTTOKEN_RE = re.compile(r"--ClientToken|--client-token", re.IGNORECASE)


def check_tccli_subprocess(text: str) -> list[str]:
    """
    Return list of lines where tccli subprocess lacks --ClientToken.
    Skips:
      - Comment / docstring lines
      - String literal lines (inside triple-quoted strings)
      - Read-only operations: --version, Describe*, Query*, List*, Get*
    """
    issues = []
    in_triple = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # Track triple-quoted string boundaries
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            continue
        if in_triple:
            continue
        # Skip blank, comment-only lines
        if not stripped or stripped.startswith('#'):
            continue
        if not _TCCLI_RE.search(line):
            continue
        # Skip read-only operations (check after tccli marker for string form)
        lower = line.lower()
        if '--version' in lower or 'describe' in lower or 'query' in lower or 'list' in lower or 'get' in lower or 'check' in lower:
            continue
        # tccli call detected — check for ClientToken flag
        if not _CLIENTTOKEN_RE.search(line):
            issues.append(f"  Line {lineno}: tccli subprocess without --ClientToken\n    {line.strip()}")
    return issues


# ─── Rule B: tencentcloud-sdk ─────────────────────────────────────────────────

_SDK_IMPORT_RE = re.compile(r"from tencentcloud", re.IGNORECASE)
# Match: client.MethodName(...) or variable = client.MethodName(...)
_SDK_CALL_RE = re.compile(
    r"(?:\w+\s*=\s*)?\w+\.\w+\s*\(",
    re.IGNORECASE
)
_CLIENTTOKEN_FIELD_RE = re.compile(r"ClientToken\s*=", re.IGNORECASE)


def check_tencentcloud_sdk(text: str) -> list[str]:
    """
    Return list of issues for tencentcloud-sdk calls without ClientToken.

    Uses a regex sliding-window approach:
      - When we find a tencentcloud import AND a nearby client.Method(...) call,
        check if ClientToken= appears within ±5 lines.
    """
    issues: list[str] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, 1):
        if not _SDK_CALL_RE.search(line):
            continue
        # Look backward for SDK import
        start = max(0, lineno - 6)
        window_before = "\n".join(lines[start:lineno - 1])
        has_sdk_import = _SDK_IMPORT_RE.search(window_before)
        if not has_sdk_import:
            continue
        # Look for ClientToken in surrounding lines
        window_after = min(len(lines), lineno + 4)
        nearby = "\n".join(lines[start:window_after])
        if not _CLIENTTOKEN_FIELD_RE.search(nearby):
            issues.append(
                f"  Line {lineno}: tencentcloud-sdk call without ClientToken in request\n    {line.strip()}"
            )
    return issues


# ─── Rule C: requests with no Idempotency-Key header ──────────────────────────

_REQUESTS_CALL_RE = re.compile(
    r"requests\.(post|put|patch|delete|request)\s*\(",
    re.IGNORECASE,
)
_IDEMPOTENCY_KEY_RE = re.compile(r"Idempotency-Key", re.IGNORECASE)


def check_requests_headers(text: str) -> list[str]:
    """Return list of line numbers where requests calls lack Idempotency-Key header."""
    issues = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not _REQUESTS_CALL_RE.search(line):
            continue
        if not _IDEMPOTENCY_KEY_RE.search(line):
            issues.append(f"  Line {lineno}: requests call without Idempotency-Key header\n    {line.strip()}")
    return issues


# ─── Rule D: boto3 (AWS SDK) ─────────────────────────────────────────────────

# boto3 methods that are NOT idempotent without ClientToken
# https://docs.aws.amazon.com/AWSEC2/latest/APIReference/query-api-qr.html
IDEMPOTENT_BOTO3_METHODS = {
    "run_instances", "create_volume", "copy_image", "copy_snapshot",
    "create_security_group", "authorize_security_group_ingress",
    "revoke_security_group_ingress", "delete_security_group",
    "create_bucket", "put_object", "delete_object", "delete_bucket",
    "create_stack", "delete_stack", "update_stack", "create_change_set",
    "delete_change_set", "start_job", "create_pipeline", "send_message",
    "receive_message", "delete_queue", "create_queue",
    "publish", "subscribe", "create_topic", "delete_topic",
    "create_table", "update_table", "delete_table",
    "create_function", "update_function_code", "delete_function",
    "create_role", "delete_role", "attach_role_policy", "detach_role_policy",
    "put_item", "delete_item", "update_item",
    "send_templated_email", "send_raw_email", "send_email",
}

_BOTO3_CALL_RE = re.compile(r"\.\s*(client|resource)\s*\(", re.IGNORECASE)


def check_boto3(text: str) -> list[str]:
    """
    Return issues for boto3 client calls that lack ClientToken kwarg.
    Uses AST to safely parse and detect missing kwargs.
    """
    issues = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []  # Let other rules handle malformed files

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match: something.client(...) or something.resource(...) returning a variable,
        # then variable.method(...) — or chained: something.client(...).method(...)
        if not isinstance(node.func, ast.Attribute):
            continue
        obj = node.func.value
        # Case: boto3.client('ec2').run_instances(...) — chained
        if isinstance(obj, ast.Attribute) and obj.attr in ("client", "resource"):
            pass  # chained, ok
        # Case: ec2 = boto3.client('ec2'); ec2.run_instances(...) — variable assignment
        elif isinstance(obj, ast.Name):
            pass  # variable holding client, ok
        else:
            continue
        # Check if method is one that needs ClientToken
        if node.func.attr not in IDEMPOTENT_BOTO3_METHODS:
            continue
        # Check kwargs for ClientToken
        kwarg_names = [k.arg for k in node.keywords if k.arg]
        if "ClientToken" in kwarg_names:
            continue
        lineno = getattr(node, "lineno", 0)
        issues.append(
            f"  Line {lineno}: boto3.{node.func.attr} without ClientToken kwarg\n"
            f"    {node.func.attr}(...) — add ClientToken kwarg for idempotency"
        )
    return issues


# ─── Rule E: azure-sdk ───────────────────────────────────────────────────────

# azure-mgmt methods that are NOT idempotent without proper request-id header
# begin_* methods are async long-running operations; non-begin mutation methods also need it
IDEMPOTENT_AZURE_METHODS = {
    # Compute
    "begin_create_or_update", "begin_delete", "begin_update",
    "begin_create", "begin_delete_method",
    # Storage
    "create", "update", "delete", "set",
    # Network
    "put", "patch",
}

_AZURE_MGMT_CALL_RE = re.compile(r"azure\.mgmt\.[a-z]+\.[a-z]+\.[a-zA-Z0-9_]+", re.IGNORECASE)
_AZURE_REQ_ID_HEADER_RE = re.compile(r"x-ms-client-request-id", re.IGNORECASE)


def check_azure_sdk(text: str) -> list[str]:
    """
    Return issues for azure-sdk calls that lack idempotency-related patterns.

    Detects:
      - azure-mgmt client.begin_*() calls without x-ms-client-request-id header
      - raw requests.post/get calls mentioning azure endpoints without idempotency header
    """
    issues = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Detect azure.mgmt.X.Y.Z.client.begin_*() or similar
        method_name = None
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            method_name = node.func.id

        if not method_name:
            continue

        # Check begin_* mutation methods
        is_begin_mutation = method_name.startswith("begin_")
        is_mutation = method_name in IDEMPOTENT_AZURE_METHODS or any(
            method_name.startswith(p) for p in ("create", "update", "delete", "put", "patch")
        )
        if not (is_begin_mutation or is_mutation):
            continue

        # Check if kwarg contains request_id or client_request_id
        kwarg_names = [k.arg for k in node.keywords if k.arg]
        has_request_id = any(
            "request_id" in name.lower() or "client_request_id" in name.lower()
            for name in kwarg_names
        )
        if has_request_id:
            continue

        # Check headers kwarg for x-ms-client-request-id
        has_header_id = False
        for k in node.keywords:
            if (k.arg in ("headers", "header_dict", "kwargs")
                    and isinstance(k.value, ast.Dict)):
                for key_node in k.value.keys:
                    if isinstance(key_node, ast.Constant) and "request-id" in str(key_node.value).lower():
                        has_header_id = True
                        break
        if has_header_id:
            continue

        lineno = getattr(node, "lineno", 0)
        issues.append(
            f"  Line {lineno}: azure-sdk {method_name} without request-id\n"
            f"    Add x-ms-client-request-id header or polling Operation-Location"
        )

    # Also flag raw requests calls to *.azure.com without Idempotency-Key
    # (complement to Rule C, but azure-specific)
    for lineno, line in enumerate(text.splitlines(), 1):
        if not _REQUESTS_CALL_RE.search(line):
            continue
        if ".azure.com" not in line.lower() and ".azurewebsites.net" not in line.lower():
            continue
        if _IDEMPOTENCY_KEY_RE.search(line) or _AZURE_REQ_ID_HEADER_RE.search(line):
            continue
        issues.append(
            f"  Line {lineno}: requests call to Azure endpoint without x-ms-client-request-id\n"
            f"    {line.strip()[:80]}"
        )

    return issues


# ─── Rule F: google-cloud-python ──────────────────────────────────────────────

# google-cloud methods that are NOT idempotent without request_id
IDEMPOTENT_GCP_METHODS = {
    # Storage
    "upload_from_string", "upload_from_filename", "upload_as_string",
    "delete", "copy_blob", "rename", "compose",
    # BigQuery
    "insert", "insert_rows", "insert_rows_json", "delete_table",
    "update_table", "patch_table", "copy_table",
    # Pub/Sub
    "publish", "publish_message", "delete_topic", "delete_subscription",
    "create_snapshot", "seek",
    # Datastore
    "put", "allocate_ids",
    # KMS
    "encrypt", "decrypt", "destroy_crypto_key", "disable_crypto_key",
    # Secret Manager
    "add_version", "destroy_secret_version",
    # AI Platform / Vertex AI
    "create_endpoint", "deploy_model", "undeploy_model",
}

_GCP_SDK_RE = re.compile(
    r"from google\.cloud|import google\.cloud"
    r"|google\.cloud\.",
    re.IGNORECASE,
)


def check_google_cloud(text: str) -> list[str]:
    """
    Return issues for google-cloud-python calls that lack request_id parameter.
    """
    issues = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    has_gcp_import = bool(_GCP_SDK_RE.search(text))
    if not has_gcp_import:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue

        method_name = node.func.attr
        # Check mutation methods
        is_mutation = (
            method_name in IDEMPOTENT_GCP_METHODS or
            any(method_name.startswith(p) for p in
                ("insert", "update", "delete", "create", "upload", "publish", "put"))
        )
        if not is_mutation:
            continue

        kwarg_names = [k.arg for k in node.keywords if k.arg]
        # GCP uses request_id, destination_id, source, etc.
        has_request_id = any(
            name in kwarg_names or name.lower() in ("request_id", "destination_id", ("source"
                             "client_request_id"), "requestid", "idempotency_token")
            for name in kwarg_names
        )
        if has_request_id:
            continue

        lineno = getattr(node, "lineno", 0)
        issues.append(
            f"  Line {lineno}: google-cloud.{method_name} without request_id\n"
            f"    {method_name}(...) — add request_id kwarg for idempotency"
        )
    return issues


# ─── Per-file check ───────────────────────────────────────────────────────────

def check_file(path: Path) -> list[str]:
    """Return all idempotency issues in a Python file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"  Cannot read {path}: {e}"]

    issues: list[str] = []
    issues.extend(check_tccli_subprocess(text))
    issues.extend(check_tencentcloud_sdk(text))
    issues.extend(check_requests_headers(text))
    issues.extend(check_boto3(text))
    issues.extend(check_azure_sdk(text))
    issues.extend(check_google_cloud(text))
    return issues


# ─── Self-test ───────────────────────────────────────────────────────────────

SELF_TEST_CASES = [
    # (description, file_content, expect_issues)
    (
        "tccli subprocess WITH ClientToken",
        'subprocess.run(["tccli", "cvm", "RunInstances", "--ClientToken", token, "--Region", "ap-guangzhou"])',
        False,
    ),
    (
        "tccli subprocess WITHOUT ClientToken",
        'subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])',
        True,
    ),
    (
        "requests.post WITH Idempotency-Key",
        'requests.post(url, headers={"Idempotency-Key": str(uuid.uuid4())})',
        False,
    ),
    (
        "requests.post WITHOUT Idempotency-Key",
        "requests.post(url, json=payload)",
        True,
    ),
    (
        "tencentcloud-sdk call without ClientToken (import form)",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "resp = client.RunInstances(req)\n"
        ),
        True,
    ),
    (
        "tencentcloud-sdk call with ClientToken in request",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "req.ClientToken = str(uuid.uuid4())\n"
            "resp = client.RunInstances(req)\n"
        ),
        False,
    ),
    (
        "tccli string form without ClientToken",
        'subprocess.run("tccli cvm RunInstances --Region ap-guangzhou", shell=True)',
        True,
    ),
    (
        "clean file (no API calls)",
        "x = 1\ny = 2\n",
        False,
    ),
    # ── Rule D: boto3 ───────────────────────────────────────────────────────────
    (
        "boto3 run_instances WITHOUT ClientToken (should flag)",
        (
            "import boto3\n"
            "ec2 = boto3.client('ec2')\n"
            "ec2.run_instances(ImageId='ami-xxx', MinCount=1, MaxCount=1)\n"
        ),
        True,
    ),
    (
        "boto3 run_instances WITH ClientToken (should NOT flag)",
        (
            "import boto3\n"
            "ec2 = boto3.client('ec2')\n"
            "ec2.run_instances(ImageId='ami-xxx', MinCount=1, MaxCount=1, ClientToken='tok-123')\n"
        ),
        False,
    ),
    (
        "boto3 create_bucket WITHOUT ClientToken (should flag)",
        (
            "import boto3\n"
            "s3 = boto3.client('s3')\n"
            "s3.create_bucket(Bucket='my-bucket', CreateBucketConfiguration={'LocationConstraint': 'ap-guangzhou'})\n"
        ),
        True,
    ),
    # ── Rule E: azure-sdk ──────────────────────────────────────────────────────
    (
        "azure-mgmt begin_create_or_update without request-id (should flag)",
        (
            "from azure.mgmt.compute.v2022_03_01 import ComputeManagementClient\n"
            "client = ComputeManagementClient(credential, subscription_id)\n"
            "async_poller = client.virtual_machines.begin_create_or_update(\n"
            "    resource_group_name, vm_name, vm_params)\n"
        ),
        True,
    ),
    (
        "azure-mgmt begin_create_or_update with request_id kwarg (should NOT flag)",
        (
            "from azure.mgmt.compute.v2022_03_01 import ComputeManagementClient\n"
            "client = ComputeManagementClient(credential, subscription_id)\n"
            "async_poller = client.virtual_machines.begin_create_or_update(\n"
            "    resource_group_name, vm_name, vm_params, request_id='req-123')\n"
        ),
        False,
    ),
    # ── Rule F: google-cloud-python ───────────────────────────────────────────
    (
        "google-cloud storage upload without request_id (should flag)",
        (
            "from google.cloud import storage\n"
            "client = storage.Client()\n"
            "bucket = client.bucket('my-bucket')\n"
            "blob = bucket.blob('my-file.txt')\n"
            "blob.upload_from_filename('/tmp/my-file.txt')\n"
        ),
        True,
    ),
]


def self_test() -> bool:
    """Run self-test, return True if all pass."""
    all_pass = True
    for desc, content, expect_issues in SELF_TEST_CASES:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
            fh.write(content)
            fh.flush()
            path = Path(fh.name)

        issues = check_file(path)
        path.unlink()

        has_issues = bool(issues)
        ok = has_issues == expect_issues
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {desc}")
        if not ok:
            if expect_issues:
                print("         Expected issues, got none")
            else:
                for iss in issues:
                    print(f"         Unexpected: {iss}")

    return all_pass


# ─── Main ─────────────────────────────────────────────────────────────────────

def get_staged_python_files() -> list[Path]:
    """Return list of staged Python files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        print("git not found — skipping staged file check", file=sys.stderr)
        return []

    files = []
    for path in result.stdout.splitlines():
        p = Path(path)
        if p.suffix == ".py":
            files.append(p)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Check idempotency in Python files")
    parser.add_argument("--self-test", action="store_true", help="Run internal self-test")
    parser.add_argument("--files", nargs="*", type=Path, help="Specific files to check (default: git staged .py)")
    args = parser.parse_args()

    if args.self_test:
        print("check_idempotency.py self-test")
        ok = self_test()
        sys.exit(0 if ok else 1)

    files = args.files if args.files else get_staged_python_files()

    if not files:
        # No staged Python files — nothing to check, allow commit
        sys.exit(0)

    total_issues = 0
    for path in files:
        issues = check_file(path)
        if issues:
            print(f"\n{path}:")
            for iss in issues:
                print(iss)
            total_issues += len(issues)

    if total_issues:
        print(f"\n[{total_issues} idempotency issue(s)] — commit blocked")
        print("Fix: add --ClientToken to tccli calls, ClientToken field to SDK requests,")
        print("     or Idempotency-Key header to requests calls.")
        sys.exit(1)
    else:
        print("check_idempotency.py: all clear")
        sys.exit(0)


if __name__ == "__main__":
    main()
