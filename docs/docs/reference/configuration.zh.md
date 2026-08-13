---
icon: material/tune-variant
---

# 配置参考

本页面记录 `docsforge.yml` 中可用的每个选项。自定义站点时，请将其作为完整参考。

---

## 顶层设置

### `site_name`

文档站点的标题。显示在页眉、浏览器标签页和社交卡片中。

```yaml
site_name: My Documentation
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | — | 是 |

---

### `site_url`

站点托管的规范 URL。用于社交卡片、RSS 订阅源和绝对链接生成。

```yaml
site_url: https://example.com/docs/
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

!!! tip "尾部斜杠"
    始终包含尾部斜杠以保持一致：
    ```yaml
    site_url: https://example.com/docs/  # 推荐
    site_url: https://example.com/docs   # 避免
    ```

---

### `site_author`

作者姓名。用于元数据和 RSS 订阅源。

```yaml
site_author: Jane Doe
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `site_description`

站点简短描述。用于元标签和社交卡片。

```yaml
site_description: Documentation for the Example Platform
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `copyright`

页脚显示的版权信息。

```yaml
copyright: Copyright &copy; 2025 Example Inc.
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `repo_url`

源代码仓库 URL。在页眉中添加指向仓库的编辑图标。

```yaml
repo_url: https://github.com/example/docs
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `repo_name`

仓库链接的显示名称。默认为 `repo_url` 的最后一段路径。

```yaml
repo_name: example/docs
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | 自动 | 否 |

---

### `edit_uri`

“编辑此页”链接的路径后缀。与 `repo_url` 组合成完整编辑 URL。

```yaml
edit_uri: edit/main/docs/
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `strict`

设置为 `true` 时，警告会被视为错误，构建失败。

```yaml
strict: true
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `boolean` | `false` | 否 |

---

### `dev_addr`

开发服务器地址。

```yaml
dev_addr: 127.0.0.1:8000
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `127.0.0.1:8000` | 否 |

---

### `use_directory_urls`

设置为 `true`（默认）时，页面构建为 `page/index.html` 而非 `page.html`。这会生成更简洁的 URL（`/page/` 而非 `/page.html`）。

```yaml
use_directory_urls: true
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `boolean` | `true` | 否 |

---

### `docs_dir`

包含 Markdown 源文件的目录。

```yaml
docs_dir: docs
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `docs` | 否 |

---

### `site_dir`

构建站点输出的目录。

```yaml
site_dir: site
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `site` | 否 |

---

### `extra_css`

额外包含的 CSS 文件。路径相对于 `docs_dir`。

```yaml
extra_css:
  - stylesheets/custom.css
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `list` | `[]` | 否 |

---

### `extra_javascript`

额外包含的 JavaScript 文件。路径相对于 `docs_dir`。

```yaml
extra_javascript:
  - javascripts/analytics.js
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `list` | `[]` | 否 |

!!! warning "不要包含已内置的资源"
    不要在此处包含 KaTeX、Mermaid 或 Material Icons。它们已内置。

### `extra_templates`

来自 `docs_dir` 的额外 Jinja2 模板（HTML 或 XML），使用全局上下文构建。

```yaml
extra_templates:
  - sitemap-custom.xml
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `list` | `[]` | 否 |

---

### `exclude_docs`

相对于 `docs_dir` 的 gitignore 风格模式，完全排除这些文件。

```yaml
exclude_docs: |
  private/notes.md
  drafts/**
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string`（gitignore） | — | 否 |

---

### `draft_docs`

标记为草稿的 gitignore 风格模式。草稿会构建但不会出现在导航中；`docsforge serve` 仍会渲染它们。

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string`（gitignore） | — | 否 |

---

### `not_in_nav`

有意不放在导航中的文件的 gitignore 风格模式。可为这些文件抑制“未包含在导航中”的警告。

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string`（gitignore） | — | 否 |

---

### `tikz`

启用 TikZ 图表编译。`docs_dir` 下包含 `\begin{tikzpicture}`（或位于 `tikz/` 目录）的 `.tex` 文件会在构建时编译为 SVG。需要 LaTeX 工具链（`latex`/`pdflatex` + `dvisvgm`/`pdf2svg`）；不可用时构建会警告并跳过编译。

```yaml
tikz: true
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `boolean` | `null`（自动） | 否 |

---

### `hooks`

作为插件加载的 Python 模块文件。每个钩子都拥有完整的插件事件 API（参见[自定义插件](../advanced/plugins.md)）—— 例如用 `on_build_done` 在构建后处理 `site/sw.js`。

```yaml
hooks:
  - my_hook.py
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `list` | `[]` | 否 |

---

### `watch`

运行 `docsforge serve` 时额外监视的路径（文件或目录）。

