# 参考

DocsForge Markdown 扩展和组件的完整语法参考。

## 概述

DocsForge 使用强大的语法扩展了标准 Markdown。所有扩展都在入门模板中默认启用。

<div class="grid cards" markdown>

-   :material-alert:{ .lg .middle } &nbsp; **[提示框](admonitions.md)**

    ---

    Note、warning、tip、danger 和自定义标注框。

-   :material-comment-text:{ .lg .middle } &nbsp; **[注释](annotations.md)**

    ---

    为代码块添加注释和说明。

-   :material-code-braces:{ .lg .middle } &nbsp; **[代码块](code-blocks.md)**

    ---

    语法高亮、行号、标题、复制按钮等。

-   :material-tab:{ .lg .middle } &nbsp; **[内容标签页](content-tabs.md)**

    ---

    使用标签页界面分组相关内容。

-   :material-table:{ .lg .middle } &nbsp; **[数据表格](data-tables.md)**

    ---

    可排序、带样式、支持对齐和格式化的表格。

-   :material-chart-tree:{ .lg .middle } &nbsp; **[图表](diagrams.md)**

    ---

    Mermaid.js 流程图、时序图等。

-   :material-format-color-fill:{ .lg .middle } &nbsp; **[格式化](formatting.md)**

    ---

    高亮、下标、上标和行内格式化。

-   :material-emoticon:{ .lg .middle } &nbsp; **[图标与表情](icons-emojis.md)**

    ---

    通过 `:material-heart:` 语法使用 8,000+ 图标和 3,000+ 表情。

-   :material-image:{ .lg .middle } &nbsp; **[图片](images.md)**

    ---

    标题、对齐、懒加载和图形标记。

-   :material-format-list-bulleted:{ .lg .middle } &nbsp; **[列表](lists.md)**

    ---

    有序列表、无序列表、嵌套列表、任务列表和定义列表。

-   :material-tooltip-text:{ .lg .middle } &nbsp; **[工具提示](tooltips.md)**

    ---

    缩写、定义和悬停工具提示。

</div>

## 默认启用的 Markdown 扩展

``` yaml
markdown_extensions:
  - abbr
  - admonition
  - attr_list
  - def_list
  - footnotes
  - md_in_html
  - toc:
      permalink: true
  - pymdownx.arithmatex
  - pymdownx.betterem
  - pymdownx.caret
  - pymdownx.details
  - pymdownx.emoji
  - pymdownx.highlight
  - pymdownx.inlinehilite
  - pymdownx.keys
  - pymdownx.magiclink
  - pymdownx.mark
  - pymdownx.smartsymbols
  - pymdownx.superfences
  - pymdownx.tabbed
  - pymdownx.tasklist
  - pymdownx.tilde
```

## 标准 Markdown

DocsForge 支持所有标准 Markdown 语法：

- 标题（`#` 到 `######`）
- 段落和换行
- 加粗（`**text**`）和斜体（`*text*`）
- 删除线（`~~text~~`）
- 链接（`[text](url)`）和图片（`![alt](url)`）
- 引用块（`> quote`）
- 行内代码（`` `code` ``）和代码块
- 水平分隔线（`---`）
- 有序和无序列表

## 下一步

从上方选择一个参考页面，查看详细语法和示例。
