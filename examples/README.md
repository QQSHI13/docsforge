# DocsForge examples & showcase

Curated examples and links for DocsForge. Everything under `examples/` is
**built in CI** — if an example breaks, the tests catch it.

## Official examples (in this repo)

| Example | What it shows | How to run |
|---|---|---|
| [`plugins/reading-time`](plugins/reading-time/) | A complete plugin: `BasePlugin` + `Config` options, exposing `{{ reading_time }}` to templates | `pip install -e examples/plugins/reading-time` |
| [`plugins/last-modified`](plugins/last-modified/) | `on_page_markdown` pattern: set `page.meta['last_modified']` from the source mtime | `pip install -e examples/plugins/last-modified` |
| [`plugins/custom-filter`](plugins/custom-filter/) | `on_env` pattern: register a custom Jinja filter (`{{ n | pluralize("comment") }}`) | `pip install -e examples/plugins/custom-filter` |
| [`hooks/hook_draft_banner.py`](hooks/hook_draft_banner.py) | Single-file hook (no packaging) via the `hooks:` config key | see the file header |
| [`site/docsforge-demo`](site/docsforge-demo/) | A complete site: config, nav, blog, tags, TikZ diagrams, math, **and a `custom_dir` override** | `docsforge build` in that directory |

The plugin API is documented in
[`docs/docs/advanced/plugin-development.md`](../docs/docs/advanced/plugin-development.md).

## Community showcase

Open a PR to add your project, plugin, or override here (one table row:
name, one-line description, link).

### Projects built with DocsForge

| Project | Description | Link |
|---|---|---|
| DocsForge Demo | The official demo site (source in this repo) | https://docsforge-demo.pages.dev |

### Community plugins

| Plugin | Description | Link |
|---|---|---|
| _(add yours)_ | | |

### Community overrides & themes

| Override | Description | Link |
|---|---|---|
| _(add yours)_ | | |
