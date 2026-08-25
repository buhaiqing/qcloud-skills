#!/usr/bin/env python3
"""kb_sync_openapi.py — Auto-generate Layer-1/2 knowledge bases from tccli metadata.

Replaces hand-maintained partial KBs in cli_param_validator.py (~13 skills) and
schema_validator.py with generated, full-coverage JSON under ``assets/shared/``:

  tcloud_cli_flags.json         {skill: {action: [flag, ...]}}
  tcloud_response_schemas.json  {skill: {action: {required, data_field, request_id}}}
  tcloud_kb_coverage.json       {skill: {actions_total, actions_covered, source}}

Input is the tccli ``services/<product>/<version>/api.json`` layout shipped with
every tccli install (or any directory with the same shape). Products without a
mapped qcloud-*-ops skill are skipped with a warning (L10 — skip gracefully).

CLI usage::

    python3 scripts/kb_sync_openapi.py                          # auto-detect installed tccli
    python3 scripts/kb_sync_openapi.py --metadata <services-dir>
    python3 scripts/kb_sync_openapi.py --check                  # CI drift gate (exit 1 on drift)

Validators consume the generated files automatically (TCLOUD_KB_DIR override).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "assets" / "shared"

FLAGS_FILE = "tcloud_cli_flags.json"
SCHEMA_FILE = "tcloud_response_schemas.json"
COVERAGE_FILE = "tcloud_kb_coverage.json"

# product (tccli services/<product>) -> owning skill
PRODUCT_SKILL: dict[str, str] = {
    "cvm": "qcloud-cvm-ops",
    "cdb": "qcloud-cdb-ops",
    "clb": "qcloud-clb-ops",
    "cos": "qcloud-cos-ops",
    "es": "qcloud-es-ops",
    "redis": "qcloud-redis-ops",
    "monitor": "qcloud-monitor-ops",
    "tke": "qcloud-tke-ops",
    "vpc": "qcloud-vpc-ops",
    "cam": "qcloud-cam-ops",
    "cdn": "qcloud-cdn-ops",
    "cbs": "qcloud-cbs-ops",
    "cls": "qcloud-cls-ops",
    "ckafka": "qcloud-ckafka-ops",
    "tencentcloudbase": "qcloud-cloudbase-ops",
    "scf": "qcloud-scf-ops",
    "mongodb": "qcloud-mongodb-ops",
    "postgres": "qcloud-postgres-ops",
    "ssl": "qcloud-ssl-ops",
    "as": "qcloud-agsx-ops",
    "billing": "qcloud-finops-ops",
    "ccn": "qcloud-ccn-ops",
    "vpcn": "qcloud-vpn-ops",
    "dc": "qcloud-dc-ops",
    "tdmq": "qcloud-tdmq-ops",
    "apigateway": "qcloud-apigw-ops",
}

# Online-only actions are worth generating; offline/deprecated ones still valid
# structurally but noisy — keep everything, validators pass silently anyway.


def detect_tccli_services_dir() -> Path | None:
    """Locate the installed tccli ``services/`` directory, or None."""
    spec = importlib.util.find_spec("tccli")
    if spec is None or not spec.submodule_search_locations:
        return None
    candidate = Path(next(iter(spec.submodule_search_locations))) / "services"
    return candidate if candidate.is_dir() else None


def _flag_variants(member_name: str) -> set[str]:
    """tccli accepts several casings; validators match lowercased tokens.

    Emit lowercase-no-separator and kebab forms so either convention matches:
      StoppedMode -> {stoppedmode, stopped-mode}
    """
    kebab = "".join(f"-{c.lower()}" if c.isupper() else c for c in member_name).lstrip("-")
    flat = member_name.lower()
    return {flat, kebab}


def _latest_version_dir(product_dir: Path) -> Path | None:
    versions = sorted((d for d in product_dir.iterdir() if d.is_dir()), key=lambda p: p.name)
    return versions[-1] if versions else None


def parse_api_json(api_json: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]], dict[str, int]]:
    """Parse one api.json into (flags_kb, schema_kb, counts).

    Self-contained pure function so tests can feed fixtures directly.
    """
    actions: dict[str, Any] = api_json.get("actions") or {}
    objects: dict[str, Any] = api_json.get("objects") or {}

    flags_kb: dict[str, list[str]] = {}
    schema_kb: dict[str, dict[str, Any]] = {}
    covered = 0

    for action, spec in sorted(actions.items()):
        input_type = spec.get("input")
        output_type = spec.get("output")

        flags: set[str] = set()
        if input_type and input_type in objects:
            for member in objects[input_type].get("members") or []:
                name = member.get("name")
                if name:
                    flags |= _flag_variants(name)
        if flags:
            flags_kb[action] = sorted(flags)
            covered += 1

        schema: dict[str, Any] = {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        }
        if output_type and output_type in objects:
            for member in objects[output_type].get("members") or []:
                if member.get("type") == "list" and member.get("name"):
                    schema["data_field"] = f"Response.{member['name']}"
                    break
        schema_kb[action] = schema

    return flags_kb, schema_kb, {"actions_total": len(actions), "actions_covered": covered}


def sync(metadata_dir: Path | None) -> dict[str, Any]:
    """Walk metadata dir and build all three KB payloads."""
    if metadata_dir is None:
        raise SystemExit(
            "No tccli metadata found. Pass --metadata <services-dir> or pip install tccli."
        )

    flags_out: dict[str, dict[str, list[str]]] = {}
    schema_out: dict[str, dict[str, dict[str, Any]]] = {}
    coverage: dict[str, dict[str, Any]] = {}
    skipped: list[str] = []

    for product_dir in sorted(p for p in metadata_dir.iterdir() if p.is_dir()):
        product = product_dir.name.lower()
        skill = PRODUCT_SKILL.get(product)
        if not skill:
            skipped.append(product)
            continue
        version_dir = _latest_version_dir(product_dir)
        api_file = version_dir / "api.json" if version_dir else None
        if api_file is None or not api_file.exists():
            print(f"WARN: no api.json for product {product}, skipping", file=sys.stderr)
            continue
        try:
            api_json = json.loads(api_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARN: cannot parse {api_file}: {exc}", file=sys.stderr)
            continue

        flags_kb, schema_kb, counts = parse_api_json(api_json)
        if not flags_kb:
            continue
        flags_out[skill] = flags_kb
        schema_out[skill] = schema_kb
        coverage[skill] = {
            **counts,
            "source": str(api_file),
            "version": version_dir.name if version_dir else "",
        }

    if skipped:
        print(f"INFO: {len(skipped)} unmapped products skipped: {', '.join(sorted(skipped))}", file=sys.stderr)

    return {"flags": flags_out, "schemas": schema_out, "coverage": coverage}


def write_kbs(payload: dict[str, Any], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, data in (
        (FLAGS_FILE, payload["flags"]),
        (SCHEMA_FILE, payload["schemas"]),
        (COVERAGE_FILE, payload["coverage"]),
    ):
        path = out_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written


def kbs_match(payload: dict[str, Any], out_dir: Path) -> bool:
    for name, key in ((FLAGS_FILE, "flags"), (SCHEMA_FILE, "schemas"), (COVERAGE_FILE, "coverage")):
        path = out_dir / name
        if not path.exists():
            return False
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        if current != payload[key]:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--metadata", type=str, default=None,
                        help="Path to tccli services/ dir (default: auto-detect installed tccli)")
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--check", action="store_true",
                        help="CI mode: exit 1 if generated files are missing or stale")
    args = parser.parse_args()

    metadata_dir: Path | None
    if args.metadata:
        metadata_dir = Path(args.metadata)
        if not metadata_dir.is_dir():
            print(f"ERROR: metadata dir not found: {metadata_dir}", file=sys.stderr)
            return 2
    else:
        metadata_dir = detect_tccli_services_dir()

    payload = sync(metadata_dir)
    out_dir = Path(args.out_dir)

    if args.check:
        if kbs_match(payload, out_dir):
            total = sum(v["actions_covered"] for v in payload["coverage"].values())
            print(f"KB up-to-date: {len(payload['coverage'])} skills, "
                  f"{total} covered actions ({out_dir})")
            return 0
        print("DRIFT: generated KBs differ from tccli metadata; re-run kb_sync_openapi.py", file=sys.stderr)
        return 1

    written = write_kbs(payload, out_dir)
    total = sum(v["actions_covered"] for v in payload["coverage"].values())
    for path in written:
        print(f"wrote {path}")
    print(f"coverage: {len(payload['coverage'])} skills, {total} covered actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
