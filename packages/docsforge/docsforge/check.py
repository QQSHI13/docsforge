"""DocsForge configuration validation command."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml

from docsforge.config_base import load_config
from docsforge.exceptions import Abort, ConfigurationError

log = logging.getLogger(__name__)


BUILTIN_PLUGINS = {'search', 'tags', 'blog', 'meta', 'info', 'minify', 'privacy', 'i18n'}
AUTOLOAD_PLUGINS = {'search', 'tags', 'blog', 'meta', 'info', 'minify', 'privacy'}


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
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f) or {}
    except Exception as e:
        log.error(f"Failed to parse {config_path}: {e}")
        return 1

    print("  YAML syntax:   ✓ Valid")

    # 3. Validate required keys
    issues = []
    warnings_list = []

    if 'site_name' not in raw_config:
        issues.append("Missing required key: 'site_name'")
    else:
        print(f"  Site name:     {raw_config['site_name']}")

    if 'site_url' not in raw_config:
        warnings_list.append("No 'site_url' set. SEO and some features will be limited.")
    else:
        site_url = raw_config['site_url']
        print(f"  Site URL:      {site_url}")
        if isinstance(site_url, str) and not site_url.endswith('/'):
            warnings_list.append("'site_url' should usually end with a trailing slash.")

    if 'site_description' in raw_config:
        print(f"  Description:   {raw_config['site_description']}")
    if 'site_author' in raw_config:
        print(f"  Author:        {raw_config['site_author']}")
    if 'repo_url' in raw_config:
        print(f"  Repository:    {raw_config['repo_url']}")
        if 'edit_uri' in raw_config:
            print(f"  Edit URI:      {raw_config['edit_uri']}")
        else:
            warnings_list.append("'repo_url' is set but 'edit_uri' is not. The default edit path may not match your repo layout.")

    # 4. Check directories
    site_dir = raw_config.get('site_dir', 'site')
    print(f"  Site dir:      {site_dir}")

    docs_dir = raw_config.get('docs_dir', 'docs')
    docs_path = Path(config_path).parent / docs_dir

    if not docs_path.exists():
        issues.append(f"Docs directory not found: {docs_path}")
    else:
        md_files = list(docs_path.rglob('*.md'))
        print(f"  Docs folder:   {docs_path} ({len(md_files)} Markdown files)")

        if not md_files:
            warnings_list.append("No .md files found in docs/ directory.")

        # Check for index.md
        if not (docs_path / 'index.md').exists():
            warnings_list.append("No index.md in docs/. Site will have no homepage.")

    # 5. Check theme
    theme_config = raw_config.get('theme', {})
    if isinstance(theme_config, str):
        theme_name = theme_config
    elif isinstance(theme_config, dict):
        theme_name = theme_config.get('name', 'material')
    else:
        theme_name = 'material'

    from docsforge.utils import get_theme_names
    available_themes = get_theme_names()

    if theme_name not in available_themes:
        issues.append(f"Theme '{theme_name}' not found. Available: {', '.join(available_themes)}")
    else:
        print(f"  Theme:         {theme_name} ✓")

    # Warn if theme keys are placed at the top level instead of under `theme:`
    top_level_theme_keys = {'palette', 'features', 'logo', 'favicon', 'icon', 'font', 'language', 'direction', 'custom_dir'}
    misplaced = top_level_theme_keys & set(raw_config.keys())
    if misplaced:
        warnings_list.append(
            f"Theme keys should be under 'theme:' (found at top level: {', '.join(sorted(misplaced))})."
        )

    # 6. Check plugins
    plugins = raw_config.get('plugins', [])
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
                name = list(plugin.keys())[0]
            else:
                continue

            clean_name = name.split('/')[-1] if '/' in name else name
            if clean_name in BUILTIN_PLUGINS or name in BUILTIN_PLUGINS:
                print(f"                   ✓ {name}")
                if clean_name in AUTOLOAD_PLUGINS:
                    warnings_list.append(
                        f"Plugin '{name}' is built-in and does not need to be declared under 'plugins:'."
                    )
            else:
                print(f"                   • {name} (third-party plugin)")
    else:
        print("  Plugins:       default set (search, meta, etc.)")

    # Check extras
    extra = raw_config.get('extra', {})
    if isinstance(extra, dict):
        if 'social' in extra:
            social = extra['social']
            count = len(social) if isinstance(social, list) else 0
            print(f"  Social links:  {count}")
        if 'analytics' in extra:
            analytics = extra['analytics']
            provider = analytics.get('provider', 'unknown') if isinstance(analytics, dict) else 'unknown'
            print(f"  Analytics:     {provider}")

    # Check for extra assets
    if raw_config.get('extra_css'):
        print(f"  Extra CSS:     {len(raw_config['extra_css'])} file(s)")
    if raw_config.get('extra_javascript'):
        print(f"  Extra JS:      {len(raw_config['extra_javascript'])} file(s)")

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
        print("  Config check:  passed")
    elif not full_validation_ok:
        print("  Config check:  failed")
    else:
        print("  Config check:  passed (with issues above)")

    # 8. Print lightweight results
    if issues:
        print(f"  ERRORS ({len(issues)}):")
        for issue in issues:
            print(f"    ✗ {issue}")

    if warnings_list:
        print(f"  WARNINGS ({len(warnings_list)}):")
        for warning in warnings_list:
            print(f"    ⚠ {warning}")

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

    with open(config_path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}

    changed = False

    # Fix 1: Add trailing slash to site_url
    site_url = raw.get('site_url', '')
    if site_url and isinstance(site_url, str) and not site_url.endswith('/'):
        raw['site_url'] = site_url + '/'
        print(f"  ✓ Added trailing slash to site_url: {raw['site_url']}")
        changed = True

    # Fix 2: Add edit_uri if repo_url is set
    if raw.get('repo_url') and 'edit_uri' not in raw:
        raw['edit_uri'] = 'edit/main/docs/'
        print("  ✓ Added edit_uri: edit/main/docs/")
        changed = True

    # Fix 3: Remove built-in plugins from explicit list
    plugins = raw.get('plugins', [])
    if isinstance(plugins, list):
        new_plugins = []
        for p in plugins:
            name = p if isinstance(p, str) else (list(p.keys())[0] if isinstance(p, dict) else '')
            clean = name.split('/')[-1] if '/' in name else name
            if clean not in KNOWN_PLUGINS and name not in KNOWN_PLUGINS:
                new_plugins.append(p)
            else:
                print(f"  ✓ Removed built-in plugin: {name}")
                changed = True
        raw['plugins'] = new_plugins

    # Fix 4: Move misplaced theme keys under theme:
    theme = raw.get('theme', {})
    if not isinstance(theme, dict):
        theme = {}
    top_level_theme_keys = {'palette', 'features', 'logo', 'favicon', 'icon', 'font', 'language', 'direction', 'custom_dir'}
    for key in list(raw.keys()):
        if key in top_level_theme_keys:
            theme[key] = raw.pop(key)
            print(f"  ✓ Moved '{key}' under 'theme:'")
            changed = True
    raw['theme'] = theme

    if not changed:
        print("  No issues found. Configuration is clean.")
        return 0

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  \nConfiguration updated: {config_path}")
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

    for name in ['docsforge.yml', 'docsforge.yaml']:
        if os.path.exists(name):
            return os.path.abspath(name)

    return None
