---
name: jinja-syntax
description: Jinja2 template syntax reference for copier templates. Use when user asks about template syntax, conditionals, filters, or how to use variables in templates.
---

# Jinja2 Syntax Reference

Quick reference for Jinja2 syntax used in copier-dart-frb-wrapper templates.

## Basic Syntax

```jinja2
{# This is a comment - not included in output #}

{{ variable }}              {# Output variable value #}
{% statement %}             {# Execute statement (if, for, etc.) #}
```

## Variable Substitution

```jinja2
{{ package_name }}                    {# Direct value #}
{{ package_name | default('value') }} {# With default if empty #}
{{ upstream_version or '' }}          {# Empty string if falsy #}
```

## Case Conversion Filters (jinja2-strcase)

```jinja2
{{ package_name | to_camel }}           {# my_package -> MyPackage #}
{{ package_name | to_lower_camel }}     {# my_package -> myPackage #}
{{ package_name | to_snake }}           {# MyPackage -> my_package #}
{{ package_name | to_screaming_snake }} {# my_package -> MY_PACKAGE #}
{{ package_name | to_kebab }}           {# my_package -> my-package #}
```

## Conditionals

### Simple if

```jinja2
{% if enable_web %}
web_enabled: true
{% endif %}
```

### If-else

```jinja2
{% if enable_web %}
platforms: all
{% else %}
platforms: native
{% endif %}
```

### If-elif-else

```jinja2
{% if rust_edition == '2024' %}
edition = "2024"
{% elif rust_edition == '2021' %}
edition = "2021"
{% else %}
edition = "2021"
{% endif %}
```

### Inline conditional

```jinja2
{{ 'enabled' if enable_web else 'disabled' }}
```

### Check if variable is defined/truthy

```jinja2
{% if upstream_crates %}
{% for crate in upstream_crates.split(',') %}
{{ crate | trim }} = "{{ upstream_version }}"
{% endfor %}
{% endif %}

{% if upstream_crates != '' %}
# Has upstream crates
{% endif %}
```

## Loops

```jinja2
{% for topic in topics.split(',') %}
  - {{ topic | trim }}
{% endfor %}
```

## String Operations

```jinja2
{# Strip prefix #}
{{ upstream_version[1:] if upstream_version.startswith('v') else upstream_version }}

{# Replace #}
{{ package_name | replace('_', '-') }}

{# Split and join #}
{{ topics.split(',') | join(', ') }}

{# Trim whitespace #}
{{ variable | trim }}

{# Upper/lower #}
{{ package_name | upper }}
{{ package_name | lower }}
```

## Whitespace Control

```jinja2
{#- Remove whitespace before -#}
{%- if condition -%}   {# Remove whitespace both sides #}
{{- variable -}}       {# Remove whitespace both sides #}
```

### Example: Clean YAML list

```jinja2
dependencies:
{%- for dep in deps %}
  - {{ dep }}
{%- endfor %}
```

## Set Variables

```jinja2
{% set normalized = upstream_version[version_tag_prefix | length:] if upstream_version.startswith(version_tag_prefix) else upstream_version %}
{{ normalized }}
```

## Common Patterns in This Template

### Conditional dependency

```jinja2
# rust/Cargo.toml.jinja
[dependencies]
flutter_rust_bridge = "{{ frb_version }}"
{% if upstream_crates %}
{% for crate in upstream_crates.split(',') %}
{{ crate | trim }} = "{{ upstream_version }}"
{% endfor %}
{% endif %}
```

### Conditional file content

```jinja2
# Makefile.jinja
{% if enable_web %}
build-web:
	wasm-pack build ...
{% endif %}
```

### Platform list

```jinja2
# pubspec.yaml.jinja
platforms:
  android:
  ios:
  linux:
  macos:
  windows:
{% if enable_web %}
  web:
{% endif %}
```

### GitHub workflow matrix

```jinja2
# .github/workflows/build.yml.jinja
jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
          - os: macos-latest
{% if enable_web %}
          - os: ubuntu-latest
            target: wasm
{% endif %}
```

## File Naming

Template files with Jinja2 content use `.jinja` suffix:
- `pubspec.yaml.jinja` -> generates `pubspec.yaml`
- `README.md.jinja` -> generates `README.md`

Directory/file names can use variables:
- `{{ package_name }}/` -> `my_package/`
- `{{ package_name }}.dart.jinja` -> `my_package.dart`

## Escaping

### Literal braces in output

```jinja2
{# For GitHub Actions expressions #}
${{"{{"}} github.token {{"}}"}}

{# Result: ${{ github.token }} #}
```

### Raw block (no processing)

```jinja2
{% raw %}
This {{ will not }} be processed
{% endraw %}
```

## Debugging

```jinja2
{# Print variable type/value for debugging #}
{# {{ variable | pprint }} #}

{# Check if defined #}
{% if variable is defined %}
  defined: {{ variable }}
{% else %}
  not defined
{% endif %}
```
