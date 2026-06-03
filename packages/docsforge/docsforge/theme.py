# Copyright (c) 2026 QQ (Cyrus)
#
# This file is part of DocsForge.
#
# DocsForge is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DocsForge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with DocsForge.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
import os
import warnings
from collections.abc import Collection, MutableMapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import jinja2
    import yaml

from docsforge import localization
from docsforge.config_base import ValidationError

log = logging.getLogger("docsforge.theme")


class Theme(MutableMapping[str, Any]):
    """
    A Theme object.

    Args:
        name: The name of the theme as defined by its entrypoint.
        custom_dir: User defined directory for custom templates.
        static_templates: A list of templates to render as static pages.

    All other keywords are passed as-is and made available as a key/value mapping.
    """

    def __init__(
        self,
        name: str | None = None,
        *,
        custom_dir: str | None = None,
        static_templates: Collection[str] = (),
        locale: str | None = None,
        **user_config,
    ) -> None:
        self.name = name
        self._custom_dir = custom_dir
        _vars: dict[str, Any] = {'name': name, 'locale': 'en'}
        self.__vars = _vars

        # DocsForge provided static templates
        package_dir = os.path.abspath(os.path.dirname(__file__))
        docsforge_templates = os.path.join(package_dir, 'templates')
        # Only include known static templates, not layout templates
        self.static_templates = set()
        for name in ('404.html', 'sitemap.xml'):
            path = os.path.join(docsforge_templates, name)
            if os.path.exists(path):
                self.static_templates.add(name)

        # Build self.dirs from various sources in order of precedence
        self.dirs = []

        if custom_dir is not None:
            self.dirs.append(custom_dir)

        if name:
            self._load_theme_config(name)

        # Include templates provided directly by DocsForge (outside any theme)
        # Skip if already included as the theme directory (e.g., when theme is material)
        if docsforge_templates not in self.dirs:
            self.dirs.append(docsforge_templates)

        # Handle remaining user configs. Override theme configs (if set)
        self.static_templates.update(static_templates)
        _vars.update(user_config)

        # Validate locale and convert to Locale object
        if locale is None:
            locale = _vars['locale']
        _vars['locale'] = localization.parse_locale(locale)

    name: str | None

    @property
    def locale(self) -> localization.Locale:
        return self['locale']

    @property
    def custom_dir(self) -> str | None:
        return self._custom_dir

    @property
    def _vars(self) -> dict[str, Any]:
        warnings.warn(
            "Do not access Theme._vars, instead access the keys of Theme directly.",
            DeprecationWarning,
        )
        return self.__vars

    dirs: list[str]

    static_templates: set[str]

    def __repr__(self) -> str:
        return "{}(name={!r}, dirs={!r}, static_templates={!r}, {})".format(
            self.__class__.__name__,
            self.name,
            self.dirs,
            self.static_templates,
            ', '.join(f'{k}={v!r}' for k, v in self.items()),
        )

    def __getitem__(self, key: str) -> Any:
        return self.__vars[key]

    def __setitem__(self, key: str, value):
        self.__vars[key] = value

    def __delitem__(self, key: str):
        del self.__vars[key]

    def __contains__(self, item: object) -> bool:
        return item in self.__vars

    def __len__(self):
        return len(self.__vars)

    def __iter__(self):
        return iter(self.__vars)

    def _load_theme_config(self, name: str) -> None:
        """Recursively load theme and any parent themes."""
        import yaml
        try:
            from yaml import CSafeLoader as SafeLoader
        except ImportError:
            from yaml import SafeLoader
        from docsforge import utils
        from docsforge.config_base import ValidationError

        theme_dir = utils.get_theme_dir(name)
        utils.get_themes.cache_clear()
        self.dirs.append(theme_dir)

        # Try theme root first, then templates/ subdirectory
        file_path = os.path.join(theme_dir, 'docsforge_theme.yml')
        if not os.path.exists(file_path):
            file_path = os.path.join(theme_dir, 'templates', 'docsforge_theme.yml')
        try:
            with open(file_path, 'rb') as f:
                theme_config = yaml.load(f, SafeLoader)
        except OSError as e:
            log.debug(e)
            raise ValidationError(
                f"The theme '{name}' does not appear to have a configuration file. "
                f"Please upgrade to a current version of the theme."
            )

        if theme_config is None:
            theme_config = {}

        log.debug(f"Loaded theme configuration for '{name}' from '{file_path}': {theme_config}")

        if parent_theme := theme_config.pop('extends', None):
            themes = utils.get_theme_names()
            if parent_theme not in themes:
                raise ValidationError(
                    f"The theme '{name}' inherits from '{parent_theme}', which does not appear to be installed. "
                    f"The available installed themes are: {', '.join(themes)}"
                )
            self._load_theme_config(parent_theme)

        self.static_templates.update(theme_config.pop('static_templates', []))
        self.__vars.update(theme_config)

    def get_env(self) -> jinja2.Environment:
        """Return a Jinja environment for the theme."""
        import jinja2
        from docsforge import templates
        loader = jinja2.FileSystemLoader(self.dirs)
        # No autoreload because editing a template in the middle of a build is not useful.
        env = jinja2.Environment(loader=loader, auto_reload=False)
        env.filters['url'] = templates.url_filter
        env.filters['script_tag'] = templates.script_tag_filter
        localization.install_translations(env, self.locale, self.dirs)
        return env
