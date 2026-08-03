---
name: release-template
description: Create a new release of the Copier template. Use when user wants to release a new version, create a tag, or publish the template.
---

# Release Template

Guide for releasing new versions of copier-dart-frb-wrapper.

## Releasing

Write the changes under `## [Unreleased]` (rules below), then:

```bash
make release ARGS="--version 4.3.0"
```

That is the whole release. The script finalizes the CHANGELOG, signs a commit
and a tag, and pushes both; pushing the tag is what makes
`.github/workflows/release.yml` publish the GitHub Release, using the CHANGELOG
section for that version as the notes.

What it does for you, in order:

1. Refuses unless you are on `main`, the tree is clean, `main` is not behind
   origin, the tag does not already exist locally or on origin, the version is
   greater than the last released one, and `## [Unreleased]` is **not empty**.
2. Renames `## [Unreleased]` → `## [X.Y.Z] - <today>` in place, repoints the
   `[Unreleased]:` compare link at the new version and inserts the `[X.Y.Z]:`
   link. The previous version and the repo URL are read out of the existing
   `[Unreleased]:` link — **do not delete that line**; it is what the next
   release reads.
3. Shows the diff, asks for confirmation, then signs the commit and tag.

Two behaviours worth knowing:

- **A mistyped signing passphrase does not abort the release.** `ssh-keygen`
  reads the passphrase once and gives up rather than re-prompting, so every
  signing and push step is retried automatically — the prompt just comes back.
  **Ctrl-C is the way out.**
- **An interrupted release resumes.** A run that dies between its commit and its
  tag leaves a state that blocks a plain re-run. Re-run the same command: it
  recognises that exact state and continues from the tag, without applying the
  CHANGELOG edit twice.

Useful variants:

```bash
make release ARGS="--version 4.3.0 --no-push"   # prepare locally, inspect, push by hand
make test                                        # the release script's own tests
```

## Versioning Rules

