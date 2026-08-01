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

## Submitting changes

1. Create a focused branch for your change.
2. Add or update tests to cover the new behavior.
3. Ensure all tests pass.
4. Open a pull request describing what changed and why.

## Code of conduct

Be respectful and constructive in all interactions.
