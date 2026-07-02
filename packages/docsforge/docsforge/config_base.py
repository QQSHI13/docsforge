from __future__ import annotations

import contextlib
import functools
import logging
import os
import sys
import warnings
import yaml
from collections import UserDict
from collections.abc import Iterator, Mapping, Sequence
from typing import IO, TYPE_CHECKING, Any, Generic, TypeVar, overload

from docsforge import exceptions, utils
from docsforge.utils import weak_property

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig


log = logging.getLogger('docsforge.config')


T = TypeVar('T')


class BaseConfigOption(Generic[T]):
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.default = None

    @property
    def default(self):
        try:
            # ensure no mutable values are assigned
            return self._default.copy()
        except AttributeError:
            return self._default

    @default.setter
    def default(self, value):
        self._default = value

    def validate(self, value: object, /) -> T:
        return self.run_validation(value)

    def reset_warnings(self) -> None:
        self.warnings = []

    def pre_validation(self, config: Config, key_name: str) -> None:
        """
        Before all options are validated, perform a pre-validation process.

        The pre-validation process method should be implemented by subclasses.
        """

    def run_validation(self, value: object, /):
        """
        Perform validation for a value.

        The run_validation method should be implemented by subclasses.
        """
        return value

    def format_error(self, value: object, key_name: str, error: Exception) -> str:
        """Format a user-friendly error message with context and suggestions."""
        msg = str(error)
        
        # Add context based on the option type
        if hasattr(self, '_type'):
            expected = self._type.__name__ if hasattr(self._type, '__name__') else str(self._type)
            msg += f"\n  Expected: {expected}"
        
        # Add suggestions for common mistakes
        suggestions = self._get_suggestions(value, key_name)
        if suggestions:
            msg += f"\n  Suggestions: {suggestions}"
        
        return msg
    
    def _get_suggestions(self, value: object, key_name: str) -> str | None:
        """Return suggestions for fixing common config errors."""
        return None

    def post_validation(self, config: Config, key_name: str) -> None:
        """
        After all options have passed validation, perform a post-validation
        process to do any additional changes dependent on other config values.

        The post-validation process method should be implemented by subclasses.
        """

    def __set_name__(self, owner, name):
        if name.endswith('_') and not name.startswith('_'):
            name = name[:-1]
        self._name = name

    @overload
    def __get__(self, obj: Config, type=None) -> T: ...

    @overload
    def __get__(self, obj, type=None) -> BaseConfigOption: ...

    def __get__(self, obj, type=None):
        if not isinstance(obj, Config):
            return self
        return obj[self._name]

    def __set__(self, obj, value: T):
        if not isinstance(obj, Config):
            raise AttributeError(
                f"can't set attribute ({self._name}) because the parent is a {type(obj)} not a {Config}"
            )
        obj[self._name] = value


class ValidationError(Exception):
    """Raised during the validation process of the config on errors."""

    def __eq__(self, other):
        return type(self) is type(other) and str(self) == str(other)


PlainConfigSchemaItem = tuple[str, BaseConfigOption]
PlainConfigSchema = Sequence[PlainConfigSchemaItem]

ConfigErrors = list[tuple[str, Exception]]
ConfigWarnings = list[tuple[str, str]]


