---
description: DocsForge demo showcasing all built-in features and plugins
tags:
  - demo
  - overview
---

# DocsForge Stress Test

<img src="images/docsforge.png" alt="DocsForge Logo" width="200">

Welcome to the **DocsForge** stress test! This site exercises every built-in feature.

!!! abstract "Featured Article"
    **[Shannon's "A Mathematical Theory of Communication"](shannon-paper/index.md)** — A comprehensive, in-depth walkthrough of Claude Shannon's foundational 1948 paper. Every section and appendix is documented with full mathematical derivations, Mermaid diagrams, and TiKz illustrations.

---

## Admonitions (All Types)

!!! note "Note"
    Standard note callout for general information.

!!! abstract "Abstract"
    Abstract provides a summary or tl;dr.

!!! info "Info"
    Info blocks highlight useful information.

!!! tip "Tip"
    Tips provide helpful suggestions and best practices.

!!! success "Success"
    Success blocks confirm something worked correctly.

!!! question "Question"
    Question blocks highlight something to consider or ask.

!!! warning "Warning"
    Warnings highlight potential issues or caution areas.

!!! failure "Failure"
    Failure blocks show what not to do or what went wrong.

!!! danger "Danger"
    Danger blocks highlight critical warnings that could cause data loss.

!!! bug "Bug"
    Bug blocks document known issues or defects.

!!! example "Example"
    Example blocks provide concrete illustrations.

!!! quote "Quote"
    Quote blocks display citations or testimonials.

### Collapsible Admonitions

??? note "Click to expand"
    This content is hidden by default. Use `???` for collapsible callouts.

???+ tip "Starts expanded"
    This admonition is open by default. Use `???+` for expanded-by-default callouts.

??? warning nested "Nested collapsible"
    ??? danger "Inner collapse"
        Even nested collapsibles work!

---

## Math Rendering (KaTeX)

### Inline Math

Einstein's famous equation: $E = mc^2$

Schrödinger equation: $i\hbar\frac{\partial}{\partial t}\Psi(r,t) = \hat{H}\Psi(r,t)$

Fourier transform: $\hat{f}(\xi) = \int_{-\infty}^{\infty} f(x)e^{-2\pi ix\xi}dx$

### Display Math

**Quadratic formula:**

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

**Maxwell's equations:**

$$
\begin{aligned}
\nabla \cdot \mathbf{E} &= \frac{\rho}{\varepsilon_0} \\
\nabla \cdot \mathbf{B} &= 0 \\
\nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \\
\nabla \times \mathbf{B} &= \mu_0\mathbf{J} + \mu_0\varepsilon_0\frac{\partial \mathbf{E}}{\partial t}
\end{aligned}
$$

**Matrix operations:**

$$
\mathbf{A} = \begin{bmatrix}
a_{11} & a_{12} & a_{13} \\
a_{21} & a_{22} & a_{23} \\
a_{31} & a_{32} & a_{33}
\end{bmatrix},
\quad
\mathbf{A}^{-1} = \frac{1}{\det(\mathbf{A})}\mathbf{C}^\top
$$

**Calculus:**

$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

$$
\frac{d}{dx}\left(\int_{a(x)}^{b(x)} f(t) dt\right) = f(b(x))b'(x) - f(a(x))a'(x)
$$

**Statistics:**

$$
\sigma = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^2}
$$

$$
P(A|B) = \frac{P(B|A)P(A)}{P(B)}
$$

---

## Code Highlighting (Pygments)

### Python

```python
class DocsForge:
    """Self-contained documentation engine."""
    
    def __init__(self, config_path: str = "docsforge.yml"):
        self.config = self._load_config(config_path)
        self.plugins = self._load_plugins()
    
    def build(self, site_dir: str = "site") -> bool:
        """Build documentation to static HTML."""
        try:
            self._render_pages()
            self._copy_assets()
            self._run_post_hooks()
            return True
        except BuildError as e:
            log.error(f"Build failed: {e}")
            return False
    
    @property
    def version(self) -> str:
        return __version__
```

### JavaScript/TypeScript

```typescript
interface DocsForgeConfig {
    site_name: string;
    theme: ThemeConfig;
    plugins?: PluginConfig[];
}

class DocsForgeBuilder {
    private config: DocsForgeConfig;
    
    constructor(config: DocsForgeConfig) {
        this.config = config;
    }
    
    async build(): Promise<BuildResult> {
        const pages = await this.renderPages();
        const assets = await this.copyAssets();
        return { pages, assets, success: true };
    }
}
```

### Rust

