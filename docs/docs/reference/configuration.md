---
icon: material/tune-variant
---

# Configuration Reference

This page documents every option available in `docsforge.yml`. Use it as a complete reference when customizing your site.

---

## Top-level settings

### `site_name`

The title of your documentation site. Displayed in the header, browser tab, and social cards.

```yaml
site_name: My Documentation
```

| Type | Default | Required |
|------|---------|----------|
| `string` | — | Yes |

---

### `site_url`

The canonical URL where your site will be hosted. Used for social cards, RSS feeds, and absolute link generation.

```yaml
site_url: https://example.com/docs/
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

!!! tip "Trailing slash"
    Always include a trailing slash for consistency:
    ```yaml
    site_url: https://example.com/docs/  # Good
    site_url: https://example.com/docs   # Avoid
    ```

---

### `site_author`

The author name. Used in metadata and RSS feeds.

```yaml
site_author: Jane Doe
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `site_description`

A short description of your site. Used in meta tags and social cards.

```yaml
site_description: Documentation for the Example Platform
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `copyright`

Copyright notice displayed in the footer.

```yaml
copyright: Copyright &copy; 2025 Example Inc.
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `repo_url`

URL to your source repository. Adds an edit icon in the header linking to the repo.

```yaml
repo_url: https://github.com/example/docs
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `repo_name`

Display name for the repository link. Defaults to the last path segment of `repo_url`.

```yaml
repo_name: example/docs
```

| Type | Default | Required |
|------|---------|----------|
| `string` | Auto | No |

---

### `edit_uri`

Path suffix for the "Edit this page" link. Combined with `repo_url` to create the full edit URL.

```yaml
edit_uri: edit/main/docs/
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `strict`

When `true`, warnings are treated as errors and the build fails.

```yaml
strict: true
```

| Type | Default | Required |
|------|---------|----------|
| `boolean` | `false` | No |

---

### `dev_addr`

Address for the development server.

```yaml
dev_addr: 127.0.0.1:8000
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `127.0.0.1:8000` | No |

---

### `use_directory_urls`

When `true` (default), pages are built as `page/index.html` instead of `page.html`. This creates cleaner URLs (`/page/` instead of `/page.html`).

```yaml
use_directory_urls: true
```

| Type | Default | Required |
|------|---------|----------|
| `boolean` | `true` | No |

---

### `docs_dir`

Directory containing your Markdown source files.

```yaml
docs_dir: docs
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `docs` | No |

---

### `site_dir`

Directory where the built site is output.

```yaml
site_dir: site
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `site` | No |

---

### `extra_css`

Additional CSS files to include. Paths are relative to `docs_dir`.

```yaml
extra_css:
  - stylesheets/custom.css
```

| Type | Default | Required |
|------|---------|----------|
| `list` | `[]` | No |

---

### `extra_javascript`

Additional JavaScript files to include. Paths are relative to `docs_dir`.

```yaml
extra_javascript:
  - javascripts/analytics.js
```

| Type | Default | Required |
|------|---------|----------|
| `list` | `[]` | No |

!!! warning "Remove vendored assets"
    Do not include KaTeX, Mermaid, or Material Icons here. They are built-in.

### `extra_templates`

Additional Jinja2 templates (HTML or XML) from `docs_dir` to build with the global context.

```yaml
extra_templates:
  - sitemap-custom.xml
