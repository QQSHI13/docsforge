"""DocsForge configuration validation command."""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import sys
from pathlib import Path

import click
import yaml

from docsforge.config_base import load_config
from docsforge.exceptions import Abort, ConfigurationError
from docsforge.yaml_utils import get_yaml_loader

log = logging.getLogger(__name__)


BUILTIN_PLUGINS = {"search", "tags", "blog", "meta", "info", "minify", "privacy", "i18n", "social"}
AUTOLOAD_PLUGINS = {"search", "tags", "blog", "meta", "info", "minify", "privacy", "i18n"}

# Keys of the explicit nav entry format (mirrors docsforge.nav). Any other
# single-key dict is the `"Title": path-or-children` shorthand.
_EXPLICIT_NAV_KEYS = frozenset({"title", "path", "children", "i18n"})


def _collect_nav_paths(nav):
    """Walk a nav tree, returning (referenced_paths, problems).

    Handles shorthand (`"Title": path`, `"Title": [children]`, bare path
    strings) and explicit (`{title, path, children}`) entries. External
    URLs are skipped (they are Links, not files). `problems` holds
    human-readable descriptions of malformed entries.
    """
    refs: list[str] = []
    problems: list[str] = []

    def walk(node):
        if isinstance(node, str):
            refs.append(node)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if set(node) <= _EXPLICIT_NAV_KEYS:
                path = node.get("path")
                if isinstance(path, str) and path:
                    refs.append(path)
                children = node.get("children")
                if isinstance(children, (list, tuple)):
                    walk(children)
                if not path and not children:
                    problems.append(f"nav entry has neither 'path' nor 'children': {node!r}")
            elif len(node) == 1:
                (title, value), = node.items()
                if isinstance(value, str):
                    refs.append(value)
                elif isinstance(value, (list, tuple)):
                    walk(value)
                else:
                    problems.append(f"nav entry {title!r} has an unsupported value: {value!r}")
            else:
                problems.append(
                    f"nav entry has multiple keys (use explicit title/path/children): {node!r}"
                )
        elif node is not None:
            problems.append(f"unsupported nav entry: {node!r}")

    walk(nav)
    return refs, problems


def _check_extra_assets(raw_config, docs_path, warnings_list):
    """Warn about relative extra_css/extra_javascript files missing on disk."""
    for key in ("extra_css", "extra_javascript"):
        for raw_entry in raw_config.get(key) or []:
            entry = raw_entry.get("path", "") if isinstance(raw_entry, dict) else raw_entry
            if not isinstance(entry, str) or not entry:
                continue
            if entry.startswith(("http://", "https://", "//")):
                continue  # remote URL, nothing to verify locally
            rel = entry.split("?", 1)[0].lstrip("/")
            if rel and not (docs_path / rel).exists():
                warnings_list.append(
                    f"'{key}' references '{entry}' but it was not found in the docs directory."
                )


def _check_nav(raw_config, docs_path, issues, warnings_list):
    """Validate the `nav:` tree against files on disk (no build needed)."""
    nav = raw_config.get("nav")
    if nav is None:
        return
    refs, problems = _collect_nav_paths(nav)
    for problem in problems:
        warnings_list.append(problem)

    # Locales whose files live beside default files as `page.xx.md` twins
    # (mirrors the i18n plugin). A twin is covered by its base entry, so it
    # must not be reported as missing from the nav.
    locales: set[str] = set()
    default_locale: str | None = None
    for lang in (raw_config.get("extra", {}) or {}).get("i18n_languages", []) or []:
        if isinstance(lang, dict) and lang.get("locale"):
            locales.add(str(lang["locale"]))
            if lang.get("default"):
                default_locale = str(lang["locale"])
    twin_locales = locales - ({default_locale} if default_locale else set())

    def is_twin(rel: str) -> bool:
        if not rel.endswith(".md") or not twin_locales:
            return False
        stem = rel[:-len(".md")]
        if "." not in stem:
            return False
        base_stem, suffix = stem.rsplit(".", 1)
        if suffix not in twin_locales:
            return False
        return (docs_path / (base_stem + ".md")).is_file()

    referenced: set[str] = set()
    for ref in refs:
        if not isinstance(ref, str) or not ref:
            continue
        if "://" in ref or ref.startswith("//"):
            continue  # external Link entry, not a file
        rel = ref.lstrip("/")
        referenced.add(rel)
        if not (docs_path / rel).is_file():
            issues.append(f"nav references '{ref}' but '{rel}' was not found in the docs directory.")

    on_disk = {
        p.relative_to(docs_path).as_posix()
        for p in docs_path.rglob("*.md")
        if p.is_file()
    }
    for rel in sorted(on_disk - referenced):
        if is_twin(rel):
            continue
        warnings_list.append(
            f"'{rel}' exists in the docs directory but is not included in the 'nav' configuration."
        )


