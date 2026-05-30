"""DocsForge migration command - converts mkdocs.yml to docsforge.yml."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

# Plugins that DocsForge supports natively (built-in or compatible)
SUPPORTED_PLUGINS = {
    'search',
    'tags',
    'blog',
    'info',
    'meta',
    'minify',
    'privacy',
    'social',
    'offline',
    'optimize',
    'typeset',
    'git-committers',
    'git-authors',
    'glightbox',
    'redirects',
    'rss',
    'statistics',
}

# Plugins that require manual attention
KNOWN_UNSUPPORTED = {
    'material/subscriptions': 'Not supported. DocsForge is self-contained, no subscription model.',
    'material/meta': 'Use the built-in meta plugin instead.',
    'i18n': 'Internationalization not yet supported in DocsForge.',
    'mkdocs-video': 'Video embedding not included. Use standard Markdown image syntax with HTML5 video.',
    'exclude': 'Use exclude_docs in docsforge.yml instead.',
    'mkdocstrings': 'API docs not included. Consider using docsforge with external API doc tools.',
    'gen-files': 'Not supported. Use pre-build scripts instead.',
    'literate-nav': 'Not supported. Use standard nav configuration.',
    'section-index': 'Not supported. Use explicit nav configuration.',
}

# Config keys that are identical
PASSTHROUGH_KEYS = {
    'site_name',
    'site_url',
    'site_author',
    'site_description',
    'repo_url',
    'repo_name',
    'edit_uri',
    'copyright',
    'google_analytics',
    'extra',
    'nav',
    'theme',
    'plugins',
    'markdown_extensions',
    'mdx_configs',
    'hooks',
    'extra_css',
    'extra_javascript',
    'watch',
    'strict',
    'dev_addr',
    'use_directory_urls',
    'site_dir',
}

# Keys to remove/rename
DEPRECATED_KEYS = {
    'docs_dir': 'docs_dir is no longer a top-level config key. Use docs_dir inside docsforge.yml or keep default.',
    'extra_templates': 'extra_templates is not supported. Use custom_dir in theme config instead.',
}


def find_mkdocs_config() -> Path | None:
    """Find mkdocs.yml or mkdocs.yaml in current directory."""
    for name in ['mkdocs.yml', 'mkdocs.yaml']:
        path = Path(name)
        if path.exists():
            return path
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML config file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def analyze_plugins(config: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Analyze plugins and return (supported, unsupported, warnings)."""
    plugins = config.get('plugins', [])
    if plugins is None:
        plugins = []
    if isinstance(plugins, dict):
        # Single plugin shorthand
        plugins = [plugins]
    
    supported = []
    unsupported = []
    warnings_list = []
    
    for plugin in plugins:
        if isinstance(plugin, str):
            name = plugin
            config_dict = {}
        elif isinstance(plugin, dict):
            name = list(plugin.keys())[0]
            config_dict = plugin[name]
        else:
            continue
        
        # Normalize name
        clean_name = name.split('/')[-1] if '/' in name else name
        
        if clean_name in SUPPORTED_PLUGINS:
            supported.append(name)
        elif name in KNOWN_UNSUPPORTED:
            unsupported.append(name)
            warnings_list.append(f"Plugin '{name}': {KNOWN_UNSUPPORTED[name]}")
        else:
            unsupported.append(name)
            warnings_list.append(f"Plugin '{name}': Unknown plugin. May or may not work with DocsForge.")
    
    return supported, unsupported, warnings_list