```rust
use std::path::PathBuf;

pub struct DocsForge {
    config: Config,
    plugins: Vec<Box<dyn Plugin>>,
}

impl DocsForge {
    pub fn new(config_path: &str) -> Result<Self, ConfigError> {
        let config = Config::load(config_path)?;
        let plugins = PluginManager::load_all(&config)?;
        Ok(Self { config, plugins })
    }
    
    pub fn build(&self, output_dir: PathBuf) -> Result<(), BuildError> {
        self.render_pages(&output_dir)?;
        self.copy_assets(&output_dir)?;
        Ok(())
    }
}
```

### Go

```go
package main

import (
    "fmt"
    "os"
)

type Config struct {
    SiteName string `yaml:"site_name"`
    Theme    string `yaml:"theme"`
}

func Build(configPath, outputDir string) error {
    cfg, err := LoadConfig(configPath)
    if err != nil {
        return fmt.Errorf("load config: %w", err)
    }
    
    if err := RenderPages(cfg, outputDir); err != nil {
        return fmt.Errorf("render: %w", err)
    }
    
    return CopyAssets(outputDir)
}
```

### Bash

```bash
#!/bin/bash
set -euo pipefail

DOCSFORGE_VERSION="10.1.0"
SITE_DIR="site"

echo "Building DocsForge v${DOCSFORGE_VERSION}..."

# Clean previous build
rm -rf "${SITE_DIR}"

# Build documentation
docsforge build --site-dir "${SITE_DIR}"

# Verify output
if [[ -f "${SITE_DIR}/index.html" ]]; then
    echo "Build successful!"
    exit 0
else
    echo "Build failed!"
    exit 1
fi
```

### SQL

```sql
-- Create documentation pages table
CREATE TABLE pages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for tag search
CREATE INDEX idx_pages_tags ON pages USING GIN (tags);

-- Get all pages with specific tag
SELECT title, slug, updated_at 
FROM pages 
WHERE 'docsforge' = ANY(tags)
ORDER BY updated_at DESC;
```

### YAML

```yaml
site_name: DocsForge Demo
theme:
  name: material
  palette:
    - scheme: default
      primary: teal
      accent: teal
plugins:
  - search
  - tags
  - blog
markdown_extensions:
  - admonition
  - pymdownx.highlight
  - pymdownx.superfences
```

---

## Content Tabs

=== "Python"
    ```python
    print("Hello from Python!")
    ```

=== "JavaScript"
    ```javascript
    console.log("Hello from JS!");
    ```

=== "Rust"
    ```rust
    println!("Hello from Rust!");
    ```

---

## Tables

### Simple Table

| Feature | Status | Notes |
|---------|--------|-------|
| Search | :material-check-circle: | Full-text with Lunr.js |
| Tags | :material-check-circle: | Auto-generated tag pages |
| Blog | :material-check-circle: | Authors, categories, archives |
| Privacy | :material-check-circle: | Self-hosted fonts |
| Minify | :material-check-circle: | HTML/CSS/JS compression |
| Math | :material-check-circle: | KaTeX built-in |
| Highlight | :material-check-circle: | Pygments at build time |

### Complex Table

| Language | Extension | Supported | Performance | Notes |
|----------|-----------|-----------|-------------|-------|
| Python | `.py` | :material-check-circle: Native | Excellent | Full Pygments support |
| JavaScript | `.js`, `.ts` | :material-check-circle: Native | Excellent | JSX/TSX supported |
| Rust | `.rs` | :material-check-circle: Native | Excellent | Full syntax coverage |
| Go | `.go` | :material-check-circle: Native | Excellent | Go templates too |
| SQL | `.sql` | :material-check-circle: Native | Good | All major dialects |
| Bash | `.sh` | :material-check-circle: Native | Good | POSIX + Bash |
| YAML | `.yml` | :material-check-circle: Native | Good | Front matter aware |
| JSON | `.json` | :material-check-circle: Native | Excellent | Schema validation |

### Wide Table

