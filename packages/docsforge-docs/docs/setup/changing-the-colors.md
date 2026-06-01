# Changing the colors

DocsForge uses the Material theme's color system. Customize colors in `docsforge.yml` under the `theme.palette` key.

## Color palette

A color palette defines the colors used throughout your site. You can define multiple palettes and let users switch between them (e.g., light and dark mode).

### Minimal configuration

``` yaml
theme:
  palette:
    primary: teal
    accent: teal
```

### Primary colors

The primary color is used for the header, navigation, links, and interactive elements.

| Color name | Value |
|-----------|-------|
| `red` | `#F44336` |
| `pink` | `#E91E63` |
| `purple` | `#9C27B0` |
| `deep purple` | `#673AB7` |
| `indigo` | `#3F51B5` |
| `blue` | `#2196F3` |
| `light blue` | `#03A9F4` |
| `cyan` | `#00BCD4` |
| `teal` | `#009688` |
| `green` | `#4CAF50` |
| `light green` | `#8BC34A` |
| `lime` | `#CDDC39` |
| `yellow` | `#FFEB3B` |
| `amber` | `#FFC107` |
| `orange` | `#FF9800` |
| `deep orange` | `#FF5722` |
| `brown` | `#795548` |
| `grey` | `#9E9E9E` |
| `blue grey` | `#607D8B` |
| `black` | `#000000` |
| `white` | `#FFFFFF` |

### Accent colors

The accent color is used for hover states, active elements, and emphasis.

Same values as primary colors, except `grey`, `brown`, `blue grey`, `black`, and `white`.

## Light and dark mode

Configure multiple palettes for automatic and manual switching:

``` yaml
theme:
  palette:
    # Auto-detect system preference
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: black
      accent: teal
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
```

### Schemes

- `default` — Light mode with white background
- `slate` — Dark mode with dark grey background

## Custom colors

Use any hex color value:

``` yaml
theme:
  palette:
    primary: "#1E90FF"
    accent: "#FF6B6B"
```

## Code block colors

Code block themes are tied to the palette scheme:

- `default` scheme → Light code highlighting (light background)
- `slate` scheme → Dark code highlighting (dark background)

This happens automatically. No configuration needed.

## Next steps

- [Changing the fonts](changing-the-fonts.md)
- [Setting up navigation](setting-up-navigation.md)
