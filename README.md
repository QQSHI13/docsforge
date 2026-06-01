# DocsForge Monorepo

> **The drop-in replacement for MkDocs + Material for MkDocs.**
> One package. One command. Beautiful docs. Zero CDN calls.
> ⚠️ **Development Mode**: DocsForge is under active development. Expect breaking changes and large updates until v11.0.0.

This is the monorepo containing all DocsForge projects:

| Package | Language | Description |
|---------|----------|-------------|
| [`packages/docsforge`](packages/docsforge/) | Python | Core documentation engine |
| [`packages/docsforge-docs`](packages/docsforge-docs/) | Markdown | Documentation website |
| [`packages/vscode-docsforge`](packages/vscode-docsforge/) | TypeScript | VS Code extension |

## Quick Start

```bash
# Install the core package
pip install packages/docsforge

# Or from PyPI
pip install docsforge

# Create a new project
docsforge --init

# Start dev server
docsforge serve

# Build for production
docsforge build
```

## Development

```bash
# Clone the monorepo
git clone https://github.com/QQSHI13/docsforge.git
cd docsforge

# Install core package in development mode
pip install -e packages/docsforge

# Build documentation site
cd packages/docsforge-docs
docsforge build

# Install VS Code extension dependencies
cd packages/vscode-docsforge
npm install
```

## Packages

### Core (`packages/docsforge`)

The Python package that builds documentation. See its [README](packages/docsforge/) for full details.

Features:
- 31 Markdown extensions (pymdownx + python-markdown)
- 7 built-in plugins (search, tags, blog, info, meta, minify, privacy)
- KaTeX math, Mermaid diagrams, TikZ diagrams
- 14,000+ icons included
- Dark mode with system detection
- Offline PWA with service worker
- Zero CDN calls

### VS Code Extension (`packages/vscode-docsforge`)

Extension for writing and previewing docs inside VS Code.

Features:
- Initialize project from VS Code
- Start/stop dev server with one click
- Live preview in VS Code panel
- One-click deploy to GitHub Pages
- Autocomplete for Markdown extensions

### Documentation (`packages/docsforge-docs`)

The documentation website at https://qqshi13.github.io/docsforge-docs/

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

LGPL v3 - See [LICENSE](packages/docsforge/LICENSE) for details.
