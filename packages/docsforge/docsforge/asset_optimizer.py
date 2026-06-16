import logging
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, urljoin

log = logging.getLogger(__name__)


def _find_referenced_assets(site_dir: str) -> set[str]:
    """Scan all HTML and CSS files in site_dir for referenced assets.
    
    Returns a set of relative paths (from site_dir) of referenced assets.
    """
    referenced = set()
    site_path = Path(site_dir)
    
    # Patterns to match asset references in HTML/CSS
    patterns = [
        # CSS links
        r'<link[^>]+href=["\']([^"\']+)["\']',
        # JS scripts
        r'<script[^>]+src=["\']([^"\']+)["\']',
        # Images
        r'<img[^>]+src=["\']([^"\']+)["\']',
        # SVG images
        r'<image[^>]+href=["\']([^"\']+)["\']',
        # CSS url() references
        r'url\(["\']?([^"\')\s]+)["\']?\)',
        # Video/audio sources
        r'<(?:video|audio)[^>]+src=["\']([^"\']+)["\']',
        # Source tags
        r'<source[^>]+src=["\']([^"\']+)["\']',
        # Data attributes that might reference files
        r'data-[a-z-]+=["\']([^"\']+\.(?:css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|otf))["\']',
    ]
    
    # Scan all HTML and CSS files
    for ext in ('.html', '.css', '.js'):
        for file_path in site_path.rglob(f'*{ext}'):
            if not file_path.is_file():
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            
            # Get relative directory of this file for resolving relative URLs
            file_dir = file_path.parent.relative_to(site_path)
            file_dir_str = str(file_dir).replace('\\', '/') if str(file_dir) != '.' else ''
            
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    url = match.group(1)
                    
                    # Skip external URLs, anchors, and data URIs
                    if url.startswith(('http://', 'https://', '//', 'data:', 'mailto:', 'tel:')):
                        continue
                    if url.startswith('#'):
                        continue
                    
                    # Normalize the URL
                    url = url.split('?')[0].split('#')[0]  # Remove query strings and fragments
                    
                    if not url:
                        continue
                    
                    # Resolve relative URL to absolute path from site_dir
                    if url.startswith('/'):
                        # Absolute from site root
                        rel_path = url.lstrip('/')
                    else:
                        # Relative to current file
                        if file_dir_str:
                            rel_path = f"{file_dir_str}/{url}"
                        else:
                            rel_path = url
                    
                    # Normalize path (resolve ../ and ./)
                    try:
                        rel_path = os.path.normpath(rel_path).replace('\\', '/')
                    except Exception:
                        continue
                    
                    if rel_path and not rel_path.startswith('..'):
                        referenced.add(rel_path)
    
    return referenced


def cleanup_unused_assets(site_dir: str, extra_whitelist: set[str] | None = None) -> None:
    """Remove unused static assets from the built site.
    
    This is a post-build cleanup that removes assets that are not referenced
    by any HTML, CSS, or JS file in the site.
    
    Args:
        site_dir: The built site directory
        extra_whitelist: Additional file paths to keep (relative to site_dir)
    """
    site_path = Path(site_dir)
    if not site_path.exists():
        return
    
    referenced = _find_referenced_assets(site_dir)
    
    # Add whitelist patterns
    if extra_whitelist:
        referenced.update(extra_whitelist)
    
    # Always keep these important files even if not directly referenced
    always_keep = {
        'sitemap.xml', 'sitemap.xml.gz',
        '404.html', 'search.html',
        'assets/javascripts/workers/search.js',  # Search worker loaded dynamically
    }
    referenced.update(always_keep)
    
    # Find all files that might be candidates for removal
    # Focus on heavy directories: icons, fonts, images
    candidate_dirs = ['.icons', 'assets/images', 'assets/fonts']
    
    removed_count = 0
    removed_size = 0
    
    for candidate_dir in candidate_dirs:
        dir_path = site_path / candidate_dir
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            rel_path = file_path.relative_to(site_path).as_posix()
            
            # Check if this file is referenced
            if rel_path not in referenced:
                # Double-check: is this file referenced by a relative path from another directory?
                # e.g., "../.icons/material/home.svg" from "assets/stylesheets/"
                is_referenced = False
                for ref in referenced:
                    if ref.endswith(os.path.basename(rel_path)) or rel_path in ref:
                        is_referenced = True
                        break
                
                if not is_referenced:
                    file_size = file_path.stat().st_size
                    try:
                        file_path.unlink()
                        removed_count += 1
                        removed_size += file_size
                        log.debug(f"Removed unused asset: {rel_path}")
                    except Exception as e:
                        log.warning(f"Could not remove {rel_path}: {e}")
    
    # Clean up empty directories
    for candidate_dir in candidate_dirs:
        dir_path = site_path / candidate_dir
        if not dir_path.exists():
            continue
        
        # Remove empty directories bottom-up
        for dirpath, dirnames, filenames in os.walk(str(dir_path), topdown=False):
            if not dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                    log.debug(f"Removed empty directory: {dirpath}")
                except Exception:
                    pass
    
    if removed_count > 0:
        log.info(
            f"Removed {removed_count} unused assets ({removed_size / 1024 / 1024:.2f} MB saved)"
        )