```

| Type | Default | Required |
|------|---------|----------|
| `list` | `[]` | No |

---

### `exclude_docs`

Gitignore-style patterns (relative to `docs_dir`) of files to exclude from the site entirely.

```yaml
exclude_docs: |
  private/notes.md
  drafts/**
```

| Type | Default | Required |
|------|---------|----------|
| `string` (gitignore) | — | No |

---

### `draft_docs`

Gitignore-style patterns of files to mark as drafts. Drafts are built but flagged, so they are not linked from the navigation; `docsforge serve` still renders them.

| Type | Default | Required |
|------|---------|----------|
| `string` (gitignore) | — | No |

---

### `not_in_nav`

Gitignore-style patterns of files that are intentionally not in the navigation. Suppresses the "not included in nav" warning for those files.

| Type | Default | Required |
|------|---------|----------|
| `string` (gitignore) | — | No |

---

### `tikz`

Enable TikZ diagram compilation. `.tex` files under `docs_dir` containing `\begin{tikzpicture}` (or in a `tikz/` directory) are compiled to SVG during the build. Requires a LaTeX toolchain (`latex`/`pdflatex` + `dvisvgm`/`pdf2svg`); when unavailable the build warns and skips compilation.

Sources without a `\documentclass` (just the picture body) are automatically wrapped in a standalone document with a default math preamble — `amsmath`, `amssymb`, `tikz`, `pgfplots`, `tikz-cd` and `tkz-euclide` are preloaded, so a diagram is just:

```latex
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\end{tikzpicture}
```

The generated SVG embeds fonts, so diagram text stays selectable and searchable; on minimal TeX installs (no `texlive-fonts-recommended`) it falls back to outlined paths.

```yaml
tikz: true
```

| Type | Default | Required |
|------|---------|----------|
| `boolean` | `null` (auto) | No |

---

### `tikz_preamble`

Extra LaTeX preamble lines injected into bare diagram sources (files without a `\documentclass`), after the default math preamble. Ignored for full documents.

```yaml
tikz_preamble:
  - \usetikzlibrary{calc}
  - \usepackage{caption}
```

| Type | Default | Required |
|------|---------|----------|
| `list` of `string` | `null` | No |

---

### `hooks`

Python module files loaded as plugins. Each hook receives the full plugin event API (see [Custom Plugins](../advanced/plugins.md)) — e.g. `on_build_done` to post-process `site/sw.js` after the build.

```yaml
hooks:
  - my_hook.py
```

| Type | Default | Required |
|------|---------|----------|
| `list` | `[]` | No |

---

### `watch`

Extra paths (files or directories) to watch while running `docsforge serve`.

```yaml
watch:
  - ../shared-content
```

| Type | Default | Required |
|------|---------|----------|
| `list` | `[]` | No |

---

### `remote_branch` / `remote_name`

Legacy MkDocs options kept for config compatibility. DocsForge has no `gh-deploy` command — deploy with GitHub Actions instead (see [Publishing your site](../publishing-your-site.md)). They are accepted but unused.

| Key | Default |
|-----|---------|
| `remote_branch` | `gh-pages` |
| `remote_name` | `origin` |

---

## Theme settings

Theme settings live under the `theme:` block, just like DocsForge Material.

```yaml
theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
  logo: assets/logo.svg
  favicon: assets/favicon.svg
  icon:
    repo: fontawesome/brands/github
```

### `theme.name`

The theme to use. DocsForge bundles Material, so this is usually `material`.

```yaml
theme:
  name: material
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `material` | No |

---

### `theme.palette`

Color scheme configuration. Supports light/dark mode toggling.

```yaml
theme:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
```

| Property | Type | Description |
|----------|------|-------------|
| `media` | `string` | CSS media query for auto-switching |
| `scheme` | `string` | Color scheme: `default` or `slate` |
| `primary` | `string` | Primary color: `red`, `pink`, `purple`, `deep-purple`, `indigo`, `blue`, `light-blue`, `cyan`, `teal`, `green`, `light-green`, `lime`, `yellow`, `amber`, `orange`, `deep-orange`, `brown`, `grey`, `blue-grey`, `black`, `white` |
| `accent` | `string` | Accent color (same options as `primary`) |
| `toggle` | `object` | Toggle button configuration |
| `toggle.icon` | `string` | Icon identifier |
| `toggle.name` | `string` | Tooltip text |

---

### `theme.features`

Navigation and UI features to enable.

```yaml
theme:
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.path
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link
    - content.code.copy
    - content.action.edit
```

| Feature | Default | Description |
|---------|:-------:|-------------|
| `navigation.tabs` | Yes | Top-level navigation tabs |
| `navigation.sections` | Yes | Section pages in sidebar |
| `navigation.expand` | No | Expand all sections by default |
| `navigation.path` | No | Breadcrumb navigation |
| `navigation.top` | Yes | Back-to-top button |
| `navigation.footer` | Yes | Previous/next footer links |
| `navigation.indexes` | Yes | Index pages for sections |
| `navigation.tracking` | Yes | Anchor tracking in URL |
| `navigation.instant` | Yes | Instant navigation |
| `navigation.instant.progress` | Yes | Instant navigation progress bar |
| `search.suggest` | Yes | Search suggestions in header |
| `search.highlight` | Yes | Highlight search terms in results |
| `search.share` | Yes | Share search query links |
| `content.tabs.link` | No | Link content tabs across pages |
| `content.tooltips` | Yes | Content tooltips |
| `content.code.copy` | Yes | Copy button on code blocks |
| `content.code.annotate` | Yes | Code annotations |
| `content.action.edit` | Yes | Edit page button |
| `content.action.view` | Yes | View source button |
| `announce.dismiss` | No | Dismissible announcement bar |
| `toc.follow` | Yes | TOC follows scroll |

---

### `theme.icon`

Icon configuration for various UI elements.

```yaml
theme:
  icon:
    repo: fontawesome/brands/github
    logo: material/library
```

| Property | Type | Description |
|----------|------|-------------|
| `repo` | `string` | Icon for repository link |
| `logo` | `string` | Icon used in logo area |
| `admonition` | `object` | Custom admonition icons |

---

### `theme.logo`

Path to your site logo (relative to `docs_dir`).

```yaml
theme:
  logo: assets/logo.svg
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `theme.favicon`

Path to favicon (relative to `docs_dir`).

```yaml
theme:
  favicon: assets/favicon.svg
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `theme.language`

Site language for internationalization.

```yaml
theme:
  language: en
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `en` | No |

---

### `theme.direction`

Text direction.

```yaml
theme:
  direction: ltr
```

| Type | Default | Options |
|------|---------|---------|
| `string` | `ltr` | `ltr`, `rtl` |

---

### `theme.custom_dir`

Directory for custom templates and overrides (relative to `docs_dir`).

```yaml
theme:
  custom_dir: overrides
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

## Plugin settings

DocsForge has many plugins built-in. Most require no configuration. Only add settings if you need to customize behavior.

### `plugins`

```yaml
plugins:
  search:
    lang: en
  tags:
    tags_file: tags.md
  blog:
    blog_dir: blog
    blog_toc: true
```

#### `search` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `lang` | `string` | `en` | Search language for stemming |
| `separator` | `string` | `[\s\-]+` | Word separator regex |
| `pipeline` | `list` | `[trimmer, stopWordFilter, stemmer]` | Processing pipeline |
| `jieba_dict` | `string` | `null` | Path to a custom jieba dictionary |
| `jieba_dict_user` | `string` | `null` | Path to a custom jieba user dictionary |

#### `tags` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `tags_file` | `string` | `tags.md` | Page for tag index |
| `tags_extra_files` | `list` | `[]` | Extra tag files |
| `tags_hierarchy` | `boolean` | `false` | Enable tag hierarchy |

#### `blog` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `blog_dir` | `string` | `blog` | Blog posts directory |
| `blog_toc` | `boolean` | `false` | Show table of contents |
| `post_date_format` | `string` | `long` | Date format |
| `post_excerpt` | `string` | `optional` | Excerpt behavior |
| `post_readtime` | `boolean` | `true` | Show reading time |
| `post_url_format` | `string` | `{date}/{slug}` | URL pattern |
| `archive_date_format` | `string` | `YYYY` | Archive format |
| `archive_url_format` | `string` | `archive/{date}` | Archive URL |
| `categories_url_format` | `string` | `category/{slug}` | Category URL |
| `pagination_url_format` | `string` | `page/{page}` | Pagination URL |
| `authors_file` | `string` | `.authors.yml` | Authors file |

#### `minify` plugin

The minify plugin is always enabled and has no configuration options. It minifies HTML pages and any `extra_css` / `extra_javascript` files.

#### `privacy` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | Enable plugin |
| `concurrency` | `integer` | `CPU count - 1` | Download concurrency |
| `cache_dir` | `string` | `.cache/plugin/privacy` | Local cache directory |
| `assets_fetch` | `boolean` | `true` | Fetch external assets from the network |
| `assets_fetch_dir` | `string` | `assets/external` | Storage directory inside `site_dir` |
| `assets_include` | `list` | `[]` | Glob patterns of external URLs to always fetch |
| `assets_exclude` | `list` | `[]` | Glob patterns of external URLs to skip |
| `assets_expr_map` | `dict` | `{}` | Extra regexes for finding assets in CSS/JS |
| `links_attr_map` | `dict` | `{}` | Extra attributes to add to external links |
| `links_noopener` | `boolean` | `true` | Add `noopener` to external links |

#### `info` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | Enable plugin |
| `enabled_on_serve` | `boolean` | `false` | Show info output when serving |

#### `meta` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `meta_file` | `string` | `.meta.yml` | Metadata file |
| `enabled` | `boolean` | `true` | Enable plugin |

#### `i18n` plugin

Multi-language sites (suffix-mode locale variants). The plugin auto-loads; it can also be configured under `extra.i18n_languages` (see [Multi-language sites](../setup/i18n.md)).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `languages` | `list` | `[]` | Locales: `locale`, `name`, `default`, optional `site_name`, `site_description`, `nav_translations` |
| `enabled` | `boolean` | `true` | Enable plugin |

#### `social` plugin

Opt-in social card generation (OpenGraph PNG per page). Needs `pip install docsforge[social]` (pillow + cairosvg); see [Setting up social cards](../setup/setting-up-social-cards.md).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | Enable plugin |
| `concurrency` | `integer` | CPU count - 1 | Parallel card rendering |
| `cache` | `boolean` | `true` | Cache generated cards |
| `cache_dir` | `string` | `.docsforge/cache/social` | Card cache directory |
| `cards` | `boolean` | `true` | Generate cards |
| `cards_dir` | `string` | `assets/images/social` | Card output directory |
| `cards_layout` | `string` | `default` | Card layout |
| `cards_layout_dir` | `string` | `layouts` | Custom layout directory |
| `cards_layout_options` | `dict` | `{}` | `background_color`, `color`, `font_family`, ... |
| `cards_include` | `list` | `[]` | Page globs to include |
| `cards_exclude` | `list` | `[]` | Page globs to exclude |

---

## Markdown extensions

DocsForge enables most common extensions by default — 36 default + 3 built-ins
(`toc`, `tables`, `fenced_code`). Only configure if you need custom behavior.

### `markdown_extensions`

```yaml
markdown_extensions:
  - toc:
      permalink: true
      title: On this page
      toc_depth: 3
```

| Extension | Built-in | Description |
|-----------|----------|-------------|
| `admonition` | Yes | Callout boxes (`!!! note`) |
| `pymdownx.details` | Yes | Collapsible details (`??? question`) |
| `pymdownx.superfences` | Yes | Fenced code blocks with custom fences |
| `fenced_code` | Yes | Standard fenced code blocks |
| `pymdownx.betterem` | Yes | Smarter emphasis handling |
| `pymdownx.highlight` | Yes | Code syntax highlighting |
| `pymdownx.inlinehilite` | Yes | Inline code highlighting |
| `pymdownx.snippets` | Yes | Content inclusion (`--8<--`) |
| `pymdownx.tabbed` | Yes | Tabbed content (`=== "Tab 1"`) |
| `pymdownx.tasklist` | Yes | Task lists (`- [ ]`) |
| `pymdownx.emoji` | Yes | Emoji and icons (`:material-check:`) |
| `pymdownx.arithmatex` | Yes | Math rendering (`$...$`, `$$...$$`) |
| `pymdownx.keys` | Yes | Keyboard keys (`++ctrl+c++`) |
| `pymdownx.mark` | Yes | Highlighted text (`==text==`) |
| `pymdownx.critic` | Yes | Critic markup |
| `pymdownx.caret` | Yes | Superscript (`^text^`) |
| `pymdownx.tilde` | Yes | Subscript (`~text~`) |
| `tables` | Yes | Markdown tables |
| `toc` | Yes | Table of contents |
| `meta` | Yes | YAML frontmatter |
| `def_list` | Yes | Definition lists |
| `footnotes` | Yes | Footnotes (`[^1]`) |
| `attr_list` | Yes | Attribute lists (`{.class}`) |
| `md_in_html` | Yes | Markdown inside HTML |
| `abbr` | Yes | Abbreviations (`*[HTML]: Hyper Text Markup Language`) |
| `nl2br` | Yes | Newlines to line breaks |
| `sane_lists` | Yes | Strict list nesting |
| `wikilinks` | Yes | Wiki-style links (`[[Page title]]`) |
| `pymdownx.b64` | Yes | Base64 image encoding |
| `pymdownx.escapeall` | Yes | Escape all characters |
| `pymdownx.extra` | Yes | Extra Markdown features |
| `pymdownx.fancylists` | Yes | Fancy ordered lists |
| `pymdownx.pathconverter` | Yes | Relative path conversion |
| `pymdownx.progressbar` | Yes | Progress bars |
| `pymdownx.quotes` | Yes | Block quotes with attributes |
| `pymdownx.saneheaders` | Yes | Sane header handling |
| `pymdownx.smartsymbols` | Yes | Smart symbols |
| `pymdownx.striphtml` | Yes | Strip HTML from output |
| `smarty` | No | Smart quotes and dashes |

---

## Extra settings

The `extra:` section holds custom variables accessible in templates and Markdown via `{{ extra.key }}`.

### `extra.social`

Social links in the footer.

```yaml
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/example
      name: Example on GitHub
    - icon: fontawesome/brands/twitter
      link: https://twitter.com/example
      name: Example on Twitter
```

---

### `extra.alternate`

Language alternates for multi-language sites.

```yaml
extra:
  alternate:
    - name: English
      link: /
      lang: en
    - name: Deutsch
      link: /de/
      lang: de
```

---

### `extra.tags`

Tag configuration.

```yaml
extra:
  tags:
    file: tags.md
    icons:
      - name: "New"
        icon: material/star
```

---

### `extra.annotate`

Code annotation settings.

```yaml
extra:
  annotate:
    json: [.s2]
```

---

### `extra.scope`

Google Analytics / Plausible scope.

```yaml
extra:
  scope:
    analytics: true
    feedback: true
```

---

## Navigation

### `nav`

Explicit navigation structure. If omitted, pages are discovered automatically from `docs_dir`.

```yaml
nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quick-start.md
  - Reference:
    - API: reference/api.md
    - CLI: reference/cli.md
  - Blog: blog/
```

| Syntax | Description |
|--------|-------------|
| `Page Title: path.md` | Single page with custom title |
| `Section:` | Nested section |
| `Directory/` | Auto-discover pages in directory |
| `!include path` | Include another nav file |

---

## Validation settings

### `validation`

Link, anchor, and navigation validation.

```yaml
validation:
  nav:
    omitted_files: warn
    not_found: warn
  links:
    absolute_links: warn
    unrecognized_links: warn
    anchors: warn
```

### `validation.nav`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `omitted_files` | `string` | `info` | Files not in `nav` |
| `not_found` | `string` | `warn` | Navigation links to missing pages |
| `absolute_links` | `string` | `info` | Absolute nav links |

### `validation.links`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `absolute_links` | `string` | `info` | Absolute Markdown links |
| `unrecognized_links` | `string` | `info` | Links that don't look like internal pages |
| `not_found` | `string` | `warn` | Markdown links to missing pages |
| `anchors` | `string` | `info` | Links to missing anchors |

Values: `warn`, `info`, `ignore`.

---

## Complete example

```yaml
# Site metadata
site_name: Example Documentation
site_url: https://docs.example.com/
site_author: Example Team
site_description: Complete documentation for the Example platform
copyright: Copyright &copy; 2025 Example Inc.

# Repository
repo_url: https://github.com/example/docs
repo_name: example/docs
edit_uri: edit/main/docs/

# Directories
docs_dir: docs
site_dir: site
use_directory_urls: true
strict: false

# Theme
theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link
    - content.code.copy
    - content.action.edit
  logo: assets/logo.svg
  favicon: assets/favicon.svg
  icon:
    repo: fontawesome/brands/github
  language: en

# Custom assets
extra_css:
  - stylesheets/custom.css

extra_javascript:
  - javascripts/analytics.js

# Plugins
plugins:
  search:
    lang: en
  tags:
    tags_file: tags.md
  blog:
    blog_dir: blog
    blog_toc: true

# Extra variables
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/example
    - icon: fontawesome/brands/twitter
      link: https://twitter.com/example

# Navigation
nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Configuration: getting-started/configuration.md
  - Reference:
    - API: reference/api.md
    - CLI: reference/cli.md
  - Blog: blog/

# Validation
validation:
  nav:
    omitted_files: warn
    not_found: warn
  links:
    absolute_links: warn
    unrecognized_links: warn
    anchors: warn
```
