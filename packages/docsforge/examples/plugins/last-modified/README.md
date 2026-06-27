# Last-modified — example DocsForge plugin

Sets `page.meta['last_modified']` from each source file's mtime, formatted
with a configurable date format, so templates can render a "last updated" date.

## Install

```bash
pip install -e packages/docsforge/examples/plugins/last-modified
```

## Use

```yaml
plugins:
  - last-modified:
      date_format: "%b %d, %Y"
```

In a template:

```jinja
{% if page.meta.last_modified %}
  <span class="last-modified">Updated {{ page.meta.last_modified }}</span>
{% endif %}
```
