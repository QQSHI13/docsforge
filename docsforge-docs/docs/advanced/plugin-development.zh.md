# 插件开发

本指南涵盖 **DocsForge 插件的编写、打包和分发**。有关事件 API 参考，请参阅 [自定义插件](plugins.md)；完整可运行示例请参见仓库中的 `examples/plugins/` 目录。

DocsForge 的插件 API 是 MkDocs 插件 API 的超集——大多数 MkDocs 插件只需稍作调整即可使用（不同的基类导入路径和配置描述符）。如果你要迁移 MkDocs 插件，请参阅 [从 MkDocs 迁移](../getting-started/migrating-from-mkdocs.md)。

## 加载插件的两种方式

### 1. Hooks — 本地，无需打包

想要快速试验，可以在 `hooks:` 下列出一个 Python 文件。模块本身即作为插件实例：在模块级别定义 `on_*` 函数。

```yaml
hooks:
  - docs/assets/draft_banner.py   # 相对于 docs_dir 的路径
```

```python
# docs/assets/draft_banner.py
def on_page_markdown(markdown, *, page, config, files):
    if "draft" in (page.file.src_uri or "").lower():
        return '!!! warning "DRAFT"\n    Not finalized.\n\n' + markdown
    return markdown
```

参见 `examples/plugins/hook_draft_banner.py`。Hooks 适用于项目专属行为；任何可复用功能都应打包为插件。

### 2. Packaged plugins — 可分发

插件是一个在 `docsforge.plugins` 组中声明入口点的 Python 包。用户通过名称引用它：

```yaml
plugins:
  - reading-time:
      wpm: 200
```

## 插件结构

插件是一个继承自 `BasePlugin[YourConfig]` 的类，并通过 `Config` 子类声明其选项：

```python
from docsforge.config_base import Config
from docsforge.config_options import Type, Optional
from docsforge.core.plugin_base import BasePlugin

class ReadingTimeConfig(Config):
    wpm = Type(int, default=200)
    label = Optional(Type(str))

class ReadingTimePlugin(BasePlugin[ReadingTimeConfig]):
    config_class = ReadingTimeConfig  # 从类型参数推断得出，但显式声明亦可

    def on_page_context(self, context, *, page, config, nav):
        import re
        words = len(re.findall(r"\w+", page.markdown or ""))
        context["reading_time"] = max(1, round(words / self.config.wpm))
```

- `self.config` 是已验证的 `ReadingTimeConfig` 实例——通过 `self.config.wpm` 等读取。
- 事件处理函数接收关键字参数（`*, page, config, files`）；第一个位置参数是要被转换的内容（markdown/html）。**返回转换后的值**（返回 `None` 表示保持输入不变）。
- 完整事件列表及签名请参阅 [自定义插件 → 插件事件](plugins.md#plugin-events)。

## 打包

使用 `pyproject.toml` 声明入口点——这是让 DocsForge 发现你插件的关键部分：

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

入口点名称（`"reading-time"`）是用户在 `plugins:` 中使用的名称。值（`"reading_time:ReadingTimePlugin"`）表示 `module:Class`。

## 开发循环

```bash
# 在 monorepo 中
pip install -e examples/plugins/reading-time

# 在你的文档项目中
docsforge serve          # 编辑插件，保存，实时重载会重新构建
```

因为安装方式是可编辑（editable）的，插件改动会在下次重建时生效，无需重新安装。

## 覆盖核心插件

第三方插件可以通过注册相同名称（例如 `"search"`）来覆盖内置插件。DocsForge 会优先选择非核心入口点，而非 `docsforge.*` 下的内置插件。

## 测试

像测试普通 Python 类一样对插件进行单元测试——构造实例、调用 `load_config({})`、使用替代 `page` 调用事件处理函数：

```python
from types import SimpleNamespace
from reading_time import ReadingTimePlugin

def test_reading_time():
    p = ReadingTimePlugin()
    p.load_config({"wpm": 100})
    ctx = {}
    page = SimpleNamespace(markdown="one two three four five")
    p.on_page_context(ctx, page=page, config=None, nav=None)
    assert ctx["reading_time"] == 1  # 5 个单词 / 100 wpm 四舍五入为 1
```

端到端测试则构建一个启用该插件的 fixture 站点，并对构建出的 HTML 进行断言——示例模式请参见 `tests/integration/test_build_e2e.py`。

## 发布

```bash
pip install build
python -m build
twine upload dist/*        # 或：使用 GitHub Actions 进行可信发布
```

将包命名为 `docsforge-*`，以便被发现。在插件的 README 中列出 `plugins:` 代码片段。

## 示例参考

| 示例 | 说明 | 位置 |
|---------|---------------|----------|
| Reading time | `BasePlugin[Config]`、`on_page_context`、打包 | `examples/plugins/reading-time/` |
| Last modified | `on_page_markdown`、`page.meta`、文件 mtime | `examples/plugins/last-modified/` |
| Draft banner (hook) | 单文件 hook，无需打包 | `examples/plugins/hook_draft_banner.py` |

## API 参考

- [插件基类](https://github.com/QQSHI13/docsforge/blob/main/docsforge/core/plugin_base.py)
- [配置选项](https://github.com/QQSHI13/docsforge/blob/main/docsforge/config_options.py)
- [内置插件](https://github.com/QQSHI13/docsforge/tree/main/docsforge/core/) — `search`、`blog`、`tags`、`meta`、`privacy`、`minify`、`info` 均为生产级参考实现。
