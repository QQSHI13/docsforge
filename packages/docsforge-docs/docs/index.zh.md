# DocsForge

<p align="center">
  <img src="assets/badge.svg" alt="DocsForge">
</p>

用 Markdown 编写文档。数秒内构建专业的静态站点。随处部署。


!!! tip "从 MkDocs 迁移而来？"

    DocsForge 是 MkDocs + Material for MkDocs 的积极维护继任者。
    查看[迁移指南](getting-started/migrating-from-mkdocs.md)，了解如何手动迁移您的项目。

```bash
pip install docsforge
docsforge serve
```

## DocsForge 有什么不同

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } &nbsp; **零依赖**

    ---

    所有功能均已内置。`pip install docsforge` 即可获得文档引擎、Material 主题、全部插件、全部扩展、字体、图标、数学渲染和服务工作者。

-   :material-rocket-launch:{ .lg .middle } &nbsp; **零配置**

    ---

    只需 `site_name:` 即可开始。全部 7 个插件和 31 个 Markdown 扩展会自动加载。仅在需要时进行自定义。

-   :material-function-variant:{ .lg .middle } &nbsp; **数学公式可用**

    ---

    编写 `$$...$$` 即可渲染。KaTeX 已内置 —— 读者端无需调用 CDN，无需 `extra_javascript`，无需额外设置。

-   :material-code-tags:{ .lg .middle } &nbsp; **语法高亮**

    ---

    代码块在构建时使用 Pygments 着色。无需客户端 JavaScript。

-   :material-magnify:{ .lg .middle } &nbsp; **即时搜索**

    ---

    内置全文搜索，由客户端 Lunr.js 索引驱动。

-   :material-palette:{ .lg .middle } &nbsp; **深色模式**

    ---

    页眉中提供浅色/深色切换。自动检测系统偏好。

-   :material-chart-bar:{ .lg .middle } &nbsp; **TikZ 图表**

    ---

    直接在 Markdown 中编写 TikZ。构建时自动编译为 SVG。

-   :material-rss-box:{ .lg .middle } &nbsp; **博客**

    ---

    内置博客，支持作者、标签、归档、分页和 RSS 订阅源。

-   :material-wifi-off:{ .lg .middle } &nbsp; **离线支持**

    ---

    服务工作者缓存所有资源。无需互联网连接即可工作。

</div>

## 快速开始

```bash
pip install docsforge
docsforge          # 以交互方式创建新项目
cd my-docs
docsforge serve
```

就是这样。您的文档站点现在运行在 [localhost:8000](http://localhost:8000)。

## 内置功能

| 功能 | 状态 |
|---------|--------|
| 提示框 (`!!! note`) | :material-check-bold: 零配置 |
| 数学公式 (`$$...$$`) | :material-check-bold: 零配置 |
| 代码高亮 | :material-check-bold: 零配置 |
| 表格 | :material-check-bold: 零配置 |
| 任务列表 (`- [x]`) | :material-check-bold: 零配置 |
| 脚注 (`[^1]`) | :material-check-bold: 零配置 |
| 定义列表 | :material-check-bold: 零配置 |
| 缩写 | :material-check-bold: 零配置 |
| 内容标签页 | :material-check-bold: 零配置 |
| 图表（Mermaid、TikZ） | :material-check-bold: 零配置 |
| 表情符号 | :material-check-bold: 零配置 |
| 博客 | :material-check-bold: 零配置 |
| 标签 | :material-check-bold: 零配置 |
| 搜索 | :material-check-bold: 零配置 |
| 隐私（自托管资源） | :material-check-bold: 零配置 |
| 压缩（HTML/CSS/JS） | :material-check-bold: 零配置 |
| 离线/PWA | :material-check-bold: 零配置 |

## 下一步

<div class="grid cards" markdown>

-   :material-cog-play:{ .lg .middle } &nbsp; **[入门指南](getting-started.md)**

    ---

    安装、初步使用和基础配置

-   :material-book-open-page-variant:{ .lg .middle } &nbsp; **[设置指南](setup/index.md)**

    ---

    自定义颜色、字体、导航、搜索等

-   :material-code-braces:{ .lg .middle } &nbsp; **[参考](reference/index.md)**

    ---

    Markdown 语法、组件和格式化选项

-   :material-rss-box:{ .lg .middle } &nbsp; **[博客](blogging.md)**

    ---

    设置支持作者、标签和 RSS 订阅源的博客

</div>
