# Contributing to DocsForge

Thank you for your interest in improving DocsForge!

DocsForge is a self-contained documentation engine: a vendored ProperDocs/MkDocs
engine + the Material for MkDocs theme, all plugins, all Markdown extensions,
KaTeX, Pygments, icons, fonts, and a service worker — one package, one command,
zero CDN calls.

This file is the entry point for contributors **and** for AI agents working in
this repository (`AGENTS.md` is a symlink to this file). For a deep dive into
what each part of the codebase does, read [`TECHNICAL.md`](TECHNICAL.md).

## Repository layout

| Path | What it is |
|------|-----------|
| `docsforge/` | The Python package (engine + core plugins + theme templates) |
| `src/` | Frontend source: Material theme templates + TypeScript/SCSS, built into `docsforge/templates/` |
| `build_frontend.py` | Frontend build pipeline (`src/` → `docsforge/templates/`) |
| `docs/` | The documentation site content (Markdown, en/zh twins) + its `docsforge.yml` |
| `studio/` | The DocsForge Studio VS Code extension (TypeScript, no language server) |
| `examples/` | Example sites (`sites/docsforge-demo`), plugins, hooks |
| `tests/` | Python tests (unit / regression / integration / e2e) |
| `.github/workflows/` | CI (test, e2e, frontend, studio), docs deploy, demo deploy, release |

## Reporting issues

Please open an issue on GitHub with:

- A clear description of the bug or feature request.
- Steps to reproduce (for bugs).
- The version of DocsForge, Python, and your operating system.

## Development setup

```bash
git clone https://github.com/QQSHI13/docsforge.git
cd docsforge

# Python package (editable, installs all runtime deps incl. pygments)
pip install -e .

# Frontend deps (esbuild, sass, svgo, icons, katex, mermaid, ...)
pnpm install

# VS Code extension
cd studio
npm install
```

## Running tests

```bash
# Python unit / regression / integration tests
python -m pytest tests/unit tests/regression tests/integration -q

# Browser E2E tests (Playwright + Chromium)
python -m pytest -m e2e -q

# VS Code extension pure-helper tests
cd studio
npm test

# Studio typecheck + lint
cd studio
npm run compile && npm run lint
```

## Frontend development

The Material theme ships as **source** under `src/` and is built into
`docsforge/templates/` by `build_frontend.py`:

```bash
pnpm install   # frozen lockfile; committed
python build_frontend.py --clean
```

The pipeline: icons are copied from node_modules and svgo-optimized
(`copy_icons`), templates are minified (`copy_templates`), TypeScript is
bundled with esbuild (`build_typescript`), SCSS is compiled + autoprefixed
(`build_styles`), `pygments.css` is regenerated from the installed Pygments
(`generate_pygments_css`), and KaTeX / Mermaid / Lunr stemmers / the service
worker are copied from node_modules (`copy_katex`, `copy_mermaid`,
`copy_lunr`, `copy_sw`). The twemoji SVG set is vendored under
`src/templates/assets/emoji/twemoji/` (the npm package no longer ships the
assets) — refresh it with `python build_frontend.py --fetch-twemoji` and
commit the result; `copy_twemoji` syncs it into `docsforge/templates/`
like the icon sets. See `build_frontend.py` for details.

The **frontend CI job** builds the frontend and fails if the committed
`docsforge/templates/` don't match the build (a parity check). Keep `src/`
close to upstream mkdocs-material and comment any intentional deviation where
you make it.

## Documentation & translations

- Docs content lives in `docs/docs/` as **en/zh twin pairs** (`page.md` +
  `page.zh.md`). The repo maintains perfect twin coverage — any new or edited
  English page must ship with its Chinese translation in the same change.
- The demo site lives in `examples/sites/docsforge-demo/` (own `docsforge.yml`).
- Changelog: `docs/docs/changelog/index.md` (en) + `index.zh.md` (zh). The
  release workflow extracts the version's entry for the GitHub release notes,
  so keep both current.
- License: Apache-2.0. Upstream attribution is consolidated in `NOTICE` and
  `docs/docs/license.md`.

## Commit conventions

This repository uses **Conventional Commits** — machine-readable messages that
drive the changelog and release notes:

```
<type>(<scope>): <subject>
```

- `<type>` — one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
  `test`, `build`, `ci`, `chore`, `revert`.
- `<scope>` — optional, lowercase module or area (`minify`, `search`, `i18n`,
  `studio`, `frontend`, `deps`, `docs`, ...).
- `<subject>` — imperative, lowercase, ≤ 72 characters, no trailing period.

Examples:

```
feat(minify): consolidate minifier forks into minify-go
fix(i18n): restore missing EN changelog heading
docs: changelog entry for the new release (en + zh)
chore(deps): bump lunr-languages from 1.20.0 to 1.21.0
```

Rules:

- `feat` and `fix` (user-visible changes) **must** ship a changelog entry in
  both `docs/docs/changelog/index.md` and `index.zh.md` — the release
  workflow extracts the version's entry for the GitHub release notes.
- `docs`-type changes that touch an English page **must** include the Chinese
  twin in the same commit (see "Documentation & translations" above).
- Breaking changes: add `!` after the type/scope (`feat!(api): ...`) and
  describe the migration in the changelog entry.

A commit message template ships as `gitmessage` at the repository root.
Enable it once:

```bash
git config commit.template gitmessage
```

After that, `git commit` opens the template with the rules and examples
pre-filled.

## Submitting changes

1. Create a focused branch for your change.
2. Add or update tests to cover the new behavior.
3. Ensure all tests pass (Python suite, studio `npm test`; frontend parity
   when touching `src/`).
4. Open a pull request describing what changed and why.

## Code of conduct

Be respectful and constructive in all interactions.
