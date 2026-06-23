"""Social cards plugin — generates OpenGraph preview images for each page.

Requires: pip install docsforge[imaging]

Hooks into on_post_build to render social preview images using Pillow.
Adapted from Material for MkDocs social plugin.
"""

from __future__ import annotations

import logging
import os
import textwrap
from pathlib import Path

from docsforge.core.plugin_base import BasePlugin
from docsforge.config_base import Config
from docsforge.config_options import Type, Optional

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Card dimensions (standard OpenGraph: 1200x630)
CARD_W = 1200
CARD_H = 630
MARGIN = 60
TITLE_MAX_W = CARD_W - MARGIN * 2 - 200  # Leave space for logo


class SocialConfig(Config):
    enabled = Type(bool, default=True)
    cache_dir = Type(str, default="assets/images/social")
    background_color = Type(str, default="#009688")  # Teal
    font_color = Type(str, default="#ffffff")
    cards_color = Type(str, default="#00796B")


class SocialPlugin(BasePlugin[SocialConfig]):
    def on_post_build(self, config):
        if not HAS_PIL:
            log.warning("Pillow not installed. Install: pip install docsforge[imaging]")
            return

        site_dir = Path(config.site_dir)
        images_dir = site_dir / self.config.cache_dir
        images_dir.mkdir(parents=True, exist_ok=True)

        # Collect all HTML pages
        html_files = sorted(site_dir.rglob("*.html"))
        if not html_files:
            return

        # Try to load fonts
        try:
            font_bold = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
            )
            font_regular = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
            )
        except (IOError, OSError):
            font_bold = ImageFont.load_default()
            font_regular = ImageFont.load_default()

        site_name = config.site_name or "DocsForge"

        for html_file in html_files:
            rel = html_file.relative_to(site_dir)
            # Skip 404.html and non-page HTML files
            if html_file.name == "404.html":
                continue

            # Extract title and description from HTML
            title, description = self._extract_meta(html_file, site_name)

            # Generate social card image
            img = self._render_card(title, description, site_name, font_bold, font_regular)

            # Save as PNG next to the HTML file (for OpenGraph)
            social_path = images_dir / rel.with_suffix(".png")
            social_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(social_path, "PNG")

            # Inject og:image meta tag into the HTML
            self._inject_meta(html_file, rel.with_suffix(".png"))

        log.info(f"Social cards generated: {len(html_files)} pages")

    def _extract_meta(self, html_file: Path, site_name: str) -> tuple[str, str]:
        """Extract title and description from HTML."""
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return site_name, ""

        title = site_name
        desc = ""

        # Extract <title>
        import re
        m = re.search(r"<title[^>]*>([^<]+)</title>", content)
        if m:
            title = m.group(1).strip()

        # Extract meta description
        m = re.search(
            r'<meta\s+name="description"\s+content="([^"]+)"',
            content, re.IGNORECASE
        )
        if m:
            desc = m.group(1).strip()

        return title, desc

    def _render_card(
        self, title: str, description: str, site_name: str,
        font_bold, font_regular
    ) -> Image.Image:
        """Render a social card image."""
        img = Image.new("RGB", (CARD_W, CARD_H), self.config.background_color)
        draw = ImageDraw.Draw(img)

        # Draw a darker bottom strip
        draw.rectangle([0, CARD_H - 100, CARD_W, CARD_H], fill=self.config.cards_color)

        # Site name at bottom
        draw.text((MARGIN, CARD_H - 75), site_name, fill=self.config.font_color, font=font_regular)

        # Title — wrap if too long
        wrapped = textwrap.fill(title, width=25)
        draw.text((MARGIN, MARGIN), wrapped, fill=self.config.font_color, font=font_bold)

        # Description
        if description:
            desc_wrapped = textwrap.fill(description, width=40)
            draw.text((MARGIN, MARGIN + 180), desc_wrapped, fill=self.config.font_color, font=font_regular)

        return img

    def _inject_meta(self, html_file: Path, image_rel: Path):
        """Inject og:image and twitter:image meta tags into HTML."""
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Only inject if not already present
        if 'property="og:image"' in content:
            return

        # Use relative path for the image
        image_url = str(image_rel).replace("\\", "/")

        meta_tags = (
            f'<meta property="og:image" content="{image_url}" />\n'
            f'<meta name="twitter:image" content="{image_url}" />\n'
            f'<meta name="twitter:card" content="summary_large_image" />'
        )

        # Inject before </head>
        content = content.replace("</head>", f"{meta_tags}\n</head>")

        html_file.write_text(content, encoding="utf-8")
