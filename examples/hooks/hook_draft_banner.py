"""Single-file "hook" plugin — no packaging required.

DocsForge can load a plain Python file as a plugin via the `hooks:` config
key. The module itself acts as the plugin instance: define `on_*` functions
at module level and they're called for the corresponding events. This is the
fastest way to experiment with a plugin locally.

Usage in docsforge.yml:

    hooks:
      - docs/assets/draft_banner.py      # path relative to docs_dir

This example prepends a "DRAFT" admonition to every page whose source path
contains "draft".
"""
from __future__ import annotations


def on_page_markdown(markdown, *, page, config, files):
    src = getattr(page.file, "src_uri", "") or ""
    if "draft" in src.lower():
        return '!!! warning "DRAFT"\n    This page is not finalized.\n\n' + markdown
    return markdown
