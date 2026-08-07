# docsforge-custom-filter

Example DocsForge plugin that registers a custom **Jinja filter** via the
`on_env` event.

```bash
pip install -e examples/plugins/custom-filter
```

```yaml
# docsforge.yml
plugins:
  - custom-filter
```

Then use it in any template or partial:

```jinja
{{ comments }} {{ comments | pluralize("comment") }}
{# -> "1 comment" or "3 comments" #}
```

See `custom_filter/__init__.py` for the full implementation — it is the
smallest `on_env` example: the config class, the filter function, and the
plugin wiring.
