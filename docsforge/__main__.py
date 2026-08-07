"""DocsForge CLI - thin front-end around cli_core.py.

Usage:
    docsforge              # Show help (or interactive init if no project)
    docsforge build        # Production build
    docsforge serve        # Start dev server
"""

from __future__ import annotations

import logging
import shutil
import sys
import textwrap
import warnings
from typing import ClassVar

import click

from docsforge import __version__
from docsforge.cli_core import AutoRouter, BuildEngine, DevServer

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
            indent = self.text_wrapper.initial_indent
            msg = '\n'.join(self.text_wrapper.fill(line) for line in message.splitlines())
            return prefix + msg[len(indent):]
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


# ---- Main CLI ----

@click.group(
    invoke_without_command=True,
    context_settings=dict(help_option_names=['-h', '--help'], max_content_width=120)
)
@click.version_option(__version__, '-v', '--version', prog_name='docsforge')
@click.pass_context
def docsforge(ctx):
    """DocsForge - Project documentation with Markdown.

    Smart default: run 'docsforge' alone in a project directory to see
    available commands. If no docsforge.yml exists, starts interactive
    project creation.
    """
    _ = State()  # Initialize default logging

    # Smart routing: show help or init based on project state
    # Only runs when no subcommand is invoked (e.g. plain 'docsforge')
    if ctx.invoked_subcommand is None:
        ctx.exit(AutoRouter.route(ctx=ctx))


@docsforge.command()
@click.option('--strict', is_flag=True, help='Fail on warnings')
@click.option('--pdf', is_flag=True, help='Also export to PDF (requires playwright)')
@click.option('--jobs', type=int, default=None, help='Number of parallel tabs for PDF rendering (default: 4)')
def build(strict, pdf, jobs):
    """Build the DocsForge documentation for production."""
    _ = State()  # Initialize default logging
    _enable_warnings()

    # Auto-check config and dependencies before building
    from docsforge.cli_core import Validator, _check_optional_deps

    result = Validator.check()
    if result != 0:
        click.secho("\nConfiguration validation failed. Fix the issues above and try again.", fg='red')
        sys.exit(result)

    _check_optional_deps()

    # Build (dirty/incremental by default — fast, but correct)
    result = BuildEngine.build(
        strict=strict,
    )

    if result != 0:
        sys.exit(result)

    # PDF export
    if pdf:
        from docsforge.pdf import build_pdf as export_pdf
        from docsforge import cli_core
        import yaml
        config_file = cli_core.find_config_file()
        if config_file:
            docs_dir = "docs"
            try:
                with open(config_file) as f:
                    cfg = yaml.safe_load(f) or {}
                docs_dir = cfg.get("docs_dir", "docs")
            except Exception:
                pass
            pdf_kwargs = {"skip_build": True}
            if jobs is not None:
                pdf_kwargs["concurrency"] = jobs
            sys.exit(export_pdf(docs_dir, **pdf_kwargs))

    sys.exit(0)


@docsforge.command()
@click.option('--fix', is_flag=True, help='Auto-fix common configuration issues')
def check(fix):
    """Validate configuration without building."""
    _ = State()
    if fix:
        from docsforge.check import fix_config
        sys.exit(fix_config())
    from docsforge.cli_core import Validator
    sys.exit(Validator.check(full_validation=True))


@docsforge.command()
@click.option('--lan', is_flag=True, help='Serve on all interfaces (0.0.0.0) instead of localhost')
@click.option('--no-open', is_flag=True, help='Do not open a browser tab automatically')
@click.option('--strict', is_flag=True, help='Treat warnings as errors during rebuilds')
def serve(lan, no_open, strict):
    """Start the live-reloading docs server."""
    _ = State()  # Initialize default logging

    # Auto-check config and dependencies before serving
    from docsforge.cli_core import Validator, _check_optional_deps

    result = Validator.check()
    if result != 0:
        click.secho("\nConfiguration validation failed. Fix the issues above and try again.", fg='red')
        sys.exit(result)

    _check_optional_deps()

    # Serve with live reload, auto-increment port if taken, auto-open browser.
    # `strict` flows through to load_config() so rebuilds count warnings and
    # raise Abort (caught by the server's builder, which keeps serving).
    kwargs = {}
    if lan:
        kwargs['host'] = '0.0.0.0'
    if no_open:
        kwargs['open_in_browser'] = False
    DevServer.serve(strict=strict, **kwargs)


if __name__ == '__main__':
    docsforge()

# Entry point alias for console scripts
cli = docsforge
