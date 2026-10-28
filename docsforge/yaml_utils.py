from __future__ import annotations

import functools
import importlib
import logging
import os
import os.path
from collections.abc import Mapping
from typing import IO, TYPE_CHECKING, Any

import yaml
import yaml_env_tag  # type: ignore[import-untyped]

from docsforge import exceptions

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig

log = logging.getLogger(__name__)


def _construct_python_name(
    loader: yaml.BaseLoader, suffix: str, node: yaml.ScalarNode
) -> Any:
    """Resolve `!!python/name:module.attr` tags (mkdocs config compat).

    Real-world mkdocs configs use e.g.
    `slugify: !!python/name:pymdownx.slugs.uslugify`. SafeLoader rejects
    unknown tags, so without this those configs fail to load.
    """
    del loader, node
    module_name, _, object_name = suffix.rpartition(".")
    if not module_name or not object_name:
        raise exceptions.ConfigurationError(
            f"Could not resolve python/name tag {suffix!r}: expected 'module.attr'"
        )
    # `!!python/name:` can name any module, but the mkdocs-compatible uses are
    # Markdown helpers (slugify functions, etc.). Log anything else so an
    # unexpected import in a semi-trusted config is at least visible at -v.
    if not module_name.startswith(("markdown", "pymdownx")):
        log.debug(f"!!python/name tag imports non-Markdown module {module_name!r} (tag {suffix!r})")
    try:
        module = importlib.import_module(module_name)
        value: Any = module
        for part in object_name.split("."):
            value = getattr(value, part)
        return value
    except (ImportError, AttributeError) as e:
        raise exceptions.ConfigurationError(
            f"Could not resolve python/name tag {suffix!r}: {e}. "
            "The tag must name an importable 'module.attr' (e.g. "
            "!!python/name:pymdownx.slugs.uslugify) and its module must be installed."
        ) from e


def _construct_dir_placeholder(
    config: DocsForgeConfig, loader: yaml.BaseLoader, node: yaml.ScalarNode
) -> _DirPlaceholder:
    loader.construct_scalar(node)

    value: str = (node and node.value) or ""
    prefix, _, suffix = value.partition("/")
    if prefix.startswith("$"):
        if prefix == "$config_dir":
            return ConfigDirPlaceholder(config, suffix)
        if prefix == "$docs_dir":
            return DocsDirPlaceholder(config, suffix)
        raise exceptions.ConfigurationError(
            f"Unknown prefix {prefix!r} in {node.tag} {node.value!r}"
        )
    return RelativeDirPlaceholder(config, value)


class _DirPlaceholder(os.PathLike):
    def __init__(self, config: DocsForgeConfig, suffix: str = ""):
        self.config = config
        self.suffix = suffix

    def value(self) -> str:
        raise NotImplementedError

    def __fspath__(self) -> str:
        """Can be used as a path."""
        return os.path.join(self.value(), self.suffix)

    def __str__(self) -> str:
        """Can be converted to a string to obtain the current class."""
        return self.__fspath__()


class ConfigDirPlaceholder(_DirPlaceholder):
    """
    A placeholder object that gets resolved to the directory of the config file when used as a path.

    The suffix can be an additional sub-path that is always appended to this path.

    This is the implementation of the `!relative $config_dir/suffix` tag, but can also be passed programmatically.
    """

    def value(self) -> str:
        return os.path.dirname(self.config.config_file_path)


class DocsDirPlaceholder(_DirPlaceholder):
    """
    A placeholder object that gets resolved to the docs dir when used as a path.

    The suffix can be an additional sub-path that is always appended to this path.

    This is the implementation of the `!relative $docs_dir/suffix` tag, but can also be passed programmatically.
    """

    def value(self) -> str:
        return self.config.docs_dir


class RelativeDirPlaceholder(_DirPlaceholder):
    """
    A placeholder object that gets resolved to the directory of the Markdown file currently being rendered.

    This is the implementation of the `!relative` tag, but can also be passed programmatically.
    """

    def __init__(self, config: DocsForgeConfig, suffix: str = ""):
        if suffix:
            raise exceptions.ConfigurationError(
                f"'!relative' tag does not expect any value; received {suffix!r}"
            )
        super().__init__(config, suffix)

    def value(self) -> str:
        current_page = self.config._current_page
        if current_page is None:
            raise exceptions.ConfigurationError(
                "The current file is not set for the '!relative' tag. "
                "It cannot be used in this context; the intended usage is within `markdown_extensions`."
            )
        return os.path.dirname(os.path.join(self.config.docs_dir, current_page.file.src_path))


