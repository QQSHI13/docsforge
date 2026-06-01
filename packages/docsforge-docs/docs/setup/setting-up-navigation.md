# Setting up navigation

DocsForge provides rich navigation options. Configure them in `docsforge.yml` under `theme.features`.

## Navigation structure

By default, DocsForge builds navigation from your `docs/` directory structure:

``` { .sh .no-copy }
docs/
├── index.md
├── getting-started.md
├── setup/
│   ├── index.md
│   ├── colors.md
│   └── fonts.md
└── reference/
    ├── index.md
    └── markdown.md
```

This creates:
- Home
- Getting started
- Setup (expandable section)
  - Setup overview (index page)
  - Colors
  - Fonts
- Reference (expandable section)
  - Reference overview (index page)
  - Markdown

## Top-level navigation tabs

Convert top-level sections into tabs:

``` yaml
theme:
  features:
    - navigation.tabs
```

!!! tip
    Combine with `navigation.tabs.sticky` to keep tabs visible when scrolling:
    ``` yaml
    theme:
      features:
        - navigation.tabs
        - navigation.tabs.sticky
    ```

## Section indexes

Make section headers clickable, linking to their `index.md`:

``` yaml
theme:
  features:
    - navigation.indexes
```

## Expand sections by default

``` yaml
theme:
  features:
    - navigation.expand
```

## Section grouping

Group navigation items into collapsible sections (enabled by default):

``` yaml
theme:
  features:
    - navigation.sections
```

## Back-to-top button

Show a "back to top" button when scrolling down:

``` yaml
theme:
  features:
    - navigation.top
```

## Footer navigation

Add previous/next page links at the bottom of each page:

``` yaml
theme:
  features:
    - navigation.footer
```

## Table of contents

### Follow active anchor

Highlight the current section in the table of contents as you scroll:

``` yaml
theme:
  features:
    - toc.follow
```

### Integrate with navigation

Move the table of contents into the navigation sidebar (for narrow layouts):

``` yaml
theme:
  features:
    - toc.integrate
```

## Custom navigation

Define navigation explicitly in `docsforge.yml`:

``` yaml
nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started.md
    - Quick start: quick-start.md
  - Setup:
    - setup/index.md
    - Colors: setup/colors.md
    - Fonts: setup/fonts.md
```

## Navigation tracking

Highlight the current page in the navigation:

``` yaml
theme:
  features:
    - navigation.tracking
```

Enabled by default.

## Complete navigation example

``` yaml
theme:
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - navigation.footer
    - navigation.tracking
    - toc.follow
```

## Next steps

- [Setting up site search](setting-up-site-search.md)
- [Setting up site analytics](setting-up-site-analytics.md)
