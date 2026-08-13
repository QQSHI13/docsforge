#!/usr/bin/env python3
"""DocsForge migration script (standalone — no docsforge install needed).

Converts an existing documentation config to docsforge.yml:

    mkdocs.yml / mkdocs.yaml      (MkDocs, ProperDocs)
    properdocs.yml / properdocs.yaml
    zensical.toml                 (Zensical [project] schema)

Usage:
    python3 migrate.py [--input FILE] [--dry-run] [--force] [--out FILE]

The script prints a migration report and, for anything it cannot convert,
tells the user how to get help. Requires Python 3.11+ and PyYAML (the
bootstrap scripts install PyYAML if missing).

Exit codes: 0 = migrated (or dry-run), 1 = nothing to migrate / error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "migrate.py: PyYAML is required.\n"
        "Install it with:  pip install pyyaml   (or: python3 -m pip install --user pyyaml)\n"
    )
    sys.exit(2)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILES = [
    "mkdocs.yml", "mkdocs.yaml",
    "properdocs.yml", "properdocs.yaml",
    "zensical.toml",
]

EMAIL = "qingquanshi65@gmail.com"
ISSUES_URL = "https://github.com/QQSHI13/docsforge/issues"

# Keys copied verbatim from mkdocs/properdocs configs.
COPY_KEYS = [
    "site_name", "site_url", "site_description", "site_author", "copyright",
    "repo_url", "repo_name", "edit_uri",
    "docs_dir", "site_dir", "dev_addr", "use_directory_urls",
    "extra_css", "extra_javascript", "extra_templates",
    "extra", "validation", "watch", "strict",
    "remote_branch", "remote_name", "markdown_extensions", "not_in_nav",
    "exclude_docs", "draft_docs",
]

# Theme sub-keys copied under theme:.
THEME_COPY_KEYS = [
    "name", "palette", "features", "font", "icon", "logo", "favicon",
    "language", "direction", "custom_dir",
]

# DocsForge built-in plugins. Those auto-load; keep a declaration only when
# it carries configuration options.
BUILTIN_PLUGINS = {"search", "tags", "blog", "meta", "info", "minify", "privacy", "i18n", "social"}

DEPRECATED_KEYS = {
    "google_analytics": "removed — use theme analytics options",
    "pages": "removed — use the `nav:` key",
    "include_search_page": "removed — search is built-in",
    "static_templates": "removed — internal",
}

# Zensical keys that have a docsforge equivalent.
ZENSICAL_KEY_MAP = {
    "site_name": "site_name",
    "site_url": "site_url",
    "site_description": "site_description",
    "site_author": "site_author",
    "copyright": "copyright",
    "repo_url": "repo_url",
    "repo_name": "repo_name",
    "edit_uri": "edit_uri",
    "docs_dir": "docs_dir",
    "content_dir": "docs_dir",  # zensical's name for docs_dir
    "site_dir": "site_dir",
    "exclude_docs": "exclude_docs",
    "extra_css": "extra_css",
    "extra_javascript": "extra_javascript",
}

ZENSICAL_WARN_KEYS = {
    "catalog": "i18n catalog (zensical) — migrate to extra.i18n_languages manually",
    "zensical": "zensical-specific runtime options — not applicable",
    "analytics": "analytics provider config — port to your analytics setup manually",
}

ZENSICAL_THEME_KEYS = {
    "name": "name",
    "language": "language",
    "custom_dir": "custom_dir",
    "logo": "logo",
    "favicon": "favicon",
    "font": "font",
    "features": "features",
    "icon": "icon",
    "direction": "direction",
    "palette": "palette",
}


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.migrated: list[str] = []
        self.warnings: list[str] = []
        self.copied_plugins: list[str] = []

    def ok(self, key: str) -> None:
        self.migrated.append(key)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def contact_block() -> str:
    return (
        "\n"
        "📧  Something the script couldn't migrate? We'll help you move it over.\n"
        f"    Email: {EMAIL}\n"
        f"    Issues: {ISSUES_URL}\n"
        "    Tell us the plugin/hook/feature and your config — a fix or a port\n"
        "    is usually quick."
    )


# ---------------------------------------------------------------------------
# Nav conversion (mkdocs legacy shorthand -> explicit schema)
# ---------------------------------------------------------------------------

def convert_nav(nav, report: Report) -> list | None:
    """Convert legacy `- Title: path` nav into explicit {title, path, children}."""
    if nav is None:
        return None
    if not isinstance(nav, list):
        report.warn("nav is not a list — left as-is")
        return nav

    out: list[dict] = []

    def conv(item):
        if isinstance(item, str):
            # bare filename
            if item.startswith("http://") or item.startswith("https://"):
                report.warn(
                    f"external nav link '{item}' dropped — "
                    "add it as a regular Markdown link instead (docsforge nav is internal-only)"
                )
                return None
            return {"path": item}
        if isinstance(item, dict) and len(item) == 1:
            title, value = next(iter(item.items()))
            if isinstance(value, list):
                children = [c for c in (conv(c) for c in value) if c is not None]
                return {"title": title, "children": children}
            # path (str) or external URL
            if isinstance(value, str):
                if value.startswith("http://") or value.startswith("https://"):
                    report.warn(
                        f"external nav link '{title}' dropped — "
                        "add it as a regular Markdown link instead (docsforge nav is internal-only)"
                    )
                    return None
                return {"title": title, "path": value}
            report.warn(f"nav item {title!r} has unsupported value type — kept as-is")
            return item
        report.warn(f"nav item not convertible: {item!r}")
        return item

    for item in nav:
        converted = conv(item)
        if converted is not None:
            out.append(converted)
    report.ok("nav")
    return out


# ---------------------------------------------------------------------------
# Plugins conversion
# ---------------------------------------------------------------------------

def convert_plugins(plugins, report: Report) -> list | None:
    if plugins is None:
        return None
    if isinstance(plugins, dict):
        plugins = [{k: v} for k, v in plugins.items()]
    if not isinstance(plugins, list):
        report.warn("plugins is not a list — left as-is")
        return plugins

    out: list = []
    for entry in plugins:
        if isinstance(entry, str):
            name = entry
            cfg = None
        elif isinstance(entry, dict) and len(entry) == 1:
            name, cfg = next(iter(entry.items()))
        else:
            report.warn(f"plugin entry not recognized: {entry!r}")
            continue

        clean = name.split("/")[-1]
        if clean in BUILTIN_PLUGINS:
            if cfg:
                out.append({name: cfg})
                report.copied_plugins.append(name)
            elif clean == "social":
                out.append({name: {}})
                report.copied_plugins.append(name)
                report.warn(
                    "social plugin needs: pip install \"docsforge[social]\" (pillow + cairosvg)"
                )
            else:
                report.ok(f"plugin:{clean} (auto-loads — declaration dropped)")
        else:
            report.warn(
                f"third-party plugin '{name}' has no built-in equivalent — "
                "install it separately or port it"
            )
    return out or None


# ---------------------------------------------------------------------------
# Markdown extensions (zensical dict-of-tables -> list)
# ---------------------------------------------------------------------------

def _flatten_dotted(table: dict, prefix: str = "") -> list[tuple[str, object]]:
    """Flatten nested TOML tables into dotted names.

    `[project.markdown_extensions.pymdownx.highlight]` parses to
    `{"pymdownx": {"highlight": {...}}}`; the YAML form needs
    `pymdownx.highlight: {...}`.
    """
    out: list[tuple[str, object]] = []
    for key, value in table.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            # Recurse only if every sub-key is itself a table (nested dotted
            # sections); otherwise treat the whole dict as config values.
            if value and all(isinstance(v, dict) for v in value.values()):
                out.extend(_flatten_dotted(value, name))
                continue
        out.append((name, value))
    return out


def convert_markdown_extensions(mdx, report: Report):
    if mdx is None:
        return None
    if isinstance(mdx, list):
        report.ok("markdown_extensions")
        return mdx
    if not isinstance(mdx, dict):
        report.warn("markdown_extensions is not a list/table — left as-is")
        return mdx

    out = []
    for name, cfg in _flatten_dotted(mdx):
        if isinstance(cfg, dict) and cfg:
            out.append({name: cfg})
        else:
            out.append(name)
    report.ok("markdown_extensions")
    return out


# ---------------------------------------------------------------------------
# YAML (mkdocs / properdocs) conversion
# ---------------------------------------------------------------------------

def convert_yaml_config(data: dict, report: Report) -> dict:
    out: dict = {}

    for key in COPY_KEYS:
        if key in data and data[key] is not None:
            out[key] = data[key]
            report.ok(key)

    for key, hint in DEPRECATED_KEYS.items():
        if key in data:
            report.warn(f"deprecated key '{key}' dropped — {hint}")

    if "INHERIT" in data:
        report.warn("INHERIT not supported — replace with YAML anchors in docsforge.yml")

    # nav
    nav = convert_nav(data.get("nav"), report)
    if nav is not None:
        out["nav"] = nav

    # plugins
    plugins = convert_plugins(data.get("plugins"), report)
    if plugins is not None:
        out["plugins"] = plugins

    # theme
    theme_in = data.get("theme")
    if theme_in is not None:
        if isinstance(theme_in, str):
            out["theme"] = {"name": theme_in}
            report.ok("theme.name")
        elif isinstance(theme_in, dict):
            theme_out = {}
            for key in THEME_COPY_KEYS:
                if key in theme_in:
                    theme_out[key] = theme_in[key]
                    report.ok(f"theme.{key}")
            if "name" not in theme_out:
                theme_out["name"] = "material"
                report.ok("theme.name (defaulted to material)")
            out["theme"] = theme_out

    # hooks
    if "hooks" in data:
        report.warn(
            "hooks copied as-is — MkDocs hook format is close, but verify each hook's events"
        )
        out["hooks"] = data["hooks"]
        report.ok("hooks")

    return out


# ---------------------------------------------------------------------------
# TOML (zensical) conversion
# ---------------------------------------------------------------------------

def convert_toml_config(data: dict, report: Report) -> dict:
    project = data.get("project")
    if isinstance(project, dict):
        src = project
    else:
        src = data  # tolerate bare zensical.toml without [project]

    out: dict = {}

    for src_key, dst_key in ZENSICAL_KEY_MAP.items():
        if src_key in src and src[src_key] is not None:
            out[dst_key] = src[src_key]
            report.ok(dst_key if dst_key == src_key else f"{src_key} -> {dst_key}")
            if src_key == "content_dir":
                report.warn(
                    "zensical 'content_dir' maps to docsforge 'docs_dir' — move content there"
                )

    for key in ("catalog", "zensical", "analytics", "directives"):
        if key in src:
            report.warn(ZENSICAL_WARN_KEYS.get(key, f"zensical key '{key}' not mapped — port manually"))

    # extra (including [[project.extra.social]] array-of-tables)
    extra = src.get("extra")
    if isinstance(extra, dict):
        out["extra"] = extra
        report.ok("extra")
    elif extra is not None:
        report.warn("extra is not a table — left as-is")
        out["extra"] = extra

    # nav
    nav = convert_nav(src.get("nav"), report)
    if nav is not None:
        out["nav"] = nav

    # theme
    theme_in = src.get("theme")
    if isinstance(theme_in, dict):
        theme_out: dict = {}
        for src_key, dst_key in ZENSICAL_THEME_KEYS.items():
            if src_key in theme_in and theme_in[src_key] is not None:
                theme_out[dst_key] = theme_in[src_key]
                report.ok(f"theme.{dst_key}")
        if "name" not in theme_out:
            theme_out["name"] = "material"
            report.ok("theme.name (defaulted to material)")
        out["theme"] = theme_out

    # markdown_extensions
    mdx = src.get("markdown_extensions")
    if mdx is not None:
        conv = convert_markdown_extensions(mdx, report)
        if conv is not None:
            out["markdown_extensions"] = conv

    # plugins
    plugins = src.get("plugins")
    if plugins is not None:
        if isinstance(plugins, dict):
            # zensical: [project.plugins.NAME] -> {"NAME": {cfg}} or {"NAME": None}
            as_list = []
            for name, cfg in plugins.items():
                if isinstance(cfg, dict) and cfg:
                    as_list.append({name: cfg})
                else:
                    as_list.append({name: {}})
            conv = convert_plugins(as_list, report)
            if conv is not None:
                out["plugins"] = conv
        else:
            conv = convert_plugins(plugins, report)
            if conv is not None:
                out["plugins"] = conv

    return out


# ---------------------------------------------------------------------------
# Detection + dispatch
# ---------------------------------------------------------------------------

def detect_input(cwd: Path) -> Path | None:
    for name in INPUT_FILES:
        p = cwd / name
        if p.is_file():
            return p
    return None


def load_config(path: Path, report: Report):
    if path.suffix == ".toml":
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
        report.ok("source: zensical.toml")
        return convert_toml_config(data, report), "zensical.toml"
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            report.warn(f"could not parse {path.name}: {e}")
            return {}, path.name
    report.ok(f"source: {path.name}")
    return convert_yaml_config(data, report), path.name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="migrate.py",
        description="Migrate mkdocs/properdocs/zensical config to docsforge.yml",
    )
    parser.add_argument("--input", help="config file to migrate (auto-detected by default)")
    parser.add_argument("--out", default="docsforge.yml", help="output file (default: docsforge.yml)")
    parser.add_argument("--dry-run", action="store_true", help="print the result without writing")
    parser.add_argument("--force", action="store_true", help="overwrite an existing docsforge.yml")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    report = Report()

    src_path = Path(args.input) if args.input else detect_input(cwd)
    if src_path is None:
        print(
            "docsforge-migrate: no config found.\n"
            "Looked for: " + ", ".join(INPUT_FILES) + "\n"
            "Run `docsforge init` to create a new project instead.",
            file=sys.stderr,
        )
        return 1

    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print(
            f"docsforge-migrate: {out_path} already exists — use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    config, source_name = load_config(src_path, report)

    if not config:
        print("docsforge-migrate: nothing to migrate (empty config).", file=sys.stderr)
        return 1

    yaml_text = yaml.safe_dump(config, sort_keys=False, default_flow_style=False, allow_unicode=True)

    # ---- report ----
    print(f"DocsForge migration — {source_name} → {out_path.name}")
    if report.migrated:
        print(f"✅ Migrated: {len(report.migrated)} items")
        for item in report.migrated:
            print(f"   • {item}")
    else:
        print("✅ Migrated: (no keys found)")

    if report.copied_plugins:
        print(f"ℹ️  Declared built-in plugins kept (with options): {', '.join(report.copied_plugins)}")

    if report.warnings:
        print(f"⚠️  Needs attention ({len(report.warnings)}):")
        for w in report.warnings:
            print(f"   • {w}")
    else:
        print("⚠️  No warnings.")

    if args.dry_run:
        print("\n--- would write docsforge.yml ---")
        print(yaml_text)
    else:
        out_path.write_text(yaml_text, encoding="utf-8")
        print(f"\n✔ Wrote {out_path}")
        print("   Next: install docsforge and build:")
        print("       pip install docsforge")
        print("       docsforge build")

    print(contact_block())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
