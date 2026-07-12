## [Unreleased]

### Added

- **`test/hook/build_hook_test.dart.jinja`** — tests for the download-cache key (device vs simulator, version invalidation, architecture distinction, exact artifact identity); ported from fork [ospaarmann/openmls_dart](https://github.com/ospaarmann/openmls_dart) (credit: Ole Spaarmann).
- **`Makefile.jinja`** — `setup-frb-codegen` target that installs `flutter_rust_bridge_codegen` pinned to `FRB_CODEGEN_VERSION` (derived from `frb_version`), so CI and local codegen runs use the same binary and generate identical bindings; `setup-rust-tools` now delegates to it instead of installing an unpinned latest.
- **`LICENSE.appstore.jinja`** — AGPL §7 additional permission for app-store distribution (generic Feeel/wger wording, ported from libsignal_dart): AGPL-compliant apps may convey the package in object-code form through app stores whose terms conflict with the AGPL, provided the source stays available through an unrestricted channel. Generated only when `license == 'AGPL-3.0'` (removed by a post-gen task otherwise); scoped to the repository's own code with an explicit note that it cannot cover the bundled upstream native library. README's License section documents the exception; `LICENSE` itself is untouched so GitHub/pub.dev keep detecting plain AGPL-3.0.
- **`rust/fuzz/examples/gen_corpus.rs`** — seed-corpus generator stub (gated on `enable_fuzzing`, ported as a generic pattern from libsignal_dart's `fuzz-seed`): writes valid inputs to `rust/fuzz/corpus/<target>/` so libFuzzer starts from structurally-correct data; ships working seeds for the placeholder `example` target with instructions to extend per real target. New `make fuzz-seed` target (+ help/CLAUDE.md/SECURITY.md mentions), and the Fuzz workflow regenerates the corpus before every run (skipping gracefully if the generator file was deleted).
- **`scripts/update_changelog.dart.jinja`** — new `--from <ver>` option: fetches the upstream commit list between the two tags via the GitHub compare API and feeds it to the AI alongside the release notes, producing complete changelog entries even when upstream release notes are terse. The update workflow passes `--from` automatically.

### Changed

- **`copier.yml`** — `frb_version` default bumped to `^2.12.0`.
- **`scripts/src/check_updates.dart.jinja`** — `--update` now also bumps the wrapper crate's version in `rust/Cargo.toml`, mirroring the upstream SemVer delta (upstream patch/minor/major bump → same component bumped in the crate, lower components reset; falls back to patch for unparseable versions). Previously a manual "Before Merge" step on every automated update PR; the AI changelog step therefore picks up the correct new crate version for the Highlights line.
- **`scripts/src/update_changelog.dart.jinja`** — the AI now also classifies the update severity (new required `bump` field: patch/minor/major, judged from release notes + commit list rather than version numbers) and, via the new `--crate-version-before` option, raises the crate version above the SemVer-mirror bump when its verdict is more severe — 0.x upstreams routinely ship breaking changes in minor releases, which pure mirroring under-bumps. The AI verdict never lowers the mirror bump. When the verdict is missing or invalid, the mirror bump stands and the PR gets a `bump-unverified` label plus a prominent ⚠️ warning in the body; breaking changelog bullets are prefixed with `**BREAKING:**`. The changelog step now runs before `Update Cargo.lock` so the lock file always reflects the final crate version.
- **`.github/workflows/check-{{ package_name }}-updates.yml.jinja`**:
  - idempotency gate: if an open update PR for the same version already exists, the scheduled run skips regeneration instead of force-pushing a near-identical commit over the PR branch (which also wiped any manual commits pushed to it); `force_update` bypasses the gate
  - installs the pinned FRB codegen binary (`make setup-frb-codegen`) and runs `make get` before `make codegen` — previously the binary was never installed on the runner, so the codegen step failed with exit 127 on every run and every update PR carried the `codegen-failed` label
  - PR body: removed the now-automated "Bump rust/Cargo.toml version" / "Run make rust-check" manual checklist items
- **`.claude/skills/update-{{ package_name }}/SKILL.md.jinja`** — Step 1 rewritten from "read the release notes" to a full upstream-diff analysis: commit list and changed files between tags via the compare API, diff scoped to the bound crates and the API surface referenced in `rust/src/api/`, upstream `Cargo.toml` deltas (MSRV, advisories); CHANGELOG verification now checks the AI entry against those findings.
- **`CLAUDE.md`** — all local template-testing commands now pass `--vcs-ref HEAD` with a note explaining that Copier otherwise renders from the latest git tag, silently ignoring uncommitted changes.

### Fixed

- **`hook/build.dart.jinja`** — download cache is now keyed by crate version and the full platform variant (`<version>-ios-device-arm64` vs `<version>-ios-simulator-arm64`) instead of `targetOS-targetArch`. On Apple-silicon hosts iOS device and simulator builds both mapped to `ios-arm64`, so whichever built first poisoned the cache for the other and dyld rejected the bundled library at runtime (`incompatible platform: have 'iOS-simulator', need 'iOS'`); a version bump could also serve a stale cached binary. Ported from [ospaarmann/openmls_dart](https://github.com/ospaarmann/openmls_dart) (credit: Ole Spaarmann).

- **`copier.yml`** — new `enable_fuzzing` variable (default `true`) that scaffolds a cargo-fuzz harness for the generated package.
- **`rust/fuzz/Cargo.toml.jinja`, `rust/fuzz/fuzz_targets/example.rs.jinja`, `rust/fuzz/.gitignore`** — cargo-fuzz harness with a placeholder target wired to the generated `init_*` function; gated on `enable_fuzzing`.
- **`.github/workflows/fuzz.yml.jinja`** — Fuzz workflow that builds and runs every fuzz target (discovered via `cargo fuzz list`) on `rust/**` pull requests and weekly, with a per-input `-timeout` watchdog and crash-artifact upload; gated on `enable_fuzzing`.
- **`rust/deny.toml.jinja`** — cargo-deny policy (advisories, license allow-list keyed on `license`, source allow-list keyed on `native_repo`).
- **`Makefile.jinja`** — `rust-deny` target; `rust-clippy` target (`cargo clippy --all-targets -- -D warnings`); `setup-fuzz` / `fuzz` / `fuzz-list` targets gated on `enable_fuzzing`; `cargo-deny` added to `setup-rust-tools`.
- **`.github/workflows/test-reusable.yml.jinja`** — `deny` job (cargo-deny) alongside the existing `audit` job; a Rust `clippy` step in the `test` job (Linux x86_64 leg, `-D warnings`).
- **`.github/actions/setup-rust/action.yml.jinja`** — installs the `clippy` component (dtolnay/rust-toolchain's minimal profile omits it, so the new `make rust-clippy` CI step needs it explicit).
- **`README.md.jinja`** — "Known Limitations" section (gated on `enable_web`) documenting that `flutter build web --wasm` / `flutter run -d chrome --wasm` (dart2wasm) is not supported. Calls into Rust fail with `Type 'JSValue' is not a subtype of type 'List<dynamic>'` because FRB's generated Dart decoders use implicit JS-array casts that only work under dart2js. Tracking upstream: [flutter_rust_bridge#2575](https://github.com/fzyzcjy/flutter_rust_bridge/issues/2575)

### Security

- **`hook/build.dart.jinja`** — native-library checksum verification is now **fail-closed**: if the SHA256 checksums cannot be fetched or lack an entry for the archive, the build aborts instead of loading an unverified binary. A `<PACKAGE_NAME>_ALLOW_UNVERIFIED_DOWNLOAD=1` escape hatch is provided for releases without a checksums file.
- **`rust/Cargo.toml.jinja`** — hand-written Rust is compiled with `unsafe_code = "deny"`, and the wrapper crate's release profile enables `overflow-checks` (scoped to the crate so audited upstream dependencies are untouched).
- **`rust/src/lib.rs.jinja`** — the FRB-generated module carries `#[allow(unsafe_code)]` so the deny lint applies only to hand-written code.
- **`.github/workflows/test-reusable.yml.jinja`** — least-privilege `permissions: contents: read` default on the reusable workflow.
- **`SECURITY.md.jinja`** — corrected inaccurate claims (removed the "Signed Releases" wording) and documented the fail-closed verification, cargo-deny, hardened profile, static analysis (Dart analyze + `cargo clippy` in CI), and (when enabled) fuzzing.

### Fixed

- **`copier.yml`** — `_tasks` no longer set `working_directory` to `_copier_conf.dst_path` (tasks already run in the destination by default); with a relative destination path the value resolved against the destination itself (e.g. `gen/gen`) and every task failed. The `example_cli` task now uses a relative `working_directory: example_cli`
- **`CLAUDE.md.jinja`** — removed the `make build ARGS="--release"` example: the Makefile's `build` target already passes `--release`, so the duplicated flag made the documented command fail
- **`scripts/src/check_updates.dart.jinja`** — `updateVersionFiles` now matches `upstream_version` in `.copier-answers.yml` regardless of YAML quoting style (double-quoted, single-quoted, or unquoted) and preserves the original quoting when writing the new version. Previously the regex only matched double-quoted values, so projects whose `.copier-answers.yml` was written with single quotes (Copier's default) silently skipped the update

## [2.4.0] - 2026-02-15

### Added

- **`README.md.jinja`** — coverage badge (shields.io endpoint via GitHub Gist) with username auto-filled from `github_repo`
- **`CONTRIBUTING.md.jinja`** — "Setting up Coverage Badge" section with step-by-step guide (create Gist, PAT, repository secret/variable)
- **`CONTRIBUTING.md.jinja`** — "Setting up pub.dev Publishing" section with OIDC setup on pub.dev and GitHub environment configuration with deployment protection rules
- **`scripts/check_deployment_targets.dart.jinja`** — new script to check deployment target consistency (iOS/macOS/Android) across all project files. Reads expected values from `.copier-answers.yml` and verifies podspecs, CI workflows, Xcode projects, build.gradle, and README match. Supports `--update` to fix mismatches and `--set <version>` to change a target everywhere
- **`Makefile.jinja`** — `check-targets` command for running the deployment targets checker
- **`setup-rust/action.yml.jinja`** — Rust dependency caching via `Swatinem/rust-cache@v2` (speeds up CI builds, especially Windows where vendored OpenSSL takes ~10 min)
- **`setup-rust/action.yml.jinja`** — Strawberry Perl configuration for Windows to fix OpenSSL build (MSYS2 Perl from Git Bash is incompatible)
- **`build-{{ package_name }}.yml.jinja`** — `IPHONEOS_DEPLOYMENT_TARGET` env var for iOS builds using `ios_min_version` template variable (fixes linker errors when vendored C code is compiled with newer Xcode)

### Changed

- **`README.md`** — expanded "On GitHub (create environment)" instructions with detailed deployment protection rules steps and explanation why the `pub.dev` environment is required

### Changed

- **`copier.yml`** — post-generation message now references `CONTRIBUTING.md` instead of `README.md` for GitHub Actions setup instructions
- **`Makefile.jinja`** — replaced `dart run scripts/` with `dart scripts/` for 6 commands (`check-new-*-version`, `check-exists-*-frb-release`, `check-template-updates`, `update-changelog`, `version`, `get-version`), removing `.skip_*_hook` workaround where present. Scripts only use `dart:` and relative imports, so `dart run` (which triggers build hooks) is unnecessary

### Fixed

- **`hook/build.dart.jinja`** — local WASM builds now take priority over cached/downloaded files. Previously, if WASM files already existed in `web/pkg/`, the hook would skip updating them even when a newer local build was available in `rust/target/wasm32/`, causing stale content hash mismatches

### Removed

- **`pubspec.yaml.jinja`** — removed `flutter:` version constraint from `environment:` section. Pure Dart packages with native code don't need Flutter SDK constraint; `sdk:` is sufficient

## [2.3.2] - 2026-02-08

### Changed

- **`README.md.jinja`** — replaced vertical platform support table (one row per architecture) with compact horizontal layout showing platforms as columns with **Support** and **Arch** rows

## [2.3.1] - 2026-02-08

### Changed

- **`frb-patterns` Claude skill** — improved FRB patterns documentation with additional patterns from real-world usage:
  - Added anti-pattern example (`❌ WRONG`) to Constructor-Style API Pattern section showing incorrect top-level function vs correct `impl` block approach
  - Added "Adapter Pattern for Upstream Traits" subsection with generic `StoreAdapter` example for bridging DartFn callbacks to upstream trait implementations via `#[async_trait(?Send)]`
  - Added "No Threading on WASM" warning about `parking_lot::Mutex` and single-threaded web constraints

## [2.3.0] - 2026-02-08

### Changed

- **`macos_min_version` default**: `10.14` → `10.15`

## [2.2.3] - 2026-02-07

### Removed

- **`prepare-release` Claude command** — redundant; the `release-package` Claude skill already covers this functionality
- **`update-template` Claude command** — redundant; the `update-template` Claude skill already covers this functionality

### Changed

- **`CLAUDE.md.jinja`** — replaced "Claude Commands" section with "Claude Skills" section

## [2.2.2] - 2026-02-07

### Fixed

- **`platform_io.dart.jinja`** — added `coverage:ignore` annotations for untestable platform code (AOT mode library loading, `openLibraryFromPath`)

## [2.2.1] - 2026-02-07

### Fixed

- **`.gitignore.jinja`** / **`.pubignore.jinja`** — only ignore `.claude/settings.local.json` instead of the entire `.claude/*` directory (previously required `!.claude/skills/` exclusion pattern)

## [2.2.0] - 2026-02-07

### Added

- **`release-package` Claude skill** — detailed guide for preparing package releases (versioning rules, CHANGELOG format, pre-release validation, publishing flow)
- **`prepare-release` Claude command** — slash command (`/project:prepare-release`) to automate release preparation: update pubspec.yaml version, update CHANGELOG.md, run publish-dry-run
- **`update-template` Claude command** — slash command (`/project:update-template`) to automate copier template update: check for updates, run copier update, resolve conflicts, verify quality

## [2.1.1] - 2026-02-07

### Changed

- **`build-{{ package_name }}.yml.jinja`** — upstream library reference in release notes is now a bold markdown link to the GitHub release (e.g., `**Based on [libsignal v0.87.0](https://github.com/signalapp/libsignal/releases/tag/v0.87.0)**`)

## [2.1.0] - 2026-02-07

### Added

- **`ios_min_version` variable** (default: `13.0`) — iOS minimum deployment target, used in `ios/*.podspec`
- **`macos_min_version` variable** (default: `10.14`) — macOS minimum deployment target, used in `macos/*.podspec`

### Fixed

- **`build-{{ package_name }}.yml.jinja`** — fix `${VERSION}` not interpolated in release notes (heredoc used `<<'EOF'` which disables variable expansion, changed to `<<EOF`)
- **`build-{{ package_name }}.yml.jinja`** — add upstream native library version to release notes when `upstream_crates` is set (e.g., "Based on libsignal v0.87.0")

## [2.0.1] - 2026-02-07

### Changed

- **`template/{{ _copier_conf.answers_file }}.jinja`** - remove comment

## [2.0.0] - 2026-02-07

### Changed (BREAKING)

- **`upstream_crate` variable removed** — consolidated into `upstream_crates` (comma-separated). Use `upstream_crates=libsignal-protocol` for single crate, `upstream_crates=libsignal-protocol,libsignal-core` for multiple
- **`strip_version_prefix` boolean replaced with `version_tag_prefix` string** — default `"v"` strips `v` prefix from tags like `v1.0.0`. Set to custom prefix (e.g. `release-v`) for repos with non-standard tag schemes (like `release-v1.0.0`)

### Changed

- All template conditionals simplified from `upstream_crate or upstream_crates` to just `upstream_crates`
- `check_updates.dart.jinja` — version normalization now uses configurable `_tagPrefix` constant with fallback to `v`/`V`
- `common.dart.jinja` — removed separate `getUpstreamVersion()` for single crate; unified to use `upstream_crates` loop
- `Cargo.toml.jinja` — unified dependency generation to single loop for `upstream_crates`
- Updated all documentation (README, CLAUDE.md, CONTRIBUTING.md) and skills to reflect new variable names
- `copier.yml` — simplified `upstream_version` visibility condition, consolidated post-generation message

### Added

- **`template/{{ _copier_conf.answers_file }}.jinja`** — Copier answers file template for generated projects (enables `copier update` to track template version)

## [1.9.0] - 2026-02-06

### Fixed

- **`test.yml.jinja`** — fix `workflow_run` trigger referencing wrong workflow name (`"Build {{ package_name }} Native Libraries"` → `"Build {{ package_name }} FRB Libraries"`), causing tests to never auto-trigger after build completion
- **`build-{{ package_name }}.yml.jinja`** — fix env var name in check-release step (`GH_TOKEN` → `GITHUB_TOKEN`). The Dart script reads `GITHUB_TOKEN`, not `GH_TOKEN` (which is for the `gh` CLI)
- **`example_pubspec.yaml.jinja`** — upgrade `flutter_lints` from `^5.0.0` to `^6.0.0`
- **`.pubignore.jinja`** — include Rust source files in published package (only exclude `rust/target/` build artifacts, not entire `rust/` directory); add trailing newline

## [1.8.0] - 2026-02-06

### Changed

- **`CLAUDE.md` template** — merged "Quick Reference" table into "Available Makefile Commands" section to eliminate duplication. Added missing commands: `setup-protoc`, `setup-web`, `setup-android`, `doc`, `rust-update`, `check-new-*-version`, `check-template-updates`, `update-changelog` (with Jinja2 conditionals for optional features)

### Fixed

- **`analysis_options.yaml` template** — added `example/**` and `example_cli/**` to analyzer excludes. These are separate packages with their own `analysis_options.yaml` and should not be analyzed as part of the main package. Without this exclude, `flutter analyze` fails in CI when `example_cli/` dependencies are not resolved

### Added

- **`check_updates.dart` script** — now also updates `upstream_version` in `.copier-answers.yml` when updating upstream version (step 4 in `updateVersionFiles()`). The check-updates workflow PR body shows `.copier-answers.yml` status alongside other updated files

## [1.7.2] - 2026-02-05

### Changed

- **`update-template` Claude skill** — document manual `_commit` update in `.copier-answers.yml` when copier fails to update it (merge conflicts or no file changes)

## [1.7.1] - 2026-02-05

### Added

- **`update-template` Claude skill** — step-by-step guide for reviewing automated PRs, running `copier update`, resolving conflicts, and quality checks
  - Documents `--defaults` flag for non-interactive `copier update` (required for Claude Code)

## [1.7.0] - 2026-02-05

### Added

- **`check-template-updates.yml` workflow** — daily CI check for new copier template versions with automated notification PR containing version comparison, changelog, and update instructions
- **`check_template_updates.dart` script** — checks `.copier-answers.yml` against latest template release, supports `--json`, `--ci-output`, `--version`, `--force` flags
- **`make check-template-updates` target** — Makefile command for template version checking
- **`update-template` Claude skill** — step-by-step guide for reviewing automated PRs, running `copier update`, resolving conflicts, and quality checks
  - Documents `--defaults` flag for non-interactive `copier update` (required for Claude Code)

### Changed

- Renamed Claude skill `ffi-patterns` → `frb-patterns` to match Flutter Rust Bridge architecture
- Removed unused `GITHUB_TOKEN` from `check_updates.dart` (not needed for public GitHub API with 1 req/day)

## [1.6.0] - 2026-02-05

### Added

- **`get_android_min_sdk.dart` script** — reads `minSdk` from `android/build.gradle` dynamically
- **Auto-format on generation** — added `dart format .` as post-generation task to ensure all generated Dart code is properly formatted

### Changed

- **`make build-android` reads minSdk dynamically** — no longer hardcoded, reads from `android/build.gradle` via script (single source of truth)
- **Simplified example app naming:**
  - Flutter example: `--project-name` changed from `{{ package_name }}_example` to `example`
  - CLI example: main file changed from `bin/{{ package_name }}_cli.dart` to `bin/main.dart`
- **Updated `update-{{ package_name }}` skill documentation:**
  - Updated commands to use `make check-new-{{ package_name }}-version` instead of `make check`
  - Simplified manual update process documentation
  - Removed SKILL.md from auto-updated files list (no longer contains version-specific examples)
- **Improved Jinja2 whitespace handling** — using `{%-` / `-%}` syntax in workflow files to prevent extra blank lines
- **Removed auto-update of SKILL.md** — `check_updates.dart` no longer updates `.claude/skills/update-{{ package_name }}/SKILL.md`

### Removed

- **Redundant comment in `build.gradle.jinja`** — removed "Native libraries are in src/main/jniLibs/" comment

## [1.5.0] - 2026-02-04

### Changed

- **Renamed `make update` → `make rust-update`** — clearer naming indicating this command updates Rust dependencies (Cargo.lock)
- **Synchronized `hook/build.dart.jinja` with reference project:**
  - Added section separator comments (`// ===`) for Web Build Support, Native Build Support, Download Support
  - Simplified `_AssetInfo` class — removed `linkMode` field (always `DynamicLoadingBundled()`)
  - Simplified `_resolveAssetInfo` — uses new `_getPlatformArchName` helper
  - Replaced `_linuxArchName`, `_macOSArchName`, `_iOSTargetName` with unified `_archName` and `_getPlatformArchName`
  - Added extended documentation header with "How it works" and "For development" sections

## [1.4.0] - 2026-02-04

### Fixed

- **Native library loading for pure Dart CLI applications:**
  - **JIT mode** (`dart run`): loads from `.dart_tool/lib/`
  - **AOT mode** (`dart build cli`): loads from `bundle/lib/` relative to executable
  - Enables standalone executables to be distributed and run from any location

### Security

- **Remove CWD-based library search** to prevent library hijacking attacks:
  - Previously searched `rust/target/release/` in current working directory
  - Attacker could place malicious library in CWD to hijack application
  - Now only searches trusted paths: build hook locations and executable-relative paths

### Changed

- **Simplified library loading** — removed `findLibraryPath` and `findPackageRoot` functions from `platform_io.dart`

## [1.3.6] - 2026-02-03

### Added

- **"Review Automated PR" section in update skill** — new detailed checklist with 10 steps for reviewing automated dependency update PRs, including:
  - Analyzing release notes for breaking changes
  - Fixing Rust compilation errors
  - Bumping FRB crate version
  - Syncing Cargo.lock

### Changed

- **Improved check-updates workflow PR instructions:**
  - Added "Bump `rust/Cargo.toml` version" step to Before Merge section
  - Added "Run `make rust-check`" step to sync Cargo.lock
  - Simplified After Merge section (removed redundant rust/Cargo.toml mention)
- **AI changelog now generates two Highlights lines:**
  - One for native library version (e.g., `**testlib v1.0.0** — description`)
  - One for FRB crate version (e.g., `**test_sync_frb v1.0.2** — Rust FFI bindings`)
  - Added `_readFrbVersion()` function to read crate version from `rust/Cargo.toml`

## [1.3.5] - 2026-02-03

### Changed

- **`create-project` skill improvements:**
  - Added complete post-generation workflow with numbered steps
  - Added warning that `make build` is required before `make test`
  - Added "Quality Verification" section with all quality checks (`make analyze`, `make test`, `make format-check`, `make rust-check`, `make rust-audit`, `make publish-dry-run`)
  - Added "Platform-Specific Builds" section

## [1.3.4] - 2026-02-03

### Added

- **`create-project` Claude skill** — new skill for generating projects from the template, supports both local files (`--vcs-ref HEAD`) and GitHub with specific version (`--vcs-ref v1.0.0`)

## [1.3.3] - 2026-02-03

### Fixed

- **Dart formatting compliance** — all generated `.dart` files now pass `dart format --set-exit-if-changed`:
  - Added blank line after shebang (`#!/usr/bin/env dart`) in scripts
  - Fixed Jinja2 whitespace handling using `{%-` / `-%}` syntax to prevent extra blank lines
  - Corrected indentation in long expressions (Process.run, Map literals, replaceAll, etc.)
  - Removed extra blank lines in test files and conditional blocks

## [1.3.2] - 2026-02-03

### Added

- **get_flutter_version.dart script** — new cross-platform script to read Flutter version from `.fvmrc`

### Changed

- **FVM setup reads version from .fvmrc** — Makefile now uses `dart scripts/get_flutter_version.dart` instead of hardcoded version, making it easier to update Flutter version in one place
- **Git repository initialized on project creation** — added `git init` task to copier post-generation
- **example_cli dependencies** — added `dart pub get` task after pubspec.yaml replacement to ensure dependencies are resolved

### Fixed

- **Unused import in widget test** — removed `package:flutter/material.dart` import from `example_widget_test.dart.jinja`

## [1.3.1] - 2026-02-03

### Added

- **Widget test for Flutter example app** — new `example_widget_test.dart.jinja` with basic app tests

### Changed

- **analysis_options.yaml improvements:**
  - Added exclude for FRB-generated files (`lib/src/rust/**`)
  - Added exclude for build scripts (`hook/**`, `scripts/**`)
- **FVM setup command** — changed `fvm install` to `fvm use --force` for more reliable setup
- **Example apps cleanup:**
  - Flutter example now uses custom widget test instead of default
  - CLI example removes default `test/` and `lib/` directories
- **Code style improvements across templates:**
  - Class fields moved after constructors (Dart style guide)
  - Cascade notation (`..writeln`) for StringBuffer operations
  - Tear-off syntax for callbacks (`tearDown(cleanup)`)
  - Better JSON type casting in platform_io.dart and update_changelog.dart
- **Script documentation** — improved doc comments with proper formatting and `library;` directives
- **Unused import warnings** — added `// ignore: unused_import` in example apps

### Fixed

- **Lint compliance** — added appropriate `ignore_for_file` directives:
  - `avoid_dynamic_calls` in platform_io.dart
  - `avoid_classes_with_only_static_members` in common.dart
- **Test file improvements:**
  - Fixed import order (test package first)
  - Simplified test assertions using `returnsNormally`
  - Removed redundant version tests

## [1.3.0] - 2026-02-02

### Added

- **New template variables for Android:**
  - `android_gradle_version` (default: `8.11.1`) — Android Gradle plugin version
  - `android_java_version` (default: `17`, choices: `11`, `17`, `21`) — Java version for Android compilation
- **Example app improvements:**
  - Added `.gitignore` files for both Flutter and CLI examples
  - Added `analysis_options.yaml` for CLI example (disables `avoid_print` lint)
  - Added iOS/macOS xcconfig files for proper CocoaPods configuration
  - Added `--org` parameter when creating Flutter example app
- **Pre-commit hook now runs `make rust-check`** — validates Rust code before commits
- **Test workflow triggers on `rust/**` changes** — ensures tests run when Rust code is modified
- **Coverage badge now uses color range** — badge color reflects coverage percentage (50-90% range)

### Changed

- **Android defaults updated:**
  - `android_min_sdk`: `21` → `24` (Android 7.0+)
  - `android_compile_sdk`: `34` → `36`
- **Rust Cargo.lock is now committed** — removed from `.gitignore` for reproducible builds
- **Simplified Makefile:**
  - Removed `make combine` target (unused)
  - Removed `make regen` alias (use `make codegen` directly)
  - Removed `.skip_{{ package_name }}_hook` workarounds from build commands
  - Added informative build completion messages
- **Improved pre-commit hook** — added colored output and Rust checking
- **Improved check-updates workflow:**
  - Simplified status tracking with boolean `success` outputs
  - Cleaner PR description format
- **Improved test-reusable workflow:**
  - Simplified Rust setup (removed explicit target specification)
  - Removed badge secrets validation step
- **Cleaned up Jinja2 whitespace** — using `{%-` syntax for cleaner output in multiple templates
- **Updated .pubignore** — added `docs/`, `rust/target/`, generated plugin files

### Fixed

- **LICENSE.jinja** — added complete AGPL-3.0 license text (was truncated)
- **analysis_options.yaml** — removed incorrect exclude for `lib/src/bindings/**`

### Removed

- **security-review Claude skill** — removed from generated projects
- **combine_artifacts.dart script** — no longer needed

## [1.2.0] - 2026-02-01

### Changed

- **BREAKING: Flat template structure** - Template no longer creates a `{{ package_name }}/` subdirectory
  - Files are now generated directly in the destination directory
  - Enables proper `copier update` support for existing projects
  - New usage: `mkdir my_package && cd my_package && copier copy <template> .`
- Updated `_tasks` working directories to use `{{ _copier_conf.dst_path }}` directly
- Updated post-copy message with new workflow instructions

### Fixed

- `copier update` now works correctly for existing projects

## [1.1.0] - 2026-02-01

### Added

- **Multiple upstream crates support**: New `upstream_crates` variable for projects that depend on multiple crates from the same git repository (e.g., `libsignal-protocol,libsignal-core,signal-crypto`)
- Updated `rust/Cargo.toml.jinja` to generate dependencies for all specified crates
- Updated `scripts/src/common.dart.jinja` with `getUpstreamVersion()` function supporting multiple crates
- Updated `scripts/src/check_updates.dart.jinja` to update all upstream crate versions simultaneously
- Updated `scripts/check_exists_frb_release.dart.jinja` for multiple crates support
- Updated `.github/workflows/build-*.yml.jinja` for multiple crates support

### Changed

- `upstream_crates` and `upstream_crate` are now mutually exclusive - use one or the other
- Improved documentation for upstream crate configuration in `copier.yml`

## [1.0.0] - 2026-02-01

### Added

#### Core Features
- Copier template for Flutter Rust Bridge (FRB) projects
- Flutter Rust Bridge integration for type-safe Dart-Rust bindings
- Dart Native Assets build hook for automatic library download
- SHA256 checksum verification for supply chain security
- Retry logic for network operations with exponential backoff

#### Cross-Platform Support
- Android (arm64-v8a, armeabi-v7a, x86_64)
- iOS (arm64 device, arm64/x86_64 simulator)
- macOS (arm64, x86_64)
- Linux (x64, arm64)
- Windows (x64)
- Web/WASM (optional via `enable_web`)

#### GitHub Actions Workflows
- `test.yml` / `test-reusable.yml` - Multi-platform testing with coverage
- `build-<package>.yml` - Native library builds for all platforms
- `publish.yml` - pub.dev publishing with OIDC + GitHub Release creation
- `check-<package>-updates.yml` - Automated upstream version checking
- Rust security audit via `cargo-audit`
- Coverage badge support via GitHub Gist

#### Template Variables
- Required: `package_name`, `description`, `native_library_name`, `github_repo`, `native_repo`
- Rust config: `crate_name`, `rust_edition`, `rust_version`, `frb_version`
- Upstream crate: `upstream_crate`, `upstream_version`, `strip_version_prefix`
- Flutter/Dart: `flutter_version`, `dart_sdk_version`, `flutter_sdk_version`
- Android: `android_min_sdk`, `android_compile_sdk`, `android_ndk_version`
- Feature flags: `enable_web`, `enable_claude`
- Metadata: `license`, `topics`

#### Developer Experience
- FVM (Flutter Version Manager) integration with Windows support
- Makefile with common commands (setup, codegen, build, test, coverage)
- Claude Code skills for generated projects (optional via `enable_claude`)
- Comprehensive documentation templates (README, CONTRIBUTING, SECURITY, CHANGELOG, CLAUDE.md)
- Automatic example app creation (Flutter GUI + CLI)
- Variable validators with helpful error messages
- Jinja2 templating with case conversion filters (jinja2-strcase)

#### Generated Project Features
- Pre-configured `analysis_options.yaml` with recommended lints
- GitHub Actions setup instructions in README
- Coverage badge setup guide
- Security policy template
- Git hooks for pre-commit checks

[2.3.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.3.1...v2.3.2
[2.3.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.3...v2.3.0
[2.2.3]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.2...v2.2.3
[2.2.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.1...v2.2.2
[2.2.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.9.0...v2.0.0
[1.9.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.2...v1.8.0
[1.7.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.6...v1.4.0
[1.3.6]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/releases/tag/v1.0.0
