# copier-dart-frb-wrapper - Claude Code Configuration

## Overview

This is a Copier template for generating Dart/Flutter packages that wrap native Rust libraries using Flutter Rust Bridge (FRB) with full CI/CD support.

## Claude Skills

This project includes Claude Skills to help with common tasks:

| Skill | Description |
|-------|-------------|
| `create-project` | Generate new project from template (local or GitHub) |
| `test-template` | Test template with different configurations |
| `add-variable` | Add new variables to copier.yml |
| `jinja-syntax` | Jinja2 syntax reference |
| `release-template` | Create new template releases |

## Project Structure

```
copier-dart-frb-wrapper/
├── copier.yml              # Template configuration and variables
├── README.md               # Template documentation
├── CONTRIBUTING.md         # Contribution guidelines
├── CHANGELOG.md            # Version history
├── CLAUDE.md               # This file
├── LICENSE                 # MIT license
├── .claude/skills/         # Claude Code skills for this project
└── template/
    └── {{ package_name }}/ # Template directory (Jinja2 syntax)
        ├── lib/            # Dart library code
        ├── rust/           # Rust crate with FRB
        ├── scripts/        # Utility scripts
        ├── hook/           # Build hook for native library download
        ├── .github/        # GitHub Actions workflows
        ├── .claude/skills/ # Claude Code skills for generated project
        └── ...
```

## Template Variables

### Required

| Variable | Type | Description |
|----------|------|-------------|
| `package_name` | string | Dart package name (lowercase, underscores) |
| `description` | string | Package description |
| `native_library_name` | string | Name of native library |
| `github_repo` | string | GitHub repository of wrapper package |
| `native_repo` | string | GitHub repository of native library |

### Optional

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `crate_name` | string | `<package_name>_frb` | Rust crate name |
| `rust_edition` | string | `2024` | Rust edition (2021 or 2024) |
| `rust_version` | string | `1.88` | Minimum Rust version (MSRV) |
| `frb_version` | string | `^2.11.1` | Flutter Rust Bridge version |
| `enable_web` | boolean | `true` | Enable Web/WASM support |
| `enable_claude` | boolean | `true` | Include Claude Code files |
| `upstream_crates` | string | `` | Upstream Rust crates (comma-separated) |
| `upstream_version` | string | `` | Version of upstream crate |
| `version_tag_prefix` | string | `v` | Tag prefix for version normalization |
| `flutter_version` | string | `3.38.4` | Flutter version for FVM |
| `dart_sdk_version` | string | `^3.10.0` | Dart SDK version constraint |
| `flutter_sdk_version` | string | `>=3.38.0` | Flutter SDK version constraint |
| `android_min_sdk` | string | `21` | Android minimum SDK |
| `android_compile_sdk` | string | `34` | Android compile SDK |
| `android_ndk_version` | string | `26.3.11579264` | Android NDK version for Rust |
| `license` | enum | `MIT` | Package license |
| `topics` | string | `ffi,native,rust` | pub.dev topics (comma-separated) |

## Template Syntax

This template uses Jinja2 with [jinja2-strcase](https://pypi.org/project/jinja2-strcase/) extension:

```jinja2
{{ package_name }}                    # Variable substitution
{{ package_name | to_camel }}         # PascalCase: MyPackage
{{ package_name | to_lower_camel }}   # camelCase: myPackage
{{ package_name | to_snake }}         # snake_case: my_package
{{ package_name | to_screaming_snake }} # CONSTANT_CASE: MY_PACKAGE
{% if enable_web %}...{% endif %}     # Conditional for web support
{% if upstream_crates %}...{% endif %} # Conditional for upstream crates
```

## Testing the Template

### Basic FRB project (web enabled by default)
```bash
copier copy . /tmp/test_frb \
  --trust \
  --defaults \
  --data package_name=test_frb \
  --data description="Test FRB wrapper" \
  --data native_library_name=testlib \
  --data github_repo=user/test_frb \
  --data native_repo=original/testlib
```

### Without Web/WASM support
```bash
copier copy . /tmp/test_no_web \
  --trust \
  --defaults \
  --data package_name=test_no_web \
  --data description="Test without web" \
  --data native_library_name=testlib \
  --data github_repo=user/test_no_web \
  --data native_repo=original/testlib \
  --data enable_web=false
```

### With upstream crate
```bash
copier copy . /tmp/test_upstream \
  --trust \
  --defaults \
  --data package_name=test_upstream \
  --data description="Test upstream wrapper" \
  --data native_library_name=signal \
  --data github_repo=user/test_upstream \
  --data native_repo=signalapp/libsignal \
  --data upstream_crates=libsignal \
  --data upstream_version=v0.86.0
```

## Files with Conditional Content

These files have conditional blocks based on `enable_web` or `upstream_crates`:

- `rust/Cargo.toml.jinja` - upstream crate dependencies, web features
- `rust/.cargo/config.toml.jinja` - WASM configuration
- `pubspec.yaml.jinja` - web platform
- `Makefile.jinja` - build-web, setup-web targets
- `.github/workflows/build-{{ package_name }}.yml.jinja` - WASM build job
- `hook/build.dart.jinja` - WASM download support
- `README.md.jinja` - web platform mention
- `CLAUDE.md.jinja` - web commands

## Versioning

Copier uses **git tags** for template versioning:

```bash
# Create a new version
git tag v1.0.0
git push origin v1.0.0

# Users can specify version
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper project --vcs-ref v1.0.0

# Update existing project to new version
cd project && copier update
```

**Important:**
- Without tags, Copier uses HEAD (shows "No git tags found" warning)
- Use semantic versioning: v1.0.0, v1.1.0, v2.0.0
- `copier update` detects new versions from tags

## Copier Configuration

Key settings in `copier.yml`:

- `_min_copier_version: "9.0.0"` - Minimum Copier version
- `_subdirectory: template` - Template files location
- `_templates_suffix: .jinja` - Only process `.jinja` files
- `_jinja_extensions` - Case conversion filters (jinja2-strcase)
- `_tasks` - Post-generation commands (create example apps)
- `_exclude` - Files to exclude from generation

## Development

### Requirements

```bash
pip install copier jinja2-strcase
# or
brew install copier && pip install jinja2-strcase
```

### Quick Test

```bash
# Test with defaults
copier copy . /tmp/test --trust --defaults \
  --data package_name=test \
  --data description=Test \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib

# Check generated files
ls -la /tmp/test/test/
```

### Updating the Template

1. Edit files in `template/{{ package_name }}/`
2. Use `.jinja` suffix for files with Jinja2 content
3. Test with different variable combinations (`enable_web`, `upstream_crates`)
4. Update `copier.yml` if adding new variables
5. Update documentation (README.md, CLAUDE.md, CONTRIBUTING.md)
6. Add changes to CHANGELOG.md under `[Unreleased]`
