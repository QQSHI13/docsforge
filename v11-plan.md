# DocsForge v11.0.0 — Built-in Editor Plan

## Vision

`docsforge serve --editor` launches a live web-based Markdown editor alongside the dev server. Edit docs in the browser, see changes instantly in the preview pane, save to disk — livereload updates the site automatically.

**Why:** MkDocs/Material has zero editor story. DocsForge becomes a lightweight CMS for teams, not just a static generator. Non-technical writers can contribute without touching a text editor.

---

## User Experience

### Launch

```bash
docsforge serve              # normal dev server
docsforge serve --editor     # dev server + editor UI on port+1 (default: 8001)
docsforge serve --editor-port 9000   # custom editor port
```

### Editor UI

Navigate to `http://localhost:8001` (or `--editor-port`):

```
┌────────────────┬──────────────────────────────┐
│  📁 docs/      │  editor.md              [💾] │
│  ├── index.md  ├──────────────────────────────┤
│  ├── getting-  │  📝 Edit    👁️ Preview        │
│  │   started.md│  ────────────────────────────  │
│  ├── setup/    │  # Getting Started             │
│  │   └── ...  │                                │
│  └── reference/│  Write markdown here...        │
│      └── ...   │                                │
│                │  [Front Matter]                │
│ [+ New File]   │  ────────────────────────────  │
│                │  description: Foo              │
│                │  tags: [bar]                   │
└────────────────┴──────────────────────────────┘
```

**Sidebar:** File tree of `docs/` directory. Click to open. Collapsible folders.

