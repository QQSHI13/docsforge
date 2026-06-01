# Changing the fonts

DocsForge supports Google Fonts out of the box. Configure fonts in `docsforge.yml` under the `theme.font` key.

## Configuration

### Google Fonts

``` yaml
theme:
  font:
    text: Roboto
    code: Roboto Mono
```

### Supported font weights

DocsForge loads regular (400) and bold (700) weights automatically. For font families that need different weight names:

``` yaml
theme:
  font:
    text: "Open Sans"  # Quotes needed for multi-word names
    code: "Fira Code"
```

### Disabling font loading

If you want to use system fonts or load fonts yourself:

``` yaml
theme:
  font: false
```

## Recommended font pairings

<div class="grid cards" markdown>

-   **Roboto + Roboto Mono**

    ---

    The default pairing. Clean, modern, excellent for technical docs.

-   **Inter + JetBrains Mono**

    ---

    Inter is optimized for screen readability. JetBrains Mono has ligatures and clear distinction between similar characters.

-   **Open Sans + Source Code Pro**

    ---

    Friendly and approachable. Great for community-oriented projects.

-   **Lato + Fira Code**

    ---

    Warm and professional. Fira Code adds programming ligatures.

</div>

## Custom fonts

To use fonts not available on Google Fonts, load them via custom CSS:

``` yaml
extra_css:
  - assets/stylesheets/custom.css
```

``` css title="docs/assets/stylesheets/custom.css"
@font-face {
  font-family: "My Font";
  src: url("../fonts/my-font.woff2") format("woff2");
  font-weight: 400;
}

:root {
  --md-text-font: "My Font";
}
```

Place your font files in `docs/assets/fonts/`.

## Next steps

- [Changing the colors](changing-the-colors.md)
- [Changing the language](changing-the-language.md)
