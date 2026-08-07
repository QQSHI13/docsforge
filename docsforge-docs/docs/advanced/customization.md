# Customization Guide

DocsForge provides powerful customization options beyond the basic configuration. This guide covers advanced techniques for tailoring your site's appearance, behavior, and functionality.

---

## Custom CSS

Add custom stylesheets via the `extra_css` setting in `docsforge.yml`:

```yaml
extra_css:
  - stylesheets/extra.css
```

Create `docs/stylesheets/extra.css`:

```css
/* Custom brand color */
:root {
  --md-primary-fg-color: #4051b5;
  --md-primary-fg-color--light: #5d6cc0;
  --md-primary-fg-color--dark: #2e3b8e;
}

/* Custom font for headings */
.md-typeset h1,
.md-typeset h2 {
  font-family: 'Georgia', serif;
  font-weight: 700;
}

/* Wider content area */
@media screen and (min-width: 76.25em) {
  .md-content {
    max-width: 900px;
  }
}
```

### Overriding theme variables

DocsForge uses CSS custom properties for theming. Override them in your custom CSS:

| Variable | Description |
|----------|-------------|
| `--md-primary-fg-color` | Primary color |
| `--md-primary-fg-color--light` | Light variant |
| `--md-primary-fg-color--dark` | Dark variant |
| `--md-accent-fg-color` | Accent color |
| `--md-typeset-color` | Body text color |
| `--md-typeset-a-color` | Link color |
| `--md-code-fg-color` | Code text color |
| `--md-code-bg-color` | Code background |
| `--md-default-fg-color` | Default foreground |
| `--md-default-bg-color` | Default background |

---

## Custom JavaScript

Add custom scripts via `extra_javascript`:

```yaml
extra_javascript:
  - javascripts/extra.js
```

Create `docs/javascripts/extra.js`:

```javascript
// Custom behavior on page load
document.addEventListener('DOMContentLoaded', function() {
  // Add copy button to all tables
  const tables = document.querySelectorAll('.md-typeset table');
  tables.forEach(table => {
    const button = document.createElement('button');
    button.className = 'md-clipboard';
    button.innerHTML = 'Copy';
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(table.innerText);
    });
    table.parentElement.insertBefore(button, table);
  });
});
```

### Hooking into DocsForge events

```javascript
// Listen for search events
window.addEventListener('docsforge-search', function(e) {
  console.log('Search query:', e.detail.query);
});

// Listen for theme changes
window.addEventListener('docsforge-theme', function(e) {
  console.log('Theme changed to:', e.detail.scheme);
});
```

---

## Custom Templates

Override built-in templates by creating an `overrides` directory and referencing it in `docsforge.yml`:

```yaml
theme:
  custom_dir: overrides
```

### Override partials

Create `docs/overrides/partials/copyright.html`:

```html
<!-- Custom copyright notice -->
<div class="md-copyright">
  <strong>My Company</strong> — 
  <a href="{{ config.repo_url }}" target="_blank" rel="noopener">
    {{ config.repo_name }}
  </a>
</div>
```

### Override base template

Create `docs/overrides/main.html` to extend the base template:

```html
{% extends "base.html" %}

{% block extrahead %}
  {{ super() }}
  <meta property="og:image" content="{{ config.site_url }}assets/social-card.png">
{% endblock %}

{% block announce %}
  <div class="announcement">
    :material-party-popper: New version released! <a href="/changelog">See what's new</a>
  </div>
{% endblock %}
```

### Available blocks

| Block | Description |
|-------|-------------|
| `extrahead` | Inside `<head>` tag |
| `announce` | Announcement banner |
| `header` | Site header |
| `tabs` | Navigation tabs |
| `content` | Main content area |
| `footer` | Page footer |
| `outdated` | Outdated version notice |

---

## Custom Admonitions

Define custom admonition types with CSS:

```css
/* Custom "tip" admonition in brand color */
.md-typeset .admonition.tip {
  border-color: #4051b5;
}

.md-typeset .admonition.tip > .admonition-title {
  background-color: rgba(64, 81, 181, 0.1);
  color: #4051b5;
}

.md-typeset .admonition.tip > .admonition-title::before {
  background-color: #4051b5;
  -webkit-mask-image: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>');
  mask-image: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>');
}
```

Usage in Markdown:

```markdown
!!! tip "Custom Tip"
    This uses your brand color!
```

---

## Custom Icons and Logos

### SVG logo

Use an SVG for crisp rendering at any size:

```yaml
theme:
  logo: assets/logo.svg
```

The SVG should be optimized and have `viewBox` for proper scaling.

### Custom icon definitions

Define custom icons in `extra.css`:

```css
.md-icon--custom::after {
  content: "";
  display: inline-block;
  width: 1em;
  height: 1em;
  background-image: url("assets/custom-icon.svg");
  background-size: contain;
  vertical-align: middle;
}
```

---

## Custom Fonts

### Self-hosted fonts

Place font files in `docs/assets/fonts/` and define them in CSS:

