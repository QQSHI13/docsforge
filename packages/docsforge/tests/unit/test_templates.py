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
