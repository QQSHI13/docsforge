# Admonitions

Admonitions (also called callouts or aside boxes) highlight important information with colored boxes and icons.

## Syntax

``` markdown
!!! type "Optional title"
    Content goes here. Must be indented.
```

## Types

### Note

``` markdown
!!! note
    This is a note admonition.
```

!!! note
    This is a note admonition.

### Tip

``` markdown
!!! tip
    This is a tip admonition.
```

!!! tip
    This is a tip admonition.

### Warning

``` markdown
!!! warning
    This is a warning admonition.
```

!!! warning
    This is a warning admonition.

### Danger

``` markdown
!!! danger
    This is a danger admonition.
```

!!! danger
    This is a danger admonition.

### Info

``` markdown
!!! info
    This is an info admonition.
```

!!! info
    This is an info admonition.

### Success

``` markdown
!!! success
    This is a success admonition.
```

!!! success
    This is a success admonition.

### Abstract

``` markdown
!!! abstract
    This is an abstract admonition.
```

!!! abstract
    This is an abstract admonition.

## Collapsible admonitions

Add `?` to make the admonition collapsible:

``` markdown
??? note "Click to expand"
    This content is hidden by default.
```

??? note "Click to expand"
    This content is hidden by default.

Add `+` to make it expanded by default:

``` markdown
???+ note "Already expanded"
    This content is visible by default.
```

???+ note "Already expanded"
    This content is visible by default.

## Custom titles

``` markdown
!!! note "Custom title here"
    You can replace the default type label.
```

!!! note "Custom title here"
    You can replace the default type label.

## Without icon

``` markdown
!!! note ""
    No icon, just the title and content.
```

!!! note ""
    No icon, just the title and content.

## Nested content

Admonitions can contain any Markdown, including code blocks:

``` markdown
!!! example "Configuration example"
    ``` yaml
    theme:
      palette:
        primary: teal
    ```
```

!!! example "Configuration example"
    ``` yaml
    theme:
      palette:
        primary: teal
    ```

## All admonition types

| Type | Color | Icon | Use for |
|------|-------|------|---------|
| `note` | Blue | Info circle | General information |
| `abstract` | Cyan | Document | Summaries, abstracts |
| `info` | Blue | Info | Detailed information |
| `tip` | Green | Lightbulb | Helpful advice |
| `success` | Green | Check | Positive outcomes |
| `question` | Orange | Help circle | Questions, FAQs |
| `warning` | Orange | Alert triangle | Caution needed |
| `failure` | Red | X circle | Something failed |
| `danger` | Red | Flash | Critical warnings |
| `bug` | Red | Bug | Bug reports |
| `example` | Purple | List | Examples |
| `quote` | Grey | Quote | Quotations |

## Next steps

- [Code blocks](code-blocks.md)
- [Content tabs](content-tabs.md)