class Config(UserDict):
    """
    Base class for DocsForge configuration, plugin configuration (and sub-configuration) objects.

    It should be subclassed and have `ConfigOption`s defined as attributes.
    For examples, see docsforge/plugins/search/lang.py and docsforge/config/defaults.py.

    Behavior as it was in the upstream project prior to version 1.4 is now handled by LegacyConfig.
    """

    _schema: PlainConfigSchema
    config_file_path: str

    def __init_subclass__(cls):
        schema = dict(getattr(cls, '_schema', ()))
        for attr_name, attr in cls.__dict__.items():
            if isinstance(attr, BaseConfigOption):
                schema[getattr(attr, '_name', attr_name)] = attr
        cls._schema = tuple(schema.items())

        for attr_name, attr in cls._schema:
            attr.required = True
            if getattr(attr, '_legacy_required', None) is not None:
                raise TypeError(
                    f"{cls.__name__}.{attr_name}: "
                    "Setting 'required' is unsupported in class-based configs. "
                    "All values are required, or can be wrapped into config_options.Optional"
                )

    def __new__(cls, *args, **kwargs) -> Config:  # noqa: PYI034
        """Compatibility: allow referring to `LegacyConfig(...)` constructor as `Config(...)`."""
        if cls is Config:
            return LegacyConfig(*args, **kwargs)
        return super().__new__(cls)

    def __init__(self, config_file_path: str | bytes | None = None):
        super().__init__()
        self.__user_configs: list[dict] = []
        self.set_defaults()

        self._schema_keys = {k for k, v in self._schema}
        # Ensure config_file_path is a Unicode string
        if config_file_path is not None and not isinstance(config_file_path, str):
            try:
                # Assume config_file_path is encoded with the file system encoding.
                config_file_path = config_file_path.decode(encoding=sys.getfilesystemencoding())
            except UnicodeDecodeError:
                raise ValidationError("config_file_path is not a Unicode string.")
        self.config_file_path = config_file_path or ''

    def set_defaults(self) -> None:
        """
        Set the base config by going through each validator and getting the
        default if it has one.
        """
        for key, config_option in self._schema:
            self[key] = config_option.default

    def _validate(self) -> tuple[ConfigErrors, ConfigWarnings]:
        failed: ConfigErrors = []
        warnings: ConfigWarnings = []

        for key, config_option in self._schema:
            try:
                value = self.get(key)
                self[key] = config_option.validate(value)
                warnings.extend((key, w) for w in config_option.warnings)
                config_option.reset_warnings()
            except ValidationError as e:
                failed.append((key, e))
                break

        for key in set(self.keys()) - self._schema_keys:
            warnings.append((key, f"Unrecognised configuration name: {key}"))

        return failed, warnings

    def _pre_validate(self) -> tuple[ConfigErrors, ConfigWarnings]:
        failed: ConfigErrors = []
        warnings: ConfigWarnings = []

        for key, config_option in self._schema:
            try:
                config_option.pre_validation(self, key_name=key)
                warnings.extend((key, w) for w in config_option.warnings)
                config_option.reset_warnings()
            except ValidationError as e:
                failed.append((key, e))

        return failed, warnings

    def _post_validate(self) -> tuple[ConfigErrors, ConfigWarnings]:
        failed: ConfigErrors = []
        warnings: ConfigWarnings = []

        for key, config_option in self._schema:
            try:
                config_option.post_validation(self, key_name=key)
                warnings.extend((key, w) for w in config_option.warnings)
                config_option.reset_warnings()
            except ValidationError as e:
                failed.append((key, e))

        return failed, warnings

    def validate(self) -> tuple[ConfigErrors, ConfigWarnings]:
        failed, warnings = self._pre_validate()

        run_failed, run_warnings = self._validate()

        failed.extend(run_failed)
        warnings.extend(run_warnings)

        # Only run the post validation steps if there are no failures, warnings
        # are okay.
        if len(failed) == 0:
            post_failed, post_warnings = self._post_validate()
            failed.extend(post_failed)
            warnings.extend(post_warnings)

        return failed, warnings

    def load_dict(self, patch: dict) -> None:
        """Load config options from a dictionary."""
        if not isinstance(patch, dict):
            raise exceptions.ConfigurationError(
                "The configuration is invalid. Expected a key-"
                f"value mapping (dict) but received: {type(patch)}"
            )

        self.__user_configs.append(patch)
        self.update(patch)

    def load_file(self, config_file: IO) -> None:
        """Load config options from the open file descriptor of a YAML file."""
        warnings.warn(
            "Config.load_file is not used in DocsForge and will be removed soon. "
            "Use DocsForgeConfig.load_file instead",
            DeprecationWarning,
        )
        return self.load_dict(utils.yaml_load(config_file))

    @weak_property
    def user_configs(self) -> Sequence[Mapping[str, Any]]:
        warnings.warn(
            "user_configs is never used in DocsForge and will be removed soon.", DeprecationWarning
        )
        return self.__user_configs


@functools.cache
def get_schema(cls: type) -> PlainConfigSchema:
    """Extract ConfigOptions defined in a class (used just as a container) and put them into a schema tuple."""
    if issubclass(cls, Config):
        return cls._schema
    return tuple((k, v) for k, v in cls.__dict__.items() if isinstance(v, BaseConfigOption))


class LegacyConfig(Config):
    """A configuration object for plugins, as just a dict without type-safe attribute access."""

    def __init__(self, schema: PlainConfigSchema, config_file_path: str | None = None):
        self._schema = tuple((k, v) for k, v in schema)  # Re-create just for validation
        super().__init__(config_file_path)


