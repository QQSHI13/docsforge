# Lists

DocsForge supports all standard list types plus extended syntax.

## Unordered lists

``` markdown
- Item 1
- Item 2
- Item 3
```

- Item 1
- Item 2
- Item 3

## Ordered lists

``` markdown
1. First item
2. Second item
3. Third item
```

1. First item
2. Second item
3. Third item

## Nested lists

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

## Fancy task lists

Custom checkbox styling is enabled by default:

``` yaml
markdown_extensions:
  - pymdownx.tasklist:
      custom_checkbox: true
```

This renders checkboxes with Material Design styling.

## List with code blocks

Lists can contain code blocks:

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

## List with admonitions

``` markdown
- Item with a note
    !!! note
        Important detail about this item
- Another item
```

- Item with a note
    !!! note
        Important detail about this item
- Another item

## Next steps

- [Formatting](formatting.md)
- [Tooltips](tooltips.md)
