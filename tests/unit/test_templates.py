from __future__ import annotations

import pytest

from docsforge.templates import validate_icon_name


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("material/menu", "material/menu"),
        ("fontawesome/brands/github", "fontawesome/brands/github"),
        ("material/file-edit-outline", "material/file-edit-outline"),
        ("material/brightness-7", "material/brightness-7"),
        ("home", "home"),
        ("  material/menu  ", "material/menu"),
        (None, None),
        ("", None),
        ("material/../etc/passwd", None),
        ("/etc/passwd", None),
        ("material/menu.svg", None),
        ("material//menu", None),
        ("material/", None),
        ("/material/menu", None),
        ("material menu", None),
        ("material@menu", None),
    ],
)
def test_validate_icon_name(value, expected):
    assert validate_icon_name(value) == expected


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("en", "partials/languages/en.html"),
        ("zh", "partials/languages/zh.html"),
        ("pt-BR", "partials/languages/pt-BR.html"),
        # BCP 47 is case-insensitive: configured case need not match the file.
        ("zh-tw", "partials/languages/zh-TW.html"),
        ("ZH-TW", "partials/languages/zh-TW.html"),
        ("pt-br", "partials/languages/pt-BR.html"),
        # Unknown or unsafe locales fall back to English, never crash.
        ("xx-unknown", "partials/languages/en.html"),
        (None, "partials/languages/en.html"),
        ("", "partials/languages/en.html"),
        ("../etc/passwd", "partials/languages/en.html"),
        ("zh-tw/../../x", "partials/languages/en.html"),
    ],
)
def test_resolve_lang_partial(locale, expected):
    from docsforge.templates import resolve_lang_partial

    assert resolve_lang_partial(locale) == expected
