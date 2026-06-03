from __future__ import annotations

import logging
import os

from docsforge import config_options as c

log = logging.getLogger(__name__)
base_path = os.path.dirname(os.path.abspath(__file__))


class LangOption(c.OptionallyRequired[list[str]]):
    """Validate Language(s) provided in config are known languages."""

    def get_lunr_supported_lang(self, lang):
        fallback = {'uk': 'ru'}
        for lang_part in lang.split("_"):
            lang_part = lang_part.lower()
            lang_part = fallback.get(lang_part, lang_part)
            if os.path.isfile(os.path.join(base_path, 'lunr-language', f'lunr.{lang_part}.js')):
                return lang_part
        return None

    def run_validation(self, value: object):
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise c.ValidationError('Expected a list of language codes.')
        for lang in value[:]:
            if lang != 'en':
                lang_detected = self.get_lunr_supported_lang(lang)
                if not lang_detected:
                    log.info(f"Option search.lang '{lang}' is not supported, falling back to 'en'")
                    value.remove(lang)
                    if 'en' not in value:
                        value.append('en')
                elif lang_detected != lang:
                    value.remove(lang)
                    value.append(lang_detected)
                    log.info(f"Option search.lang '{lang}' switched to '{lang_detected}'")
        return value
