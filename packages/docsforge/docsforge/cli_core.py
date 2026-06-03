"""DocsForge CLI Core - Backend logic independent of CLI interface.

This module provides the core functionality that can be called from any
interface: CLI, VS Code extension, API, or programmatically.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import BinaryIO

from docsforge import config as config_module
from docsforge.config.base import _open_config_file

log = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert site name to directory slug."""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug.strip('-') or 'my-docs'

# Config file priority order (first match wins)
CONFIG_PRIORITY = [
    'docsforge.yml',
    'docsforge.yaml',
]


def find_config_file(config_file: str | BinaryIO | None = None) -> Path | None:
    """Find the appropriate configuration file.
    
    Returns the path if found, None otherwise.
    """
    if config_file is not None:
        if isinstance(config_file, str):
            path = Path(config_file)
            if path.exists():
                return path
        return None
    
    for name in CONFIG_PRIORITY:
        path = Path(name)
        if path.exists():
            return path
    
    return None


def detect_environment() -> dict:
    """Detect the current docs environment.
    
    Returns dict with:
        - config_found: bool
        - config_path: Path | None
        - docs_dir_exists: bool
        - has_index: bool
    """
    result = {
        'config_found': False,
        'config_path': None,
        'docs_dir_exists': False,
        'has_index': False,
    }
    
    config_path = find_config_file()
    if config_path:
        result['config_found'] = True
        result['config_path'] = config_path
        
        # Check if docs/ directory exists
        try:
            with _open_config_file(config_path) as f:
                import yaml
                cfg = yaml.safe_load(f) or {}
                docs_dir = cfg.get('docs_dir', 'docs')
                docs_path = Path(docs_dir)
                result['docs_dir_exists'] = docs_path.exists()
                result['has_index'] = (docs_path / 'index.md').exists()
        except Exception:
            pass
    
    return result


class BuildEngine:
    """Production build engine."""
    
    @staticmethod
    def build(
        config_file: str | BinaryIO | None = None,
        *,
        clean: bool = True,
        strict: bool = False,
        site_dir: str | None = None,
        progress: bool | None = None,
        **kwargs,
    ) -> int:
        """Build documentation.
        
        If config_file is not specified, auto-detects docsforge.yml.
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge.commands import build
        
        try:
            cfg = config_module.load_config(
                config_file=config_file,
                strict=strict,
                site_dir=site_dir,
                **kwargs,
            )
            cfg.plugins.on_startup(command='build', dirty=not clean)
            try:
                build.build(cfg, dirty=not clean, progress=progress)
            finally:
                cfg.plugins.on_shutdown()
            return 0
        except Exception as e:
            log.error(f"Build failed: {e}")
            return 1


class DevServer:
    """Development server engine."""
    
    @staticmethod
    def serve(
        config_file: str | BinaryIO | None = None,
        **kwargs,
    ) -> None:
        """Start the development server with live reload, watch all dirs, open browser.
        
        This function blocks until the server is interrupted.
        """
        from docsforge.commands import serve
        
        serve.serve(
            config_file=config_file,
            livereload=True,
            open_in_browser=True,
            watch_theme=True,
            watch=[],
            **kwargs,
        )


class ProjectManager:
    """Project initialization."""
    
    @staticmethod
    def init(
        project_directory: str | None = None,
        *,
        site_name: str | None = None,
        theme_color: str = 'teal',
        enable_blog: bool = False,
        enable_search: bool = True,
        enable_tags: bool = False,
    ) -> int:
        """Initialize a new project interactively.
        
        Prompts for values in a TTY. Creates a new directory named after the
        site name slug. If not a TTY, returns error.
        
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge.commands import init
        
        if not sys.stdin.isatty():
            log.error("No docsforge.yml found. Run in an interactive terminal to create a project.")
            return 1
        
        # Welcome banner
        print()
        print("=" * 56)
        print("  Welcome to DocsForge!")
        print("  Let's set up your documentation project.")
        print("=" * 56)
        print()
        
        try:
            # Step 1: Site name
            print("Step 1/5 — Site name")
            site_name = input(f"  What should we call your docs? [{site_name or 'My Documentation'}]: ").strip() or site_name or 'My Documentation'
            print()
            
            # Step 2: Theme color
            print("Step 2/5 — Theme color")
            print("  Available: teal, indigo, blue, green, red, orange, purple, pink")
            theme_input = input(f"  Pick a color [{theme_color}]: ").strip() or theme_color
            theme_color = theme_input
            print()
            
            # Step 3: Search
            print("Step 3/5 — Search")
            print("  Full-text search lets users find content across your docs.")
            search_input = input("  Enable search? [Y/n]: ").strip().lower()
            enable_search = search_input in ('', 'y', 'yes')
            print()
            
            # Step 4: Tags
            print("Step 4/5 — Tags")
            print("  Tags let you group pages by topic (e.g. 'tutorial', 'reference').")
            tags_input = input("  Enable tags? [y/N]: ").strip().lower()
            enable_tags = tags_input in ('y', 'yes')
            print()
            
            # Step 5: Blog
            print("Step 5/5 — Blog")
            print("  A blog for changelog posts, announcements, etc.")
            blog_input = input("  Enable blog? [y/N]: ").strip().lower()
            enable_blog = blog_input in ('y', 'yes')
            print()
            
        except (EOFError, KeyboardInterrupt):
            print()
            print("  Cancelled.")
            return 1
        
        # Use site name slug as project directory if not explicitly provided
        if project_directory is None:
            project_directory = _slugify(site_name)
        
        try:
            init.init(
                project_directory=project_directory,
                site_name=site_name or 'My Documentation',
                site_url=None,
                theme_color=theme_color,
                enable_blog=enable_blog,
                enable_search=enable_search,
                enable_tags=enable_tags,
            )
            
            # Summary
            print("=" * 56)
            print("  All done! Here's what was created:")
            print()
            print(f"  Directory:  ./{project_directory}/")
            print(f"  Config:     ./{project_directory}/docsforge.yml")
            print(f"  Docs:       ./{project_directory}/docs/index.md")
            print()
            print("  Next steps:")
            print(f"    cd {project_directory}")
            print("    docsforge serve")
            print()
            print("  Happy documenting! 📚")
            print("=" * 56)
            print()
            return 0
        except Exception as e:
            log.error(f"Init failed: {e}")
            return 1


