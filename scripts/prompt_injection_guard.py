from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TrustLevel(Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    SUSPICIOUS = "suspicious"


_TRUSTED_SOURCES = frozenset({"system", "skill", "internal", "config"})
_UNTRUSTED_SOURCES = frozenset({"user", "web", "external"})
_SUSPICIOUS_SOURCES = frozenset({"suspicious"})


def classify_trust(source: str) -> TrustLevel:
    normalized = source.strip().lower()
    if normalized in _TRUSTED_SOURCES:
        return TrustLevel.TRUSTED
    if normalized in _UNTRUSTED_SOURCES:
        return TrustLevel.UNTRUSTED
    if normalized in _SUSPICIOUS_SOURCES:
        return TrustLevel.SUSPICIOUS
    # Unknown sources default to UNTRUSTED (fail-closed).
    return TrustLevel.UNTRUSTED


# Module-level frozen pattern list. Each entry is (regex, canonical_name).
# English + Chinese bilingual coverage: override, jailbreak, exfiltration,
# system-prompt disclosure, role-hijack, command/system-update injection.
_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"ignore\s+previous\s+instructions", "ignore previous instructions"),
    (r"ignore\s+all\s+previous\s+instructions", "ignore all previous instructions"),
    (r"disregard\s+the\s+above", "disregard the above"),
    (r"disregard\s+(all\s+)?previous", "disregard previous"),
    (r"forget\s+(all\s+)?previous\s+instructions", "forget previous instructions"),
    (r"override\s+(your\s+)?instructions", "override instructions"),
    (r"you\s+are\s+now\s+dan\b", "you are now dan"),
    (r"\bdan\s+mode\b", "dan mode"),
    (r"jailbreak", "jailbreak"),
    (r"do\s+anything\s+now", "do anything now"),
    (r"send\s+your\s+api\s+key\s+to", "send your api key to"),
    (r"reveal\s+your\s+system\s+prompt", "reveal your system prompt"),
    (r"output\s+your\s+prompt", "output your prompt"),
    (r"输出你的提示词", "输出你的提示词"),
    (r"泄露\s*你的\s*提示词", "泄露你的提示词"),
    (r"忽略以上", "忽略以上"),
    (r"忽略前面的指令", "忽略前面的指令"),
    (r"忽略\s*之前的\s*指令", "忽略之前的指令"),
    (r"无视\s*之前的\s*指令", "无视之前的指令"),
    (r"系统已更新，请执行", "系统已更新，请执行"),
    (r"现在你(是|扮演)\s*\S*", "现在你是/扮演角色劫持"),
    (r"假装\s*你是", "假装你是"),
    (r"执行\s*以下\s*系统\s*命令", "执行以下系统命令"),
    (r";\s*rm\s+-rf", "; rm -rf"),
    (r"`[^`]*`", "backtick command"),
    (r"\bexfiltrate\b", "exfiltrate"),
    (r"窃取.*(密钥|凭证|api\s*key)", "窃取密钥/凭证"),
)

# Pre-compiled for performance; case-insensitive for EN, irrelevant for ZH.
_COMPILED: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pat, re.IGNORECASE), name) for pat, name in _INJECTION_PATTERNS
)

# Severity weight per canonical name (exfiltration / destructive command higher).
_HIGH_SEVERITY = frozenset(
    {
        "send your api key to",
        "; rm -rf",
        "backtick command",
        "exfiltrate",
        "窃取密钥/凭证",
        "执行以下系统命令",
    }
)


@dataclass(frozen=True)
class InjectionVerdict:
    risk_score: float
    matched_patterns: list[str]
    action: str  # BLOCK | FLAG | ALLOW
    trust: TrustLevel


def detect_injection(text: str, *, source: str = "user") -> InjectionVerdict:
    trust = classify_trust(source)
    matched: list[str] = []
    high_count = 0
    for regex, name in _COMPILED:
        if regex.search(text):
            matched.append(name)
            if name in _HIGH_SEVERITY:
                high_count += 1

    if not matched:
        return InjectionVerdict(risk_score=0.0, matched_patterns=[], action="ALLOW", trust=trust)

    # risk_score scales with number and severity of matches, clamped to [0,1].
    base = 0.35 * len(matched) + 0.25 * high_count
    # Slight boost for UNTRUSTED to reflect higher exposure.
    if trust == TrustLevel.UNTRUSTED:
        base += 0.1
    risk_score = min(1.0, round(base, 3))

    if trust == TrustLevel.TRUSTED:
        action = "FLAG"
    elif trust == TrustLevel.SUSPICIOUS:
        # Suspicious behaves like UNTRUSTED but explicitly flagged as suspicious.
        action = "BLOCK"
    else:
        action = "BLOCK"

    return InjectionVerdict(
        risk_score=risk_score,
        matched_patterns=matched,
        action=action,
        trust=trust,
    )


def run_guard_eval(corpus_path: Path) -> dict[str, int]:
    total = 0
    blocked = 0
    flagged = 0
    allowed = 0
    mismatches = 0
    with open(corpus_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            total += 1
            text = record.get("text", "")
            source = record.get("source", "user")
            expected = record.get("expected_action", "ALLOW")
            verdict = detect_injection(text, source=source)
            if verdict.action == "BLOCK":
                blocked += 1
            elif verdict.action == "FLAG":
                flagged += 1
            else:
                allowed += 1
            if verdict.action != expected:
                mismatches += 1
    return {
        "total": total,
        "blocked": blocked,
        "flagged": flagged,
        "allowed": allowed,
        "mismatches": mismatches,
    }
