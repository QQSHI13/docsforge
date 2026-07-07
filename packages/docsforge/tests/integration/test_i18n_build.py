"""Integration tests for the i18n plugin end-to-end build."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from docsforge.config_base import load_config
from docsforge.build import build

pytestmark = pytest.mark.slow


def _build_i18n_site(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    assets = docs / "assets"
    assets.mkdir()
    (docs / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n\n[Second](second.md)\n\n"
        "![Diagram](assets/diagram.png)\n\n![Other](assets/other.png)\n"
    )
    (docs / "index.zh.md").write_text(
        "---\ntitle: 首页\n---\n# 首页\n\n[第二页](second.md)\n\n"
        "![Diagram](assets/diagram.png)\n\n![Other](assets/other.png)\n"
    )
    (docs / "second.md").write_text("---\ntitle: Second\n---\n# Second\n")
    (docs / "second.zh.md").write_text("---\ntitle: 第二页\n---\n# 第二页\n")
    (assets / "diagram.png").write_text("default-diagram")
    (assets / "diagram.zh.png").write_text("zh-diagram")
    (assets / "other.png").write_text("default-other")

    config = {
        "site_name": "I18n Test",
        "docs_dir": "docs",
        "site_url": "https://example.com/",
        "theme": {"name": "material"},
        "nav": ["index.md", {"Second": "second.md"}],
        "plugins": [
            {
                "material/i18n": {
                    "languages": [
                        {"locale": "en", "name": "English", "default": True},
                        {"locale": "zh", "name": "中文"},
                    ]
                }
            }
        ],
    }
    import yaml

    (tmp_path / "docsforge.yml").write_text(yaml.safe_dump(config))

    cfg = load_config(config_file=str(tmp_path / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()
    return tmp_path / "site"


class TestI18nBuild:
    def test_creates_default_and_locale_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "index.html").is_file()
        assert (site / "second" / "index.html").is_file()
        assert (site / "zh" / "index.html").is_file()
        assert (site / "zh" / "second" / "index.html").is_file()

    def test_creates_locale_search_index_and_sitemap(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "search" / "search_index.json").is_file()
        assert (site / "zh" / "search" / "search_index.json").is_file()
        assert (site / "zh" / "sitemap.xml").is_file()
        assert (site / "zh" / "sitemap.xml.gz").is_file()

    def test_content_links_point_to_locale_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        # The link should stay inside the zh subtree, not climb out to /second/.
        assert re.search(r'<a[^>]+href="second/"[^>]*>第二页</a>', html) or \
               re.search(r'<a[^>]+href=second/[^>]*>第二页</a>', html)

    def test_emits_alternate_head_links(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        assert 'hreflang=en' in html
        assert 'hreflang=zh' in html

    def test_emits_language_switcher(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        assert "English" in html
        assert "中文" in html

    def test_translated_asset_copied_to_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "assets" / "diagram.png").read_text() == "default-diagram"
        assert (site / "zh" / "assets" / "diagram.png").read_text() == "zh-diagram"
        # The suffixed source file should not be emitted at the site root.
        assert not (site / "assets" / "diagram.zh.png").exists()

    def test_fallback_asset_copied_to_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "assets" / "other.png").read_text() == "default-other"
        assert (site / "zh" / "assets" / "other.png").read_text() == "default-other"

    def test_locale_asset_links_rewritten(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        # Both images should reference the locale copy, not climb out to the root.
        assert re.search(r'<img[^>]+src=["\']?assets/diagram\.png["\'\s>]', html)
        assert re.search(r'<img[^>]+src=["\']?assets/other\.png["\'\s>]', html)

    def test_translated_pages_not_emitted_at_root(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        # Translated source files must not produce root-level pages or assets.
        assert not (site / "index.zh.html").exists()
        assert not (site / "second.zh.html").exists()
        assert not (site / "assets" / "diagram.zh.png").exists()
