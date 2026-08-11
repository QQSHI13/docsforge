# Lists

DocsForge supports all standard list types plus extended syntax for task lists, definition lists, and complex nesting.

---

## Unordered lists

Standard Markdown bullet lists:

``` markdown
- Item 1
- Item 2
- Item 3
```

- Item 1
- Item 2
- Item 3

### Nested unordered lists

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

### Different bullet styles

Use `-`, `*`, or `+` interchangeably:

``` markdown
- Dash item
* Asterisk item
+ Plus item
```

- Dash item
* Asterisk item
+ Plus item

---

## Ordered lists

Standard numbered lists:

``` markdown
1. First item
2. Second item
3. Third item
```

1. First item
2. Second item
3. Third item

### Nested ordered lists

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

### Starting from a specific number

``` markdown
5. Fifth item
6. Sixth item
7. Seventh item
```

5. Fifth item
6. Sixth item
7. Seventh item

---

## Mixed lists

Combine ordered and unordered lists:

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

## Task lists

Enable with `pymdownx.tasklist`:

``` markdown
- [x] Completed task
- [ ] Incomplete task
- [ ] Another task
```

- [x] Completed task
- [ ] Incomplete task
- [ ] Another task

### Nested task lists

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

### Task lists with descriptions

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

## Fancy task lists (custom styling)

Custom checkbox styling with Material Design is enabled by default:

``` yaml
markdown_extensions:
  - pymdownx.tasklist:
      custom_checkbox: true
```

This renders checkboxes with Material Design styling instead of default browser checkboxes.

---

## Definition lists

Enable with `def_list`:

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

### Nested definitions

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

## Lists with code blocks

Lists can contain code blocks and other block elements:

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

## Lists with admonitions

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
        Important detail about this item
- Another item
    !!! warning
        Be careful with this step

---

## Lists with icons

``` markdown
- :material-check: Completed feature
- :material-wrench: Work in progress
- :material-clock-outline: Planned for next release
- :material-alert: Needs attention
```

- :material-check: Completed feature
- :material-wrench: Work in progress
- :material-clock-outline: Planned for next release
- :material-alert: Needs attention

---

## Lists with links and formatting

``` markdown
- **Bold item** with *italic* description
- [Link to another page](getting-started.md)
- `inline code` for technical terms
- ==Highlighted text== for emphasis
```

- **Bold item** with *italic* description
- [Link to another page](../getting-started.md)
- `inline code` for technical terms
- ==Highlighted text== for emphasis

---

## Best practices

- Use unordered lists for features, options, or unordered items
- Use ordered lists for sequential steps or ranked items
- Use task lists for todo lists, checklists, or progress tracking
- Use definition lists for glossaries, FAQs, or key-value pairs
- Keep nesting to 3 levels maximum for readability
- Indent nested items with 2 or 4 spaces consistently
- Avoid mixing too many element types in one list
- Use task lists in GitHub issues or project documentation for progress tracking

---

## Next steps

- [Formatting](formatting.md)
- [Tooltips](tooltips.md)
- [Icons & Emojis](icons-emojis.md)
