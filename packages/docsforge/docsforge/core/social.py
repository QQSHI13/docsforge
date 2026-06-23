"""Social plugin - generates OpenGraph preview images for each page.

Requires: pip install docsforge[imaging]
Adapted from Material for MkDocs social plugin.
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from fnmatch import fnmatch
from hashlib import sha1
from pathlib import Path

from docsforge.core.plugin_base import BasePlugin, event_priority
from docsforge.config_base import Config
from docsforge.config_options import (
    Choice, Deprecated, DictOfItems, ListOfItems, Optional, SubConfig, Type
)

try:
    from PIL import Image as _Image
    HAS_IMAGE = True
except ImportError:
    HAS_IMAGE = False

log = logging.getLogger(__name__)

# ── Config ──

class SocialConfig(Config):
    enabled = Type(bool, default=True)
    concurrency = Type(int, default=max(1, os.cpu_count() - 1))
    cache = Type(bool, default=True)
    cache_dir = Type(str, default=".cache/plugin/social")
    cards = Type(bool, default=True)
    cards_dir = Type(str, default="assets/images/social")
    cards_layout = Type(str, default="default")
    cards_layout_options = Type(dict, default={})
    cards_include = ListOfItems(Type(str), default=[])
    cards_exclude = ListOfItems(Type(str), default=[])
    debug = Type(bool, default=False)
    log = Type(bool, default=True)

# ── Plugin ──

class SocialPlugin(BasePlugin[SocialConfig]):
    supports_multiple_instances = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []
        self._executor = None

    def on_config(self, config):
        if not HAS_IMAGE:
            log.warning("pillow not installed. Install: pip install docsforge[imaging]")
            return
        self._executor = ThreadPoolExecutor(max_workers=self.config.concurrency)

    def on_page_content(self, html, *, page, config, files):
        if not HAS_IMAGE:
            return html
        if not _is_included(page, self.config):
            return html

        self._pages.append(page)
        image_path = _image_path(page, self.config)

        meta = (
            f'<meta property="og:image" content="{image_path}" />\n'
            f'<meta name="twitter:image" content="{image_path}" />\n'
            f'<meta name="twitter:card" content="summary_large_image" />\n'
            f'<meta property="og:image:width" content="1200" />\n'
            f'<meta property="og:image:height" content="630" />'
        )
        return html.replace("</head>", f"{meta}\n</head>")

    def on_post_build(self, config):
        if not HAS_IMAGE or not self._pages:
            return

        site_dir = Path(config.site_dir)
        images_dir = site_dir / self.config.cards_dir
        images_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for page in self._pages:
            image_path = images_dir / (
                Path(page.file.src_uri).with_suffix(".png")
            )
            image_path.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(
                self._executor.submit(_render_card, page, image_path, config)
            )

        for task in tasks:
            task.result()

        log.info(f"Generated {len(tasks)} social cards")


def _is_included(page, config):
    if not config.cards:
        return False
    src = page.file.src_uri if page.file else ""
    if src == "404.html":
        return False
    for pattern in config.cards_include:
        if not fnmatch(src, pattern):
            return False
    for pattern in config.cards_exclude:
        if fnmatch(src, pattern):
            return False
    return True


def _image_path(page, config):
    src = Path(page.file.src_uri if page.file else "index.md")
    return str(Path(config.cards_dir) / src.with_suffix(".png"))


def _render_card(page, image_path, config):
    """Render a social card image for a page."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font_bold = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
        )
        font_reg = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
        )
    except (IOError, OSError):
        font_bold = ImageFont.load_default()
        font_reg = ImageFont.load_default()

    title = page.title or config.site_name or "DocsForge"
    desc = page.meta.get("description", "") if page.meta else ""
    site = config.site_name or "DocsForge"
    bg = "#009688"

    img = Image.new("RGB", (1200, 630), bg)
    draw = ImageDraw.Draw(img)

    # Bottom strip
    draw.rectangle([0, 530, 1200, 630], fill="#00796B")
    draw.text((60, 555), site, fill="white", font=font_reg)

    # Title
    import textwrap
    draw.text((60, 60), textwrap.fill(title, width=25), fill="white", font=font_bold)

    # Description
    if desc:
        draw.text(
            (60, 240), textwrap.fill(desc, width=40),
            fill="white", font=font_reg
        )

    img.save(image_path, "PNG")