def remove_source_maps(site_dir: str) -> None:
    """Remove .map files and sourceMappingURL comments from the built site."""
    site_path = Path(site_dir)
    if not site_path.exists():
        return
    
    # Remove .map files
    removed_count = 0
    removed_size = 0
    
    for map_file in site_path.rglob('*.map'):
        if not map_file.is_file():
            continue
        
        file_size = map_file.stat().st_size
        try:
            map_file.unlink()
            removed_count += 1
            removed_size += file_size
        except Exception as e:
            log.warning(f"Could not remove {map_file}: {e}")
    
    if removed_count > 0:
        log.info(
            f"Removed {removed_count} source map files ({removed_size / 1024:.2f} KB saved)"
        )
    
    # Strip sourceMappingURL comments from JS files to prevent 404 requests
    js_files_modified = 0
    sourcemap_pattern = re.compile(r'//# sourceMappingURL=[^\s]+\s*\n?')
    
    for js_file in site_path.rglob('*.js'):
        if not js_file.is_file():
            continue
        
        try:
            content = js_file.read_text(encoding='utf-8', errors='ignore')
            if 'sourceMappingURL=' in content:
                cleaned = sourcemap_pattern.sub('', content)
                js_file.write_text(cleaned, encoding='utf-8')
                js_files_modified += 1
        except Exception as e:
            log.warning(f"Could not strip source map comment from {js_file}: {e}")
    
    if js_files_modified > 0:
        log.info(f"Stripped source map comments from {js_files_modified} JS files")


def remove_unused_font_formats(site_dir: str) -> None:
    """Remove font formats that are not needed (keep only WOFF2).
    
    Modern browsers support WOFF2. We keep WOFF as a fallback for older browsers
    but remove TTF, EOT, and SVG font formats.
    """
    site_path = Path(site_dir)
    if not site_path.exists():
        return
    
    font_dirs = list(site_path.rglob('**/fonts'))
    
    removed_count = 0
    removed_size = 0
    
    # Remove old font formats
    old_extensions = {'.ttf', '.eot', '.svg'}
    
    for font_dir in font_dirs:
        if not font_dir.is_dir():
            continue
        
        for font_file in font_dir.iterdir():
            if not font_file.is_file():
                continue
            
            if font_file.suffix.lower() in old_extensions:
                file_size = font_file.stat().st_size
                try:
                    font_file.unlink()
                    removed_count += 1
                    removed_size += file_size
                except Exception as e:
                    log.warning(f"Could not remove {font_file}: {e}")
    
    if removed_count > 0:
        log.info(
            f"Removed {removed_count} old font files ({removed_size / 1024:.2f} KB saved)"
        )


def optimize_assets(site_dir: str) -> None:
    """Run all asset optimization passes on the built site."""
    log.info("Optimizing static assets...")
    
    # Remove source maps (pure bloat)
    remove_source_maps(site_dir)
    
    # Remove unused font formats
    remove_unused_font_formats(site_dir)
    
    # Remove unused assets (icons, images, etc.)
    cleanup_unused_assets(site_dir)
    
    log.info("Asset optimization complete")
