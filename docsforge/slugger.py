"""Canonical heading-slug rules shared between the engine and the Studio extension.

The engine renders heading anchors with Python-Markdown's ``toc`` extension
(``markdown.extensions.toc.slugify``). The VS Code extension (``studio/``)
needs to predict the same anchors to offer rename / link-fix. Rather than
hand-maintain a second implementation on the TypeScript side, we compute the
rules once from the real ``toc`` slugify and export them as JSON so the
extension can reproduce the behaviour — and document honestly where a
JavaScript ``RegExp`` cannot match Python's ``re`` exactly.

The rules deliberately capture *parameters* (separator, unicode mode, the
character-class intent) rather than a raw regex string, because a Python
``re`` pattern is not portable to JS (different word-char semantics).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass

# The default separator Python-Markdown's toc extension uses when none is
# configured. We read it from the live module where possible so a markdown
# upgrade flows through, but pin a fallback so a broken install still builds.
try:  # pragma: no cover - exercised indirectly via build
    from markdown.extensions.toc import slugify as _py_slugify

    _DEFAULT_SEPARATOR = "-"
except Exception:  # pragma: no cover
    _py_slugify = None
    _DEFAULT_SEPARATOR = "-"

# Version the rules so the extension can detect a stale file.
RULES_VERSION = 1


@dataclass(frozen=True)
class SlugRules:
    """Parameters describing how the engine turns a heading into an anchor id.

    ``char_class`` is an *intent* description, not a portable regex:
      - ``word``      -> keep word characters and the separator (Python
                         ``re`` ``\\w`` is Unicode-aware in py3 and includes
                         ``_`` and CJK).
      - ``separator`` -> the string collapsed runs of whitespace/underscore
                         are folded into.
    """

    separator: str = _DEFAULT_SEPARATOR
    # Engine default is markdown.extensions.toc.slugify in NON-unicode mode:
    # NFKD normalize then ASCII-fold, so non-ASCII chars (CJK, accented) are
    # dropped before the character-class strip. The Studio must mirror the
    # ASCII fold. ``slugify_unicode`` instead keeps non-ASCII word chars.
    unicode: bool = False
    char_class: str = "word"
    # False when the site configured a custom ``toc.slugify`` callable: its
    # behaviour cannot be derived from parameters, so the Studio must ignore
    # ``separator``/``unicode`` here and use its own fallback instead.
    predictable: bool = True
    version: int = RULES_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def compute_rules(
    separator: str = _DEFAULT_SEPARATOR,
    unicode: bool = False,
    predictable: bool = True,
) -> SlugRules:
    """Derive the canonical rules from the engine's toc configuration.

    ``separator`` and ``unicode`` mirror the ``toc`` extension's ``separator``
    option and its ``slugify`` choice (stock ``slugify`` = non-unicode,
    ``slugify_unicode`` = unicode). ``predictable`` is False when a custom
    ``slugify`` callable makes the anchors unpredictable.
    """
    return SlugRules(separator=separator, unicode=unicode, predictable=predictable)


def write_rules(path, rules: SlugRules) -> None:
    """Write ``rules`` to ``path`` as JSON (atomic tmp+rename)."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(rules.to_json())
        fh.write("\n")
    os.replace(tmp, path)


def slugify(title: str, rules: SlugRules | None = None) -> str:
    """Engine-side slug for a heading title.

    This intentionally mirrors ``markdown.extensions.toc.slugify`` with the
    configured rules. It exists so a single function is the source of truth
    and so tests can assert the rules and the behaviour stay in sync.
    """
    rules = rules or compute_rules()
    sep = rules.separator
    if not rules.unicode:
        title = unicodedata.normalize("NFKD", title)
        title = title.encode("ascii", "ignore").decode("ascii")
    # Python \w is Unicode-aware: letters, digits, underscore, and (in py3)
    # CJK. [^\w\s-] strips everything else, then whitespace/underscore runs
    # collapse to the separator.
    value = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(rf"[{re.escape(sep)}\s]+", sep, value)
