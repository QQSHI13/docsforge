# Tooltips

Tooltips show additional information when hovering over text.

## Abbreviations

Define abbreviations that show full text on hover:

``` markdown
The HTML specification is maintained by the W3C.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium
```

The HTML specification is maintained by the W3C.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium

## Footnotes

Add footnotes with references:

``` markdown
DocsForge is a self-contained documentation build system.[^1]

[^1]: All dependencies are vendored into the project repository.
```

DocsForge is a self-contained documentation build system.[^1]

[^1]: All dependencies are vendored into the project repository.

## Content tooltips

Enable with `content.tooltips` feature:

``` yaml
theme:
  features:
    - content.tooltips
```

This adds hover tooltips for abbreviations and links throughout the site.

## Link tooltips

Use `title` attribute for link tooltips:

``` markdown
[DocsForge](https://github.com/QQSHI13/docsforge "Self-contained documentation builds")
```

## Definition lists as tooltips

Definition terms can serve as glossary entries:

``` markdown
DocsForge
:   A self-contained documentation build system with vendored dependencies.
```

DocsForge
:   A self-contained documentation build system with vendored dependencies.

## Magic links

Automatic link conversion for GitHub references:

``` markdown
See issue #123 and PR #456 for details.
```

Enable with:

``` yaml
markdown_extensions:
  - pymdownx.magiclink:
      repo_url_shorthand: true
      user: QQSHI13
      repo: docsforge-docs
```

## Next steps

- [Formatting](formatting.md)
- [Icons & Emojis](icons-emojis.md)
