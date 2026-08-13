---
icon: material/developer-board
---

# Plugin Development

This guide covers **authoring, packaging, and distributing** a DocsForge plugin. For the event API reference, see [Custom Plugins](plugins.md); for complete runnable examples, see the `examples/plugins/` directory in the repo.

DocsForge's plugin API is a superset of MkDocs' — most MkDocs plugins work with minor adjustments (different base-class import path and config descriptors). If you're migrating a MkDocs plugin, see [Migrating from MkDocs](../getting-started/migrating-from-mkdocs.md).

## Two ways to load a plugin

### 1. Hooks — local, no packaging

For quick experimentation, list a Python file under `hooks:`. The **module itself** acts as the plugin instance: define `on_*` functions at module level.

```yaml
hooks:
  - docs/assets/draft_banner.py   # path relative to docs_dir
```

```python
# docs/assets/draft_banner.py
def on_page_markdown(markdown, *, page, config, files):
    if "draft" in (page.file.src_uri or "").lower():
        return '!!! warning "DRAFT"\n    Not finalized.\n\n' + markdown
    return markdown
```

See `examples/plugins/hook_draft_banner.py`. Hooks are great for project-specific behavior; for anything reusable, package it.

### 2. Packaged plugins — distributable

A plugin is a Python package that declares an entry point in the `docsforge.plugins` group. Users reference it by name:

```yaml
plugins:
  - reading-time:
      wpm: 200
```

## Anatomy of a plugin

A plugin is a class subclassing `BasePlugin[YourConfig]`, with a `Config` subclass declaring its options:

```python
from docsforge.config_base import Config
from docsforge.config_options import Type, Optional
from docsforge.core.plugin_base import BasePlugin

class ReadingTimeConfig(Config):
    wpm = Type(int, default=200)
    label = Optional(Type(str))

class ReadingTimePlugin(BasePlugin[ReadingTimeConfig]):
    config_class = ReadingTimeConfig  # inferred from the type parameter, but explicit is fine

    def on_page_context(self, context, *, page, config, nav):
        import re
        words = len(re.findall(r"\w+", page.markdown or ""))
        context["reading_time"] = max(1, round(words / self.config.wpm))
```

- `self.config` is the validated `ReadingTimeConfig` instance — read `self.config.wpm` etc.
- Event handlers receive keyword args (`*, page, config, files`); the first positional arg is the thing being transformed (markdown/html). **Return the transformed value** (returning `None` keeps the input unchanged).
- The full event list and signatures are in [Custom Plugins → Plugin Events](plugins.md#plugin-events).

## Packaging

`pyproject.toml` with the entry point — this is the part that makes DocsForge discover your plugin:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "docsforge-reading-time"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["docsforge >= 11.0"]

[project.entry-points."docsforge.plugins"]
"reading-time" = "reading_time:ReadingTimePlugin"
```

The entry-point **name** (`"reading-time"`) is what users put in `plugins:`. The value (`"reading_time:ReadingTimePlugin"`) is `module:Class`.

## The dev loop

```bash
# from the monorepo
pip install -e examples/plugins/reading-time

# in your docs project
docsforge serve          # edit the plugin, save, livereload rebuilds
```

Because the install is editable, changes to the plugin take effect on the next rebuild without reinstalling.

## Overriding a core plugin

A third-party plugin can override a built-in one by registering under the same name (e.g. `"search"`). DocsForge gives precedence to non-core entry points over the built-ins under `docsforge.*`.

## Testing

Unit-test a plugin like any Python class — construct it, `load_config({})`, call the event handler with a stand-in `page`:

```python
from types import SimpleNamespace
from reading_time import ReadingTimePlugin

def test_reading_time():
    p = ReadingTimePlugin()
    p.load_config({"wpm": 100})
    ctx = {}
    page = SimpleNamespace(markdown="one two three four five")
    p.on_page_context(ctx, page=page, config=None, nav=None)
    assert ctx["reading_time"] == 1  # 5 words / 100 wpm rounds to 1
```

For end-to-end tests, build a fixture site with the plugin enabled and assert on the built HTML — see `tests/integration/test_build_e2e.py` for the pattern.

## Publishing

```bash
pip install build
python -m build
twine upload dist/*        # or: GitHub Actions with trusted publishing
```

Name your package `docsforge-*` so it's discoverable. List it in your plugin's README with the `plugins:` snippet.

## Reference examples

| Example | What it shows | Location |
|---------|---------------|----------|
| Reading time | `BasePlugin[Config]`, `on_page_context`, packaging | `examples/plugins/reading-time/` |
| Last modified | `on_page_markdown`, `page.meta`, file mtime | `examples/plugins/last-modified/` |
| Draft banner (hook) | Single-file hook, no packaging | `examples/plugins/hook_draft_banner.py` |

## API reference

- [Plugin base class](https://github.com/QQSHI13/docsforge/blob/main/docsforge/core/plugin_base.py)
- [Config options](https://github.com/QQSHI13/docsforge/blob/main/docsforge/config_options.py)
- [Built-in plugins](https://github.com/QQSHI13/docsforge/tree/main/docsforge/core/) — `search`, `blog`, `tags`, `meta`, `privacy`, `minify`, `info` are production-grade reference implementations.
