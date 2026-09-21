# Credential Masking Rules (Shared Reference)

> Source of truth for credential masking across all qcloud-*-ops skills.
> Referenced by SKILL.md template and AGENTS.md.

## Security Warning (MANDATORY)

**NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value in console output, debug messages, error messages, or logs.

## Masking Rules Across All Execution Paths

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `TENCENTCLOUD_SECRET_KEY=<masked>` | `TENCENTCLOUD_SECRET_KEY=abc123...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: InvalidSecretKey.XXX ... actual key...` |
| Log files | `[INFO] Credentials configured: Key=***` | `[INFO] Secret Key: abc123...` |
| Verification | `test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ Key is set"` | `echo "Key=$TENCENTCLOUD_SECRET_KEY"` |
| Python SDK | `SecretKey=os.environ.get("...")` (env read is safe) | `print(f"Config: {config}")` or `logging.info("%s", ...)` |
| Debug/verbose | `⚠️ Debug mode may expose credential values` (warning only) | `--debug` with un-masked credential output |

## Credential Verification

MUST check existence only, never echo the value:
- Bash: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌
- Python: `if os.environ.get("TENCENTCLOUD_SECRET_KEY") == ""` ✅ | `print(os.environ.get("TENCENTCLOUD_SECRET_KEY"))` ❌

## Enforcement

If any execution flow violates this rule, the skill SHALL be blocked from merge as a security incident.
