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

[Unreleased]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/releases/tag/v1.0.0
