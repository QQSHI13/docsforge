#!/usr/bin/env python3
"""Build DocsForge frontend from source.

Copies mkdocs-material-style source files and builds them into
docsforge/templates/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("build_frontend")

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "docsforge" / "templates"
NODE_MODULES = ROOT / "node_modules"


def _bin_path(pkg_dir: Path, name: str) -> Path | None:
    """Resolve the executable for a package's declared ``bin`` field.

    The bin path is not predictable (svgo 3 ships ``bin/svgo``, svgo 4 ships
    ``bin/svgo.js``), so read it from each candidate's package.json.
    """
    pkg_file = pkg_dir / "package.json"
    if not pkg_file.is_file():
        return None
    try:
        data = json.loads(pkg_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bin_field = data.get("bin")
    if isinstance(bin_field, str):
        path = pkg_dir / bin_field
    elif isinstance(bin_field, dict) and name in bin_field:
        path = pkg_dir / bin_field[name]
    else:
        return None
    return path if path.is_file() else None


def find_binary(name: str) -> Path:
    """Find a Node binary.

    Some pnpm .bin shims (e.g. esbuild) run `node` on a native executable,
    which fails. We prefer the actual binary in the pnpm virtual store.

    The virtual store can hold several versions of the same package (e.g.
    svgo 3 pulled in transitively by postcss-svgo alongside the svgo 4 direct
    dependency), so we resolve the version via the top-level `node_modules`
    symlink and pick the matching store entry — otherwise a transitive copy
    can shadow the tool the pipeline actually declared.
    """
    # Version of the direct dependency, resolved through pnpm's top-level
    # symlink (node_modules/<name> -> .pnpm/<name>@<version>/node_modules/<name>).
    want: str | None = None
    direct_pkg = NODE_MODULES / name / "package.json"
    if direct_pkg.is_file():
        try:
            want = json.loads(direct_pkg.read_text(encoding="utf-8")).get("version")
        except (OSError, ValueError):
            want = None

    candidates: list[tuple[str, Path]] = []
    for pkg_dir in sorted(NODE_MODULES.glob(f".pnpm/{name}@*/node_modules/{name}")):
        version = None
        for part in pkg_dir.parts:
            if part.startswith(f"{name}@"):
                # Store dirs are <name>@<version> or <name>@<version>_<peer>...
                version = part[len(name) + 1:].split("_", 1)[0]
        if version is None:
            continue
        path = _bin_path(pkg_dir, name)
        if path is not None:
            candidates.append((version, path))

    if want:
        for version, path in candidates:
            if version == want:
                return path

    for _, path in candidates:
        return path

    # Fallback to the .bin wrapper.
    shim = NODE_MODULES / ".bin" / name
    if shim.exists():
        return shim

    raise FileNotFoundError(f"Could not find Node binary: {name}")


def run(cmd: list[str], **kwargs) -> None:
    log.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT, **kwargs)


def clean_output() -> None:
    """Remove generated files while preserving DocsForge-specific files."""
    preserved = {
        OUT / "assets" / "javascripts" / "sw.js",
        OUT / "assets" / "javascripts" / "lunr",
        OUT / "assets" / "katex",
    }
    for sub in [OUT / "assets" / "javascripts" / "bundle.min.js",
                OUT / "assets" / "javascripts" / "workers" / "search.min.js",
                OUT / "assets" / "stylesheets" / "main.min.css",
                OUT / "assets" / "stylesheets" / "palette.min.css"]:
        if sub.exists():
            sub.unlink()


def build_typescript() -> None:
    """Bundle TypeScript source into minified JS outputs."""
    entries = [
        ("src/assets/javascripts/bundle.ts", "assets/javascripts/bundle.min.js"),
        ("src/assets/javascripts/workers/search.ts", "assets/javascripts/workers/search.min.js"),
    ]
    for src_file, out_file in entries:
        out_path = OUT / out_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run([
            str(find_binary("esbuild")),
            src_file,
            "--bundle",
            "--minify",
            "--target=es2020",
            f"--outfile={out_path}",
            "--format=iife",
            "--platform=browser",
            "--jsx-factory=h",
            "--jsx-fragment=Fragment",
            # material imports mermaid's index.css as a string (themeCSS option);
            # without the text loader it gets extracted to a stray bundle.min.css
            # and mermaid theming breaks.
            "--loader:.css=text",
        ])


def build_styles() -> None:
    """Compile SCSS to minified CSS."""
    entries = [
        ("src/assets/stylesheets/main.scss", "assets/stylesheets/main.min.css"),
        ("src/assets/stylesheets/palette.scss", "assets/stylesheets/palette.min.css"),
    ]
    for src_file, out_file in entries:
        out_path = OUT / out_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_css = ROOT / ".tmp" / out_file.replace("/", "_")
        tmp_css.parent.mkdir(parents=True, exist_ok=True)
        run([
            str(find_binary("sass")),
            src_file,
            str(tmp_css),
            "--style=expanded",
            "--load-path=node_modules",
            "--load-path=node_modules/material-design-color",
            "--load-path=node_modules/material-shadows",
            "--load-path=src/assets/stylesheets",
            # The SCSS is vendored from mkdocs-material and still uses the
            # classic @import/global-builtin style. Dart Sass deprecates these
            # (removal in 3.0); silencing keeps output byte-identical and lets
            # the upstream migration land when we upgrade material.
            "--silence-deprecation=import,global-builtin",
        ])
        # Apply autoprefixer + inline svg-load() icons (postcss.config.js).
        prefixed = tmp_css.with_suffix(".prefixed.css")
        run([
            str(find_binary("postcss")),
            str(tmp_css),
            "--no-map",
            "--output", str(prefixed),
        ])
        # Minify with esbuild (cssnano OOMs on this CSS with current versions).
        run([
            str(find_binary("esbuild")),
            str(prefixed),
            "--minify",
            f"--outfile={out_path}",
        ])


def minify_html_file(src: Path, dst: Path) -> None:
    """Minify a single HTML template."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    banner = "{#-\n  This file was automatically generated - do not edit\n-#}\n"
    content = src.read_text(encoding="utf-8")
    # Add banner if not present
    if not content.strip().startswith("{#-"):
        content = banner + content
    tmp = ROOT / ".tmp" / "html" / dst.relative_to(OUT)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(content, encoding="utf-8")
    run([
        str(find_binary("html-minifier-terser")),
        "--case-sensitive",
        "--collapse-boolean-attributes",
        "--no-include-auto-generated-tags",
        "--minify-css",
        "--minify-js",
        "--remove-comments",
        "--remove-script-type-attributes",
        "--remove-style-link-type-attributes",
        "--collapse-whitespace",
        "--conservative-collapse",
        "--preserve-line-breaks",
        "--output", str(dst),
        str(tmp),
    ])


def copy_templates() -> None:
    """Copy and minify HTML templates; copy non-HTML static templates verbatim.

    Non-HTML static templates (docsforge_theme.yml, sitemap.xml, ...) are part
    of the installed theme and must ship alongside the HTML templates.
    """
    template_src = SRC / "templates"
    if not template_src.exists():
        log.warning("Template source does not exist: %s", template_src)
        return
    for src in template_src.rglob("*.html"):
        rel = src.relative_to(template_src)
        dst = OUT / rel
        minify_html_file(src, dst)
    for src in template_src.rglob("*"):
        if not src.is_file() or src.suffix.lower() == ".html":
            continue
        rel = src.relative_to(template_src)
        # .icons/ is a 14k-file set synced separately by copy_icons_to_out();
        # copying it here doubles the work and duplicates the output.
        if rel.parts[0] == ".icons":
            continue
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def copy_icons() -> None:
    """Copy optimized icons from node_modules into source tree."""
    icon_sets = [
        ("node_modules/@mdi/svg/svg", "src/templates/.icons/material"),
        ("node_modules/@primer/octicons/build/svg", "src/templates/.icons/octicons"),
        ("node_modules/@fortawesome/fontawesome-free/svgs", "src/templates/.icons/fontawesome"),
        ("node_modules/simple-icons/icons", "src/templates/.icons/simple"),
    ]
    for src_dir, dst_dir in icon_sets:
        src = ROOT / src_dir
        dst = ROOT / dst_dir
        if not src.exists():
            log.warning("Icon source missing: %s", src)
            continue
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)
        # Use svgo directory mode to optimize all icons in one invocation.
        run([
            str(find_binary("svgo")),
            "--folder", str(src),
            "--output", str(dst),
            "--recursive",
            "--quiet",
            "--config", str(ROOT / "svgo.config.js"),
        ])
    # Copy the upstream license files alongside each optimized icon set so the
    # vendored attribution ships with the build (svgo only emits .svg files).
    extra_licenses = [
        ("node_modules/@fortawesome/fontawesome-free/LICENSE.txt",
         "src/templates/.icons/fontawesome/LICENSE.txt"),
        ("node_modules/@primer/octicons/LICENSE",
         "src/templates/.icons/octicons/LICENSE"),
    ]
    for src_file, dst_file in extra_licenses:
        src_lic = ROOT / src_file
        dst_lic = ROOT / dst_file
        if src_lic.exists():
            dst_lic.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_lic, dst_lic)
    # Preserve DocsForge-specific badges already in src/templates/.icons


