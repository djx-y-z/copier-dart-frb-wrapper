#!/usr/bin/env python3
"""Guard: nothing under `template/` may name one particular generated project.

The template is shared by every project generated from it, so a hardcoded
`libsignal` reaches a repository wrapping something else and tells its
contributors about a library they do not have. That is not hypothetical — four
of them were found at once (2026-09-04), and the most expensive sat in
`.github/workflows/codegen-guard.yml`, a file with no `.jinja` suffix and
therefore no substitution at all: the only sentence a human reads when that
gate fires named the wrong library.

Prose is exactly where this hides. The Jinja variables are used correctly in
the code around it — `{{ package_name }}`, `{{ native_library_name }}`,
`{{ crate_name }}` — while a comment two lines above still names the project
the text was first written in. Nothing renders it, nothing compiles it, and no
generated project's CI has any reason to complain.

Run with:  make test
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template"

# The upstream libraries and the projects wrapping them. Add a name here when a
# new project is generated: the cost of a false positive is one commit that has
# to reach for a variable, and the cost of a miss is shipping it to everyone.
#
# Matched case-insensitively and as a substring, so `libsignal` also catches
# `libsignal_frb`, `build-libsignal.yml` and `LibSignal`.
FORBIDDEN = [
    "libsignal",
    "signalapp",
    "openmls",
]

# The template's own repository is not a project name: every generated project
# updates from it, so its URL is correct everywhere and appears on purpose.
ALLOWED_SUBSTRINGS = [
    "copier-dart-frb-wrapper",
]


def _offending_lines(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable: nothing to read a name out of
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        haystack = line.lower()
        for allowed in ALLOWED_SUBSTRINGS:
            haystack = haystack.replace(allowed.lower(), "")
        for name in FORBIDDEN:
            if name in haystack:
                hits.append((lineno, name, line.strip()))
    return hits


class NoProjectNamesInTemplate(unittest.TestCase):
    def test_template_names_no_particular_project(self) -> None:
        self.assertTrue(TEMPLATE.is_dir(), f"{TEMPLATE} not found")

        findings = []
        for path in sorted(TEMPLATE.rglob("*")):
            if not path.is_file():
                continue
            for lineno, name, line in _offending_lines(path):
                rel = path.relative_to(TEMPLATE.parent)
                findings.append(f"{rel}:{lineno} names '{name}': {line[:120]}")

        self.assertEqual(
            findings,
            [],
            "template/ must not name one generated project — use the Jinja "
            "variables (`{{ package_name }}`, `{{ native_library_name }}`, "
            "`{{ crate_name }}`) or neutral wording such as 'the upstream "
            "library'. In a file with no `.jinja` suffix there is no "
            "substitution, so the wording has to be neutral.\n  "
            + "\n  ".join(findings),
        )


if __name__ == "__main__":
    unittest.main()
