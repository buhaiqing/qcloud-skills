#!/usr/bin/env python3
"""Check secOps file completeness: all secOps references in SKILL.md point to existing files."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_all_skills():
    return sorted([d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("qcloud-") and d.name.endswith("-ops")])


def extract_secops_refs(skill_dir: Path) -> list[dict]:
    """Extract secOps-related file references from SKILL.md."""
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    refs_dir = skill_dir / "references"

    refs = []
    if not skill_md.exists():
        return refs

    content = skill_md.read_text()
    # Match both secops-checklist.md and secops-security-operations.md
    pattern = re.compile(r'\[([^\]]+)\]\(([^\)]*(?:secops[_-][^\)/]+)\.md)\)')

    for m in pattern.finditer(content):
        label = m.group(1)
        rel_path = m.group(2)
        # Resolve relative path
        if rel_path.startswith('references/'):
            target = refs_dir / rel_path[len('references/'):]
        else:
            target = skill_dir / rel_path

        refs.append({
            'skill': skill_name,
            'label': label,
            'referenced_file': rel_path,
            'target_exists': target.exists(),
            'line': content[:m.start()].count('\n') + 1,
        })

    return refs


def check_legacy_filenames() -> list[dict]:
    """Find any remaining secops-checklist.md files."""
    issues = []
    for skill_dir in find_all_skills():
        refs_dir = skill_dir / 'references'
        legacy = refs_dir / 'secops-checklist.md'
        if legacy.exists():
            issues.append({
                'skill': skill_dir.name,
                'type': 'legacy_filename',
                'file': str(legacy.relative_to(ROOT)),
                'severity': 'MEDIUM',
                'detail': 'secops-checklist.md exists but should be renamed to secops-security-operations.md'
            })
    return issues


def main():
    all_issues = []

    # Check broken references
    for skill_dir in find_all_skills():
        for ref in extract_secops_refs(skill_dir):
            if not ref['target_exists']:
                all_issues.append({
                    'skill': ref['skill'],
                    'type': 'broken_reference',
                    'referenced_file': ref['referenced_file'],
                    'referenced_from': f'SKILL.md line {ref["line"]}',
                    'severity': 'HIGH',
                    'detail': f'SKILL.md references {ref["referenced_file"]} but file does not exist'
                })

    # Check legacy filenames
    all_issues.extend(check_legacy_filenames())

    broken_refs = [i for i in all_issues if i['type'] == 'broken_reference']
    legacy = [i for i in all_issues if i['type'] == 'legacy_filename']

    report = {
        'check': 'secops-completeness',
        'timestamp': '2026-07-19T00:00:00+08:00',
        'total_skills': len(find_all_skills()),
        'issues': all_issues,
        'summary': {
            'broken_references': len(broken_refs),
            'legacy_filenames': len(legacy),
            'pass': len(all_issues) == 0
        }
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    # Self-verify
    errors = []
    if report['summary']['broken_references'] > 0:
        errors.append(f"broken_references = {report['summary']['broken_references']}")
    if report['summary']['legacy_filenames'] > 0:
        errors.append(f"legacy_filenames = {report['summary']['legacy_filenames']}")

    if errors:
        print(f"Self-verify FAILED: {errors}", file=sys.stderr)
        sys.exit(1)
    else:
        print('Self-verify: PASS', file=sys.stderr)


if __name__ == '__main__':
    main()