Use [Semantic Versioning](https://semver.org/): `vMAJOR.MINOR.PATCH`

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| Breaking changes | MAJOR | Renamed/removed variables, changed defaults that break existing projects |
| New features | MINOR | New variables, new template files, new conditionals |
| Bug fixes | PATCH | Typo fixes, documentation updates, minor corrections |

## CHANGELOG.md Rules

### Released versions are immutable

**NEVER edit entries for already-released versions** (those with a git tag). Released entries are a historical record of what shipped with that tag. If the v1.0.0 entry says `upstream_crate`, it stays `upstream_crate` even if the variable was later renamed to `upstream_crates` in v2.0.0.

- To document a rename/removal: add a new version entry describing the breaking change
- To fix a factual error in an old entry: add a correction note in the new version, not by editing the old one

### Section order

Use [Keep a Changelog](https://keepachangelog.com/) categories in this order:

1. `### Changed (BREAKING)` — for breaking changes (MAJOR version bumps only)
2. `### Added` — new features
3. `### Changed` — non-breaking changes to existing functionality
4. `### Fixed` — bug fixes
5. `### Removed` — removed features
6. `### Security` — security-related changes

Not every section is needed — only include sections that have entries.

### Entry format

- Start each entry with **bold file/component name** followed by em dash and description
- Use backticks for code identifiers: variable names, file names, commands
- For template files, use the Jinja filename: `build-{{ package_name }}.yml.jinja`
- Be specific about what changed and why — "fixed workflow" is too vague

```markdown
- **`check_updates.dart.jinja`** — version normalization now uses configurable `_tagPrefix` constant
- **`Cargo.toml.jinja`** — unified dependency generation to single loop for `upstream_crates`
```

### Examples must be consistent

Use the project's canonical examples throughout:
- Single upstream crate: `libsignal-protocol`
- Multiple upstream crates: `libsignal-protocol,libsignal-core`
- Version tag prefix: `release-v` (for non-standard tags like `release-v1.0.0`)
- Native repo: `signalapp/libsignal`

Do NOT use other libraries (e.g. openmls) as examples — keep all documentation consistent.

### Comparison links

Every version entry needs a comparison link at the bottom of the file:

```markdown
[2.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.9.0...v2.0.0
[1.9.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.8.0...v1.9.0
```

- Each link compares from the previous version tag to the current version tag
- The first version uses `/releases/tag/v1.0.0` (no comparison)
- When releasing: remove the `[Unreleased]` link, add the new version link

### Format reference

```markdown
## [2.0.0] - 2026-02-07

### Changed (BREAKING)
- **`upstream_crate` variable removed** — consolidated into `upstream_crates`

### Changed
- **`Cargo.toml.jinja`** — unified dependency generation

### Added
- **`template/{{ _copier_conf.answers_file }}.jinja`** — Copier answers file

[2.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.9.0...v2.0.0
[1.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/releases/tag/v1.0.0
```

## Pre-Release Verification

Before releasing, verify:

### 1. Test all configurations

```bash
# Basic
rm -rf /tmp/test && copier copy . /tmp/test --trust --defaults \
  --data package_name=test \
  --data description="Test" \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib
ls /tmp/test/test/

# Without web
rm -rf /tmp/test && copier copy . /tmp/test --trust --defaults \
  --data package_name=test \
  --data description="Test" \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib \
  --data enable_web=false

# With upstream
rm -rf /tmp/test && copier copy . /tmp/test --trust --defaults \
  --data package_name=test \
  --data description="Test" \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib \
  --data upstream_crates=some_crate \
  --data upstream_version=v1.0.0
```

### 2. Check documentation is updated

- [ ] README.md - new variables documented
- [ ] CLAUDE.md - template variables table updated
- [ ] CONTRIBUTING.md - examples updated if needed
- [ ] CHANGELOG.md - all changes listed

### 3. Verify no uncommitted changes

```bash
git status
git diff
```

## Doing It by Hand

`make release` is the supported path — these are the steps it performs, for
when something goes wrong mid-release and you have to finish manually.

### Step 1: Update CHANGELOG.md

Rename the `[Unreleased]` heading in place — do **not** leave an empty one
behind, the next change recreates it:

```markdown
## [1.1.0] - 2025-01-28

### Added
- (items that were under Unreleased)
```

Update links at the bottom. Keep the `[Unreleased]:` line: it carries the repo
URL and the previous version that the next release reads.

```markdown
[Unreleased]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.0.0...v1.1.0
```

### Step 2: Commit and Tag

```bash
git add CHANGELOG.md
git commit -m "chore: prepare release v1.1.0"
git tag -s v1.1.0 -m "Release v1.1.0"
git push origin main
git push origin v1.1.0
```

The commit subject must be exactly `chore: prepare release vX.Y.Z` — that is
what `make release` looks for when deciding whether an interrupted release can
be resumed.

### Step 3: GitHub Release

Nothing to do — pushing the tag triggers `.github/workflows/release.yml`, which
creates the release with the CHANGELOG section for that version as its notes.
```

## How Copier Uses Tags

- Copier lists available versions from git tags
- Users see versions when running `copier copy`
- `copier update` detects newer versions
- Without tags, Copier uses HEAD (development mode)

```bash
# User specifies version
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper project --vcs-ref v1.1.0

# User updates to latest
cd project && copier update

# User updates to specific version
copier update --vcs-ref v1.1.0
```

## Hotfix Release

For urgent fixes to a released version:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/v1.0.1 v1.0.0

# Make fixes
# ...

# Update CHANGELOG.md
# Commit and tag
git add .
git commit -m "fix: critical bug fix"
git tag v1.0.1

# Push
git push origin hotfix/v1.0.1
git push origin v1.0.1

# Merge back to main if applicable
git checkout main
git merge hotfix/v1.0.1
git push origin main
```
