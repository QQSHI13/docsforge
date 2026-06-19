# Icons & Emojis

DocsForge includes **8,000+ Material Design icons** and **3,000+ Twemoji emojis** out of the box. No external downloads needed.

---

## Icons

### Syntax

Use `:material-icon-name:` syntax anywhere in your Markdown:

``` markdown
:material-heart: I love DocsForge!
```

:material-heart: I love DocsForge!

---

### Finding icons

Browse the full [Material Design Icons](https://materialdesignicons.com/) library. Common categories:

| Category | Examples |
|----------|----------|
| Navigation | :material-home: `:material-home:` :material-arrow-right: `:material-arrow-right:` :material-menu: `:material-menu:` |
| Actions | :material-download: `:material-download:` :material-upload: `:material-upload:` :material-refresh: `:material-refresh:` |
| Content | :material-file-document: `:material-file-document:` :material-image: `:material-image:` :material-code-braces: `:material-code-braces:` |
| Status | :material-check-circle: `:material-check-circle:` :material-alert-circle: `:material-alert-circle:` :material-information: `:material-information:` |
| Hardware | :material-memory: `:material-memory:` :material-harddisk: `:material-harddisk:` :material-server: `:material-server:` |
| Social | :material-github: `:material-github:` :material-twitter: `:material-twitter:` :material-web: `:material-web:` |

!!! tip "Icon search"
    Use the [Material Icons search](https://materialdesignicons.com/) to find the exact name. Replace spaces with hyphens: `arrow-right` → `:material-arrow-right:`

---

### Using icons

#### In text

``` markdown
Click the :material-settings: settings icon to configure.
```

Click the :material-settings: settings icon to configure.

#### In buttons and links

``` markdown
[Get started :material-arrow-right:](getting-started.md)

[Download :material-download:](https://example.com)
```

[Get started :material-arrow-right:](../getting-started.md)

[Download :material-download:](https://example.com)

#### In admonitions

Icons appear automatically in admonition titles based on the type:

``` markdown
!!! tip "Tip with icon"
    This admonition has an automatic icon.
```

!!! tip "Tip with icon"
    This admonition has an automatic icon.

#### In headers

``` markdown
## :material-rocket: Getting Started
```

## :material-rocket: Getting Started

#### In tables

``` markdown
| Feature | Status |
|---------|--------|
| :material-check: Working | :material-check-circle: Complete |
| :material-wrench: In progress | :material-alert: Attention needed |
```

| Feature | Status |
|---------|--------|
| :material-check: Working | :material-check-circle: Complete |
| :material-wrench: In progress | :material-alert: Attention needed |

---

### Icon sizing

Apply CSS classes for sizing (requires custom CSS):

``` markdown
:material-heart:{ .twemoji .lg } Large heart
:material-heart:{ .twemoji .2x } Double size
:material-heart:{ .twemoji .3x } Triple size
```

### Custom icon colors

``` markdown
:material-heart:{ .red } Red heart
:material-heart:{ .blue } Blue heart
```

(Requires defining `.red` and `.blue` CSS classes.)

---

## Emojis

### Standard shortcodes

Use standard emoji shortcodes:

``` markdown
:smile: :thumbsup: :rocket: :fire: :star: :warning: :heart: :tada:
```

:smile: :thumbsup: :rocket: :fire: :star: :warning: :heart: :tada:

### Common emojis for documentation

| Emoji | Shortcode | Use case |
|-------|-----------|----------|
| :rocket: | `:rocket:` | New feature, launch |
| :warning: | `:warning:` | Warning, caution |
| :star: | `:star:` | Favorite, recommended |
| :fire: | `:fire:` | Hot topic, trending |
| :bulb: | `:bulb:` | Idea, tip |
| :bug: | `:bug:` | Bug, issue |
| :white_check_mark: | `:white_check_mark:` | Completed |
| :x: | `:x:` | Failed, removed |
| :memo: | `:memo:` | Documentation |
| :gear: | `:gear:` | Configuration |

---

## Font Awesome icons

Font Awesome brand icons are also available:

``` markdown
:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker
:fontawesome-brands-linux: Linux
:fontawesome-brands-windows: Windows
:fontawesome-brands-apple: Apple
:fontawesome-brands-js: JavaScript
:fontawesome-brands-react: React
:fontawesome-brands-vuejs: Vue
:fontawesome-brands-html5: HTML5
:fontawesome-brands-css3: CSS3
```

:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker
:fontawesome-brands-linux: Linux
:fontawesome-brands-windows: Windows
:fontawesome-brands-apple: Apple
:fontawesome-brands-js: JavaScript
:fontawesome-brands-react: React
:fontawesome-brands-vuejs: Vue
:fontawesome-brands-html5: HTML5
:fontawesome-brands-css3: CSS3

!!! note "Font Awesome regular and solid"
    Brand icons (`fontawesome-brands-*`) are always available. Regular and solid variants may require additional configuration.

---

## Custom icons

### Adding custom icons

Place SVG icons in `docs/assets/icons/` and reference them:

``` yaml
theme:
  icon:
    logo: assets/icons/my-logo.svg
    repo: assets/icons/custom-repo.svg
```

### Using custom icons in Markdown

``` markdown
:custom-icon-name:
```

Requires registering the icon in your `docsforge.yml`:

``` yaml
theme:
  icon:
    admonition:
      note: custom-icon-name
```

---

## Configuration

Icon support is enabled by default. The configuration is:

``` yaml
markdown_extensions:
  - pymdownx.emoji:
      emoji_generator: !!python/name:docsforge.emoji.to_svg
      emoji_index: !!python/name:docsforge.emoji.twemoji
```

!!! warning "Don't change this"
    DocsForge vendors all emoji and icon assets. Changing the generator or index may break offline support.

---

## Best practices

- Use icons sparingly — too many make text hard to read
- Prefer Material icons over emojis for professional documentation
- Use emojis for informal content, release notes, or social cards
- Always include the text label alongside icons for accessibility
- Test how icons render in both light and dark themes
- Avoid icons in table headers — use text instead

---

## Next steps

- [Images](images.md)
- [Lists](lists.md)
- [Data tables](data-tables.md)
