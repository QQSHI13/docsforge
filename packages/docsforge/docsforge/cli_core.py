"""DocsForge CLI Core - Backend logic independent of CLI interface.

This module provides the core functionality that can be called from any
interface: CLI, VS Code extension, API, or programmatically.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import BinaryIO

from docsforge import config as config_module
from docsforge.config.base import _open_config_file

log = logging.getLogger(__name__)

# Config file priority order (first match wins)
CONFIG_PRIORITY = [
    'docsforge.yml',
    'docsforge.yaml',
    'properdocs.yml',
    'properdocs.yaml',
    'mkdocs.yml',
    'mkdocs.yaml',
]

LEGACY_CONFIGS = {'mkdocs.yml', 'mkdocs.yaml', 'properdocs.yml', 'properdocs.yaml'}


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


def is_legacy_config(config_path: Path) -> bool:
    """Check if the config file is a legacy format (mkdocs/properdocs)."""
    return config_path.name in LEGACY_CONFIGS


def detect_environment() -> dict:
    """Detect the current docs environment.
    
    Returns dict with:
        - config_found: bool
        - config_path: Path | None
        - is_legacy: bool
        - docs_dir_exists: bool
        - has_index: bool
    """
    result = {
        'config_found': False,
        'config_path': None,
        'is_legacy': False,
        'docs_dir_exists': False,
        'has_index': False,
    }
    
    config_path = find_config_file()
    if config_path:
        result['config_found'] = True
        result['config_path'] = config_path
        result['is_legacy'] = is_legacy_config(config_path)
        
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
    """Project initialization and migration."""
    
    @staticmethod
    def init(
        project_directory: str = '.',
        *,
        site_name: str | None = None,
        theme_color: str = 'teal',
        enable_blog: bool = False,
        enable_search: bool = True,
        enable_tags: bool = False,
    ) -> int:
        """Initialize a new project interactively.
        
        Prompts for values in a TTY. If not a TTY, returns error.
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge.commands import init
        
        if not sys.stdin.isatty():
            log.error("No docsforge.yml found. Run in an interactive terminal to create a project.")
            return 1
        
        try:
            # Interactive prompts
            site_name = input(f"Site name [{site_name or 'My Documentation'}]: ").strip() or site_name or 'My Documentation'
            theme_input = input(f"Theme color (teal/indigo/blue/green/red/orange/purple/pink) [{theme_color}]: ").strip() or theme_color
            enable_search = input("Enable search? [Y/n]: ").strip().lower() in ('', 'y', 'yes')
            enable_tags = input("Enable tags? [y/N]: ").strip().lower() in ('y', 'yes')
            enable_blog = input("Enable blog? [y/N]: ").strip().lower() in ('y', 'yes')
            theme_color = theme_input
        except (EOFError, KeyboardInterrupt):
            print()
            log.error("Init cancelled.")
            return 1
        
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
            return 0
        except Exception as e:
            log.error(f"Init failed: {e}")
            return 1
    
    @staticmethod
    def migrate(
        config_file: str | BinaryIO | None = None,
        *,
        dry_run: bool = False,
        force: bool = False,
    ) -> int:
        """Migrate from legacy config to docsforge.yml.
        
        If config_file is not specified, searches for legacy configs.
        Returns exit code.
        """
        from docsforge.commands import migrate
        
        if config_file is None:
            # Search for legacy configs
            for name in ['properdocs.yml', 'properdocs.yaml', 'mkdocs.yml', 'mkdocs.yaml']:
                path = Path(name)
                if path.exists():
                    config_file = str(path)
                    break
        
        return migrate.migrate(
            dry_run=dry_run,
            force=force,
        )


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
        force_migrate: bool = False,
        **kwargs,
    ) -> int:
        """Smart routing - decides what to do based on project state.
        
        Priority:
        1. If legacy config exists -> prompt to migrate, then serve
        2. If docsforge.yml exists -> show help
        3. If no config exists -> start interactive init
        
        Returns exit code.
        """
        env = detect_environment()
        
        # Handle forced flags first
        if force_migrate:
            return ProjectManager.migrate(**kwargs)
        
        # Smart routing based on environment
        if not env['config_found']:
            # No config found -> start interactive init
            if not sys.stdin.isatty():
                log.error("No docsforge.yml found. Run in an interactive terminal to create a project.")
                return 1
            return ProjectManager.init()
        
        if env['is_legacy']:
            # Legacy config found
            print(f"\nDetected legacy config: {env['config_path'].name}")
            print("DocsForge is the maintained successor to MkDocs + Material.")
            print("Run 'docsforge --migrate' to convert.\n")
            
            if not sys.stdin.isatty():
                log.error("Legacy config detected. Run 'docsforge --migrate' to convert.")
                return 1
            
            try:
                response = input("Migrate to docsforge.yml now? [Y/n]: ").strip().lower()
                if response in ('', 'y', 'yes'):
                    result = ProjectManager.migrate(
                        config_file=str(env['config_path']),
                        dry_run=False,
                        force=False,
                    )
                    if result != 0:
                        return result
                    # After migration, show help
                    return 0
                else:
                    # Serve with legacy config anyway
                    return DevServer.serve(config_file=str(env['config_path']), **kwargs)
            except (EOFError, KeyboardInterrupt):
                print()
                log.error("Non-interactive environment. Use 'docsforge --migrate'.")
                return 1
        
        # Normal docsforge.yml found -> show help
        print("DocsForge project detected.\n")
        print("Available commands:")
        print("  docsforge serve    Start dev server with live reload")
        print("  docsforge build    Build for production")
        print("  docsforge --help   Show all options\n")
        return 0
