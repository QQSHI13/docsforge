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


def _generate_config(
    site_name: str,
    site_url: str | None,
    theme_color: str,
    privacy: bool,
) -> str:
    """Generate docsforge.yml content with all core features enabled."""
    
    color = COLOR_MAP.get(theme_color, COLOR_MAP['teal'])
    
    lines = [
        f'site_name: {site_name}',
    ]
    
    if site_url:
        lines.append(f'site_url: {site_url}')
    
    lines.extend([
        '',
        'theme:',
        '  name: material',
        '  palette:',
        '    - media: "(prefers-color-scheme: light)"',
        '      scheme: default',
        f"      primary: {color['primary']}",
        f"      accent: {color['accent']}",
        '      toggle:',
        '        icon: material/brightness-7',
        '        name: Switch to dark mode',
        '    - media: "(prefers-color-scheme: dark)"',
        '      scheme: slate',
        f"      primary: {color['primary']}",
        f"      accent: {color['accent']}",
        '      toggle:',
        '        icon: material/brightness-4',
        '        name: Switch to light mode',
        '',
        '# Core features are always enabled:',
        '# search, tags, blog, info, meta, minify, social, optimize',
        '',
    ])
    
    if privacy:
        lines.extend([
            '# Privacy: external assets are fetched and inlined locally',
            '# This is the only optional core feature.',
            'privacy: true',
            '',
        ])
    
    lines.extend([
        'nav:',
        '  - Home: index.md',
        '  - Blog:',
        '    - blog/index.md',
        '',
    ])
    
    return '\n'.join(lines)


def _generate_index(site_name: str) -> str:
    """Generate index.md content."""
    return f"""# Welcome to {site_name}

This documentation is built with [DocsForge](https://qqshi13.github.io/docsforge-docs/).

## Getting Started

Edit this file at `docs/index.md` to add your content.

## Commands

- `docsforge serve` — Start live-reloading dev server
- `docsforge build` — Build for production
- `docsforge check` — Validate configuration

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


def init(
    project_directory: str,
    site_name: str,
    site_url: str | None,
    theme_color: str,
    privacy: bool,
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
        )
        config_path.write_text(config_content, encoding='utf-8')
    
    # Write index.md
    if index_path.exists():
        log.warning(f'{index_path} already exists. Skipping index creation.')
    else:
        log.info(f'Writing homepage: {index_path}')
        index_path.write_text(_generate_index(site_name), encoding='utf-8')
    
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
    print("  Next steps:")
    print(f"    cd {output_dir}")
    print("    docsforge serve")
    print()
    print("  Documentation: https://qqshi13.github.io/docsforge-docs/")
    print()
