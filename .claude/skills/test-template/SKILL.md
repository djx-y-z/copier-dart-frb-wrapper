---
name: test-template
description: Test the Copier template with different configurations. Use when user wants to test template changes, verify generation works, or check specific variable combinations.
---

# Test Copier Template

Help with testing the copier-dart-frb-wrapper template with different configurations.

## Quick Test Commands

```bash
# Basic FRB project (web enabled by default)
rm -rf /tmp/test_basic && copier copy . /tmp/test_basic \
  --trust --vcs-ref HEAD \
  --data package_name=test_basic \
  --data description="Test FRB wrapper" \
  --data native_library_name=testlib \
  --data github_repo=user/test_basic \
  --data native_repo=original/testlib

# Test without Web/WASM support
rm -rf /tmp/test_no_web && copier copy . /tmp/test_no_web \
  --trust --vcs-ref HEAD \
  --data package_name=test_no_web \
  --data description="Test without web" \
  --data native_library_name=testlib \
  --data github_repo=user/test_no_web \
  --data native_repo=original/testlib \
  --data enable_web=false

# Test without Claude Code files
rm -rf /tmp/test_no_claude && copier copy . /tmp/test_no_claude \
  --trust --vcs-ref HEAD \
  --data package_name=test_no_claude \
  --data description="Test without Claude" \
  --data native_library_name=testlib \
  --data github_repo=user/test_no_claude \
  --data native_repo=original/testlib \
  --data enable_claude=false

# Test with upstream crate
rm -rf /tmp/test_upstream && copier copy . /tmp/test_upstream \
  --trust --vcs-ref HEAD \
  --data package_name=test_signal \
  --data description="Test Signal wrapper" \
  --data native_library_name=signal \
  --data github_repo=user/test_signal \
  --data native_repo=signalapp/libsignal \
  --data upstream_crates=libsignal-protocol \
  --data upstream_version=v0.86.0

# Full configuration (upstream + web)
rm -rf /tmp/test_full && copier copy . /tmp/test_full \
  --trust --vcs-ref HEAD \
  --data package_name=test_full \
  --data description="Full test wrapper" \
  --data native_library_name=signal \
  --data github_repo=user/test_full \
  --data native_repo=signalapp/libsignal \
  --data upstream_crates=libsignal-protocol \
  --data upstream_version=v0.86.0 \
  --data enable_web=true
```

## Important Flags

| Flag | Description |
|------|-------------|
| `--trust` | Skip safety prompts (needed for tasks) |
| `--vcs-ref HEAD` | Use current uncommitted changes |
| `--defaults` | Use default values for unspecified variables |
| `--data key=value` | Set template variable |

## Template Variables Reference

### Required
- `package_name` - Dart package name (lowercase, underscores)
- `description` - Package description
- `native_library_name` - Native library name
- `github_repo` - GitHub repo of wrapper (user/repo)
- `native_repo` - GitHub repo of native library (user/repo)

### Optional (with defaults)
- `crate_name` - Rust crate name (default: `<package_name>_frb`)
- `rust_edition` - "2021" or "2024" (default: "2024")
- `rust_version` - MSRV (default: "1.88")
- `frb_version` - FRB version (default: "^2.11.1")
- `enable_web` - Web/WASM support (default: true)
- `enable_claude` - Claude Code files (default: true)
- `upstream_crates` - Upstream Rust crates, comma-separated (default: "")
- `upstream_version` - Upstream version (default: "")
- `version_tag_prefix` - Tag prefix for version normalization (default: "v")
- `flutter_version` - FVM Flutter version (default: "3.38.4")
- `dart_sdk_version` - Dart SDK constraint (default: "^3.10.0")
- `flutter_sdk_version` - Flutter SDK constraint (default: ">=3.38.0")
- `ios_min_version` - iOS minimum deployment target (default: "13.0")
- `macos_min_version` - macOS minimum deployment target (default: "10.14")
- `android_min_sdk` - Android min SDK (default: "21")
- `android_compile_sdk` - Android compile SDK (default: "34")
- `license` - MIT, Apache-2.0, etc. (default: "MIT")
- `topics` - pub.dev topics (default: "ffi,native,rust")

## Verification Checklist

After generation, check:

1. **Files exist:**
   ```bash
   ls /tmp/test_basic/test_basic/
   # Should have: lib/, rust/, hook/, scripts/, .github/, Makefile, pubspec.yaml, etc.
   ```

2. **Conditional files (enable_web=false):**
   ```bash
   # These should NOT exist when enable_web=false:
   ls /tmp/test_no_web/test_no_web/rust/.cargo/config.toml  # No WASM config
   grep "build-web" /tmp/test_no_web/test_no_web/Makefile   # No build-web target
   ```

3. **Conditional files (enable_claude=false):**
   ```bash
   # These should NOT exist when enable_claude=false:
   ls /tmp/test_no_claude/test_no_claude/CLAUDE.md      # Should not exist
   ls /tmp/test_no_claude/test_no_claude/.claude/       # Should not exist
   ```

4. **Upstream crate in Cargo.toml:**
   ```bash
   grep "libsignal-protocol" /tmp/test_upstream/test_signal/rust/Cargo.toml
   ```

5. **Variable substitution:**
   ```bash
   grep "test_basic" /tmp/test_basic/test_basic/pubspec.yaml
   grep "test_basic_frb" /tmp/test_basic/test_basic/rust/Cargo.toml
   ```

## Cleanup

```bash
rm -rf /tmp/test_basic /tmp/test_no_web /tmp/test_no_claude /tmp/test_upstream /tmp/test_full
```

## Troubleshooting

### "DirtyLocalWarning"
This is normal when testing uncommitted changes with `--vcs-ref HEAD`.

### "No git tags found"
Normal for development - template uses HEAD as version.

### Task fails during generation
Check the copier output for Jinja2 syntax errors in template files.
