# PDF Export

DocsForge can export your documentation as PDF files using `docsforge build --pdf`.

## Quick Start

```bash
pip install "docsforge[pdf]"
playwright install chromium  # or set PLAYWRIGHT_CHROMIUM_EXECUTABLE
docsforge build --pdf
```

Output goes to `pdf/` preserving the site directory structure.

## Requirements

| Dependency | Install | Purpose |
|-----------|---------|---------|
| **Playwright** | `pip install playwright` | Headless browser for rendering HTML to PDF |
| **Chromium** | `playwright install chromium` | Browser engine. Can also use system browser (see below). |

## Usage

```bash
# Build site + export PDF
docsforge build --pdf

# Use more parallel tabs for faster rendering
docsforge build --pdf --jobs 8

# Only export PDF (skip rebuild if site is already built)
docsforge build --pdf
```

## System Browser

Instead of Playwright's bundled Chromium, you can use a system-installed browser:

```bash
export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser
docsforge build --pdf
```

Auto-detected browsers: thorium, chromium, google-chrome, brave-browser.

## How It Works

1. **Full `docsforge build`** — runs the complete build pipeline with all plugins
2. **Playwright render** — opens each HTML page in a headless Chromium tab
3. **Print mode** — uses CSS `@media print` to strip navigation, tabs, footer
4. **Mermaid rendering** — diagrams are rendered by the browser before capture
5. **Tooltip expansion** — hover tooltips are expanded inline in the PDF
6. **Output** — one PDF per page, preserving the site directory structure

## Performance

- **Parallel tabs**: defaults to 4. Use `--jobs N` to adjust
- **Network requests**: external requests are served from the local filesystem
- **Mermaid**: waits for all diagrams to render before capturing each page
