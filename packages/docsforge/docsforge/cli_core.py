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
        theme: str | None = None,
        progress: bool | None = None,
        **kwargs,
    ) -> int:
        """Build documentation.
        
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge.commands import build
        
        try:
            cfg = config_module.load_config(
                config_file=config_file,
                strict=strict,
                theme=theme,
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
        *,
        livereload: bool = True,
        open_browser: bool = False,
        watch_theme: bool = False,
        watch: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Start the development server.
        
        This function blocks until the server is interrupted.
        """
        from docsforge.commands import serve
        
        serve.serve(
            config_file=config_file,
            livereload=livereload,
            open_in_browser=open_browser,
            watch_theme=watch_theme,
            watch=watch or [],
            **kwargs,
        )


class ProjectManager:
    """Project initialization and migration."""
    
    @staticmethod
    def init(
        project_directory: str = '.',
        *,
        site_name: str | None = None,
        site_url: str | None = None,
        theme_color: str = 'teal',
        enable_blog: bool = False,
        enable_search: bool = True,
        enable_tags: bool = False,
        interactive: bool = True,
    ) -> int:
        """Initialize a new project.
        
        If interactive=True and stdin is a TTY, prompts for missing values.
        If interactive=True but stdin is not a TTY, returns an error.
        If interactive=False, uses defaults or provided values.
        
        Returns exit code.
        """
        from docsforge.commands import init
        
        if interactive and site_name is None:
            if not sys.stdin.isatty():
                log.error("Cannot run interactive init in non-TTY environment.")
                log.error("Use: docsforge --init --init-defaults --name='My Site'")
                return 1
            try:
                site_name = input('Site name: ').strip()
            except EOFError:
                log.error("EOF reached. Use non-interactive mode.")
                return 1
        
        if not site_name:
            site_name = 'My Documentation'
        
        try:
            init.init(
                project_directory=project_directory,
                site_name=site_name,
                site_url=site_url,
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

    # Map: plugin name → (import to try, install command)
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
        force_init: bool = False,
        force_migrate: bool = False,
        **kwargs,
    ) -> int:
        """Smart routing - decides what to do based on project state.
        
        Priority:
        1. If --init flag → run init
        2. If --migrate flag → run migrate
        3. If docsforge.yml exists → serve (with auto-check)
        4. If legacy config exists → prompt to migrate, then serve
        5. If no config exists → prompt to init
        
        Returns exit code.
        """
        env = detect_environment()
        
        # Handle forced flags first
        if force_init:
            return ProjectManager.init(**kwargs)
        
        if force_migrate:
            return ProjectManager.migrate(**kwargs)
        
        # Smart routing based on environment
        if not env['config_found']:
            # No config found
            if not sys.stdin.isatty():
                log.error("No docsforge.yml found. Run 'docsforge --init' to create a project.")
                return 1
            
            print("No documentation configuration found.")
            try:
                response = input("Create a new project? [Y/n]: ").strip().lower()
                if response in ('', 'y', 'yes'):
                    return ProjectManager.init(interactive=True)
                else:
                    return 0
            except EOFError:
                log.error("Non-interactive environment. Use 'docsforge --init'.")
                return 1
        
        if env['is_legacy']:
            # Legacy config found
            print(f"\nDetected legacy config: {env['config_path'].name}")
            print("DocsForge is the maintained successor to MkDocs + Material.")
            
            if not sys.stdin.isatty():
                log.error("Legacy config detected. Run 'docsforge --migrate' to convert.")
                return 1
            
            try:
                response = input("Migrate to docsforge.yml now? [Y/n]: ").strip().lower()
                if response in ('', 'y', 'yes'):
                    result = ProjectManager.migrate(
                        config_file=str(env['config_path']),
                    )
                    if result == 0:
                        # Validate migrated config before serving
                        check_result = Validator.check(config_file='docsforge.yml')
                        if check_result != 0:
                            log.error("Migration succeeded but the new config is invalid.")
                            return check_result
                        _check_optional_deps('docsforge.yml')
                        print("\nMigration complete. Starting development server...")
                        DevServer.serve(config_file='docsforge.yml', **kwargs)
                    return result
                else:
                    # Serve with legacy config - auto-check first
                    result = Validator.check(config_file=str(env['config_path']))
                    if result != 0:
                        log.error("Config validation failed. Fix the issues above or run 'docsforge --migrate'.")
                        return result
                    _check_optional_deps(str(env['config_path']))
                    kwargs.pop('config_file', None)
                    DevServer.serve(config_file=str(env['config_path']), **kwargs)
                    return 0
            except EOFError:
                log.error("Non-interactive environment. Use 'docsforge --migrate'.")
                return 1
        
        # docsforge.yml exists → serve (with auto-check)
        result = Validator.check(config_file=str(env['config_path']))
        if result != 0:
            log.error("Config validation failed. Fix the issues above and try again.")
            return result
        
        _check_optional_deps(str(env['config_path']))
        kwargs.pop('config_file', None)
        DevServer.serve(config_file=str(env['config_path']), **kwargs)
        return 0
