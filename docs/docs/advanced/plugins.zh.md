---
icon: material/puzzle-outline
---

# 自定义插件

DocsForge 支持通过自身的插件 API 使用自定义插件（与 MkDocs 类似，但基类不同）。

## 什么是插件？

插件可以接入文档构建流水线，用于修改内容、添加数据、生成文件或与外部服务集成。与新增语法的 [Markdown 扩展](../reference/configuration.md#markdown-extensions) 不同，插件在更高层面运行——它们可以看到所有页面、修改导航、添加模板，或执行构建后任务。

## 插件结构

DocsForge 插件是一个继承自 `docsforge.core.plugin_base.BasePlugin` 的 Python 类：

```python
from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config
from docsforge.config_options import Type, Optional

class MyPluginConfig(Config):
    """从 docsforge.yml 读取的插件配置。"""
    enabled = Type(bool, default=True)
    api_key = Optional(Type(str))

class MyPlugin(BasePlugin[MyPluginConfig]):
    """
    一个对每页执行某些操作的插件。

    配置类型参数告诉 DocsForge 使用哪个配置类。
    """

    def on_page_markdown(self, markdown, *, page, config, files):
        # 在渲染前修改 Markdown 内容
        return markdown

    def on_page_content(self, html, *, page, config, files):
        # 修改渲染后的 HTML
        return html
```

## 配置

用户在 `docsforge.yml` 的 `plugins:` 下配置你的插件：

```yaml
plugins:
  - myplugin:
      api_key: sk-abc123
```

## 插件事件

| 事件 | 触发时机 | 签名 | 返回值 |
|------|---------|------|--------|
| `on_startup` | CLI 启动时（build/serve） | `(command, dirty)` | `None` |
| `on_config` | 配置加载后 | `(config)` | `None` |
| `on_pre_build` | 构建页面前 | `(config)` | `None` |
| `on_page_markdown` | 每页的 Markdown | `(markdown, *, page, config, files)` | `str` |
| `on_page_content` | 每页渲染后的 HTML | `(html, *, page, config, files)` | `str` |
| `on_page_context` | 模板上下文 | `(context, *, page, config)` | `None` |
| `on_post_build` | 所有页面构建完成后 | `(config)` | `None` |
| `on_page_deps` | 每页渲染前 | `(deps, *, page, files, config)` | `list` |
| `on_serve` | 开发服务器启动时 | `(server, *, config, builder)` | `server` |
| `on_shutdown` | 构建/服务结束时 | `()` | `None` |
| `on_build_error` | 发生构建错误时 | `(error)` | `None` |
| `on_build_done` | 所有输出（含 SW/清单）完成后 —— 仅成功构建 | `(config)` | `None` |

## 事件详情

### `on_page_markdown`

在每个 Markdown 页面渲染前调用。`markdown` 参数是原始 Markdown 内容字符串。返回修改后的 Markdown。如果返回 `None`，则使用原始 Markdown 不变。

```python
def on_page_markdown(self, markdown, *, page, config, files):
    # 在每页顶部添加警告横幅
    return "> :material-alert: This is a draft\n\n" + markdown
```

### `on_page_content`

在 Markdown 渲染为 HTML 后调用。`html` 参数是渲染后的 HTML 字符串。返回修改后的 HTML。

```python
def on_page_content(self, html, *, page, config, files):
    # 为每页添加自定义页脚
    return html + "<footer>Custom footer</footer>"
```

### `on_page_context`

在构建页面的模板上下文时调用。`context` 是一个字典，你可以修改它以添加模板中可用的变量。

```python
def on_page_context(self, context, *, page, config):
    context['my_custom_var'] = 'hello'
```

### `on_serve`

在开发服务器启动时调用。`server` 是一个 `LiveReloadServer` 实例。你可以监视额外文件以实现实时重载：

```python
def on_serve(self, server, *, config, builder):
    server.watch('/path/to/extra/files')
    return server
```

## 示例

### 阅读时间估算

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

在模板中使用：`{{ reading_time }} min read`

### 最后修改徽章

```python
import os, datetime
from docsforge.core.plugin_base import BasePlugin

class LastModifiedPlugin(BasePlugin):
    def on_page_context(self, context, *, page, config):
        mtime = os.path.getmtime(page.file.abs_src_path)
        context['last_modified'] = datetime.date.fromtimestamp(mtime)
```

### 为所有页面添加分析

```python
from docsforge.core.plugin_base import BasePlugin

class AnalyticsPlugin(BasePlugin):
    def on_page_content(self, html, *, page, config, files):
        tag = '<script defer src="https://analytics.example.com/script.js"></script>'
        return html.replace('</head>', f'{tag}\n</head>')
```

## 加载插件

有两种方式可以让自定义插件可用——完整步骤请参见 [插件开发](plugin-development.md)：

- **Hooks**（本地，无需打包）：在 `hooks:` 下列出一个 Python 文件。该模块中的 `on_*` 函数将作为事件处理程序。
- **Packaged**（可分发）：在 `docsforge.plugins` 组中注册入口点，然后在 `plugins:` 下通过名称引用。

## 完整 API 参考

完整的 API 请参见：

- [Plugin base class](https://github.com/QQSHI13/docsforge/blob/main/docsforge/core/plugin_base.py)
- [Config options](https://github.com/QQSHI13/docsforge/blob/main/docsforge/config_options.py)
- [Built-in plugins](https://github.com/QQSHI13/docsforge/tree/main/docsforge/core/) 作为参考实现
