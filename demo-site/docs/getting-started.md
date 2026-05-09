# Getting Started

## Installation

```bash
pip install docsforge
```

This installs:
- ProperDocs engine (MkDocs fork)
- Material for MkDocs theme
- All recommended plugins

## Create a New Site

```bash
docsforge new my-documentation
cd my-documentation
```

## Preview Locally

```bash
docsforge serve
```

Open http://127.0.0.1:8000 in your browser.

## Build for Production

```bash
docsforge build
```

The built site will be in the `site/` directory.

## Deploy to GitHub Pages

```bash
docsforge gh-deploy
```

---

*Next: [Features](features.md)*
