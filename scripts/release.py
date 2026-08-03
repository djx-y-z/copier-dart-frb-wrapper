#!/usr/bin/env python3
"""Release this copier template: finalize the CHANGELOG, sign a commit and a
tag, and push them.

A template release is just a git tag — copier reads its versions from tags, and
`.github/workflows/release.yml` turns a pushed `v*` tag into a GitHub Release
whose notes are the CHANGELOG section for that version. So the whole job is:
rename `## [Unreleased]`, fix the compare links, commit, tag, push. Doing that
by hand is what this replaces.

Python and nothing else on purpose. The one hard dependency this repository
already has is copier, which is Python; a Dart script would add a second
toolchain that nothing else here needs, and rewriting the CHANGELOG's link
footer with sed is exactly the kind of thing that silently half-works.

The two behaviours worth knowing about are inherited from the release scripts
this template ships to generated projects, because they were written for the
same problem:

  * **A mistyped signing passphrase does not abort the release.** Git signs by
    shelling out to `ssh-keygen -Y sign`, which reads the passphrase once and
    gives up. Every signing and push step is retried instead (see
    `run_inherit_retry`).
  * **An interrupted release is resumed by re-running the same command.** A run
    that dies between its commit and its tag leaves a state that blocks its own
    retry, so that state is detected and continued from.

Usage:
    python3 scripts/release.py --version 4.3.0
    python3 scripts/release.py --version 4.3.0 --no-push
    make release ARGS="--version 4.3.0"
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import time

CHANGELOG = "CHANGELOG.md"
RELEASE_FILES = [CHANGELOG]
MAIN_BRANCH = "main"


# --------------------------------------------------------------------------
# Terminal output
# --------------------------------------------------------------------------

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def log_step(msg: str) -> None:
    print(_c(f"[STEP] {msg}", "36"))


def log_info(msg: str) -> None:
    print(_c(f"[INFO] {msg}", "34"))


def log_warn(msg: str) -> None:
    print(_c(f"[WARN] {msg}", "33"))


def log_error(msg: str) -> None:
    print(_c(f"[ERROR] {msg}", "31"))


def log_success(msg: str) -> None:
    print(_c(f"[OK] {msg}", "32"))


class ReleaseError(Exception):
    """A precondition failed, or a step could not be completed."""


# --------------------------------------------------------------------------
# Process helpers
# --------------------------------------------------------------------------


def _git_raw(args: list[str]) -> str:
    """Runs a read-only git command and returns stdout with trailing newlines
    removed, but nothing else touched."""
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.rstrip("\n")


def git(args: list[str]) -> str:
    """Runs a read-only git command and returns fully trimmed stdout.

    For scalar answers — a sha, a branch name, a count. Not for
    `status --porcelain`; see `git_status`.
    """
    return _git_raw(args).strip()


def git_status() -> str:
    """`git status --porcelain`, with leading whitespace preserved.

    The two status columns are positional: an unstaged modification is
    `' M path'`, so the first line begins with a space. Trimming the output
    would shift that line's path by one character and make it match nothing —
    which silently downgrades the "only the release's own files are dirty"
    message to the generic one. Found by releasing a tree whose single dirty
    file was the CHANGELOG and getting the generic message.
    """
    return _git_raw(["status", "--porcelain"])


def stdin_is_terminal() -> bool:
    """Whether a human can answer a prompt, retype a passphrase, or Ctrl-C.

    `isatty()` is the honest test here, unlike the Dart equivalent this mirrors:
    Dart's `stdin.hasTerminal` reports a terminal for any character device and
    so calls a run redirected from `/dev/null` interactive. Python's does not —
    checked against `/dev/null`, a pipe and a regular file, all False.
    """
    return sys.stdin.isatty()


def run_inherit(cmd: list[str], fail_message: str | None = None) -> None:
    """Runs a command with inherited stdio, raising on a non-zero exit.

    Inherited stdio is what makes the signing passphrase prompt work: the child
    owns the terminal.
    """
    code = subprocess.run(cmd, check=False).returncode
    if code != 0:
        message = fail_message or f"`{' '.join(cmd)}` failed"
        raise ReleaseError(f"{message} (exit {code})")


def run_inherit_retry(
    cmd: list[str],
    *,
    what: str,
    fail_message: str | None = None,
    already_done=None,
    before_retry=None,
) -> None:
    """Like `run_inherit`, but re-runs the step on failure instead of raising.

    This exists for the signing steps. `ssh-keygen -Y sign` reads the passphrase
    exactly once and fails on a typo rather than re-prompting, so without a
    retry a single typo aborts the release wherever it happened — and the
    position that hurts is between the commit and the tag, a state that blocks
    its own retry.

    The retry is automatic and unprompted: the failure is printed and the step
    runs again, so the passphrase prompt simply comes back, the way `ssh` and
    `sudo` behave. **Ctrl-C is the interactive way out**, and it must stay one —
    nothing in this path may install a SIGINT handler without exiting from it.

    The loop is uncapped on purpose, because a cap would reinstate the very
    failure it prevents: the run that dies on the last allowed attempt. Two
    things bound it instead. A **non-interactive stdin raises on the first
    failure**, since nobody is there to retype anything or to interrupt, and a
    structurally broken step would otherwise spin forever. **From the third
    consecutive failure the loop paces itself**, so a step failing in
    milliseconds for a reason no passphrase will fix cannot scroll past faster
    than it can be read.
    """
    attempt = 0
    while True:
        attempt += 1
        code = subprocess.run(cmd, check=False).returncode
        if code == 0:
            return

        if already_done is not None and already_done():
            log_warn(f"{what} exited {code}, but its result is already in place.")
            return

        print("")
        log_error(f"{what} failed (exit {code}).")

        if not stdin_is_terminal():
            message = fail_message or f"`{' '.join(cmd)}` failed"
            raise ReleaseError(f"{message} (exit {code})")

        if attempt >= 3:
            log_warn(
                f"Attempt {attempt} failed. Retrying in 2s — press Ctrl-C to "
                "abort. If a passphrase is not what is failing, the message "
                "above says what is."
            )
            time.sleep(2)
        else:
            log_info(
                "A mistyped signing passphrase is the usual cause — signing "
                "tools do not re-prompt on their own. Retrying; enter it again "
                "(Ctrl-C to abort)."
            )
        if before_retry is not None:
            before_retry()


def confirm(prompt: str) -> bool:
    """Asks a yes/no question, defaulting to no.

    Returns False without prompting when stdin is not a terminal, and False on
    EOF, so a non-interactive run neither blocks nor reads an empty stdin as
    consent.
    """
    if not stdin_is_terminal():
        return False
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_RELEASED_HEADING_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")
_UNRELEASED_LINK_RE = re.compile(
    r"^\[Unreleased\]:\s*(\S+?)/compare/v(\d+\.\d+\.\d+)\.\.\.HEAD\s*$"
)


def is_newer_version(a: str, b: str) -> bool:
    """Whether `a` is a strictly greater X.Y.Z version than `b`.

    An unparseable side warns and returns True, so a release is never blocked on
    a parse quirk.
    """
    ma, mb = _VERSION_RE.match(a.strip()), _VERSION_RE.match(b.strip())
    if not ma or not mb:
        log_warn(
            f'Could not compare versions "{a}" and "{b}"; skipping the '
            "greater-than check."
        )
        return True
    return tuple(int(x) for x in ma.groups()) > tuple(int(x) for x in mb.groups())


def top_released_version(changelog: str) -> str:
    """The newest released version in the CHANGELOG, or '0.0.0' if there is none.

    This is the repository's version: there is no manifest to read, and the tag
    is created by this script, so the newest finalized heading is what "current"
    means both for the greater-than check and for detecting a resumed run.
    """
    for line in changelog.split("\n"):
        m = _RELEASED_HEADING_RE.match(line)
        if m:
            return m.group(1)
    return "0.0.0"


def unreleased_body(changelog: str) -> str:
    """The content under `## [Unreleased]`, or '' when the section is absent."""
    lines = changelog.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if line.startswith("## [Unreleased]"):
            start = i
            break
    if start == -1:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## ["):
            break
        body.append(line)
    return "\n".join(body).strip()


def only_these_files_dirty(porcelain_status: str, files: list[str]) -> bool:
    """Whether every dirty path is one of `files`.

    Conservative by construction: an empty status, an untracked path (`??`,
    which `git restore` would not help with) and a rename (whose payload is
    `old -> new` and matches no plain path) all return False, so the caller
    falls back to its generic message rather than suggesting a command that
    would not work — or one that would discard something else.
    """
    lines = [l for l in porcelain_status.split("\n") if l.strip()]
    if not lines:
        return False
    return all(
        len(l) > 3 and not l.startswith("??") and l[3:] in files for l in lines
    )


def is_resumable_release(
    *,
    requested_version: str,
    current_version: str,
    head_subject: str,
    expected_subject: str,
    tree_clean: bool,
) -> bool:
    """Whether a previous run already produced this release's commit.

    This is the one predicate here whose false positive is unrecoverable — it
    would tag and push a commit that is not the release commit — so it requires
    all of: a clean tree, the CHANGELOG already finalized to the requested
    version, and `HEAD`'s subject being exactly the subject this release writes
    (not merely a commit made afterwards).

    `expected_subject` must come from the same variable passed to
    `git commit -m`, so the two cannot drift apart and silently disable
    resuming.
    """
    return (
        tree_clean
        and current_version == requested_version
        and head_subject == expected_subject
    )


def finalize_changelog(changelog: str, *, version: str, date: str) -> str:
    """Turns `## [Unreleased]` into `## [version] - date` and fixes the links.

    Two edits, mirroring what this template's own release scripts do for
    generated projects:

      1. The `## [Unreleased]` heading is renamed **in place**. No fresh empty
         `## [Unreleased]` is emitted — the next unreleased change recreates it,
         and an empty section left behind reads as "nothing shipped".
      2. The bottom `[Unreleased]:` compare link is repointed at the new version
         and a `[version]:` link is inserted below it.

    The previous version and the repository URL are both read out of the
    existing `[Unreleased]:` link, which makes it the single source of truth for
    the compare range and means this function needs no repo slug. That footer
    link is deliberately kept even though no heading references it any more:
    it is what the next release reads.

    Raises if either the heading or the link is missing, rather than guessing.
    """
    lines = changelog.split("\n")

    heading_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("## [Unreleased]"):
            heading_idx = i
            break
    if heading_idx == -1:
        raise ReleaseError(f'No "## [Unreleased]" heading found in {CHANGELOG}.')

    link_idx, base, previous = -1, "", ""
    for i, line in enumerate(lines):
        m = _UNRELEASED_LINK_RE.match(line)
        if m:
            link_idx, base, previous = i, m.group(1), m.group(2)
            break
    if link_idx == -1:
        raise ReleaseError(
            'No "[Unreleased]: <base>/compare/vX.Y.Z...HEAD" link found at the '
            f"bottom of {CHANGELOG}. It is what the compare range is built "
            "from; restore it and re-run."
        )

    # Rename first, then edit the footer: the heading always precedes the links,
    # so this ordering keeps both indices valid without recomputing them.
    lines[heading_idx] = f"## [{version}] - {date}"
    lines[link_idx] = f"[Unreleased]: {base}/compare/v{version}...HEAD"
    lines.insert(link_idx + 1, f"[{version}]: {base}/compare/v{previous}...v{version}")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Release
# --------------------------------------------------------------------------


def release(version: str, *, push: bool) -> None:
    repo_root = git(["rev-parse", "--show-toplevel"])
    os.chdir(repo_root)

    tag = f"v{version}"
    commit_subject = f"chore: prepare release {tag}"
    release_date = datetime.date.today().isoformat()

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch != MAIN_BRANCH:
        raise ReleaseError(
            f"Releases are cut from {MAIN_BRANCH}; you are on {branch}."
        )

    status = git_status()
    tree_clean = status == ""

    changelog_path = os.path.join(repo_root, CHANGELOG)
    with open(changelog_path, encoding="utf-8") as f:
        changelog = f.read()
    current = top_released_version(changelog)

    # A run that died between its commit and its tag already finalized the
    # CHANGELOG and committed it, leaving nothing to tag. Recognise that exact
    # state and continue from there, instead of tripping the "must be greater"
    # check and leaving a manual tag-and-push as the only way forward.
    resuming = is_resumable_release(
        requested_version=version,
        current_version=current,
        head_subject=git(["log", "-1", "--pretty=%s"]),
        expected_subject=commit_subject,
        tree_clean=tree_clean,
    )

    if not tree_clean and not resuming:
        if only_these_files_dirty(status, RELEASE_FILES):
            raise ReleaseError(
                "Working tree is not clean — the only modified paths are this "
                "release's own files, which an interrupted run leaves behind.\n"
                f"{status}\n"
                f"Discard them with: git restore {' '.join(RELEASE_FILES)}"
            )
        raise ReleaseError(
            f"Working tree is not clean. Commit or stash first.\n{status}"
        )

    if resuming:
        log_warn(
            f'Resuming an interrupted release: "{commit_subject}" is already '
            "the HEAD commit, so the CHANGELOG edit is skipped."
        )
    else:
        if not is_newer_version(version, current):
            raise ReleaseError(
                f"New version {version} must be greater than the current "
                f"released version {current}."
            )
        if not unreleased_body(changelog):
            raise ReleaseError(
                f'The "## [Unreleased]" section of {CHANGELOG} is empty — there '
                "is nothing to release. Describe the changes first."
            )

    # A leftover tag is resumable only when it is this release's tag AND points
    # at the release commit; the same name on any other commit is a conflict
    # this must not push over.
    tag_created = False
    if git(["tag", "--list", tag]):
        tagged = git(["rev-list", "-n", "1", tag])
        if resuming and tagged == git(["rev-parse", "HEAD"]):
            tag_created = True
            log_warn(f"Tag {tag} already exists on HEAD; skipping tag creation.")
        else:
            raise ReleaseError(
                f"Tag {tag} already exists locally, on {tagged[:7]}. Delete it "
                f"(git tag -d {tag}) or release a different version."
            )

    log_step("Fetching origin...")
    git(["fetch", "origin", MAIN_BRANCH, "--no-tags", "--quiet"])
    if git(["ls-remote", "--tags", "origin", tag]):
        raise ReleaseError(
            f"Tag {tag} already exists on origin — {tag} is already released. "
            "Release a higher version."
        )

    behind = git(["rev-list", "--count", f"HEAD..origin/{MAIN_BRANCH}"])
    if behind != "0":
        raise ReleaseError(
            f"Local {MAIN_BRANCH} is behind origin/{MAIN_BRANCH} by {behind} "
            f"commit(s). Run: git pull --ff-only origin {MAIN_BRANCH}"
        )
    ahead = git(["rev-list", "--count", f"origin/{MAIN_BRANCH}..HEAD"])
    if ahead != "0":
        log_warn(
            f"Local {MAIN_BRANCH} is ahead of origin/{MAIN_BRANCH} by {ahead} "
            "commit(s); these will be pushed with the release commit."
        )

    # ---- Prepare -----------------------------------------------------------
    if resuming:
        log_step("Commit to be tagged:")
        run_inherit(["git", "--no-pager", "log", "-1", "--oneline", "--stat"])
    else:
        log_step(f"Finalizing CHANGELOG: [Unreleased] -> [{version}] - {release_date}")
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(finalize_changelog(changelog, version=version, date=release_date))
        log_step("Changes to be committed:")
        run_inherit(["git", "--no-pager", "diff", "--stat", *RELEASE_FILES])

    # ---- Confirm -----------------------------------------------------------
    if resuming and tag_created and not push:
        log_success(f"Nothing left to do: the commit and tag {tag} already exist.")
        log_info(f"When ready: git push origin {MAIN_BRANCH} && git push origin {tag}")
        return

    steps: list[str] = []
    if not resuming:
        steps.append(f"commit {CHANGELOG} as “{commit_subject}”")
    if not tag_created:
        steps.append(f"create signed tag {tag}")
    if push:
        steps.append(f"push {MAIN_BRANCH} and {tag} to origin")
    else:
        steps.append("stop before pushing (--no-push)")

    print("")
    log_info(f"About to release {tag}:")
    for step in steps:
        log_info(f"  - {step}")
    log_info("Signing prompts appear below; a mistyped passphrase is retried.")
    if not confirm("Proceed?"):
        if not resuming:
            log_warn(f"Aborted — reverting the {CHANGELOG} edit.")
            run_inherit(["git", "checkout", "--", *RELEASE_FILES])
        else:
            log_warn("Aborted. The release commit is left in place.")
        return

    # ---- Commit, tag, push -------------------------------------------------
    if not resuming:
        run_inherit(["git", "add", *RELEASE_FILES])
        run_inherit_retry(
            ["git", "commit", "-m", commit_subject],
            what="git commit",
            already_done=lambda: git(["log", "-1", "--pretty=%s"]) == commit_subject,
            before_retry=lambda: run_inherit(["git", "add", *RELEASE_FILES]),
            fail_message=(
                f"git commit failed and {CHANGELOG} is still staged — fix the "
                "issue and re-run `git commit`/`git tag` by hand, or reset and "
                "start over"
            ),
        )

    if not tag_created:
        run_inherit_retry(
            ["git", "tag", "-s", tag, "-m", f"Release {tag}"],
            what="git tag",
            already_done=lambda: bool(git(["tag", "--list", tag])),
            fail_message=(
                "git tag failed. The release commit exists but is not tagged. "
                "Re-run this command, or tag by hand:\n"
                f'  git tag -s {tag} -m "Release {tag}"'
            ),
        )

    if not push:
        log_success(f"Release {tag} prepared locally (not pushed).")
        log_info(f"When ready: git push origin {MAIN_BRANCH} && git push origin {tag}")
        return

    run_inherit_retry(
        ["git", "push", "origin", MAIN_BRANCH],
        what=f"git push origin {MAIN_BRANCH}",
        fail_message=(
            f"git push origin {MAIN_BRANCH} failed. The commit and tag {tag} "
            "exist locally; push them manually once the cause is fixed."
        ),
    )
    run_inherit_retry(
        ["git", "push", "origin", tag],
        what=f"git push origin {tag}",
        fail_message=f"git push tag failed. Push it manually: git push origin {tag}",
    )

    log_success(f"Released {tag}.")
    log_info("The Release workflow will create the GitHub Release from the tag.")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="Release this copier template (CHANGELOG + signed commit + tag).",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version to release, as X.Y.Z (a leading 'v' is accepted).",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Prepare the commit and tag locally without pushing.",
    )
    args = parser.parse_args()

    version = args.version.strip()
    if version.startswith("v"):
        version = version[1:]
    if not _VERSION_RE.match(version):
        log_error(f'--version must be X.Y.Z, got "{args.version}".')
        return 2

    try:
        release(version, push=not args.no_push)
    except ReleaseError as e:
        print("")
        log_error(str(e))
        return 1
    except KeyboardInterrupt:
        print("")
        log_warn("Interrupted. Re-run the same command to resume.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
