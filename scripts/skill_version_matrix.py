from __future__ import annotations

SKILL_COMPAT: dict[str, dict[str, str | None]] = {
    "qcloud-cvm-ops": {
        "min_agent_version": "1.2.0",
        "max_agent_version": None,
        "tccli_min": "3.0.0",
        "notes": "Requires CVM API 2017-03-12+",
    },
    "qcloud-cdb-ops": {
        "min_agent_version": "1.2.0",
        "max_agent_version": None,
        "tccli_min": "3.0.0",
        "notes": "Requires MySQL API 2017-03-20+",
    },
    "qcloud-cos-ops": {
        "min_agent_version": "1.3.0",
        "max_agent_version": None,
        "tccli_min": "3.0.0",
        "notes": "Requires COS XML API",
    },
    "qcloud-finops-ops": {
        "min_agent_version": "1.5.0",
        "max_agent_version": None,
        "tccli_min": "3.0.400",
        "notes": "Requires billing API + TENCENTCLOUD_FINOPS_CONFIG",
    },
}


def parse_version(v: str) -> tuple[int, int, int]:
    parts = v.strip().split(".")
    nums: list[int] = []
    for p in parts:
        p = p.strip()
        if not p:
            nums.append(0)
            continue
        # strip leading v
        if p.lower().startswith("v"):
            p = p[1:]
        nums.append(int(p))
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _version_in_range(
    version: tuple[int, int, int],
    min_v: tuple[int, int, int],
    max_v: tuple[int, int, int] | None,
) -> bool:
    if version < min_v:
        return False
    return not (max_v is not None and version > max_v)


def is_compatible(
    skill: str,
    agent_version: str,
    *,
    tccli_version: str | None = None,
) -> bool:
    entry = SKILL_COMPAT.get(skill)
    if entry is None:
        return False
    min_v = parse_version(str(entry["min_agent_version"]))  # type: ignore[arg-type]
    max_raw = entry["max_agent_version"]
    max_v = parse_version(str(max_raw)) if max_raw is not None else None
    agent_v = parse_version(agent_version)
    if not _version_in_range(agent_v, min_v, max_v):
        return False
    if tccli_version is not None:
        tccli_min = parse_version(str(entry["tccli_min"]))  # type: ignore[arg-type]
        if parse_version(tccli_version) < tccli_min:
            return False
    return True


def compatible_skills(agent_version: str) -> list[str]:
    return [s for s in SKILL_COMPAT if is_compatible(s, agent_version)]


def render_matrix() -> str:
    lines = [
        "| skill | agent range | tccli min | notes |",
        "| --- | --- | --- | --- |",
    ]
    for skill, entry in SKILL_COMPAT.items():
        min_v = entry["min_agent_version"]
        max_v = entry["max_agent_version"]
        if max_v is None:
            agent_range = f">={min_v}"
        else:
            agent_range = f">={min_v}, <={max_v}"
        lines.append(f"| {skill} | {agent_range} | {entry['tccli_min']} | {entry['notes']} |")
    return "\n".join(lines) + "\n"
