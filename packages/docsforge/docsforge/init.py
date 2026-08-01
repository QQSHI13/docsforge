"""DocsForge init command - interactive setup wizard."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

COLOR_MAP = {
    'teal': {'primary': 'teal', 'accent': 'teal'},
    'indigo': {'primary': 'indigo', 'accent': 'indigo'},
    'blue': {'primary': 'blue', 'accent': 'blue'},
    'green': {'primary': 'green', 'accent': 'green'},
    'red': {'primary': 'red', 'accent': 'red'},
    'orange': {'primary': 'orange', 'accent': 'orange'},
    'purple': {'primary': 'purple', 'accent': 'purple'},
    'pink': {'primary': 'pink', 'accent': 'pink'},
}


def _generate_config(
    site_name: str,
    site_url: str | None,
    theme_color: str,
    privacy: bool,
    author_name: str | None = None,
    repo_url: str | None = None,
    site_description: str | None = None,
    language: str = 'en',
    copyright: str | None = None,
    favicon: str | None = None,
    logo: str | None = None,
) -> str:
    """Generate docsforge.yml content with all core features enabled."""

    color = COLOR_MAP.get(theme_color, COLOR_MAP['teal'])

    config: dict = {
        'site_name': site_name,
    }

    if site_description:
        config['site_description'] = site_description

    if site_url:
        config['site_url'] = site_url

    if copyright:
        config['copyright'] = copyright

    if repo_url:
        config['repo_url'] = repo_url
        config['edit_uri'] = 'edit/main/docs/'

    theme: dict = {
        'name': 'material',
        'palette': [
            {
                'scheme': 'default',
                'primary': color['primary'],
                'accent': color['accent'],
                'toggle': {
                    'icon': 'material/brightness-7',
                    'name': 'Switch to dark mode',
                },
            },
            {
                'scheme': 'slate',
                'primary': color['primary'],
                'accent': color['accent'],
                'toggle': {
                    'icon': 'material/brightness-4',
                    'name': 'Switch to light mode',
                },
            },
        ],
        'language': language,
    }

    if favicon:
        theme['favicon'] = favicon
    if logo:
        theme['logo'] = logo

    config['theme'] = theme

    if privacy:
        config['privacy'] = True

    if author_name:
        config['extra'] = {'author': author_name}

    config['extra_css'] = ['stylesheets/extra.css']
    config['extra_javascript'] = ['javascripts/extra.js']
    config['nav'] = [
        {'Home': 'index.md'},
        {'Getting Started': 'getting-started.md'},
        {'Blog': ['blog/index.md']},
    ]

    return yaml.dump(config, sort_keys=False, default_flow_style=False, allow_unicode=True)


def _generate_github_workflow(site_url: str | None) -> str:
    """Generate GitHub Pages deployment workflow."""
    return '''name: Deploy Docs

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: 3.x
      - run: pip install docsforge
      - run: docsforge build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
'''


def _generate_readme(site_name: str) -> str:
    """Generate README.md content."""
    return f'''# {site_name}

Documentation built with [DocsForge](https://qqshi13.github.io/docsforge/).

## Quick Start

```bash
# Install DocsForge
pip install docsforge

# Start development server
docsforge serve

# Build for production
docsforge build
```

## Project Structure

```
.
├── docs/              # Documentation source files
│   ├── blog/          # Blog posts
│   ├── stylesheets/   # Custom CSS
│   ├── javascripts/   # Custom JavaScript
│   └── index.md       # Homepage
├── docsforge.yml      # Site configuration
└── .github/
    └── workflows/     # Deployment automation
```

## Writing Documentation

- Edit `docs/index.md` to customize the homepage
- Add pages by creating `.md` files in `docs/`
- Add blog posts in `docs/blog/posts/YYYY-MM-DD-title.md`
- Use tags by adding `tags: [tag1, tag2]` in front matter
- Organize navigation in `docsforge.yml`

## Deployment

Pushes to `main` automatically deploy to GitHub Pages via the workflow in `.github/workflows/pages.yml`.
'''


def _generate_gitignore() -> str:
    """Generate .gitignore for DocsForge projects."""
    return '''# DocsForge build output
site/

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/

# Virtual environments
venv/
.env/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
'''


def _generate_extra_css() -> str:
    """Generate extra.css with useful defaults."""
    return '''/* Custom styles for your documentation */

/* Increase content width on large screens */
.md-grid {
  max-width: 1440px;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Custom hover effect for links */
.md-content a:hover {
  text-decoration: underline;
}
'''


def _generate_extra_js() -> str:
    """Generate extra.js with useful defaults."""
    return '''// Custom JavaScript for your documentation

// Add keyboard shortcut for search (Cmd/Ctrl + K)
document.addEventListener('keydown', function(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    document.querySelector('[data-md-component=search]').focus();
  }
});
'''


def _generate_authors_yml(author_name: str | None = None) -> str:
    """Generate blog authors configuration."""
    name = author_name or "Author Name"
    return f'''# Blog authors configuration
# Add your authors here, then reference them in blog posts

authors:
  default:
    name: {name}
    description: Brief bio
    avatar: https://github.com/username.png
'''


def _generate_blog_post() -> str:
    """Generate a demo blog post."""
    return '''---
date: 2026-01-01
authors:
  - default
tags:
  - hello
  - docsforge
---

# Hello World

Welcome to your new DocsForge blog! This is a demo post to get you started.

## What's Next?

- Edit this post at `docs/blog/posts/2026-01-01-hello-world.md`
- Create new posts following the `YYYY-MM-DD-title.md` naming convention
- Add authors in `docs/blog/posts/.authors.yml`
- Tag posts with `tags: [tag1, tag2]` in the front matter

## Features

DocsForge blog supports:

- **Authors** with avatars and bios
- **Tags** for categorization
- **Archive** by year and month
- **RSS feeds** automatically generated
- **Related posts** based on tags
'''


def _generate_getting_started() -> str:
    """Generate getting-started.md content."""
    return '''# Getting Started

This guide helps you get the most out of DocsForge.

## Writing Content

DocsForge uses Markdown with extended syntax:

### Admonitions (Callouts)

!!! note "Note"
    This is a note callout. Use `!!! note`, `!!! warning`, `!!! tip`, etc.

!!! warning "Warning"
    This is a warning callout for important information.

!!! tip "Tip"
    Tips provide helpful suggestions.

### Code Blocks

```python
# Syntax highlighting with Pygments
print("Hello, DocsForge!")
```

### Math

Inline math: $E = mc^2$

Display math:
$$\\frac{\\partial f}{\\partial x} = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}$$

### Diagrams

```mermaid
graph LR
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
```

### Tags

Add tags to any page in the front matter:

```yaml
---
tags:
  - tutorial
  - getting-started
---
```

## Customization

- **Colors**: Edit `theme.palette` in `docsforge.yml`
- **CSS**: Add rules to `docs/stylesheets/extra.css`
- **JavaScript**: Add scripts to `docs/javascripts/extra.js`
- **Fonts**: Configure `theme.font` in `docsforge.yml`

## Navigation

Control the sidebar navigation in `docsforge.yml`:

```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Reference:
    - API: api.md
    - CLI: cli.md
```
'''


def _generate_index(site_name: str, author_name: str | None = None, repo_url: str | None = None) -> str:
    """Generate index.md content."""
    lines = [f"# Welcome to {site_name}"]
    
    if author_name:
        lines.append(f"\nBy **{author_name}**")
    
    if repo_url:
        lines.append(f'\n[:fontawesome-brands-github: Repository]({repo_url})')
    
    lines.append("""