def get_yaml_loader(loader=yaml.SafeLoader, config: DocsForgeConfig | None = None):
    """Wrap PyYaml's loader so we can extend it to suit our needs."""

    class Loader(loader):
        """
        Define a custom loader derived from the global loader to leave the
        global loader unaltered.
        """

        def __init__(self, stream):
            super().__init__(stream)
            # PyYAML does not tell constructors which file they are reading, so
            # remember the stream name for error messages (may be None).
            self.source_name = getattr(stream, "name", None)

        def construct_mapping(self, node, deep=False):
            """Reject duplicate keys instead of silently keeping the last one."""
            if isinstance(node, yaml.MappingNode):
                self.flatten_mapping(node)
                seen: dict[Any, int] = {}
                for key_node, _value_node in node.value:
                    if key_node.tag == "tag:yaml.org,2002:merge":
                        continue  # `<<:` may legally repeat; flatten_mapping merged them.
                    key: Any = self.construct_object(key_node, deep=deep)
                    line = key_node.start_mark.line + 1
                    if key in seen:
                        where = self.source_name or "<string>"
                        raise exceptions.ConfigurationError(
                            f"Duplicate key {key!r} in {where}: "
                            f"first defined on line {seen[key]}, again on line {line}."
                        )
                    seen[key] = line
            return super().construct_mapping(node, deep=deep)


    # Attach Environment Variable constructor.
    # See https://github.com/waylan/pyyaml-env-tag
    Loader.add_constructor("!ENV", yaml_env_tag.construct_env_tag)

    # Attach mkdocs-style !!python/name:module.attr constructor.
    Loader.add_multi_constructor("tag:yaml.org,2002:python/name:", _construct_python_name)

    if config is not None:
        Loader.add_constructor("!relative", functools.partial(_construct_dir_placeholder, config))

    return Loader


def yaml_load(
    source: IO | str,
    loader: type[yaml.BaseLoader | yaml.SafeLoader] | None = None,
    _inheriting: list[str] | None = None,
) -> dict[str, Any]:
    """Return dict of source YAML file using loader, recursively deep merging inherited parent."""
    if loader is None:
        loader = get_yaml_loader()
    # Stack of realpaths currently being resolved, so INHERIT cycles are
    # reported as a ConfigurationError instead of recursing until RecursionError.
    inheriting = _inheriting if _inheriting is not None else []
    own_path = None if isinstance(source, str) else getattr(source, "name", None)
    own_realpath = os.path.realpath(own_path) if own_path else None
    if own_realpath is not None:
        inheriting.append(own_realpath)
    try:
        return _yaml_load_inherited(source, loader, inheriting, own_path)
    finally:
        if own_realpath is not None:
            inheriting.remove(own_realpath)


def _yaml_load_inherited(
    source: IO | str,
    loader: type[yaml.BaseLoader | yaml.SafeLoader],
    inheriting: list[str],
    own_path: str | None,
) -> dict[str, Any]:
    try:
        result = yaml.load(source, Loader=loader)
    except yaml.YAMLError as e:
        raise exceptions.ConfigurationError(
            f"DocsForge encountered an error parsing the configuration file: {e}"
        )
    if result is None:
        return {}
    if "INHERIT" in result and own_path is not None:
        relpath = result.pop("INHERIT")
        if not isinstance(relpath, str):
            raise exceptions.ConfigurationError(
                f"INHERIT must be a file path, got {type(relpath).__name__}"
            )
        config_dir = os.path.realpath(os.path.dirname(own_path))
        abspath = os.path.realpath(os.path.join(config_dir, relpath))
        try:
            common = os.path.commonpath([config_dir, abspath])
        except ValueError as e:
            # e.g. on Windows, paths on different drives have no common path.
            raise exceptions.ConfigurationError(
                f"Inherited config file '{relpath}' resolves outside the config directory."
            ) from e
        if common != config_dir:
            raise exceptions.ConfigurationError(
                f"Inherited config file '{relpath}' resolves outside the config directory."
            )
        if not os.path.isfile(abspath):
            raise exceptions.ConfigurationError(
                f"Inherited config file '{relpath}' does not exist at '{abspath}'."
            )
        if abspath in inheriting:
            chain = " -> ".join([*inheriting, abspath])
            raise exceptions.ConfigurationError(
                f"Circular INHERIT chain detected: {chain}. "
                "A config file cannot inherit from itself, directly or through another file."
            )
        log.debug(f"Loading inherited configuration file: {abspath}")
        with open(abspath, "rb") as fd:
            parent = yaml_load(fd, loader, inheriting)
        result = deep_merge_dicts(parent, result)
    return result


def deep_merge_dicts(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    for key, src_value in src.items():
        if isinstance(dst.get(key), Mapping) and isinstance(src_value, Mapping):
            deep_merge_dicts(dst[key], src_value)
        else:
            dst[key] = src_value
    return dst