def convert_config(mkdocs_config: dict[str, Any]) -> dict[str, Any]:
    """Convert mkdocs config to docsforge format."""
    docsforge_config = {}
    
    # Copy passthrough keys
    for key in PASSTHROUGH_KEYS:
        if key in mkdocs_config:
            docsforge_config[key] = deepcopy(mkdocs_config[key])
    
    # Handle plugins specially
    if 'plugins' in mkdocs_config:
        plugins = mkdocs_config['plugins']
        if plugins is None:
            docsforge_config['plugins'] = None
        else:
            new_plugins = []
            for plugin in plugins:
                if isinstance(plugin, str):
                    name = plugin
                elif isinstance(plugin, dict):
                    name = list(plugin.keys())[0]
                else:
                    continue
                
                # Skip material-specific plugins that are built-in
                if name.startswith('material/'):
                    continue
                
                new_plugins.append(plugin)
            
            docsforge_config['plugins'] = new_plugins
    
    # Handle docs_dir - it's still valid in DocsForge
    if 'docs_dir' in mkdocs_config:
        docsforge_config['docs_dir'] = mkdocs_config['docs_dir']
    
    # Add DocsForge-specific defaults that differ from MkDocs
    if 'theme' in docsforge_config and isinstance(docsforge_config['theme'], dict):
        # Ensure Material theme is specified
        if 'name' not in docsforge_config['theme']:
            docsforge_config['theme']['name'] = 'material'
    
    return docsforge_config


def write_yaml(config: dict[str, Any], path: Path) -> None:
    """Write config to YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# DocsForge configuration\n')
        f.write('# Migrated from mkdocs.yml\n')
        f.write('# See https://qqshi13.github.io/docsforge-docs/ for full documentation\n\n')
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def migrate(dry_run: bool = False, force: bool = False) -> int:
    """Main migration entry point. Returns exit code."""
    mkdocs_path = find_mkdocs_config()
    
    if not mkdocs_path:
        log.error("No mkdocs.yml or mkdocs.yaml found in current directory.")
        return 1
    
    docsforge_path = Path('docsforge.yml')
    
    if docsforge_path.exists() and not force:
        log.error(
            f"docsforge.yml already exists. Use --force to overwrite, or remove it first.\n"
            f"  Existing: {docsforge_path.absolute()}"
        )
        return 1
    
    log.info(f"Reading configuration from {mkdocs_path}")
    
    try:
        mkdocs_config = load_yaml(mkdocs_path)
    except Exception as e:
        log.error(f"Failed to parse {mkdocs_path}: {e}")
        return 1
    
    # Analyze plugins
    supported, unsupported, warnings = analyze_plugins(mkdocs_config)
    
    # Convert config
    docsforge_config = convert_config(mkdocs_config)
    
    # Print summary
    print()
    print("=" * 60)
    print("  DOCSFORGE MIGRATION REPORT")
    print("=" * 60)
    print()
    print(f"  Source:      {mkdocs_path.absolute()}")
    print(f"  Destination: {docsforge_path.absolute()}")
    print()
    
    print(f"  Supported plugins ({len(supported)}):")
    for p in supported:
        print(f"    ✓ {p}")
    
    if unsupported:
        print()
        print(f"  Attention needed ({len(unsupported)}):")
        for w in warnings:
            print(f"    ⚠ {w}")
    
    deprecated_found = [k for k in DEPRECATED_KEYS if k in mkdocs_config]
    if deprecated_found:
        print()
        print(f"  Deprecated keys found ({len(deprecated_found)}):")
        for k in deprecated_found:
            print(f"    ⚠ {k}: {DEPRECATED_KEYS[k]}")
    
    print()
    print("=" * 60)
    print()
    
    if dry_run:
        log.info("Dry run - no changes written.")
        print("Run without --dry-run to create docsforge.yml")
        return 0
    
    # Write the new config
    try:
        write_yaml(docsforge_config, docsforge_path)
        log.info(f"Created {docsforge_path}")
    except Exception as e:
        log.error(f"Failed to write {docsforge_path}: {e}")
        return 1
    
    # Optionally backup the old config
    backup_path = mkdocs_path.with_suffix('.yml.backup')
    if not backup_path.exists():
        shutil.copy2(mkdocs_path, backup_path)
        log.info(f"Backed up original to {backup_path}")
    
    print()
    print("Next steps:")
    print("  1. Review docsforge.yml for any needed adjustments")
    print("  2. Run 'docsforge build' to test the migration")
    print("  3. Run 'docsforge serve' for live preview")
    print("  4. When satisfied, you can remove mkdocs.yml")
    print()
    print("Documentation: https://qqshi13.github.io/docsforge-docs/")
    print()
    
    return 0
