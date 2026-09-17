#!/usr/bin/env python3
"""Build DocsForge frontend from source.

Copies mkdocs-material-style source files and builds them into
docsforge/templates/.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

log = logging.getLogger("build_frontend")

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "docsforge" / "templates"
NODE_MODULES = ROOT / "node_modules"

# Pinned twemoji tag (maintained fork of the archived twitter/twemoji).
TWEMOJI_TAG = "v17.0.3"
TWEMOJI_TARBALL_URL = (
    f"https://codeload.github.com/jdecked/twemoji/tar.gz/refs/tags/{TWEMOJI_TAG}"
)
TWEMOJI_SRC = SRC / "templates" / "assets" / "emoji" / "twemoji"
TWEMOJI_LICENSES = ["LICENSE", "LICENSE-GRAPHICS"]

# Frontend dependencies whose installed versions must satisfy package.json.
# Checked by check_dependencies() before anything is built: building with
# drifted node_modules silently produces wrong output (older icon artwork,
# older mermaid/wasm bundles) and can even destroy newer vendored sources
# during --refresh-icons.


def _parse_version(text: str) -> tuple[int, ...]:
    """Parse `1.44.0` (or `1.44.0-beta.1`, `1.44`) into an int tuple."""
    core = text.strip().lstrip("v").split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError as e:
        raise ValueError(f"unparseable version: {text!r}") from e


def _pad(version: tuple[int, ...], length: int = 3) -> tuple[int, ...]:
    return version + (0,) * max(0, length - len(version))


def satisfies_range(installed: str, spec: str) -> bool:
    """Check an installed version against an npm range (`^`, `~`, `>=`, exact).

    Unknown operators return False so the caller reports them instead of
    silently trusting an unchecked dependency.
    """
    spec = spec.strip()
    inst = _pad(_parse_version(installed))
    if spec.startswith("^"):
        base = _pad(_parse_version(spec[1:]))
        if inst < base:
            return False
        if base[0] != 0:
            return inst[0] == base[0]
        if base[1] != 0:
            return inst[:2] == base[:2]
        return inst == base
    if spec.startswith("~"):
        base = _pad(_parse_version(spec[1:]))
        return inst >= base and inst[:2] == base[:2]
    if spec.startswith(">="):
        return inst >= _pad(_parse_version(spec[2:]))
    if spec.startswith("="):
        return inst == _pad(_parse_version(spec[1:]))
    if spec[0].isdigit():
        return inst == _pad(_parse_version(spec))
    return False


def check_dependencies() -> None:
    """Fail fast when node_modules does not satisfy package.json.

    Every dependency (including icon sets and vendored bundles) feeds
    byte-identical build output, so drift must be a loud error telling the
    user to run `pnpm install` — never a silent downgrade of the output.
    """
    try:
        wanted = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    except OSError as e:
        raise SystemExit(f"build_frontend: cannot read package.json: {e}") from e
    specs = {**wanted.get("dependencies", {}), **wanted.get("devDependencies", {})}
    problems: list[str] = []
    for name in sorted(specs):
        installed_pkg = NODE_MODULES / name / "package.json"
        try:
            installed = json.loads(installed_pkg.read_text(encoding="utf-8")).get("version", "")
        except OSError:
            problems.append(f"{name}: not installed (wanted {specs[name]})")
            continue
        except ValueError:
            problems.append(f"{name}: installed package.json is unreadable")
            continue
        try:
            ok = satisfies_range(installed, specs[name])
        except ValueError:
            problems.append(f"{name}: cannot parse version {installed!r} or range {specs[name]!r}")
            continue
        if not ok:
            problems.append(f"{name}: installed {installed}, wanted {specs[name]}")
    if problems:
        detail = "\n  ".join(problems)
        raise SystemExit(
            "build_frontend: node_modules does not satisfy package.json:\n"
            f"  {detail}\n"
            "Run `pnpm install` (frozen lockfile, committed) and retry. "
            "Building with drifted dependencies produces wrong output."
        )
    log.info("Dependencies satisfy package.json (%d packages)", len(specs))


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
    """Remove generated files while preserving DocsForge-specific files.

    Only the four files this script regenerates are unlinked. Everything else
    under OUT/assets is left alone — notably sw.js, javascripts/marz/ and
    katex/, which are DocsForge-specific additions that would not be rebuilt
    if deleted.
    """
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
    try:
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
    except subprocess.CalledProcessError as e:
        log.error("HTML minification failed for %s (exit %s)", src, e.returncode)
        raise


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
        # assets/emoji/ (twemoji, ~4k files) is synced by copy_twemoji().
        if rel.parts[0] == ".icons" or rel.parts[:2] == ("assets", "emoji"):
            continue
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _sync_tree(src: Path, dst: Path, label: str) -> None:
    """Mirror `src` into `dst`: copy new/changed files, prune deleted ones.

    Change detection is size + mtime-ns (the same cheap rule the engine's
    incremental builds use). Unlike a blind copytree, deletions propagate,
    so renamed upstream icons or removed twemoji files cannot linger in the
    output forever.
    """
    copied = pruned = skipped = 0
    dst.mkdir(parents=True, exist_ok=True)
    want: set[Path] = set()
    for s in src.rglob("*"):
        if not s.is_file():
            continue
        rel = s.relative_to(src)
        want.add(rel)
        d = dst / rel
        if d.is_file():
            s_stat, d_stat = s.stat(), d.stat()
            if (
                s_stat.st_size == d_stat.st_size
                and s_stat.st_mtime_ns == d_stat.st_mtime_ns
            ):
                skipped += 1
                continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        copied += 1
    for d in dst.rglob("*"):
        if d.is_file() and d.relative_to(dst) not in want:
            d.unlink()
            pruned += 1
    # Drop directories left empty by pruning (deepest first).
    for d in sorted((p for p in dst.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        with contextlib.suppress(OSError):
            d.rmdir()
    log.info("%s: %d copied, %d pruned, %d unchanged", label, copied, pruned, skipped)


def copy_icons() -> None:
    """Refresh vendored icon sources from node_modules (DESTRUCTIVE).

    Overwrites `src/templates/.icons/*` with the installed packages'
    artwork. Only run via `--refresh-icons` after `pnpm install`/`pnpm
    update` (check_dependencies() guarantees the versions first); the
    normal build never calls this and treats `src/` as canonical. Review
    the resulting `git status` before committing: upstream renames show up
    as delete+add pairs.
    """
    icon_sets = [
        ("node_modules/@mdi/svg/svg", "src/templates/.icons/material"),
        ("node_modules/@primer/octicons/build/svg", "src/templates/.icons/octicons"),
        ("node_modules/@fortawesome/fontawesome-free/svgs", "src/templates/.icons/fontawesome"),
        ("node_modules/simple-icons/icons", "src/templates/.icons/simple"),
        ("node_modules/lucide-static/icons", "src/templates/.icons/lucide"),
    ]
    for src_dir, dst_dir in icon_sets:
        src = ROOT / src_dir
        dst = ROOT / dst_dir
        if not src.exists():
            log.warning("Icon source missing: %s", src)
            continue
        before = {p.relative_to(dst) for p in dst.rglob("*.svg")} if dst.exists() else set()
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
        after = {p.relative_to(dst) for p in dst.rglob("*.svg")}
        log.info(
            "Icons %s: +%d ~%d -%d",
            dst.name, len(after - before), len(after & before), len(before - after),
        )
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
    _sync_tree(src, dst, "Icons")


def fetch_twemoji() -> None:
    """Download the pinned twemoji SVG set into the source tree.

    The twemoji npm package no longer ships the SVG assets, so the set is
    pulled from the pinned tag of the maintained jdecked/twemoji fork (the
    upstream twitter/twemoji repository is archived). Run this when bumping
    TWEMOJI_TAG, commit the result, then a normal build syncs it into
    docsforge/templates/ via copy_twemoji().
    """
    log.info("Fetching twemoji %s ...", TWEMOJI_TAG)
    with urllib.request.urlopen(TWEMOJI_TARBALL_URL) as resp:
        data = resp.read()

    prefix = f"twemoji-{TWEMOJI_TAG.removeprefix('v')}"
    svg_dir = f"{prefix}/assets/svg/"
    if TWEMOJI_SRC.exists():
        shutil.rmtree(TWEMOJI_SRC)
    TWEMOJI_SRC.mkdir(parents=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if name.startswith(svg_dir) and name.endswith(".svg"):
                out = TWEMOJI_SRC / Path(name).name
                f = tar.extractfile(member)
                if f is not None:
                    out.write_bytes(f.read())
                    count += 1
            elif name in {f"{prefix}/{lic}" for lic in TWEMOJI_LICENSES}:
                f = tar.extractfile(member)
                if f is not None:
                    (TWEMOJI_SRC / Path(name).name).write_bytes(f.read())

    log.info("Wrote %d SVGs + licenses to %s", count, TWEMOJI_SRC)
    if count == 0:
        raise SystemExit(
            f"build_frontend: twemoji fetch yielded 0 SVGs from {TWEMOJI_TAG} "
            "(tarball layout may have changed) — source tree left with an "
            "empty set, aborting before anything consumes it."
        )


def copy_twemoji() -> None:
    """Sync the vendored twemoji SVG set from the source tree to templates.

    The twemoji npm package no longer ships the SVG assets, so the set is
    vendored under src/templates/assets/emoji/twemoji/ and refreshed with
    `python build_frontend.py --fetch-twemoji` (pinned upstream tag).
    """
    src = TWEMOJI_SRC
    dst = OUT / "assets" / "emoji" / "twemoji"
    if not src.exists():
        log.warning("Twemoji source does not exist: %s", src)
        return
    _sync_tree(src, dst, "Twemoji")


def copy_marz_wasm() -> None:
    """Copy the Marz WebAssembly runtime from node_modules."""
    src = NODE_MODULES / "marz-search" / "pkg" / "marz_wasm_bg.wasm"
    dst = OUT / "assets" / "javascripts" / "marz" / "marz_wasm_bg.wasm"
    if not src.exists():
        log.warning("marz-search WASM runtime missing")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    # License must travel with the runtime (check package for its name)
    for name in ["LICENSE", "LICENSE.md"]:
        lic = NODE_MODULES / "marz-search" / name
        if lic.exists():
            shutil.copy2(lic, dst.parent / name)
            break


def copy_katex() -> None:
    """Copy KaTeX (min.js, min.css, fonts) from node_modules.

    KaTeX is vendored so math renders offline and no CDN is referenced. It is
    a manifest-tracked devDependency (package.json), so dependabot can bump it.
    """
    src = NODE_MODULES / "katex" / "dist"
    dst = OUT / "assets" / "katex"
    if not src.exists():
        log.warning("katex missing from node_modules")
        return
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in ["katex.min.js", "katex.min.css", "contrib"]:
        s = src / name
        if s.exists():
            shutil.copytree(s, dst / name) if s.is_dir() else shutil.copy2(s, dst / name)
    # Fonts referenced by katex.min.css
    fonts = src / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, dst / "fonts")
    # MIT: the copyright notice must be included in copies
    katex_license = NODE_MODULES / "katex" / "LICENSE"
    if katex_license.exists():
        shutil.copy2(katex_license, dst / "LICENSE")
    log.info("Copied KaTeX %s", _pkg_version("katex"))


def copy_mermaid() -> None:
    """Copy Mermaid (min.js) from node_modules.

    Vendored so diagrams render offline and the SW can cache the script. The
    theme's base.html exposes the local URL via window.docsforge.mermaidUrl;
    the bundle falls back to a CDN only if that global is missing.
    """
    src = NODE_MODULES / "mermaid" / "dist" / "mermaid.min.js"
    dst = OUT / "assets" / "javascripts" / "mermaid.min.js"
    if not src.exists():
        log.warning("mermaid missing from node_modules")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    # MIT: the copyright notice must be included in copies (esbuild strips
    # the upstream banner, so ship the license file alongside the bundle)
    mermaid_license = NODE_MODULES / "mermaid" / "LICENSE"
    if mermaid_license.exists():
        shutil.copy2(mermaid_license, dst.parent / "mermaid.LICENSE")
    log.info("Copied Mermaid %s", _pkg_version("mermaid"))


def _pkg_version(name: str) -> str:
    try:
        pkg = json.loads((NODE_MODULES / name / "package.json").read_text())
        return pkg.get("version", "?")
    except Exception:
        return "?"


def generate_pygments_css() -> None:
    """Regenerate assets/stylesheets/pygments.css from the installed Pygments.

    The file is the Pygments 'default' style rendered as class rules for
    .highlight (pymdownx.highlight emits class-based spans). It was previously
    a frozen committed snapshot; generating it keeps it in sync with the
    declared `pygments` dependency. Skips with a warning if Pygments is not
    importable (e.g. running the frontend build in an env without Python deps).
    """
    dst = OUT / "assets" / "stylesheets" / "pygments.css"
    try:
        import pygments
        from pygments.formatters import HtmlFormatter
    except ImportError:
        log.warning("pygments not installed; leaving pygments.css unchanged")
        return
    css = HtmlFormatter(style="default").get_style_defs(".highlight")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(css)
    log.info("Regenerated pygments.css (%d bytes, pygments %s)", len(css), getattr(pygments, "__version__", "?"))


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
    parser.add_argument(
        "--fetch-twemoji",
        action="store_true",
        help="Fetch the pinned twemoji SVG set into src/ and exit",
    )
    parser.add_argument("--skip-templates", action="store_true", help="Skip template copy/minify")
    parser.add_argument("--skip-icons", action="store_true", help="Skip icon sync to output")
    parser.add_argument(
        "--refresh-icons",
        action="store_true",
        help="Refresh vendored icon sources in src/ from node_modules (DESTRUCTIVE: "
        "overwrites src/templates/.icons). Run only after `pnpm install`/`pnpm update`, "
        "then review `git status` before committing. The normal build never touches src/.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s - %(message)s",
    )

    if args.fetch_twemoji:
        fetch_twemoji()
        return 0

    if args.clean:
        clean_output()

    # Ensure source tree exists
    if not SRC.exists():
        log.error("Source tree missing: %s", SRC)
        return 1

    # Fail fast on drifted dependencies (silently building with the wrong
    # icon artwork or bundle versions is how output gets corrupted).
    check_dependencies()

    # Build steps
    if args.refresh_icons:
        copy_icons()
    if not args.skip_icons:
        copy_icons_to_out()
    if not args.skip_templates:
        copy_templates()
    build_typescript()
    build_styles()
    generate_pygments_css()
    copy_marz_wasm()
    copy_katex()
    copy_mermaid()
    copy_twemoji()
    copy_sw()

    if args.watch:
        log.info("Watch mode not yet implemented")

    return 0


if __name__ == "__main__":
    sys.exit(main())
