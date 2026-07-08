"""DocsForge CLI Core - Backend logic independent of CLI interface.

This module provides the core functionality that can be called from any
interface: CLI, VS Code extension, API, or programmatically.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

from docsforge import slugify

if TYPE_CHECKING:
    import docsforge.config_base as config_module

log = logging.getLogger(__name__)

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
            from docsforge.config_base import _open_config_file
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
        strict: bool = False,
        progress: bool | None = None,
        **kwargs,
    ) -> int:
        """Build documentation.
        
        Uses dirty/incremental build by default for speed.
        If config_file is not specified, auto-detects docsforge.yml.
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge import build as build_module
        
        try:
            import docsforge.config_base as config_module
            cfg = config_module.load_config(
                config_file=config_file,
                strict=strict,
                **kwargs,
            )
            cfg.plugins.on_startup(command='build', dirty=True)
            try:
                build_module.build(cfg, dirty=True, progress=progress)
            finally:
                cfg.plugins.on_shutdown()
            return 0
        except Exception as e:
            log.exception(f"Build failed: {e}")
            return 1


class DevServer:
    """Development server engine."""

    @staticmethod
    def serve(
        config_file: str | BinaryIO | None = None,
        *,
        host: str | None = None,
        open_in_browser: bool = True,
        **kwargs,
    ) -> None:
        """Start the development server with live reload, watch all dirs, open browser.

        This function blocks until the server is interrupted.
        """
        from docsforge import serve as serve_module

        serve_module.serve(
            config_file=config_file,
            livereload=True,
            watch_theme=True,
            watch=[],
            host=host,
            open_in_browser=open_in_browser,
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
        privacy: bool = False,
    ) -> int:
        """Initialize a new project interactively.
        
        Prompts for values in a TTY. Creates a new directory named after the
        site name slug. If not a TTY, returns error.
        
        Returns exit code: 0 = success, 1 = failure.
        """
        from docsforge import init as init_module
        
        if not sys.stdin.isatty():
            log.error("No docsforge.yml found. Run in an interactive terminal to create a project.")
            return 1
        
        # Welcome banner
        print()
        print("=" * 56)
        print("  Welcome to DocsForge!")
        print("  Let's set up your documentation project.")
        print("  Core features (search, tags, blog, etc.) are always included.")
        print("=" * 56)
        print()
        
        try:
            # Step 1: Site name
            print("Step 1/10 — Site name")
            site_name = input(f"  What should we call your docs? [{site_name or 'My Documentation'}]: ").strip() or site_name or 'My Documentation'
            print()

            # Step 2: Site description
            print("Step 2/10 — Site description")
            site_description = input("  Short description [Optional]: ").strip() or None
            print()

            # Step 3: Author / Organization
            print("Step 3/10 — Author / Organization")
            author_name = input("  Who is the author or organization? [Optional]: ").strip() or None
            print()

            # Step 4: Copyright
            print("Step 4/10 — Copyright")
            copyright = input("  Copyright notice [Optional]: ").strip() or None
            print()

            # Step 5: Theme color
            print("Step 5/10 — Theme color")
            print("  Available: teal, indigo, blue, green, red, orange, purple, pink")
            theme_input = input(f"  Pick a color [{theme_color}]: ").strip() or theme_color
            theme_color = theme_input
            print()

            # Step 6: Language
            print("Step 6/10 — Language")
            language_input = input("  Site language code [en]: ").strip() or 'en'
            language = language_input
            print()

            # Step 7: GitHub repository
            print("Step 7/10 — GitHub repository")
            print("  Used for social cards and edit links. Format: https://github.com/user/repo")
            repo_url = input("  GitHub repo URL [Optional]: ").strip() or None
            print()

            # Step 8: Site URL (for social cards, RSS, etc.)
            print("Step 8/10 — Site URL")
            print("  Where will your docs be hosted? e.g. https://user.github.io/repo/")
            site_url_input = input("  Site URL [Optional]: ").strip()
            site_url = site_url_input if site_url_input else None
            print()

            # Step 9: Branding assets
            print("Step 9/10 — Branding assets")
            favicon = input("  Path to favicon (relative to docs/) [Optional]: ").strip() or None
            logo = input("  Path to logo (relative to docs/) [Optional]: ").strip() or None
            print()

            # Step 10: Privacy
            print("Step 10/10 — Privacy mode")
            print("  Privacy mode fetches external assets and inlines them locally.")
            print("  This prevents tracking and ensures docs work offline.")
            privacy_input = input("  Enable privacy mode? [Y/n]: ").strip().lower()
            privacy = privacy_input in ('', 'y', 'yes')
            print()

        except (EOFError, KeyboardInterrupt):
            print()
            print("  Cancelled.")
            return 1

        # Use site name slug as project directory if not explicitly provided
        if project_directory is None:
            project_directory = slugify(site_name)

        try:
            init_module.init(
                project_directory=project_directory,
                site_name=site_name or 'My Documentation',
                site_url=site_url,
                theme_color=theme_color,
                privacy=privacy,
                author_name=author_name,
                repo_url=repo_url,
                site_description=site_description,
                language=language,
                copyright=copyright,
                favicon=favicon,
                logo=logo,
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


# Maps optional package names to the install extra that provides them.
OPTIONAL_DEPS = {
    'jieba': 'docsforge[chinese]',
    'playwright': 'docsforge[pdf]',
}


def _check_optional_deps(config_file=None):
    """Best-effort detection of missing optional dependencies based on config.

    Checks configured plugins against importable packages and logs warnings
    with the exact install command needed.
    """
    import yaml
    from docsforge.config_base import _open_config_file

    try:
        with _open_config_file(config_file) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return  # Best-effort, don't fail build because dep check failed

    plugins_cfg = cfg.get('plugins', [])
    if not isinstance(plugins_cfg, list):
        return

    # Collect configured plugin names and their config dicts.
    configured: dict[str, dict] = {}
    for p in plugins_cfg:
        if isinstance(p, str):
            configured[p] = {}
        elif isinstance(p, dict):
            for name, opts in p.items():
                configured[name] = opts if isinstance(opts, dict) else {}

    # Flatten plugin configs for legacy key-based checks.
    plugin_configs = {}
    for p in plugins_cfg:
        if isinstance(p, dict):
            plugin_configs.update(p)

    missing: set[str] = set()

    # Query plugins for declared optional dependencies.
    from docsforge.core.plugin_base import get_plugins

    available = get_plugins()
    for name in configured:
        ep = available.get(name)
        if ep is None:
            continue
        try:
            plugin_cls = ep.load()
        except Exception:
            continue
        for dep in getattr(plugin_cls, 'optional_dependencies', []):
            if dep not in OPTIONAL_DEPS:
                continue
            try:
                __import__(dep)
            except ImportError:
                missing.add(f"pip install {OPTIONAL_DEPS[dep]}")

    # Legacy key-based checks for configs not yet declaring optional deps.
    search_cfg = plugin_configs.get('material/search') or plugin_configs.get('search')
    if isinstance(search_cfg, dict) and search_cfg.get('jieba_dict'):
        try:
            __import__('jieba')
        except ImportError:
            missing.add(f"pip install {OPTIONAL_DEPS['jieba']}")

    if missing:
        log.warning("Optional dependencies missing for configured plugins.")
        for cmd in sorted(missing):
            log.warning("  %s", cmd)


class Validator:
    """Configuration validation."""
    
    @staticmethod
    def check(config_file: str | BinaryIO | None = None, *, full_validation: bool = False) -> int:
        """Validate configuration without building.

        Args:
            full_validation: When True, also run ``load_config`` to catch
                errors the lightweight check misses (e.g. missing third-party
                plugins). Used by ``docsforge check``.

        Returns exit code: 0 = valid, 1 = errors found.
        """
        from docsforge import check as check_module
        return check_module.check(config_file=config_file, full_validation=full_validation)


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
