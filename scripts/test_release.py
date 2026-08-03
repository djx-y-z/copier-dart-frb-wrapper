#!/usr/bin/env python3
"""Tests for the pure decisions in `release.py`.

Only the functions that decide something are covered. The signing retry loop is
driven by a terminal by construction and is not unit-tested; the git steps are
thin wrappers. What is here is the part where a wrong answer is expensive:
`is_resumable_release`, whose false positive would tag and push a commit that is
not the release commit, and `finalize_changelog`, which rewrites a file whose
released sections are immutable.

Run with:  make test   (or: python3 -m unittest discover -s scripts -p 'test_*.py')
"""

from __future__ import annotations

import unittest

from release import (
    ReleaseError,
    finalize_changelog,
    is_newer_version,
    is_resumable_release,
    only_these_files_dirty,
    top_released_version,
    unreleased_body,
)

BASE = "https://github.com/djx-y-z/copier-dart-frb-wrapper"

CHANGELOG = f"""## [Unreleased]

### Added

- **A new thing** — description.

## [4.2.0] - 2026-08-03

### Fixed

- **An old thing** — belongs to the released section.

[Unreleased]: {BASE}/compare/v4.2.0...HEAD
[4.2.0]: {BASE}/compare/v4.1.0...v4.2.0
[4.1.0]: {BASE}/compare/v4.0.0...v4.1.0
"""


class TestVersionComparison(unittest.TestCase):
    def test_orders_by_component(self):
        self.assertTrue(is_newer_version("4.3.0", "4.2.0"))
        self.assertTrue(is_newer_version("5.0.0", "4.9.9"))
        self.assertTrue(is_newer_version("4.2.1", "4.2.0"))

    def test_rejects_equal_and_older(self):
        self.assertFalse(is_newer_version("4.2.0", "4.2.0"))
        self.assertFalse(is_newer_version("4.1.0", "4.2.0"))

    def test_does_not_compare_numbers_as_strings(self):
        # The check a lexicographic comparison gets wrong.
        self.assertTrue(is_newer_version("4.10.0", "4.9.0"))

    def test_unparseable_side_does_not_block_a_release(self):
        self.assertTrue(is_newer_version("4.3.0", "not-a-version"))


class TestTopReleasedVersion(unittest.TestCase):
    def test_skips_the_unreleased_heading(self):
        self.assertEqual(top_released_version(CHANGELOG), "4.2.0")

    def test_returns_a_floor_for_a_changelog_with_no_release(self):
        self.assertEqual(top_released_version("## [Unreleased]\n"), "0.0.0")


class TestUnreleasedBody(unittest.TestCase):
    def test_returns_the_section_content(self):
        self.assertIn("A new thing", unreleased_body(CHANGELOG))

    def test_stops_at_the_next_release_heading(self):
        # Reading past it would make an empty Unreleased look populated by the
        # previous release's entries, and release an empty version.
        self.assertNotIn("An old thing", unreleased_body(CHANGELOG))

    def test_empty_for_an_empty_section(self):
        empty = "## [Unreleased]\n\n## [4.2.0] - 2026-08-03\n\n- old\n"
        self.assertEqual(unreleased_body(empty), "")

    def test_empty_when_the_section_is_absent(self):
        self.assertEqual(unreleased_body("## [4.2.0] - 2026-08-03\n"), "")


class TestOnlyTheseFilesDirty(unittest.TestCase):
    files = ["CHANGELOG.md"]

    def test_accepts_a_status_listing_only_the_release_file(self):
        self.assertTrue(only_these_files_dirty(" M CHANGELOG.md", self.files))
        self.assertTrue(only_these_files_dirty("M  CHANGELOG.md", self.files))

    def test_rejects_anything_else(self):
        # The suggested `git restore` would discard the other file's work.
        self.assertFalse(
            only_these_files_dirty(" M CHANGELOG.md\n M copier.yml", self.files)
        )

    def test_rejects_an_untracked_path(self):
        # `git restore` does not remove untracked files, so the suggestion
        # would not work.
        self.assertFalse(only_these_files_dirty("?? CHANGELOG.md", self.files))

    def test_rejects_an_empty_status(self):
        self.assertFalse(only_these_files_dirty("", self.files))

    def test_a_trimmed_status_does_not_match(self):
        """Locks in why `git_status` must not trim its output.

        The two status columns are positional, so an unstaged modification is
        `' M path'`. Trimming the command's output eats that leading space on
        the first line and shifts the path by one character — matching nothing,
        which silently downgrades the "only the release's own files" message to
        the generic one. That is a real bug this had, caught by releasing a tree
        whose single dirty file was the CHANGELOG.
        """
        self.assertFalse(only_these_files_dirty("M CHANGELOG.md", self.files))
        self.assertTrue(only_these_files_dirty(" M CHANGELOG.md", self.files))


