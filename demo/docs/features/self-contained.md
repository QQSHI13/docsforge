# Self-Contained

DocsForge is designed to work **without any external dependencies** for the core engine.

## How It Works

All upstream code is vendored into `docsforge/_vendor/`:

```
docsforge/
├── _vendor/
│   ├── mkdocs/          # MkDocs 1.6 engine
│   └── properdocs/        # Material 9.7 engine
├── plugins/               # Material plugins (blog, tags, etc.)
├── themes/material/       # Material theme templates
└── extensions/            # Markdown extensions
```

## Why Vendoring?

1. **No Dependency Hell**: No conflicting versions of MkDocs/Material
2. **Reproducible Builds**: Same code every time, no lockfiles needed
3. **Offline Compatible**: Works without internet after install
4. **Faster Install**: Single package, no resolving dependency tree

## Optional Dependencies

Some plugins need extra packages:

| Plugin | Extra | Install |
|--------|-------|---------|
| Social cards | Pillow, CairoSVG | `pip install docsforge[imaging]` |
| Optimize | pngquant binary | `apt install pngquant` |
| Versioning | mike | `pip install docsforge[versioning]` |

Core features (search, blog, tags, theme) work out of the box.
