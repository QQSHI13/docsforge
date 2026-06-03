"""DocsForge init command - interactive setup wizard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

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


def _generate_config(site_name: str, site_url: str | None, theme_color: str,
                     enable_blog: bool, enable_search: bool, enable_tags: bool) -> str:
    """Generate docsforge.yml content based on user choices."""
    
    color = COLOR_MAP.get(theme_color, COLOR_MAP['teal'])
    
    lines = [
        f'site_name: {site_name}',
    ]
    
    if site_url:
        lines.append(f'site_url: {site_url}')
    
    lines.append('')
    lines.append('theme:')
    lines.append('  name: material')
    lines.append('  palette:')
    lines.append('    - media: "(prefers-color-scheme: light)"')
    lines.append('      scheme: default')
    lines.append(f"      primary: {color['primary']}")
    lines.append(f"      accent: {color['accent']}")
    lines.append('      toggle:')
    lines.append('        icon: material/brightness-7')
    lines.append('        name: Switch to dark mode')
    lines.append('    - media: "(prefers-color-scheme: dark)"')
    lines.append('      scheme: slate')
    lines.append(f"      primary: {color['primary']}")
    lines.append(f"      accent: {color['accent']}")
    lines.append('      toggle:')
    lines.append('        icon: material/brightness-4')
    lines.append('        name: Switch to light mode')
    lines.append('')
    
    # Plugins section
    plugins = []
    if enable_search:
        plugins.append('search')
    if enable_tags:
        plugins.append('tags')
    if enable_blog:
        plugins.append('blog')
    
    if plugins:
        lines.append('plugins:')
        for plugin in plugins:
            lines.append(f'  - {plugin}')
        lines.append('')
    
    # Nav section
    lines.append('nav:')
    lines.append('  - Home: index.md')
    
    if enable_blog:
        lines.append('  - Blog:')
        lines.append('    - blog/index.md')
    
    lines.append('')
    
    return '\n'.join(lines)


def _generate_index(site_name: str) -> str:
    """Generate index.md content."""
    return f"""# Welcome to {site_name}

This documentation is built with [DocsForge](https://qqshi13.github.io/docsforge-docs/).

## Getting Started

Edit this file at `docs/index.md` to add your content.

## Commands

- `docsforge serve` - Start live-reloading dev server
- `docsforge build` - Build for production
- `docsforge check` - Validate configuration

## Features

DocsForge includes everything you need out of the box:

- 📝 **Markdown** with 31 extensions
- 🎨 **Material theme** with dark mode
- 🔍 **Full-text search** built-in
- ➗ **Math rendering** with KaTeX
- 📐 **Diagrams** with Mermaid and TikZ
- 📱 **Offline support** with service worker
"""


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


def init(project_directory: str, site_name: str, site_url: str | None,
         theme_color: str, enable_blog: bool, enable_search: bool,
         enable_tags: bool) -> None:
    """Create a new DocsForge project with interactive configuration."""
    
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
            enable_blog=enable_blog,
            enable_search=enable_search,
            enable_tags=enable_tags,
        )
        config_path.write_text(config_content, encoding='utf-8')
    
    # Write index.md
    if index_path.exists():
        log.warning(f'{index_path} already exists. Skipping index creation.')
    else:
        log.info(f'Writing homepage: {index_path}')
        index_path.write_text(_generate_index(site_name), encoding='utf-8')
    
    # Write blog index if blog enabled
    if enable_blog:
        blog_dir = docs_dir / 'blog'
        posts_dir = blog_dir / 'posts'
        blog_index_path = blog_dir / 'index.md'
        
        if not blog_dir.exists():
            blog_dir.mkdir()
        if not posts_dir.exists():
            posts_dir.mkdir()
        
        if not blog_index_path.exists():
            blog_index_path.write_text(_generate_blog_index(), encoding='utf-8')
    
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
    print(f"  Search:        {'✓' if enable_search else '✗'}")
    print(f"  Tags:          {'✓' if enable_tags else '✗'}")
    print(f"  Blog:          {'✓' if enable_blog else '✗'}")
    print()
    print("  Next steps:")
    print(f"    cd {output_dir}")
    print("    docsforge serve")
    print()
    print("  Documentation: https://qqshi13.github.io/docsforge-docs/")
    print()
