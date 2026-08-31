# Auto-fix for Doc-Code Drift — Design Spec

## Background

`check_doc_code_drift.py` detects oversized Python blocks (≥30 lines, no `AUTHORITATIVE` marker) in docs.
It reports drift but applies no fix. Auto-fix closes the loop: detect + suggest patch, require user
confirmation, then apply.

## Authority Inference Algorithm

```
For each oversized block (>30 lines, no AUTHORITATIVE marker):
  1. Extract import lines: `from xxx import yyy` / `import xxx`
  2. Match pattern: `references.<module>` or `from references import <module>`
     → authority = `references/<module>.py`
  3. Match pattern: relative import (`from .` / `from ..`)
     → authority = `same-file-relative-import` (skip, manual review needed)
  4. No imports, or other imports
     → authority = None → skip (no auto-fix possible)
  5. Replace entire block with: `> 权威实现见 <authority>`
```

**Limitation**: Blocks that contain full script implementations (with stdlib imports like `pathlib`,
`json`) but no `references.*` imports are **not auto-fixable** — they must be resolved manually.
Currently 8 drifted files exist; all contain full scripts without `references.*` imports.

## Modes

| Flag | Behavior |
|------|----------|
| `--dry-run` (default) | Show unified diff, no writes |
| `--apply` | Write changes (blocked without `--confirm yes-i-really-mean-it` or stdin `yes`) |
| `--target <file>` | Process single file |
| `--verbose` / `-v` | Show non-fixable oversized blocks with reason |
| `--self-test` | Run internal assertions, exit 0/1 |

## Safety Gates

- `--apply` requires either `--confirm yes-i-really-mean-it` or stdin `yes`
- Dry-run is the default — zero files modified without explicit `--apply`
- The tool shares detection logic with `check_doc_code_drift.py` (same threshold, same exempt rules)

## Usage Examples

```bash
# Dry-run all docs
python3 scripts/auto_fix_doc_drift.py

# Dry-run with verbose (shows why each block is not fixable)
python3 scripts/auto_fix_doc_drift.py --verbose

# Dry-run single file
python3 scripts/auto_fix_doc_drift.py --target docs/gcl-enforcement-plan.md

# Apply (interactive confirmation)
python3 scripts/auto_fix_doc_drift.py --apply --confirm yes-i-really-mean-it

# Apply via stdin pipe
yes | python3 scripts/auto_fix_doc_drift.py --apply

# Self-test
python3 scripts/auto_fix_doc_drift.py --self-test
```

## Files

| File | Role |
|------|------|
| `scripts/auto_fix_doc_drift.py` | Main script, stdlib-only |
| `scripts/check_doc_code_drift.py` | Detection-only (unchanged) |

## Verification

```bash
python3 -m py_compile scripts/auto_fix_doc_drift.py && echo "compile OK"
ruff check scripts/auto_fix_doc_drift.py && echo "ruff OK"
python3 scripts/auto_fix_doc_drift.py --self-test
python3 scripts/auto_fix_doc_drift.py          # exit 0, dry-run
python3 scripts/auto_fix_doc_drift.py --apply  # exit 1 (blocked)
```
