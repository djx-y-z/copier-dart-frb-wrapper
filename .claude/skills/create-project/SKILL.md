---
name: create-project
description: Generate a new Dart/Flutter FRB wrapper project from this Copier template. Use when user wants to create a new project from the template, either from local files or from GitHub with a specific version.
---

# Create Project from Template

Generate a new Dart/Flutter package with Flutter Rust Bridge support using the copier-dart-frb-wrapper template.

## Quick Start

### From Local Template (Development)

Use this when testing template changes or working locally.

**Option 1: Run from template directory**

```bash
# First, cd to the template directory
cd /path/to/copier-dart-frb-wrapper

# Then run copier with "." as source
copier copy . /path/to/destination \
  --trust \
  --vcs-ref HEAD \
  --data package_name=my_package \
  --data description="My package description" \
  --data native_library_name=mylib \
  --data github_repo=username/my_package \
  --data native_repo=original/mylib
```

**Option 2: Specify full path to template**

```bash
# Run from anywhere, specifying absolute path to template
copier copy /path/to/copier-dart-frb-wrapper /path/to/destination \
  --trust \
  --vcs-ref HEAD \
  --data package_name=my_package \
  --data description="My package description" \
  --data native_library_name=mylib \
  --data github_repo=username/my_package \
  --data native_repo=original/mylib
```

**Note:** `--vcs-ref HEAD` is required for local git repositories to use current uncommitted changes. Without it, Copier uses the latest git tag.

### From GitHub (Production)

Use this for creating real projects from a released version:

```bash
# Latest version
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper /path/to/destination \
  --trust \
  --data package_name=my_package \
  --data description="My package description" \
  --data native_library_name=mylib \
  --data github_repo=username/my_package \
  --data native_repo=original/mylib

# Specific version
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper /path/to/destination \
  --trust \
  --vcs-ref v1.0.0 \
  --data package_name=my_package \
  --data description="My package description" \
  --data native_library_name=mylib \
  --data github_repo=username/my_package \
  --data native_repo=original/mylib
```

## Command Flags

| Flag | Description |
|------|-------------|
| `--trust` | Skip safety prompts (required for post-generation tasks) |
| `--vcs-ref <ref>` | Git reference: tag (`v1.0.0`), branch (`main`), or `HEAD` |
| `--defaults` | Use default values for unspecified optional variables |
| `--data key=value` | Set template variable value |
| `--pretend` | Dry run - show what would be generated without creating files |
| `--force` | Overwrite existing destination directory |

## Template Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `package_name` | Dart package name (lowercase, underscores) | `signal_dart` |
| `description` | Package description for pubspec.yaml | `"Dart bindings for Signal"` |
| `native_library_name` | Name of the native library being wrapped | `signal` |
| `github_repo` | GitHub repository for the wrapper package | `user/signal_dart` |
| `native_repo` | GitHub repository of the native library | `signalapp/libsignal` |

### Optional Variables (with Defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `crate_name` | `<package_name>_frb` | Rust crate name |
| `rust_edition` | `2024` | Rust edition (2021 or 2024) |
| `rust_version` | `1.88` | Minimum Rust version (MSRV) |
| `frb_version` | `^2.11.1` | Flutter Rust Bridge version |
| `enable_web` | `true` | Enable Web/WASM support |
| `enable_claude` | `true` | Include Claude Code configuration files |
| `upstream_crate` | `""` | Upstream Rust crate to wrap (optional) |
| `upstream_version` | `""` | Version of upstream crate |
| `strip_version_prefix` | `false` | Strip 'v' prefix from version tags |
| `flutter_version` | `3.38.4` | Flutter version for FVM |
| `dart_sdk_version` | `^3.10.0` | Dart SDK version constraint |
| `flutter_sdk_version` | `>=3.38.0` | Flutter SDK version constraint |
| `android_min_sdk` | `21` | Android minimum SDK version |
| `android_compile_sdk` | `34` | Android compile SDK version |
| `android_ndk_version` | `26.3.11579264` | Android NDK version |
| `license` | `MIT` | Package license (MIT, Apache-2.0, BSD-3-Clause, etc.) |
| `topics` | `ffi,native,rust` | pub.dev topics (comma-separated) |