def check(config_file=None, strict=None, theme=None, use_directory_urls=None, *, full_validation: bool = False) -> int:
    """Validate DocsForge configuration without building.

    By default this is a lightweight check: it parses the YAML, verifies
    required keys, docs directory, theme and plugin names. When
    ``full_validation=True`` (used by the ``docsforge check`` command), it also
    calls ``load_config`` to catch errors the lightweight check misses,
    especially third-party plugins that are configured but not installed.

    Returns exit code: 0 = valid, 1 = errors found.
    """
    # 1. Find config file
    config_path = _find_config(config_file)
    if not config_path:
        log.error("No docsforge.yml or docsforge.yaml found.")
        print("  To create a new project:")
        print("    docsforge")
        print("    # (runs interactive init wizard)")
        return 1

    print(f"  Config file:   {config_path}")

    # 2. Parse YAML
    try:
        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.load(f, Loader=get_yaml_loader()) or {}
    except Exception as e:
        log.error(f"Failed to parse {config_path}: {e}")
        return 1

    print("  YAML syntax:   ", end="")
    click.secho("✓ Valid", fg="green")

    # 3. Validate required keys
    issues = []
    warnings_list = []

    if "site_name" not in raw_config:
        issues.append("Missing required key: 'site_name'")
    else:
        print(f"  Site name:     {raw_config['site_name']}")

    if "site_url" not in raw_config:
        warnings_list.append("No 'site_url' set. SEO and some features will be limited.")
    else:
        site_url = raw_config["site_url"]
        print(f"  Site URL:      {site_url}")
        if isinstance(site_url, str) and not site_url.endswith("/"):
            warnings_list.append("'site_url' should usually end with a trailing slash.")

    if "site_description" in raw_config:
        print(f"  Description:   {raw_config['site_description']}")
    if "site_author" in raw_config:
        print(f"  Author:        {raw_config['site_author']}")
    if "repo_url" in raw_config:
        print(f"  Repository:    {raw_config['repo_url']}")
        if "edit_uri" in raw_config:
            print(f"  Edit URI:      {raw_config['edit_uri']}")
        else:
            warnings_list.append(
                "'repo_url' is set but 'edit_uri' is not. "
                "The default edit path may not match your repo layout."
            )

    # 4. Check directories
    site_dir = raw_config.get("site_dir", "site")
    print(f"  Site dir:      {site_dir}")

    docs_dir = raw_config.get("docs_dir", "docs")
    docs_path = Path(config_path).parent / docs_dir

    if not docs_path.exists():
        issues.append(f"Docs directory not found: {docs_path}")
    else:
        md_files = list(docs_path.rglob("*.md"))
        print(f"  Docs folder:   {docs_path} ({len(md_files)} Markdown files)")

        if not md_files:
            warnings_list.append("No .md files found in docs/ directory.")

        # Check for index.md
        if not (docs_path / "index.md").exists():
            warnings_list.append("No index.md in docs/. Site will have no homepage.")

    # 5. Check theme
    theme_config = raw_config.get("theme", {})
    if isinstance(theme_config, str):
        theme_name = theme_config
    elif isinstance(theme_config, dict):
        theme_name = theme_config.get("name", "material")
    else:
        theme_name = "material"

    from docsforge.utils import get_theme_names
    available_themes = get_theme_names()

    if theme_name not in available_themes:
        issues.append(f"Theme '{theme_name}' not found. Available: {', '.join(available_themes)}")
    else:
        print(f"  Theme:         {theme_name} ", end="")
        click.secho("✓", fg="green")

    # Warn if theme keys are placed at the top level instead of under `theme:`
    top_level_theme_keys = {
        "palette", "features", "logo", "favicon", "icon", "font", "language",
        "direction", "custom_dir",
    }
    misplaced = top_level_theme_keys & set(raw_config.keys())
    if misplaced:
        warnings_list.append(
            f"Theme keys should be under 'theme:' (found at top level: {', '.join(sorted(misplaced))})."
        )

    # 6. Check plugins
    plugins = raw_config.get("plugins", [])
    if plugins is None:
        plugins = []
    if isinstance(plugins, dict):
        plugins = [plugins]
    if isinstance(plugins, str):
        plugins = [plugins]

    if plugins:
        print(f"  Plugins:       {len(plugins)} configured")
        for plugin in plugins:
            if isinstance(plugin, str):
                name = plugin
            elif isinstance(plugin, dict):
                name = next(iter(plugin.keys()))
            else:
                continue

            clean_name = name.split("/")[-1] if "/" in name else name
            if clean_name in BUILTIN_PLUGINS or name in BUILTIN_PLUGINS:
                click.secho(f"                   ✓ {name}", fg="green")
                if clean_name in AUTOLOAD_PLUGINS:
                    # A declaration carrying options (e.g. `blog: {enabled:
                    # false}`) is meaningful — only flag bare redeclarations.
                    options = (
                        next(iter(plugin.values()))
                        if isinstance(plugin, dict)
                        else None
                    )
                    if not options:
                        warnings_list.append(
                            f"Plugin '{name}' is built-in and does not need to be declared under 'plugins:'."
                        )
            else:
                click.secho(f"                   • {name} (third-party plugin)", fg="cyan")
    else:
        print("  Plugins:       default set (search, meta, etc.)")

    # Check extras
    extra = raw_config.get("extra", {})
    if isinstance(extra, dict):
        if "social" in extra:
            social = extra["social"]
            count = len(social) if isinstance(social, list) else 0
            print(f"  Social links:  {count}")
        if "analytics" in extra:
            analytics = extra["analytics"]
            provider = analytics.get("provider", "unknown") if isinstance(analytics, dict) else "unknown"
            print(f"  Analytics:     {provider}")

    # Check for extra assets
    if raw_config.get("extra_css"):
        print(f"  Extra CSS:     {len(raw_config['extra_css'])} file(s)")
    if raw_config.get("extra_javascript"):
        print(f"  Extra JS:      {len(raw_config['extra_javascript'])} file(s)")
    # 6b. Check nav tree against files on disk (paths, orphans, shape).
    # Runs before full validation so nav problems surface even when the
    # config would otherwise fail to load. Skipped when docs_dir itself is
    # missing (already reported as an error above).
    if docs_path.exists():
        _check_extra_assets(raw_config, docs_path, warnings_list)
        _check_nav(raw_config, docs_path, issues, warnings_list)

    # 7. Full validation: load_config catches errors the lightweight check
    # misses, especially third-party plugins that are configured but not
    # installed (e.g. "plugins.backlinks"). This is skipped for the preflight
    # check inside ``docsforge build``/``serve`` because those commands call
    # ``load_config`` themselves right after.
    full_validation_ok = True
    if full_validation:
        try:
            load_config(config_path)
        except (Abort, ConfigurationError):
            # load_config already printed a detailed, friendly error block.
            full_validation_ok = False

    print()
    if full_validation_ok and not issues:
        print("  Config check:  ", end="")
        click.secho("passed ✓  — ready to build!", fg="green", bold=True)
    elif not full_validation_ok:
        print("  Config check:  ", end="")
        click.secho("failed ✗", fg="red", bold=True)
    else:
        print("  Config check:  ", end="")
        click.secho("passed (with issues below)", fg="yellow", bold=True)

    # 8. Print lightweight results
    if issues:
        click.secho(f"  ERRORS ({len(issues)}):", fg="red", bold=True)
        for issue in issues:
            click.secho(f"    ✗ {issue}", fg="red")
        print("  See above — fix these, then run 'docsforge check' again.")

    if warnings_list:
        click.secho(f"  WARNINGS ({len(warnings_list)}):", fg="yellow", bold=True)
        for warning in warnings_list:
            click.secho(f"    ⚠ {warning}", fg="yellow")

    # Flush stdout so the whole check summary appears BEFORE the build/serve
    # logs that follow. build/serve log to stderr (logging.StreamHandler
    # defaults to sys.stderr, unbuffered); check() prints to stdout, which is
    # block-buffered when piped or run without a TTY (CI, `docker run`,
    # `| grep`). Without this flush the check block would be held in the stdout
    # buffer until process exit and appear at the END of the merged output.
    sys.stdout.flush()

    return 0 if full_validation_ok and not issues else 1


