# Contributing to copier-dart-frb-wrapper

Thank you for your interest in contributing to this Copier template!

## Getting Started

### Prerequisites

- Python 3.8+
- [Copier](https://copier.readthedocs.io/) 9.0+
- [jinja2-strcase](https://pypi.org/project/jinja2-strcase/)

```bash
pip install copier jinja2-strcase
# or
brew install copier && pip install jinja2-strcase
```

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/copier-dart-frb-wrapper.git
   cd copier-dart-frb-wrapper
   ```

## Development Workflow

### Template Structure

```
copier-dart-frb-wrapper/
├── copier.yml                    # Template configuration and variables
├── template/
│   └── {{ package_name }}/       # Template files (Jinja2 syntax)
│       ├── lib/                  # Dart library code
│       ├── rust/                 # Rust FRB crate
│       ├── hook/                 # Native library download hook
│       ├── scripts/              # Build and utility scripts
│       ├── .github/              # GitHub Actions workflows
│       ├── .claude/skills/       # Claude Code skills
│       └── ...
├── README.md                     # Template documentation
├── CONTRIBUTING.md               # This file
├── CHANGELOG.md                  # Version history
├── CLAUDE.md                     # Development instructions
└── LICENSE                       # MIT license
```

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```

2. Edit template files in `template/{{ package_name }}/`
   - Use `.jinja` suffix for files with Jinja2 content
   - Use `{{ variable_name }}` for variable substitution
   - Use `{% if condition %}...{% endif %}` for conditionals

3. If adding new variables, update `copier.yml`:
   ```yaml
   my_variable:
     type: str
     help: "Description of the variable"
     default: "default_value"
   ```

### Testing Changes

Test with different configurations after making changes:

```bash
# Test basic FRB project (web enabled by default)
rm -rf /tmp/test_basic && copier copy . /tmp/test_basic \
  --trust --vcs-ref HEAD \
  --data package_name=test_basic \
  --data description="Test FRB wrapper" \
  --data native_library_name=testlib \
  --data github_repo=user/test_basic \
  --data native_repo=original/testlib

# Check generated files
ls -la /tmp/test_basic/test_basic/

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

# Test full configuration (upstream + web)
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

### Jinja2 Syntax Reference

This template uses Jinja2 with [jinja2-strcase](https://pypi.org/project/jinja2-strcase/) extension:

```jinja2
{{ package_name }}                      # Variable substitution
{{ package_name | to_camel }}           # PascalCase: MyPackage
{{ package_name | to_lower_camel }}     # camelCase: myPackage
{{ package_name | to_snake }}           # snake_case: my_package
{{ package_name | to_screaming_snake }} # CONSTANT_CASE: MY_PACKAGE

{% if enable_web %}...{% endif %}       # Conditional for Web/WASM support
{% if upstream_crates %}...{% endif %}  # Conditional for upstream crates
```

## Pull Request Process

1. Ensure your changes work with different configurations:
   - Basic FRB project (web enabled by default)
   - With `enable_web=false`
   - With `enable_claude=false`
   - With `upstream_crates` specified
2. Update documentation if needed:
   - `README.md` - if adding new variables or features
   - `CLAUDE.md` - if adding new variables or changing template structure
   - `CHANGELOG.md` - add your changes under `[Unreleased]`
3. Follow the commit message format (see below)
4. Submit a pull request

## Releasing New Versions

This template uses git tags for versioning. Copier automatically detects versions from tags.

### Creating a Release

1. **Update CHANGELOG.md:**
   - Move items from `[Unreleased]` to new version section
   - Add release date: `## [1.1.0] - 2025-01-28`
   - Add comparison link at bottom

2. **Commit the changelog:**
   ```bash
   git add CHANGELOG.md
   git commit -m "chore: prepare release v1.1.0"
   ```

3. **Create and push tag:**
   ```bash
   git tag v1.1.0
   git push origin main
   git push origin v1.1.0
   ```

4. **Create GitHub Release** (optional but recommended):
   - Go to Releases → Draft a new release
   - Select the tag
   - Copy changelog section as release notes

### Version Guidelines

- Use [Semantic Versioning](https://semver.org/): `vMAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes (renamed variables, removed features)
- **MINOR**: New features, new variables (backward compatible)
- **PATCH**: Bug fixes, documentation updates

### How Users Get Updates

```bash
# Users update their projects with:
cd my_project
copier update

# Or specify a version:
copier update --vcs-ref v1.1.0
```

## Commit Messages

Use clear, descriptive commit messages following [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: Add new feature` - new functionality
- `fix: Fix bug in XYZ` - bug fixes
- `docs: Update README` - documentation only
- `refactor: Improve code structure` - code changes that neither fix bugs nor add features
- `chore: Update dependencies` - maintenance tasks

Examples:
```
feat: add support for custom Cargo features
fix: correct WASM build configuration
docs: add examples for upstream crate usage
```

## Code Style

### Template Files

- Use 2 spaces for indentation in YAML, Dart, and shell scripts
- Use meaningful variable names
- Add comments for complex Jinja2 logic
- Keep conditionals simple and readable

### copier.yml

- Group related variables with comments
- Provide helpful descriptions in `help` field
- Add validators for required fields
- Use sensible defaults where possible

## Reporting Issues

When reporting issues, please include:

1. Copier version (`copier --version`)
2. Python version (`python --version`)
3. Operating system
4. Template variables used
5. Steps to reproduce
6. Expected vs actual behavior
7. Relevant error messages

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
