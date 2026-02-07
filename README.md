# copier-dart-frb-wrapper

[![GitHub release](https://img.shields.io/github/v/release/djx-y-z/copier-dart-frb-wrapper)](https://github.com/djx-y-z/copier-dart-frb-wrapper/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Copier template for generating Flutter/Dart packages that wrap native Rust libraries using Flutter Rust Bridge (FRB) with full CI/CD support.

## Features

- Cross-platform native library support (Android, iOS, macOS, Linux, Windows, Web/WASM)
- Flutter Rust Bridge integration for type-safe bindings
- Automatic native library download via build hooks
- SHA256 checksum verification for supply chain security
- GitHub Actions workflows for CI/CD

## Requirements

- Python 3.8+
- [Copier](https://copier.readthedocs.io/) 9.0+
- [jinja2-strcase](https://pypi.org/project/jinja2-strcase/) (for case conversion filters)

### Installation

**All platforms (pip):**
```bash
pip install copier jinja2-strcase
```

**macOS (Homebrew + pip):**
```bash
brew install copier && pip install jinja2-strcase
```

**Linux (pipx - recommended for isolation):**
```bash
pipx install copier
pipx inject copier jinja2-strcase
```

**Windows (pip or pipx):**
```powershell
pip install copier jinja2-strcase
# or with pipx
pipx install copier
pipx inject copier jinja2-strcase
```

## Usage

### Create a new project

```bash
mkdir my_package && cd my_package
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper .
```

### Update an existing project

```bash
cd my_package
copier update
```

### Example with all parameters

```bash
mkdir my_signal_lib && cd my_signal_lib
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper . \
  --data package_name=my_signal_lib \
  --data description="Dart bindings for Signal Protocol" \
  --data native_library_name=signal \
  --data github_repo=user/my_signal_lib \
  --data native_repo=signalapp/libsignal \
  --data crate_name=my_signal_lib_frb \
  --data rust_edition=2024 \
  --data rust_version=1.88 \
  --data frb_version="^2.11.1" \
  --data upstream_crates=libsignal \
  --data upstream_version=v0.86.0 \
  --data enable_web=true \
  --data flutter_version=3.38.4 \
  --data dart_sdk_version="^3.10.0" \
  --data flutter_sdk_version=">=3.38.0" \
  --data android_min_sdk=21 \
  --data android_compile_sdk=34 \
  --data topics="cryptography,ffi,native" \
  --data license=MIT
```

### Minimal example (uses defaults)

```bash
mkdir my_lib && cd my_lib
copier copy https://github.com/djx-y-z/copier-dart-frb-wrapper . \
  --trust \
  --defaults \
  --data package_name=my_lib \
  --data description="My Rust library wrapper" \
  --data native_library_name=mylib \
  --data github_repo=user/my_lib \
  --data native_repo=original/mylib
```

## Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `package_name` | Dart package name (lowercase, underscores) | `my_signal_lib` |
| `description` | Package description for pubspec.yaml | `Dart bindings for Signal Protocol` |
| `native_library_name` | Name of the native library | `signal` |
| `github_repo` | GitHub repository of your wrapper | `user/my_signal_lib` |
| `native_repo` | GitHub repository of native library | `signalapp/libsignal` |

### Rust Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `crate_name` | Rust crate name for FRB wrapper | `<package_name>_frb` | `my_signal_lib_frb` |
| `rust_edition` | Rust edition (2021 or 2024) | `2024` | `2021` |
| `rust_version` | Minimum Rust version (MSRV) | `1.88` | `1.75` |
| `frb_version` | Flutter Rust Bridge version | `^2.11.1` | `^2.10.0` |

### Upstream Crate (optional)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `upstream_crates` | Upstream Rust crates (comma-separated) | `` | `libsignal-protocol` or `libsignal-protocol,libsignal-core` |
| `upstream_version` | Version/tag of upstream crate | `` | `v0.86.0` |
| `version_tag_prefix` | Tag prefix for upstream version tags (used for version normalization) | `v` | `release-v` |

### Flutter/Dart Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `flutter_version` | Flutter version for FVM | `3.38.4` | `3.35.0` |
| `dart_sdk_version` | Dart SDK version constraint | `^3.10.0` | `^3.8.0` |
| `flutter_sdk_version` | Flutter SDK version constraint | `>=3.38.0` | `>=3.35.0` |
| `enable_web` | Enable Web/WASM support | `true` | `false` |
| `enable_claude` | Include Claude Code files (CLAUDE.md, .claude/skills/) | `true` | `false` |

### Android Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `android_min_sdk` | Android minimum SDK version | `21` | `24` |
| `android_compile_sdk` | Android compile SDK version | `34` | `35` |
| `android_ndk_version` | Android NDK version for Rust | `26.3.11579264` | `27.0.12077973` |

### Package Metadata

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `license` | Package license | `MIT` | `Apache-2.0` |
| `topics` | pub.dev topics (comma-separated) | `ffi,native,rust` | `cryptography,ffi,native` |

## Post-Generation Setup

After generating the project, follow these steps:

### 1. Initial Setup

```bash
cd <package_name>

# Install dependencies and set up the project
make setup

# Generate Flutter Rust Bridge bindings
make codegen

# Build native libraries for current platform
make build

# Verify everything works
make analyze          # Dart static analysis (should be clean)
make rust-check       # Rust type check
make test             # Run tests (should pass)
```

### 2. GitHub Repository Setup

1. Create a new repository on GitHub matching `github_repo`
2. Push the generated code:
   ```bash
   git remote add origin https://github.com/<github_repo>.git
   git push -u origin main
   ```

### 3. GitHub Actions Configuration

Configure secrets and variables in your repository settings (Settings → Secrets and variables → Actions).

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Description | Required For |
|--------|-------------|--------------|
| `APP_PRIVATE_KEY` | GitHub App private key (PEM format) | Update checker workflow |
| `GIST_TOKEN` | Personal Access Token with `gist` scope | Coverage badge |

#### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Description | Required For |
|----------|-------------|--------------|
| `APP_ID` | GitHub App ID | Update checker workflow |
| `COVERAGE_GIST_ID` | Gist ID for coverage badge JSON | Coverage badge |

#### GitHub App Setup (for update checker)

The GitHub App is used by the `check-*-updates.yml` workflow to create Pull Requests with signed commits when a new version of the native library is detected. This ensures commits are verified and associated with a bot account rather than a personal account.

1. Go to **Settings → Developer settings → GitHub Apps → New GitHub App**
2. Fill in:
   - **Name**: `my-package-bot` (must be unique on GitHub)
   - **Homepage URL**: Your repository URL
   - **Webhook**: Uncheck "Active" (not needed)
3. Set **Repository permissions**:
   - **Contents**: Read & Write
   - **Pull requests**: Read & Write
   - **Metadata**: Read-only
4. Click **Create GitHub App**
5. Copy the **App ID** (shown at the top) → add as `APP_ID` **variable**
6. Scroll down to **Private keys** → **Generate a private key**
7. A `.pem` file will download → copy its contents as `APP_PRIVATE_KEY` secret
8. Go to **Install App** (left sidebar) → Install on your repository

#### Coverage Badge Setup

1. Go to https://gist.github.com and create a new **secret** gist
2. Name the file `coverage.json` with content: `{"schemaVersion":1,"label":"coverage","message":"0%","color":"red"}`
3. Click **Create secret gist**
4. Copy the **Gist ID** from URL (e.g., `https://gist.github.com/user/abc123def456` → `abc123def456`)
5. Add the Gist ID as `COVERAGE_GIST_ID` **variable** (not secret)
6. Create a Personal Access Token:
   - Go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**
   - Click **Generate new token (classic)**
   - Name: `gist-coverage`
   - Scopes: check only `gist`
   - Click **Generate token** → copy and add as `GIST_TOKEN` secret

### 4. Repository Topics

Add these topics to your GitHub repository for discoverability:
- `dart`
- `flutter`
- `rust`
- `ffi`
- `flutter-rust-bridge`
- Your native library name

### 5. Update SECURITY.md

Review and update `SECURITY.md` with your security policy and contact information.

## Development Commands

The generated project includes a Makefile. Run `make help` to see all available commands:

```bash
# Setup
make setup              # Full setup (FVM + Rust tools + dependencies)
make setup-fvm          # Install FVM and project Flutter version only
make setup-rust-tools   # Install Rust tools (cargo-audit, frb codegen)
make setup-android      # Install Android build tools (cargo-ndk)
make setup-web          # Install web build tools (wasm-pack) - if enable_web=true

# Build & Codegen
make codegen            # Generate Dart bindings from Rust code
make build              # Build Rust library for current platform
make build-android      # Build for Android (all ABIs)
make build-web          # Build WASM for web platform - if enable_web=true

# Development
make check-upstream     # Check for native library updates
make version            # Show current crate version

# Rust Quality
make rust-check         # Check Rust code compiles
make rust-audit         # Audit Rust dependencies for vulnerabilities

# Dart Quality
make test               # Run tests
make coverage           # Run tests with coverage report
make analyze            # Run static analysis
make format             # Format Dart code
make format-check       # Check Dart code formatting
make doc                # Generate API documentation

# Utilities
make get                # Get dependencies
make clean              # Clean build artifacts
make publish-dry-run    # Validate package before publishing
```

## Troubleshooting

### FRB codegen fails

Ensure you have the correct Rust toolchain and cross-compilation targets installed.

**Note:** These are *target* architectures (what you build for), not your development machine's architecture. You can add targets on any OS, but some targets have platform requirements.

```bash
rustup update

# Desktop - Linux (any OS, but native builds require Linux)
rustup target add x86_64-unknown-linux-gnu   # Linux x86_64
rustup target add aarch64-unknown-linux-gnu  # Linux ARM64

# Desktop - macOS (macOS only - requires Xcode)
rustup target add aarch64-apple-darwin       # macOS Apple Silicon
rustup target add x86_64-apple-darwin        # macOS Intel

# Desktop - Windows (any OS, but native builds require Windows + MSVC)
rustup target add x86_64-pc-windows-msvc     # Windows x86_64

# Mobile - iOS (macOS only - requires Xcode)
rustup target add aarch64-apple-ios          # iOS devices (ARM64)
rustup target add aarch64-apple-ios-sim      # iOS Simulator on Apple Silicon
rustup target add x86_64-apple-ios           # iOS Simulator on Intel Mac

# Mobile - Android (any OS with Android NDK)
rustup target add aarch64-linux-android      # ARM64 devices (most modern phones)
rustup target add armv7-linux-androideabi    # ARMv7 devices (older phones)
rustup target add x86_64-linux-android       # x86_64 emulator

# Web/WASM (any OS)
rustup target add wasm32-unknown-unknown
```

### Native library download fails

1. Check that `native_repo` is correct and the repository has releases
2. Verify the release assets follow the expected naming convention
3. Check your network connection and GitHub API rate limits

### Build hook not found

Ensure you're using Dart 3.10+ with native assets support:
```bash
dart --version
flutter --version
```

### WASM build issues

For Web/WASM support:
```bash
# Install wasm-pack
cargo install wasm-pack

# Build WASM
make build-web
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This template is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Generated projects inherit this license by default, but you can choose a different license during generation.