def copy_icons_to_out() -> None:
    """Sync optimized icons from the source tree to the installed templates."""
    src = ROOT / "src" / "templates" / ".icons"
    dst = OUT / ".icons"
    if not src.exists():
        log.warning("Icon source does not exist: %s", src)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_lunr() -> None:
    """Copy Lunr language stemmers from node_modules."""
    src = NODE_MODULES / "lunr-languages"
    dst = OUT / "assets" / "javascripts" / "lunr"
    if not src.exists():
        log.warning("lunr-languages missing")
        return
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for pattern in ["min/*.js", "tinyseg.js", "wordcut.js"]:
        for f in src.glob(pattern):
            rel = f.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)


def copy_sw() -> None:
    """Minify and copy the service worker, keeping the build placeholders.

    The __DOCSFORGE_BASE_URL__ and __DOCSFORGE_BUILD_HASH__ placeholders are
    deliberately left in place: docsforge/build.py replaces them at site-build
    time with the real base path and a deterministic hash (see build.py's SW
    injection). Replacing them here (e.g. with 'dev'/'') would make the SW
    bytes identical across builds, defeat the browser's SW-update check, and
    leave build.py's injection dead. The new SW no longer uses
    __PRE_CACHE_PAGES__ (manifest-driven sync replaces the baked precache
    list), so build.py's precache substitution is a no-op.
    """
    src = SRC / "assets" / "javascripts" / "sw.js"
    if not src.exists():
        log.warning("Service worker source missing")
        return
    dst = OUT / "assets" / "javascripts" / "sw.js"
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Minify with esbuild so the shipped worker has no comments/whitespace, like
    # every other JS asset. The __DOCSFORGE_*__ placeholders are string literals
    # and survive minification for build.py to substitute.
    tmp = ROOT / ".tmp" / "sw.min.js"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(find_binary("esbuild")),
        str(src),
        "--minify",
        "--target=es2020",
        f"--outfile={tmp}",
    ])
    shutil.copy2(tmp, dst)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build DocsForge frontend")
    parser.add_argument("--watch", action="store_true", help="Watch for changes")
    parser.add_argument("--clean", action="store_true", help="Clean output first")
    parser.add_argument("--skip-templates", action="store_true", help="Skip template copy/minify")
    parser.add_argument("--skip-icons", action="store_true", help="Skip icon copy/optimize")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s - %(message)s",
    )

    if args.clean:
        clean_output()

    # Ensure source tree exists
    if not SRC.exists():
        log.error("Source tree missing: %s", SRC)
        return 1

    # Build steps
    if not args.skip_icons:
        copy_icons()
        copy_icons_to_out()
    if not args.skip_templates:
        copy_templates()
    build_typescript()
    build_styles()
    copy_lunr()
    copy_sw()

    if args.watch:
        log.info("Watch mode not yet implemented")

    return 0


if __name__ == "__main__":
    sys.exit(main())
