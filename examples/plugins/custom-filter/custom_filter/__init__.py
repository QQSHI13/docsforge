"""Custom-filter example plugin.

Registers a small Jinja filter (``pluralize``) into the template environment
via ``on_env``, so templates can write:

    {{ comments }} {{ comments | pluralize("comment") }}

Shows the ``on_env`` event, which receives the Jinja environment before any
page is rendered.
"""
from __future__ import annotations

from docsforge.config_base import Config
from docsforge.core.plugin_base import BasePlugin


class CustomFilterConfig(Config):
    """No options — a minimal config still documents the pattern."""


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """Return ``singular`` for a count of 1, ``plural`` (or singular+'s') otherwise."""
    return singular if count == 1 else (plural or singular + "s")


class CustomFilterPlugin(BasePlugin[CustomFilterConfig]):
    """Registers the ``pluralize`` Jinja filter."""

    def on_env(self, env, /, *, config, files):
        env.filters["pluralize"] = pluralize
        return env