def fix_config(config_file=None) -> int:
    """Auto-fix common configuration issues."""
    config_path = _find_config(config_file)
    if not config_path:
        log.error("No docsforge.yml found.")
        return 1

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.load(f, Loader=get_yaml_loader()) or {}

    changed = False

    # Fix 1: Add trailing slash to site_url
    site_url = raw.get("site_url", "")
    if site_url and isinstance(site_url, str) and not site_url.endswith("/"):
        raw["site_url"] = site_url + "/"
        click.secho(f"  ✓ Added trailing slash to site_url: {raw['site_url']}", fg="green")
        changed = True

    # Fix 2: Add edit_uri if repo_url is set
    if raw.get("repo_url") and "edit_uri" not in raw:
        raw["edit_uri"] = "edit/main/docs/"
        click.secho("  ✓ Added edit_uri: edit/main/docs/", fg="green")
        changed = True

    # Fix 3: Remove built-in plugins from explicit list — but only bare
    # redeclarations. An entry carrying options (e.g. `blog: {enabled:
    # false}`) is meaningful configuration, not redundancy.
    plugins = raw.get("plugins", [])
    if isinstance(plugins, list):
        new_plugins = []
        for p in plugins:
            if isinstance(p, dict):
                name = next(iter(p.keys()))
                options = next(iter(p.values()))
            else:
                name, options = p, None
            clean = name.split("/")[-1] if "/" in name else name
            known = BUILTIN_PLUGINS | AUTOLOAD_PLUGINS
            if (clean not in known and name not in known) or options:
                new_plugins.append(p)
            else:
                click.secho(f"  ✓ Removed built-in plugin: {name}", fg="green")
                changed = True
        raw["plugins"] = new_plugins

    # Fix 4: Move misplaced theme keys under theme:
    theme = raw.get("theme", {})
    top_level_theme_keys = {
        "palette", "features", "logo", "favicon", "icon", "font", "language",
        "direction", "custom_dir",
    }
    misplaced = top_level_theme_keys & set(raw.keys())
    if misplaced:
        if isinstance(theme, str):
            theme = {"name": theme}
        elif not isinstance(theme, dict):
            theme = {}
        for key in misplaced:
            theme[key] = raw.pop(key)
            click.secho(f"  ✓ Moved '{key}' under 'theme:'", fg="green")
            changed = True
        raw["theme"] = theme

    if not changed:
        click.secho("  No issues found. Configuration is clean. ✓", fg="green")
        return 0

    # yaml.dump() re-serializes from the parsed tree, so comments, key order
    # inside nested maps, blank lines and quoting style in the original file are
    # lost. Keep a copy next to the config so an unwanted reformat is one `mv`
    # away, and say so rather than silently rewriting the user's file.
    backup_path = config_path + ".bak"
    try:
        shutil.copyfile(config_path, backup_path)
    except OSError as e:
        log.error(f"Could not back up {config_path}: {e}. Aborting without changes.")
        return 1

    # Write to a PID-unique temp file in the same directory, then atomically
    # replace the config. Dumping straight into the config would truncate it
    # before serialization succeeds, destroying the file on dump failure.
    tmp_path = f"{config_path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        os.replace(tmp_path, config_path)
    except Exception as e:
        log.error(f"Could not write {config_path}: {e}. Original preserved at {backup_path}.")
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        return 1
    print(f"  \nConfiguration updated: {config_path}")
    print(f"  Comments and formatting are not preserved; original saved to {backup_path}")
    return 0


def _find_config(config_file) -> str | None:
    """Find configuration file."""
    if config_file:
        if isinstance(config_file, str):
            if os.path.exists(config_file):
                return os.path.abspath(config_file)
        else:
            # It's a file object
            return os.path.abspath(config_file.name)

    for name in ["docsforge.yml", "docsforge.yaml"]:
        if os.path.exists(name):
            return os.path.abspath(name)

    return None
