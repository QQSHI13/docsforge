#!/usr/bin/env python3
"""Download Material Icons from Material for MkDocs during package build.

Material for MkDocs curates Google's Material Icons with naming that matches
the theme templates. We fetch the latest matching version during build.
"""

import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def download_file(url: str, dest: Path) -> None:
    """Download a file from URL to destination."""
    print(f"Downloading {url}...")
    urllib.request.urlretrieve(url, dest)
    print(f"  -> {dest} ({dest.stat().st_size / 1024 / 1024:.1f}MB)")


def download_material_icons() -> None:
    """Download Material Icons from Material for MkDocs release."""
    output_dir = Path("docsforge/themes/material/templates/.icons")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing icons
    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tar_path = tmpdir / "material.tar.gz"

        # Download Material for MkDocs source (matches our vendored version)
        url = "https://github.com/squidfunk/mkdocs-material/archive/refs/tags/9.7.6.tar.gz"
        download_file(url, tar_path)

        with tarfile.open(tar_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("mkdocs-material-9.7.6/material/templates/.icons/"):
                    tar.extract(member, tmpdir)

            src = tmpdir / "mkdocs-material-9.7.6/material/templates/.icons"
            if src.exists():
                for item in src.iterdir():
                    dest = output_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

                count = sum(1 for _ in output_dir.rglob("*.svg"))
                print(f"Extracted {count} icons")
            else:
                print("ERROR: Could not find icons in downloaded archive")
                raise RuntimeError("Icon extraction failed")


if __name__ == "__main__":
    download_material_icons()
