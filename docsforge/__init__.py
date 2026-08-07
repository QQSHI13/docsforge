"""DocsForge - Unified documentation engine with Material theme.

DocsForge combines a vendored documentation build engine with the Material
for MkDocs theme and plugins into a single, cohesive package.
"""

from __future__ import annotations

from docsforge.utils import (
    clean_directory,
    copy_file,
    CountHandler,
    DuplicateFilter,
    get_build_date,
    get_build_datetime,
    get_markdown_title,
    get_relative_url,
    get_theme_dir,
    get_theme_names,
    get_themes,
    get_url_path,
    is_error_template,
    markdown_extensions,
    nest_paths,
    normalize_url,
    reduce_list,
    slugify,
    weak_property,
    write_file,
)

__version__ = "12.3.1"
__prog_name__ = "docsforge"
