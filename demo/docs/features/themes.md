# Themes

DocsForge ships with the full Material Design theme.

## Material Theme

The default theme with all features:

```yaml
theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: teal
      accent: teal
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - content.code.copy
```

## Features

| Feature | Description |
|---------|-------------|
| Light/Dark mode | Automatic or manual switching |
| Navigation tabs | Top-level sections as tabs |
| Sidebars | Collapsible navigation |
| Search | Real-time search with suggestions |
| Code blocks | Syntax highlighting, copy button |
| Admonitions | Callout boxes |
| Tables | Styled data tables |

## Customization

Override any template by creating a `overrides/` directory:

```yaml
theme:
  name: material
  custom_dir: overrides
```

Or add extra CSS/JS:

```yaml
extra_css:
  - stylesheets/extra.css
extra_javascript:
  - javascripts/extra.js
```
