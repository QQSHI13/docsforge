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

---

## Theme settings

In DocsForge, theme settings are **top-level keys** — there is no `theme:` wrapper (unlike MkDocs).

### `palette`

Color scheme configuration. Supports light/dark mode toggling.

```yaml
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

### `features`

Navigation and UI features to enable.

```yaml
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

| Feature | Description |
|---------|-------------|
| `navigation.tabs` | Top-level navigation tabs |
| `navigation.sections` | Section pages in sidebar |
| `navigation.expand` | Expand all sections by default |
| `navigation.path` | Breadcrumb navigation |
| `navigation.top` | Back-to-top button |
| `navigation.footer` | Previous/next footer links |
| `search.suggest` | Search suggestions in header |
| `search.highlight` | Highlight search terms in results |
| `search.share` | Share search query links |
| `content.tabs.link` | Link content tabs across pages |
| `content.code.copy` | Copy button on code blocks |
| `content.code.annotate` | Code annotations |
| `content.action.edit` | Edit page button |
| `content.action.view` | View source button |
| `header.autohide` | Auto-hide header on scroll |
| `announce.dismiss` | Dismissible announcement bar |

---

### `icon`

Icon configuration for various UI elements.

```yaml
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

### `logo`

Path to your site logo (relative to `docs_dir`).

```yaml
logo: assets/logo.svg
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `favicon`

Path to favicon (relative to `docs_dir`).

```yaml
favicon: assets/favicon.png
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `null` | No |

---

### `language`

Site language for internationalization.

```yaml
language: en
```

| Type | Default | Required |
|------|---------|----------|
| `string` | `en` | No |

---

### `direction`

Text direction.

```yaml
direction: ltr
```

| Type | Default | Options |
|------|---------|---------|
| `string` | `ltr` | `ltr`, `rtl` |

---

### `custom_dir`

Directory for custom templates and overrides (relative to `docs_dir`).

```yaml
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
  minify:
    minify_html: true
```

#### `search` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `lang` | `string` | `en` | Search language for stemming |
| `separator` | `string` | `[\s\-]+` | Word separator regex |
| `pipeline` | `list` | `[trimmer, stopWordFilter, stemmer]` | Processing pipeline |
| `min_search_length` | `integer` | `3` | Minimum query length |
| `prebuild_index` | `boolean` | `false` | Prebuild Lunr index |
| `index_dynamics` | `boolean` | `false` | Dynamic index updates |

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

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `minify_html` | `boolean` | `true` | Minify HTML output |
| `minify_css` | `boolean` | `true` | Minify CSS |
| `minify_js` | `boolean` | `true` | Minify JavaScript |
| `cache_busting` | `boolean` | `true` | Add cache-busting hashes |
| `htmlmin_opts` | `object` | `{}` | Extra htmlmin options |

#### `privacy` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `assets` | `boolean` | `true` | Download external assets |
| `assets_dir` | `string` | `assets/externals` | Storage directory |
| `concurrency` | `integer` | `1` | Download concurrency |
| `enabled` | `boolean` | `true` | Enable plugin |
| `extra_modules` | `list` | `[]` | Extra modules to download |
| `extra_requests` | `list` | `[]` | Extra requests to download |
| `log` | `boolean` | `true` | Log downloads |
| `externals` | `list` | `[]` | External URLs to cache |
| `externals_dir` | `string` | `assets/externals` | Cache directory |

#### `info` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | Enable info banner |
| `enabled_on_home` | `boolean` | `false` | Show on home page |

#### `meta` plugin

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `meta_file` | `string` | `.meta.yml` | Metadata file |
| `enabled` | `boolean` | `true` | Enable plugin |

---

## Markdown extensions

DocsForge enables most common extensions by default. Only configure if you need custom behavior.

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
| `smarty` | No | Smart quotes and dashes |
| `sane_lists` | No | Strict list nesting |
| `wikilinks` | No | Wiki-style links |

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

### `extra.version`

Version information.

```yaml
extra:
  version:
    provider: mike
    default: stable
```

| Option | Type | Description |
|--------|------|-------------|
| `provider` | `string` | Version provider: `mike` |
| `default` | `string` | Default version label |
| `alias` | `boolean` | Enable version aliases |

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

### `extra.discussion`

Comment system integration.

```yaml
extra:
  discussion:
    enabled: true
    provider: giscus
    repo: example/discussions
    category: General
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

Link and anchor validation.

```yaml
validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `omitted_files` | `string` | `warn` | Files not in `nav` |
| `absolute_links` | `string` | `warn` | Absolute link warnings |
| `unrecognized_links` | `string` | `warn` | Unknown link warnings |
| `anchors` | `string` | `warn` | Missing anchor warnings |

Values: `warn`, `ignore`, `strict`.

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
favicon: assets/favicon.png
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
  version:
    provider: mike
    default: stable
  annotate:
    json: [.s2]

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
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn
```
