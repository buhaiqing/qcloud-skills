#!/usr/bin/env python3
"""Operation type classifier for tccli commands.

Classifies tccli commands into read/write/delete based on Action name.
Used for op_type_success_rate analysis in trajectory quality evaluation.

Usage:
  python3 scripts/op_type_classifier.py "tccli cvm DescribeInstances"
  # read

  python3 scripts/op_type_classifier.py "tccli cdb DeleteAccounts"
  # delete
"""

from __future__ import annotations

import re

READ_KEYWORDS = frozenset({
    "describe", "query", "list", "search",
    "get", "check", "inspect", "detail",
})
DELETE_KEYWORDS = frozenset({
    "delete", "destroy", "release", "remove",
    "cancel", "drop", "terminate", "purge",
})
WRITE_KEYWORDS = frozenset({
    "create", "modify", "update", "set", "resize",
    "add", "remove",  # AddClusterInstances, Remove... (before delete kw)
    "start", "stop", "restart", "reboot",
    "open", "close",
    "associate", "disassociate", "attach", "detach",
    "put", "upload", "register",
})


def classify_operation(command: str) -> str:
    """Classify a tccli command into read/write/delete.

    Args:
        command: Full tccli command string.
            Examples: 'tccli cvm DescribeInstances --Region ap-guangzhou'

    Returns:
        'read' | 'write' | 'delete'

    The classification is based on the Action name (3rd token) only.
    Priority: delete > write > read.
    Empty or unrecognized commands default to 'read' (safe default).

    Examples:
        classify_operation('tccli cvm DescribeInstances')  → 'read'
        classify_operation('tccli cdb DeleteAccounts')      → 'delete'
        classify_operation('tccli cos PutObject')           → 'write'
        classify_operation('')                             → 'read'
    """
    if not command:
        return "read"

    tokens = command.strip().split()
    # tccli <product> <Action> ...
    # Split CamelCase BEFORE lowercasing: DeleteAccounts → ['Delete','Accounts']
    action_raw = tokens[2] if len(tokens) > 2 else ""
    words = set(w.lower() for w in re.findall(r'[A-Z][a-z]*', action_raw))
    action_lower = action_raw.lower()
    # Priority: read > delete > write
    if words & READ_KEYWORDS or action_lower in READ_KEYWORDS:
        return "read"
    if words & DELETE_KEYWORDS or action_lower in DELETE_KEYWORDS:
        return "delete"
    if words & WRITE_KEYWORDS or action_lower in WRITE_KEYWORDS:
        return "write"
    return "read"


def classify_batch(commands: list[str]) -> list[str]:
    """Classify a list of commands."""
    return [classify_operation(cmd) for cmd in commands]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python op_type_classifier.py '<tccli command>'")
        sys.exit(0)

    result = classify_operation(sys.argv[1])
    print(result)
