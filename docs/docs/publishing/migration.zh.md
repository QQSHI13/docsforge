# 迁移指南

对于大多数网站来说，从 MkDocs/Material 迁移到 DocsForge 非常简单。本指南介绍哪些内容可以轻松迁移，哪些需要额外工作。

## 易于迁移（零/低工作量）

| 功能 | 状态 | 说明 |
|---------|--------|-------|
| **Markdown 内容** | :material-check-bold: 直接 | 所有 `.md` 文件可直接使用 |
| **导航 (`nav`)** | :material-check-bold: 直接 | `nav:` 部分可直接复制 |
| **主题设置** | :material-check-bold: 直接 | 颜色、字体、徽标、网站图标 |
| **额外 CSS/JS** | :material-check-bold: 直接 | `extra_css`、`extra_javascript` |
| **Markdown 扩展** | :material-check-bold: 直接 | admonition、pymdownx 等 |
| **搜索** | :material-check-bold: 直接 | 内置，无需配置 |
| **标签** | :material-check-bold: 直接 | `tags:` 插件为内置 |
| **Git 修订信息** | :material-check-bold: 直接 | Git 日期自动显示 |
| **PWA / Service Worker** | :material-check-bold: 直接 | 内置，自动生成 |
| **站点地图** | :material-check-bold: 直接 | 自动生成 |

## 需要一些工作量

