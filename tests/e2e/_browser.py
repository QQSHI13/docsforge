"""Browser selection for e2e tests.

Honors the ``PLAYWRIGHT_CHROMIUM_EXECUTABLE`` environment variable (same
convention as ``docsforge.pdf``) so a system browser can be used instead of
Playwright's bundled Chromium. With no env var set, Playwright's default
browser is used (the CI e2e job installs it with ``playwright install
chromium``).
"""
from __future__ import annotations

import os


def launch_opts() -> dict:
    """Keyword arguments for ``p.chromium.launch(**launch_opts())``."""
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    return {"executable_path": exe} if exe else {}
