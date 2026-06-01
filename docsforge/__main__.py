"""DocsForge CLI - thin front-end around cli_core.py.

Usage:
    docsforge              # Smart: serve, init, or migrate based on context
    docsforge build        # Production build
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import textwrap
import traceback
import warnings
from typing import ClassVar

import click

from docsforge import __version__
from docsforge.cli_core import AutoRouter, BuildEngine, DevServer, InfoReporter, ProjectManager, Validator

if sys.platform.startswith("win"):
    try:
        import colorama
    except ImportError:
        pass
    else:
        colorama.init()

log = logging.getLogger(__name__)


class ColorFormatter(logging.Formatter):
    colors: ClassVar = {
        'CRITICAL': 'red',
        'ERROR': 'red',
        'WARNING': 'yellow',
        'DEBUG': 'blue',
    }

    text_wrapper = textwrap.TextWrapper(
        width=shutil.get_terminal_size(fallback=(0, 0)).columns,
        replace_whitespace=False,
        break_long_words=False,
        break_on_hyphens=False,
        initial_indent=' ' * 11,
        subsequent_indent=' ' * 11,
    )

    def format(self, record):
        message = super().format(record)
        prefix = f'{record.levelname:<8}-  '
        if record.levelname in self.colors:
            prefix = click.style(prefix, fg=self.colors[record.levelname])
        if self.text_wrapper.width:
            msg = '\n'.join(self.text_wrapper.fill(line) for line in message.splitlines())
            return prefix + msg[11:]
        return prefix + message


class State:
    """Maintain logging level."""

    def __init__(self):
        self.logger = logging.getLogger('docsforge')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.stream = logging.StreamHandler()
        self.stream.setFormatter(ColorFormatter())
        self.stream.name = 'DocsForgeStreamHandler'
        self.logger.addHandler(self.stream)

    def __del__(self):
        self.logger.removeHandler(self.stream)


def _enable_warnings():
    if not sys.warnoptions:
        from docsforge import utils
        warning_counter = utils.CountHandler()
        warning_counter.setLevel(logging.WARNING)
        logging.getLogger("docsforge").addHandler(warning_counter)
        warnings.simplefilter('module', DeprecationWarning)


def _set_log_level(level: int):
    """Set the logging level for docsforge."""
    logging.getLogger('docsforge').setLevel(level)


# ---- Main CLI ----

@click.group(context_settings=dict(help_option_names=['-h', '--help'], max_content_width=120))
@click.version_option(__version__, '-V', '--version', prog_name='docsforge')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-q', '--quiet', is_flag=True, help='Silence warnings')
@click.option('--color/--no-color', default=None, help='Force enable or disable color output')
@click.option('--init', is_flag=True, help='Create a new project (interactive wizard)')
@click.option('--init-defaults', is_flag=True, hidden=True, help='Non-interactive project setup')
@click.option('--name', help='Site name for --init', default=None)
@click.option('--migrate', is_flag=True, help='Migrate from legacy config (mkdocs/properdocs)')
@click.option('--migrate-dry-run', is_flag=True, hidden=True, help='Preview migration')
@click.option('--migrate-force', is_flag=True, hidden=True, help='Force overwrite')
@click.option('--check', is_flag=True, help='Validate configuration without building')
@click.option('--info', is_flag=True, help='Show system information')
@click.option('--deps', is_flag=True, help='Show required dependencies')
@click.option('-f', '--config-file', type=click.File('rb'), help='Specify config file')
@click.option('-t', '--theme', help='Theme to use')
@click.option('--strict', is_flag=True, help='Fail on warnings')
@click.option('--no-livereload', is_flag=True, help='Disable live reload (for serve)')
@click.option('--watch', type=click.Path(exists=True), multiple=True, default=[], help='Extra directories to watch')
@click.option('--watch-theme', is_flag=True, help='Watch theme files for changes')
@click.option('--open', 'open_browser', is_flag=True, help='Open browser after starting server')
@click.pass_context
def docsforge(ctx, verbose, quiet, color, init, init_defaults, name, migrate, migrate_dry_run,
              migrate_force, check, info, deps, config_file, theme, strict, no_livereload,
              watch, watch_theme, open_browser):
    """DocsForge - Project documentation with Markdown.

    Smart default: run 'docsforge' alone to start the dev server,
    or create a new project if no config is found.
    """
    # Setup logging
    if quiet:
        _set_log_level(logging.ERROR)
    elif verbose:
        _set_log_level(logging.DEBUG)

    if color is False or (color is None and not sys.stdout.isatty()):
        logging.getLogger('docsforge').handlers[0].setFormatter(
            logging.Formatter('%(levelname)-8s-  %(message)s')
        )

    # Handle forced commands
    if init or init_defaults:
        sys.exit(ProjectManager.init(
            interactive=not init_defaults,
            site_name=name,
        ))

    if migrate:
        sys.exit(ProjectManager.migrate(
            dry_run=migrate_dry_run,
            force=migrate_force,
            config_file=config_file.name if config_file else None,
        ))

    if check:
        sys.exit(Validator.check(config_file=config_file.name if config_file else None))

    if info:
        InfoReporter.show()
        sys.exit(0)

    if deps:
        # Show dependencies
        from docsforge.commands.get_deps import get_deps, get_projects_file
        from docsforge.config.base import _open_config_file
        p = get_projects_file(None)
        with _open_config_file(config_file.name if config_file else None) as f:
            deps_list = get_deps(config_file=f, projects_file=p)
        for dep in deps_list:
            print(dep)
        sys.exit(0)

    # Smart routing: serve, migrate, or init based on project state
    sys.exit(AutoRouter.route(
        force_init=False,
        force_migrate=False,
        force_check=False,
        force_info=False,
        config_file=config_file.name if config_file else None,
        theme=theme,
        strict=strict,
        livereload=not no_livereload,
        watch_theme=watch_theme,
        watch=list(watch),
        open_browser=open_browser,
    ))


@docsforge.command()
@click.option('-c', '--clean/--dirty', is_flag=True, default=True, help='Clean build (default) or dirty (incremental)')
@click.option('--strict', is_flag=True, help='Fail on warnings')
@click.option('--deploy', is_flag=True, help='Deploy to GitHub Pages after build')
@click.option('--check', 'check_first', is_flag=True, help='Validate config before building')
@click.option('-d', '--site-dir', type=click.Path(), help='Output directory for built site')
@click.option('-f', '--config-file', type=click.File('rb'), help='Specify config file')
@click.option('-t', '--theme', help='Theme to use')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-q', '--quiet', is_flag=True, help='Silence warnings')
@click.option('--color/--no-color', default=None, help='Force enable or disable color output')
def build(clean, strict, deploy, check_first, site_dir, config_file, theme, verbose, quiet, color):
    """Build the DocsForge documentation for production.

    Outputs to site/ by default (or --site-dir).
    Use --deploy to publish to GitHub Pages after building.
    """
    # Setup logging
    if quiet:
        _set_log_level(logging.ERROR)
    elif verbose:
        _set_log_level(logging.DEBUG)

    if color is False or (color is None and not sys.stdout.isatty()):
        logging.getLogger('docsforge').handlers[0].setFormatter(
            logging.Formatter('%(levelname)-8s-  %(message)s')
        )

    _enable_warnings()

    config_file_name = config_file.name if config_file else None

    # Check first if requested
    if check_first:
        result = Validator.check(config_file=config_file_name)
        if result != 0:
            sys.exit(result)

    # Build
    result = BuildEngine.build(
        config_file=config_file_name,
        clean=clean,
        strict=strict,
        site_dir=site_dir,
        theme=theme,
    )

    if result != 0:
        sys.exit(result)

    # Deploy if requested
    if deploy:
        from docsforge.commands import gh_deploy
        from docsforge import config as config_module
        try:
            cfg = config_module.load_config(config_file=config_file_name)
            gh_deploy.gh_deploy(cfg)
        except Exception as e:
            log.error(f"Deploy failed: {e}")
            sys.exit(1)

    sys.exit(0)


# Legacy commands (hidden, for backwards compatibility)
@docsforge.command(hidden=True, deprecated=True)
def serve():
    """Deprecated: Use 'docsforge' without arguments."""
    log.warning("'docsforge serve' is deprecated. Use 'docsforge' instead.")
    sys.exit(AutoRouter.route())


@docsforge.command(hidden=True, deprecated=True)
def new():
    """Deprecated: Use 'docsforge --init'."""
    log.warning("'docsforge new' is deprecated. Use 'docsforge --init' instead.")
    sys.exit(ProjectManager.init(interactive=True))


@docsforge.command(hidden=True, deprecated=True)
def gh_deploy():
    """Deprecated: Use 'docsforge build --deploy'."""
    log.warning("'docsforge gh-deploy' is deprecated. Use 'docsforge build --deploy' instead.")
    # Build then deploy
    result = BuildEngine.build()
    if result != 0:
        sys.exit(result)
    from docsforge.commands import gh_deploy as gh_deploy_cmd
    from docsforge import config as config_module
    cfg = config_module.load_config()
    gh_deploy_cmd.gh_deploy(cfg)


if __name__ == '__main__':
    docsforge()