@contextlib.contextmanager
def _open_config_file(config_file: str | IO | None) -> Iterator[IO]:
    """
    A context manager which yields an open file descriptor ready to be read.

    Accepts a filename as a string, an open or closed file descriptor, or None.
    When None, it defaults to `docsforge.yml` in the CWD. If a closed file descriptor
    is received, a new file descriptor is opened for the same file.

    The file descriptor is automatically closed when the context manager block is existed.
    """
    # Default to the standard config filename.
    if config_file is None:
        paths_to_try = ['docsforge.yml', 'docsforge.yaml']
    # If it is a string or path-like, attempt to open it as a file path.
    elif isinstance(config_file, (str, os.PathLike)):
        paths_to_try = [os.fspath(config_file)]
    else:
        result_config_file = config_file
        paths_to_try = None

    if paths_to_try:
        # config_file is not a file descriptor, so open it as a path.
        for path in paths_to_try:
            abspath = os.path.abspath(path)
            log.debug(f"Loading configuration file: {abspath}")
            try:
                result_config_file = open(abspath, 'rb')
                break
            except FileNotFoundError:
                continue
        else:
            raise exceptions.ConfigurationError(f"Config file '{paths_to_try[0]}' does not exist.")
    else:
        log.debug(f"Loading configuration file: {result_config_file}")
        # Ensure file descriptor is at beginning
        with contextlib.suppress(OSError):
            result_config_file.seek(0)

    try:
        yield result_config_file
    finally:
        if hasattr(result_config_file, 'close'):
            result_config_file.close()


def load_config(
    config_file: str | IO | None = None, *, config_file_path: str | None = None, **kwargs
) -> DocsForgeConfig:
    """
    Load the configuration for a given file object or name.

    The config_file can either be a file object, string or None. If it is None
    the default `docsforge.yml` filename will loaded.

    Extra kwargs are passed to the configuration to replace any default values
    unless they themselves are None.
    """
    options = kwargs.copy()

    # Filter None values from the options. This usually happens with optional
    # parameters from Click.
    for key, value in options.copy().items():
        if value is None:
            options.pop(key)

    with _open_config_file(config_file) as fd:
        # Initialize the config with the default schema.
        from docsforge.config_defaults import DocsForgeConfig

        if config_file_path is None:
            if sys.stdin and fd is not sys.stdin.buffer:
                config_file_path = getattr(fd, 'name', None)
        cfg = DocsForgeConfig(config_file_path=config_file_path)
        # load the config file
        try:
            cfg.load_file(fd)
        except yaml.YAMLError as e:
            print()
            print("=" * 60)
            print("  YAML SYNTAX ERROR")
            print("=" * 60)
            print()
            print(f"  Failed to parse {config_file_path or 'docsforge.yml'}:")
            print()
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                print(f"  Line {mark.line + 1}, Column {mark.column + 1}:")
                print(f"  {e.problem}")
                print()
                print("  Common fixes:")
                print("    - Use spaces, not tabs for indentation")
                print("    - Wrap special characters in quotes: 'value'")
                print("    - Ensure lists use '- ' before each item")
            else:
                print(f"  {e}")
            print()
            raise exceptions.Abort("YAML syntax error — fix the issues above and try again.")

    # Then load the options to overwrite anything in the config.
    cfg.load_dict(options)

    errors, warnings = cfg.validate()

    for config_name, warning in warnings:
        log.warning(f"Config value '{config_name}': {warning}")

    for key, value in cfg.items():
        log.debug(f"Config value '{key}' = {value!r}")

    if len(errors) > 0:
        # Format friendly error messages
        print()
        print("=" * 60)
        print("  CONFIGURATION ERROR")
        print("=" * 60)
        print()
        print(f"  Found {len(errors)} error(s) in {config_file_path or 'docsforge.yml'}:")
        print()
        for config_name, error in errors:
            print(f"  ✗ {config_name}")
            print(f"    {error}")
            print()
        print("  Common fixes:")
        print("    - Check docsforge.yml syntax (no tabs, proper indentation)")
        print("    - See docs: https://qqshi13.github.io/docsforge-docs/")
        print()
        raise exceptions.Abort("Configuration error — fix the issues above and try again.")
    elif cfg.strict and len(warnings) > 0:
        raise exceptions.Abort(
            f"Aborted with {len(warnings)} configuration warnings in 'strict' mode!"
        )

    return cfg
