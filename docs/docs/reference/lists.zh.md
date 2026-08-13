---
icon: material/format-list-bulleted
---

# 列表

DocsForge 支持所有标准列表类型，以及任务列表、定义列表和复杂嵌套的扩展语法。

---

## 无序列表

标准 Markdown 项目符号列表：

``` markdown
- Item 1
- Item 2
- Item 3
```

- Item 1
- Item 2
- Item 3

### 嵌套无序列表

``` markdown
- Parent item
  - Child item 1
  - Child item 2
    - Grandchild item
- Another parent
```

- Parent item
  - Child item 1
  - Child item 2
    - Grandchild item
- Another parent

### 不同项目符号样式

可互换使用 `-`、`*` 或 `+`：

``` markdown
- Dash item
* Asterisk item
+ Plus item
```

- Dash item
* Asterisk item
+ Plus item

---

## 有序列表

标准编号列表：

``` markdown
1. First item
2. Second item
3. Third item
```

1. First item
2. Second item
3. Third item

### 嵌套有序列表

``` markdown
1. First step
   1. Sub-step A
   2. Sub-step B
2. Second step
   1. Sub-step C
   2. Sub-step D
```

1. First step
   1. Sub-step A
   2. Sub-step B
2. Second step
   1. Sub-step C
   2. Sub-step D

### 从指定数字开始

``` markdown
5. Fifth item
6. Sixth item
7. Seventh item
```

5. Fifth item
6. Sixth item
7. Seventh item

---

## 混合列表

组合有序和无序列表：

``` markdown
1. First step
   - Detail A
   - Detail B
2. Second step
   - Detail C
     1. Sub-detail 1
     2. Sub-detail 2
```

1. First step
   - Detail A
   - Detail B
2. Second step
   - Detail C
     1. Sub-detail 1
     2. Sub-detail 2

---

## 任务列表

通过 `pymdownx.tasklist` 启用：

``` markdown
- [x] Completed task
- [ ] Incomplete task
- [ ] Another task
```

- [x] Completed task
- [ ] Incomplete task
- [ ] Another task

### 嵌套任务列表

``` markdown
- [x] Parent task completed
  - [x] Child task completed
  - [ ] Child task pending
- [ ] Parent task pending
  - [ ] Child task pending
  - [ ] Another child task pending
```

- [x] Parent task completed
  - [x] Child task completed
  - [ ] Child task pending
- [ ] Parent task pending
  - [ ] Child task pending
  - [ ] Another child task pending

### 带说明的任务列表

``` markdown
- [x] Install DocsForge
  Simple pip install command
- [ ] Create your first page
  Write a `index.md` file
- [ ] Build the site
  Run `docsforge build`
```

- [x] Install DocsForge
  Simple pip install command
- [ ] Create your first page
  Write a `index.md` file
- [ ] Build the site
  Run `docsforge build`

---

## 精美任务列表（自定义样式）

默认启用 Material Design 自定义复选框样式：

``` yaml
markdown_extensions:
  - pymdownx.tasklist:
      custom_checkbox: true
```

这将使用 Material Design 样式渲染复选框，而非默认浏览器复选框。

---

## 定义列表

通过 `def_list` 启用：

``` markdown
Term 1
:   Definition of term 1

Term 2
:   Definition of term 2
:   Another definition for term 2
```

Term 1
:   Definition of term 1

Term 2
:   Definition of term 2
:   Another definition for term 2

### 嵌套定义

``` markdown
DocsForge
:   A self-contained documentation engine
    :   Vendored dependencies
    :   Zero external downloads
    :   Fast builds

Material Design
:   The design system used by DocsForge
    :   Clean, modern aesthetic
    :   Responsive layouts
```

DocsForge
:   A self-contained documentation engine
    :   Vendored dependencies
    :   Zero external downloads
    :   Fast builds

Material Design
:   The design system used by DocsForge
    :   Clean, modern aesthetic
    :   Responsive layouts

---

## 包含代码块的列表

列表可以包含代码块和其他块级元素：

``` markdown
1. First step
   ``` bash
   echo "Hello"
   ```
2. Second step
   ``` bash
   echo "World"
   ```
```

1. First step
   ``` bash
   echo "Hello"
   ```
2. Second step
   ``` bash
   echo "World"
   ```

---

## 包含提示框的列表

``` markdown
- Item with a note
    !!! note
        Important detail about this item
- Another item
    !!! warning
        Be careful with this step
```

- Item with a note
    !!! note
        关于此项目的重要细节
- Another item
    !!! warning
        此步骤需谨慎

---

## 包含图标的列表

``` markdown
- :material-check: Completed feature
- :material-wrench: Work in progress
- :material-clock-outline: Planned for next release
- :material-alert: Needs attention
```

- :material-check: 已完成功能
- :material-wrench: 进行中
- :material-clock-outline: 计划下个版本
- :material-alert: 需要注意

---

## 包含链接和格式的列表

``` markdown
- **Bold item** with *italic* description
- [Link to another page](getting-started.md)
- `inline code` for technical terms
- ==Highlighted text== for emphasis
```

- **Bold item** with *italic* description
- [链接到另一页面](../getting-started.md)
- `inline code` for technical terms
- ==Highlighted text== for emphasis

---

## 最佳实践

- 对功能、选项或无顺序的项目使用无序列表
- 对连续步骤或有排名的项目使用有序列表
- 对待办清单、检查清单或进度跟踪使用任务列表
- 对术语表、常见问题或键值对使用定义列表
- 为可读性，嵌套最多保持 3 层
- 始终使用 2 或 4 个空格缩进嵌套项目
- 避免在一个列表中混合过多元素类型
- 在 GitHub issues 或项目文档中使用任务列表来跟踪进度

---

## 下一步

- [格式设置](formatting.md)
- [工具提示](tooltips.md)
- [图标与表情](icons-emojis.md)
