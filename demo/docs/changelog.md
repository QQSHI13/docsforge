# Changelog

## 9.7.6

### Added
- Vendored MkDocs 1.6 and Material 9.7 into `_vendor/`
- All plugins work without external dependencies
- Added `material/minify` plugin
- Added `imaging` optional dependency group (Pillow, CairoSVG)

### Changed
- Renamed package to DocsForge
- All imports rewritten to use internal packages
- Entry points registered for `mkdocs.*`, `properdocs.*`, and `docsforge.*`

### Fixed
- Config class type checking for vendored packages
- Emoji extension path resolution
- Privacy plugin asset downloading
