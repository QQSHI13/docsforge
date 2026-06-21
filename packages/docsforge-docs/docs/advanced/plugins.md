# Custom Plugins

DocsForge supports custom plugins using its own plugin API (similar to MkDocs but with a different base class).

## Plugin Structure

A DocsForge plugin is a Python class that extends `docsforge.core.plugin_base.BasePlugin`:

```python
from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config
from docsforge.config_options import Type

class MyPluginConfig(Config):
    enabled = Type(bool, default=True)
    api_key = Optional(Type(str))

class MyPlugin(BasePlugin[MyPluginConfig]):
    def on_page_markdown(self, markdown, *, page, config, files):
        # Modify markdown content before rendering
        return markdown

    def on_page_content(self, html, *, page, config, files):
        # Modify rendered HTML
        return html
```

## Plugin Events

| Event | When | Signature |
|-------|------|-----------|
| `on_startup` | CLI starts (build/serve) | `(command, dirty)` |
| `on_config` | Config loaded | `(config)` |
| `on_pre_build` | Before building pages | `(config)` |
| `on_page_markdown` | Each page's markdown | `(markdown, *, page, config, files)` |
| `on_page_content` | Each page's rendered HTML | `(html, *, page, config, files)` |
| `on_page_context` | Template context | `(context, *, page, config)` |
| `on_post_build` | After all pages built | `(config)` |
| `on_serve` | Dev server starts | `(server, *, config, builder)` |
| `on_shutdown` | Build/serve ends | `()` |
| `on_build_error` | Build error occurs | `(error)` |

## Registering

Declare your plugin in `docsforge.yml`:

```yaml
plugins:
  - myplugin
```

DocsForge discovers plugins via entry points or direct imports. For custom plugins, place them in your project's root and import them:

```python
# mkdocs_plugin.py in your project root
from docsforge.core.plugin_base import BasePlugin
```

Then reference them by module path in the config.

## Example: Reading Time Estimator

```python
import re
from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config

class ReadingTimeConfig(Config):
    wpm = Type(int, default=200)

class ReadingTimePlugin(BasePlugin[ReadingTimeConfig]):
    def on_page_context(self, context, *, page, config):
        if page.markdown:
            words = len(re.findall(r'\w+', page.markdown))
            minutes = max(1, round(words / self.config.wpm))
            context['reading_time'] = minutes
```

## Example: Last Modified Badge

```python
import os, datetime
from docsforge.core.plugin_base import BasePlugin

class LastModifiedPlugin(BasePlugin):
    def on_page_context(self, context, *, page, config):
        mtime = os.path.getmtime(page.file.abs_src_path)
        context['last_modified'] = datetime.date.fromtimestamp(mtime)
```

## Full API Reference

For the complete API, see the [plugin base class source](https://github.com/QQSHI13/docsforge/blob/main/packages/docsforge/docsforge/core/plugin_base.py) and [config options](https://github.com/QQSHI13/docsforge/blob/main/packages/docsforge/docsforge/config_options.py).
