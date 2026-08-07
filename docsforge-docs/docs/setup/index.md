# Setup

DocsForge's setup guides help you customize every aspect of your documentation site. All configuration happens in `docsforge.yml`.

## Overview

The following guides cover the most common customization scenarios:

<div class="grid cards" markdown>

-   :material-palette:{ .lg .middle } &nbsp; **[Changing the colors](changing-the-colors.md)**

    ---

    Customize primary, accent, and background colors. Configure light and dark mode palettes.

-   :material-format-font:{ .lg .middle } &nbsp; **[Changing the fonts](changing-the-fonts.md)**

    ---

    Use Google Fonts or custom font files for text and code.

-   :material-translate:{ .lg .middle } &nbsp; **[Changing the language](changing-the-language.md)**

    ---

    Set the site language, configure search stemming, and RTL support.

-   :material-navigation-variant:{ .lg .middle } &nbsp; **[Setting up navigation](setting-up-navigation.md)**

    ---

    Tabs, sections, indexes, footer links, and table of contents.

-   :material-magnify:{ .lg .middle } &nbsp; **[Setting up site search](setting-up-site-search.md)**

    ---

    Configure search behavior, separators, and result presentation.

-   :material-chart-line:{ .lg .middle } &nbsp; **[Setting up site analytics](setting-up-site-analytics.md)**

    ---

    Add Plausible or Google Analytics to track page views.

-   :material-image:{ .lg .middle } &nbsp; **[Setting up social cards](setting-up-social-cards.md)**

    ---

    Configure Open Graph and Twitter Card meta tags for rich link previews.

-   :material-package-variant-closed-check:{ .lg .middle } &nbsp; **[Building an optimized site](building-an-optimized-site.md)**

    ---

    Enable HTML minification, asset compression, and build optimization.

-   :material-github:{ .lg .middle } &nbsp; **[Adding a git repository](adding-a-git-repository.md)**

    ---

    Link to your source repo with "Edit this page" buttons.

</div>

## Configuration file

All customization is done in `docsforge.yml`. DocsForge loads all plugins and Markdown extensions automatically — you only configure what you want to customize.

``` yaml title="docsforge.yml"
site_name: My Project
site_url: https://example.com/docs/
site_author: Your Name
site_description: Documentation for My Project

repo_name: username/repo
repo_url: https://github.com/username/repo

copyright: Copyright &copy; 2025 Your Name

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: black
      accent: teal
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  font:
    text: Roboto
    code: Roboto Mono
```

## Next steps

Pick a guide above to customize a specific aspect of your site. Each guide includes copy-paste-ready configuration examples.