```yaml
watch:
  - ../shared-content
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `list` | `[]` | 否 |

---

### `remote_branch` / `remote_name`

为兼容配置而保留的旧版 MkDocs 选项。DocsForge 没有 `gh-deploy` 命令 —— 请改用 GitHub Actions 部署（参见[发布你的站点](../publishing-your-site.md)）。它们会被接受但不会使用。

| 键 | 默认值 |
|-----|---------|
| `remote_branch` | `gh-pages` |
| `remote_name` | `origin` |

---

## 主题设置

主题设置位于 `theme:` 块下，与 DocsForge Material 相同。

```yaml
theme:
  name: material
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
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
  logo: assets/logo.svg
  favicon: assets/favicon.svg
  icon:
    repo: fontawesome/brands/github
```

### `theme.name`

要使用的主题。DocsForge 内置 Material，因此通常是 `material`。

```yaml
theme:
  name: material
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `material` | 否 |

---

### `theme.palette`

配色方案配置。支持浅色/深色模式切换。

```yaml
theme:
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

| 属性 | 类型 | 描述 |
|----------|------|-------------|
| `media` | `string` | 自动切换的 CSS 媒体查询 |
| `scheme` | `string` | 配色方案：`default` 或 `slate` |
| `primary` | `string` | 主色：`red`、`pink`、`purple`、`deep-purple`、`indigo`、`blue`、`light-blue`、`cyan`、`teal`、`green`、`light-green`、`lime`、`yellow`、`amber`、`orange`、`deep-orange`、`brown`、`grey`、`blue-grey`、`black`、`white` |
| `accent` | `string` | 强调色（选项与 `primary` 相同） |
| `toggle` | `object` | 切换按钮配置 |
| `toggle.icon` | `string` | 图标标识符 |
| `toggle.name` | `string` | 工具提示文本 |

---

### `theme.features`

要启用的导航和 UI 功能。

```yaml
theme:
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

| 功能 | 描述 |
|---------|-------------|
| `navigation.tabs` | 顶层导航标签页 |
| `navigation.sections` | 侧边栏中的章节页面 |
| `navigation.expand` | 默认展开所有章节 |
| `navigation.path` | 面包屑导航 |
| `navigation.top` | 返回顶部按钮 |
| `navigation.footer` | 上一页/下一页页脚链接 |
| `search.suggest` | 页眉中的搜索建议 |
| `search.highlight` | 结果中高亮搜索词 |
| `search.share` | 分享搜索查询链接 |
| `content.tabs.link` | 跨页面链接内容标签页 |
| `content.code.copy` | 代码块上的复制按钮 |
| `content.code.annotate` | 代码注释 |
| `content.action.edit` | 编辑页面按钮 |
| `content.action.view` | 查看源代码按钮 |
| `announce.dismiss` | 可关闭的公告栏 |

---

### `theme.icon`

各种 UI 元素的图标配置。

```yaml
theme:
  icon:
    repo: fontawesome/brands/github
    logo: material/library
```

| 属性 | 类型 | 描述 |
|----------|------|-------------|
| `repo` | `string` | 仓库链接图标 |
| `logo` | `string` | 徽标区域使用的图标 |
| `admonition` | `object` | 自定义提示框图标 |

---

### `theme.logo`

站点徽标路径（相对于 `docs_dir`）。

```yaml
theme:
  logo: assets/logo.svg
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `theme.favicon`

Favicon 路径（相对于 `docs_dir`）。

```yaml
theme:
  favicon: assets/favicon.svg
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

### `theme.language`

站点语言，用于国际化。

```yaml
theme:
  language: en
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `en` | 否 |

---

### `theme.direction`

文本方向。

```yaml
theme:
  direction: ltr
```

| 类型 | 默认值 | 选项 |
|------|---------|---------|
| `string` | `ltr` | `ltr`、`rtl` |

---

### `theme.custom_dir`

自定义模板和覆盖的目录（相对于 `docs_dir`）。

```yaml
theme:
  custom_dir: overrides
```

| 类型 | 默认值 | 必填 |
|------|---------|----------|
| `string` | `null` | 否 |

---

## 插件设置

DocsForge 有许多内置插件。大多数无需配置。仅在需要自定义行为时才添加设置。

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
```

#### `search` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `lang` | `string` | `en` | 搜索词干提取语言 |
| `separator` | `string` | `[\s\-]+` | 单词分隔符正则 |
| `pipeline` | `list` | `[trimmer, stopWordFilter, stemmer]` | 处理管道 |
| `jieba_dict` | `string` | `null` | 自定义 jieba 字典路径 |
| `jieba_dict_user` | `string` | `null` | 自定义 jieba 用户字典路径 |

