---
name: add-variable
description: Add a new variable to the Copier template. Use when user wants to add a new configuration option, template variable, or customize the generated project.
---

# Add Template Variable

Guide for adding new variables to the copier-dart-frb-wrapper template.

## Step 1: Define Variable in copier.yml

Add the variable definition in the appropriate section:

```yaml
# copier.yml

# Basic string variable
my_variable:
  type: str
  help: "Description shown to user"
  default: "default_value"

# Boolean variable
enable_feature:
  type: bool
  help: "Enable the feature"
  default: false

# Choice variable
feature_type:
  type: str
  help: "Type of feature"
  choices:
    - option1
    - option2
    - option3
  default: option1

# Conditional variable (shown only when condition is true)
feature_config:
  type: str
  help: "Feature configuration"
  default: ""
  when: "{{ enable_feature }}"

# Variable with validation
repo_name:
  type: str
  help: "Repository name (user/repo format)"
  validator: >-
    {% if not (repo_name | regex_search('^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$')) %}
    Must be in format "username/repo_name"
    {% endif %}
```

## Step 2: Use Variable in Templates

### In .jinja files

```jinja2
{# Simple substitution #}
name: {{ my_variable }}

{# Conditional block #}
{% if enable_feature %}
feature_enabled: true
{% endif %}

{# Case conversion filters #}
{{ package_name | to_camel }}           {# PascalCase: MyPackage #}
{{ package_name | to_lower_camel }}     {# camelCase: myPackage #}
{{ package_name | to_snake }}           {# snake_case: my_package #}
{{ package_name | to_screaming_snake }} {# CONSTANT_CASE: MY_PACKAGE #}

{# Default value if empty #}
{{ my_variable or 'fallback_value' }}

{# Strip tag prefix from version #}
version: {{ upstream_version[version_tag_prefix | length:] if upstream_version.startswith(version_tag_prefix) else upstream_version }}
```

### In file/directory names

```
template/{{ package_name }}/lib/src/{{ feature_name }}.dart.jinja
```

## Step 3: Update Documentation

### 1. README.md - Variables section

Add to appropriate table in the Variables section.

### 2. README.md - Example with all parameters

Add `--data my_variable=value` to the full example.

### 3. CLAUDE.md - Template Variables table

Add variable to the documentation table.

### 4. CONTRIBUTING.md - Test examples (if needed)

Add test case if variable significantly changes output.

## Variable Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `str` | String value | `"hello"` |
| `bool` | Boolean | `true` / `false` |
| `int` | Integer | `42` |
| `float` | Float | `3.14` |
| `yaml` | YAML structure | Complex objects |

## Conditional File Exclusion

To conditionally remove files based on variables, use `_tasks` with `when` in copier.yml:

```yaml
_tasks:
  # Remove feature files when enable_feature is false
  - command: rm -rf lib/src/feature/
    working_directory: "{{ _copier_conf.dst_path }}/{{ package_name }}"
    when: "{{ not enable_feature }}"

  # Remove Claude files when enable_claude is false
  - command: rm -rf CLAUDE.md .claude
    working_directory: "{{ _copier_conf.dst_path }}/{{ package_name }}"
    when: "{{ not enable_claude }}"
```

**Note:** The `when` condition uses Jinja2 syntax and runs after all files are copied.

## Testing New Variable

```bash
# Test with default value
rm -rf /tmp/test && copier copy . /tmp/test \
  --trust --vcs-ref HEAD \
  --data package_name=test \
  --data description="Test" \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib

# Verify default
grep "expected_default" /tmp/test/test/path/to/file

# Test with custom value
rm -rf /tmp/test && copier copy . /tmp/test \
  --trust --vcs-ref HEAD \
  --data package_name=test \
  --data description="Test" \
  --data native_library_name=lib \
  --data github_repo=u/r \
  --data native_repo=o/lib \
  --data my_variable=custom_value

# Verify custom value
grep "custom_value" /tmp/test/test/path/to/file
```

## Common Patterns

### Optional feature with files

```yaml
# copier.yml
enable_feature:
  type: bool
  default: false

_tasks:
  # Remove feature files when disabled
  - command: rm -rf lib/src/feature.dart
    working_directory: "{{ _copier_conf.dst_path }}/{{ package_name }}"
    when: "{{ not enable_feature }}"
```

### Version with tag prefix

```yaml
upstream_version:
  type: str
  default: ""

version_tag_prefix:
  type: str
  default: "v"
```

```jinja2
{# In template #}
{% set version = upstream_version[version_tag_prefix | length:] if upstream_version.startswith(version_tag_prefix) else upstream_version %}
```

### Computed default

```yaml
crate_name:
  type: str
  help: "Rust crate name"
  default: "{{ package_name }}_frb"
```