**Editor pane:** Monaco Editor (VS Code's engine) with Markdown syntax highlighting, auto-completion for Material admonitions (`!!! note`), front matter keys, internal links.

**Preview pane:** Live-rendered HTML using the same build pipeline as `docsforge build`, so what you see = what you get. Updates on save (or auto-save).

**Front matter editor:** Toggle between raw YAML and form fields (description, tags, title). Validates YAML.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` / `Cmd+S` | Save file |
| `Ctrl+P` / `Cmd+P` | Quick open file |
| `Ctrl+Shift+N` | New file |
| `Ctrl+Shift+D` | Delete file (confirm) |
| `Ctrl+Shift+S` | Sync nav (update `docsforge.yml` if needed) |

---

## Technical Architecture

### Components

```
┌─────────────────────────────────────────────┐
│           docsforge serve --editor          │
├─────────────────────────────────────────────┤
│  Livereload Server (port 8000)              │
│  ├── Serves built site + WebSocket reload   │
│  └── Already exists                         │
├─────────────────────────────────────────────┤
│  Editor Server (port 8001)                  │
│  ├── Static UI assets (HTML/CSS/JS)         │
│  ├── REST API: /__editor/api/               │
│  └── WebSocket: live sync / preview push    │
└─────────────────────────────────────────────┘
```

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/__editor/api/files` | List all `.md` files in `docs/` |
| `GET` | `/__editor/api/file?path=docs/index.md` | Read file content |
| `PUT` | `/__editor/api/file` | Save file `{path, content}` |
| `POST` | `/__editor/api/file` | Create new file `{path, content}` |
| `DELETE` | `/__editor/api/file?path=docs/x.md` | Delete file |
| `GET` | `/__editor/api/config` | Current `docsforge.yml` (sanitized) |
| `POST` | `/__editor/api/nav` | Update nav entry `{path, title}` |
| `POST` | `/__editor/api/preview` | Render markdown → HTML preview |
| `POST` | `/__editor/api/upload` | Upload image/asset to `docs/assets/` |

### File Operations

- **Read:** Direct `open()` on `docs/` tree, respect `exclude_docs`
- **Write:** Atomic write (temp file + rename), validate Markdown before save
- **Create:** Prompt for filename, auto-add `.md`, optional front matter template
- **Delete:** Confirm dialog, optional "Move to trash" subdir
- **Upload:** Save to `docs/assets/`, return relative path for Markdown insertion

### Security

- **Default:** `localhost` / `127.0.0.1` only (`--editor-host` to override)
- **Optional auth:** `--editor-password secret` adds basic HTTP auth
- **No execution:** Editor only touches `docs/` and `docsforge.yml` nav section. Never runs arbitrary code.
- **Backup:** On first save of each session, create `.docsforge-backup/` with original files (git is better, but safety net)

### Monaco Integration

- CDN load from jsDelivr or vendored in `docsforge/editor/static/`
- Markdown mode with custom completions:
  - `!!!(type)` → admonition snippet
  - `=== "Tab"` → content tab snippet
  - `[text](` → autocomplete from `nav:` for internal links
  - Front matter key hints (`description:`, `tags:`, `icon:`)
- Vendored approach preferred (no internet dependency)

---

## Build Pipeline Integration

### Preview Rendering

When user hits Save:
1. Write to disk
2. Trigger livereload WebSocket → browser refreshes
3. Editor's preview pane calls `POST /__editor/api/preview` with content
4. Server runs same Markdown → HTML pipeline as `Page.render()` but returns HTML fragment
5. Preview pane injects HTML into iframe with Material CSS

### Nav Sync

When creating/deleting/moving files:
- Prompt: "Add to navigation?"
- If yes, modify `docsforge.yml` nav section
- Validate YAML after modification
- Show visual diff before applying

---

## Implementation Phases

### Phase 1: Core Editor (MVP)
- [ ] `docsforge serve --editor` flag parsing
- [ ] Editor server on secondary port (Flask/FastAPI/simple WSGI)
- [ ] Static UI: file tree sidebar + Monaco editor
- [ ] REST API: read/save files
- [ ] Basic preview pane (iframe with livereload)

### Phase 2: Enhanced UX
- [ ] Front matter form editor
- [ ] Auto-complete for admonitions, internal links
- [ ] New file / delete / rename
- [ ] Image drag-drop upload
- [ ] Quick open (`Ctrl+P`)
- [ ] Keyboard shortcuts

### Phase 3: Power Features
- [ ] Nav editor (drag-and-drop reorder in UI)
- [ ] Search across all docs
- [ ] Spell check
- [ ] Git integration (show changed files, commit button)
- [ ] Collaborative cursors (WebSocket sync for multi-user)

### Phase 4: Polish
- [ ] Mobile-responsive editor UI
- [ ] Theme switcher (matches docs palette)
- [ ] Plugin: custom editor extensions
- [ ] Export to PDF / single-page HTML from editor

---

## Why v11.0.0 (Major Version)

This is a **paradigm shift**:
- v10.x: Static site generator (MkDocs replacement)
- v11.x: Live documentation platform with authoring UI

Justifies major bump because:
1. New default behavior (`serve` could auto-open editor in future)
2. New dependency footprint (Monaco, optional WebSocket lib)
3. New mental model — DocsForge is not just "build docs" but "write docs"

---

## Open Questions

1. **Monaco vs CodeMirror vs simple textarea?**
   - Monaco: Best UX, heavy (~2MB JS)
   - CodeMirror: Lighter, good enough
   - **Decision:** Monaco vendored, loaded on demand

2. **Separate process or thread?**
   - Same process: simpler, but blocks if editor crashes
   - Separate thread: harder, safer
   - **Decision:** Same process for MVP, refactor later

3. **Preview: iframe or live render?**
   - iframe pointing at livereload site: simplest, but full page reload
   - Live render API: snappier, more work
   - **Decision:** iframe for MVP, API preview for Phase 2

4. **Authentication for remote access?**
   - `--editor-password` basic auth
   - Or integrate with GitHub OAuth for team use
   - **Decision:** `--editor-password` for MVP, OAuth plugin later

---

## Competitor Analysis

| Tool | Editor | Live Preview | File Browser | Notes |
|------|--------|--------------|--------------|-------|
| **MkDocs** | ❌ | ✅ (serve) | ❌ | No editor at all |
| **Material for MkDocs** | ❌ | ✅ | ❌ | Theme only |
| **Docusaurus** | ❌ | ✅ | ❌ | No editor |
| **GitBook** | ✅ | ✅ | ✅ | SaaS, proprietary |
| **Notion** | ✅ | ✅ | ✅ | Not static site generator |
| **DocsForge v11** | ✅ | ✅ | ✅ | **Static + editor = unique** |

**Differentiator:** DocsForge is the only open-source, self-hosted, static-site generator with a built-in editor that renders identically to the final output.

---

*Plan created 2026-05-25 by Nova ☄️*
