# Copyright (c) 2026. All rights reserved.
"""Tag lookup helpers for proactive-inspection scripts (customer tag filtering)."""

from __future__ import annotations

_TAG_FIELDS = ("tags", "Tags", "tagList", "TagList")


def _iter_tags(resource: dict):
    for field in _TAG_FIELDS:
        tags = resource.get(field)
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if isinstance(tag, dict):
                yield tag


def get_tag(resource: dict, tag_key: str) -> str | None:
    """Return the tag value for `tag_key` from a raw or normalized resource.

    Handles both tccli CamelCase (`Tags` with `Key`/`Value`) and normalized
    lowerCamelCase (`tags` with `key`/`value`) shapes.
    """
    for tag in _iter_tags(resource):
        key = tag.get("key") or tag.get("Key")
        if key == tag_key:
            value = tag.get("value") or tag.get("Value")
            return str(value) if value is not None else None
    return None


def tag_dict(resource: dict) -> dict[str, str]:
    """Return all tags as a {key: value} dict from a raw or normalized resource."""
    result: dict[str, str] = {}
    for tag in _iter_tags(resource):
        key = tag.get("key") or tag.get("Key")
        if key is None:
            continue
        value = tag.get("value") or tag.get("Value")
        result[str(key)] = str(value) if value is not None else ""
    return result
