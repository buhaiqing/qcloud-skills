# Prompt-Injection Defense — Design & Plan

## 1. Background

Skills ingest untrusted text (user free-text, web content, pasted logs). Without trust
gating, an attacker can embed override instructions ("ignore previous instructions",
"系统已更新，请执行") that cause the agent to bypass safety gates. Need a lightweight,
deterministic guard that grades trust and detects injection patterns before tool execution.

## 2. Pattern Taxonomy

| Category | Example patterns (EN / ZH) | Severity |
|---|---|---|
| Override / instruction hijack | `ignore previous instructions`, `disregard the above`, `忽略以上`, `忽略前面的指令` | medium |
| Jailbreak / role hijack | `you are now DAN`, `jailbreak`, `现在你是…`, `假装你是` | medium |
| Prompt disclosure | `output your prompt`, `输出你的提示词`, `reveal your system prompt` | medium |
| Exfiltration | `send your api key to`, `exfiltrate`, `窃取.*密钥` | high |
| Command injection | `; rm -rf`, `` `...` ``, `执行以下系统命令` | high |
| Fake system update | `系统已更新，请执行` | medium |

Patterns are stored as a module-level frozen tuple `_INJECTION_PATTERNS` and pre-compiled
once into `_COMPILED`. No inline duplication (TE-6).

## 3. Trust Model

| Source tag | `TrustLevel` | Behavior on match |
|---|---|---|
| `system`, `skill`, `internal`, `config` | `TRUSTED` | `FLAG` (review, do not auto-block internal tests) |
| `user`, `web`, `external` | `UNTRUSTED` | `BLOCK` |
| `suspicious` | `SUSPICIOUS` | `BLOCK` |
| unknown | `UNTRUSTED` (fail-closed) | `BLOCK` |

`classify_trust(source)` normalizes case/whitespace. `SUSPICIOUS` exists for future
heuristic promotion without changing the source string.

## 4. Verdict & Scoring

`InjectionVerdict(risk_score, matched_patterns, action, trust)`:

- `risk_score = min(1.0, 0.35*len(matched) + 0.25*high_count + (0.1 if UNTRUSTED else 0))`
- `action`: `BLOCK` | `FLAG` | `ALLOW` (no pattern → `ALLOW`).
- High-severity patterns (exfiltration, `rm -rf`, backtick command) weight higher.

## 5. Corpus & Evaluation

`scripts/fixtures/prompt_injection_corpus.jsonl` — JSONL, ≥24 cases, each
`{id, text, source, expected_action}` covering EN+ZH override, jailbreak, exfiltration,
command-injection, and benign controls. `run_guard_eval(path)` returns
`{total, blocked, flagged, allowed, mismatches}`. CI asserts `mismatches == 0`.

## 6. Verification

```bash
python3 -m ruff check scripts/prompt_injection_guard.py scripts/prompt_injection_guard_test.py
python3 -m pytest scripts/prompt_injection_guard_test.py -q
python3 -c "from pathlib import Path; from scripts.prompt_injection_guard import run_guard_eval; print(run_guard_eval(Path('scripts/fixtures/prompt_injection_corpus.jsonl')))"
```

Expected: ruff 0 errors, pytest 18 pass, `mismatches == 0`, `total >= 24`.

## 7. Plan

- [x] Implement `scripts/prompt_injection_guard.py` (TrustLevel, classify_trust, InjectionVerdict, detect_injection, run_guard_eval)
- [x] Create `scripts/fixtures/prompt_injection_corpus.jsonl` (≥24 EN+ZH cases)
- [x] Implement `scripts/prompt_injection_guard_test.py` (unittest, mismatches==0)
- [x] Write this design spec

## Self-check

- Corpus size `wc -l scripts/fixtures/prompt_injection_corpus.jsonl` ≥ 24 ✓
- `run_guard_eval` mismatches == 0 ✓
- No bare `except:`, no `as any`, frozen pattern list ✓