| Feature | Markdown | PyMdownX | Python-Markdown | KaTeX | Pygments | Plugin | Config Required |
|---------|----------|----------|-----------------|-------|----------|--------|-----------------|
| Admonitions | `!!!` | `details` | `admonition` | — | — | `info` | No |
| Math | — | `arithmatex` | — | `$$` | — | — | No |
| Code Highlight | ` ``` ` | `superfences` | `fenced_code` | — | `highlight` | — | No |
| Tables | `\|` | — | `tables` | — | — | — | No |
| Footnotes | `[^1]` | — | `footnotes` | — | — | — | No |
| Task Lists | `- [x]` | `tasklist` | — | — | — | — | No |
| Definition Lists | `:` | — | `def_list` | — | — | — | No |
| Abbreviations | `*[abbr]` | — | `abbr` | — | — | — | No |

---

## Task Lists

### Setup Checklist

- [x] Install DocsForge (`pip install docsforge`)
- [x] Create new project (`docsforge new my-docs`)
- [x] Write first page (`docs/index.md`)
- [x] Start dev server (`docsforge serve`)
- [x] Verify all features work
- [x] Build for production (`docsforge build`)
- [ ] Deploy to GitHub Pages
- [ ] Share with team
- [ ] Write blog post about it

### Feature Checklist

- [x] Admonitions (all 12 types)
- [x] Math (inline + display)
- [x] Code highlighting (8+ languages)
- [x] Tables (simple + complex)
- [x] Content tabs
- [x] Task lists
- [x] Footnotes
- [x] Definition lists
- [x] Abbreviations
- [x] Emojis
- [x] Blog posts
- [x] Tags
- [x] Search
- [x] Dark mode toggle
- [x] Privacy (self-hosted fonts)
- [x] Minification

---

## Footnotes

DocsForge includes powerful features by default[^1]. The `privacy` plugin downloads external assets[^2], while `minify` compresses output[^3].

[^1]: All 36 Markdown extensions and 8 core plugins load automatically; social cards are opt-in.
[^2]: Google Fonts, CDN scripts, and other external resources are cached locally during build.
[^3]: HTML, CSS, and JavaScript are minified at build time with no configuration needed.

---

## Definition Lists

DocsForge
:   A self-contained documentation engine that bundles Material theme, all plugins, and all extensions into a single installable package.

Material for MkDocs
:   The world's most popular documentation theme, created by Martin Donath. DocsForge vendors it for zero-config usage.

PyMdownX
:   A collection of Markdown extensions that add advanced syntax like admonitions, superfences, and task lists.

Pygments
:   A syntax highlighting library written in Python. DocsForge uses it for build-time code highlighting.

KaTeX
:   A fast math typesetting library. DocsForge vendors it for zero-config math rendering.

---

## Abbreviations

DocsForge uses the HTML spec maintained by the W3C. Styling is done via CSS, and interactivity with JS.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium
*[CSS]: Cascading Style Sheets
*[JS]: JavaScript
*[API]: Application Programming Interface
*[CI/CD]: Continuous Integration / Continuous Deployment
*[SEO]: Search Engine Optimization

---

## Emojis

:material-heart: DocsForge is built with love.

:material-rocket-launch: Zero to docs in seconds.

:material-package-variant-closed: Everything is bundled.

:material-magnify: Search works out of the box.

:material-theme-light-dark: Dark mode included.

:material-code-tags: Syntax highlighting for all languages.

:material-function-variant: Math rendering with KaTeX.

:material-check-circle: All features work without configuration.

---

## Blockquotes

> "Documentation is a love letter that you write to your future self."
> — *Damian Conway*

> "The best documentation is the documentation that gets written."
> — *DocsForge Philosophy*

> The `privacy` plugin ensures your documentation works offline by downloading and caching external assets during the build process. This includes Google Fonts, CDN scripts, and other external resources.

---

## Horizontal Rules

Above the first rule.

---

Between two rules.

---

Below the second rule.

---

## HTML in Markdown

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } &nbsp; **Fast Builds**

    ---

    Documentation builds in under a second.

-   :material-package-variant-closed:{ .lg .middle } &nbsp; **Self-Contained**

    ---

    No external dependencies after installation.

-   :material-magnify:{ .lg .middle } &nbsp; **Full Search**

    ---

    Client-side search with Lunr.js index.

</div>

---

## Nested Structures

### Lists within Admonitions

!!! tip "Nested Content"
    You can nest lists inside admonitions:
    
    1. First step
    2. Second step
        - Sub-item A
        - Sub-item B
    3. Third step
    
    And even code:
    
    ```python
    print("Hello from inside a tip!")
    ```

### Admonitions within Lists

1. First item

    !!! note "Note in list"
        This admonition is inside a list item.

2. Second item

    ```python
    # Code in list
    x = 42
    ```

3. Third item with table

    | Col 1 | Col 2 |
    |-------|-------|
    | A     | B     |
    | C     | D     |

---

## Critic Markup

This is {++added++} text and this is {--removed--} text.

Here is a {~~substitution~>replacement~~}.

And a {==highlight==}{>>with a comment<<}.

---

## Keys

Press ++ctrl+c++ to copy.

Press ++ctrl+v++ to paste.

Press ++ctrl+alt+delete++ to open Task Manager.

Use ++arrow-up++ and ++arrow-down++ to navigate.

---

## Mark and Tilde

This is ==marked text== for highlighting.

This is ~~deleted text~~ for strikethrough.

This is ^superscript^ and ~subscript~.

---

## Snippets

--8<-- "features.md"