#### `tags` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `tags_file` | `string` | `tags.md` | 标签索引页面 |
| `tags_extra_files` | `list` | `[]` | 额外标签文件 |
| `tags_hierarchy` | `boolean` | `false` | 启用标签层级 |

#### `blog` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `blog_dir` | `string` | `blog` | 博客文章目录 |
| `blog_toc` | `boolean` | `false` | 显示目录 |
| `post_date_format` | `string` | `long` | 日期格式 |
| `post_excerpt` | `string` | `optional` | 摘要行为 |
| `post_readtime` | `boolean` | `true` | 显示阅读时间 |
| `post_url_format` | `string` | `{date}/{slug}` | URL 模式 |
| `archive_date_format` | `string` | `YYYY` | 归档格式 |
| `archive_url_format` | `string` | `archive/{date}` | 归档 URL |
| `categories_url_format` | `string` | `category/{slug}` | 分类 URL |
| `pagination_url_format` | `string` | `page/{page}` | 分页 URL |
| `authors_file` | `string` | `.authors.yml` | 作者文件 |

#### `minify` 插件

minify 插件始终启用，没有可配置选项。它会压缩 HTML 页面以及任何 `extra_css` / `extra_javascript` 文件。

#### `privacy` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | 启用插件 |
| `concurrency` | `integer` | `CPU count - 1` | 下载并发数 |
| `cache_dir` | `string` | `.cache/plugin/privacy` | 本地缓存目录 |
| `assets_fetch` | `boolean` | `true` | 从网络获取外部资源 |
| `assets_fetch_dir` | `string` | `assets/external` | `site_dir` 内的存储目录 |
| `assets_include` | `list` | `[]` | 始终获取的外部 URL 通配模式 |
| `assets_exclude` | `list` | `[]` | 跳过获取的外部 URL 通配模式 |
| `assets_expr_map` | `dict` | `{}` | 在 CSS/JS 中查找资源的额外正则 |
| `links_attr_map` | `dict` | `{}` | 添加到外部链接的额外属性 |
| `links_noopener` | `boolean` | `true` | 为外部链接添加 `noopener` |

#### `info` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | 启用插件 |
| `enabled_on_serve` | `boolean` | `false` | 服务时显示 info 输出 |

#### `meta` 插件

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `meta_file` | `string` | `.meta.yml` | 元数据文件 |
| `enabled` | `boolean` | `true` | 启用插件 |

#### `i18n` 插件

多语言站点（后缀式语言变体）。插件自动加载；也可以在 `extra.i18n_languages` 下配置（参见[多语言站点](../setup/i18n.md)）。

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `languages` | `list` | `[]` | 语言列表：`locale`、`name`、`default`，可选 `site_name`、`site_description`、`nav_translations` |
| `enabled` | `boolean` | `true` | 启用插件 |

#### `social` 插件

可选的社交卡片生成（每页一个 OpenGraph PNG）。需要 `pip install docsforge[social]`（pillow + cairosvg）；参见[设置社交卡片](../setup/setting-up-social-cards.md)。

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | 启用插件 |
| `concurrency` | `integer` | CPU 数 - 1 | 并行卡片渲染 |
| `cache` | `boolean` | `true` | 缓存生成的卡片 |
| `cache_dir` | `string` | `.docsforge/cache/social` | 卡片缓存目录 |
| `cards` | `boolean` | `true` | 生成卡片 |
| `cards_dir` | `string` | `assets/images/social` | 卡片输出目录 |
| `cards_layout` | `string` | `default` | 卡片布局 |
| `cards_layout_dir` | `string` | `layouts` | 自定义布局目录 |
| `cards_layout_options` | `dict` | `{}` | `background_color`、`color`、`font_family` 等 |
| `cards_include` | `list` | `[]` | 包含的页面 glob |
| `cards_exclude` | `list` | `[]` | 排除的页面 glob |

---

## Markdown 扩展

DocsForge 默认启用大多数常见扩展 —— 36 个默认 + 3 个内置（`toc`、`tables`、`fenced_code`）。仅在需要自定义行为时才配置。

### `markdown_extensions`

```yaml
markdown_extensions:
  - toc:
      permalink: true
      title: On this page
      toc_depth: 3
```

