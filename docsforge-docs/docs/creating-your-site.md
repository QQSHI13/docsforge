# Creating your site

## Project structure

``` { .sh .no-copy }
my-docs/
├── docsforge.yml      # Site configuration
├── docs/                # Your documentation
│   ├── index.md
│   └── ...
└── site/                # Build output (auto-generated)
```

### The `docs/` directory

Every `.md` file becomes a page. Subdirectories become sections.

``` { .sh .no-copy }
docs/
├── index.md
├── getting-started.md
├── guides/
│   ├── index.md
│   ├── install.md
│   └── configure.md
└── reference/
    ├── index.md
    └── api.md
```

### The `docsforge.yml` file

Minimal config:

```yaml
site_name: My Project
```

With navigation:

```yaml
site_name: My Project

nav:
  - Home: index.md
  - Guides:
    - Installation: guides/install.md
    - Configuration: guides/configure.md
  - Reference: reference/index.md
```

## Writing content

DocsForge supports **all** Material-flavored Markdown out of the box. No extension config needed.

### Admonitions

```markdown
!!! note "Note"
    This is a callout.

??? warning "Click to expand"
    This is collapsible.
```

### Math

```markdown
Inline: $E = mc^2$

Display:
$$\sum_{i=1}^n x_i$$
```

### Code blocks

```markdown
```python
def hello():
    print("Hello")
```
```

### Tables, task lists, footnotes, definition lists

All work without configuration. See [Reference](reference/index.md) for full syntax.

## Building

```bash
docsforge serve      # Dev server with live reload
docsforge build      # Production build to site/
```

## Publishing

DocsForge builds static HTML. Deploy `site/` anywhere:

- **GitHub Pages**: See [publishing guide](publishing-your-site.md)
- **Netlify, Vercel**: Drag and drop `site/`
- **Your own server**: `rsync -av site/ server:/var/www/docs`
