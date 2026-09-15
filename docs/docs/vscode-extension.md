---
icon: material/microsoft-visual-studio-code
---

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

- **VS Code 1.85+**
- **Python 3.10+** with `docsforge` installed:
  ```bash
  pip install docsforge
  ```

If `docsforge` is missing, the extension offers to install it into a project `.venv`, for your user, or globally — you don't have to set anything up by hand.

## Updating

You never have to watch the releases page. The extension updates itself on two channels:

### Check for Updates

Run **`DocsForge: Check for Updates`** from the command palette (`Ctrl+Shift+P`), the sidebar Actions view, or the sidebar title bar. One check covers both:

- **Engine** — the `docsforge` Python package, compared against PyPI. Updating runs `pip install docsforge==<version>` in the same interpreter your project already uses (venv, user, or global install), with progress and output in the DocsForge channel.
- **Extension** — the VSIX itself, compared against GitHub releases. Updating downloads the `.vsix` to a temp file, installs it, and offers to reload the window.

### Automatic checks

About 45 seconds after startup, the extension silently checks in the background and notifies you only when something is newer. Each version nags at most once ("Don't ask again" is per version). Disable it entirely with:

```json
{
  "docsforge.autoCheckUpdates": false
}
```

### Pre-releases

Beta and alpha releases are skipped by default. To track them (recommended while a `13.0.0bN`-style beta is current):

```json
{
  "docsforge.includePrereleases": true
}
```

The sidebar Actions item shows the available versions inline once a check finds them, e.g. `Check for Updates — engine 12.5.7 → 13.0.0b3`.

> **Coming from 12.5.7 or older?** Those builds predate the updater — install one newer VSIX by hand (see above), and every update after that is one click.

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
4. The project is created in your workspace root — editor features activate immediately, no reload needed

## Features

### Sidebar Actions

The DocsForge sidebar appears in the activity bar and shows contextual actions:

| Action | When | What it does |
|--------|------|-------------|
| **Start Server** | Server stopped | Starts `docsforge serve --no-open` in the workspace |
| **Stop Server** | Server running | Stops the running dev server |
| **Build** | Always | Runs `docsforge build` and shows output in the channel |
| **Stop Build** | Build running | Cancels the running build |
| **Open Preview** | Server running | Opens the site in VS Code's built-in browser |
| **Open Built Page** | Server running | Opens the built HTML for the current document |
| **Initialize Project** | Always | Creates a new DocsForge project interactively |
| **Open Docs** | Always | Opens the DocsForge documentation site |
| **Open Output** | Always | Shows the DocsForge build/serve output panel |
| **Check Python Environment** | Always | Detects Python and installs DocsForge if missing |
| **Rename Document** | Always | Renames a document and updates all links to it |
| **Rename Anchor** | Always | Renames a heading and updates all links to its anchor |
| **Refresh Diagnostics** | Always | Re-reads the build validation cache and refreshes squiggles |
| **Check for Updates** | Always | Checks for engine and extension updates (shows versions when found) |

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

Click **Build** to run `docsforge build`. Output streams to the DocsForge channel. A notification shows the result. Diagnostics refresh automatically when the build finishes.

### Editor intelligence

No language server needed — the extension reads your project directly:

- **Diagnostics** — broken links, missing anchors, and footnote problems surface as squiggles, sourced from the build's validation cache and refreshed after every build (or on demand via Refresh Diagnostics)
- **Link navigation** — go-to-definition and hover on Markdown links jump to the target document and anchor; path completions inside `(...)` suggest project files
- **Rename** — Rename Document moves a file (plus its translations) and rewrites every link to it in one undoable step; Rename Anchor does the same for headings. Renaming a folder in the Explorer updates links too
- **Quick fixes** — the lightbulb on a broken link offers to fix it (or all broken links in scope)
- **Formatting** — Format Document tidies trailing whitespace and blank-line runs (also available on save via `editor.formatOnSave`)

## Configuration

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `docsforge.pythonPath` | `"python"` | Python interpreter path. Use `"python3"` on systems where `python` isn't Python 3 |
| `docsforge.lan` | `false` | Serve on all interfaces (`0.0.0.0`) instead of localhost only |
| `docsforge.openBrowser` | `true` | Open the site in VS Code's Simple Browser when the server starts |
| `docsforge.rememberedPython` | `""` | Interpreter the extension resolved (e.g. a project `.venv`). Managed automatically; set `pythonPath` to override |
| `docsforge.formatOnSave` | `false` | Format the Markdown document on save (requires `editor.formatOnSave`) |
| `docsforge.autoCheckUpdates` | `true` | Check for engine and extension updates after startup; notifies only when something is newer |
| `docsforge.includePrereleases` | `false` | Include beta/alpha releases when checking for updates |

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

### Stay current

1. Accept the update notification, or run **Check for Updates**
2. Update the engine, the extension, or both
3. Reload when prompted — that's the whole release process

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **"Failed to run python"** | Set `docsforge.pythonPath` to the correct Python binary, or run **Check Python Environment** |
| **"No docsforge.yml found"** | Run **Initialize Project** first, or create a `docsforge.yml` manually |
| **Preview shows blank page** | Check the DevTools console in VS Code (`Help → Toggle Developer Tools`) |
| **Server won't start** | Open the DocsForge output channel (`Ctrl+Shift+U`) for error details |
| **"python: command not found"** | Install Python 3.10+ from [python.org](https://python.org) |
| **Update check can't reach the server** | Check your connection / proxy; the check is skipped silently at startup and warns only on manual runs |
| **On a beta but offered nothing** | Turn on `docsforge.includePrereleases` — betas are excluded by default |

## Commands

All available commands (accessible via `Ctrl+Shift+P`):

| Command | Description |
|---------|-------------|
| `DocsForge: Initialize Project` | Create a new DocsForge project |
| `DocsForge: Start Server` | Start the development server |
| `DocsForge: Stop Server` | Stop the development server |
| `DocsForge: Build` | Build the documentation |
| `DocsForge: Stop Build` | Cancel the running build |
| `DocsForge: Open Preview` | Open the site in VS Code's built-in browser |
| `DocsForge: Open Built Page` | Open the built HTML for the current document |
| `DocsForge: Refresh` | Refresh the sidebar |
| `DocsForge: Open Docs` | Open the DocsForge documentation site |
| `DocsForge: Open Output` | Show the DocsForge output panel |
| `DocsForge: Check Python Environment` | Detect Python and install DocsForge if missing |
| `DocsForge: Rename Document` | Rename a document and update all links |
| `DocsForge: Rename Anchor` | Rename a heading and update its anchor links |
| `DocsForge: Refresh Diagnostics` | Re-read validation cache and refresh squiggles |
| `DocsForge: Open Link Target` | Jump to a link's target (used by quick fixes) |
| `DocsForge: Check for Updates` | Check for engine and extension updates |

## Next Steps

- [Usage Guide](publishing/usage.md) — Day-to-day DocsForge usage
- [Deployment Guide](publishing/deployment-guide.md) — Deploy your site after building
- [Features](features.md) — All core features