| 扩展 | 内置 | 描述 |
|-----------|----------|-------------|
| `admonition` | 是 | 标注框（`!!! note`） |
| `pymdownx.details` | 是 | 可折叠详情（`??? question`） |
| `pymdownx.superfences` | 是 | 支持自定义围栏的代码块 |
| `fenced_code` | 是 | 标准围栏代码块 |
| `pymdownx.betterem` | 是 | 更智能的强调处理 |
| `pymdownx.highlight` | 是 | 代码语法高亮 |
| `pymdownx.inlinehilite` | 是 | 行内代码高亮 |
| `pymdownx.snippets` | 是 | 内容包含（`--8<--`） |
| `pymdownx.tabbed` | 是 | 标签页内容（`=== "Tab 1"`） |
| `pymdownx.tasklist` | 是 | 任务列表（`- [ ]`） |
| `pymdownx.emoji` | 是 | 表情和图标（`:material-check:`） |
| `pymdownx.arithmatex` | 是 | 数学渲染（`$...$`、`$$...$$`） |
| `pymdownx.keys` | 是 | 键盘按键（`++ctrl+c++`） |
| `pymdownx.mark` | 是 | 高亮文本（`==text==`） |
| `pymdownx.critic` | 是 | 批评标记 |
| `pymdownx.caret` | 是 | 上标（`^text^`） |
| `pymdownx.tilde` | 是 | 下标（`~text~`） |
| `tables` | 是 | Markdown 表格 |
| `toc` | 是 | 目录 |
| `meta` | 是 | YAML 前置元数据 |
| `def_list` | 是 | 定义列表 |
| `footnotes` | 是 | 脚注（`[^1]`） |
| `attr_list` | 是 | 属性列表（`{.class}`） |
| `md_in_html` | 是 | HTML 内的 Markdown |
| `smarty` | 否 | 智能引号和破折号 |
| `sane_lists` | 否 | 严格列表嵌套 |
| `wikilinks` | 否 | Wiki 风格链接 |

---

## Extra 设置

`extra:` 部分保存可在模板和 Markdown 中通过 `{{ extra.key }}` 访问的自定义变量。

### `extra.social`

页脚中的社交链接。

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

### `extra.alternate`

多语言站点的语言替代链接。

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

标签配置。

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

代码注释设置。

```yaml
extra:
  annotate:
    json: [.s2]
```

---

### `extra.scope`

Google Analytics / Plausible 作用域。

```yaml
extra:
  scope:
    analytics: true
    feedback: true
```

---

## 导航

### `nav`

显式导航结构。如果省略，页面会自动从 `docs_dir` 发现。

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

| 语法 | 描述 |
|--------|-------------|
| `Page Title: path.md` | 自定义标题的单个页面 |
| `Section:` | 嵌套章节 |
| `Directory/` | 自动发现目录中的页面 |
| `!include path` | 包含另一个导航文件 |

---

## 验证设置

### `validation`

链接、锚点和导航验证。

```yaml
validation:
  nav:
    omitted_files: warn
    not_found: warn
  links:
    absolute_links: warn
    unrecognized_links: warn
    anchors: warn
```

### `validation.nav`

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `omitted_files` | `string` | `info` | 不在 `nav` 中的文件 |
| `not_found` | `string` | `warn` | 导航链接指向缺失页面 |
| `absolute_links` | `string` | `info` | 绝对导航链接 |

### `validation.links`

| 选项 | 类型 | 默认值 | 描述 |
|--------|------|---------|-------------|
| `absolute_links` | `string` | `info` | 绝对 Markdown 链接 |
| `unrecognized_links` | `string` | `info` | 看起来不像内部页面的链接 |
| `not_found` | `string` | `warn` | Markdown 链接指向缺失页面 |
| `anchors` | `string` | `info` | 指向缺失锚点的链接 |

取值：`warn`、`info`、`ignore`。

---

## 完整示例

```yaml
# 站点元数据
site_name: Example Documentation
site_url: https://docs.example.com/
site_author: Example Team
site_description: Complete documentation for the Example platform
copyright: Copyright &copy; 2025 Example Inc.

# 仓库
repo_url: https://github.com/example/docs
repo_name: example/docs
edit_uri: edit/main/docs/

# 目录
docs_dir: docs
site_dir: site
use_directory_urls: true
strict: false

# 主题
theme:
  name: material
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
  favicon: assets/favicon.svg
  icon:
    repo: fontawesome/brands/github
  language: en

# 自定义资源
extra_css:
  - stylesheets/custom.css

extra_javascript:
  - javascripts/analytics.js

# 插件
plugins:
  search:
    lang: en
  tags:
    tags_file: tags.md
  blog:
    blog_dir: blog
    blog_toc: true

# 额外变量
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/example
    - icon: fontawesome/brands/twitter
      link: https://twitter.com/example

# 导航
nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Configuration: getting-started/configuration.md
  - Reference:
    - API: reference/api.md
    - CLI: reference/cli.md
  - Blog: blog/

# 验证
validation:
  nav:
    omitted_files: warn
    not_found: warn
  links:
    absolute_links: warn
    unrecognized_links: warn
    anchors: warn
```
