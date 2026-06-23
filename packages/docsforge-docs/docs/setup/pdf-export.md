# PDF Export

DocsForge can export your documentation as PDF files using `docsforge build --pdf`.

## Quick Start

```bash
pip install "docsforge[pdf]"
playwright install chromium
docsforge build --pdf
```

Output goes to `pdf/` preserving the site directory structure.

## Requirements

| Dependency | Install | Purpose |
|-----------|---------|---------|
| **Playwright** | `pip install "docsforge[pdf]"` | Headless browser for rendering HTML to PDF |
| **Chromium** | `playwright install chromium` | Browser engine. Can also use system browser. |

## Usage

```bash
# Build site + export PDF
docsforge build --pdf

# Use more parallel tabs for faster rendering (default: 4)
docsforge build --pdf --jobs 8

# Single-threaded (for debugging)
docsforge build --pdf --jobs 1
```

The output is written to the `pdf/` directory, preserving the site's directory structure:

```
pdf/
├── index.pdf
├── getting-started/
│   └── index.pdf
└── setup/
    └── changing-the-colors/
        └── index.pdf
```

## System Browser

Instead of Playwright's bundled Chromium, use a system-installed browser:

```bash
export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser
docsforge build --pdf
```

Auto-detected browsers: thorium, chromium, google-chrome, brave-browser.

## Docker

```bash
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build --pdf
```

The Docker image includes Playwright, Chromium, and all dependencies.

## How It Works

1. **Full `docsforge build`** — runs the complete build pipeline with all plugins (Mermaid, KaTeX, TikZ, privacy, search)
2. **Playwright render** — opens each HTML page in a headless Chromium tab with `@media print` CSS
3. **Print mode strips UI chrome** — navigation bars, tabs, footer, search are hidden automatically
4. **Mermaid rendering** — diagrams are rendered by the browser before capture
5. **Tooltip expansion** — hover tooltips are expanded inline in the PDF
6. **Output** — one PDF per page, preserving the directory structure

## Performance

- **Parallel tabs**: defaults to 4. Use `--jobs N` to adjust
- **Network requests**: external requests are served from the local filesystem (privacy plugin cache)
- **Work queue**: each tab picks the next page as soon as it finishes — no batch waiting

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Mermaid diagrams blank** | Install Playwright's Chromium: `playwright install chromium` |
| **"Executable doesn't exist"** | Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to your system browser path |
| **Fonts missing** | Run `docsforge build` first so the privacy plugin downloads fonts |
| **PDF is empty / white** | Check `docsforge build` succeeds before running `--pdf` |
| **Slow rendering** | Increase parallel tabs: `--jobs 8` |
| **Error reading pages from file://** | Ensure your browser supports `--allow-file-access-from-files` |
