#!/usr/bin/env python3
"""Fetch the twemoji SVG asset set into the vendored templates directory.

The twemoji npm package no longer ships the SVG assets, so we pull the
pinned tag from the maintained jdecked/twemoji fork (the upstream
twitter/twemoji repository is archived). Run this after bumping
TWEMOJI_TAG below; commit the result (src/templates/assets/emoji/twemoji/)
as part of the change, then rebuild the frontend so copy_twemoji syncs it
into docsforge/templates/.

Usage: python scripts/fetch_twemoji.py
"""

from __future__ import annotations

import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

TWEMOJI_TAG = "v17.0.3"
TARBALL_URL = (
    f"https://codeload.github.com/jdecked/twemoji/tar.gz/refs/tags/{TWEMOJI_TAG}"
)
DEST = (
    Path(__file__).resolve().parent.parent
    / "src" / "templates" / "assets" / "emoji" / "twemoji"
)
LICENSES = ["LICENSE", "LICENSE-GRAPHICS"]


def main() -> int:
    print(f"Fetching twemoji {TWEMOJI_TAG} ...")
    with urllib.request.urlopen(TARBALL_URL) as resp:
        data = resp.read()

    prefix = f"twemoji-{TWEMOJI_TAG.removeprefix('v')}"
    svg_dir = f"{prefix}/assets/svg/"
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if name.startswith(svg_dir) and name.endswith(".svg"):
                out = DEST / Path(name).name
                f = tar.extractfile(member)
                if f is not None:
                    out.write_bytes(f.read())
                    count += 1
            elif name in {f"{prefix}/{lic}" for lic in LICENSES}:
                f = tar.extractfile(member)
                if f is not None:
                    (DEST / Path(name).name).write_bytes(f.read())

    print(f"Wrote {count} SVGs + licenses to {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())