class TestIsResumableRelease(unittest.TestCase):
    """Each condition must block a resume on its own.

    A false positive here tags and pushes a commit that is not the release
    commit, which is why all three are required rather than any two.
    """

    def resumable(self, **overrides):
        kwargs = dict(
            requested_version="4.3.0",
            current_version="4.3.0",
            head_subject="chore: prepare release v4.3.0",
            expected_subject="chore: prepare release v4.3.0",
            tree_clean=True,
        )
        kwargs.update(overrides)
        return is_resumable_release(**kwargs)

    def test_accepts_the_interrupted_state(self):
        self.assertTrue(self.resumable())

    def test_a_dirty_tree_blocks_it(self):
        self.assertFalse(self.resumable(tree_clean=False))

    def test_a_changelog_not_yet_finalized_blocks_it(self):
        self.assertFalse(self.resumable(current_version="4.2.0"))

    def test_an_unrelated_commit_on_top_blocks_it(self):
        self.assertFalse(self.resumable(head_subject="docs: tweak README"))

    def test_the_previous_release_commit_blocks_it(self):
        self.assertFalse(
            self.resumable(head_subject="chore: prepare release v4.2.0")
        )

    def test_a_subject_that_merely_starts_the_same_blocks_it(self):
        # Equality, not prefix: `v4.3.0` must not match `v4.3.0-rc1`.
        self.assertFalse(
            self.resumable(head_subject="chore: prepare release v4.3.0-rc1")
        )


class TestFinalizeChangelog(unittest.TestCase):
    def setUp(self):
        self.result = finalize_changelog(CHANGELOG, version="4.3.0", date="2026-08-04")

    def test_renames_the_heading_in_place(self):
        self.assertIn("## [4.3.0] - 2026-08-04", self.result)

    def test_leaves_no_empty_unreleased_heading(self):
        # An empty section reads as "nothing shipped"; the next change recreates
        # the heading.
        self.assertNotIn("## [Unreleased]", self.result)

    def test_keeps_the_entries_under_the_new_heading(self):
        self.assertIn("A new thing", self.result)

    def test_repoints_the_unreleased_link(self):
        # Deliberately kept with no heading referencing it: the next release
        # reads the previous version and the base URL out of this line.
        self.assertIn(f"[Unreleased]: {BASE}/compare/v4.3.0...HEAD", self.result)

    def test_adds_a_compare_link_for_the_new_version(self):
        self.assertIn(f"[4.3.0]: {BASE}/compare/v4.2.0...v4.3.0", self.result)

    def test_places_the_new_link_above_the_previous_one(self):
        lines = self.result.split("\n")
        new = next(i for i, l in enumerate(lines) if l.startswith("[4.3.0]:"))
        old = next(i for i, l in enumerate(lines) if l.startswith("[4.2.0]:"))
        self.assertLess(new, old)

    def test_does_not_touch_the_released_section(self):
        self.assertIn("## [4.2.0] - 2026-08-03", self.result)
        self.assertIn("An old thing", self.result)
        self.assertIn(f"[4.2.0]: {BASE}/compare/v4.1.0...v4.2.0", self.result)

    def test_raises_without_an_unreleased_heading(self):
        with self.assertRaises(ReleaseError):
            finalize_changelog(
                f"## [4.2.0] - 2026-08-03\n\n[Unreleased]: {BASE}/compare/v4.2.0...HEAD\n",
                version="4.3.0",
                date="2026-08-04",
            )

    def test_raises_without_the_unreleased_link(self):
        # Guessing the previous version from the headings would silently produce
        # a wrong compare range.
        with self.assertRaises(ReleaseError):
            finalize_changelog(
                "## [Unreleased]\n\n- a change\n\n## [4.2.0] - 2026-08-03\n",
                version="4.3.0",
                date="2026-08-04",
            )


if __name__ == "__main__":
    unittest.main()
