#!/usr/bin/env python3
"""Inline the shared blocks in `common/` into every SKILL.md that marks them.

Skills install independently - `npx skills add locallybuild/skills --skill
locally-run` puts exactly one directory on disk - so a skill cannot reference a
file outside its own folder at runtime. Anything every skill needs to say has to
physically appear in each SKILL.md.

That leaves the copies to drift, which is a real failure and not a theoretical
one: a wrong claim about the docs site had to be corrected in six files at once,
and the same block rewrapped in six files again. Six hand-edits is five chances
to miss one.

So the copies stay, but they are generated. Edit `common/<name>.md`, run this,
and every skill carries the same text. Each skill is still self-contained on
disk, which is the constraint that mattered.

Usage:
    scripts/sync-common.py           # write the blocks into each SKILL.md
    scripts/sync-common.py --check   # exit 1 if any skill is out of date

Stdlib only, deliberately: this runs in the skills repo, which carries no
dependency tooling of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_DIR = REPO_ROOT / "common"
SKILLS_DIR = REPO_ROOT / "skills"


def markers(name: str) -> tuple[str, str]:
    """Open/close markers for a shared block.

    HTML comments so they render as nothing and read as nothing - a skill is
    prose an agent reads, and bookkeeping should not compete with it.
    """
    return f"<!-- common:{name} -->", f"<!-- /common:{name} -->"


def replace_block(text: str, name: str, body: str) -> tuple[str, bool]:
    """Return (new_text, changed). Leaves text alone if the markers are absent."""
    start, end = markers(name)
    before, sep, rest = text.partition(start)
    if not sep:
        return text, False
    _, sep_end, after = rest.partition(end)
    if not sep_end:
        raise SystemExit(f"unclosed marker {start} - expected a matching {end}")
    replacement = f"{start}\n{body.rstrip()}\n{end}"
    updated = f"{before}{replacement}{after}"
    return updated, updated != text


def main(argv: list[str]) -> int:
    check_only = "--check" in argv

    blocks = {p.stem: p.read_text() for p in sorted(COMMON_DIR.glob("*.md"))}
    if not blocks:
        raise SystemExit(f"no shared blocks found in {COMMON_DIR}")

    stale: list[str] = []
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = original = skill_file.read_text()
        for name, body in blocks.items():
            text, _ = replace_block(text, name, body)
        if text == original:
            continue
        rel = skill_file.relative_to(REPO_ROOT)
        if check_only:
            stale.append(str(rel))
        else:
            skill_file.write_text(text)
            print(f"updated {rel}")

    if check_only and stale:
        print("These skills are out of date with common/ - run scripts/sync-common.py:")
        for path in stale:
            print(f"  {path}")
        return 1
    if check_only:
        print("all skills are in sync with common/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
