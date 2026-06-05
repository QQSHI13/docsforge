"""DocsForge configuration validation command."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import docsforge.config_base as config_module

log = logging.getLogger(__name__)


def check(config_file=None, strict=None, theme=None, use_directory_urls=None) -> int:
    """Validate DocsForge configuration without building.
    
    Returns exit code: 0 = valid, 1 = errors found.
    """
    print()
    print("=" * 60)
    print("  DOCSFORGE CONFIGURATION CHECK")
    print("=" * 60)
    print()
    
    # 1. Find config file
    config_path = _find_config(config_file)
    if not config_path:
        log.error("No docsforge.yml or docsforge.yaml found.")
        print()
        print("  To create a new project:")
        print("    docsforge")
        print("    # (runs interactive init wizard)")
        print()
        return 1
    
    print(f"  Config file:   {config_path}")
    
    # 2. Parse YAML
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f) or {}
    except Exception as e:
        log.error(f"Failed to parse {config_path}: {e}")
        return 1
    
    print(f"  YAML syntax:   ✓ Valid")
    
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
        print(f"  Site URL:      {raw_config['site_url']}")
    
    # 4. Check docs/ directory
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
    
    # 6. Check plugins
    plugins = raw_config.get('plugins', [])
    if plugins is None:
        plugins = []
    if isinstance(plugins, dict):
        plugins = [plugins]
    if isinstance(plugins, str):
        plugins = [plugins]
    
    KNOWN_PLUGINS = {'search', 'tags', 'blog', 'meta', 'info', 'minify', 'privacy'}
    
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
            if clean_name in KNOWN_PLUGINS or name in KNOWN_PLUGINS:
                print(f"                   ✓ {name}")
            else:
                print(f"                   ⚠ {name} (unknown plugin)")
    else:
        print(f"  Plugins:       default set (search, meta, etc.)")
    
    # 7. Full config load test
    print()
    print("  Validating full configuration...")
    try:
        cfg = config_module.load_config(
            config_file=str(config_path),
            strict=strict,
            theme=theme,
            use_directory_urls=use_directory_urls,
        )
        print("  Full config:   ✓ Valid")
    except Exception as e:
        issues.append(f"Configuration validation failed: {e}")
    
    # 8. Print results
    print()
    print("=" * 60)
    
    if issues:
        print()
        print(f"  ERRORS ({len(issues)}):")
        for issue in issues:
            print(f"    ✗ {issue}")
    
    if warnings_list:
        print()
        print(f"  WARNINGS ({len(warnings_list)}):")
        for warning in warnings_list:
            print(f"    ⚠ {warning}")
    
    if not issues and not warnings_list:
        print()
        print("  ✓ Configuration is valid. Ready to build.")
    elif not issues:
        print()
        print("  ✓ Configuration is valid (with warnings).")
    
    print()
    print("  Next step:")
    if not issues:
        print("    docsforge build")
    else:
        print("    Fix errors above, then run: docsforge check")
    print()
    
    return 1 if issues else 0


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
