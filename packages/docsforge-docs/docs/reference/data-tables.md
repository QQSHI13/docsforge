# Data tables

DocsForge renders Markdown tables with enhanced styling.

## Basic table

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
| `GET` | Retrieve a resource |
| `POST` | Create a new resource |
| `PUT` | Update a resource |
| `DELETE` | Remove a resource |

## Aligned columns

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

## Wide tables

For tables with many columns, wrap them in a scrollable container:

``` markdown
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">

| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 |
|----------|----------|----------|----------|----------|
| Data     | Data     | Data     | Data     | Data     |

</div></div>
```

## Tables with code

``` markdown
| Extension | Syntax | Description |
|-----------|--------|-------------|
| `admonition` | `!!! note` | Callout boxes |
| `attr_list` | `{: .class }` | HTML attributes |
| `pymdownx.highlight` | ` ```python ` | Code highlighting |
```

| Extension | Syntax | Description |
|-----------|--------|-------------|
| `admonition` | `!!! note` | Callout boxes |
| `attr_list` | `{: .class }` | HTML attributes |
| `pymdownx.highlight` | ` ```python ` | Code highlighting |

## Tables with links

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
| Colors | [Setup](../setup/changing-the-colors.md) | — |
| Fonts | [Setup](../setup/changing-the-fonts.md) | — |
| Admonitions | — | [Reference](admonitions.md) |
| Code blocks | — | [Reference](code-blocks.md) |

## CSV tables

For complex data, consider using the `tables` extension or importing from CSV:

``` yaml
markdown_extensions:
  - tables
```

## Styling

Apply CSS classes to tables:

``` markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
{: .highlight }
```

## Next steps

- [Admonitions](admonitions.md)
- [Formatting](formatting.md)