This documentation is built with [DocsForge](https://qqshi13.github.io/docsforge/).

## Getting Started

New to DocsForge? Check out the [Getting Started](getting-started.md) guide for a full tour of features.

## Quick Reference

| Command | Description |
|---------|-------------|
| `docsforge serve` | Start live-reloading dev server |
| `docsforge build` | Build for production |
| `docsforge check` | Validate configuration |

## Features

DocsForge includes everything you need out of the box:

- 📝 **Markdown** with 31 extensions
- 🎨 **Material theme** with dark mode
- 🔍 **Full-text search** built-in
- ➗ **Math rendering** with KaTeX
- 📐 **Diagrams** with Mermaid and TikZ
- 📱 **Offline support** with service worker
- 🏷️ **Tags** for organizing content
- 📰 **Blog** for announcements and changelogs
- 🔒 **Privacy** mode (external assets inlined locally)
- 📊 **Info banners** for highlighting content
- 🌐 **Social cards** for link previews
- ⚡ **Minification** for production builds
- 🖼️ **Image optimization** for faster loading
""")
    return "\n".join(lines)


def _generate_blog_index() -> str:
    """Generate blog/index.md content."""
    return """# Blog

Welcome to the blog! Posts go in the `docs/blog/posts/` directory.

## Creating Posts

1. Create a file: `docs/blog/posts/YYYY-MM-DD-post-title.md`
2. Add front matter:
   ```yaml
   ---
   date: 2026-05-31
   authors:
     - your-name
   ---
   ```
3. Write your content in Markdown

Posts are automatically listed here.
"""


def init(
    project_directory: str,
    site_name: str,
    site_url: str | None,
    theme_color: str,
    privacy: bool,
    author_name: str | None = None,
    repo_url: str | None = None,
    site_description: str | None = None,
    language: str = 'en',
    copyright: str | None = None,
    favicon: str | None = None,
    logo: str | None = None,
) -> None:
    """Create a new DocsForge project with interactive configuration.

    All core features (search, tags, blog, info, meta, minify, social, optimize)
    are always enabled. Privacy is the only optional feature.
    """
    
    output_dir = Path(project_directory)
    docs_dir = output_dir / 'docs'
    config_path = output_dir / 'docsforge.yml'
    index_path = docs_dir / 'index.md'
    
    # Create directories
    if not output_dir.exists():
        log.info(f'Creating project directory: {output_dir}')
        output_dir.mkdir(parents=True)
    
    if not docs_dir.exists():
        docs_dir.mkdir()
    
    # Write config
    if config_path.exists():
        log.warning(f'{config_path} already exists. Skipping config creation.')
    else:
        log.info(f'Writing configuration: {config_path}')
        config_content = _generate_config(
            site_name=site_name,
            site_url=site_url,
            theme_color=theme_color,
            privacy=privacy,
            author_name=author_name,
            repo_url=repo_url,
            site_description=site_description,
            language=language,
            copyright=copyright,
            favicon=favicon,
            logo=logo,
        )
        config_path.write_text(config_content, encoding='utf-8')
    
    # Write index.md
    if index_path.exists():
        log.warning(f'{index_path} already exists. Skipping index creation.')
    else:
        log.info(f'Writing homepage: {index_path}')
        index_path.write_text(_generate_index(site_name, author_name, repo_url), encoding='utf-8')
    
    # Write getting-started.md
    getting_started_path = docs_dir / 'getting-started.md'
    if not getting_started_path.exists():
        log.info(f'Writing guide: {getting_started_path}')
        getting_started_path.write_text(_generate_getting_started(), encoding='utf-8')
    
    # Write blog index and directories
    blog_dir = docs_dir / 'blog'
    posts_dir = blog_dir / 'posts'
    blog_index_path = blog_dir / 'index.md'
    
    if not blog_dir.exists():
        blog_dir.mkdir()
    if not posts_dir.exists():
        posts_dir.mkdir()
    
    if not blog_index_path.exists():
        blog_index_path.write_text(_generate_blog_index(), encoding='utf-8')
    
    # Write demo blog post
    blog_post_path = posts_dir / '2026-01-01-hello-world.md'
    if not blog_post_path.exists():
        log.info(f'Writing demo blog post: {blog_post_path}')
        blog_post_path.write_text(_generate_blog_post(), encoding='utf-8')
    
    # Write blog authors config
    authors_path = posts_dir / '.authors.yml'
    if not authors_path.exists():
        authors_path.write_text(_generate_authors_yml(author_name), encoding='utf-8')
    
    # Write stylesheets
    stylesheets_dir = docs_dir / 'stylesheets'
    if not stylesheets_dir.exists():
        stylesheets_dir.mkdir()
    css_path = stylesheets_dir / 'extra.css'
    if not css_path.exists():
        log.info(f'Writing stylesheet: {css_path}')
        css_path.write_text(_generate_extra_css(), encoding='utf-8')
    
    # Write javascripts
    javascripts_dir = docs_dir / 'javascripts'
    if not javascripts_dir.exists():
        javascripts_dir.mkdir()
    js_path = javascripts_dir / 'extra.js'
    if not js_path.exists():
        log.info(f'Writing JavaScript: {js_path}')
        js_path.write_text(_generate_extra_js(), encoding='utf-8')
    
    # Write README.md
    readme_path = output_dir / 'README.md'
    if not readme_path.exists():
        log.info(f'Writing README: {readme_path}')
        readme_path.write_text(_generate_readme(site_name), encoding='utf-8')
    
    # Write .gitignore
    gitignore_path = output_dir / '.gitignore'
    if not gitignore_path.exists():
        log.info(f'Writing .gitignore: {gitignore_path}')
        gitignore_path.write_text(_generate_gitignore(), encoding='utf-8')
    
    # Write GitHub workflow
    github_dir = output_dir / '.github' / 'workflows'
    if not github_dir.exists():
        github_dir.mkdir(parents=True)
    workflow_path = github_dir / 'pages.yml'
    if not workflow_path.exists():
        log.info(f'Writing GitHub workflow: {workflow_path}')
        workflow_path.write_text(_generate_github_workflow(site_url), encoding='utf-8')
    
    # Print summary
    print()
    print("=" * 60)
    print("  PROJECT CREATED")
    print("=" * 60)
    print()
    print(f"  Directory:     {output_dir.absolute()}")
    print(f"  Site name:     {site_name}")
    if site_url:
        print(f"  Site URL:      {site_url}")
    print(f"  Theme color:   {theme_color}")
    print(f"  Privacy:       {'✓ enabled' if privacy else '✗ disabled'}")
    print()
    print("  Core features (always enabled):")
    print("    ✓ Search      ✓ Tags      ✓ Blog")
    print("    ✓ Info        ✓ Meta      ✓ Minify")
    print("    ✓ Social      ✓ Optimize")
    print()
    print("  Files created:")
    print("    docsforge.yml        - Site configuration")
    print("    docs/index.md        - Homepage")
    print("    docs/getting-started.md - Feature guide")
    print("    docs/blog/           - Blog with demo post")
    print("    docs/stylesheets/    - Custom CSS")
    print("    docs/javascripts/    - Custom JavaScript")
    print("    .github/workflows/   - GitHub Pages deployment")
    print("    README.md            - Project readme")
    print("    .gitignore           - Git ignore rules")
    print()
    print("  Next steps:")
    print(f"    cd {output_dir}")
    print("    docsforge serve")
    print()
    print("  Documentation: https://qqshi13.github.io/docsforge/")
    print()
