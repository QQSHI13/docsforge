# Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""Social plugin - generate social cards for pages.

Flattened, vendored port of mkdocs-material's social plugin
(src/plugins/social/) into a single module, in the same style as
docsforge.core.tags and docsforge.core.blog. The card layout templates
(which upstream ships as separate YAML files) are embedded as module-level
strings, and the `on_files` layout-file exclusion is dropped, as there are
no layout files to exclude anymore. A custom `cards_layout_dir` may still be
used to override the embedded layouts.
"""

from __future__ import annotations

import functools
import html
import json
import logging
import os
import pickle
import posixpath
import re
import requests
import sys
import yaml

from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy
from fnmatch import fnmatch
from hashlib import sha1
from html import unescape
from io import BytesIO
from jinja2.sandbox import SandboxedEnvironment
from jinja2.meta import find_undeclared_variables
from statistics import stdev
from textwrap import dedent
from threading import Lock
from yaml import SafeLoader

from docsforge.config_base import Config
from docsforge.config_defaults import DocsForgeConfig
from docsforge.config_options import (
    Choice, Deprecated, DictOfItems, ListOfItems, SubConfig, Type
)
from docsforge.exceptions import PluginError
from docsforge.core.plugin_base import BasePlugin, event_priority
from docsforge.files import File
from docsforge.pages import Page
from docsforge.utils import write_file

try:
    from PIL import Image, ImageColor, ImageDraw, ImageFont
    from PIL.Image import Image as _Image
except ImportError as e:
    import_errors = {repr(e)}
else:
    import_errors = set()

cairosvg_error: str = ""
try:
    from cairosvg import svg2png
except ImportError as e:
    import_errors.add(repr(e))
except OSError as e:
    cairosvg_error = str(e)

# -----------------------------------------------------------------------------
# Layout templates (embedded)
# -----------------------------------------------------------------------------

# From social/templates/default.yml
_LAYOUT_DEFAULT = dedent("""\
    # Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to
    # deal in the Software without restriction, including without limitation the
    # rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    # sell copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    # IN THE SOFTWARE.

    # -----------------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------------

    # Definitions
    definitions:

      # Background image
      - &background_image >-
        {{ layout.background_image | x }}

      # Background color (default: indigo)
      - &background_color >-
        {%- if layout.background_color -%}
          {{ layout.background_color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ef5552",
            "pink":        "#e92063",
            "purple":      "#ab47bd",
            "deep-purple": "#7e56c2",
            "indigo":      "#4051b5",
            "blue":        "#2094f3",
            "light-blue":  "#02a6f2",
            "cyan":        "#00bdd6",
            "teal":        "#009485",
            "green":       "#4cae4f",
            "light-green": "#8bc34b",
            "lime":        "#cbdc38",
            "yellow":      "#ffec3d",
            "amber":       "#ffc105",
            "orange":      "#ffa724",
            "deep-orange": "#ff6e42",
            "brown":       "#795649",
            "grey":        "#757575",
            "blue-grey":   "#546d78",
            "black":       "#000000",
            "white":       "#ffffff"
          }[primary] or "#4051b5" }}
        {%- endif -%}

      # Text color (default: white)
      - &color >-
        {%- if layout.color -%}
          {{ layout.color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ffffff",
            "pink":        "#ffffff",
            "purple":      "#ffffff",
            "deep-purple": "#ffffff",
            "indigo":      "#ffffff",
            "blue":        "#ffffff",
            "light-blue":  "#ffffff",
            "cyan":        "#ffffff",
            "teal":        "#ffffff",
            "green":       "#ffffff",
            "light-green": "#ffffff",
            "lime":        "#000000",
            "yellow":      "#000000",
            "amber":       "#000000",
            "orange":      "#000000",
            "deep-orange": "#ffffff",
            "brown":       "#ffffff",
            "grey":        "#ffffff",
            "blue-grey":   "#ffffff",
            "black":       "#ffffff",
            "white":       "#000000"
          }[primary] or "#ffffff" }}
        {%- endif -%}

      # Font family (default: Roboto)
      - &font_family >-
        {%- if layout.font_family -%}
          {{ layout.font_family }}
        {%- elif config.theme.font is mapping -%}
          {{ config.theme.font.get("text", "Roboto") }}
        {%- else -%}
          Roboto
        {%- endif -%}

      # Font variant
      - &font_variant >-
        {%- if layout.font_variant -%}
          {{ layout.font_variant }}
        {%- endif -%}

      # Site name
      - &site_name >-
        {{ config.site_name }}

      # Page title
      - &page_title >-
        {%- if layout.title -%}
          {{ layout.title }}
        {%- else -%}
          {{ page.meta.get("title", page.title) }}
        {%- endif -%}

      # Page title with site name
      - &page_title_with_site_name >-
        {%- if not page.is_homepage -%}
          {{ page.meta.get("title", page.title) }} - {{ config.site_name }}
        {%- else -%}
          {{ config.site_name }}
        {%- endif -%}

      # Page description
      - &page_description >-
        {%- if layout.description -%}
          {{ layout.description }}
        {%- else -%}
          {{ page.meta.get("description", config.site_description) | x }}
        {%- endif -%}

      # Logo
      - &logo >-
        {%- if layout.logo -%}
          {{ layout.logo }}
        {%- elif config.theme.logo -%}
          {{ config.docs_dir }}/{{ config.theme.logo }}
        {%- endif -%}

      # Logo (icon)
      - &logo_icon >-
        {%- if not layout.logo and config.theme.icon -%}
          {{ config.theme.icon.logo | x }}
        {%- endif -%}

    # Meta tags
    tags:

      # Open Graph
      og:type: website
      og:title: *page_title_with_site_name
      og:description: *page_description
      og:image: "{{ image.url }}"
      og:image:type: "{{ image.type }}"
      og:image:width: "{{ image.width }}"
      og:image:height: "{{ image.height }}"
      og:url: "{{ page.canonical_url }}"

      # Twitter
      twitter:card: summary_large_image
      twitter:title: *page_title_with_site_name
      twitter:description: *page_description
      twitter:image: "{{ image.url }}"

    # -----------------------------------------------------------------------------
    # Specification
    # -----------------------------------------------------------------------------

    # Card size and layers
    size: { width: 1200, height: 630 }
    layers:

      # Background
      - background:
          image: *background_image
          color: *background_color

      # Logo
      - size: { width: 144, height: 144 }
        offset: { x: 992, y: 64 }
        background:
          image: *logo
        icon:
          value: *logo_icon
          color: *color

      # Site name
      - size: { width: 832, height: 42 }
        offset: { x: 64, y: 64 }
        typography:
          content: *site_name
          color: *color
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page title
      - size: { width: 832, height: 310 }
        offset: { x: 62, y: 160 }
        typography:
          content: *page_title
          align: start
          color: *color
          line:
            amount: 3
            height: 1.25
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page description
      - size: { width: 832, height: 64 }
        offset: { x: 64, y: 512 }
        typography:
          content: *page_description
          align: start
          color: *color
          line:
            amount: 2
            height: 1.5
          font:
            family: *font_family
            variant: *font_variant
            style: Regular
    """).strip()

# From social/templates/variant.yml
_LAYOUT_VARIANT = dedent("""\
    # Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to
    # deal in the Software without restriction, including without limitation the
    # rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    # sell copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    # IN THE SOFTWARE.

    # -----------------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------------

    # Definitions
    definitions:

      # Background image
      - &background_image >-
        {{ layout.background_image | x }}

      # Background color (default: indigo)
      - &background_color >-
        {%- if layout.background_color -%}
          {{ layout.background_color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ef5552",
            "pink":        "#e92063",
            "purple":      "#ab47bd",
            "deep-purple": "#7e56c2",
            "indigo":      "#4051b5",
            "blue":        "#2094f3",
            "light-blue":  "#02a6f2",
            "cyan":        "#00bdd6",
            "teal":        "#009485",
            "green":       "#4cae4f",
            "light-green": "#8bc34b",
            "lime":        "#cbdc38",
            "yellow":      "#ffec3d",
            "amber":       "#ffc105",
            "orange":      "#ffa724",
            "deep-orange": "#ff6e42",
            "brown":       "#795649",
            "grey":        "#757575",
            "blue-grey":   "#546d78",
            "black":       "#000000",
            "white":       "#ffffff"
          }[primary] or "#4051b5" }}
        {%- endif -%}

      # Text color (default: white)
      - &color >-
        {%- if layout.color -%}
          {{ layout.color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ffffff",
            "pink":        "#ffffff",
            "purple":      "#ffffff",
            "deep-purple": "#ffffff",
            "indigo":      "#ffffff",
            "blue":        "#ffffff",
            "light-blue":  "#ffffff",
            "cyan":        "#ffffff",
            "teal":        "#ffffff",
            "green":       "#ffffff",
            "light-green": "#ffffff",
            "lime":        "#000000",
            "yellow":      "#000000",
            "amber":       "#000000",
            "orange":      "#000000",
            "deep-orange": "#ffffff",
            "brown":       "#ffffff",
            "grey":        "#ffffff",
            "blue-grey":   "#ffffff",
            "black":       "#ffffff",
            "white":       "#000000"
          }[primary] or "#ffffff" }}
        {%- endif -%}

      # Font family (default: Roboto)
      - &font_family >-
        {%- if layout.font_family -%}
          {{ layout.font_family }}
        {%- elif config.theme.font is mapping -%}
          {{ config.theme.font.get("text", "Roboto") }}
        {%- else -%}
          Roboto
        {%- endif -%}

      # Font variant
      - &font_variant >-
        {%- if layout.font_variant -%}
          {{ layout.font_variant }}
        {%- endif -%}

      # Site name
      - &site_name >-
        {{ config.site_name }}

      # Page title
      - &page_title >-
        {%- if layout.title -%}
          {{ layout.title }}
        {%- else -%}
          {{ page.meta.get("title", page.title) }}
        {%- endif -%}

      # Page title with site name
      - &page_title_with_site_name >-
        {%- if not page.is_homepage -%}
          {{ page.meta.get("title", page.title) }} - {{ config.site_name }}
        {%- else -%}
          {{ config.site_name }}
        {%- endif -%}

      # Page description
      - &page_description >-
        {%- if layout.description -%}
          {{ layout.description }}
        {%- else -%}
          {{ page.meta.get("description", config.site_description) | x }}
        {%- endif -%}

      # Page icon
      - &page_icon >-
        {{ page.meta.icon | x }}

      # Logo
      - &logo >-
        {%- if layout.logo -%}
          {{ layout.logo }}
        {%- elif config.theme.logo -%}
          {{ config.docs_dir }}/{{ config.theme.logo }}
        {%- endif -%}

      # Logo (icon)
      - &logo_icon >-
        {%- if not layout.logo and config.theme.icon -%}
          {{ config.theme.icon.logo | x }}
        {%- endif -%}

    # Meta tags
    tags:

      # Open Graph
      og:type: website
      og:title: *page_title_with_site_name
      og:description: *page_description
      og:image: "{{ image.url }}"
      og:image:type: "{{ image.type }}"
      og:image:width: "{{ image.width }}"
      og:image:height: "{{ image.height }}"
      og:url: "{{ page.canonical_url }}"

      # Twitter
      twitter:card: summary_large_image
      twitter:title: *page_title_with_site_name
      twitter:description: *page_description
      twitter:image: "{{ image.url }}"

    # -----------------------------------------------------------------------------
    # Specification
    # -----------------------------------------------------------------------------

    # Card size and layers
    size: { width: 1200, height: 630 }
    layers:

      # Background
      - background:
          image: *background_image
          color: *background_color

      # Page icon
      - size: { width: 630, height: 630 }
        offset: { x: 800, y: 0 }
        icon:
          value: *page_icon
          color: "#00000033"

      # Logo
      - size: { width: 64, height: 64 }
        offset: { x: 64, y: 64 }
        background:
          image: *logo
        icon:
          value: *logo_icon
          color: *color

      # Site name
      - size: { width: 768, height: 42 }
        offset: { x: 160, y: 74 }
        typography:
          content: *site_name
          color: *color
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page title
      - size: { width: 864, height: 256 }
        offset: { x: 62, y: 192 }
        typography:
          content: *page_title
          align: start
          color: *color
          line:
            amount: 3
            height: 1.25
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page description
      - size: { width: 864, height: 64 }
        offset: { x: 64, y: 512 }
        typography:
          content: *page_description
          align: start
          color: *color
          line:
            amount: 2
            height: 1.5
          font:
            family: *font_family
            variant: *font_variant
            style: Regular
    """).strip()

# From social/templates/accent.yml
_LAYOUT_ACCENT = dedent("""\
    # Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to
    # deal in the Software without restriction, including without limitation the
    # rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    # sell copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    # IN THE SOFTWARE.

    # -----------------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------------

    # Definitions
    definitions:

      # Background image
      - &background_image >-
        {{ layout.background_image | x }}

      # Background color (default: indigo)
      - &background_color >-
        {%- if layout.background_color -%}
          {{ layout.background_color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("accent") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set accent = palette.get("accent", "indigo") -%}
          {%- set accent = accent.replace(" ", "-") -%}
          {{ {
            "red":         "#ff1a47",
            "pink":        "#f50056",
            "purple":      "#df41fb",
            "deep-purple": "#7c4dff",
            "indigo":      "#526cfe",
            "blue":        "#4287ff",
            "light-blue":  "#0091eb",
            "cyan":        "#00bad6",
            "teal":        "#00bda4",
            "green":       "#00c753",
            "light-green": "#63de17",
            "lime":        "#b0eb00",
            "yellow":      "#ffd500",
            "amber":       "#ffaa00",
            "orange":      "#ff9100",
            "deep-orange": "#ff6e42"
          }[accent] or "#4051b5" }}
        {%- endif -%}

      # Text color (default: white)
      - &color >-
        {%- if layout.color -%}
          {{ layout.color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("accent") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set accent = palette.get("accent", "indigo") -%}
          {%- set accent = accent.replace(" ", "-") -%}
          {{ {
            "red":         "#ffffff",
            "pink":        "#ffffff",
            "purple":      "#ffffff",
            "deep-purple": "#ffffff",
            "indigo":      "#ffffff",
            "blue":        "#ffffff",
            "light-blue":  "#ffffff",
            "cyan":        "#ffffff",
            "teal":        "#ffffff",
            "green":       "#ffffff",
            "light-green": "#ffffff",
            "lime":        "#000000",
            "yellow":      "#000000",
            "amber":       "#000000",
            "orange":      "#000000",
            "deep-orange": "#ffffff"
          }[accent] or "#ffffff" }}
        {%- endif -%}

      # Font family (default: Roboto)
      - &font_family >-
        {%- if layout.font_family -%}
          {{ layout.font_family }}
        {%- elif config.theme.font is mapping -%}
          {{ config.theme.font.get("text", "Roboto") }}
        {%- else -%}
          Roboto
        {%- endif -%}

      # Font variant
      - &font_variant >-
        {%- if layout.font_variant -%}
          {{ layout.font_variant }}
        {%- endif -%}

      # Site name
      - &site_name >-
        {{ config.site_name }}

      # Page title
      - &page_title >-
        {%- if layout.title -%}
          {{ layout.title }}
        {%- else -%}
          {{ page.meta.get("title", page.title) }}
        {%- endif -%}

      # Page title with site name
      - &page_title_with_site_name >-
        {%- if not page.is_homepage -%}
          {{ page.meta.get("title", page.title) }} - {{ config.site_name }}
        {%- else -%}
          {{ config.site_name }}
        {%- endif -%}

      # Page description
      - &page_description >-
        {%- if layout.description -%}
          {{ layout.description }}
        {%- else -%}
          {{ page.meta.get("description", config.site_description) | x }}
        {%- endif -%}

      # Logo
      - &logo >-
        {%- if layout.logo -%}
          {{ layout.logo }}
        {%- elif config.theme.logo -%}
          {{ config.docs_dir }}/{{ config.theme.logo }}
        {%- endif -%}

      # Logo (icon)
      - &logo_icon >-
        {%- if not layout.logo and config.theme.icon -%}
          {{ config.theme.icon.logo | x }}
        {%- endif -%}

    # Meta tags
    tags:

      # Open Graph
      og:type: website
      og:title: *page_title_with_site_name
      og:description: *page_description
      og:image: "{{ image.url }}"
      og:image:type: "{{ image.type }}"
      og:image:width: "{{ image.width }}"
      og:image:height: "{{ image.height }}"
      og:url: "{{ page.canonical_url }}"

      # Twitter
      twitter:card: summary_large_image
      twitter:title: *page_title_with_site_name
      twitter:description: *page_description
      twitter:image: "{{ image.url }}"

    # -----------------------------------------------------------------------------
    # Specification
    # -----------------------------------------------------------------------------

    # Card size and layers
    size: { width: 1200, height: 630 }
    layers:

      # Background
      - background:
          image: *background_image
          color: *background_color

      # Logo
      - size: { width: 144, height: 144 }
        offset: { x: 992, y: 64 }
        background:
          image: *logo
        icon:
          value: *logo_icon
          color: *color

      # Site name
      - size: { width: 832, height: 42 }
        offset: { x: 64, y: 64 }
        typography:
          content: *site_name
          color: *color
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page title
      - size: { width: 832, height: 310 }
        offset: { x: 62, y: 160 }
        typography:
          content: *page_title
          align: start
          color: *color
          line:
            amount: 3
            height: 1.25
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page description
      - size: { width: 832, height: 64 }
        offset: { x: 64, y: 512 }
        typography:
          content: *page_description
          align: start
          color: *color
          line:
            amount: 2
            height: 1.5
          font:
            family: *font_family
            variant: *font_variant
            style: Regular
    """).strip()

# From social/templates/invert.yml
_LAYOUT_INVERT = dedent("""\
    # Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to
    # deal in the Software without restriction, including without limitation the
    # rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    # sell copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    # IN THE SOFTWARE.

    # -----------------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------------

    # Definitions
    definitions:

      # Background image
      - &background_image >-
        {{ layout.background_image | x }}

      # Background color (default: white)
      - &background_color >-
        {%- if layout.background_color -%}
          {{ layout.background_color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ffffff",
            "pink":        "#ffffff",
            "purple":      "#ffffff",
            "deep-purple": "#ffffff",
            "indigo":      "#ffffff",
            "blue":        "#ffffff",
            "light-blue":  "#ffffff",
            "cyan":        "#ffffff",
            "teal":        "#ffffff",
            "green":       "#ffffff",
            "light-green": "#ffffff",
            "lime":        "#000000",
            "yellow":      "#000000",
            "amber":       "#000000",
            "orange":      "#000000",
            "deep-orange": "#ffffff",
            "brown":       "#ffffff",
            "grey":        "#ffffff",
            "blue-grey":   "#ffffff",
            "black":       "#ffffff",
            "white":       "#000000"
          }[primary] or "#ffffff" }}
        {%- endif -%}

      # Text color (default: indigo)
      - &color >-
        {%- if layout.color -%}
          {{ layout.color }}
        {%- else -%}
          {%- set palette = config.theme.palette or {} -%}
          {%- if not palette is mapping -%}
            {%- set list = palette | selectattr("primary") | list + palette -%}
            {%- set palette = list | first -%}
          {%- endif -%}
          {%- set primary = palette.get("primary", "indigo") -%}
          {%- set primary = primary.replace(" ", "-") -%}
          {{ {
            "red":         "#ef5552",
            "pink":        "#e92063",
            "purple":      "#ab47bd",
            "deep-purple": "#7e56c2",
            "indigo":      "#4051b5",
            "blue":        "#2094f3",
            "light-blue":  "#02a6f2",
            "cyan":        "#00bdd6",
            "teal":        "#009485",
            "green":       "#4cae4f",
            "light-green": "#8bc34b",
            "lime":        "#cbdc38",
            "yellow":      "#ffec3d",
            "amber":       "#ffc105",
            "orange":      "#ffa724",
            "deep-orange": "#ff6e42",
            "brown":       "#795649",
            "grey":        "#757575",
            "blue-grey":   "#546d78",
            "black":       "#000000",
            "white":       "#ffffff"
          }[primary] or "#4051b5" }}
        {%- endif -%}

      # Font family (default: Roboto)
      - &font_family >-
        {%- if layout.font_family -%}
          {{ layout.font_family }}
        {%- elif config.theme.font is mapping -%}
          {{ config.theme.font.get("text", "Roboto") }}
        {%- else -%}
          Roboto
        {%- endif -%}

      # Font variant
      - &font_variant >-
        {%- if layout.font_variant -%}
          {{ layout.font_variant }}
        {%- endif -%}

      # Site name
      - &site_name >-
        {{ config.site_name }}

      # Page title
      - &page_title >-
        {%- if layout.title -%}
          {{ layout.title }}
        {%- else -%}
          {{ page.meta.get("title", page.title) }}
        {%- endif -%}

      # Page title with site name
      - &page_title_with_site_name >-
        {%- if not page.is_homepage -%}
          {{ page.meta.get("title", page.title) }} - {{ config.site_name }}
        {%- else -%}
          {{ config.site_name }}
        {%- endif -%}

      # Page description
      - &page_description >-
        {%- if layout.description -%}
          {{ layout.description }}
        {%- else -%}
          {{ page.meta.get("description", config.site_description) | x }}
        {%- endif -%}

      # Logo
      - &logo >-
        {%- if layout.logo -%}
          {{ layout.logo }}
        {%- elif config.theme.logo -%}
          {{ config.docs_dir }}/{{ config.theme.logo }}
        {%- endif -%}

      # Logo (icon)
      - &logo_icon >-
        {%- if not layout.logo and config.theme.icon -%}
          {{ config.theme.icon.logo | x }}
        {%- endif -%}

    # Meta tags
    tags:

      # Open Graph
      og:type: website
      og:title: *page_title_with_site_name
      og:description: *page_description
      og:image: "{{ image.url }}"
      og:image:type: "{{ image.type }}"
      og:image:width: "{{ image.width }}"
      og:image:height: "{{ image.height }}"
      og:url: "{{ page.canonical_url }}"

      # Twitter
      twitter:card: summary_large_image
      twitter:title: *page_title_with_site_name
      twitter:description: *page_description
      twitter:image: "{{ image.url }}"

    # -----------------------------------------------------------------------------
    # Specification
    # -----------------------------------------------------------------------------

    # Card size and layers
    size: { width: 1200, height: 630 }
    layers:

      # Background
      - background:
          image: *background_image
          color: *background_color

      # Logo
      - size: { width: 144, height: 144 }
        offset: { x: 992, y: 64 }
        background:
          image: *logo
        icon:
          value: *logo_icon
          color: *color

      # Site name
      - size: { width: 832, height: 42 }
        offset: { x: 64, y: 64 }
        typography:
          content: *site_name
          color: *color
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page title
      - size: { width: 832, height: 310 }
        offset: { x: 62, y: 160 }
        typography:
          content: *page_title
          align: start
          color: *color
          line:
            amount: 3
            height: 1.25
          font:
            family: *font_family
            variant: *font_variant
            style: Bold

      # Page description
      - size: { width: 832, height: 64 }
        offset: { x: 64, y: 512 }
        typography:
          content: *page_description
          align: start
          color: *color
          line:
            amount: 2
            height: 1.5
          font:
            family: *font_family
            variant: *font_variant
            style: Regular
    """).strip()

# From social/templates/image.yml
_LAYOUT_IMAGE = dedent("""\
    # Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to
    # deal in the Software without restriction, including without limitation the
    # rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    # sell copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    # IN THE SOFTWARE.

    # -----------------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------------

    # Definitions
    definitions:

      # Background image
      - &background_image >-
        {{ layout.background_image }}

      # Page title with site name
      - &page_title_with_site_name >-
        {%- if not page.is_homepage -%}
          {{ page.meta.get("title", page.title) }} - {{ config.site_name }}
        {%- else -%}
          {{ page.meta.get("title", page.title) }}
        {%- endif -%}

      # Page description
      - &page_description >-
        {%- if layout.description -%}
          {{ layout.description }}
        {%- else -%}
          {{ page.meta.get("description", config.site_description) | x }}
        {%- endif -%}

    # Meta tags
    tags:

      # Open Graph
      og:type: website
      og:title: *page_title_with_site_name
      og:description: *page_description
      og:image: "{{ image.url }}"
      og:image:type: "{{ image.type }}"
      og:image:width: "{{ image.width }}"
      og:image:height: "{{ image.height }}"
      og:url: "{{ page.canonical_url }}"

      # Twitter
      twitter:card: summary_large_image
      twitter:title: *page_title_with_site_name
      twitter:description: *page_description
      twitter:image: "{{ image.url }}"

    # -----------------------------------------------------------------------------
    # Specification
    # -----------------------------------------------------------------------------

    # Card size and layers
    size: { width: 1200, height: 630 }
    layers:

      # Background
      - background:
          image: *background_image
    """).strip()

# Map of embedded layout templates
_LAYOUTS = {
    "default": _LAYOUT_DEFAULT,
    "variant": _LAYOUT_VARIANT,
    "accent":  _LAYOUT_ACCENT,
    "invert":  _LAYOUT_INVERT,
    "image":   _LAYOUT_IMAGE,
}

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# From social/templates/__init__.py - filter for coercing everything that is
# falsy to an empty string
def x_filter(value: str | None):
    return value or ""

# -----------------------------------------------------------------------------
# Classes (from social/layout.py)
# -----------------------------------------------------------------------------

# Options for origin
Origin = (
    "start top",        "center top",       "end top",
    "start center",     "center",           "end center",
    "start bottom",     "center bottom",    "end bottom",
    "start",                                "end"
)

# Options for overflow
Overflow = (
    "truncate",
    "shrink"
)

# Size
class Size(Config):
    width = Type(int, default = 0)
    height = Type(int, default = 0)

# Offset
class Offset(Config):
    x = Type(int, default = 0)
    y = Type(int, default = 0)

# Background
class Background(Config):
    color = Type(str, default = "")
    image = Type(str, default = "")

# Icon
class Icon(Config):
    value = Type(str, default = "")
    color = Type(str, default = "")

# Line
class Line(Config):
    amount = Type((int, float), default = 1)
    height = Type((int, float), default = 1)

# Font
class Font(Config):
    family = Type(str, default = "Roboto")
    variant = Type(str, default = "")
    style = Type(str, default = "Regular")

# Typography
class Typography(Config):
    content = Type(str, default = "")
    align = Choice(Origin, default = "start top")
    overflow = Choice(Overflow, default = "truncate")
    color = Type(str, default = "")
    line = SubConfig(Line)
    font = SubConfig(Font)

# Layer
class Layer(Config):
    size = SubConfig(Size)
    offset = SubConfig(Offset)
    origin = Choice(Origin, default = "start top")
    background = SubConfig(Background)
    icon = SubConfig(Icon)
    typography = SubConfig(Typography)

# Layout
class Layout(Config):
    definitions = ListOfItems(Type(str), default = [])
    tags = DictOfItems(Type(str), default = {})
    size = SubConfig(Size)
    layers = ListOfItems(SubConfig(Layer), default = [])

# Get layer or layout size as tuple
def get_size(layer: Layer | Layout):
    return layer.size.width, layer.size.height

# Get layer offset as tuple
def get_offset(layer: Layer, image: _Image):
    x, y = layer.offset.x, layer.offset.y

    # Compute offset from origin - if an origin is given, compute the offset
    # relative to the image and layer size to allow for flexible positioning
    if layer.origin != "start top":
        origin = re.split(r"\s+", layer.origin)

        # Get layer size
        w, h = get_size(layer)

        # Compute origin on x-axis
        if   "start"  in origin: pass
        elif "end"    in origin: x += (image.width  - w)  - 2 * x
        elif "center" in origin: x += (image.width  - w) >> 1

        # Compute origin on y-axis
        if   "top"    in origin: pass
        elif "bottom" in origin: y += (image.height - h)  - 2 * y
        elif "center" in origin: y += (image.height - h) >> 1

    # Return offset
    return x, y

# -----------------------------------------------------------------------------
# Classes (from social/config.py)
# -----------------------------------------------------------------------------

# Social plugin configuration
class SocialConfig(Config):
    enabled = Type(bool, default = True)
    concurrency = Type(int, default = max(1, os.cpu_count() - 1))

    # Settings for caching
    cache = Type(bool, default = True)
    cache_dir = Type(str, default = ".cache/plugin/social")

    # Settings for logging
    log = Type(bool, default = True)
    log_level = Type(str, default = "warn")

    # Settings for cards
    cards = Type(bool, default = True)
    cards_dir = Type(str, default = "assets/images/social")
    cards_layout_dir = Type(str, default = "layouts")
    cards_layout = Type(str, default = "default")
    cards_layout_options = Type(dict, default = {})
    cards_include = ListOfItems(Type(str), default = [])
    cards_exclude = ListOfItems(Type(str), default = [])

    # Settings for debugging
    debug = Type(bool, default = False)
    debug_on_build = Type(bool, default = False)
    debug_grid = Type(bool, default = True)
    debug_grid_step = Type(int, default = 32)
    debug_color = Type(str, default = "grey")

    # Deprecated settings
    cards_color = Deprecated(
        message =
            "Deprecated, use 'cards_layout_options.background_color' "
            "and 'cards_layout_options.color' with 'default' layout"
        )
    cards_font = Deprecated(
        message = "Deprecated, use 'cards_layout_options.font_family'"
    )

# -----------------------------------------------------------------------------
# Classes (from social/plugin.py)
# -----------------------------------------------------------------------------

# Social plugin
class SocialPlugin(BasePlugin[SocialConfig]):
    supports_multiple_instances = True

    # Manifest
    manifest: dict[str, str] = {}

    # Initialize plugin
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize incremental builds
        self.is_serve = False

    # Determine whether we're serving the site, and thus doing an incremental
    # build, and initialize two thread pools for card generation, because it's
    # split into two stages: rendering of layers and composition. We use two
    # thread pools, one for each stage, as we need to make sure that all layers
    # of a card are rendered before we compose the card itself. At the same time
    # we want to off-load as much as possible onto worker threads, as card
    # generation is a problem that can be perfectly solved in parallel. Thus,
    # we leverage the file system to cache the generated images, so we don't
    # re-generate the exact same images again and again, making successive
    # builds of large sites much faster.
    def on_startup(self, *, command, dirty):
        self.is_serve = command == "serve"

        # Initialize thread pool for cards
        self.card_pool = ThreadPoolExecutor(self.config.concurrency)
        self.card_pool_jobs: dict[str, Future] = {}

        # Initialize thread pool for card layers
        self.card_layer_pool = ThreadPoolExecutor(self.config.concurrency)
        self.card_layer_pool_jobs: dict[str, Future] = {}

    # Resolve and load manifest and initialize environment
    def on_config(self, config):
        if not self.config.enabled:
            return

        # Resolve cache directory (once) - this is necessary, so the cache is
        # always relative to the configuration file, and thus project, and not
        # relative to the current working directory, or it would not work with
        # the projects plugin.
        path = os.path.abspath(self.config.cache_dir)
        if path != self.config.cache_dir:
            self.config.cache_dir = os.path.join(
                os.path.dirname(config.config_file_path),
                os.path.normpath(self.config.cache_dir)
            )

            # Ensure cache directory exists
            os.makedirs(self.config.cache_dir, exist_ok = True)

        # Initialize manifest
        self.manifest_file = os.path.join(
            self.config.cache_dir, "manifest.json"
        )

        # Load manifest if it exists and the cache should be used
        if os.path.isfile(self.manifest_file) and self.config.cache:
            try:
                with open(self.manifest_file) as f:
                    self.manifest = json.load(f)
            except:
                pass

        # Initialize lock for synchronizing downloading of fonts
        self.lock = Lock()

        # Initialize card layouts and variables
        self.card_layouts: dict[str, Layout] = {}
        self.card_variables: dict[str, list[list[str]]] = {}

        # Initialize card environment
        self.card_env = SandboxedEnvironment()
        self.card_env.filters["x"] = x_filter

        # Always print a warning when debug mode is active
        if self.config.debug:
            log.warning("Debug mode is enabled for \"social\" plugin.")

            # By default, debug mode is disabled when the documentation is
            # built, but not when it is served, for a better user experience
            if not self.is_serve and not self.config.debug_on_build:
                self.config.debug = False

        # Check if site URL is defined
        if not config.site_url:
            log.warning(
                "The \"site_url\" option is not set. The cards are generated, "
                "but not linked, so they won't be visible on social media."
            )

        # Check if the required dependencies for rendering cards are available
        # and warn, so the author knows why no cards are generated - note that
        # card generation is skipped (and only fails if `log: false` is set)
        if import_errors:
            log.warning(
                "Required dependencies of \"social\" plugin not found:\n"
                + str("\n".join(map(lambda x: "- " + x, import_errors)))
                + "\n\n"
                + "--> Install with: pip install \"docsforge[social]\""
            )
        if cairosvg_error:
            log.warning(
                "\"cairosvg\" Python module is installed, but it crashed with:\n"
                + cairosvg_error
                + "\n\n"
                + "--> Check out the troubleshooting guide: https://t.ly/MfX6u"
            )

    # Generate card as soon as metadata is available (run latest) - run this
    # after all other plugins, so they can alter the card configuration
    @event_priority(-100)
    def on_page_markdown(self, markdown, *, page, config, files):
        if not self.config.enabled:
            return

        # Skip if cards should not be generated
        if self._is_excluded(page):
            return

        # Resolve card layout - we also preload the layout here, so we're not
        # triggering multiple concurrent loads in the worker threads
        name = self._config("cards_layout", page)
        self._resolve_layout(name, config)

        # Spawn concurrent job to generate card for page and add future to
        # job dictionary, as it returns the file we need to copy later
        self.card_pool_jobs[page.file.src_uri] = self.card_pool.submit(
            self._generate, name, page, config
        )

    # Generate card metadata (run earlier) - don't run this too late, as we
    # want plugins like the minify plugin to pick up the HTML we inject
    @event_priority(50)
    def on_post_page(self, output, *, page, config):
        if not self.config.enabled:
            return

        # Skip if cards should not be generated
        if self._is_excluded(page):
            return

        # Reconcile concurrent jobs - we need to wait for the card job to finish
        # before we can copy the generated files to the output directory. If an
        # exception occurred in one of the jobs, we either log it as configured
        # by the user, or raise it, so the build fails.
        future = self.card_pool_jobs[page.file.src_uri]
        if future.exception():
            e = future.exception()
            if self.config.log and isinstance(e, PluginError):
                level = logging.getLevelName(self.config.log_level.upper())
                if not isinstance(level, int):
                    level = logging.WARNING
                log.log(level, e)
                return

            # Otherwise throw error
            raise e
        else:
            file: File = future.result()
            file.copy_file()

        # Resolve card layout
        name = self._config("cards_layout", page)
        layout, _ = self._resolve_layout(name, config)

        # Stop if no tags are present or site URL is not set
        if not layout.tags or not config.site_url:
            return

        # Resolve image dimensions and curate image metadata
        width, height = get_size(layout)
        image = {
            "url": posixpath.join(config.site_url, file.url),
            "type": "image/png",
            "width": width,
            "height": height
        }

        # Find offset of closing head tag, so we can insert meta tags before
        # it - a bit hacky, but much faster than regular expressions
        at = output.find("</head>")
        return "\n".join([
            output[:at],
            "\n".join([
                f"<meta property=\"{property}\" content=\"{content}\" />"
                    for property, content in _replace(
                        layout.tags, self.card_env, config,
                        page = page, image = image,
                        layout = self._config("cards_layout_options", page),
                    ).items() if content
            ]),
            output[at:]
        ])

    # Save manifest after build
    def on_post_build(self, *, config):
        if not self.config.enabled:
            return

        # Save manifest if cache should be used
        if self.config.cache:
            with open(self.manifest_file, "w") as f:
                f.write(json.dumps(self.manifest, indent = 2, sort_keys = True))

    # Add custom layout directory to watched files
    def on_serve(self, server, *, config, builder):
        path = os.path.abspath(self.config.cards_layout_dir)
        if os.path.isdir(path):
            server.watch(path, recursive = True)

    # Reconcile jobs (run latest) - all other plugins do not depend on the
    # generated cards, so we can run this after all of them
    @event_priority(-100)
    def on_shutdown(self):
        if not self.config.enabled:
            return

        # Shutdown thread pools - if we're on Python 3.9 and above, cancel all
        # pending futures that have not yet been scheduled
        for pool in [self.card_layer_pool, self.card_pool]:
            if sys.version_info >= (3, 9):
                pool.shutdown(cancel_futures = True)
            else:
                pool.shutdown()

        # Save manifest if cache should be used
        if self.manifest and self.config.cache:
            with open(self.manifest_file, "w") as f:
                f.write(json.dumps(self.manifest, indent = 2, sort_keys = True))

    # -------------------------------------------------------------------------

    # Check if the given page is excluded - giving the author the option to
    # include and exclude specific pages is important, as it allows to control
    # which pages should generate social cards, and which shouldn't. Different
    # cards can be built by using multiple instances of the plugin.
    def _is_excluded(self, page: Page):
        path = page.file.src_path

        # Check if card generation is disabled for the given page
        if not self._config("cards", page):
            return True

        # Check if page matches one of the inclusion patterns
        if self.config.cards_include:
            for pattern in self.config.cards_include:
                if fnmatch(page.file.src_uri, pattern):
                    return False

            # Page is not included
            log.debug(f"Excluding page '{path}' due to inclusion patterns")
            return True

        # Check if page matches one of the exclusion patterns
        for pattern in self.config.cards_exclude:
            if fnmatch(page.file.src_uri, pattern):
                log.debug(f"Excluding page '{path}' due to exclusion patterns")
                return True

        # Page is not excluded
        return False

    # -------------------------------------------------------------------------

    # Generate card for the given page - generation of cards does not depend on
    # anything else than the page content (incl. metadata) and configuration,
    # which is why it is an embarrassingly parallel problem and can be solved
    # by delegating the generation of each card to a thread pool
    def _generate(self, name: str, page: Page, config: DocsForgeConfig):
        layout, variables = self._resolve_layout(name, config)

        # Each card can consist of multiple layers, many of which are likely
        # the same across cards (like background or logo layers). Some of the
        # input values to generate a card may be dependent on author-provided
        # data, e.g., the site description or card title that is sourced from
        # front matter. Additionally, layouts may allow to define arbitrary
        # text boxes with author-provided metadata like tags or categories.
        # Thus, we generate a hash for each card, which is based on the layers
        # and the values of all variables that are used to generate the card.
        layers: dict[str, Layer] = {}
        for layer, templates in zip(layout.layers, variables):
            fingerprints = [self.config, layer]

            # Compute fingerprints for each layer
            for template in templates:
                template = _compile(template, self.card_env)
                fingerprints.append(template.render(
                    config = config, page = page,
                    layout = self._config("cards_layout_options", page)
                ))

            # Compute digest of fingerprints
            layers[_digest(fingerprints)] = layer

        # Compute digest of all fingerprints - we use this value to check if
        # the exact same card was already generated and cached
        hash = _digest([layout, *list(layers)])

        # Determine part of path we need to replace - this depends on whether
        # we're using directory URLs and if the page is an index page or not
        suffix = ".html"
        if config.use_directory_urls and not page.is_index:
            suffix = "/index.html"

        # Compute path to card, which is sourced from the cache directory, and
        # generate file to register it with MkDocs as soon as it was generated.
        # If the suffix does not match - e.g. for alternate-language pages
        # like 'index.zh.html' created by the i18n plugin - we replace the
        # file extension instead, so alternate pages get their own card.
        path = page.file.dest_uri.replace(suffix, ".png")
        if not path.endswith(".png"):
            path = posixpath.splitext(path)[0] + ".png"
        file = self._path_to_file(path, config)

        # Check if file hash changed, so we need to re-generate the card - if
        # the hash didn't change, we can just return the existing file
        prev = self.manifest.get(file.url, "")
        if hash == prev and os.path.isfile(file.abs_src_path):
            return file

        # Check if the required dependencies for rendering are available, which
        # is, at the absolute minimum, the 'pillow' package, and raise an error
        # to the caller, so he can decide what to do with the error. The caller
        # can treat this as a warning or an error to abort the build.
        if import_errors:
            raise PluginError(
                "Required dependencies of \"social\" plugin not found:\n"
                + str("\n".join(map(lambda x: "- " + x, import_errors)))
                + "\n\n"
                + "--> Install with: pip install \"docsforge[social]\""
            )
        if cairosvg_error:
            raise PluginError(
                "\"cairosvg\" Python module is installed, but it crashed with:\n"
                + cairosvg_error
                + "\n\n"
                + "--> Check out the troubleshooting guide: https://t.ly/MfX6u"
            )

        # Spawn concurrent jobs to render layers - we only need to render layers
        # that we haven't already dispatched, reducing work by deduplication
        for h, layer in layers.items():
            sentinel = Future()

            # We need to use a hack here to avoid locking the thread pool while
            # we check if the layer was already dispatched. If we don't do this,
            # layers might be dispatched multiple times. The trick is to use a
            # sentinel value to check if the layer was already dispatched.
            if sentinel == self.card_layer_pool_jobs.setdefault(h, sentinel):
                self.card_layer_pool_jobs[h] = self.card_layer_pool.submit(
                    self._render, layer, page, config
                )

        # Reconcile concurrent jobs to render layers and compose card - since
        # layers are rendered in parallel, we can compose the card as soon as
        # all layers have been rendered. For this, we await each future to
        # resolve with the image of the rendered layer.
        image = Image.new(mode = "RGBA", size = get_size(layout))
        for h, layer in layers.items():
            image.alpha_composite(
                self.card_layer_pool_jobs[h].result(),
                get_offset(layer, image)
            )

        # If debug mode is enabled, render overlay
        if self.config.debug:
            image = self._render_overlay(layout, image)

        # Save composed image to cache - the caller must copy the image from
        # the cache, so we don't need to worry about concurrent access
        os.makedirs(os.path.dirname(file.abs_src_path), exist_ok = True)
        image.save(file.abs_src_path)

        # Update manifest by associating file with hash
        self.manifest[file.url] = hash

        # Return file for generated card
        return file

    # Render layer - this is the core of the plugin, which renders a single
    # layer of a card. Order is: background, icon, and typography.
    def _render(self, layer: Layer, page: Page, config: DocsForgeConfig):
        image = Image.new(mode = "RGBA", size = get_size(layer))
        layer = _replace(
            layer, self.card_env, config,
            page = page, layout = self._config("cards_layout_options", page)
        )

        # Render background, icon, and typography
        image = self._render_background(layer, image)
        image = self._render_icon(layer, image, config)
        image = self._render_typography(layer, image)

        # Return image with layer
        return image

    # Render layer background
    def _render_background(self, layer: Layer, input: _Image):
        background = layer.background

        # If given, load background image and resize it proportionally to cover
        # the entire area while retaining the aspect ratio of the input image
        if background.image:
            if not os.path.isfile(background.image):
                raise PluginError(f"Couldn't find image '{background.image}'")

            # Open file and convert SVGs to PNGs
            with open(background.image, "rb") as f:
                data = f.read()
                if background.image.endswith(".svg"):
                    data = svg2png(data, output_width = input.width)

            # Resize image to cover entire area
            image = Image.open(BytesIO(data)).convert("RGBA")
            input.alpha_composite(_resize_cover(image, input))

        # If given, fill background color - this is done after the image is
        # loaded to allow for transparent tints. How awesome is that?
        if background.color:
            color = background.color
            if color == "transparent":
                return input

            # Create image filled with background color
            image = Image.new(mode = "RGBA", size = input.size, color = color)
            input.alpha_composite(image)

        # Return image with background
        return input

    # Render layer icon
    def _render_icon(self, layer: Layer, input: _Image, config: DocsForgeConfig):
        icon = layer.icon
        if not icon.value:
            return input

        # Resolve icon by searching all configured theme directories and apply
        # the fill color before rendering, if given. Note that the fill color
        # must be converted to rgba() function syntax, or opacity will not work
        # correctly. This way, we don't need to use the fill-opacity property.
        data = self._resolve_icon(icon.value, config)
        if icon.color:
            (r, g, b, *a) = ImageColor.getrgb(icon.color)
            opacity = a[0] / 255 if a else 1

            # Compute and replace fill color
            fill = f"rgba({r}, {g}, {b}, {opacity})"
            data = data.replace("<svg", f"<svg fill=\"{fill}\"")

        # Rasterize vector image given by icon to match the size of the
        # input image, resize it and render it on top of the input image
        image = Image.open(BytesIO(
            svg2png(data.encode("utf-8"), output_width = input.width)
        ))
        input.alpha_composite(_resize_contain(image.convert("RGBA"), input))

        # Return image with icon
        return input

    # Render layer typography
    def _render_typography(self, layer: Layer, input: _Image):
        typography = layer.typography
        if not typography.content:
            return input

        # Retrieve font family and font style
        family = typography.font.family
        variant = typography.font.variant
        style = typography.font.style

        # Resolve and load font and compute metrics
        path = self._resolve_font(family, style, variant)
        current, spacing = _metrics(path, typography.line, input)
        font = ImageFont.truetype(path, current)

        # Create image and initialize drawing context
        image = Image.new(mode = "RGBA", size = input.size)
        context = ImageDraw.Draw(image)

        # Compute length of whitespace and ellipsis - in the next step, we will
        # distribute the words across the lines we have available, which means
        # we need to compute the length of each word and intersperse it with
        # whitespace. Note that lengths of words are perfectly additive, so we
        # can compute the length of a line by adding the lengths of all words
        # and the whitespace between them.
        space = context.textlength(" ", font = font)
        ellipsis = context.textlength("...", font = font)

        # Initialize lists to hold the lengths of words and indexes of lines.
        # Tracking line indexes allows us to improve splitting using heuristics.
        lengths: list[int] = []
        indexes, current = [0], 0

        # Split words at whitespace, and successively add words to the current
        # line. For every other than the first word, account for the whitespace
        # between words. If the next word would exceed the width of the input
        # image, and thus overflow the line, start a new one.
        words = re.split(r"\s+", unescape(typography.content))
        for word in words:
            length = context.textlength(word, font = font)
            lengths.append(length)

            # Start new line if current line overflows
            whitespace = space if current else 0
            if current + whitespace + length > input.width:
                indexes.append(len(lengths) - 1)
                current = length

            # Add word to current line
            else:
                current += whitespace + length

        # Add terminating index, if not already present
        if len(lengths) != indexes[-1]:
            indexes.append(len(lengths))

        # If the number of lines exceeds the maximum amount we are able to
        # render, either shrink or truncate the text and add an ellipsis
        amount = typography.line.amount
        if amount < len(indexes) - 1:

            # If overflow mode is set to 'shrink', decrease the font size and
            # try to render the typography again to see if it fits
            overflow = typography.overflow
            if overflow == "shrink":
                typography.line.amount += 1

                # Render layer with new typography metrics by calling this
                # function recursively and returning immediately from it
                return self._render_typography(layer, input)

            # Determine last and penultimate line indexes
            indexes = indexes[:amount + 1]
            p, q = indexes[-2:]

            # Compute the length of the last line, and check whether we can add
            # the ellipsis after the last word. If not, replace the last word.
            current = sum(lengths[p:q]) + (q - p) * space
            if current + ellipsis < input.width:
                q += 1

            # Update line indexes and replace word with ellipsis
            indexes[-1]  = q
            words[q - 1] = "..."

        # If there are exactly two lines, check if we can improve splitting by
        # moving the last word of the first line to the last line
        elif len(indexes) == 3:
            p, q, r = indexes[-3:]

            # Create two configurations of lines, one with the last word of the
            # first line moved to the last line, and one without the change
            a = [len(" ".join(l)) for l in [words[p:q],     words[q:r]]]
            b = [len(" ".join(l)) for l in [words[p:q - 1], words[q - 1:r]]]

            # Compute standard deviation of line lengths before and after the
            # change, and if the standard deviation decreases, move the word
            if stdev(b) < stdev(a):
                indexes[-2] -= 1

        # Compute anchor and deduce alignment, as well as offset. The anchor
        # is computed as a string of two characters, where the first character
        # denotes the horizontal alignment and the second character denotes
        # the vertical alignment.
        anchor = _anchor(typography.align)

        # Compute horizontal alignment
        if   anchor[0] == "l": align, x = "left",   0
        elif anchor[0] == "m": align, x = "center", input.width  >> 1
        else:                  align, x = "right",  input.width  >> 0

        # Compute vertical alignment
        if   anchor[1] == "a":        y =           0
        elif anchor[1] == "m":        y =           input.height >> 1
        else:                         y =           input.height >> 0

        # Join words with whitespace and lines with line breaks
        text = "\n".join([
            " ".join(words[p:q])
                for p, q in zip(indexes, indexes[1:])
        ])

        # Draw text onto image
        context.text(
            (x, y), text,
            font = font,
            anchor = anchor,
            spacing = spacing,
            fill = typography.color,
            align = align
        )

        # Return image with typography
        input.alpha_composite(image)
        return input

    # Render overlay for debugging
    def _render_overlay(self, layout: Layout, input: _Image):
        path = self._resolve_font("Roboto", "Regular")
        font = ImageFont.truetype(path, 12)

        # Create image and initialize drawing context
        image = Image.new(mode = "RGBA", size = input.size)
        context = ImageDraw.Draw(image)

        # Draw overlay grid
        fill = self.config.debug_color
        if self.config.debug_grid:
            step = self.config.debug_grid_step
            for i in range(0, input.width, step):
                for j in range(0, input.height, step):
                    context.ellipse(
                        ((i - 1, j - 1), (i + 1, j + 1)),
                        fill = fill
                    )

        # Compute luminosity of debug color and use it to determine the color
        # of the text that will be drawn on top of the debug color
        (r, g, b, *_) = ImageColor.getrgb(fill)
        color = "black" if r * 0.299 + g * 0.587 + b * 0.114 > 150 else "white"

        # Draw overlay outline for each layer
        for i, layer in enumerate(layout.layers):
            x, y = get_offset(layer, image)
            w, h = get_size(layer)

            # Draw overlay outline
            context.rectangle(outline = fill, xy = (x, y,
                min(x + w, input.width  - 1),
                min(y + h, input.height - 1)
            ))

            # Assemble text and compute its width and height - we only use the
            # coordinates denoting the width and height of the text, as we need
            # to compute the coordinates of the text box manually in order to
            # have the rectangle align perfectly with the outline
            text = f"{i} – {x}, {y}"
            (_, _, x1, y1) = context.textbbox((x, y), text, font = font)

            # Draw text on a small rectangle in the top left corner of the
            # layer denoting the number of the layer and its offset
            context.rectangle(fill = fill, xy = (x, y, x1 + 8, y1 + 4))
            context.text((x + 4, y + 2), text, font = font, fill = color)

        # Return image with overlay
        input.alpha_composite(image)
        return input

    # -------------------------------------------------------------------------

    # Resolve layout - authors can specify a custom directory for layouts in
    # the configuration, which is checked prior to the layouts embedded in this
    # module. If the layout cannot be resolved in any of the known locations,
    # the plugin must abort with an error.
    def _resolve_layout(self, name: str, config: DocsForgeConfig):
        name, _ = os.path.splitext(name)
        if name in self.card_layouts:
            return self.card_layouts[name], self.card_variables[name]

        # If the author specified a custom directory, try to resolve the layout
        # from this directory first, otherwise fall back to the embedded ones
        source, path, data = None, "", None
        if os.path.isdir(self.config.cards_layout_dir):
            path = os.path.normpath(
                os.path.join(self.config.cards_layout_dir, f"{name}.yml")
            )
            if os.path.isfile(path):
                source = self.config.cards_layout_dir
                with open(path, encoding = "utf-8-sig") as f:
                    data = f.read()

        # Fall back to the layout embedded in this module
        if data is None:
            data = _LAYOUTS.get(name)
            source, path = "module", f"{name}.yml"

        # Abort if the layout could not be resolved
        if data is None:
            raise PluginError(f"Couldn't find layout '{name}'")

        # Open file and parse as YAML
        layout: Layout = Layout(config_file_path = path)
        try:
            layout.load_dict(yaml.load(data, SafeLoader) or {})

        # The layout could not be loaded because of a syntax error, which we
        # display to the author with a nice error message
        except Exception as e:
            raise PluginError(
                f"Error reading layout file '{path}' in '{source}':\n"
                f"{e}"
            )

        # Validate layout and abort if errors occurred
        errors, warnings = layout.validate()
        for _, w in warnings:
            log.warning(w)
        for _, e in errors:
            raise PluginError(
                f"Error reading layout file '{path}' in '{source}':\n"
                f"{e}"
            )

        # Store layout and variables
        self.card_layouts[name] = layout
        self.card_variables[name] = []

        # Extract variables for each layer from layout
        for layer in layout.layers:
            variables = _extract(layer, self.card_env, config)
            self.card_variables[name].append(variables)

            # Set default values for for layer size, if not given
            for key, value in layer.size.items():
                if value == 0:
                    layer.size[key] = layout.size[key]

        # Return layout and variables
        return self.card_layouts[name], self.card_variables[name]

    # Resolve icon with given name - this function searches for the icon in all
    # known theme directories, including custom directories specified by the
    # author, which allows for using custom icons in cards. If the icon cannot
    # be resolved, the plugin must abort with an error.
    def _resolve_icon(self, name: str, config: DocsForgeConfig):
        for base in config.theme.dirs:
            path = os.path.join(base, ".icons", f"{name}.svg")
            path = os.path.normpath(path)

            # Skip if icon does not exist and try next directory
            if not os.path.isfile(path):
                continue

            # Open and return icon
            with open(path, encoding = "utf-8") as f:
                return f.read()

        # Abort if the icon could not be resolved
        raise PluginError(f"Couldn't find icon '{name}'")

    # Resolve font family with specific style - if we haven't already done it,
    # the font family is first downloaded from Google Fonts and the styles are
    # saved to the cache directory. If the font cannot be resolved, the plugin
    # must abort with an error.
    def _resolve_font(self, family: str, style: str, variant = ""):
        path = os.path.join(self.config.cache_dir, "fonts", family)

        # Fetch font family, if it hasn't been fetched yet - we use a lock to
        # synchronize access, so the font is not downloaded multiple times, but
        # all other threads wait for the font being available. This is also why
        # we need the double path check, which makes sure that we only use the
        # lock when we actually need to download a font that doesn't exist. If
        # we already downloaded it, we don't want to block at all.
        if not os.path.isdir(path):
            with self.lock:
                if not os.path.isdir(path):
                    self._fetch_font_from_google_fonts(family)

        # Assemble fully qualified style - see https://t.ly/soDF0
        if variant:
            style = f"{variant} {style}"

        # Check for availability of font style
        list = sorted(os.listdir(path))
        for file in list:
            name, _ = os.path.splitext(file)
            if name == style:
                return os.path.join(path, file)

        # Find regular variant of font family - we cannot rely on the fact that
        # fonts always have a single regular variant - some of them have several
        # of them, potentially prefixed with "Condensed" etc. For this reason we
        # use the first font we find if we find no regular one.
        fallback = ""
        for file in list:
            name, _ = os.path.splitext(file)

            # 1. Fallback: use first font
            if not fallback:
                fallback = name

            # 2. Fallback: use regular font - use the shortest one, i.e., prefer
            # "10pt Regular" over "10pt Condensed Regular". This is a heuristic.
            if "Regular" in name:
                if not fallback or len(name) < len(fallback):
                    fallback = name

        # Fall back to regular font (guess if there are multiple)
        return self._resolve_font(family, fallback)

    # -------------------------------------------------------------------------

    # Fetch font family from Google Fonts
    def _fetch_font_from_google_fonts(self, family: str):
        path = os.path.join(self.config.cache_dir, "fonts")

        # Download manifest from Google Fonts - Google returns JSON with syntax
        # errors, so we just treat the response as plain text and parse out all
        # URLs to font files, as we're going to rename them anyway. This should
        # be more resilient than trying to correct the JSON syntax.
        url = f"https://fonts.google.com/download/list?family={family}"
        res = requests.get(url)

        # Ensure that the download succeeded
        if res.status_code != 200:
            raise PluginError(
                f"Couldn't find font family '{family}' on Google Fonts "
                f"({res.status_code}: {res.reason})"
            )

        # Extract font URLs from manifest
        for match in re.findall(
            r"\"(https:(?:.*?)\.[ot]tf)\"", str(res.content)
        ):
            with requests.get(match) as res:
                res.raise_for_status()

                # Construct image font for analysis by directly reading the
                # contents from the response without priorily writing to a
                # temporary file (like we did before), as this might lead to
                # problems on Windows machines, see https://t.ly/LiF_k
                with BytesIO(res.content) as f:
                    font = ImageFont.truetype(f)

                # Extract font family name and style
                name, style = font.getname()
                name = " ".join([name.replace(family, ""), style]).strip()

                # Write file to cache directory
                target = os.path.join(path, family, f"{name}.ttf")
                write_file(res.content, target)

    # -------------------------------------------------------------------------

    # Retrieve configuration value - each page can override certain parts of
    # the site configuration, depending on the type and structure of the value
    def _config(self, name: str, page: Page):
        meta = page.meta.get("social", {})

        # Primitive values: choose page- over site-level configuration
        if isinstance(self.config[name], (bool, str, int, float)):
            return meta.get(name, self.config[name])

        # Dictionary values: merge site- with page-level configuration
        if isinstance(self.config[name], (dict)):
            return { **self.config[name], **meta.get(name, {}) }

    # Create a file for the given path
    def _path_to_file(self, path: str, config: DocsForgeConfig):
        assert path.endswith(".png")
        return File(
            posixpath.join(self.config.cards_dir, path),
            self.config.cache_dir,
            config.site_dir,
            False
        )

# -----------------------------------------------------------------------------
# Helper functions (from social/plugin.py)
# -----------------------------------------------------------------------------

# Compute a stable hash from an object - since we're doing compositing, we can
# leverage caching to omit re-generating layers when their parameters stay the
# same. Additionally, we can identify identical layers between images, e.g.,
# background, logos, or avatars, but also unchanged text. Note that we need to
# convert the data to a string prior to hashing, because configuration objects
# are inherently unstable, always resulting in new hashes.
def _digest(data: object):
    return sha1(pickle.dumps(str(data))).hexdigest()

# -----------------------------------------------------------------------------

# Extract all variables recursively
def _extract(data: any, env: SandboxedEnvironment, config: DocsForgeConfig):

    # Traverse configuration or dictionary
    if isinstance(data, (Config, dict)):
        return [
            variable for value in data.values()
                for variable in _extract(value, env, config)
        ]

    # Traverse list
    elif isinstance(data, list):
        return [
            variable for value in data
                for variable in _extract(value, env, config)
        ]

    # Retrieve variables from string
    elif isinstance(data, str):
        if find_undeclared_variables(env.parse(data)):
            return [data]

    # Return nothing
    return []

# Replace all variables recursively and return a copy of the given data
def _replace(
    data: any, env: SandboxedEnvironment, config: DocsForgeConfig, **kwargs
):

    # Traverse configuration or dictionary
    if isinstance(data, (Config, dict)):
        data = copy(data)
        for key, value in data.items():
            data[key] = _replace(value, env, config, **kwargs)

    # Traverse list
    elif isinstance(data, list):
        return [
            _replace(value, env, config, **kwargs)
                for value in data
        ]

    # Retrieve variables from string
    elif isinstance(data, str):
        return _compile(data, env).render(
            config = config, **kwargs
        ) or None

    # Return data
    return data

# Compile template and cache it indefinitely
@functools.lru_cache(maxsize = None)
def _compile(data: str, env: SandboxedEnvironment):
    return env.from_string(html.unescape(data))

# -----------------------------------------------------------------------------

# Resize image to match the size of the reference image and align it to the
# center of the reference image so that it is fully covered
def _resize_cover(image: _Image, ref: _Image):
    ratio = max(
        ref.width  / image.width,
        ref.height / image.height
    )

    # Compute aspect ratios of both images and choose the larger one, then
    # resize the image so that it covers the entire reference image
    image = image.resize((
        int(image.width  * ratio),
        int(image.height * ratio)
    ))

    # Align image to the center of the reference image - we also need to crop
    # the image if it's larger than the given reference image
    return image.crop((
        image.width  - ref.width  >> 1,
        image.height - ref.height >> 1,
        image.width  + ref.width  >> 1,
        image.height + ref.height >> 1
    ))

# Resize image to match the size of the reference image and align it to the
# center of the reference image so that it is fully contained
def _resize_contain(image: _Image, ref: _Image):
    ratio = min(
        ref.width  / image.width,
        ref.height / image.height
    )

    # Resize image according to minimum ratio
    image = image.resize((
        int(image.width  * ratio),
        int(image.height * ratio)
    ))

    # Create a blank image and paste the resized image into it
    blank = Image.new(mode = "RGBA", size = ref.size)
    blank.paste(image, (
        ref.width  - image.width  >> 1,
        ref.height - image.height >> 1
    ))

    # Return resized image
    return blank

# -----------------------------------------------------------------------------

# Resolve font metrics for given truetype font - this function computes the
# font size and spacing between lines based on the number of lines and height.
# In order to omit rounding errors, we compute the ascender and descender based
# on a font size of 1,000.
def _metrics(path: str, line: Line, ref: _Image):
    font = ImageFont.truetype(path, 1000)
    ascender, descender = font.getmetrics()

    # It would be too complex to let the author define the font size, since this
    # would involve a lot of fiddling to find the right value. Instead, we let
    # the author define the number of lines and the line height, and we compute
    # the font size from that. This is much more intuitive. As a basis, we use
    # the ascender as the actual line height and also add the descender to
    # account for the last line. It's no secret that correctly handling font
    # metrics is super tricky - see https://bit.ly/31u9bh6
    extent = line.amount * ascender + 1 * descender

    # Now, we still need to account for spacing between lines, which is why we
    # take the number of lines - 1, and multiply that with the line height we
    # computed from the ascender. We add this to the extent we computed before,
    # which we use as a basis for the final font size.
    extent += (line.amount - 1) * (line.height - 1) * ascender
    size = (1000 * ref.height) / extent

    # From this, we can compute the spacing between lines, and we're done. We
    # then return both, the font size and spacing between lines.
    spacing = (line.height - 1) * ascender * size / 1000
    return int(size), spacing

# Compute anchor, determining the alignment of text relative to the given
# coordinates, with the default being "top left" - see https://bit.ly/3NEfr07
def _anchor(data: str):
    axis = re.split(r"\s+", data)

    # Determine anchor on x-axis
    if   "start"  in axis: anchor  = "l"
    elif "end"    in axis: anchor  = "r"
    elif "center" in axis: anchor  = "m"
    else:                  anchor  = "l"

    # Determine anchor on y-axis
    if   "top"    in axis: anchor += "a"
    elif "bottom" in axis: anchor += "d"
    elif "center" in axis: anchor += "m"
    else:                  anchor += "a"

    # Return anchor
    return anchor

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs.material.social")
