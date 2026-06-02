"""DocsForge CLI - thin front-end around cli_core.py.

Usage:
    docsforge              # Serve if config exists, else start interactive init
    docsforge build        # Production build
    docsforge --migrate    # Migrate from legacy config
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import textwrap
import warnings
from typing import ClassVar

import click

from docsforge import __version__
from docsforge.cli_core import AutoRouter, BuildEngine

if sys.platform.startswith("win"):
    try:
        import colorama
    except ImportError:
        pass
    else:
        colorama.init()

log = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert site name to directory slug."""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug.strip('-') or 'my-docs'


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

        # Avoid duplicate handlers when group + subcommand both instantiate
        if not any(h.name == 'DocsForgeStreamHandler' for h in self.logger.handlers):
            self.stream = logging.StreamHandler()
            self.stream.setFormatter(ColorFormatter())
            self.stream.name = 'DocsForgeStreamHandler'
            self.logger.addHandler(self.stream)

    def __del__(self):
        # Only remove if we created it
        for h in list(self.logger.handlers):
            if h.name == 'DocsForgeStreamHandler':
                self.logger.removeHandler(h)


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

@click.group(
    invoke_without_command=True,
    context_settings=dict(help_option_names=['-h', '--help'], max_content_width=120)
)
@click.version_option(__version__, '-V', '--version', prog_name='docsforge')
@click.option('--migrate', is_flag=True, help='Migrate from legacy config (mkdocs/properdocs)')
@click.option('--migrate-dry-run', is_flag=True, hidden=True, help='Preview migration')
@click.option('--migrate-force', is_flag=True, hidden=True, help='Force overwrite')
@click.option('--strict', is_flag=True, help='Fail on warnings')
@click.pass_context
def docsforge(ctx, migrate, migrate_dry_run, migrate_force, strict):
    """DocsForge - Project documentation with Markdown.

    Smart default: run 'docsforge' alone in a project directory to see
    available commands. If no docsforge.yml exists, starts interactive
    project creation.
    """
    _ = State()  # Initialize default logging

    if migrate:
        from docsforge.cli_core import ProjectManager
        ctx.exit(ProjectManager.migrate(
            dry_run=migrate_dry_run,
            force=migrate_force,
        ))

    # Smart routing: serve, init, or migrate based on project state
    # Only runs when no subcommand is invoked (e.g. plain 'docsforge')
    if ctx.invoked_subcommand is None:
        ctx.exit(AutoRouter.route(
            force_migrate=False,
            strict=strict,
        ))


@docsforge.command()
@click.option('-c', '--clean/--dirty', is_flag=True, default=True, help='Clean build (default) or dirty (incremental)')
@click.option('--strict', is_flag=True, help='Fail on warnings')
@click.option('-d', '--site-dir', type=click.Path(), help='Output directory for built site')
def build(clean, strict, site_dir):
    """Build the DocsForge documentation for production.

    Outputs to site/ by default (or --site-dir).
    """
    _ = State()  # Initialize default logging
    _enable_warnings()

    # Auto-check config and dependencies before building
    from docsforge.cli_core import Validator, _check_optional_deps

    result = Validator.check()
    if result != 0:
        click.secho("\nConfiguration validation failed. Fix the issues above and try again.", fg='red')
        sys.exit(result)

    _check_optional_deps()

    # Build
    result = BuildEngine.build(
        clean=clean,
        strict=strict,
        site_dir=site_dir,
    )

    if result != 0:
        sys.exit(result)

    sys.exit(0)


if __name__ == '__main__':
    docsforge()

# Entry point alias for console scripts
cli = docsforge