def _check_optional_deps(config_file=None):
    """Best-effort detection of missing optional dependencies based on config.
    
    Checks configured plugins against importable packages and logs warnings
    with the exact install command needed.
    """
    import yaml
    from docsforge.config.base import _open_config_file

    # Map: plugin name -> (import to try, install command)
    _OPTIONAL_PLUGINS = {
        'material/social': [
            ('PIL', 'pip install docsforge[imaging]'),
            ('cairosvg', 'pip install docsforge[imaging]'),
        ],
        'social': [
            ('PIL', 'pip install docsforge[imaging]'),
            ('cairosvg', 'pip install docsforge[imaging]'),
        ],
    }
    
    try:
        with _open_config_file(config_file) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return  # Best-effort, don't fail build because dep check failed
    
    plugins = cfg.get('plugins', [])
    if not isinstance(plugins, list):
        return
    
    # Flatten plugin names from list of strings/dicts
    plugin_names = set()
    plugin_configs = {}
    for p in plugins:
        if isinstance(p, str):
            plugin_names.add(p)
        elif isinstance(p, dict):
            for k, v in p.items():
                plugin_names.add(k)
                plugin_configs[k] = v
    
    missing = set()
    
    # Check plugin-specific optional deps
    for name in plugin_names:
        if name in _OPTIONAL_PLUGINS:
            for import_name, install_cmd in _OPTIONAL_PLUGINS[name]:
                try:
                    __import__(import_name)
                except ImportError:
                    missing.add(install_cmd)
    
    # Check jieba: enabled if search plugin has jieba_dict configured
    search_cfg = plugin_configs.get('material/search') or plugin_configs.get('search')
    if isinstance(search_cfg, dict) and search_cfg.get('jieba_dict'):
        try:
            __import__('jieba')
        except ImportError:
            missing.add('pip install docsforge[chinese]')
    
    if missing:
        log.warning("Optional dependencies missing for configured plugins.")
        for cmd in sorted(missing):
            log.warning("  %s", cmd)


class Validator:
    """Configuration validation."""
    
    @staticmethod
    def check(config_file: str | BinaryIO | None = None) -> int:
        """Validate configuration without building.
        
        Returns exit code: 0 = valid, 1 = errors found.
        """
        from docsforge.commands import check
        return check.check(config_file=config_file)


class AutoRouter:
    """Smart routing based on project state."""
    
    @staticmethod
    def route(
        *,
        ctx=None,
        **kwargs,
    ) -> int:
        """Smart routing - decides what to do based on project state.
        
        Priority:
        1. If docsforge.yml exists -> show help with project detected notice
        2. If no config exists -> start interactive init
        
        Returns exit code.
        """
        env = detect_environment()
        
        # Smart routing based on environment
        if not env['config_found']:
            # No config found -> start interactive init
            if not sys.stdin.isatty():
                log.error("No docsforge.yml found. Run in an interactive terminal to create a project.")
                return 1
            return ProjectManager.init()
        
        # Normal docsforge.yml found -> show help with project detected notice
        if ctx:
            print("DocsForge project detected.\n")
            print(ctx.get_help())
        return 0
