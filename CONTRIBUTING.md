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
pip install -e .

# VS Code extension
cd vscode-docsforge
npm install
```

## Running tests

```bash
# Python unit / regression / integration tests
python -m pytest tests/unit tests/regression tests/integration -q

# VS Code extension pure-helper tests
cd vscode-docsforge
npm test
```

## Frontend development

The Material theme ships as **source** under `src/` and is
built into `docsforge/templates/` by the pipeline at
`build_frontend.py` (esbuild bundles, sass + autoprefixer
CSS, svgo icons, html-minifier-terser templates, minified service worker):

```bash
pnpm install   # esbuild, sass, svgo, ... (committed lockfile)
python build_frontend.py --clean
```

The pipeline is documented in `build_frontend.py` itself. Keep `src/` close to
upstream mkdocs-material (v9.7.7) and comment any intentional deviation where
you make it. The frontend CI job (`frontend.yml`) builds the frontend and
fails if the committed templates don't match the build, then runs the full
Python test suite on every push/PR.

## Submitting changes

1. Create a focused branch for your change.
2. Add or update tests to cover the new behavior.
3. Ensure all tests pass.
4. Open a pull request describing what changed and why.

## Code of conduct

Be respectful and constructive in all interactions.
