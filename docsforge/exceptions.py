from __future__ import annotations

import sys
from collections.abc import Sequence

from click import ClickException, echo

if sys.version_info >= (3, 11):
    # ruff targets py310 (matching requires-python), so it cannot see through
    # this guard and flags the builtin as undefined.
    BuildErrorGroup = ExceptionGroup  # noqa: F821
else:
    class BuildErrorGroup(Exception):  # name mirrors the stdlib ExceptionGroup
        """Fallback for the 3.11+ builtin ``ExceptionGroup``.

        ``requires-python`` is >=3.10, where the builtin does not exist. Only
        the surface the build actually uses is reproduced: the message and the
        ``exceptions`` tuple. It intentionally does not implement ``split()``
        or ``except*`` support, which are unavailable on 3.10 anyway.
        """

        def __init__(self, message: str, exceptions: Sequence[BaseException]) -> None:
            if not exceptions:
                raise ValueError("second argument (exceptions) must be a non-empty sequence")
            super().__init__(message)
            self.message = message
            self.exceptions = tuple(exceptions)

        def __str__(self) -> str:
            return f"{self.message} ({len(self.exceptions)} sub-exceptions)"


class DocsForgeException(ClickException):
    """
    The base class which all DocsForge exceptions inherit from. This should
    not be raised directly. One of the subclasses should be raised instead.
    """


MkDocsException = DocsForgeException  # Legacy alias


class Abort(DocsForgeException, SystemExit):
    """Abort the build."""

    code = 1

    def show(self, *args, **kwargs) -> None:
        echo("\n" + self.format_message())


class ConfigurationError(DocsForgeException):
    """
    This error is raised by configuration validation when a validation error
    is encountered. This error should be raised by any configuration options
    defined in a plugin's [config_scheme][].
    """


class BuildError(DocsForgeException):
    """
    This error may be raised by DocsForge during the build process. Plugins should
    not raise this error.
    """


class PluginError(BuildError):
    """
    A subclass of [`docsforge.exceptions.BuildError`][] which can be raised by plugin
    events.
    """
