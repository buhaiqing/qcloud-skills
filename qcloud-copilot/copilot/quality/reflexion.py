from __future__ import annotations


def normalize_reflexion_key(
    category: str, skill: str, command: str, error: str
) -> tuple[str, str, str, str]:
    """Normalize a failure pattern into a cross-system dedup key (fixes L5).

    Same shape ``(category, skill, command_normalized, error)`` the analysis
    recommends for unifying copilot scratch with GCL ``failure_pattern``.
    Command is normalized to its verb/operation token (args dropped) and
    lowercased; error is lowercased and whitespace-collapsed so the same
    failure converging from two sinks dedups instead of double-writing.
    """
    norm_cmd = command.strip().lower().split("\n")[0].split(" ")[0]
    norm_err = " ".join(error.strip().lower().split())
    return (category.strip().lower(), skill.strip().lower(), norm_cmd, norm_err)
