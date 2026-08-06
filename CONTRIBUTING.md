# Contributing to DocsForge

Thank you for your interest in improving DocsForge!

## Reporting issues

Please open an issue on GitHub with:
- A clear description of the bug or feature request.
- Steps to reproduce (for bugs).
- The version of DocsForge, Python, and your operating system.

## Development setup

```bash
git clone https://github.com/QQSHI13/docsforge.git
cd docsforge

# Python package
pip install -e packages/docsforge

# VS Code extension
cd packages/vscode-docsforge
npm install
```

## Running tests

```bash
# Python unit / regression / integration tests
cd packages/docsforge
python -m pytest tests/unit tests/regression tests/integration -q

# VS Code extension pure-helper tests
cd packages/vscode-docsforge
npm test
```

## Frontend development

The Material theme ships as **source** under `packages/docsforge/src/` and is
built into `packages/docsforge/docsforge/templates/` by the in-repo pipeline
(esbuild bundles, sass + autoprefixer CSS, svgo icons, html-minifier-terser
templates, minified service worker):

```bash
cd packages/docsforge
pnpm install   # esbuild, sass, svgo, ... (committed lockfile)
python scripts/build_frontend.py --clean
```

`scripts/frontend-patches.md` is the living inventory of every intentional
deviation from upstream mkdocs-material (v9.7.7) — keep it in sync when you
touch `src/`.

Every change to `src/` must keep the committed output reproducible. Run the
per-area parity gates before pushing:

```bash
cd packages/docsforge
for area in templates css js sw lunr; do
  python scripts/check_frontend_parity.py --area "$area"
done
python scripts/check_frontend_parity.py --vs-ref main   # fast output diff vs main
```

- `--area X` — fresh build vs the committed output for area X (the gate).
- `--vs-ref REF` — committed output vs the same dir at git ref REF, no build.
- `--baseline-snapshot scripts/parity/baseline-*.sha256` — every delta vs the
  pre-migration output (no whitelist).
- `SENTINEL_MARKERS` in the parity script fail the gate if a DocsForge
  customization string (e.g. `X-DocsForge-Instant-Nav`) disappears from a
  fresh build — hash parity alone cannot see a lost customization.

## Submitting changes

1. Create a focused branch for your change.
2. Add or update tests to cover the new behavior.
3. Ensure all tests pass.
4. Open a pull request describing what changed and why.

## Code of conduct

Be respectful and constructive in all interactions.
