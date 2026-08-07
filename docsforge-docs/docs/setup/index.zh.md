# 设置

DocsForge 的设置指南帮助你自定义文档站点的每个方面。所有配置都在 `docsforge.yml` 中完成。

## 概述

以下指南涵盖最常见的自定义场景：

<div class="grid cards" markdown>

-   :material-palette:{ .lg .middle } &nbsp; **[更改颜色](changing-the-colors.md)**

    ---

    自定义主色、强调色和背景色。配置浅色和深色模式调色板。

-   :material-format-font:{ .lg .middle } &nbsp; **[更改字体](changing-the-fonts.md)**

    ---

    使用 Google Fonts 或自定义字体文件作为正文字体和代码字体。

-   :material-translate:{ .lg .middle } &nbsp; **[更改语言](changing-the-language.md)**

    ---

    设置站点语言、配置搜索词干提取和 RTL 支持。

-   :material-navigation-variant:{ .lg .middle } &nbsp; **[设置导航](setting-up-navigation.md)**

    ---

    标签页、章节、索引、页脚链接和目录。

-   :material-magnify:{ .lg .middle } &nbsp; **[设置站点搜索](setting-up-site-search.md)**

    ---

    配置搜索行为、分隔符和结果展示。

-   :material-chart-line:{ .lg .middle } &nbsp; **[设置站点分析](setting-up-site-analytics.md)**

    ---

    添加 Plausible 或 Google Analytics 以跟踪页面浏览量。

-   :material-image:{ .lg .middle } &nbsp; **[设置社交卡片](setting-up-social-cards.md)**

    ---

    配置 Open Graph 和 Twitter Card 元标签，实现丰富的链接预览。

-   :material-package-variant-closed-check:{ .lg .middle } &nbsp; **[构建优化站点](building-an-optimized-site.md)**

    ---

    启用 HTML 压缩、资源压缩和构建优化。

-   :material-github:{ .lg .middle } &nbsp; **[添加 Git 仓库](adding-a-git-repository.md)**

    ---

    链接到源代码仓库，并显示“编辑此页”按钮。

</div>

## 配置文件

所有自定义都在 `docsforge.yml` 中完成。DocsForge 会自动加载所有插件和 Markdown 扩展——你只需配置想要自定义的部分。

``` yaml title="docsforge.yml"
site_name: My Project
site_url: https://example.com/docs/
site_author: Your Name
site_description: Documentation for My Project

repo_name: username/repo
repo_url: https://github.com/username/repo

copyright: Copyright &copy; 2025 Your Name

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: black
      accent: teal
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  font:
    text: Roboto
    code: Roboto Mono
```

## 下一步

从上方选择一个指南，自定义站点的特定方面。每个指南都包含可直接复制粘贴的配置示例。
