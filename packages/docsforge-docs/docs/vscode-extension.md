# Visual Studio Code Extension

DocsForge provides a VS Code extension for writing, previewing, and building documentation without leaving your editor.

## Installation

### From GitHub Releases (Recommended)

1. Download the latest `.vsix` file from the [GitHub Releases page](https://github.com/QQSHI13/docsforge/releases)
2. In VS Code, open **Extensions** (`Ctrl+Shift+X`)
3. Click the **...** (More Actions) menu → **Install from VSIX...**
4. Select the downloaded `.vsix` file

### From VSIX (Manual)

```bash
# Install via command line
code --install-extension docsforge-vscode-*.vsix
```

### Prerequisites

- **VS Code 1.99+**
- **Python 3.10+** with `docsforge` installed:
  ```bash
  pip install docsforge
  ```

## Getting Started

### 1. Open a DocsForge project

Open a folder containing a `docsforge.yml` file. The extension activates automatically and prompts:

> **"DocsForge project detected. Start dev server?"**

Select **"Yes"** to start the dev server immediately, or use the sidebar later.

### 2. Create a new project

If you don't have a project yet:

1. Click the **DocsForge icon** in the activity bar (left sidebar)
2. Click **Initialize Project**
3. Follow the wizard: site name, description, theme color, language, privacy mode, etc.
4. The project is created in your workspace root

## Features

### Sidebar Actions

The DocsForge sidebar appears in the activity bar and shows contextual actions:

| Action | When | What it does |
|--------|------|-------------|
| **Start Server** | Server stopped | Starts `docsforge serve --no-open` in the workspace |
| **Stop Server** | Server running | Stops the running dev server |
| **Build** | Always | Runs `docsforge build` and shows output in the channel |
| **Open Preview** | Server running | Opens the site in VS Code's built-in browser |
| **Initialize Project** | Always | Creates a new DocsForge project interactively |

### Status Bar

The status bar shows the current server state:

- **`▶ DocsForge: stopped`** — Click to start the server
- **`▶ DocsForge: starting...`** — Server is starting up
- **`▶ DocsForge: http://localhost:8000`** — Server is running. Click to open preview

### Dev Server

The extension runs `docsforge serve --no-open` in the background:

- Output streams to the **DocsForge** output channel (`Ctrl+Shift+U` → select "DocsForge")
- A progress notification shows "Starting DocsForge server..." until the URL is detected
- When the server is ready, the URL appears in the status bar
- VS Code's built-in browser handles navigation and hot-reload

### Preview

Click **Open Preview** to see your site in VS Code's Simple Browser. This is VS Code's Electron-based browser — it supports all feature navigation, search, and page transitions.

### Build

Click **Build** to run `docsforge build`. Output streams to the DocsForge channel. A notification shows the result.

## Configuration

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `docsforge.pythonPath` | `"python"` | Python interpreter path. Use `"python3"` on systems where `python` isn't Python 3 |
| `docsforge.lan` | `false` | Serve on all interfaces (`0.0.0.0`) instead of localhost only |
| `docsforge.openBrowser` | `true` | Open the site in VS Code's Simple Browser when the server starts |

### Example: Configuring Python Path

If you use a virtual environment or a non-default Python:

```json
{
  "docsforge.pythonPath": "/home/user/.venv/bin/python"
}
```

Or via `.vscode/settings.json` in your project:

```json
{
  "docsforge.pythonPath": ".venv/bin/python"
}
```

## Workflows

### Edit → Preview Loop

1. **Start Server** from the sidebar
2. Click **Open Preview** when it's ready
3. Edit your Markdown files
4. The preview auto-reloads on save
5. **Stop Server** when done

### Build → Deploy

1. **Build** from the sidebar
2. Check the output for any errors
3. The built site is in `site/` — deploy anywhere

### Initialize → Develop → Deploy

1. **Initialize Project** — creates the project structure
2. **Start Server** — preview and iterate
3. **Build** — production build
4. Deploy `site/` to your hosting platform

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **"Failed to run python"** | Set `docsforge.pythonPath` to the correct Python binary |
| **"No docsforge.yml found"** | Run **Initialize Project** first, or create a `docsforge.yml` manually |
| **Preview shows blank page** | Check the DevTools console in VS Code (`Help → Toggle Developer Tools`) |
| **Server won't start** | Open the DocsForge output channel (`Ctrl+Shift+U`) for error details |
| **"python: command not found"** | Install Python 3.10+ from [python.org](https://python.org) |

## Commands

All available commands (accessible via `Ctrl+Shift+P`):

| Command | Description |
|---------|-------------|
| `DocsForge: Initialize Project` | Create a new docsforge project |
| `DocsForge: Start Dev Server` | Start the development server |
| `DocsForge: Stop Dev Server` | Stop the development server |
| `DocsForge: Build` | Build the documentation |
| `DocsForge: Open in VS Code Browser` | Open the preview |
| `DocsForge: Refresh` | Refresh the sidebar |

### Deploy Script

The project includes a convenience script that builds the VSIX and deploys the docs site:

```bash
./scripts/deploy.sh            # Build VSIX + install + deploy docs
./scripts/deploy.sh vsix       # Build the VSIX only
./scripts/deploy.sh install    # Build + install extension via VS Code CLI
./scripts/deploy.sh docs       # Build the docs site locally
./scripts/deploy.sh deploy     # Build + deploy docs to GitHub Pages
```

Requires `npm`, `vsce`, `code` (VS Code CLI), and `gh` (GitHub CLI) for full functionality.

## Updates

Check the [GitHub Releases](https://github.com/QQSHI13/docsforge/releases) for new versions. The release includes both the Python package and the `.vsix` file. Extension version matches the main package version.

## Next Steps

- [Usage Guide](publishing/usage.md) — Day-to-day DocsForge usage
- [Deployment Guide](publishing/deployment-guide.md) — Deploy your site after building
- [Features](features.md) — All core features
