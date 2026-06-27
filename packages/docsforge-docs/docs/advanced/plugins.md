# Custom Plugins

DocsForge supports custom plugins using its own plugin API (similar to MkDocs but with a different base class).

## What's a Plugin?

A plugin hooks into the documentation build pipeline to modify content, add data, generate files, or integrate with external services. Unlike [Markdown extensions](../reference/configuration.md#markdown-extensions) which add new syntax, plugins operate at a higher level — they can see all pages, modify the navigation, add templates, or run post-build tasks.

## Plugin Structure

A DocsForge plugin is a Python class that extends `docsforge.core.plugin_base.BasePlugin`:

```python
from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config
from docsforge.config_options import Type, Optional

class MyPluginConfig(Config):
    """Configuration for your plugin (read from docsforge.yml)."""
    enabled = Type(bool, default=True)
    api_key = Optional(Type(str))

class MyPlugin(BasePlugin[MyPluginConfig]):
    """
    A plugin that does something on every page.
    
    The config type parameter tells DocsForge what config class to use.
    """
    
    def on_page_markdown(self, markdown, *, page, config, files):
        # Modify markdown content before rendering
        return markdown

    def on_page_content(self, html, *, page, config, files):
        # Modify rendered HTML
        return html
```

## Configuration

Users configure your plugin in `docsforge.yml` under `plugins:`:

```yaml
plugins:
  - myplugin:
      api_key: sk-abc123
```

## Plugin Events

| Event | When | Signature | Return |
|-------|------|-----------|--------|
| `on_startup` | CLI starts (build/serve) | `(command, dirty)` | `None` |
| `on_config` | Config loaded | `(config)` | `None` |
| `on_pre_build` | Before building pages | `(config)` | `None` |
| `on_page_markdown` | Each page's markdown | `(markdown, *, page, config, files)` | `str` |
| `on_page_content` | Each page's rendered HTML | `(html, *, page, config, files)` | `str` |
| `on_page_context` | Template context | `(context, *, page, config)` | `None` |
| `on_post_build` | After all pages built | `(config)` | `None` |
| `on_serve` | Dev server starts | `(server, *, config, builder)` | `server` |
| `on_shutdown` | Build/serve ends | `()` | `None` |
| `on_build_error` | Build error occurs | `(error)` | `None` |

## Event Details

### `on_page_markdown`
Called for every Markdown page before it's rendered. The `markdown` parameter is the raw Markdown content as a string. Return the modified Markdown. If you return `None`, the original Markdown is used unchanged.

```python
def on_page_markdown(self, markdown, *, page, config, files):
    # Prepend a warning banner to every page
    return "> :material-alert: This is a draft\n\n" + markdown
```

### `on_page_content`
Called after the Markdown is rendered to HTML. The `html` parameter is the rendered HTML string. Return the modified HTML.

```python
def on_page_content(self, html, *, page, config, files):
    # Add a custom footer to every page
    return html + "<footer>Custom footer</footer>"
```

### `on_page_context`
Called when building the template context for a page. The `context` is a dict that you can modify to add variables available in templates.

```python
def on_page_context(self, context, *, page, config):
    context['my_custom_var'] = 'hello'
```

### `on_serve`
Called when the dev server starts. The `server` is a `LiveReloadServer` instance. You can watch additional files for live reload:

```python
def on_serve(self, server, *, config, builder):
    server.watch('/path/to/extra/files')
    return server
```

## Examples

### Reading Time Estimator

```python
import re
from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config
from docsforge.config_options import Type

class ReadingTimeConfig(Config):
    wpm = Type(int, default=200)

class ReadingTimePlugin(BasePlugin[ReadingTimeConfig]):
    def on_page_context(self, context, *, page, config):
        if page.markdown:
            words = len(re.findall(r'\w+', page.markdown))
            minutes = max(1, round(words / self.config.wpm))
            context['reading_time'] = minutes
```

Use in templates: `{{ reading_time }} min read`

### Last Modified Badge

```python
import os, datetime
from docsforge.core.plugin_base import BasePlugin

class LastModifiedPlugin(BasePlugin):
    def on_page_context(self, context, *, page, config):
        mtime = os.path.getmtime(page.file.abs_src_path)
        context['last_modified'] = datetime.date.fromtimestamp(mtime)
```

### Add Analytics to All Pages

```python
from docsforge.core.plugin_base import BasePlugin

class AnalyticsPlugin(BasePlugin):
    def on_page_content(self, html, *, page, config, files):
        tag = '<script defer src="https://analytics.example.com/script.js"></script>'
        return html.replace('</head>', f'{tag}\n</head>')
```

## Loading a plugin

There are two ways to make a custom plugin available — see [Plugin Development](plugin-development.md) for the full walkthrough:

- **Hooks** (local, no packaging): list a Python file under `hooks:`. The module's `on_*` functions act as event handlers.
- **Packaged** (distributable): register an entry point in the `docsforge.plugins` group and reference it by name under `plugins:`.

## Full API Reference

For the complete API, see:

- [Plugin base class](https://github.com/QQSHI13/docsforge/blob/main/packages/docsforge/docsforge/core/plugin_base.py)
- [Config options](https://github.com/QQSHI13/docsforge/blob/main/packages/docsforge/docsforge/config_options.py)
- [Built-in plugins](https://github.com/QQSHI13/docsforge/tree/main/packages/docsforge/docsforge/core/) for reference implementations