```css
@font-face {
  font-family: 'CustomFont';
  src: url('../assets/fonts/CustomFont.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

:root {
  --md-text-font: 'CustomFont', 'Roboto', sans-serif;
}
```

---

## Custom 404 Page

Create `docs/overrides/404.html`:

```html
{% extends "base.html" %}

{% block content %}
  <div class="md-content__inner">
    <h1>404 — Page Not Found</h1>
    <p>The page you requested doesn't exist.</p>
    <a href="{{ nav.homepage.url | url }}" class="md-button md-button--primary">
      Go Home
    </a>
  </div>
{% endblock %}
```

---

## Performance Tuning

### Lazy loading images

Images are lazy-loaded by default. For above-the-fold images, use `loading="eager"`:

```markdown
![Hero image](hero.png){ loading=eager }
```

### Image optimization

Optimize images before adding them to `docs/`:

```bash
# Convert to WebP for smaller size
ffmpeg -i image.png image.webp

# Or use ImageMagick
convert image.png -quality 85 image.webp
```

### Preload critical resources

```html
{% block extrahead %}
  {{ super() }}
  <link rel="preload" href="{{ 'assets/fonts/CustomFont.woff2' | url }}" as="font" type="font/woff2" crossorigin>
{% endblock %}
```

---

## Accessibility

### Color contrast

Ensure your custom colors meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text). Test with a contrast checker.

### Keyboard navigation

DocsForge supports keyboard navigation out of the box. Custom interactive elements should handle `Tab`, `Enter`, and `Escape` keys.

### ARIA labels

```html
<button class="md-button" aria-label="Close announcement">
  <span class="md-icon">close</span>
</button>
```

---

## Multi-language Sites

DocsForge includes a built-in internationalization plugin via `material/i18n`. See [Internationalization setup](../setup/i18n.md) for details.

If the built-in plugin doesn't fit your workflow, you can also use one of these alternatives:

### Option 1: Build separate sites per language

Maintain a `docsforge.yml` for each language and build them independently:

```
docs/
├── en/
│   └── index.md
├── de/
│   └── index.md
└── fr/
    └── index.md
```

Use a small build script to output each language to a separate subdirectory.

### Option 2: Use a third-party i18n plugin

Install an MkDocs-compatible i18n plugin and declare it under `plugins:`:

```yaml
plugins:
  - i18n:
      languages:
        - locale: en
          name: English
          default: true
        - locale: de
          name: Deutsch
        - locale: fr
          name: Français
```

!!! warning "Compatibility"
    Third-party MkDocs plugins may need to be adapted for DocsForge. Test thoroughly before relying on them in production.

---

## Analytics Integration

### Google Analytics 4

```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

### Plausible

```yaml
extra:
  analytics:
    provider: plausible
    property: docs.example.com
```

### Custom analytics

```html
{% block extrahead %}
  {{ super() }}
  <script async src="https://analytics.example.com/script.js" data-site="YOUR_SITE_ID"></script>
{% endblock %}
```

---

## Social Cards

DocsForge does not auto-generate social card images, but it does set basic OpenGraph tags. For a custom card image, add it manually in a template override:

```html
{% block extrahead %}
  {{ super() }}
  <meta property="og:title" content="{{ page.title | default(config.site_name) }}">
  <meta property="og:description" content="{{ page.meta.description | default(config.site_description) }}">
  <meta property="og:image" content="{{ config.site_url }}assets/social-card.png">
  <meta name="twitter:card" content="summary_large_image">
{% endblock %}
```

---

## Build Hooks

`hooks` are Python modules that act like mini-plugins. Each file listed under `hooks:` is imported and can implement `on_pre_build` and/or `on_post_build` events.

```yaml
hooks:
  - scripts/hooks.py
```

Create `docs/scripts/hooks.py`:

```python
import os


def on_pre_build(*, config):
    """Run before DocsForge starts building pages."""
    print("Pre-build hook running...")


def on_post_build(*, config):
    """Run after DocsForge has written the site directory."""
    print(f"Site built at: {config.site_dir}")
```

!!! note "Shell scripts"
    If you need to run a shell command, invoke it from the Python hook with `subprocess.run(["..."])`.

## Custom Plugins

For functionality that spans multiple events or needs its own configuration, write a full plugin by subclassing `docsforge.core.plugin_base.BasePlugin`.

```python
from docsforge.config_base import Config
from docsforge.config_options import Type
from docsforge.core.plugin_base import BasePlugin


class MyPluginConfig(Config):
    enabled = Type(bool, default=True)


class MyPlugin(BasePlugin[MyPluginConfig]):
    def on_page_markdown(self, markdown, *, page, config, files):
        if not self.config.enabled:
            return markdown
        return markdown.replace("{{year}}", "2026")
```

Register the plugin in `docsforge.yml`:

```yaml
plugins:
  - my_plugin:
      enabled: true
```

DocsForge uses the same event names as MkDocs (`on_page_markdown`, `on_page_content`, `on_post_build`, etc.). If you are migrating an MkDocs plugin, change the import from `mkdocs.plugins` to `docsforge.core.plugin_base` and use DocsForge's `Config` class for the plugin's options.

