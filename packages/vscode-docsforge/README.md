# DocsForge for VS Code

Write and preview DocsForge documentation inside VS Code.

## Features

- **Dev Server** — Start/stop `docsforge serve` from the sidebar
- **Live Preview** — Open your site in VS Code's built-in browser with auto-reload
- **Build** — Run `docsforge build` with output streaming
- **Project Init** — Create new DocsForge projects with an interactive wizard

## Install

Download the `.vsix` from [GitHub Releases](https://github.com/QQSHI13/docsforge/releases), then:

```
Extensions → ... → Install from VSIX...
```

Requires Python 3.10+ with `docsforge` installed:

```bash
pip install docsforge
```

## Usage

1. Open a folder with `docsforge.yml`, or create one via **Initialize Project**
2. Click **Start Server** in the DocsForge sidebar
3. Click **Open Preview** when the server is ready

## Settings

| Name | Default | Description |
|------|---------|-------------|
| `docsforge.pythonPath` | `"python"` | Python interpreter to use |
| `docsforge.lan` | `false` | Serve on all interfaces |
| `docsforge.openBrowser` | `true` | Auto-open preview on server start |

## Build

```bash
npm install
npm run compile
vsce package
```