## Complete Examples

### Basic Project (All Defaults)

```bash
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper ~/projects/my_wrapper \
  --trust \
  --defaults \
  --data package_name=my_wrapper \
  --data description="Dart wrapper for MyLib" \
  --data native_library_name=mylib \
  --data github_repo=myuser/my_wrapper \
  --data native_repo=original/mylib
```

### Project Without Web Support

```bash
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper ~/projects/native_only \
  --trust \
  --defaults \
  --data package_name=native_only \
  --data description="Native-only wrapper" \
  --data native_library_name=nativelib \
  --data github_repo=myuser/native_only \
  --data native_repo=original/nativelib \
  --data enable_web=false
```

### Project Wrapping Upstream Crate

When wrapping an existing Rust crate from crates.io:

```bash
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper ~/projects/signal_dart \
  --trust \
  --defaults \
  --data package_name=signal_dart \
  --data description="Dart bindings for Signal Protocol" \
  --data native_library_name=signal \
  --data github_repo=myuser/signal_dart \
  --data native_repo=signalapp/libsignal \
  --data upstream_crate=libsignal-protocol \
  --data upstream_version=v0.86.0 \
  --data strip_version_prefix=true
```

### Full Custom Configuration

```bash
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper ~/projects/custom_pkg \
  --trust \
  --vcs-ref v1.2.0 \
  --data package_name=custom_pkg \
  --data description="Custom package with full configuration" \
  --data native_library_name=customlib \
  --data github_repo=myorg/custom_pkg \
  --data native_repo=original/customlib \
  --data crate_name=custom_bridge \
  --data rust_edition=2024 \
  --data rust_version=1.85 \
  --data frb_version="^2.12.0" \
  --data enable_web=true \
  --data enable_claude=true \
  --data flutter_version=3.38.4 \
  --data dart_sdk_version="^3.10.0" \
  --data android_min_sdk=24 \
  --data android_compile_sdk=35 \
  --data license=Apache-2.0 \
  --data topics="ffi,native,rust,bindings"
```

## Source Selection Guide

| Source | When to Use | Command |
|--------|-------------|---------|
| Local (`.`) | Testing template changes | `copier copy . dest --vcs-ref HEAD` |
| GitHub latest | Production projects | `copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper dest` |
| GitHub tagged | Reproducible builds | `copier copy ... --vcs-ref v1.0.0` |
| GitHub branch | Testing unreleased features | `copier copy ... --vcs-ref feature-branch` |

## Post-Generation Steps

After project generation, the template runs these tasks automatically:

1. `git init` - Initialize git repository
2. Create `example_cli/` - Dart CLI example app
3. Create `example/` - Flutter example app

Then manually:

```bash
cd /path/to/destination/package_name

# Install dependencies
make setup

# Generate Flutter Rust Bridge code
make codegen

# Build for your platform
make build-macos  # or build-linux, build-windows, build-android, build-ios
```

## Updating Existing Projects

To update a project created from this template:

```bash
cd /path/to/existing/project

# Update to latest version
copier update

# Update to specific version
copier update --vcs-ref v1.2.0

# Preview changes without applying
copier update --pretend
```

## Listing Available Versions

```bash
# List all tags (versions)
git ls-remote --tags https://github.com/djx-y-z/copier-dart-frb-wrapper

# Or using GitHub CLI
gh release list --repo djx-y-z/copier-dart-frb-wrapper
```

## Troubleshooting

### "No git tags found" Warning

This is normal when:
- Using `--vcs-ref HEAD` for local development
- The repository has no releases yet

### "DirtyLocalWarning"

Appears when using `--vcs-ref HEAD` with uncommitted changes. This is expected during development.

### Task Execution Fails

Ensure you have the required tools installed:
- `flutter` (via FVM or directly)
- `git`

### Permission Denied

Use `--trust` flag to allow post-generation tasks to run.

### Destination Already Exists

Use `--force` to overwrite, or choose a different destination path.
