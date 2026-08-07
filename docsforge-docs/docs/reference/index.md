# Reference

Complete syntax reference for all DocsForge Markdown extensions and components.

## Overview

DocsForge extends standard Markdown with powerful syntax for technical documentation. All extensions are enabled by default in the starter template.

<div class="grid cards" markdown>

-   :material-alert:{ .lg .middle } &nbsp; **[Admonitions](admonitions.md)**

    ---

    Note, warning, tip, danger, and custom callout boxes.

-   :material-comment-text:{ .lg .middle } &nbsp; **[Annotations](annotations.md)**

    ---

    Add comments and explanations to code blocks.

-   :material-code-braces:{ .lg .middle } &nbsp; **[Code blocks](code-blocks.md)**

    ---

    Syntax highlighting, line numbers, titles, copy button, and more.

-   :material-tab:{ .lg .middle } &nbsp; **[Content tabs](content-tabs.md)**

    ---

    Group related content with tabbed interfaces.

-   :material-table:{ .lg .middle } &nbsp; **[Data tables](data-tables.md)**

    ---

    Sortable, styled tables with alignment and formatting.

-   :material-chart-tree:{ .lg .middle } &nbsp; **[Diagrams](diagrams.md)**

    ---

    Mermaid.js flowcharts, sequence diagrams, and more.

-   :material-format-color-fill:{ .lg .middle } &nbsp; **[Formatting](formatting.md)**

    ---

    Highlight, subscript, superscript, and inline formatting.

-   :material-emoticon:{ .lg .middle } &nbsp; **[Icons & Emojis](icons-emojis.md)**

    ---

    8,000+ icons and 3,000+ emojis via `:material-heart:` syntax.

-   :material-image:{ .lg .middle } &nbsp; **[Images](images.md)**

    ---

    Captions, alignment, lazy loading, and figure markup.

-   :material-format-list-bulleted:{ .lg .middle } &nbsp; **[Lists](lists.md)**

    ---

    Ordered, unordered, nested, task lists, and definition lists.

-   :material-tooltip-text:{ .lg .middle } &nbsp; **[Tooltips](tooltips.md)**

    ---

    Abbreviations, definitions, and hover tooltips.

</div>

## Markdown extensions enabled by default

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

## Standard Markdown

DocsForge supports all standard Markdown syntax:

- Headings (`#` to `######`)
- Paragraphs and line breaks
- Bold (`**text**`) and italic (`*text*`)
- Strikethrough (`~~text~~`)
- Links (`[text](url)`) and images (`![alt](url)`)
- Blockquotes (`> quote`)
- Inline code (`` `code` ``) and code blocks
- Horizontal rules (`---`)
- Ordered and unordered lists

## Next steps

Pick a reference page above for detailed syntax and examples.
