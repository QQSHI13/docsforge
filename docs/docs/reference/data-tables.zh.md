---
icon: material/table
---

# 数据表格

DocsForge 使用增强的样式渲染 Markdown 表格。

## 基础表格

``` markdown
| Method | Description |
|--------|-------------|
| `GET` | Retrieve a resource |
| `POST` | Create a new resource |
| `PUT` | Update a resource |
| `DELETE` | Remove a resource |
```

| Method | Description |
|--------|-------------|
| `GET` | 检索资源 |
| `POST` | 创建新资源 |
| `PUT` | 更新资源 |
| `DELETE` | 删除资源 |

## 对齐列

``` markdown
| Left | Center | Right |
|:-----|:------:|------:|
| L    | C      | R     |
| left | center | right |
```

| Left | Center | Right |
|:-----|:------:|------:|
| L    | C      | R     |
| left | center | right |

## 宽表格

对于包含多列的表格，将其包裹在可滚动容器中：

``` markdown
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">

| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 |
|----------|----------|----------|----------|----------|
| Data     | Data     | Data     | Data     | Data     |

</div></div>
```

## 包含代码的表格

``` markdown
| Extension | Syntax | Description |
|-----------|--------|-------------|
| `admonition` | `!!! note` | Callout boxes |
| `attr_list` | `{: .class }` | HTML attributes |
| `pymdownx.highlight` | ` ```python ` | Code highlighting |
```

| Extension | Syntax | Description |
|-----------|--------|-------------|
| `admonition` | `!!! note` | 提示框 |
| `attr_list` | `{: .class }` | HTML 属性 |
| `pymdownx.highlight` | ` ```python ` | 代码高亮 |

## 包含链接的表格

``` markdown
| Feature | Guide | Reference |
|---------|-------|-----------|
| Colors | [Setup](../setup/changing-the-colors.md) | — |
| Fonts | [Setup](../setup/changing-the-fonts.md) | — |
| Admonitions | — | [Reference](admonitions.md) |
| Code blocks | — | [Reference](code-blocks.md) |
```

| Feature | Guide | Reference |
|---------|-------|-----------|
| Colors | [设置](../setup/changing-the-colors.md) | — |
| Fonts | [设置](../setup/changing-the-fonts.md) | — |
| Admonitions | — | [参考](admonitions.md) |
| Code blocks | — | [参考](code-blocks.md) |

## CSV 表格

对于复杂数据，可以考虑使用 `tables` 扩展或从 CSV 导入：

``` yaml
markdown_extensions:
  - tables
```

## 样式

为表格应用 CSS 类：

``` markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
{: .highlight }
```

## 表格排序

如需交互式排序，请添加 `data-table` 类：

``` markdown
| Name | Age | Role |
|------|-----|------|
| Alice | 30 | Developer |
| Bob | 25 | Designer |
| Carol | 35 | Manager |
{: data-table }
```

## 多行单元格

在单元格内使用 `<br>` 进行换行：

``` markdown
| Feature | Description |
|---------|-------------|
| Search | Full-text search<br>with highlighting |
| Dark mode | Light and dark<br>themes included |
```

| Feature | Description |
|---------|-------------|
| Search | 全文搜索<br>带高亮 |
| Dark mode | 浅色和深色<br>主题均已包含 |

## 最佳实践

- 为保持可读性，表格列数应控制在 10 列以内
- 使用 `|--------|` 对齐方式以保持视觉一致性
- 始终包含表头行以提升可访问性
- 使用 ` `（空格）表示空单元格，而不是 `||`
- 将宽表格放入可滚动容器中

## 下一步

- [提示框](admonitions.md)
- [格式](formatting.md)
