"""Shared fixtures for the DocsForge test suite.

Tests never touch the real repo on disk — every fixture builds a throwaway
project in a tmp_path so builds are hermetic and parallel-safe.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal docsforge project root with a config and one page.

    Chdirs into the project so relative paths (docs/, docsforge.yml) resolve
    exactly as they would for a real `docsforge build` invocation.
    """
    root = tmp_path / "site"
    docs = root / "docs"
    docs.mkdir(parents=True)

    (docs / "index.md").write_text("# Home\n\nWelcome to the test site.\n")

    (root / "docsforge.yml").write_text(
        textwrap.dedent(
            """
            site_name: Test Site
            docs_dir: docs
            site_dir: site
            privacy: false   # hermetic: no network downloads in tests
            theme:
              name: material
              palette:
                - scheme: default
                  primary: teal
                  accent: teal
            """
        ).strip()
        + "\n"
    )

    monkeypatch.chdir(root)
    # The cache lives under .docsforge/ in cwd; make sure tests start clean.
    return root


@pytest.fixture()
def tmp_project_with_include(tmp_project: Path) -> tuple[Path, Path, Path]:
    """A project where one page includes a snippet via pymdownx.snippets.

    Returns (root, page_path, include_path).
    """
    docs = tmp_project / "docs"
    inc = docs / "header.md"
    inc.write_text("# Included Header\n")
    page = docs / "page.md"
    page.write_text('# Page\n\n--8<-- "header.md"\n')
    return tmp_project, page, inc
