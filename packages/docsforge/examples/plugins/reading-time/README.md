# Reading Time — example DocsForge plugin

A minimal, fully-packaged example plugin that estimates reading time for each
page and exposes it to templates as `{{ reading_time }}`.

## Install (editable, from the monorepo)

```bash
pip install -e packages/docsforge/examples/plugins/reading-time
```

## Use

```yaml
# docsforge.yml
plugins:
  - reading-time:
      wpm: 200
```

Then in a template (e.g. a custom `partials/content.html`):

```jinja
{% if reading_time %}<span class="reading-time">{{ reading_time }} min read</span>{% endif %}
```

## Layout

This is a reference for plugin authors — it shows the four moving parts:

1. `reading_time/__init__.py` — the plugin class (`BasePlugin[Config]`) + its `Config`.
2. `pyproject.toml` — the `[project.entry-points."docsforge.plugins"]` registration that makes DocsForge discover the plugin by name.
3. `README.md` — install + usage.
4. (optional) tests.

See `docs/advanced/plugin-development.md` for a walkthrough.