| 功能 | 状态 | 迁移路径 |
|---------|--------|---------------|
| **自定义钩子** | :material-alert: 适配 | 重写为 DocsForge 插件，或如果兼容则使用 `hooks:` |
| **自定义插件** | :material-alert: 适配 | 检查 DocsForge 是否有等效功能；否则重写 |
| **自定义模板** | :material-alert: 适配 | 模板路径不同；请检查 `docsforge/templates/` |
| **Insiders 功能** | :material-alert: 适配 | 许多功能已包含在 DocsForge 中；请检查[功能对比](#feature-parity-material-vs-docsforge) |
| **Privacy 插件** | :material-alert: 内置 | DocsForge 默认包含隐私功能 |
| **Optimize 插件** | :material-alert: 内置 | 资源优化在构建后自动运行 |
| **标签布局** | :material-alert: 已更改 | 自定义标签模板从 `fragments/tags/{layout}/` 移动到 `fragments/tags/{layout}-tag.html` 和 `fragments/tags/{layout}-listing.html`（扁平化目录结构） |

## 需要大量工作量

| 功能 | 状态 | 说明 |
|---------|--------|-------|
| **构建后脚本** | :material-wrench: 自定义 | 修改已构建 HTML 的 Node.js/Python 脚本需要移植 |
| **深入的 MkDocs 内部机制** | :material-wrench: 自定义 | 对 MkDocs 类进行猴子补丁的插件 |
| **自定义扩展** | :material-wrench: 自定义 | 包含 MkDocs 特定逻辑的 Python Markdown 扩展 |

## MkDocs 插件迁移指南

MkDocs 插件与 DocsForge 不兼容。以下是常见 MkDocs 插件到 DocsForge 等效功能或替代方案的映射。

### 内置（零工作量）

这些 MkDocs 插件在 DocsForge 中都有直接的内置等效功能 — 从 `plugins:` 中移除即可自动加载：

| MkDocs 插件 | DocsForge | 说明 |
|---------------|-----------|-------|
| `search` | :material-check-bold: 内置 | Lunr.js 搜索，行为相同。从配置中移除。 |
| `tags` | :material-check-bold: 内置 | 相同的 `tags:` 前置元数据，相同的标签页面。从配置中移除。 |
| `blog` | :material-check-bold: 内置 | 包含作者、分类、归档、RSS 的博客。从配置中移除。 |
| `minify` | :material-check-bold: 内置 | HTML/CSS/JS 压缩在构建后自动运行。 |
| `meta` | :material-check-bold: 内置 | OpenGraph 元数据、社交预览。默认包含。 |
| `privacy` | :material-check-bold: 内置 | 外部资源下载和内联（Google Fonts、CDN 资源）。 |

### 配置兼容（复制插件配置）

这些 MkDocs 插件不受支持，但可以通过 DocsForge 的内置能力复制其功能：

| MkDocs 插件 | DocsForge 等效方案 |
|---------------|---------------------|
| `git-revision-date-localized` | 内置 — 每个页面自动显示 Git 修订日期 |
| `git-authors` | 内置 — 从 Git 历史中提取作者信息 |
| `macros` | 使用 Jinja2 模板或 `extra:` 配置变量 |
| `redirects` | 使用 Web 服务器重定向（Netlify `_redirects`、nginx 配置等） |
| `awesome-pages` | 省略 `nav:` 时自动发现导航；使用 `nav:` 进行显式排序 |
| `section-index` | 内置 — 分区索引页面自动生效 |
| `tooltipster-links` | 内置 — 参考链接的工具提示包含在主题中 |
| `embed-external` | 使用标准 Markdown 链接或 `pymdownx.snippets` |
| `include-markdown` | 内置 — 默认启用 `pymdownx.snippets` |
| `mkdocstrings` | 非内置；使用 `pymdownx.snippets` 或自定义构建后脚本 |

### 无直接等效方案（需要自定义工作）

| MkDocs 插件 | 替代方案 |
|---------------|-----------|
| `mkdocs-material/plugins/social` | 非内置。需要 Pillow + CairoSVG。使用 `pip install docsforge[imaging]` 安装并手动配置 `social:` 插件。 |
| `mkdocs-redirects` | 使用服务器级重定向（Cloudflare `_redirects`、nginx 等） |
| `mkdocs-awesome-pages` | 手动指定 `nav:` 结构 |
| `mkdocs-glightbox` | 图片灯箱非内置。如果主题支持，使用内置的图片缩放功能。 |
| `mkdocs-pdf-export` | 使用 `docsforge build --pdf`（参见 [PDF 导出设置](../setup/pdf-export.md)） |
| `mkdocs-static-i18n` | 使用内置的 `material/i18n` 插件（参见 [国际化设置](../setup/i18n.md)） |
| `mkdocs-video` | 在 Markdown 中使用标准 HTML `<video>` 标签 |
| `mkdocs-gallery` | 使用标准 Markdown 图片语法 |
| `mkdocs-jupyter` | 不支持。先将笔记本导出为 Markdown。 |
| `mkdocs-swagger-ui-tag` | 不支持。使用自定义插件或直接嵌入 Swagger UI HTML。 |

### 自定义 MkDocs 插件

扩展 MkDocs `BasePlugin` 类或接入 MkDocs 事件（`on_page_markdown`、`on_page_content` 等）的插件需要为 DocsForge 的插件系统重写：

1. DocsForge 使用相同的事件名称（`on_page_markdown`、`on_post_build` 等）—— 许多 MkDocs 插件只需将导入从 `mkdocs.plugins` 改为 `docsforge.core.plugin_base` 即可适配。
2. 配置模式使用 DocsForge 的 `Config` 类，而不是 MkDocs 的 `BaseConfig`。
3. 详情请参见[插件开发指南](../advanced/customization.md#custom-plugins)。

### Markdown 扩展

所有兼容 MkDocs 的 Markdown 扩展都可以直接使用。DocsForge 使用相同的 `python-markdown` 包和 `pymdown-extensions`。按原样复制您的 `markdown_extensions:` 配置块：

```yaml
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tasklist:
      custom_checkbox: true
  # ... 所有现有扩展均可保持不变
```

31 个最常用的扩展已经默认启用 — 只有需要自定义配置时才需要列出它们。

### 配置键迁移

| MkDocs / Material 键 | DocsForge | 说明 |
|-----------------------|-----------|-------|
| `mkdocs.yml` | `docsforge.yml` | 重命名文件 |
| `theme.name: material` | `theme.name: material` | 相同 — DocsForge 内置 Material |
| `theme.features` | `theme.features` | 相同 — 支持所有 Material 功能 |
| `theme.palette` | `theme.palette` | 相同 — 配色方案配置 |
| `theme.font` | `theme.font` | 相同 — 字体配置 |
| `theme.favicon` | `theme.favicon` | 相同 — 相对于 `docs_dir` |
| `theme.logo` | `theme.logo` | 相同 — 相对于 `docs_dir` |
| `theme.icon.logo` | `theme.icon.logo` | 相同 — Material 图标引用 |
| `markdown_extensions` | `markdown_extensions` | **相同** — 完全兼容 |
| `plugins` | `plugins` | **部分** — 内置插件可用；第三方插件需要移植 |
| `extra_css` | `extra_css` | 相同 |
| `extra_javascript` | `extra_javascript` | 相同 |
| `extra` | `extra` | 相同 — 自定义模板变量 |
| `site_dir` | `site_dir` | 相同 |
| `docs_dir` | `docs_dir` | 相同 |
| `hooks` | `hooks` | 相同 — 但 MkDocs 钩子格式可能不同 |
| `INHERIT` | ❌ 不支持 | 改用 YAML 锚点 |
| `validation` | `validation` | 相同 |
| `watch` | `watch` | 相同 — 服务期间额外监视的路径 |

### 已弃用 / 已移除的键

| 键 | 状态 | 替代方案 |
|-----|--------|-------------|
| `strict` | :material-check-bold: 支持 | 在配置中使用 `strict: true` 或在 CLI 中使用 `docsforge build --strict` |
| `config_file_path` | 内部 | 用户配置中不需要 |
| `site_description` | :material-check-bold: 支持 | 相同键 |
| `site_author` | :material-check-bold: 支持 | 相同键 |
| `copyright` | :material-check-bold: 支持 | 相同键 |
| `repo_url` | :material-check-bold: 支持 | 相同键 |
| `repo_name` | :material-check-bold: 支持 | 相同键 |
| `edit_uri` | :material-check-bold: 支持 | 相同键 |
| `remote_branch` | ❌ 已移除 | 使用 GitHub Actions 部署 |
| `remote_name` | ❌ 已移除 | 使用 GitHub Actions 部署 |
| `use_directory_urls` | :material-check-bold: 支持 | 相同键（默认值：true） |
| `dev_addr` | :material-check-bold: 支持 | 相同键（默认值：`127.0.0.1:8000`） |
| `site_url` | :material-check-bold: 必需 | 必须设置，用于社交卡片、站点地图、RSS |

OI Wiki 使用了一些高级功能。以下是每个功能的映射方式：

| OI Wiki 功能 | DocsForge 等效方案 | 工作量 |
|-----------------|---------------------|--------|
| `hooks/on_env.py`（nav_math 过滤器） | 自定义插件或钩子 | 中等 |
| `toggle-sidebar` 插件 | 主题自定义 | 低 |
| `document-offsets-injection` 扩展 | 内置或自定义插件 | 中等 |
| `extra: disqus` | Disqus 集成（手动） | 低 |
| `extra: pagetime` | 内置 Git 日期显示 | 无 |
| `_static/css/extra.css` | `extra_css` — 直接复制 | 无 |
| `_static/js/math-csr.js` | `extra_javascript` — 直接复制 | 无 |
| MathJax 外部 CDN | 内置 KaTeX 或 MathJax | 低 |
| 构建后 Node 脚本 | 自定义构建流程 | 高 |

### 估计迁移工作量

- **基础内容 + 样式**：< 1 小时
- **自定义钩子 + 扩展**：2–4 小时
- **构建后流程**：4–8 小时
- **完整的 OI Wiki 迁移**：熟悉两个系统的开发者约需 1–2 天

## 功能对比：Material vs DocsForge

| 功能 | Material | DocsForge |
|---------|----------|-----------|
| Material 主题 | :material-check-bold: | :material-check-bold:（已包含） |
| 搜索 | :material-check-bold: | :material-check-bold:（内置） |
| 标签 | :material-check-bold: | :material-check-bold:（内置） |
| 社交卡片 | :material-check-bold:（Insiders） | ❌ 非内置 |
| 博客 | :material-check-bold:（Insiders） | :material-check-bold:（内置） |
| Privacy 插件 | :material-check-bold:（Insiders） | :material-check-bold:（内置） |
| Optimize 插件 | :material-check-bold:（Insiders） | :material-check-bold:（构建后自动） |
| PWA / 离线 | :material-check-bold:（Insiders） | :material-check-bold:（内置） |
| Git 修订日期 | :material-check-bold:（插件） | :material-check-bold:（内置） |
| 压缩 | :material-check-bold:（Insiders） | :material-check-bold:（自动） |
| 内置图标 | :material-check-bold: | :material-check-bold:（捆绑 58MB） |
| 即时导航 | :material-check-bold: | :material-check-bold: |
| 自定义提示框 | :material-check-bold: | :material-check-bold: |
| Mermaid 图表 | :material-check-bold:（插件） | :material-check-bold:（内置） |
| 代码注释 | :material-check-bold:（Insiders） | :material-check-bold:（内置） |
| 内容标签页 | :material-check-bold: | :material-check-bold: |
| 数据表格 | :material-check-bold: | :material-check-bold: |
| 工具提示 | :material-check-bold: | :material-check-bold: |

## 分步迁移

### 1. 备份您的网站
```bash
cp mkdocs.yml mkdocs.yml.bak
git add -A && git commit -m "backup before docsforge migration"
```

### 2. 创建 `docsforge.yml`

将您的 `mkdocs.yml` 复制为 `docsforge.yml`。大多数设置可以直接使用：

```yaml
site_name: Your Site
site_url: https://yourdomain.com
copyright: Copyright © 2025

nav:
  - Home: index.md
  # ... 复制您的导航结构

# 主题设置按原样工作
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

# 额外 CSS/JS 直接复制
extra_css:
  - stylesheets/extra.css
extra_javascript:
  - javascripts/extra.js

# Markdown 扩展直接复制
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  # ... 等等

plugins:
  - tags
  - search
  # - blog        # 内置，仅在需要时自定义
```

### 3. 转换配置键

DocsForge 使用与 `mkdocs.yml` 相同模式的 `docsforge.yml`。替换以下键：

| MkDocs | DocsForge |
|--------|-----------|
| `mkdocs.yml` | `docsforge.yml` |
| `site_dir` | `site_dir`（相同） |
| `docs_dir` | `docs_dir`（相同） |
| `plugins` | `plugins`（相同） |

### 4. 安装 DocsForge
```bash
pip install docsforge
```

### 5. 构建并测试
```bash
cd your-project
docsforge build
# 检查 site/ 目录
docsforge serve
```

### 6. 部署

DocsForge 将静态 HTML 输出到 `site/` — 可部署到任何静态主机。平台特定说明请参见[部署指南](deployment-guide.md)。

## 故障排除

| 问题 | 原因 | 解决方案 |
|-------|-------|-----|
| `plugin not found` | 插件不在 DocsForge 中 | 检查[功能对比](#feature-parity-material-vs-docsforge)或单独安装 |
| `theme not found` | Material 主题路径 | DocsForge 内置 Material；使用 `name: material` |
| 自定义钩子失败 | MkDocs API 差异 | 更新钩子以使用 DocsForge API |
| CSS/JS 未加载 | 路径解析 | 检查相对于 `docs_dir` 的路径 |
| 搜索不工作 | 缺少索引 | 确保 `search` 插件在 `plugins:` 中 |

## 获取帮助

- GitHub Issues：[github.com/QQSHI13/docsforge/issues](https://github.com/QQSHI13/docsforge/issues)
- 文档：[qqshi13.github.io/docsforge](https://qqshi13.github.io/docsforge/)
