# Icons & Emojis

DocsForge includes 8,000+ Material Design icons and 3,000+ Twemoji emojis.

## Icons

### Syntax

Use `:material-icon-name:` syntax:

``` markdown
:material-heart: I love DocsForge!
```

:material-heart: I love DocsForge!

### Finding icons

Browse the [Material Design Icons](https://materialdesignicons.com/) library. Common categories:

- `:material-home:` — :material-home:
- `:material-settings:` — :material-settings:
- `:material-code-braces:` — :material-code-braces:
- `:material-book-open:` — :material-book-open:
- `:material-github:` — :material-github:
- `:material-rocket-launch:` — :material-rocket-launch:
- `:material-check-circle:` — :material-check-circle:
- `:material-alert-circle:` — :material-alert-circle:

### In admonitions

Icons appear automatically in admonition titles.

### In buttons and links

``` markdown
[Get started :material-arrow-right:](getting-started.md)
```

[Get started :material-arrow-right:](../getting-started.md)

### Sized icons

Apply CSS classes for sizing:

``` markdown
:material-heart:{ .lg } Large heart
```

## Emojis

Use standard emoji shortcodes:

``` markdown
:smile: :thumbsup: :rocket: :fire: :star: :warning:
```

:smile: :thumbsup: :rocket: :fire: :star: :warning:

## Font Awesome icons

Font Awesome brands are also available:

``` markdown
:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker
```

:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker

## Custom icons

Add your own icons in `docs/assets/icons/`:

``` yaml
extra:
  icon:
    logo: assets/logo.png
```

## Icon in headers

``` markdown
## :material-rocket: Getting Started
```

## :material-rocket: Getting Started

## Configuration

Icon support is enabled by default:

``` yaml
markdown_extensions:
  - pymdownx.emoji:
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
      emoji_index: !!python/name:material.extensions.emoji.twemoji
```

## Next steps

- [Images](images.md)
- [Lists](lists.md)
