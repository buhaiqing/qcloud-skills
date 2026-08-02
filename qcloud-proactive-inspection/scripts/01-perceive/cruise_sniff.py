#!/usr/bin/env python3
"""Topology sniff for qcloud-proactive-inspection (tccli-backed, customer tag filter)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CUSTOMER_TAG_KEY = "客户"
ALL_REGIONS = ["ap-guangzhou", "ap-shanghai", "ap-beijing", "ap-nanjing", "ap-chengdu"]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.env_loader import ensure_runtime_env
from lib.normalize import normalize_resource
from lib.tags import get_tag

ensure_runtime_env()


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "qcloud-copilot").is_dir() and (parent / "AGENTS.md").is_file():
            return parent
    return Path.cwd()


def _run_tccli(product: str, operation: str, region: str, extra: list[str] | None = None) -> dict:
    """Run a tccli query. Failures return ``{"_error": ...}`` instead of ``{}``.

    An empty dict is indistinguishable from "no resources", so auth failures and
    throttling used to look like healthy empty inventories.
    """
    cmd = ["tccli", product, operation, "--region", region, "--output", "json"]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
    if proc.returncode != 0:
        logger.warning(
            "tccli %s %s failed (rc=%s): %s", product, operation, proc.returncode,
            (proc.stderr or "").strip()[:200],
        )
        return {"_error": f"rc={proc.returncode}", "_stderr": (proc.stderr or "")[:200]}
    if not proc.stdout.strip():
        return {}
    try:
        resp = json.loads(proc.stdout).get("Response", {})
    except json.JSONDecodeError:
        logger.warning("tccli %s %s returned non-JSON output", product, operation)
        return {"_error": "InvalidJSON"}
    if "Error" in resp:
        code = resp["Error"].get("Code", "Unknown")
        logger.warning("tccli %s %s API error: %s", product, operation, code)
        return {"_error": code, "_stderr": (proc.stderr or "")[:200]}
    return resp


def _list_items(resp: dict, *keys: str) -> list[dict]:
    # A failed query must not be reported as an empty inventory: an operator
    # acting on "0 resources found" would draw the opposite conclusion.
    if "_error" in resp:
        raise RuntimeError(f"tccli failed: {resp['_error']}")
    for key in keys:
        items = resp.get(key)
        if isinstance(items, list):
            return items
    return []


def _tagged(items: list[dict], tag_key: str, customer: str) -> list[dict]:
    matched: list[dict] = []
    for item in items:
        normalized = normalize_resource(item)
        if get_tag(item, tag_key) == customer or get_tag(normalized, tag_key) == customer:
            matched.append(normalized)
    return matched


def discover(customer: str, region: str, tag_key: str) -> dict[str, list]:
    raw: dict[str, list] = {
        "vms": [],
        "lbs": [],
        "vpcs": [],
        "redis": [],
        "rds": [],
        "eips": [],
        "mongodb": [],
        "es": [],
        "nats": [],
        "security_groups": [],
    }

    raw["vms"] = _tagged(_list_items(_run_tccli("cvm", "DescribeInstances", region), "InstanceSet"), tag_key, customer)
    raw["lbs"] = _tagged(
        _list_items(_run_tccli("clb", "DescribeLoadBalancers", region), "LoadBalancerSet"), tag_key, customer
    )
    raw["vpcs"] = _tagged(_list_items(_run_tccli("vpc", "DescribeVpcs", region), "VpcSet"), tag_key, customer)
    raw["redis"] = _tagged(_list_items(_run_tccli("redis", "DescribeInstances", region), "InstanceSet"), tag_key, customer)
    raw["rds"] = _tagged(_list_items(_run_tccli("cdb", "DescribeDBInstances", region), "Items"), tag_key, customer)
    raw["eips"] = _tagged(_list_items(_run_tccli("vpc", "DescribeAddresses", region), "AddressSet"), tag_key, customer)
    raw["mongodb"] = _tagged(
        _list_items(_run_tccli("mongodb", "DescribeDBInstances", region), "InstanceDetails"), tag_key, customer
    )
    raw["es"] = _tagged(_list_items(_run_tccli("es", "DescribeInstances", region), "InstanceList"), tag_key, customer)
    raw["nats"] = _tagged(
        _list_items(_run_tccli("vpc", "DescribeNatGateways", region), "NatGatewaySet"), tag_key, customer
    )

    all_sgs = [normalize_resource(sg) for sg in _list_items(_run_tccli("vpc", "DescribeSecurityGroups", region), "SecurityGroupSet")]
    vm_sg_ids: set[str] = set()
    for vm in raw["vms"]:
        for sg_id in vm.get("securityGroupIds") or vm.get("SecurityGroupIds") or []:
            vm_sg_ids.add(str(sg_id))
    raw["security_groups"] = [sg for sg in all_sgs if sg.get("groupId") in vm_sg_ids or get_tag(sg, tag_key) == customer]

    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1: resource sniff by customer tag")
    parser.add_argument("--customer", required=True)
    parser.add_argument("--region", default=os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    parser.add_argument("--tag-key", default=os.environ.get("COPILOT_CUSTOMER_TAG_KEY", DEFAULT_CUSTOMER_TAG_KEY))
    parser.add_argument("--output-dir", default=str(_repo_root() / ".runtime" / "proactive-inspection"))
    args = parser.parse_args()

    regions = [args.region] if args.region else ALL_REGIONS
    merged: dict[str, list] = {
        "vms": [],
        "lbs": [],
        "vpcs": [],
        "redis": [],
        "rds": [],
        "eips": [],
        "mongodb": [],
        "es": [],
        "nats": [],
        "security_groups": [],
    }
    for region in regions:
        chunk = discover(args.customer, region, args.tag_key)
        for key, items in chunk.items():
            merged[key].extend(items)

    payload = {
        "customer": args.customer,
        "regions": regions,
        "tag_key": args.tag_key,
        "raw": merged,
        "counts": {k: len(v) for k, v in merged.items()},
        "generated_at": datetime.now().isoformat(),
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"sniff-{args.customer}-{ts}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[已保存] 拓扑嗅探结果: {out_path}")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    # Without a handler the tccli failure warnings are swallowed by the
    # "no handlers" fallback, which is how the silent-empty-inventory bug hid.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    sys.exit(main())
